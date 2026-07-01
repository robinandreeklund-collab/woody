"""Bygg HAL ur config + läge. Samma program, två backends."""
from __future__ import annotations

from ..core.config import AppConfig
from .base import Scanner


def build_scanner(cfg: AppConfig) -> Scanner:
    if cfg.mode == "sim":
        from .sim.sim_backends import SimScanner
        return SimScanner()
    if cfg.mode == "real":
        from .real.real_backends import RealScanner
        return RealScanner(cfg)
    raise ValueError(f"okänt läge: {cfg.mode!r}")
