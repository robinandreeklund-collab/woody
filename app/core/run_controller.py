"""AppController — QObject som driver simuleringen och exponerar allt till QML.

Driver en ~60 Hz-timer: matar brädan genom mätzonen, läser sensorerna via HAL,
graderar, och uppdaterar egenskaper som QML binder mot. I M0 körs allt i denna
tråd (simulering är lätt); i Fas 4 flyttas förvärv/behandling till egna trådar.
"""
from __future__ import annotations

import random
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from ..geometry import RIG
from ..hal.factory import build_scanner
from ..processing.grade import grade_board
from ..hal.sim.board_gen import DEFECT_INFO
from .config import AppConfig
from .state import AppState


class AppController(QObject):
    stateChanged = Signal()           # generell ändring (per frame) → QML rebindar
    surfaceChanged = Signal()         # ny yt-bild tillgänglig (busta image-cache)
    defectsChanged = Signal()         # defektlistan ändrad (ej per frame)

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
            self._zprofile = [round(float(v), 3)
                              for v in self._scanner.profile_red.read_profile(y)]
        self.stateChanged.emit()

    def _set_phase(self, p): self._s.phase = p

    def _new_board(self):
        self._scanner.new_board()
        b = self._scanner.board()
        self._surface_provider.set_array(b.surface)
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
