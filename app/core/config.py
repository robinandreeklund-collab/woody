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
    auto_advance: bool = True         # starta skanning automatiskt när bräda detekteras
    pass_mode: str = "single"         # "single" (1 pass → analys + ladda ny) | "multi"
    passes_target: int = 3            # multi: antal pass per bräda (skanna→backa→skanna)
    gap_mm: float = 25.0              # mellanrum mellan brädor
    fullscreen: bool = False          # kiosk-läge på bänken

    def validate(self) -> "AppConfig":
        if self.mode not in ("sim", "real"):
            raise ValueError(f"okänt läge: {self.mode!r} (sim|real)")
        if self.pass_mode not in ("single", "multi"):
            raise ValueError(f"okänt pass-läge: {self.pass_mode!r} (single|multi)")
        self.feed_mm_s = max(1.0, float(self.feed_mm_s))
        self.profile_rate_hz = max(1.0, float(self.profile_rate_hz))
        self.passes_target = max(1, int(self.passes_target))
        return self
