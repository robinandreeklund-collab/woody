"""Översätter master-kommandon → DeviceManager-anrop (rent från transporten).

``CommandHandler.handle(msg)`` tar ett parsat begäran-meddelande och returnerar ett
svar-dict. Ingen Qt-socket här → testbart med en DeviceManager i sim-läge.
"""
from __future__ import annotations

from . import head_config
from . import protocol as p

VERSION = "1"


class CommandHandler:
    def __init__(self, devmgr, name: str = "woody-node", controller=None):
        self.devmgr = devmgr
        self.name = name
        self.ctrl = controller                  # AppController (skanning), kan vara None
        self.scanner = getattr(devmgr, "_scanner", None)
        self.position = head_config.load()      # huvudets sektion av brädan

    def scan_state(self) -> dict:
        c = self.ctrl
        if c is None:
            return {"available": False}
        return {
            "available": True,
            "running": c.running, "status": c.statusText, "mode": c.modeText,
            "run_mode": c.runMode, "pass_mode": c.passMode, "feed": c.feedSpeed,
            "rate": c.profileRate, "throughput": c.throughput, "boards": c.boardCount,
            "load": c.jetsonLoad, "progress": c.scanProgress, "pass_count": c.passCount,
            "passes_target": c.passesTarget, "auto": c.autoAdvance, "notify": c.notifyText,
            "grade_class": c.gradeClass, "grade_title": c.gradeTitle,
            "grade_color": c.gradeColor, "grade_reason": c.gradeReason,
            "grade_governing": c.gradeGoverning,
            "defects": list(c.defects), "zprofile": list(c.zProfile),
            "nominal_thick": c.nominalThick, "lr_thickness": list(c.lrThickness),
            "history": list(c.history),
        }

    # ---- nodstatus (för master-översikten) ----
    def _status(self) -> dict:
        dm = self.devmgr
        devs = dm.devices
        connected = sum(1 for d in devs if d.get("connected"))
        calib_done = sum(d.get("calibDone", 0) for d in devs)
        calib_total = sum(d.get("calibTotal", 0) for d in devs)
        return {
            "name": self.name, "mode": dm.mode,
            "devices_total": len(devs), "devices_connected": connected,
            "calib_done": calib_done, "calib_total": calib_total,
            "calib_running": dm.calibRunning, "lasers_armed": self._lasers_armed(),
            "position": dict(self.position),
            "has_conveyor": bool(self.position.get("has_conveyor", True)),
        }

    def _lasers_armed(self) -> bool:
        fn = getattr(self.scanner, "lasers_armed", None)
        try:
            return bool(fn()) if fn else False
        except Exception:
            return False

    def _calib_state(self) -> dict:
        dm = self.devmgr
        return {"running": dm.calibRunning, "device": dm.calibDevice,
                "title": dm.calibTitle, "pct": dm.calibPct, "step": dm.calibStep,
                "log": list(dm.calibLog), "result": dm.calibResult, "ok": dm.calibOk}

    # ---- kommandodispatch ----
    def handle(self, msg: dict) -> dict | None:
        mid = msg.get("id")
        cmd = msg.get("cmd")
        args = msg.get("args") or {}
        try:
            result = self._dispatch(cmd, args)
            return {"id": mid, "ok": True, "result": result}
        except Exception as exc:
            return {"id": mid, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def _dispatch(self, cmd: str, args: dict):
        dm = self.devmgr
        if cmd == p.CMD_HELLO:
            return {"name": self.name, "mode": dm.mode, "version": VERSION}
        if cmd == p.CMD_STATUS:
            return self._status()
        if cmd == p.CMD_DEVICES:
            return list(dm.devices)
        if cmd == p.CMD_METHODS:
            return dm.methodsFor(args["dev"])
        if cmd == p.CMD_START_CALIB:
            return dm.startCalibration(args["dev"], args["method"])
        if cmd == p.CMD_CANCEL_CALIB:
            dm.cancelCalibration(); return True
        if cmd == p.CMD_CALIB_STATE:
            return self._calib_state()
        if cmd == p.CMD_REFRESH:
            dm.refresh(); return True
        if cmd == p.CMD_SCAN:
            c = self.ctrl
            if c is None:
                return {"available": False}
            a, v = args.get("action"), args.get("value")
            if a == "toggle_run": c.toggleRun()
            elif a == "next_board": c.nextBoard()
            elif a == "set_feed": c.setFeed(float(v))
            elif a == "set_run_mode": c.setRunMode(str(v))
            elif a == "set_pass_mode": c.setPassMode(str(v))
            elif a == "set_auto": c.setAuto(bool(v))
            elif a == "set_rate": c.setRate(float(v))
            elif a == "set_passes": c.setPasses(int(v))
            elif a == "dismiss_notify": c.dismissNotify()
            return self.scan_state()
        if cmd == p.CMD_SET_POSITION:
            self.position = head_config.save({
                "label": args.get("label", ""),
                "start_mm": args.get("start_mm", 0.0),
                "end_mm": args.get("end_mm", 0.0)})
            return dict(self.position)
        if cmd == p.CMD_ARM_LASERS:
            fn = getattr(self.scanner, "arm_lasers", None)
            return bool(fn(confirm=bool(args.get("confirm")))) if fn else False
        if cmd == p.CMD_DISARM_LASERS:
            fn = getattr(self.scanner, "disarm_lasers", None)
            if fn:
                fn()
            return True
        raise ValueError(f"okänt kommando: {cmd!r}")
