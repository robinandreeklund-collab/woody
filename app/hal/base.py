"""Hårdvaruabstraktion (HAL) — gränssnitt per enhet.

GUI och behandling pratar BARA mot dessa gränssnitt. Sim- och real-backends
implementerar dem, så att samma program kör mot simulering eller fysisk hårdvara
genom att byta backend (config: mode=sim|real).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class DeviceInfo:
    name: str
    model: str
    interface: str
    connected: bool = False


class Device(ABC):
    @abstractmethod
    def info(self) -> DeviceInfo: ...
    def open(self) -> None: ...
    def close(self) -> None: ...


class ProfileCameraIF(Device):
    """Profilkamera (mono + bandpass) — ger laserstripe-profil → höjd via triangulering."""
    @abstractmethod
    def read_profile(self, y_mm: float) -> np.ndarray:
        """Tjocklek längs X (mm) vid matningsposition y_mm."""


class SurfaceCameraIF(Device):
    """Färg-radkamera — ger en bild av hela ytan (uint8 HxWx3)."""
    @abstractmethod
    def surface_image(self) -> np.ndarray: ...


class PointLaserIF(Device):
    """Punktlaser (LR400) — absolut tjocklek i en punkt."""
    @abstractmethod
    def read_mm(self, y_mm: float) -> float: ...


class ConveyorIF(Device):
    """Transportör (Jrk G2) — matning."""
    @abstractmethod
    def set_speed(self, mm_s: float) -> None: ...
    @abstractmethod
    def position_mm(self) -> float: ...


class Scanner(ABC):
    """Hela riggen: matar fram brädor och exponerar sensorerna.

    M0 modellerar livscykeln på rigg-nivå (en bräda i taget genom mätzonen).
    Real-HAL kommer trigga riktiga kameror via encoder/matning.
    """
    profile_red: ProfileCameraIF
    profile_green: ProfileCameraIF
    surface: SurfaceCameraIF
    point_lasers: list  # [PointLaserIF, ...]
    conveyor: ConveyorIF

    @abstractmethod
    def new_board(self) -> None: ...
    @abstractmethod
    def board(self): ...
    @abstractmethod
    def devices(self) -> list: ...

    # -- löpande flöde (encoder-radtrigg + närvarogrind) -------------------
    # Standardimplementationer räcker för sim/profilering. Real-HAL bör
    # överrida ``board_present`` med fotocellen (GPIO pin 7, snabb flank).
    def feed_position_mm(self) -> float:
        """Monoton bandposition (encoder/RoboClaw) — radklockan för linjekameran."""
        return self.conveyor.position_mm()

    def board_present(self) -> bool:
        """Närvaro vid givaren (fotocell). Real-HAL: överrid med GPIO pin 7."""
        return self.board() is not None

    def lr400_heights(self, y_mm: float | None = None) -> list:
        """3× LR400 absolut tjocklek (+ lateral utbredning) vid matningsposition."""
        y = self.feed_position_mm() if y_mm is None else y_mm
        return [pl.read_mm(y) for pl in self.point_lasers]

    # -- löpande flöde: livscykel ----------------------------------------
    # Sim överrider med ett virtuellt band; real tänder/släcker ljus. Default
    # är no-op så profilering/fejk-scanner funkar utan vidare.
    def begin_stream(self, gap_mm: float = 25.0) -> None:
        """Förbered löpande flöde (anropas när drift startar i flödesläge)."""

    def end_stream(self) -> None:
        """Avsluta löpande flöde (städa)."""

    def stream_local_mm(self) -> float:
        """Aktuell bräds lokala position vid linjen (GUI-display, avancerar EJ bandet)."""
        return 0.0
