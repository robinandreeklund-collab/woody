"""DeviceManager — enheternas status + kalibrerings-API mot QML.

Exponerar den LÅSTA hårdvarukatalogen med live anslutningsstatus, och kör
kalibreringsmetoder (CalibrationRunner) med progress-signaler som GUI binder mot.

  * SIM-läge: alla enheter "SIM" (gröna), metoder kör simulerat → hela
    GUI-flödet är testbart innan hårdvaran kommer.
  * REAL-läge: HAL-enheter probas (i bakgrundstråd, blockerar inte GUI);
    fält-enheter utan egen buss (lasrar/encodrar/fotocell) får status via
    GPIO/sina värdar. Metoder kräver ansluten enhet.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import autocalib
from .calibration import (CALIB_METHODS, DEVICE_CATALOG, CalibrationRunner,
                          CalibrationStore, methods_for)

_TICK_MS = 120


class DeviceManager(QObject):
    devicesChanged = Signal()         # status/anslutning ändrad
    methodsChanged = Signal()         # kalibreringsresultat ändrat → rebinda metodlistor
    calibChanged = Signal()           # pågående körning (pct/steg) ändrad

    def __init__(self, cfg, scanner=None, store_path="data/calibration.json", parent=None):
        super().__init__(parent)
        self._mode = getattr(cfg, "mode", "sim")
        self._scanner = scanner
        self._store = CalibrationStore(store_path)
        # Real-läge: ge runnern kameraåtkomst så auto-rutinerna kan MÄTA mot HAL.
        ctx = (autocalib.CalibrationContext(scanner)
               if self._mode == "real" and scanner is not None else None)
        self._runner = CalibrationRunner(self._store, sim=(self._mode == "sim"), context=ctx)
        self._runner.on_progress = self._on_progress
        self._runner.on_finished = self._on_finished
        self._status: dict[str, dict] = {}            # dev_id -> {connected, status}
        self._armed = False                           # laser-interlock (klass 3B)
        self._calib = {"dev": "", "method": "", "title": "", "pct": 0.0,
                       "msg": "", "log": [], "result": "", "ok": True}
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._init_status()

    # ------------------------------------------------------------------ status
    def _init_status(self):
        for dev_id, *_ in DEVICE_CATALOG:
            if self._mode == "sim":
                self._status[dev_id] = {"connected": True, "status": "SIM"}
            else:
                self._status[dev_id] = {"connected": False, "status": "EJ ANSLUTEN"}
        if self._mode == "real":
            self.refresh()

    @Slot()
    def refresh(self):
        """Proba verklig hårdvara i bakgrundstråd (blockera aldrig GUI)."""
        if self._mode != "real" or self._scanner is None:
            self.devicesChanged.emit()
            return

        def probe():
            # HAL-enheter: profilkameror, linjekamera, transportör
            hal_map = {"prof_red": self._scanner.profile_red,
                       "prof_green": self._scanner.profile_green,
                       "surface": self._scanner.surface,
                       "conveyor": self._scanner.conveyor}
            for dev_id, dev in hal_map.items():
                try:
                    dev.open()
                    self._status[dev_id] = {"connected": True, "status": "ANSLUTEN"}
                except Exception as exc:
                    self._status[dev_id] = {"connected": False,
                                            "status": f"EJ ANSLUTEN · {str(exc)[:60]}"}
            # 3× LR400 över RS-485 (Waveshare 4CH) — ansluten om någon kanal svarar
            pls = getattr(self._scanner, "point_lasers", []) or []
            n_ok = 0
            for pl in pls:
                try:
                    pl.open(); n_ok += 1
                except Exception:
                    pass
            self._status["lr400"] = {"connected": n_ok > 0,
                                     "status": f"{n_ok}/{len(pls)} kanaler · RS-485" if pls
                                               else "EJ ANSLUTEN"}
            # enheter utan egen buss: status via sina värdar
            conv_ok = self._status["conveyor"]["connected"]
            surf_ok = self._status["surface"]["connected"]
            self._status["enc_a"] = {"connected": conv_ok,
                                     "status": "VIA ROBOCLAW" if conv_ok else "VÄNTAR PÅ ROBOCLAW"}
            self._status["enc_b"] = {"connected": conv_ok or surf_ok,
                                     "status": "VIA KAMERA/EN2" if (conv_ok or surf_ok) else "VÄNTAR"}
            # fält-IO via gpio_io (riktiga pin-setup:er, släcker alltid vid close)
            gpio_map = {"laser_red": getattr(self._scanner, "laser_red", None),
                        "laser_green": getattr(self._scanner, "laser_green", None),
                        "led_white": getattr(self._scanner, "led_white", None),
                        "photocell": getattr(self._scanner, "photocell", None)}
            for d, dev in gpio_map.items():
                if dev is None:
                    self._status[d] = {"connected": False, "status": "SAKNAS I HAL"}
                    continue
                try:
                    dev.open()
                    st = dev.info().interface
                    if d == "photocell":
                        st += " · " + ("BRÄDA VID ANHÅLL" if dev.read() else "ingen bräda")
                    self._status[d] = {"connected": True, "status": st}
                except Exception as exc:
                    self._status[d] = {"connected": False,
                                       "status": f"GPIO EJ REDO · {str(exc)[:40]}"}
            self._status["jetson"] = {"connected": True, "status": "DENNA NOD"}
            self._status["rig"] = {"connected": all(s["connected"] for k, s in self._status.items()
                                                    if k in hal_map),
                                   "status": "REDO" if conv_ok else "DELVIS"}
            self.devicesChanged.emit()

        threading.Thread(target=probe, daemon=True).start()

    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        out = []
        for dev_id, name, model, iface, kind in DEVICE_CATALOG:
            st = self._status.get(dev_id, {"connected": False, "status": "?"})
            out.append({"id": dev_id, "name": name, "model": model, "iface": iface,
                        "kind": kind, "connected": st["connected"], "status": st["status"],
                        "calibDone": self._store.count_done(dev_id),
                        "calibTotal": len(methods_for(dev_id))})
        return out

    @Property("QVariantMap", notify=devicesChanged)
    def statusMap(self):
        return {k: dict(v) for k, v in self._status.items()}

    @Property(str, constant=True)
    def mode(self):
        return self._mode

    # ----------------------------------------------------------- kalibrering
    @Slot(str, result="QVariantList")
    def methodsFor(self, dev_id: str):
        out = []
        for m in methods_for(dev_id):
            rec = self._store.get(dev_id, m["id"]) or {}
            values = rec.get("values", {})
            out.append({
                "id": m["id"], "title": m["title"], "desc": m["desc"],
                "steps": [s[0] for s in m["steps"]],
                "done": bool(rec.get("ok")), "date": rec.get("date", ""),
                "auto": autocalib.has_auto(dev_id, m["id"]),   # mäter mot kameran
                "summary": " · ".join(f"{k}: {v}" for k, v in list(values.items())[:3]),
            })
        return out

    @Slot(str, str, result=bool)
    def startCalibration(self, dev_id: str, method_id: str) -> bool:
        st = self._status.get(dev_id, {})
        method = next((m for m in methods_for(dev_id) if m["id"] == method_id), None)
        if method is None:
            return False
        ok = self._runner.start(dev_id, method_id, connected=st.get("connected", False))
        if ok:
            self._calib = {"dev": dev_id, "method": method_id, "title": method["title"],
                           "pct": 0.0, "msg": method["steps"][0][0],
                           "log": [], "result": "", "ok": True}
            self._timer.start()
            self.calibChanged.emit()
        return ok

    # ------------------------------------------------- lasersäkerhet (klass 3B)
    @Slot(bool, result=bool)
    def armLasers(self, confirm: bool) -> bool:
        """Bekräfta människo-interlock → lås upp laser-tändning. Auto-kalibrering
        får då tända→mäta→släcka. Speglar RemoteNode.armLasers (samma GUI funkar)."""
        fn = getattr(self._scanner, "arm_lasers", None)
        self._armed = bool(fn(confirm=confirm)) if fn else bool(confirm)
        self.devicesChanged.emit()
        return self._armed

    @Slot()
    def disarmLasers(self):
        fn = getattr(self._scanner, "disarm_lasers", None)
        if fn:
            fn()
        self._armed = False
        self.devicesChanged.emit()

    @Property(bool, notify=devicesChanged)
    def lasersArmed(self) -> bool:
        fn = getattr(self._scanner, "lasers_armed", None)
        try:
            return bool(fn()) if fn else self._armed
        except Exception:
            return self._armed

    @Slot()
    def cancelCalibration(self):
        self._runner.cancel()
        self._timer.stop()
        self._calib["result"] = "avbruten"
        self._calib["ok"] = False
        self.calibChanged.emit()

    def _tick(self):
        self._runner.tick(_TICK_MS / 1000.0)

    def _on_progress(self, pct: float, msg: str):
        c = self._calib
        if msg != c["msg"]:
            c["log"] = c["log"] + [f"✓ {c['msg']}"] if c["msg"] else c["log"]
            c["msg"] = msg
        c["pct"] = pct
        self.calibChanged.emit()

    def _on_finished(self, ok: bool, values: dict):
        self._timer.stop()
        c = self._calib
        if c["msg"]:
            c["log"] = c["log"] + [f"✓ {c['msg']}"]
        c["pct"] = 1.0
        c["msg"] = ""
        c["ok"] = ok
        c["result"] = " · ".join(f"{k}: {v}" for k, v in values.items())
        self.calibChanged.emit()
        self.methodsChanged.emit()
        self.devicesChanged.emit()

    # ------------------------------------------------- körningens egenskaper
    @Property(bool, notify=calibChanged)
    def calibRunning(self):
        return self._runner.running

    @Property(str, notify=calibChanged)
    def calibDevice(self):
        return self._calib["dev"]

    @Property(str, notify=calibChanged)
    def calibTitle(self):
        return self._calib["title"]

    @Property(float, notify=calibChanged)
    def calibPct(self):
        return float(self._calib["pct"])

    @Property(str, notify=calibChanged)
    def calibStep(self):
        return self._calib["msg"]

    @Property("QVariantList", notify=calibChanged)
    def calibLog(self):
        return list(self._calib["log"])

    @Property(str, notify=calibChanged)
    def calibResult(self):
        return self._calib["result"]

    @Property(bool, notify=calibChanged)
    def calibOk(self):
        return bool(self._calib["ok"])
