"""Simulerade HAL-backends — drivna av board_gen, med riktiga databladsvärden.

Implementerar HAL-gränssnitten så GUI/behandling är identiska i sim och real.
"""
from __future__ import annotations

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


class SimSurfaceCamera(SurfaceCameraIF):
    def __init__(self, scanner: "SimScanner"):
        self._scanner = scanner

    def info(self) -> DeviceInfo:
        return DeviceInfo("Ytkamera 4K färg", "Huateng 4096×4 TDI", "GigE Vision", True)

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


class SimScanner(Scanner):
    def __init__(self):
        self._board: Board | None = None
        self._seed = 0
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
