"""AppController — QObject som driver simuleringen och exponerar allt till QML.

Driver en ~60 Hz-timer: matar brädan genom mätzonen, läser sensorerna via HAL,
graderar, och uppdaterar egenskaper som QML binder mot. I M0 körs allt i denna
tråd (simulering är lätt); i Fas 4 flyttas förvärv/behandling till egna trådar.
"""
from __future__ import annotations

import math
import queue
import random
import threading
import time

import numpy as np

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
    meshChanged = Signal()            # ny 3D-rekonstruktion klar (bräda färdigskannad)
    boardDetected = Signal()          # fotocell: bräda laddad (från GPIO-tråd → queued)
    flowBoardReady = Signal()         # löpande flöde: ny bräda klar (från flödestråd → queued)
    repaintTick = Signal()            # throttlad (~20 Hz) → tunga Canvas-vyer ritar om
    camChanged = Signal()             # live kamera-previews uppdaterade (header)

    def __init__(self, cfg: AppConfig, surface_provider, parent=None):
        super().__init__(parent)
        self._cfg = cfg.validate()
        self._s = AppState()
        self._scanner = build_scanner(self._cfg)
        self._surface_provider = surface_provider
        self._surface_rev = 0
        self._lr = [RIG.board_thick_mm] * len(RIG.point_lasers_x_mm)
        self._lr_track = [[] for _ in RIG.point_lasers_x_mm]   # (feed_mm, tjocklek) per laser
        self._zprofile: list = []
        self._grade = None
        self._history: list = []
        self._store = None            # sätts av main (persistens)
        self._zprofile_w: list = []   # tvärprofil Z(y) (bredd)
        self._left_facet: list = []   # mätt tjocklekfasett vänster (röd)
        self._right_facet: list = []  # mätt tjocklekfasett höger (grön)
        self._mesh: dict = {}         # senaste 3D-data (live under skanning, full vid klar)
        self._mesh_t: float = 0.0     # senaste mesh-uppdatering (throttling)
        self._pass_grades: list = []  # grad per pass (multi-pass → kombineras)
        # löpande flöde (scan_stream i egen tråd → brädor via kö till GUI-tråden)
        self._flow_thread: threading.Thread | None = None
        self._flow_stop: threading.Event | None = None
        self._flow_pipe = None
        self._flow_q: queue.Queue = queue.Queue()
        self._tel: dict = {}          # cachad telemetri (byggs ~5 Hz, ej per frame)
        self._tel_t: float = 0.0
        self._paint_t: float = 0.0    # senaste repaintTick (throttle)
        self._meas_t: float = 0.0     # senaste tunga sim-mätning (throttle → avlasta GUI-tråd)
        self._state_t: float = 0.0    # senaste per-tick stateChanged (throttle ~33 Hz)
        self._cam_rev: int = 0        # revision för live kamera-previews (cache-bust)
        self._scanner.conveyor.set_speed(0.0)

        self._timer = QTimer(self)
        self._timer.setInterval(16)   # ~60 Hz
        self._timer.timeout.connect(self._tick)
        self._last_ns = None

        # löpande flöde: bräda klar i flödestråden → konsumera på GUI-tråden (queued)
        self.flowBoardReady.connect(self._drain_flow)
        # verkligt läge: anhåll-fotocellen laddar ny bräda (queued från GPIO-tråd)
        self.boardDetected.connect(self._on_board_detected)
        arm = getattr(self._scanner, "arm_photocell", None)
        if arm is not None:
            try:
                arm(self.boardDetected.emit)
            except Exception as exc:
                print("fotocell-arm:", exc)

    @Slot()
    def _on_board_detected(self):
        """Bräda detekterad vid anhållet → starta ny cykel (om vi väntar)."""
        if self._cfg.run_mode == "flow":
            return                                # flödesläget hanterar brädor själv
        if self._cfg.auto_advance and (not self._s.running or self._s.phase == "reload"):
            self.nextBoard()

    # ---------------------------------------------------------------- livscykel
    def _tick(self):
        now = time.perf_counter()
        if self._last_ns is None:
            self._last_ns = now
        dt = min(0.05, now - self._last_ns)
        self._last_ns = now
        if now - self._paint_t > 0.05:        # ~20 Hz → throttlad omritning av Canvas-vyer
            self._paint_t = now
            self.repaintTick.emit()
        s, cfg = self._s, self._cfg
        BW = RIG.board_width_mm

        if s.running and cfg.run_mode == "flow":
            s.up_ms += dt * 1000
            self._tick_flow(dt)
            s.jetson_load += (s.load_target - s.jetson_load) * min(1.0, dt * 1.5)
            self._emit_state_throttled(now)
            return

        if s.running:
            s.up_ms += dt * 1000
            if s.phase == "scanning":
                s.feed_pos_mm += cfg.feed_mm_s * dt              # framåt-pass
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
                    self._finish_pass()
            elif s.phase == "returning":
                s.feed_pos_mm -= cfg.feed_mm_s * dt              # backa mot anhåll/fotocell
                self._scanner.conveyor.advance(dt)
                if s.feed_pos_mm <= 0:
                    s.feed_pos_mm = 0.0
                    self._home_reached()
            # "reload" = väntar på ny bräda (notis visas); inget rör sig
            cycle = (2 * BW) / max(1.0, cfg.feed_mm_s) + 0.7     # fram + tillbaka per pass
            s.throughput += (60.0 / cycle - s.throughput) * min(1.0, dt * 2)

        s.jetson_load += (s.load_target - s.jetson_load) * min(1.0, dt * 1.5)

        # sensoravläsningar via HAL
        b = self._scanner.board()
        if b is not None and s.phase == "scanning":
            y = min(BW - 1e-3, s.feed_pos_mm)
            # LR400-ankaret sitter UPPSTRÖMS → mäter raden y_lr i förväg (utanför FOV)
            y_lr = min(BW - 1e-3, y + RIG.lr_lead_mm)
            for i, pl in enumerate(self._scanner.point_lasers):
                target = pl.read_mm(y_lr)
                self._lr[i] += (target - self._lr[i]) * min(1.0, dt * 8)
                # spara LR400-spår (absolut tjocklek vid varje matningsrad → massa
                # datapunkter över 75 mm). Glesa till ~0,6 mm-steg, tak 140 punkter.
                tr = self._lr_track[i]
                if not tr or (y - tr[-1][0]) >= 0.6:
                    tr.append([round(y, 1), round(target, 2)])
                    if len(tr) > 140:
                        del tr[0]
            # TUNG mätning throttlad till ~25 Hz (annars blockerar den GUI-tråden 60 ggr/s
            # → upplevd lagg). Graferna märker ingen skillnad.
            if now - self._meas_t > 0.04:
                self._meas_t = now
                # ankaret för AKTUELL profilrad = värdet som fångades när raden passerade
                # LR-planet (sim: brädan är statisk → läs sanna tjockleken vid den raden)
                lr_anchor = [b.thickness_at(x, y) for x in RIG.point_lasers_x_mm]
                # ÄKTA mätning: dubbel-oblik stripe → subpixel → triangulering → fusion → ankring
                z = measure_profile(self._scanner, y, lr_anchor, RIG.point_lasers_x_mm)
                self._zprofile = [round(float(v), 3) for v in z]
                xc = RIG.board_len_mm * 0.5                     # tvärprofil Z(y) vid skannfronten
                self._zprofile_w = [round(float(v), 3) for v in b.z_profile_col(xc)]
                lf, rf = b.cross_facets(xc)                     # mätta sidofasetter (röd/grön)
                self._left_facet = [[round(p[0], 2), round(p[1], 3)] for p in lf]
                self._right_facet = [[round(p[0], 2), round(p[1], 3)] for p in rf]
                self._update_cam_previews(y)                    # live kamera-header
                # live 3D: bygg upp brädan i realtid (throttlat ~12 Hz)
                if now - self._mesh_t > 0.08:
                    self._mesh = self._build_mesh(b, self.scanProgress, full=False)
                    self._mesh_t = now
                    self.meshChanged.emit()
        self._emit_state_throttled(now)

    def _emit_state_throttled(self, now):
        """Per-tick stateChanged throttlad till ~33 Hz → halverar QML-bindnings-
        omräkningarna på Python-huvudtråden (mindre lagg). Händelsestyrda emits
        (knappar, pass-byten) går direkt och påverkas ej."""
        if now - self._state_t > 0.03:
            self._state_t = now
            self.stateChanged.emit()

    @staticmethod
    def _tint(gray, rgb):
        """(rows,cols) gråskala → HxWx3 uint8 i laserfärg (för kamera-preview)."""
        g = np.clip(np.asarray(gray, dtype=np.float32), 0, 255)
        return np.dstack([(g * rgb[0]), (g * rgb[1]), (g * rgb[2])]).astype(np.uint8)

    def _update_cam_previews(self, y):
        """Live kamera-previews → bild-providern (header). Sim: demo-data via
        stripe_preview/surface_image; real: samma väg med riktiga kameraramar."""
        sc = self._scanner
        try:
            sp = getattr(sc.profile_red, "stripe_preview", None)
            if sp is not None:                                  # sim
                gr = sc.profile_red.stripe_preview(y)
                gg = sc.profile_green.stripe_preview(y)
            else:                                               # real (GenICam-ROI)
                gr = sc.profile_red.read_stripe(y)
                gg = sc.profile_green.read_stripe(y)
            self._surface_provider.set_array(self._tint(gr, (1.0, 0.22, 0.24)), "cam_red")
            self._surface_provider.set_array(self._tint(gg, (0.22, 1.0, 0.36)), "cam_green")
        except Exception:
            pass
        try:
            img = sc.surface.surface_image()
            if img is not None and getattr(img, "size", 0):
                # linjekameran BYGGER bilden rad-för-rad i realtid OCH först NÄR brädan
                # når kameran i tvillingen. Brädan glider anhåll→fram; den korsar
                # linjekameran i fönstret ~0.68→0.87 av glidet (ur tvillingens kalibrering
                # anhåll 360, lineCam −339,4). Innan dess: svart (board ej framme än).
                prog = min(1.0, self._s.feed_pos_mm / RIG.board_width_mm)
                fill = max(0.0, min(1.0, (prog - 0.68) / 0.19))
                rows = int(fill * img.shape[0])
                built = np.zeros_like(img)
                if rows > 0:
                    built[:rows] = img[:rows]
                self._surface_provider.set_array(np.ascontiguousarray(built), "cam_line")
        except Exception:
            pass
        self._cam_rev += 1
        self.camChanged.emit()

    @Property(int, notify=camChanged)
    def camRev(self): return self._cam_rev

    def _set_phase(self, p): self._s.phase = p

    def _build_mesh(self, b, progress: float, full: bool) -> dict:
        """3D-höjdrutnät. full=True → hela brädan + skevhet; annars upp till skannfronten."""
        NX, NY = 200, 30                                  # full mesh (~2,5 mm-celler, GPU)
        ny = NY if full else max(2, min(NY, int(round(NY * progress)) or 2))
        row_limit = None if full else max(2, int(round(progress * b.h)))
        grid = b.mesh_grid(NX, ny, row_limit)
        cg = b.color_grid(NX, ny, row_limit)
        mesh = {
            "nx": int(grid.shape[1]), "ny": int(grid.shape[0]),
            "z": [round(float(v), 3) for v in grid.flatten()],
            "rgb": [int(v) for v in cg.reshape(-1)],     # foto-textur (ny·nx·3, radvis)
            "len": RIG.board_len_mm, "width": RIG.board_width_mm,
            "wfrac": 1.0 if full else max(0.02, progress),   # skannad andel (växer från ledande kant)
            "thick": RIG.board_thick_mm,
            "zmin": float(grid.min()), "zmax": float(grid.max()),
            # sågad kant-lutning (mm) — V-kant (RÖD) / H-kant (GRÖN) mäts; ger
            # sidoytorna sin verkliga lutning i 3D (rektangel → fasad sida).
            "bevel": [round(float(b.edge_bevel[0]), 2), round(float(b.edge_bevel[1]), 2)],
        }
        if full and self._grade is not None:
            mesh.update(b.warp_metrics())
            mesh["cls"] = self._grade.cls
            mesh["color"] = self._grade.color
        return mesh

    def _new_board(self):
        self._scanner.new_board()
        b = self._scanner.board()
        if b is not None:                      # sim ger en bräda direkt
            self._surface_provider.set_array(b.surface, "surface")
            self._surface_provider.set_array(b.height_rgb(), "height")
        self._surface_rev += 1
        self._s.phase = "scanning" if b is not None else "idle"
        self._s.feed_pos_mm = 0.0
        self._s.pass_count = 0
        self._s.notify = ""
        self._pass_grades = []
        self._s.detected = []
        self._grade = None
        self._lr_track = [[] for _ in RIG.point_lasers_x_mm]
        self._mesh = {}; self._mesh_t = 0.0
        self.meshChanged.emit()
        self._s.load_target = 58 + 22 * random.random()
        self._scanner.conveyor.set_speed(self._cfg.feed_mm_s)   # framåt
        self.surfaceChanged.emit()
        self.defectsChanged.emit()
        self.stateChanged.emit()

    # -- en framåt-pass klar: gradera passet, börja backa mot fotocellen --
    def _finish_pass(self):
        s = self._s
        s.pass_count += 1
        b = self._scanner.board()
        self._pass_grades.append(grade_board(s.detected, b.warp_metrics() if b else {}))
        self._grade = self._combine_grades()
        # backa till anhåll/home (fotocellen nollar där)
        self._scanner.conveyor.set_speed(-self._cfg.feed_mm_s)
        s.phase = "returning"
        self.stateChanged.emit()

    # -- åter vid fotocellen: nolla; multi → ny pass på samma bräda, annars klar --
    def _home_reached(self):
        s, cfg = self._s, self._cfg
        self._scanner.conveyor.set_speed(0.0)
        conv = self._scanner.conveyor
        if hasattr(conv, "zero"):              # fotocell-home → nollställ encoder/position
            try:
                conv.zero()
            except Exception:
                pass
        more = cfg.pass_mode == "multi" and s.pass_count < cfg.passes_target
        if more:
            # skanna SAMMA bräda igen (multi-pass medel) — nollställ pass-detektion
            b = self._scanner.board()
            if b is not None:
                for d in b.defects:
                    d.pop("_seen", None)
            s.detected = []
            s.feed_pos_mm = 0.0
            s.phase = "scanning"
            self._scanner.conveyor.set_speed(cfg.feed_mm_s)
            self.defectsChanged.emit()
            self.stateChanged.emit()
        else:
            self._finalize_board()

    def _combine_grades(self):
        """Brädans grad ur alla pass: sämsta klassen styr, medelpoäng."""
        gs = self._pass_grades
        if not gs:
            return None
        order = ["A", "B", "C", "D", "V"]
        worst = max(gs, key=lambda g: order.index(g.cls))
        if len(gs) > 1:
            worst.score = round(sum(g.score for g in gs) / len(gs))
            worst.reasons = worst.reasons + [f"{len(gs)} pass (medel)"]
        return worst

    # -- bräda färdig (efter sista passet): logga, mesh, notis "ladda ny" --
    def _finalize_board(self):
        s = self._s
        s.board_count += 1
        b = self._scanner.board()
        self._grade = self._combine_grades() or grade_board(s.detected,
                                                            b.warp_metrics() if b else {})
        s.load_target = 22 + 10 * random.random()
        try:
            n_vision = len(detect_defects(b.surface)) if b else 0
        except Exception:
            n_vision = 0
        entry = {
            "n": s.board_count,
            "cls": self._grade.cls, "title": self._grade.title, "color": self._grade.color,
            "score": self._grade.score, "ndef": len(s.detected), "nvision": n_vision,
            "passes": s.pass_count, "time": time.strftime("%H:%M:%S"),
        }
        self._history.insert(0, entry)
        del self._history[200:]
        if b is not None:
            self._mesh = self._build_mesh(b, 1.0, full=True)
            self.meshChanged.emit()
        if self._store is not None:
            try:
                self._store.log_board(entry, s.detected, b)
            except Exception as exc:           # persistens får aldrig stoppa drift
                print("persistens-fel:", exc)
        # analys klar → notis om att ladda ny bräda; vänta (eller auto vid fotocell)
        s.phase = "reload"
        s.notify = (f"Analys klar — klass {self._grade.cls} ({s.pass_count} pass). "
                    f"Ladda ny bräda mot anhållet.")
        self._scanner.conveyor.set_speed(0.0)
        self.historyChanged.emit()
        self.stateChanged.emit()

    # ============================================================ LÖPANDE FLÖDE
    # Encoder-klockad scan_stream i egen tråd: brädor segmenteras av BoardGate
    # (närvarogrind) och graderas löpande. Samma kod kör mot sim (virtuellt band)
    # och real (RoboClaw-encoder + fotocell). Brädor med godtyckligt mellanrum.
    def _start_flow(self):
        from ..processing.acquisition import AcquisitionPipeline
        from ..processing.segmentation import BoardGate, GateConfig
        s, cfg = self._s, self._cfg
        self._scanner.begin_stream(cfg.gap_mm)                 # sim: virtuellt band
        self._scanner.conveyor.set_speed(cfg.feed_mm_s)        # driver bandet (sim+real)
        self._flow_pipe = AcquisitionPipeline(
            self._scanner, lr_positions=list(RIG.point_lasers_x_mm))
        self._flow_stop = threading.Event()
        gate = BoardGate(GateConfig(
            sensor_offset_mm=cfg.sensor_offset_mm,
            min_board_mm=min(40.0, RIG.board_width_mm * 0.5)))
        s.phase = "flow"; s.notify = ""; s.pass_count = 0
        s.detected = []; self._grade = None
        s.load_target = 64 + 18 * random.random()
        self._flow_thread = threading.Thread(
            target=self._flow_worker, args=(gate,), daemon=True)
        self._flow_thread.start()
        self.defectsChanged.emit()

    def _flow_worker(self, gate):
        """Flödestråd: scan_stream yieldar en Board per bräda → kö + signal till GUI."""
        try:
            for board in self._flow_pipe.scan_stream(gate, self._flow_stop):
                self._flow_q.put(board)
                self.flowBoardReady.emit()                     # queued → _drain_flow
        except Exception as exc:                               # tråden får aldrig krascha appen
            print("flöde-fel:", exc)

    def _stop_flow(self):
        if self._flow_stop is not None:
            self._flow_stop.set()
        if self._flow_thread is not None:
            self._flow_thread.join(timeout=2.0)
        self._flow_thread = None
        try:
            self._scanner.end_stream()                         # släcker ljus i real
        except Exception:
            pass
        self._drain_flow()                                     # ta hand om sista brädan

    def _tick_flow(self, dt):
        """Live-uppdatering i flödesläge: bandposition + genomströmning."""
        s, cfg = self._s, self._cfg
        get_local = getattr(self._scanner, "stream_local_mm", None)
        s.feed_pos_mm = float(get_local()) if get_local else 0.0
        cycle = (RIG.board_width_mm + cfg.gap_mm) / max(1.0, cfg.feed_mm_s)
        s.throughput += (60.0 / max(0.1, cycle) - s.throughput) * min(1.0, dt * 2)
        self._drain_flow()

    @Slot()
    def _drain_flow(self):
        """Konsumera färdiga brädor från flödestråden (körs på GUI-tråden)."""
        while True:
            try:
                board = self._flow_q.get_nowait()
            except queue.Empty:
                break
            self._consume_flow_board(board)

    def _consume_flow_board(self, b):
        """En bräda klar i flödet → gradera, logga, uppdatera yta/3D/historik."""
        s = self._s
        detected = list(getattr(b, "defects", []) or [])
        s.detected = detected
        self._grade = grade_board(detected, b.warp_metrics())
        s.board_count += 1
        s.pass_count = 1
        self._surface_provider.set_array(b.surface, "surface")
        self._surface_provider.set_array(b.height_rgb(), "height")
        self._surface_rev += 1
        self._mesh = self._build_mesh(b, 1.0, full=True)
        entry = {
            "n": s.board_count,
            "cls": self._grade.cls, "title": self._grade.title, "color": self._grade.color,
            "score": self._grade.score, "ndef": len(detected), "nvision": len(detected),
            "passes": 1, "time": time.strftime("%H:%M:%S"),
        }
        self._history.insert(0, entry)
        del self._history[200:]
        if self._store is not None:
            try:
                self._store.log_board(entry, detected, b)
            except Exception as exc:
                print("persistens-fel:", exc)
        self.surfaceChanged.emit()
        self.meshChanged.emit()
        self.defectsChanged.emit()
        self.historyChanged.emit()
        self.stateChanged.emit()

    def _stop_run(self):
        """Stoppa pågående drift (pass eller flöde) snyggt."""
        if self._cfg.run_mode == "flow":
            self._stop_flow()
        self._scanner.conveyor.set_speed(0.0)

    # ----------------------------------------------------------------- slots
    @Slot()
    def toggleRun(self):
        self._s.running = not self._s.running
        if self._s.running:
            if self._cfg.run_mode == "flow":
                self._start_flow()
            elif self._scanner.board() is None or self._s.phase in ("idle", "done", "reload"):
                self._new_board()
            else:
                # återuppta i rätt riktning för aktuell fas
                d = -1.0 if self._s.phase == "returning" else 1.0
                self._scanner.conveyor.set_speed(d * self._cfg.feed_mm_s)
            self._timer.start()
        else:
            self._stop_run()
        self.stateChanged.emit()

    @Slot()
    def start(self):
        if not self._s.running:
            self.toggleRun()

    @Slot()
    def nextBoard(self):
        """Ladda ny bräda (fotocellen i verkligt läge, knappen i sim) → ny cykel."""
        if self._cfg.run_mode == "flow":
            return                                # flödet matar brädor löpande
        self._new_board()
        if not self._s.running:
            self.toggleRun()
        elif not self._timer.isActive():
            self._timer.start()

    @Slot(float)
    def setFeed(self, v):
        self._cfg.feed_mm_s = float(v)
        if self._s.running and self._s.phase in ("scanning", "returning"):
            d = -1.0 if self._s.phase == "returning" else 1.0
            self._scanner.conveyor.set_speed(d * v)
        self.stateChanged.emit()

    @Slot(float)
    def setRate(self, v):
        self._cfg.profile_rate_hz = float(v)
        self.stateChanged.emit()

    @Slot(bool)
    def setAuto(self, v):
        self._cfg.auto_advance = bool(v)
        self.stateChanged.emit()

    @Slot(str)
    def setPassMode(self, m):
        if m in ("single", "multi"):
            self._cfg.pass_mode = m
            self.stateChanged.emit()

    @Slot(str)
    def setRunMode(self, m):
        """Byt driftläge pass↔flöde. Stoppar pågående drift först (rena trådar)."""
        if m not in ("pass", "flow") or m == self._cfg.run_mode:
            return
        if self._s.running:
            self._s.running = False
            self._stop_run()
        self._cfg.run_mode = m
        self._s.phase = "idle"
        self._s.notify = ""
        self._s.feed_pos_mm = 0.0
        self.stateChanged.emit()

    @Slot(int)
    def setPasses(self, n):
        self._cfg.passes_target = max(1, int(n))
        self.stateChanged.emit()

    @Slot()
    def dismissNotify(self):
        self._s.notify = ""
        self.stateChanged.emit()

    # -------------------------------------------------------------- properties
    @Property(bool, notify=stateChanged)
    def running(self): return self._s.running

    @Property(str, notify=stateChanged)
    def statusText(self):
        if not self._s.running:
            return "PAUSAD" if self._s.board_count else "VÄNTAR"
        ph = self._s.phase
        if ph == "flow":
            return "LÖPANDE FLÖDE"
        if ph == "scanning":
            return f"SKANNAR · PASS {self._s.pass_count + 1}" \
                if self._cfg.pass_mode == "multi" else "SKANNAR"
        if ph == "returning":
            return "ÅTERGÅNG → ANHÅLL"
        if ph == "reload":
            return "LADDA NY BRÄDA"
        return "I DRIFT"

    @Property(int, notify=stateChanged)
    def boardCount(self): return self._s.board_count

    @Property(str, notify=stateChanged)
    def passMode(self): return self._cfg.pass_mode

    @Property(str, notify=stateChanged)
    def runMode(self): return self._cfg.run_mode

    @Property(int, notify=stateChanged)
    def passesTarget(self): return self._cfg.passes_target

    @Property(int, notify=stateChanged)
    def passCount(self): return self._s.pass_count

    @Property(str, notify=stateChanged)
    def notifyText(self): return self._s.notify

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

    @Property(bool, notify=stateChanged)
    def scanActive(self):
        """Skannar just nu → lasrar + LED tända (digital tvilling: glöd)."""
        return self._s.running and self._s.phase in ("scanning", "flow")

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

    @Property("QVariantList", notify=stateChanged)
    def lrTrack(self):
        """LR400-spår: per laser en lista [feed_mm, tjocklek] över 75 mm-passagen."""
        return [list(tr) for tr in self._lr_track]

    @Property("QVariantMap", notify=stateChanged)
    def dims(self):
        """Uppmätta brädmått (mm): längd × bredd + tjocklek (medel/min/max) ur höjd-
        kartan + LR400. Längd/bredd ur skann-geometrin, tjocklek ur mätdata."""
        b = self._scanner.board()
        thick = [v for v in self._lr if v]
        if b is not None:
            import numpy as np
            t = RIG.board_thick_mm + b.zmap
            tmean, tmin, tmax = float(t.mean()), float(t.min()), float(t.max())
        else:
            tmean = sum(thick) / len(thick) if thick else RIG.board_thick_mm
            tmin = min(thick) if thick else tmean
            tmax = max(thick) if thick else tmean
        return {"length": round(RIG.board_len_mm, 1), "width": round(RIG.board_width_mm, 1),
                "thick_mean": round(tmean, 2), "thick_min": round(tmin, 2),
                "thick_max": round(tmax, 2),
                "scanned_mm": round(self._s.feed_pos_mm, 1)}

    @Property("QVariantList", constant=True)
    def lrPositions(self): return list(RIG.point_lasers_x_mm)

    @Property("QVariantList", notify=stateChanged)
    def zProfile(self): return self._zprofile

    @Property("QVariantList", notify=stateChanged)
    def zProfileWidth(self): return self._zprofile_w

    @Property("QVariantList", notify=stateChanged)
    def leftFacet(self): return self._left_facet

    @Property("QVariantList", notify=stateChanged)
    def rightFacet(self): return self._right_facet

    @Property("QVariantMap", notify=meshChanged)
    def mesh3d(self): return self._mesh

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

    @Property(str, notify=stateChanged)
    def gradeGoverning(self): return self._grade.governing if self._grade else ""

    @Property("QVariantMap", notify=stateChanged)
    def gradeBreakdown(self): return self._grade.breakdown if self._grade else {}

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
            "lrLead": RIG.lr_lead_mm, "surfLead": RIG.surface_cam_lead_mm,
            "surfMmPx": round(RIG.surface_mm_per_px, 4), "profLatMmPx": round(RIG.profile_lat_mm_per_px, 4),
        }

    # ------------------------------------------------------ sensor-telemetri (live)
    @Property("QVariantMap", notify=stateChanged)
    def telemetry(self):
        # cachad: bygg om högst ~5 Hz i st f per binding-läsning per frame (~25 läsningar
        # × 60 Hz tidigare). Sänker CPU rejält, särskilt på Jetson.
        now = time.perf_counter()
        if self._tel and now - self._tel_t < 0.2:
            return self._tel
        self._tel_t = now
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
        self._tel = {
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
        return self._tel
