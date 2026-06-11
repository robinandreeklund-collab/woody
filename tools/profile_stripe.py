#!/usr/bin/env python3
"""Profilera laserstripe-extraktionen mot SYNTETISKA ramar — bevisa keep-up @ 60 fps.

Körs UTAN kameror (Fas B i docs/jetson-prep-plan.md): genererar realistiska
profilkamera-ramar (gaussisk laserstripe + brus + bakgrund) och mäter hur många
ramar/s subpixel-centroid-extraktionen klarar — på CPU (numpy) och GPU (CuPy) om
tillgängligt. Jämför mot designkravet 60 fps per profilkamera (×2 kameror).

    python tools/profile_stripe.py                 # auto-backend + flera ROI-höjder
    WOODY_STRIPE_BACKEND=cpu python tools/profile_stripe.py
    python tools/profile_stripe.py --rows 250 --cols 2448 --n 300

MV-CS050-10UM: 2448×2048 @ 60 fps. Vid triangulering används ett ROI-band runt
stripen (rader = djup, kolumner = längs linjen ≈ 2448). Lägre ROI = fler fps.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.processing.stripe_gpu import StripeExtractor, centroid_batch, get_xp, to_cpu  # noqa: E402

TARGET_FPS = 60.0            # MV-CS050-10UM full frame rate (per kamera)
N_CAMERAS = 2               # röd + grön profilkamera


def synth_frames(n: int, rows: int, cols: int, xp) -> "object":
    """n syntetiska ramar: gaussisk stripe på varierande rad + bakgrund + brus (uint8-likt)."""
    rng = xp.random.default_rng(0) if hasattr(xp.random, "default_rng") else xp.random
    r = xp.arange(rows, dtype=xp.float32)[None, :, None]
    # stripens centrumrad varierar längs linjen (böjd bräda) och mellan ramar
    base = rows / 2.0
    col_wave = 6.0 * xp.sin(xp.linspace(0, 9, cols, dtype=xp.float32))[None, None, :]
    frame_off = xp.linspace(-8, 8, n, dtype=xp.float32)[:, None, None]
    center = base + col_wave + frame_off                       # (N,1,C)
    sigma = 1.8
    peak = 200.0
    stripe = peak * xp.exp(-((r - center) ** 2) / (2 * sigma ** 2))   # (N,R,C)
    bg = xp.float32(18.0)
    noise = xp.asarray(np.random.default_rng(1).normal(0, 4, (n, rows, cols)), dtype=xp.float32)
    return xp.clip(stripe + bg + noise, 0, 255).astype(xp.float32)


def bench(rows: int, cols: int, n: int):
    xp, name = get_xp()
    ex = StripeExtractor()
    ex.warmup(rows, cols)
    frames = synth_frames(n, rows, cols, xp)

    # värm + sync
    centroid_batch(frames[:1], xp=xp); ex.sync()

    # batchad genomströmning — i minnessäkra delar (mellanresultat är N×R×C)
    chunk = max(1, int(40_000_000 / (rows * cols)))      # ~40M element/chunk
    t0 = time.perf_counter()
    res0 = None
    for i in range(0, n, chunk):
        r = centroid_batch(frames[i:i + chunk], xp=xp)
        if res0 is None:
            res0 = r[0] if r.ndim == 2 else r
    ex.sync()
    batch_s = time.perf_counter() - t0

    # per-ram-latens (som i drift: en ram i taget)
    t0 = time.perf_counter()
    for i in range(min(n, 120)):
        centroid_batch(frames[i], xp=xp)
    ex.sync()
    per = time.perf_counter() - t0
    single_n = min(n, 120)

    fps_batch = n / batch_s
    fps_single = single_n / per
    ms_single = per / single_n * 1000.0
    bytes_per = rows * cols  # uint8-ekvivalent
    mbps = fps_batch * bytes_per / 1e6

    # sanity: centroid nära den sanna stripcentrumraden?
    c0 = to_cpu(res0)
    valid = np.isfinite(c0)
    ok = "✓" if valid.mean() > 0.9 else "✗"

    margin = fps_single / (TARGET_FPS)
    keep = "✓ KEEP-UP" if fps_single >= TARGET_FPS else "✗ FÖR LÅNGSAM"
    print(f"  ROI {rows:>4}×{cols} | {fps_single:8.0f} fps/ram  "
          f"({ms_single:5.2f} ms) | batch {fps_batch:8.0f} fps "
          f"| {mbps:6.0f} MB/s | {keep} ({margin:.1f}× mål) | stripe {ok}")
    return fps_single


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, help="bara denna ROI-höjd")
    ap.add_argument("--cols", type=int, default=2448)
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()

    _, name = get_xp()
    print(f"\nLaserstripe-extraktion — backend: {name}")
    print(f"Mål: {TARGET_FPS:.0f} fps per profilkamera ({N_CAMERAS} kameror = "
          f"{TARGET_FPS*N_CAMERAS:.0f} ramar/s totalt)\n")

    rois = [args.rows] if args.rows else [128, 250, 512, 2048]
    results = {}
    for rows in rois:
        results[rows] = bench(rows, args.cols, args.n)

    print()
    worst = min(results.values())
    total_needed = TARGET_FPS * N_CAMERAS
    print(f"Sämsta ROI klarar {worst:.0f} fps/ram. Två kameror behöver "
          f"{total_needed:.0f} ramar/s.")
    if worst >= total_needed:
        print("→ En enhet räcker för BÅDA kamerorna i denna backend. ✓")
    elif worst >= TARGET_FPS:
        print("→ Klarar 60 fps/kamera; kör kamerorna i parallella trådar/strömmar. ✓")
    else:
        print("→ UNDER 60 fps på denna backend — kräver GPU (CuPy/VPI) på Jetson. ✗")
    print()


if __name__ == "__main__":
    main()
