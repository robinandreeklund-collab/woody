"""Programkonfiguration. M0 håller det enkelt (dataclass + ev. YAML senare).

Läget (sim/real) väljer HAL-backend. Resten är driftparametrar som GUI:t kan ändra.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppConfig:
    mode: str = "sim"                 # "sim" | "real"
    feed_mm_s: float = 50.0           # transportörens matningshastighet
    profile_rate_hz: float = 500.0    # profiltakt (profiler/s)
    auto_advance: bool = True         # mata nästa bräda automatiskt
    gap_mm: float = 25.0              # mellanrum mellan brädor
    fullscreen: bool = False          # kiosk-läge på bänken

    def validate(self) -> "AppConfig":
        if self.mode not in ("sim", "real"):
            raise ValueError(f"okänt läge: {self.mode!r} (sim|real)")
        self.feed_mm_s = max(1.0, float(self.feed_mm_s))
        self.profile_rate_hz = max(1.0, float(self.profile_rate_hz))
        return self
