"""Sammanslagning av de två oblika höjdprofilerna + absolut-ankring med LR400.

RÖD och GRÖN ser samma laserlinje från var sin sida → de fyller varandras
ocklusioner (vankant/skugga). Punktlasrarna (absolut tjocklek) korrigerar
trianguleringens globala offset/tilt.
"""
from __future__ import annotations

import numpy as np

from ..geometry import RIG


def _interp_nan(a: np.ndarray) -> np.ndarray:
    a = a.copy()
    nan = np.isnan(a)
    if nan.all():
        return np.full_like(a, RIG.board_thick_mm)
    idx = np.arange(a.size)
    a[nan] = np.interp(idx[nan], idx[~nan], a[~nan])
    return a


def fuse(z_red: np.ndarray, z_green: np.ndarray) -> np.ndarray:
    """Slå ihop två profiler: medel där båda giltiga, annars den giltiga."""
    zr, zg = np.asarray(z_red, float), np.asarray(z_green, float)
    both = ~np.isnan(zr) & ~np.isnan(zg)
    out = np.where(np.isnan(zr), zg, zr)
    out[both] = 0.5 * (zr[both] + zg[both])
    return _interp_nan(out)


def anchor(z: np.ndarray, lr_values, lr_positions) -> np.ndarray:
    """Korrigera global offset så profilen matchar punktlasrarnas absoluta tjocklek."""
    if not lr_values:
        return z
    n = z.size
    meas = []
    for x_mm, v in zip(lr_positions, lr_values):
        i = int(np.clip(round(x_mm / RIG.board_len_mm * (n - 1)), 0, n - 1))
        meas.append(v - z[i])
    return z + float(np.mean(meas))
