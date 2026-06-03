"""Kör hela virkesinspektions-simuleringen och genererar figurer.

Tre steg, på CPU mot den syntetiska generatorn (inga nedladdningar):

  1. Skriver ut förvärvstabellen (pixlar tvärs längden, radtakt, dataflöde)
     för prototypsektion och full längd vid olika upplösningar.
  2. Genererar en syntetisk bräda och ritar färgbild + facit-etiketter.
  3. Visar varför line-scan triggas på pulsgivare (encoder) och inte på klocka,
     samt extraherar tjocklek och vankant ur laserhöjdprofilen.

Figurer skrivs till outputs/. Kör med:  python run_demo.py
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")  # rendera till fil utan display (funkar i Codespace/CI)
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from src.config import LineConfig, CLASSES, CLASS_COLORS
from src.board import make_board
from src.acquisition import acquire_encoder, acquire_timetrigger, laser_profile
from src.metrics import print_table

OUT = Path(__file__).resolve().parent / "outputs"
MM_PER_PX = 0.5          # demoupplösning (snabb på CPU)
SEED = 10                # frö som uppvisar samtliga defektklasser + vankant


def _label_rgb(label: np.ndarray) -> np.ndarray:
    """Bygger en RGB-bild av facit-etiketterna via CLASS_COLORS."""
    rgb = np.zeros(label.shape + (3,), float)
    for cid, color in CLASS_COLORS.items():
        rgb[label == cid] = color
    return rgb


def _show_board(ax, img):
    """Visar en brädbild med längden liggande vågrätt (axel 0 = längd)."""
    ax.imshow(np.transpose(img, (1, 0, 2)) if img.ndim == 3 else img.T,
              aspect="auto")
    ax.set_xlabel("längs längden (px)")
    ax.set_ylabel("bredd (px)")


def fig_board_labels(board, path):
    """Figur 1: syntetisk bräda + facit-etiketter på pixelnivå."""
    fig, axes = plt.subplots(2, 1, figsize=(8.8, 4.4))
    _show_board(axes[0], board["color"])
    axes[0].set_title("Syntetisk bräda (färgkamera)")
    _show_board(axes[1], _label_rgb(board["label"]))
    axes[1].set_title("Facit – pixeletiketter")

    handles = [Patch(facecolor=CLASS_COLORS[c], edgecolor="0.3", label=CLASSES[c])
               for c in sorted(CLASSES)]
    fig.legend(handles=handles, loc="lower center",
               ncol=len(CLASSES), fontsize=7, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_encoder_vs_time(board, path):
    """Figur 2: encoder-trigger (måttriktig) vs tids-trigger (distorderad)."""
    cfg = LineConfig()
    v = cfg.sideways_speed_mps
    enc = acquire_encoder(board)
    tt = acquire_timetrigger(board, v_mean_mps=v, dt_s=0.0008, seed=3)

    fig, axes = plt.subplots(2, 1, figsize=(7.7, 9.9))
    _show_board(axes[0], enc)
    axes[0].set_title("Encoder-trigger: en kolumn per fast sträcka → måttriktig")
    _show_board(axes[1], tt)
    axes[1].set_title("Tids-trigger med hastighetsjitter → geometrisk distorsion")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_laser_profile(board, path):
    """Figur 3: tjocklek (höjdkarta) och vankantbredd ur laserprofilen."""
    prof = laser_profile(board)
    height = board["height"]
    mm_per_px = board["mm_per_px"]
    x_mm = np.arange(height.shape[0]) * mm_per_px

    fig, axes = plt.subplots(2, 1, figsize=(9.9, 8.8))
    im = axes[0].imshow(height.T, aspect="auto", cmap="viridis")
    axes[0].set_title(
        f"Laserhöjdkarta – median-tjocklek ≈ {prof['thickness_mm']:.1f} mm")
    axes[0].set_xlabel("längs längden (px)")
    axes[0].set_ylabel("bredd (px)")
    fig.colorbar(im, ax=axes[0], label="höjd över banan (mm)")

    axes[1].plot(x_mm, prof["wane_mm"], color="#a060d0")
    axes[1].fill_between(x_mm, prof["wane_mm"], color="#a060d0", alpha=0.25)
    axes[1].set_title(
        f"Vankantbredd längs längden – max ≈ {prof['wane_max_mm']:.1f} mm")
    axes[1].set_xlabel("position längs längden (mm)")
    axes[1].set_ylabel("vankant (mm)")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    print_table(LineConfig())
    print()

    board = make_board(length_mm=1200.0, width_mm=125.0,
                       mm_per_px=MM_PER_PX, seed=SEED)

    fig_board_labels(board, OUT / "1_board_labels.png")
    fig_encoder_vs_time(board, OUT / "2_encoder_vs_time.png")
    fig_laser_profile(board, OUT / "3_laser_profile.png")
    print(f"Figurer skrivna till {OUT}/")


if __name__ == "__main__":
    main()
