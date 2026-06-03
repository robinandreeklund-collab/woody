"""Hela flödet end-to-end: förvärv -> syntetisk data -> träning -> inferens.

Steg:
  1. Förvärvsspec (radtakt, dataflöde) + de tre förvärvsfigurerna (run_demo).
  2. Tränar segmenteringsnätet på syntetiska brädor (CPU-verifierbart).
  3. Kör inferens på en osedd bräda och jämför facit mot modellens prediktion.

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
from src.config import LineConfig, SegConfig, CLASSES, CLASS_COLORS
from src.metrics import print_table
from src.board import make_board
from src.train import fit
from src.losses import ConfusionMatrix
from src.infer import load_model, predict_board, colorize, find_checkpoint

HELD_OUT_SEED = 12345  # bräda som varken tränings- eller valmängden har sett


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
    print("STEG 3 – Inferens på osedd bräda + jämförelse mot facit")
    print("=" * 64)
    board = make_board(length_mm=cfg.board_length_mm, width_mm=cfg.board_width_mm,
                       mm_per_px=cfg.mm_per_px, seed=HELD_OUT_SEED)
    color, gt = board["color"], board["label"]
    pred = predict_board(model, color, cfg)

    import torch
    cm = ConfusionMatrix(cfg.n_classes)
    cm.update(torch.from_numpy(np.eye(cfg.n_classes)[pred].transpose(2, 0, 1)[None]),
              torch.from_numpy(gt.astype(np.int64))[None])
    miou = cm.mean_iou()
    print(f"Hel-bräda mIoU (osedd): {miou:.3f}  pixel_acc: {cm.pixel_acc():.3f}")

    fig_path = out / "4_segmentation.png"
    fig_segmentation(color, gt, pred, miou, fig_path)
    print(f"Figur skriven: {fig_path}")
    print("\nKlart – hela flödet kört.")


if __name__ == "__main__":
    main()
