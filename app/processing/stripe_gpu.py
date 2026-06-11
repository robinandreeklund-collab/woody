"""GPU-accelererad laserstripe-extraktion (CuPy/CUDA på Jetson, numpy som fallback).

Samma subpixel-centroid-algoritm som ``stripe.py`` men ARRAY-MODUL-AGNOSTISK (``xp``),
så EXAKT samma matematik kör på GPU (CuPy) eller CPU (numpy). På Jetson Orin Nano är
GPU-vägen det som ger keep-up @ 60 fps (se docs/jetson-setup.md §4) — en naiv
Python/CPU-loop räcker inte vid full sensorupplösning.

Backend väljs automatiskt (CuPy om CUDA finns, annars numpy). Tvinga med env
``WOODY_STRIPE_BACKEND=cpu|gpu``. Profilera med ``python tools/profile_stripe.py``.
"""
from __future__ import annotations

import os

import numpy as np

from .stripe import MIN_PEAK, WIN


_XP = None
_XP_NAME = None


def get_xp():
    """Returnerar (array-modul, namn). CuPy om tillgängligt + CUDA-enhet, annars numpy."""
    global _XP, _XP_NAME
    if _XP is not None:
        return _XP, _XP_NAME
    forced = os.environ.get("WOODY_STRIPE_BACKEND", "").lower()
    if forced == "cpu":
        _XP, _XP_NAME = np, "numpy (CPU, tvingad)"
        return _XP, _XP_NAME
    try:
        import cupy as cp                       # noqa
        if cp.cuda.runtime.getDeviceCount() > 0:
            _XP, _XP_NAME = cp, "cupy (GPU/CUDA)"
            return _XP, _XP_NAME
    except Exception:
        pass
    if forced == "gpu":
        raise RuntimeError("WOODY_STRIPE_BACKEND=gpu men CuPy/CUDA saknas")
    _XP, _XP_NAME = np, "numpy (CPU)"
    return _XP, _XP_NAME


def centroid_batch(frames, win: int = WIN, min_peak: float = MIN_PEAK, xp=None):
    """Subpixel-stripe-centroid för en STACK ramar.

    frames: (N, rows, cols) eller (rows, cols). Returnerar (N, cols) resp. (cols,)
    subpixel-radposition per kolumn, NaN där signalen är för svag (ocklusion).
    Beräknas på samma enhet som ``xp`` (GPU om CuPy); kvar som device-array.
    """
    if xp is None:
        xp, _ = get_xp()
    a = xp.asarray(frames, dtype=xp.float32)
    squeeze = (a.ndim == 2)
    if squeeze:
        a = a[None, ...]
    n, rows, cols = a.shape

    bg = xp.median(a, axis=1, keepdims=True)              # (N,1,C) bakgrund per kolumn
    sig = xp.clip(a - bg, 0, None)
    peak = xp.argmax(sig, axis=1)                          # (N,C) toppens rad
    ni = xp.arange(n)[:, None]
    ci = xp.arange(cols)[None, :]
    peak_val = sig[ni, peak, ci]                           # (N,C) toppintensitet

    r = xp.arange(rows, dtype=xp.float32)[None, :, None]   # (1,R,1)
    win_mask = xp.abs(r - peak[:, None, :]) <= win         # (N,R,C)
    w = sig * win_mask
    denom = w.sum(axis=1)                                  # (N,C)
    num = (w * r).sum(axis=1)
    safe = denom > 0
    centroid = num / xp.where(safe, denom, xp.float32(1.0))
    nan = xp.float32(xp.nan)
    centroid = xp.where(safe, centroid, nan)
    centroid = xp.where(peak_val >= min_peak, centroid, nan)
    return centroid[0] if squeeze else centroid


def to_cpu(arr):
    """Hämta hem en device-array till numpy (no-op för numpy)."""
    return arr.get() if hasattr(arr, "get") else np.asarray(arr)


class StripeExtractor:
    """Återanvändbar extraktor som binder backend en gång (med uppvärmning)."""

    def __init__(self, win: int = WIN, min_peak: float = MIN_PEAK):
        self.xp, self.name = get_xp()
        self.win, self.min_peak = win, min_peak

    def warmup(self, rows: int = 256, cols: int = 2448):
        """Kompilera/allokera kernels så första riktiga ramen inte tar straffet."""
        dummy = self.xp.zeros((1, rows, cols), dtype=self.xp.float32)
        centroid_batch(dummy, self.win, self.min_peak, self.xp)
        self.sync()

    def process(self, frame):
        """En ram (rows, cols) → centroid (cols,) som NUMPY (klar för triangulering)."""
        c = centroid_batch(frame, self.win, self.min_peak, self.xp)
        return to_cpu(c)

    def sync(self):
        if hasattr(self.xp, "cuda"):
            self.xp.cuda.runtime.deviceSynchronize()
