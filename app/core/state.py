"""Körtidstillstånd (ren data). QObject-bryggan i run_controller speglar detta till QML."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppState:
    running: bool = False
    phase: str = "idle"            # idle | scanning | gap
    board_count: int = 0
    feed_pos_mm: float = 0.0       # matningsposition (0..bredd)
    gap_t: float = 0.0
    throughput: float = 0.0        # br/min (glidande)
    jetson_load: float = 0.0
    load_target: float = 0.0
    up_ms: float = 0.0
    detected: list = field(default_factory=list)
