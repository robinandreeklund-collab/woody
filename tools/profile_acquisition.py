#!/usr/bin/env python3
"""Profilera den trådade förvärvspipelinen mot sim-HAL (UTAN fältmaskinvara).

Visar att CAPTURE (kamera) och PROCESS (GPU-stripe→triangulering) ÖVERLAPPAR och
mäter rader/s + brädor/s + kö-djup. Bekräftar att radackumulering → färdig bräda
fungerar end-to-end och att resultatet graderas korrekt (Fas C-runtime, körbar nu).

    python tools/profile_acquisition.py                 # auto-backend
    python tools/profile_acquisition.py --rows 150 --boards 5
    WOODY_STRIPE_BACKEND=cpu python tools/profile_acquisition.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geometry import RIG                                    # noqa: E402
from app.hal.sim.sim_backends import SimScanner                 # noqa: E402
from app.processing.acquisition import AcquisitionPipeline      # noqa: E402
from app.processing.grade import grade_board                    # noqa: E402
from app.processing.stripe_gpu import get_xp                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150, help="rader (matningssteg) per bräda")
    ap.add_argument("--cols", type=int, default=200, help="sampel längs laserlinjen")
    ap.add_argument("--boards", type=int, default=5)
    args = ap.parse_args()

    _, backend = get_xp()
    print(f"\nFörvärvspipeline — backend: {backend}")
    print(f"{args.boards} brädor × {args.rows} rader × {args.cols} kolumner\n")

    scanner = SimScanner()
    pipe = AcquisitionPipeline(scanner, cols=args.cols)

    tot_rows = 0
    tot_wall = 0.0
    overlaps = []
    t_start = time.perf_counter()
    for n in range(args.boards):
        scanner.new_board()
        board, st = pipe.scan_board(n_rows=args.rows, width_mm=RIG.board_width_mm)
        g = grade_board(board.defects, board.warp_metrics())
        tot_rows += st.rows
        tot_wall += st.wall_s
        overlaps.append(st.overlap)
        print(f"  bräda {n+1}: {st.rows_per_s:6.0f} rader/s | wall {st.wall_s*1000:6.1f} ms "
              f"| cap {st.capture_s*1000:5.1f} + proc {st.process_s*1000:5.1f} ms "
              f"| kömax {st.max_queue} | överlapp {st.overlap:.2f}× "
              f"| grad {g.cls} ({len(board.defects)} def)")

    wall_total = time.perf_counter() - t_start
    rps = tot_rows / tot_wall if tot_wall else 0.0
    # vid 60 mm/s matning och ~0,5 mm/rad ≈ 120 rader/s krävs per bräda (75 mm → ~150 rader)
    boards_per_min = args.boards / wall_total * 60.0
    print(f"\nSnitt: {rps:.0f} rader/s, ~{np.mean(overlaps):.2f}× överlapp "
          f"(1.0 = kamera & GPU helt parallella).")
    print(f"Genomströmning: {boards_per_min:.0f} brädor/min vid denna upplösning/backend.")
    needed = 120.0   # rader/s vid 60 mm/s & 0,5 mm/rad
    if rps >= needed:
        print(f"→ Klarar målet ~{needed:.0f} rader/s (60 mm/s matning). ✓")
    else:
        print(f"→ Under ~{needed:.0f} rader/s — på Jetson-GPU (CuPy) lyfter detta. ⚠")
    print()


if __name__ == "__main__":
    main()
