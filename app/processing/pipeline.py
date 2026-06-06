"""Behandlingspipeline: rå sensordata → mätt höjdprofil + defekter + gradering.

Samma kod i sim och verkligt läge (den läser via HAL). Profilmätningen är ÄKTA:
syntetisk laserstripe → subpixel-centroid → triangulering → fusion → ankring.
"""
from __future__ import annotations

import numpy as np

from .stripe import subpixel_centroid
from .triangulate import centroid_to_z
from .fusion import fuse, anchor
from .surface import detect_defects
from ..geometry import RIG


def measure_profile(scanner, y_mm: float, lr_values, lr_positions, n: int = 200) -> np.ndarray:
    """Mät tjocklek längs X vid matningsposition y_mm via dubbel-oblik triangulering."""
    red = scanner.profile_red.read_stripe(y_mm, n)
    green = scanner.profile_green.read_stripe(y_mm, n)
    z_red = centroid_to_z(subpixel_centroid(red))
    z_green = centroid_to_z(subpixel_centroid(green))
    z = fuse(z_red, z_green)
    return anchor(z, list(lr_values), list(lr_positions))


if __name__ == "__main__":   # självtest: återvinner triangulering den sanna höjden?
    from ..hal.sim.sim_backends import SimScanner
    s = SimScanner(); s.new_board(); b = s.board()
    y = RIG.board_width_mm * 0.5
    true = np.array(b.z_profile_row(y, 200))
    meas = measure_profile(s, y, [RIG.board_thick_mm]*3, list(RIG.point_lasers_x_mm))
    err = np.abs(meas - true)
    print(f"triangulering: medel-fel {err.mean()*1000:.0f} µm, max {err.max()*1000:.0f} µm")
    dets = detect_defects(b.surface)
    print(f"ytdetektion: {len(dets)} regioner, facit {len(b.defects)} defekter")
