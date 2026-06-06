"""AppController — QObject som driver simuleringen och exponerar allt till QML.

Driver en ~60 Hz-timer: matar brädan genom mätzonen, läser sensorerna via HAL,
graderar, och uppdaterar egenskaper som QML binder mot. I M0 körs allt i denna
tråd (simulering är lätt); i Fas 4 flyttas förvärv/behandling till egna trådar.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from ..geometry import RIG
from ..hal.factory import build_scanner
from ..processing.grade import grade_board
from ..processing.pipeline import measure_profile
from ..processing.surface import detect_defects
from ..hal.sim.board_gen import DEFECT_INFO
from .config import AppConfig
from .state import AppState


class AppController(QObject):
    stateChanged = Signal()           # generell ändring (per frame) → QML rebindar
    surfaceChanged = Signal()         # ny yt-bild tillgänglig (busta image-cache)
    defectsChanged = Signal()         # defektlistan ändrad (ej per frame)
    historyChanged = Signal()         # ny bräda klar → logg uppdaterad

    def __init__(self, cfg: AppConfig, surface_provider, parent=None):
        super().__init__(parent)
        self._cfg = cfg.validate()
        self._s = AppState()
        self._scanner = build_scanner(self._cfg)
        self._surface_provider = surface_provider
        self._surface_rev = 0
        self._lr = [RIG.board_thick_mm] * len(RIG.point_lasers_x_mm)
        self._zprofile: list = []
        self._grade = None
        self._history: list = []
        self._store = None            # sätts av main (persistens)
        self._scanner.conveyor.set_speed(0.0)

        self._timer = QTimer(self)
        self._timer.setInterval(16)   # ~60 Hz
        self._timer.timeout.connect(self._tick)
        self._last_ns = None

    # ---------------------------------------------------------------- livscykel
    def _tick(self):
        now = time.perf_counter()
        if self._last_ns is None:
            self._last_ns = now
        dt = min(0.05, now - self._last_ns)
        self._last_ns = now
        s, cfg = self._s, self._cfg
        BW = RIG.board_width_mm

        if s.running:
            s.up_ms += dt * 1000
            if s.phase == "scanning":
                s.feed_pos_mm += cfg.feed_mm_s * dt
                self._scanner.conveyor.advance(dt)
                b = self._scanner.board()
                if b:
                    added = False
                    for d in b.defects:
                        if not d.get("_seen") and d["y"] <= s.feed_pos_mm:
                            d["_seen"] = True
                            s.detected.append(d)
                            added = True
                    if added:
                        self.defectsChanged.emit()
                if s.feed_pos_mm >= BW:
                    s.feed_pos_mm = BW
                    self._finish_board()
            elif s.phase == "gap":
                s.gap_t += dt
                if s.gap_t > 0.7:
                    self._new_board() if cfg.auto_advance else self._set_phase("done")
            cycle = (BW + cfg.gap_mm) / max(1.0, cfg.feed_mm_s) + 0.7
            s.throughput += (60.0 / cycle - s.throughput) * min(1.0, dt * 2)

        s.jetson_load += (s.load_target - s.jetson_load) * min(1.0, dt * 1.5)

        # sensoravläsningar via HAL
        if self._scanner.board() and s.phase == "scanning":
            y = min(BW - 1e-3, s.feed_pos_mm)
            for i, pl in enumerate(self._scanner.point_lasers):
                target = pl.read_mm(y)
                self._lr[i] += (target - self._lr[i]) * min(1.0, dt * 8)
            # ÄKTA mätning: dubbel-oblik stripe → subpixel → triangulering → fusion → ankring
            z = measure_profile(self._scanner, y, self._lr, RIG.point_lasers_x_mm)
            self._zprofile = [round(float(v), 3) for v in z]
        self.stateChanged.emit()

    def _set_phase(self, p): self._s.phase = p

    def _new_board(self):
        self._scanner.new_board()
        b = self._scanner.board()
        self._surface_provider.set_array(b.surface, "surface")
        self._surface_provider.set_array(b.height_rgb(), "height")
        self._surface_rev += 1
        self._s.phase = "scanning"
        self._s.feed_pos_mm = 0.0
        self._s.detected = []
        self._grade = None
        self._s.load_target = 58 + 22 * random.random()
        self.surfaceChanged.emit()
        self.defectsChanged.emit()
        self.stateChanged.emit()

    def _finish_board(self):
        s = self._s
        s.phase = "gap" if self._cfg.auto_advance else "done"
        s.gap_t = 0.0
        s.board_count += 1
        b = self._scanner.board()
        self._grade = grade_board(s.detected, b.warp if b else (0, 0, 0))
        s.load_target = 22 + 10 * random.random()
        # ytdetektion ur färgbilden (äkta CV) — för logg/jämförelse mot facit
        try:
            n_vision = len(detect_defects(b.surface)) if b else 0
        except Exception:
            n_vision = 0
        entry = {
            "n": s.board_count,
            "cls": self._grade.cls, "title": self._grade.title, "color": self._grade.color,
            "score": self._grade.score, "ndef": len(s.detected), "nvision": n_vision,
            "time": time.strftime("%H:%M:%S"),
        }
        self._history.insert(0, entry)
        del self._history[200:]
        if self._store is not None:
            try:
                self._store.log_board(entry, s.detected, b)
            except Exception as exc:           # persistens får aldrig stoppa drift
                print("persistens-fel:", exc)
        self.historyChanged.emit()

    # ----------------------------------------------------------------- slots
    @Slot()
    def toggleRun(self):
        self._s.running = not self._s.running
        if self._s.running:
            if self._scanner.board() is None or self._s.phase in ("idle", "done"):
                self._new_board()
            self._scanner.conveyor.set_speed(self._cfg.feed_mm_s)
            self._timer.start()
        else:
            self._scanner.conveyor.set_speed(0.0)
        self.stateChanged.emit()

    @Slot()
    def start(self):
        if not self._s.running:
            self.toggleRun()

    @Slot()
    def nextBoard(self):
        self._new_board()
        if not self._s.running:
            self.toggleRun()
        elif not self._timer.isActive():
            self._timer.start()

    @Slot(float)
    def setFeed(self, v):
        self._cfg.feed_mm_s = float(v)
        if self._s.running:
            self._scanner.conveyor.set_speed(v)
        self.stateChanged.emit()

    @Slot(float)
    def setRate(self, v):
        self._cfg.profile_rate_hz = float(v)
        self.stateChanged.emit()

    @Slot(bool)
    def setAuto(self, v):
        self._cfg.auto_advance = bool(v)
        self.stateChanged.emit()

    # -------------------------------------------------------------- properties
    @Property(bool, notify=stateChanged)
    def running(self): return self._s.running

    @Property(str, notify=stateChanged)
    def statusText(self):
        return "I DRIFT" if self._s.running else ("PAUSAD" if self._s.board_count else "VÄNTAR")

    @Property(int, notify=stateChanged)
    def boardCount(self): return self._s.board_count

    @Property(float, notify=stateChanged)
    def throughput(self): return round(self._s.throughput, 1)

    @Property(float, notify=stateChanged)
    def jetsonLoad(self): return round(self._s.jetson_load)

    @Property(float, notify=stateChanged)
    def feedSpeed(self): return self._cfg.feed_mm_s

    @Property(float, notify=stateChanged)
    def profileRate(self): return self._cfg.profile_rate_hz

    @Property(bool, notify=stateChanged)
    def autoAdvance(self): return self._cfg.auto_advance

    @Property(float, notify=stateChanged)
    def feedPos(self): return round(self._s.feed_pos_mm, 1)

    @Property(float, notify=stateChanged)
    def scanProgress(self):
        return min(1.0, self._s.feed_pos_mm / RIG.board_width_mm)

    @Property(float, constant=True)
    def boardAspect(self): return RIG.board_aspect

    @Property(float, constant=True)
    def boardLen(self): return RIG.board_len_mm

    @Property(float, constant=True)
    def boardWidth(self): return RIG.board_width_mm

    @Property(float, constant=True)
    def boardThick(self): return RIG.board_thick_mm

    @Property(int, notify=surfaceChanged)
    def surfaceRev(self): return self._surface_rev

    @Property("QVariantList", notify=stateChanged)
    def lrThickness(self): return [round(v, 2) for v in self._lr]

    @Property("QVariantList", constant=True)
    def lrPositions(self): return list(RIG.point_lasers_x_mm)

    @Property("QVariantList", notify=stateChanged)
    def zProfile(self): return self._zprofile

    @Property(float, constant=True)
    def nominalThick(self): return RIG.board_thick_mm

    @Property("QVariantList", notify=stateChanged)
    def defects(self):
        out = []
        for d in self._s.detected:
            sv, rgb = DEFECT_INFO[d["type"]]
            out.append({"name": sv, "color": "#%02x%02x%02x" % rgb,
                        "x": round(d["x"]), "y": round(d["y"]),
                        "dia": round(d.get("r", 1) * 2)})
        return out

    @Property(str, notify=stateChanged)
    def gradeClass(self): return self._grade.cls if self._grade else "–"

    @Property(str, notify=stateChanged)
    def gradeTitle(self):
        return self._grade.title if self._grade else ("Skannar…" if self._s.running else "Inväntar bräda")

    @Property(str, notify=stateChanged)
    def gradeColor(self): return self._grade.color if self._grade else "#61768c"

    @Property(str, notify=stateChanged)
    def gradeReason(self): return " · ".join(self._grade.reasons) if self._grade else "—"

    @Property(str, constant=True)
    def modeText(self): return self._cfg.mode.upper()

    @Property("QVariantList", notify=historyChanged)
    def history(self): return self._history

    def set_store(self, store):
        self._store = store

    exportDone = Signal(str)

    @Slot()
    def exportLog(self):
        if self._store is None:
            self.exportDone.emit("ingen loggdatabas aktiv")
            return
        try:
            path = self._store.export_csv()
            self.exportDone.emit("Exporterad: " + str(path))
        except Exception as exc:
            self.exportDone.emit("export-fel: " + str(exc))

    # -------------------------------------------------- riggens geometri (= head-mech.svg)
    @Property("QVariantMap", constant=True)
    def rig(self):
        return {
            "wd": RIG.work_distance_mm,
            "camArm": RIG.cam_arm_deg, "laserArm": RIG.laser_arm_deg,
            "theta": RIG.tri_angle_deg, "oblique": RIG.oblique_deg,
            "camHeight": round(RIG.cam_height_mm), "camOffset": round(RIG.cam_offset_mm),
            "laserHeight": round(RIG.laser_height_mm), "laserOffset": round(RIG.laser_offset_mm),
            "baseline": round(RIG.baseline_mm), "surfWd": RIG.surface_cam_wd_mm,
            "len": RIG.board_len_mm, "width": RIG.board_width_mm, "thick": RIG.board_thick_mm,
            "surfMmPx": round(RIG.surface_mm_per_px, 4), "profLatMmPx": round(RIG.profile_lat_mm_per_px, 4),
        }

    # ------------------------------------------------------ sensor-telemetri (live)
    @Property("QVariantMap", notify=stateChanged)
    def telemetry(self):
        sc = self._s.phase == "scanning"
        rate = self._cfg.profile_rate_hz
        feed = self._cfg.feed_mm_s
        load = self._s.jetson_load
        # profilkameror
        dr_prof = 2448 * 256 * rate / 1e6                 # MB/s (ROI 256 rader)
        zres_um = round(RIG.profile_lat_mm_per_px / math.tan(math.radians(RIG.tri_angle_deg)) * 0.1 * 1000)
        sig = (88 + 4 * math.sin(time.perf_counter())) if sc else 0
        # ytkamera
        mmpx = RIG.surface_mm_per_px
        srate = feed / mmpx if sc else 0
        dr_surf = 4096 * 3 * srate / 1e6
        rows_now = round(self._s.feed_pos_mm / mmpx) if self._scanner.board() else 0
        rows_tot = round(RIG.board_width_mm / mmpx)
        # transportör
        spd = feed if (self._s.running and sc) else 0
        cur = (0.35 + spd * 0.004) if spd else 0.05
        enc = round(self._scanner.conveyor.position_mm())
        # jetson
        ingest = (2 * dr_prof if sc else 0) + dr_surf
        return {
            "profRate": f"{rate:.0f} Hz", "profData": f"{(dr_prof if sc else 0):.0f} MB/s",
            "profZres": f"~{zres_um} µm", "profSig": f"{sig:.0f} %",
            "profExp": f"{(1e6/rate*0.4 if sc else 0):.0f} µs",
            "surfRate": f"{srate:.0f} Hz", "surfData": f"{dr_surf:.1f} MB/s",
            "surfRows": f"{rows_now} / {rows_tot}", "surfMmPx": f"{mmpx:.3f} mm/px",
            "surfCap": f"{srate/8000*100:.1f} %",
            "convSpeed": f"{spd:.0f} mm/s", "convCurrent": f"{cur:.2f} A",
            "convEnc": f"{enc} mm", "convPwm": f"{(round(spd/120*78+12) if spd else 0)} %",
            "jetCpu": f"{22 + load*0.45:.0f} %", "jetGpu": f"{load:.0f} %",
            "jetRam": f"{38 + load*0.12:.0f} %", "jetIngest": f"{ingest:.0f} MB/s",
            "jetPwr": f"{7 + load*0.16:.1f} W", "jetTemp": f"{45 + load*0.18:.0f} °C",
        }
