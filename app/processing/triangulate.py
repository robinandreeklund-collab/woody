"""Triangulering: laserstripens pixelposition (kamera) → höjd Z (mm).

Kalibreringsmodell (M2, linjär): Z = Z0 + (rad0 − centroid_px) / gain.
``gain`` [px/mm] sätts av trianguleringsgeometrin (kalibreras i Fas 3 mot en
känd referenstrappa). Här delas konstanterna med sim-stripe-generatorn så att
sim ↔ behandling är självkonsistenta — exakt samma kod körs på riktiga ramar.
"""
from __future__ import annotations

import numpy as np

from ..geometry import RIG

STRIPE_ROWS = 80                      # kamera-ROI höjd (rader) i höjd-/triangulerings-led
STRIPE_GAIN_PX_PER_MM = 2.1           # px per mm i Z (≈ ROI/djupområde)
ROW0 = STRIPE_ROWS / 2.0              # rad som motsvarar nominell tjocklek


def centroid_to_z(centroid_px: np.ndarray) -> np.ndarray:
    """Pixelcentroid (per kolumn) → tjocklek Z [mm]. NaN bevaras (ocklusion)."""
    return RIG.board_thick_mm + (ROW0 - centroid_px) / STRIPE_GAIN_PX_PER_MM


def z_to_row(z_mm: np.ndarray) -> np.ndarray:
    """Invers (för sim-generatorn): tjocklek → stripens radposition."""
    return ROW0 - (np.asarray(z_mm) - RIG.board_thick_mm) * STRIPE_GAIN_PX_PER_MM
