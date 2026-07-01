"""Ytdefekt-detektion ur färgbilden (riktig bildbehandling, ej facit).

Enkel men äkta pixelanalys: färg-/intensitetströsklar → binär defektmask per typ
→ grova sammanhängande regioner (flood fill på nedskalat rutnät). Demonstrerar
detektionskedjan; byts mot ML-modell (TensorRT) i Fas 5 men har samma utdata.
"""
from __future__ import annotations

import numpy as np

from ..geometry import RIG


def _label_blobs(mask: np.ndarray, min_px: int):
    """Sammanhängande regioner (4-grann) via iterativ flood fill. Liten bild."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    blobs = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]; seen[sy, sx] = True; px = []
            while stack:
                y, x = stack.pop(); px.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; stack.append((ny, nx))
            if len(px) >= min_px:
                ys = [p[0] for p in px]; xs = [p[1] for p in px]
                blobs.append((np.mean(xs), np.mean(ys), len(px)))
    return blobs


def detect_defects(surface_rgb: np.ndarray, ds: int = 4) -> list:
    """Returnerar lista [{type,x_mm,y_mm,r_mm}] ur en RGB-bild (HxWx3 uint8)."""
    if surface_rgb is None or surface_rgb.size == 0:
        return []
    img = surface_rgb[::ds, ::ds].astype(np.int16)          # nedskala för fart
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    lum = (R + G + B) / 3.0
    mean_lum = float(lum.mean())

    masks = {
        "stain": (B > R + 10) & (B > 55),                   # blåaktigt
        "crack": (lum < mean_lum * 0.34),                   # mycket mörka linjer
        "knot":  (lum < mean_lum * 0.66) & (R >= B),        # mörkt brunt
    }
    out = []
    claimed = np.zeros(img.shape[:2], dtype=bool)           # undvik dubbeltäckning
    for typ, m in masks.items():
        m = m & ~claimed
        for cx, cy, n in _label_blobs(m, min_px=3):
            out.append({"type": typ,
                        "x": round(float(cx * ds / 2.0), 1),
                        "y": round(float(cy * ds / 2.0), 1),
                        "r": round(float(np.sqrt(n / np.pi) * ds / 2.0), 1)})
        claimed |= m
    return out
