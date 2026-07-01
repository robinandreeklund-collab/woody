"""Tracheid-effekten: laserspridning för fiberriktning och hållfasthet.

När en fokuserad laserpunkt träffar barrträ leds ljuset företrädesvis LÄNGS
fibrerna (tracheidcellerna fungerar som ljusledare), så spridningsfläcken blir
en ellips som pekar längs fiberriktningen. Ur ellipsens orientering läses lokal
fiberriktning, och ur dess form fibervinkelns avvikelse. Kring kvistar svänger
fibrerna kraftigt -> stor avvikelse -> både kvistindikering och hållfasthetsmått
(snedfibrighet sänker hållfastheten).

Bygger på fiberfältet board["fiber_angle"] (vinkel mot längdaxeln, rad).
"""
from __future__ import annotations

import numpy as np

from .config import SensorRig


def fiber_angle(board: dict) -> np.ndarray:
    """Lokal fiberriktning (rad), 0 = längs brädans längd."""
    return board["fiber_angle"]


def grain_deviation_deg(board: dict) -> np.ndarray:
    """Fibervinkelavvikelse i grader – hållfasthets-/kvistindikatorn."""
    return np.degrees(np.abs(board["fiber_angle"]))


def scatter_aspect(board: dict, rig: SensorRig | None = None) -> np.ndarray:
    """Spridningsfläckens längd/bredd per pixel.

    Hög i ren ved (ljuset leds längs fibern), nära 1 över kvist/märg där
    ändträet sprider ljuset mer isotropt.
    """
    rig = rig or SensorRig()
    label = board["label"]
    aspect = np.full(label.shape, rig.tracheid_clear_aspect, dtype=np.float64)
    end_grain = np.isin(label, (1, 2, 6))   # levande/död kvist + märg = ändträ
    aspect[end_grain] = 1.15
    return aspect


def sample_ellipses(board: dict, rig: SensorRig | None = None,
                    n_r: int = 12, n_c: int = 6):
    """Glesa provpunkter med (rad, kol, vinkel, aspekt) för visualisering."""
    rig = rig or SensorRig()
    H, W = board["fiber_angle"].shape
    ang = board["fiber_angle"]
    asp = scatter_aspect(board, rig)
    rs = np.linspace(0.04 * H, 0.96 * H, n_r).astype(int)
    cs = np.linspace(0.08 * W, 0.92 * W, n_c).astype(int)
    pts = []
    for r in rs:
        for c in cs:
            pts.append((r, c, float(ang[r, c]), float(asp[r, c])))
    return pts
