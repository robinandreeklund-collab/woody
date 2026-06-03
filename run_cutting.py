"""Kapoptimering på en hel bräda: var ska den sågas för maximalt värde?

Genererar en full längd-bräda, tar dess kvalitetsprofil (segmenteringens
prediktion om en checkpoint finns, annars facit), kör DP-optimeringen och ritar
kapplanen (figur 8). För hela kedjan tränad -> segmenterad -> kapad i en körning,
se run_pipeline.py.

Kör:  python run_cutting.py [--length-m 5.4] [--seed 7]
"""
import argparse
from pathlib import Path

from src.config import CutConfig, SegConfig
from src.board import make_board
from src.cutting import optimize_cuts, greedy_plan, format_plan, plot_cut_plan
from src.infer import find_checkpoint, load_model, predict_board

OUT = Path(__file__).resolve().parent / "outputs"
MM_PER_PX = 0.5


def quality_map(board):
    """Kvalitetsprofil att kapa efter: modellens prediktion om möjligt, annars facit."""
    ckpt = find_checkpoint(SegConfig())
    if ckpt is not None:
        model, mcfg = load_model(str(ckpt))
        return predict_board(model, board, mcfg), "segmenteringsmodell"
    return board["label"], "facit"


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
    plot_cut_plan(board, label, plan, naive, source, fig_path)
    print(f"Figur skriven: {fig_path}")


if __name__ == "__main__":
    main()
