"""Kapoptimering på en hel bräda: var ska den sågas för maximalt värde?

Genererar en full längd-bräda, tar dess kvalitetsprofil (segmenteringens
prediktion om en checkpoint finns, annars facit), kör DP-optimeringen och ritar
kapplanen: brädan med kapsnitt, varje bits klass/längd/värde samt spill.

Kör:  python run_cutting.py [--length-m 5.4] [--seed 7]
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from src.config import CutConfig, SegConfig
from src.board import make_board
from src.cutting import (optimize_cuts, greedy_plan, defect_fraction_per_row,
                         format_plan, GRADE_COLORS)
from src.infer import find_checkpoint, load_model, predict_board

OUT = Path(__file__).resolve().parent / "outputs"
MM_PER_PX = 0.5


def quality_map(board):
    """Kvalitetsprofil att kapa efter: modellens prediktion om möjligt, annars facit."""
    cfg = SegConfig()
    ckpt = find_checkpoint(cfg)
    if ckpt is not None:
        model, mcfg = load_model(str(ckpt))
        return predict_board(model, board, mcfg), "segmenteringsmodell"
    return board["label"], "facit"


def fig_cut_plan(board, plan, naive, source, path):
    color = board["color"].astype(np.float32) / 255.0
    H, W = board["label"].shape
    dev = defect_fraction_per_row(board["label"])
    x_mm = np.arange(H) * board["mm_per_px"]

    fig, axes = plt.subplots(2, 1, figsize=(11, 5),
                             gridspec_kw={"height_ratios": [2, 1]})

    # Övre: brädan (längden vågrätt) + kapplan
    axes[0].imshow(np.transpose(color, (1, 0, 2)), aspect="auto",
                   extent=(0, H * board["mm_per_px"] / 1000, 0, W))
    for pc in plan["pieces"]:
        x0, x1 = pc["start_mm"] / 1000, pc["end_mm"] / 1000
        axes[0].axvspan(x0, x1, color=GRADE_COLORS[pc["grade"]], alpha=0.32)
        axes[0].axvline(x0, color="k", lw=1.2)
        axes[0].axvline(x1, color="k", lw=1.2)
        axes[0].text((x0 + x1) / 2, W * 0.5,
                     f"{pc['length_m']:.1f} m\nklass {pc['grade']}\n{pc['value']:.0f} kr",
                     ha="center", va="center", fontsize=8, weight="bold")
    axes[0].set_yticks([])
    axes[0].set_xlabel("position längs brädan (m)")
    gain = plan["total_value"] - naive["total_value"]
    axes[0].set_title(f"Kapplan ({source}) – totalt {plan['total_value']:.0f} kr "
                      f"(+{gain:.0f} kr mot naiv längsta-först), "
                      f"utbyte {plan['yield_frac']*100:.0f} %, "
                      f"spill {plan['waste_mm']/1000:.2f} m")

    # Undre: defektandel längs brädan (visar varför kapen ligger där de ligger)
    axes[1].fill_between(x_mm / 1000, dev, color="#c0392b", alpha=0.5)
    for pc in plan["pieces"]:
        axes[1].axvspan(pc["start_mm"] / 1000, pc["end_mm"] / 1000,
                        color=GRADE_COLORS[pc["grade"]], alpha=0.18)
    axes[1].set_xlim(0, H * board["mm_per_px"] / 1000)
    axes[1].set_ylabel("defektandel")
    axes[1].set_xlabel("position längs brädan (m)")
    axes[1].grid(alpha=0.3)

    handles = [Patch(facecolor=GRADE_COLORS[g], edgecolor="0.3", label=f"klass {g}")
               for g in ("A", "B", "C", "reject")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--length-m", type=float, default=5.4)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    OUT.mkdir(exist_ok=True)
    board = make_board(length_mm=a.length_m * 1000, width_mm=125.0,
                       mm_per_px=MM_PER_PX, seed=a.seed)
    label, source = quality_map(board)
    cfg = CutConfig()
    plan = optimize_cuts(label, board["mm_per_px"], cfg)
    naive = greedy_plan(label, board["mm_per_px"], cfg)

    print(format_plan(plan))
    gain = plan["total_value"] - naive["total_value"]
    pct = 100 * gain / naive["total_value"] if naive["total_value"] else 0
    print(f"Naiv (längsta-först): {naive['total_value']:.0f} kr  "
          f"-> optimering ger +{gain:.0f} kr ({pct:+.0f} %)")
    fig_path = OUT / "8_cut_plan.png"
    fig_cut_plan(board, plan, naive, source, fig_path)
    print(f"Figur skriven: {fig_path}")


if __name__ == "__main__":
    main()
