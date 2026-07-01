"""Hela flödet end-to-end på samma bräda.

Steg:
  1. Förvärvsspec (radtakt, dataflöde) + de tre förvärvsfigurerna (run_demo).
  2. Tränar segmenteringsnätet på syntetiska brädor (CPU-verifierbart).
  3. Segmenterar en osedd full längd-bräda och jämför facit mot prediktionen.
  4. Kapoptimerar utifrån modellens prediktion: var brädan ska sågas för
     maximalt värde (figur 8).

Resultatfigurer hamnar i outputs/. Kör::

    python run_pipeline.py            # full körning (några minuter på CPU)
    python run_pipeline.py --smoke    # minimal rökverifiering
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import run_demo
from src.config import LineConfig, SegConfig, CutConfig, CLASSES, CLASS_COLORS
from src.metrics import print_table
from src.board import make_board
from src.train import fit
from src.losses import ConfusionMatrix
from src.infer import load_model, predict_board, colorize, find_checkpoint
from src.cutting import optimize_cuts, greedy_plan, format_plan, plot_cut_plan

HELD_OUT_SEED = 12345    # bräda som varken tränings- eller valmängden har sett
HELD_OUT_LENGTH_M = 5.4  # full längd så kapoptimeringen har något att arbeta med


def _show(ax, img):
    ax.imshow(np.transpose(img, (1, 0, 2)), aspect="auto")
    ax.set_xlabel("längs längden (px)")
    ax.set_ylabel("bredd (px)")


def fig_segmentation(color, gt, pred, miou, path):
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 6.0))
    _show(axes[0], color.astype(np.float32) / 255.0)
    axes[0].set_title("Indata (färgkamera)")
    _show(axes[1], colorize(gt))
    axes[1].set_title("Facit (syntetiskt ground truth)")
    _show(axes[2], colorize(pred))
    axes[2].set_title(f"Modellprediktion – mIoU {miou:.3f}")

    handles = [Patch(facecolor=CLASS_COLORS[c], edgecolor="0.3", label=CLASSES[c])
               for c in sorted(CLASSES)]
    fig.legend(handles=handles, loc="lower center",
               ncol=len(CLASSES), fontsize=7, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description="Kör hela inspektionsflödet")
    p.add_argument("--smoke", action="store_true", help="minimal snabbkörning")
    p.add_argument("--epochs", type=int, help="override antal epoker")
    p.add_argument("--retrain", action="store_true",
                   help="träna även om checkpoint finns")
    a = p.parse_args()

    cfg = SegConfig.smoke() if a.smoke else SegConfig()
    if a.epochs is not None:
        cfg = replace(cfg, epochs=a.epochs)
    out = Path(cfg.out_dir)
    out.mkdir(exist_ok=True)

    print("=" * 64)
    print("STEG 1 – Förvärvssimulering (line-scan vid tvärmatning)")
    print("=" * 64)
    print_table(LineConfig())
    print()
    run_demo.main()  # 1_board_labels, 2_encoder_vs_time, 3_laser_profile

    print("\n" + "=" * 64)
    print("STEG 2 – Träning av segmenteringsnätet")
    print("=" * 64)
    ckpt = find_checkpoint(cfg)
    if ckpt is not None and not a.retrain:
        print(f"Använder befintlig checkpoint: {ckpt} (--retrain för att träna om)")
        model, cfg = load_model(str(ckpt))
    else:
        model, _, ckpt = fit(cfg)
        model, cfg = load_model(str(ckpt))

    print("\n" + "=" * 64)
    print("STEG 3 – Segmentering av osedd full längd-bräda + jämförelse mot facit")
    print("=" * 64)
    board = make_board(length_mm=HELD_OUT_LENGTH_M * 1000, width_mm=cfg.board_width_mm,
                       mm_per_px=cfg.mm_per_px, seed=HELD_OUT_SEED)
    color, gt = board["color"], board["label"]
    pred = predict_board(model, board, cfg)

    import torch
    cm = ConfusionMatrix(cfg.n_classes)
    cm.update(torch.from_numpy(np.eye(cfg.n_classes)[pred].transpose(2, 0, 1)[None]),
              torch.from_numpy(gt.astype(np.int64))[None])
    miou = cm.mean_iou()
    print(f"Hel-bräda mIoU (osedd): {miou:.3f}  pixel_acc: {cm.pixel_acc():.3f}")
    fig_segmentation(color, gt, pred, miou, out / "4_segmentation.png")
    print(f"Figur skriven: {out / '4_segmentation.png'}")

    print("\n" + "=" * 64)
    print("STEG 4 – Kapoptimering på modellens prediktion")
    print("=" * 64)
    ccfg = CutConfig()
    plan = optimize_cuts(pred, board["mm_per_px"], ccfg)   # kapa efter modellen
    naive = greedy_plan(pred, board["mm_per_px"], ccfg)
    print(format_plan(plan))
    gain = plan["total_value"] - naive["total_value"]
    pct = 100 * gain / naive["total_value"] if naive["total_value"] else 0
    print(f"Naiv (längsta-först): {naive['total_value']:.0f} kr  "
          f"-> optimering ger +{gain:.0f} kr ({pct:+.0f} %)")
    plot_cut_plan(board, pred, plan, naive, "segmenteringsmodell",
                  out / "8_cut_plan.png")
    print(f"Figur skriven: {out / '8_cut_plan.png'}")
    print("\nKlart – hela flödet kört: förvärv -> segmentering -> kapplan.")


if __name__ == "__main__":
    main()
