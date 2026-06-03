"""Simulerar linjelaser-triangulering över en 3D-brädgeometri.

En linjelaser projicerar en stripe tvärs brädan; en kamera i vinkel (tri_angle)
ser strippen förskjuten i proportion till höjden. Simuleringen speglar verkliga
effekter:
  - höjdupplösning ur kamerans pixel + trianguleringsvinkel (hardware.Rig)
  - ocklusion/skuggning: branta väggar (vankantkant, sprickvägg) döljer strippen
    -> bortfall (precis som riktiga profilsensorer)
  - laserns linjebredd -> utsmetning, plus sensorbrus
Resultatet är en uppmätt höjdkarta med realistiska artefakter vs sann geometri.
"""
from __future__ import annotations

import numpy as np

from .hardware import Rig


def _blur_width(z: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return z
    ker = np.ones(k) / k
    return np.apply_along_axis(lambda m: np.convolve(m, ker, mode="same"), 1, z)


def _fill_rows(z: np.ndarray) -> np.ndarray:
    out = z.copy()
    W = z.shape[1]
    xs = np.arange(W)
    for r in range(z.shape[0]):
        row = out[r]
        m = ~np.isnan(row)
        if m.sum() >= 2:
            out[r] = np.interp(xs, xs[m], row[m])
        elif m.sum() == 1:
            out[r] = float(row[m][0])
        else:
            out[r] = 0.0
    return out


def simulate_triangulation(z_true_mm: np.ndarray, mm_per_px: float,
                           rig: Rig | None = None, seed: int = 0) -> dict:
    """z_true_mm (H=längd, W=bredd) -> uppmätt höjd + giltighetsmask + täckning."""
    rig = rig or Rig()
    rng = np.random.default_rng(seed)
    dz = rig.height_resolution_mm
    tan_a = np.tan(np.radians(rig.tri_angle_deg))

    # laserns linjebredd smetar ut strippen tvärs bredden
    z = _blur_width(z_true_mm, max(1, int(round(rig.laser.line_width_mm / mm_per_px))))

    # branta väggar tvärs bredden kan inte ses (laser/kamera-geometrin)
    dzdx = np.gradient(z, mm_per_px, axis=1)
    invalid = np.abs(dzdx) > tan_a

    # skugga: ett nedåtsteg döljer punkter strax bakom (kamerasidan)
    shadow_px = max(1, int(round(2.0 / mm_per_px)))
    drop = dzdx < -0.7 * tan_a
    for s in range(1, shadow_px):
        invalid[:, s:] |= drop[:, :-s]

    # kvantisering ur trianguleringen + sensorbrus
    z_q = np.round(z / dz) * dz + rng.normal(0, dz * 0.3, z.shape)
    z_meas = z_q.copy()
    z_meas[invalid] = np.nan
    z_filled = _fill_rows(z_meas)
    return {
        "z_meas": z_meas, "z_filled": z_filled, "valid": ~invalid,
        "dz": dz, "coverage": float((~invalid).mean()),
    }


def simulate_array(z_true_mm: np.ndarray, mm_per_px: float,
                   rig: Rig | None = None, seed: int = 0) -> dict:
    """Array av lasrar/kameror längs längden med överlapp + fusion.

    Varje modul läser sitt längdsegment (egen triangulering, bortfall, brus);
    segmenten vägs ihop med en mjuk ramp i överlappet. Returnerar fusionerad
    höjd + per-laser-data (så varje laser kan visas enskilt) + ägar-/täckningskartor.
    """
    rig = rig or Rig()
    H, W = z_true_mm.shape
    segs = rig.segments()
    z_fused = np.zeros((H, W))
    wsum = np.zeros((H, W))
    n_cov = np.zeros(H, int)
    ov_px = max(1, int(round(rig.overlap_mm / mm_per_px)))
    per_laser = []
    for idx, (s, e, c) in enumerate(segs):
        r0, r1 = int(round(s / mm_per_px)), min(H, int(round(e / mm_per_px)))
        if r1 <= r0:
            continue
        res = simulate_triangulation(z_true_mm[r0:r1], mm_per_px, rig, seed + idx)
        zf = res["z_filled"]
        w = np.ones(r1 - r0)
        ramp = np.linspace(0.0, 1.0, min(ov_px, r1 - r0))
        w[:len(ramp)] = np.minimum(w[:len(ramp)], ramp)
        w[-len(ramp):] = np.minimum(w[-len(ramp):], ramp[::-1])
        z_fused[r0:r1] += zf * w[:, None]
        wsum[r0:r1] += w[:, None]
        n_cov[r0:r1] += 1
        per_laser.append({"idx": idx, "r0": r0, "r1": r1, "start_mm": s,
                          "end_mm": e, "coverage": res["coverage"]})
    z_fused = z_fused / np.clip(wsum, 1e-6, None)
    centers = np.array([c for _, _, c in segs]) / mm_per_px
    owner = np.argmin(np.abs(np.arange(H)[:, None] - centers[None, :]), axis=1)
    return {
        "z_fused": z_fused, "segments": segs, "per_laser": per_laser,
        "owner": owner, "n_cov": n_cov, "overlap_rows": n_cov > 1,
        "coverage": float((wsum[:, 0] > 0).mean()), "rig": rig,
    }
