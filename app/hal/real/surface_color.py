"""Ytkamerans färgkalibrering — tillämpas i MJUKVARA på den debayrade RGB-bilden.

HT-GELM44C-T2 har ingen ISP (bara Bayer ut), så vitbalans/flat-field/färgmatris kan
INTE ställas på kameran (BalanceRatio ignoreras). De beräknas mot referenser under
jämnt LED-ljus (se ``autocalib``) och appliceras här, i denna ordning:

  1. **Flat-field** (per-kolumn, 4096 px × 3 kanaler): rättar vinjettering, LED-ojämnhet
     OCH färgskugga längs linjen (kanten varmare än mitten) — det som en enda vitbalans
     inte kan, eftersom tonen skiftar över bredden.
  2. **Vitbalans** (per-kanal-gain): neutral referens → R=G=B.
  3. **Färgmatris** (3×3): rättar grön/blå-överhörning (Bayer 2×grön) som per-kanal-gain
     inte klarar — anpassad mot färgtavlans facit-RGB.

Allt är ren numpy (ingen cv2) → testbart utan hårdvara. Sparas som .npz.
"""
from __future__ import annotations

import numpy as np


class SurfaceColorCalib:
    """Håller vitbalans (3,), flat-field (W,3) och färgmatris (3,3). Tomma = identitet."""

    def __init__(self, wb=None, flat=None, ccm=None):
        self.wb = None if wb is None else np.asarray(wb, np.float32).reshape(3)
        self.flat = None if flat is None else np.asarray(flat, np.float32)
        self.ccm = None if ccm is None else np.asarray(ccm, np.float32).reshape(3, 3)

    def is_identity(self) -> bool:
        return self.wb is None and self.flat is None and self.ccm is None

    def apply(self, rgb: np.ndarray) -> np.ndarray:
        """Korrigera en debayrad RGB-bild (H,W,3) uint8 → (H,W,3) uint8.
        Flat-field skalas om bredden skiljer (ROI/annan upplösning)."""
        if self.is_identity() or rgb.ndim != 3 or rgb.shape[2] != 3:
            return rgb
        out = rgb.astype(np.float32)
        if self.flat is not None:
            f = self.flat if self.flat.ndim == 2 else self.flat[:, None]
            if f.shape[1] == 1:
                f = np.repeat(f, 3, axis=1)
            if f.shape[0] != out.shape[1]:                       # bredd-matcha (ROI)
                idx = np.linspace(0, f.shape[0] - 1, out.shape[1]).round().astype(int)
                f = f[idx]
            out *= f[None, :, :]
        if self.wb is not None:
            out *= self.wb[None, None, :]
        if self.ccm is not None:
            out = (out.reshape(-1, 3) @ self.ccm.T).reshape(out.shape)
        return np.clip(out, 0, 255).astype(np.uint8)

    # -- persistens --
    def save(self, path) -> None:
        d = {}
        if self.wb is not None:   d["wb"] = self.wb
        if self.flat is not None: d["flat"] = self.flat
        if self.ccm is not None:  d["ccm"] = self.ccm
        np.savez(str(path), **d)

    @classmethod
    def load(cls, path):
        try:
            z = np.load(str(path))
            return cls(wb=z["wb"] if "wb" in z else None,
                       flat=z["flat"] if "flat" in z else None,
                       ccm=z["ccm"] if "ccm" in z else None)
        except Exception:
            return cls()


# -- anpassnings-funktioner (kalibrering) ---------------------------------------

def fit_white_balance(neutral_rgb: np.ndarray) -> np.ndarray:
    """Per-kanal-gain (3,) så en neutral referens blir R=G=B. Normerad mot grön (=1)."""
    m = np.asarray(neutral_rgb, np.float64).reshape(-1, 3).mean(axis=0)
    m = np.clip(m, 1e-6, None)
    g = m.max() / m                          # höj svagare kanaler till starkaste
    return (g / g[1]).astype(np.float32)     # grön = 1.00


def fit_flat_field(white_frames: np.ndarray) -> np.ndarray:
    """Per-kolumn-gain (W,3) från en JÄMN vit yta. ``white_frames`` = (N,W,3) eller (N,W).
    Mål: varje kolumn/kanal = bildens medel → platt ljus OCH neutral färg över bredden."""
    a = np.asarray(white_frames, np.float64)
    if a.ndim == 2:                          # (N,W) mono → 3 kanaler
        a = np.repeat(a[:, :, None], 3, axis=2)
    prof = a.mean(axis=0)                     # (W,3) medel per kolumn
    target = prof.mean(axis=0)               # (3,) jämn nivå per kanal
    return (target[None, :] / np.clip(prof, 1e-6, None)).astype(np.float32)


def fit_color_matrix(measured_rgb: np.ndarray, facit_rgb: np.ndarray) -> np.ndarray:
    """3×3-färgmatris som minstakvadrat-mappar uppmätt RGB → facit-RGB (färgtavlan).
    ``apply`` gör ``in @ ccm.T`` så att uppmätt fält ≈ facit-fält."""
    M = np.asarray(measured_rgb, np.float64).reshape(-1, 3)
    F = np.asarray(facit_rgb, np.float64).reshape(-1, 3)
    X, *_ = np.linalg.lstsq(M, F, rcond=None)   # F ≈ M @ X
    return X.T.astype(np.float32)               # apply: in @ ccm.T = in @ X ≈ facit
