"""Simulerade HAL-backends — drivna av board_gen, med riktiga databladsvärden.

Implementerar HAL-gränssnitten så GUI/behandling är identiska i sim och real.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from ..base import (ConveyorIF, DeviceInfo, PointLaserIF, ProfileCameraIF,
                    Scanner, SurfaceCameraIF)
from ...geometry import RIG
from .board_gen import Board, make_board


class SimProfileCamera(ProfileCameraIF):
    def __init__(self, color: str, scanner: "SimScanner"):
        self._color = color           # "red" | "green"
        self._scanner = scanner

    def info(self) -> DeviceInfo:
        nm = "RÖD 650" if self._color == "red" else "GRÖN 520"
        return DeviceInfo(f"Profilkamera {nm}", "Hikrobot MV-CS050-10UM", "USB3 Vision", True)

    def read_profile(self, y_mm: float) -> np.ndarray:
        b = self._scanner.board()
        return b.z_profile_row(y_mm) if b else np.full(200, RIG.board_thick_mm)

    def read_stripe(self, y_mm: float, n: int = 200) -> np.ndarray:
        """Syntetisk laserstripe-ROI (rows×n) som riktig profilkamera skulle ge:
        ljus stripe vars radposition kodar höjden, med ocklusion på fel kant."""
        from ...processing.triangulate import STRIPE_ROWS, z_to_row
        b = self._scanner.board()
        z = b.z_profile_row(y_mm, n) if b else np.full(n, RIG.board_thick_mm)
        stripe = z_to_row(z)                                   # (n,)
        rr = np.arange(STRIPE_ROWS)[:, None]
        img = np.exp(-((rr - stripe[None, :]) ** 2) / (2 * 1.6 ** 2)) * 220.0
        fx = np.linspace(0, 1, n)
        occ = fx if self._color == "red" else (1 - fx)        # motsatt kant skuggas
        shadow = (occ > 0.9) & (z < RIG.board_thick_mm - 2)
        img[:, shadow] *= 0.04
        img += np.random.normal(0, 1.5, img.shape)        # realistiskt SNR → ~0,1 mm
        return np.clip(img, 0, 255)

    def stripe_preview(self, pos_mm: float, cols: int = 260, rows: int = 120) -> np.ndarray:
        """Profilkamerans FAKTISKA bild (live, påverkar EJ mätningen): laserstripen
        LÄNGS brädan (500 mm), höjd-kodad. Kameran ser BARA stripen där lasern
        träffar en yta — ALDRIG lasern i luften. Brädan cross-matas i bredd (75 mm)
        → de två långsidorna (V-kant/H-kant) passerar lasern vid matningens ÄNDLÄGEN,
        EN i taget: RÖD ser sin kant vid ena änden, GRÖN vid andra. Mitt på brädan
        ser båda bara ovansidan. read_stripe (smal mät-ROI) är orörd."""
        b = self._scanner.board()
        BW, BT = RIG.board_width_mm, RIG.board_thick_mm
        # ovansidans höjdprofil LÄNGS brädan vid matningsraden pos_mm
        z = np.asarray(b.z_profile_row(pos_mm, cols), float) if b is not None \
            else np.full(cols, BT)
        base = rows * 0.30                                     # ovansidans nominella rad
        gain = (rows * 0.42) / max(BT, 1.0)                   # px/mm höjd (förstärkt)
        top = base - (z - BT) * gain                          # stripen vandrar med höjden
        under = base + BT * gain                              # bandnivå (undersidan)
        rr = np.arange(rows)[:, None]
        img = np.exp(-((rr - top[None, :]) ** 2) / (2 * 1.7 ** 2)) * 232.0   # OVANSIDAN

        # Ser DETTA huvud sin kant just nu? (en kant i taget vid matningens ändläge)
        near_left = (self._color == "red")
        ez = 9.0                                              # kant-zon (mm)
        prox = (max(0.0, (ez - pos_mm) / ez) if near_left
                else max(0.0, (ez - (BW - pos_mm)) / ez))     # 0..1, 1 = kanten vid lasern
        if prox > 0.02:
            # SIDOYTAN syns: stripen faller NED längs hela längden mot bandet
            face = np.exp(-((rr - under) ** 2) / (2 * 1.5 ** 2)) * (150.0 * prox)  # underkant
            band = ((rr >= top[None, :]) & (rr <= under)).astype(float) * (70.0 * prox)  # fasaden
            img = np.maximum(img, band)
            img += np.broadcast_to(face, (rows, cols))

        img += np.random.normal(0, 2.0, img.shape)
        return np.clip(img, 0, 255)


class SimSurfaceCamera(SurfaceCameraIF):
    """Line-scan färgkamera (Huateng 4K). RAKT NED → avbildar längden 1:1 (ingen
    oblik förvrängning som profilkamerorna). Hänger på EGEN rad +40 mm nedströms
    laserlinjen (RIG.surface_cam_lead_mm) så laserplanet ligger UTANFÖR FOV →
    INGEN laser i färgbilden. Encoder-triggad: en färgrad per matningssteg;
    registreras mot höjdkartan via encoder-leadet → färg ↔ höjd hamnar i linje."""

    def __init__(self, scanner: "SimScanner"):
        self._scanner = scanner

    def info(self) -> DeviceInfo:
        return DeviceInfo("Ytkamera 4K färg", "Huateng 4096×6 TDI", "GigE Vision", True)

    def grab_line(self, pos_mm: float = 0.0) -> np.ndarray:
        """En encoder-triggad färgrad (RGB längs LÄNGDEN) vid matningsposition
        ``pos_mm`` — rakt ned, 1:1, ingen laser. Registrerad till brädans rad."""
        b = self._scanner.board()
        if b is None:
            return np.full((RIG.surface_px, 3), 160, np.uint8)
        from .board_gen import PX_PER_MM
        ry = int(np.clip(pos_mm * PX_PER_MM, 0, b.h - 1))
        xs = np.linspace(0, b.w - 1, RIG.surface_px).astype(int)
        return b.surface[ry, xs].astype(np.uint8)

    def surface_image(self) -> np.ndarray:
        b = self._scanner.board()
        if b is None:
            return np.zeros((10, 67, 3), np.uint8)
        return b.surface


class SimPointLaser(PointLaserIF):
    def __init__(self, idx: int, x_mm: float, scanner: "SimScanner"):
        self._idx, self._x, self._scanner = idx, x_mm, scanner

    def info(self) -> DeviceInfo:
        return DeviceInfo(f"Punktlaser LR-{['V', 'C', 'H'][self._idx]}",
                          "LR400", f"RS-485 ch{self._idx + 1}", True)

    def read_mm(self, y_mm: float) -> float:
        b = self._scanner.board()
        base = b.thickness_at(self._x, y_mm) if b else RIG.board_thick_mm
        return base + float(np.random.normal(0, 0.01))      # 8 µm-brus


class SimConveyor(ConveyorIF):
    def __init__(self):
        self._speed = 0.0
        self._pos = 0.0

    def info(self) -> DeviceInfo:
        return DeviceInfo("Transportör", "24 V DC · Jrk G2", "USB", True)

    def set_speed(self, mm_s: float) -> None:
        self._speed = float(mm_s)

    def advance(self, dt: float) -> None:
        self._pos += self._speed * dt

    def position_mm(self) -> float:
        return self._pos


class _BeltSim:
    """Virtuellt transportband för löpande flöde i sim.

    Brädor (``board_width_mm`` i matningsled) läggs med ``gap_mm`` mellanrum;
    bandet rör sig i wall-clock-takt efter conveyor-hastigheten. Tjänar grinden:
      * ``advance()``  → monoton bandposition (radklockan) + uppdaterar aktiv Board,
      * ``present()``  → närvaro vid linjen (snapshot från senaste advance),
      * ``local_mm()`` → brädans lokala position (GUI-display, avancerar ej).
    Endast capture-tråden anropar ``advance``; GUI:t läser ``local_mm``/``present``.
    """

    def __init__(self, scanner: "SimScanner", gap_mm: float = 25.0, seed0: int = 1000):
        self._sc = scanner
        self._board_len = float(RIG.board_width_mm)      # matningsled (Y)
        self._gap = max(2.0, float(gap_mm))
        # kapa per-anrop-steget så vi aldrig aliasar förbi en lucka/bräda
        self._step_max = max(0.25, min(2.0, self._gap * 0.4, self._board_len * 0.1))
        self._pos = 0.0
        self._last: float | None = None
        self._seed0 = seed0
        self._cache: dict[int, Board] = {}
        self._present = False
        self._local = 0.0
        self._lock = threading.Lock()

    def _pitch(self) -> float:
        return self._board_len + self._gap

    def _board(self, idx: int) -> Board:
        b = self._cache.get(idx)
        if b is None:
            b = make_board(self._seed0 + idx)
            self._cache[idx] = b
            for k in list(self._cache):                  # behåll bara grannar
                if k < idx - 1:
                    self._cache.pop(k, None)
        return b

    def advance(self) -> float:
        """Avancera bandet (wall-clock × hastighet), uppdatera aktiv bräda + snapshot.

        Steget KAPAS till ``_step_max`` (< halva luckan) så bandet aldrig hoppar
        över en bräda/lucka mellan pollningar — emulerar encoderns rad-tick och
        gör att flödet självreglerar mot processhastigheten (backpressure).
        """
        with self._lock:
            now = time.perf_counter()
            if self._last is None:
                self._last = now
            spd = max(0.0, float(getattr(self._sc.conveyor, "_speed", 0.0)))
            inc = min(spd * (now - self._last), self._step_max)   # anti-aliasing
            self._last = now
            self._pos += inc
            idx = int(self._pos // self._pitch())
            local = self._pos - idx * self._pitch()
            self._present = local < self._board_len
            self._local = min(self._board_len, local)
            if self._present:                            # bräda vid linjen → gör aktiv
                self._sc._board = self._board(idx)
            return self._pos

    def present(self) -> bool:
        return self._present

    def local_mm(self) -> float:
        return self._local


class SimScanner(Scanner):
    def __init__(self):
        self._board: Board | None = None
        self._seed = 0
        self._belt: _BeltSim | None = None
        self.profile_red = SimProfileCamera("red", self)
        self.profile_green = SimProfileCamera("green", self)
        self.surface = SimSurfaceCamera(self)
        self.point_lasers = [SimPointLaser(i, x, self)
                             for i, x in enumerate(RIG.point_lasers_x_mm)]
        self.conveyor = SimConveyor()

    def new_board(self) -> None:
        self._seed += 1
        self._board = make_board(self._seed)

    def board(self) -> Board | None:
        return self._board

    def devices(self) -> list:
        return [self.profile_red, self.profile_green, self.surface,
                *self.point_lasers, self.conveyor]

    # -- löpande flöde (virtuellt band; samma scan_stream-väg som real) --------
    def begin_stream(self, gap_mm: float = 25.0) -> None:
        self._belt = _BeltSim(self, gap_mm)
        self._board = None

    def end_stream(self) -> None:
        self._belt = None

    def feed_position_mm(self) -> float:
        return self._belt.advance() if self._belt else self.conveyor.position_mm()

    def board_present(self) -> bool:
        return self._belt.present() if self._belt else (self._board is not None)

    def stream_local_mm(self) -> float:
        return self._belt.local_mm() if self._belt else 0.0
