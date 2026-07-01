"""Undersidesavbildning genom springorna mellan transportkedjorna.

Brädan vilar på flera parallella kedjor som löper i matningsriktningen. En
kamera under banan ser undersidan – men bara genom springorna mellan kedjorna;
remsorna rakt ovanför en kedja är skymda. Eftersom brädan glider längs kedjorna
hålls samma längdpositioner skymda hela tiden, så undersidan täcks som ränder
(gapen) medan kedjraderna förblir blinda fläckar.

Modellen genererar en egen undersida (egna defekter) och maskerar bort de
längdband som ligger under kedjorna.
"""
from __future__ import annotations

import numpy as np

from .board import make_board
from .config import SensorRig


def chain_occlusion(length_mm: float, mm_per_px: float,
                    rig: SensorRig | None = None) -> np.ndarray:
    """Bool-vektor per längdrad: True = skymd av en kedja."""
    rig = rig or SensorRig()
    H = int(round(length_mm / mm_per_px))
    occ = np.zeros(H, dtype=bool)
    cw = max(1, int(round(rig.chain_width_mm / mm_per_px)))
    centers = np.linspace(0, H, rig.n_chains + 2)[1:-1]
    for ctr in centers:
        lo = max(0, int(ctr - cw / 2))
        hi = min(H, int(ctr + cw / 2))
        occ[lo:hi] = True
    return occ


def underside_view(top_board: dict, rig: SensorRig | None = None) -> dict:
    """Genererar undersidan och maskerar bort kedjornas blinda band.

    Returnerar full undersida, den faktiskt synliga (randiga) bilden, vilka
    rader som är skymda, samt täckningsgraden.
    """
    rig = rig or SensorRig()
    H, W = top_board["label"].shape
    mm = top_board["mm_per_px"]
    length_mm, width_mm = H * mm, W * mm

    seed = int(abs(hash(("under", H, W))) % (2 ** 31)) ^ rig.underside_seed_offset
    under = make_board(length_mm=length_mm, width_mm=width_mm,
                       mm_per_px=mm, seed=seed % (2 ** 31))

    occ = chain_occlusion(length_mm, mm, rig)
    visible_color = under["color"].copy()
    visible_color[occ] = 0           # kedjraderna blir blinda (svarta) band
    visible_label = under["label"].copy()
    visible_label[occ] = 255         # 255 = "ej observerad"

    return {
        "under_color": under["color"],
        "under_label": under["label"],
        "visible_color": visible_color,
        "visible_label": visible_label,
        "occluded_rows": occ,
        "coverage": float((~occ).mean()),
        "mm_per_px": mm,
    }
