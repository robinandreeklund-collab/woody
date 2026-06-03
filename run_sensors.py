"""Demonstrerar de tre kompletterande sensorkanalerna och genererar figurer.

  5_photometric.png – fotometrisk stereo: riktade LED -> relief/sprickor
  6_tracheid.png    – tracheid-effekten: fiberriktning + snedfibrighet
  7_underside.png   – undersida genom springorna mellan kedjorna

Kör:  python run_sensors.py
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

from src.config import SensorRig
from src.board import make_board
from src import photometric as ps
from src import tracheid as tr
from src import underside as us

OUT = Path(__file__).resolve().parent / "outputs"
SEED = 10  # bräda med samtliga defektklasser (kvist, spricka, vankant, märg...)


def _himg(ax, img, cmap=None):
    """Visar en bräda med längden vågrätt (axel 0 = längd)."""
    arr = np.transpose(img, (1, 0, 2)) if img.ndim == 3 else img.T
    ax.imshow(arr, aspect="auto", cmap=cmap)
    ax.set_xticks([]); ax.set_yticks([])


def fig_photometric(board, rig, path):
    images, L, _, _ = ps.capture(board, rig)
    normals, _ = ps.solve(images, L)
    relief = ps.relief_map(normals)
    K = images.shape[0]
    az = np.degrees(np.arctan2(L[:, 1], L[:, 0]))

    # Albedofri emboss: skillnad mellan motsatta LED tar bort färgen och visar
    # ren lutning -> sprickor/kanter framträder som relief, färgdefekter inte.
    emboss = images[0] - images[K // 2]
    lim = np.percentile(np.abs(emboss), 99.5) + 1e-6
    relief_n = np.clip(relief / (np.percentile(relief, 99) + 1e-6), 0, 1)

    rows = [("färg (referens)", board["color"].astype(np.float32) / 255.0, None, None),
            (f"LED {az[0]:.0f}°", images[0], "gray", None),
            (f"LED {az[K//2]:.0f}°", images[K // 2], "gray", None),
            ("emboss\n(albedofri)", emboss, "RdBu", (-lim, lim)),
            ("normaler", ps.normals_to_rgb(normals), None, None),
            ("relief\n(sprickor/kant)", relief_n, "magma", (0, 1))]

    fig, axes = plt.subplots(len(rows), 1, figsize=(9.5, 8.5))
    for ax, (lbl, img, cmap, clim) in zip(axes, rows):
        arr = np.transpose(img, (1, 0, 2)) if img.ndim == 3 else img.T
        im = ax.imshow(arr, aspect="auto", cmap=cmap)
        if clim:
            im.set_clim(*clim)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_ylabel(lbl, rotation=0, ha="right", va="center", fontsize=8)
    fig.suptitle("Fotometrisk stereo – riktade LED lyfter fram grund relief: "
                 "sprickor och vankantkant framträder, färgplatta defekter inte",
                 fontsize=10)
    fig.tight_layout(rect=(0.07, 0, 1, 0.96))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_tracheid(board, rig, path):
    dev = tr.grain_deviation_deg(board)
    ang = board["fiber_angle"]
    H, W = ang.shape

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.0))

    # 1) Färg + fiberriktning (quiver). Display-koord: x=längd(rad), y=bredd(kol)
    _himg(axes[0], board["color"].astype(np.float32) / 255.0)
    step_r, step_c = max(1, H // 36), max(1, W // 10)
    rs, cs = np.arange(0, H, step_r), np.arange(0, W, step_c)
    RR, CC = np.meshgrid(rs, cs, indexing="ij")
    a = ang[RR, CC]
    axes[0].quiver(RR, CC, np.cos(a), np.sin(a), color="cyan", scale=30,
                   width=0.0015, headwidth=3)
    axes[0].set_title("Fiberriktning ur tracheid-spotens orientering "
                      "(böjer av kring kvistar)", fontsize=9)

    # 2) Snedfibrighet (grader) – hållfasthets-/kvistindikator
    im = axes[1].imshow(dev.T, aspect="auto", cmap="inferno")
    axes[1].set_xticks([]); axes[1].set_yticks([])
    axes[1].set_title("Fibervinkelavvikelse (grader) – kvistar och störd fiber lyser",
                      fontsize=9)
    fig.colorbar(im, ax=axes[1], fraction=0.025, pad=0.01, label="grad")

    # 3) Spridningsfläckens form: ren ved (avlång längs fibern) vs kvist (rund)
    axes[2].set_xlim(0, 10); axes[2].set_ylim(0, 3)
    axes[2].set_aspect("equal"); axes[2].set_yticks([])
    base = rig.tracheid_clear_aspect
    for x, asp, lbl in [(2.5, base, "ren ved\n(leds längs fibern)"),
                        (7.5, 1.15, "över kvist\n(isotrop spridning)")]:
        axes[2].add_patch(Ellipse((x, 1.5), width=asp, height=1.0, angle=0,
                                  facecolor="#d23", alpha=0.5, edgecolor="k"))
        axes[2].annotate(lbl, (x, 0.15), ha="center", va="bottom", fontsize=8)
    axes[2].set_title("Tracheid-spotens form (aspekt = längd/bredd)", fontsize=9)

    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_underside(board, rig, path):
    view = us.underside_view(board, rig)
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 4.5))
    _himg(axes[0], view["under_color"].astype(np.float32) / 255.0)
    axes[0].set_title("Undersidan (faktisk yta)", fontsize=9)
    _himg(axes[1], view["visible_color"].astype(np.float32) / 255.0)
    axes[1].set_title(f"Synligt genom springorna – {rig.n_chains} kedjor à "
                      f"{rig.chain_width_mm:.0f} mm skymmer "
                      f"(täckning {view['coverage']*100:.0f} %)", fontsize=9)
    fig.suptitle("Undersidesavbildning: kedjraderna blir blinda band; "
                 "gapen ger randvis täckning", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    rig = SensorRig()
    board = make_board(length_mm=1200.0, width_mm=125.0, mm_per_px=0.5, seed=SEED)

    fig_photometric(board, rig, OUT / "5_photometric.png")
    fig_tracheid(board, rig, OUT / "6_tracheid.png")
    fig_underside(board, rig, OUT / "7_underside.png")
    print(f"Sensorfigurer skrivna till {OUT}/ (5_photometric, 6_tracheid, 7_underside)")


if __name__ == "__main__":
    main()
