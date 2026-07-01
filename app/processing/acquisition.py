"""Trådad förvärvspipeline — encoder-triggad radackumulering → färdig bräda.

Detta är REAL-LÄGETS körtidsmotor (regel 2 i docs/jetson-setup.md §4 / Fas C i
jetson-prep-plan): medan brädan matas läser en CAPTURE-tråd råa laserstripe-rader
(röd + grön profilkamera) + en färgrad (linjekameran) per matningsposition och
lägger i en buffrad kö. En PROCESS-konsument kör GPU-stripe-extraktion →
triangulering → fusion per rad och bygger upp höjdkartan. Stegen ÖVERLAPPAR
(kamera ∥ GPU), vilket är det som ger keep-up.

Samma kod kör mot sim- och real-HAL (läser bara via HAL-gränssnitten). Resultatet
är en ``Board`` (board_gen) → ``warp_metrics()``, ``detect_defects`` och
``grade_board`` fungerar oförändrat. Drivs av en positionskälla (sim: stegad
matning; real: RoboClaw-position / fotocell).
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from ..geometry import RIG
from ..hal.sim.board_gen import Board
from .fusion import fuse, anchor
from .segmentation import BoardGate
from .stripe_gpu import StripeExtractor
from .surface import detect_defects
from .triangulate import centroid_to_z


@dataclass
class ScanStats:
    rows: int = 0
    wall_s: float = 0.0
    capture_s: float = 0.0
    process_s: float = 0.0
    max_queue: int = 0
    dropped: int = 0

    @property
    def rows_per_s(self) -> float:
        return self.rows / self.wall_s if self.wall_s else 0.0

    @property
    def overlap(self) -> float:
        """1.0 = perfekt överlapp (wall ≈ max(capture,process)); >1 = seriellt."""
        denom = max(self.capture_s, self.process_s)
        return (self.wall_s / denom) if denom else 0.0


def _resize_canonical(arr: np.ndarray, len_px: int, wid_px: int) -> np.ndarray:
    """Skala (bredd, längd[, 3]) → (wid_px, len_px[, 3]). cv2 om den finns
    (bilinjär), annars en numpy-fallback (nearest) så appen aldrig kraschar på
    en maskin utan OpenCV."""
    try:
        import cv2
        return cv2.resize(arr, (len_px, wid_px), interpolation=cv2.INTER_LINEAR)
    except Exception:
        ys = np.linspace(0, arr.shape[0] - 1, wid_px).astype(int)
        xs = np.linspace(0, arr.shape[1] - 1, len_px).astype(int)
        return arr[np.ix_(ys, xs)] if arr.ndim == 2 else arr[np.ix_(ys, xs, np.arange(arr.shape[2]))]


def _surface_line(scanner, y_mm: float, width_mm: float, cols: int) -> np.ndarray:
    """En färgrad (RGB, cols) från linjekameran. Ytkameran sitter +40 mm nedströms
    (RIG.surface_cam_lead_mm) men encoder-leadet registrerar varje färgrad mot
    SAMMA brädrad som höjden → vi samplar brädrad ``y_mm`` (sim: positions-medveten
    grab_line; real: kamerans aktuella encoder-triggade rad)."""
    cam = scanner.surface
    grab = getattr(cam, "grab_line", None)
    if grab is not None:
        try:
            try:
                line = np.asarray(grab(y_mm))         # positions-medveten (sim)
            except TypeError:
                line = np.asarray(grab())             # aktuell kameralinje (real)
            if line.ndim == 2 and line.shape[1] == 3:
                idx = np.linspace(0, line.shape[0] - 1, cols).astype(int)
                return line[idx].astype(np.uint8)
        except Exception:
            pass
    img = cam.surface_image()
    if img is None or img.size == 0:
        return np.full((cols, 3), 160, np.uint8)
    h, w = img.shape[:2]
    ry = int(np.clip(y_mm / max(1e-6, width_mm) * (h - 1), 0, h - 1))
    xs = np.linspace(0, w - 1, cols).astype(int)
    return img[ry, xs].astype(np.uint8)


class AcquisitionPipeline:
    """Producent (capture) ∥ konsument (GPU-process) → assemblerad Board."""

    def __init__(self, scanner, cols: int = 200, queue_size: int = 8,
                 lr_positions=None):
        self.scanner = scanner
        self.cols = cols
        self._q: queue.Queue = queue.Queue(maxsize=queue_size)
        self._extractor = StripeExtractor()
        self._extractor.warmup(cols=cols)
        self._lr_pos = list(lr_positions or [])

    # ---------------------------------------------------------------- capture
    def _capture(self, n_rows: int, width_mm: float, stats: ScanStats, stop: threading.Event):
        t0 = time.perf_counter()
        for i in range(n_rows):
            if stop.is_set():
                break
            y = (i / max(1, n_rows - 1)) * width_mm
            red = self.scanner.profile_red.read_stripe(y, self.cols)
            green = self.scanner.profile_green.read_stripe(y, self.cols)
            line = _surface_line(self.scanner, y, width_mm, self.cols)
            try:
                self._q.put((i, y, red, green, line), timeout=1.0)
            except queue.Full:
                stats.dropped += 1
            stats.max_queue = max(stats.max_queue, self._q.qsize())
        stats.capture_s = time.perf_counter() - t0
        self._q.put(None)            # sentinel: klar

    # ---------------------------------------------------------------- process
    def scan_board(self, n_rows: int = 150, width_mm: float | None = None,
                   lr_provider=None):
        """Kör en hel brädskanning. Returnerar (Board, ScanStats).

        ``lr_provider(y)`` → lista abs.tjocklek för ankring (valfritt; utan
        punktlasrar i låst hw lämnas den tom och trianguleringen är absolut).
        """
        width_mm = RIG.board_width_mm if width_mm is None else width_mm
        stats = ScanStats(rows=n_rows)
        stop = threading.Event()
        zrows = [None] * n_rows
        crows = [None] * n_rows

        cap = threading.Thread(target=self._capture, args=(n_rows, width_mm, stats, stop),
                               daemon=True)
        wall0 = time.perf_counter()
        cap.start()
        proc_t = 0.0
        try:
            while True:
                item = self._q.get()
                if item is None:
                    break
                i, y, red, green, line = item
                t0 = time.perf_counter()
                cr = self._extractor.process(red)
                cg = self._extractor.process(green)
                z = fuse(centroid_to_z(cr), centroid_to_z(cg))
                if lr_provider is not None and self._lr_pos:
                    z = anchor(z, lr_provider(y), self._lr_pos)
                zrows[i] = z
                crows[i] = line
                proc_t += time.perf_counter() - t0
        finally:
            stop.set()
            cap.join(timeout=2.0)
        stats.process_s = proc_t
        stats.wall_s = time.perf_counter() - wall0
        return self._assemble_board(zrows, crows), stats

    # ---------------------------------------------------------------- assemblering
    def _assemble_board(self, zrows, crows) -> Board:
        """Bygg en Board ur ackumulerade höjd-/färgrader (delas av single + ström).

        Raderna kommer i kamerans ordning: en BREDD-linje (cols px ≈ brädans bredd)
        per scannad rad längs LÄNGDEN. Vi normaliserar till board_gen:s konvention
        (axel0 = bredd, axel1 = längd) + brädans bildförhållande (500:75) så att yta,
        3D och preview blir IDENTISKA i pass- och flödesläge."""
        from ..hal.sim.board_gen import PX_PER_MM
        nominal = RIG.board_thick_mm
        zmap = np.array([(r if r is not None else np.full(self.cols, nominal))
                         for r in zrows], dtype=np.float32) - nominal       # (längd, bredd)
        surface = np.array([(c if c is not None else np.full((self.cols, 3), 160, np.uint8))
                            for c in crows], dtype=np.uint8)                  # (längd, bredd, 3)
        # → kanonisk (bredd_px, längd_px): transponera ALLTID (axel0=bredd,
        # axel1=längd) + skala till brädans bildförhållande. Transponeringen får
        # inte hänga på en cv2-import — annars blir flödesläget en roterad fyrkant
        # på maskiner utan OpenCV.
        len_px = max(2, int(RIG.board_len_mm * PX_PER_MM))                    # 1000 för 500 mm
        wid_px = max(2, int(RIG.board_width_mm * PX_PER_MM))                  # 150 för 75 mm
        surface = np.ascontiguousarray(surface.transpose(1, 0, 2))            # (bredd, längd, 3)
        zmap = np.ascontiguousarray(zmap.T)                                   # (bredd, längd)
        if surface.shape[0] >= 2 and surface.shape[1] >= 2:
            surface = _resize_canonical(surface, len_px, wid_px)
            zmap = _resize_canonical(zmap, len_px, wid_px)
        h, w = zmap.shape
        board = Board(seed=-1, w=w, h=h, surface=np.ascontiguousarray(surface),
                      zmap=zmap, defects=detect_defects(surface))
        wm = board.warp_metrics()
        board.warp = (wm["bow"], wm["cup"], wm["twist"])
        return board

    # ---------------------------------------------------------------- löpande flöde
    def _put_stream(self, item, stop: threading.Event) -> bool:
        """Lägg i kön men ge upp om stop sätts (undviker hängning vid full kö)."""
        while not stop.is_set():
            try:
                self._q.put(item, timeout=0.2)
                return True
            except queue.Full:
                continue
        return False

    def _capture_stream(self, gate: BoardGate, stop: threading.Event):
        """Pollar bandposition + närvaro → grind klockar rader → råa rader i kön."""
        cols, width = self.cols, RIG.board_width_mm
        while not stop.is_set():
            pos = self.scanner.feed_position_mm()
            present = self.scanner.board_present()
            for e in gate.update(pos, present):
                if e.kind == "rad":
                    # lokal bräd-y (från framkant) — sim läser rätt bräda; real
                    # griper live så y är bara etikett.
                    red = self.scanner.profile_red.read_stripe(e.local_mm, cols)
                    green = self.scanner.profile_green.read_stripe(e.local_mm, cols)
                    line = _surface_line(self.scanner, e.local_mm, width, cols)
                    if not self._put_stream(("rad", e.local_mm, red, green, line), stop):
                        return
                elif e.kind == "slut":
                    if not self._put_stream(("slut", e.local_mm, None, None, None), stop):
                        return
        self._q.put(None)            # sentinel: stoppad

    def scan_stream(self, gate: BoardGate, stop: threading.Event, lr_provider=None):
        """Löpande flöde: encoder-klockad capture ∥ GPU-process, yieldar Board/bräda.

        Capture-tråden klockar rader via ``gate`` (encoder + närvarogrind); denna
        konsument kör GPU-stripe per rad och färdigställer en Board vid varje
        'slut'-händelse. Avslutas genom att sätta ``stop`` (eller stänga generatorn).
        """
        cap = threading.Thread(target=self._capture_stream, args=(gate, stop), daemon=True)
        cap.start()
        zrows: list = []
        crows: list = []
        try:
            while True:
                item = self._q.get()
                if item is None:                 # sentinel: stoppad
                    break
                kind, y, red, green, line = item
                if kind == "rad":
                    cr = self._extractor.process(red)
                    cg = self._extractor.process(green)
                    z = fuse(centroid_to_z(cr), centroid_to_z(cg))
                    if lr_provider is not None and self._lr_pos:
                        z = anchor(z, lr_provider(y), self._lr_pos)
                    zrows.append(z)
                    crows.append(line)
                elif kind == "slut":
                    if zrows:
                        yield self._assemble_board(zrows, crows)
                    zrows, crows = [], []
        finally:
            stop.set()
            cap.join(timeout=2.0)
