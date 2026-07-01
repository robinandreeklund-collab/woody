"""Subpixel-extraktion av laserstripen ur en kamera-ROI.

In: 2D-intensitet (rader = höjd/triangulering, kolumner = längs linjen).
Ut: per kolumn, stripens subpixel-radposition (intensitetstyngdpunkt i ett fönster
runt toppen) eller NaN där signalen är för svag (ocklusion/skugga). Fönstret runt
toppen tar bort brus-bias från tomma rader. Samma steg körs på riktiga ramar.
"""
from __future__ import annotations

import numpy as np

MIN_PEAK = 25.0           # toppintensitet (efter bg-avdrag) under detta = ocklusion
WIN = 6                   # ± rader runt toppen för tyngdpunkten


def subpixel_centroid(roi: np.ndarray) -> np.ndarray:
    """roi: (rows, cols) float. Returnerar (cols,) subpixel-rad eller NaN."""
    roi = np.asarray(roi, dtype=np.float64)
    rows, cols = roi.shape
    bg = np.median(roi, axis=0, keepdims=True)
    sig = np.clip(roi - bg, 0, None)
    peak = np.argmax(sig, axis=0)                       # (cols,)
    peak_val = sig[peak, np.arange(cols)]
    r = np.arange(rows)[:, None]
    win_mask = np.abs(r - peak[None, :]) <= WIN         # (rows, cols)
    w = sig * win_mask
    denom = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        centroid = (w * r).sum(axis=0) / denom
    centroid[peak_val < MIN_PEAK] = np.nan
    return centroid
