"""Fysikalisk laser-/kamera-array-simulering över en slumpad 3D-bräda.

Räknar ut hela rigg-layouten ur de riktiga produktspecarna (laser- och
kamera-array med överlapp) och simulerar trianguleringen: varje laser läser sitt
längdsegment, segmenten fusioneras. Visar varje laser enskilt.

Kör:  python run_laser.py
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.hardware import Rig
from src.geometry import random_warp, warp_height, warp_summary
from src.board import make_board
from src.laser import simulate_array

OUT = Path(__file__).resolve().parent / "outputs"
MM_PER_PX = 3.0
SEED = 4


def _h(ax, img, **kw):
    ax.imshow(img.T, aspect="auto", **kw)
    ax.set_xlabel("längs brädan (px)")
    ax.set_yticks([])


def main():
    OUT.mkdir(exist_ok=True)
    rig = Rig()
    print("RIGG-LAYOUT (ur riktiga produktspecar):")
    for k, v in rig.summary().items():
        print(f"  {k:24s} {v}")

    rng = np.random.default_rng(SEED)
    p = random_warp(rng)
    board = make_board(length_mm=rig.board_length_mm, width_mm=rig.board_width_mm,
                       mm_per_px=MM_PER_PX, seed=SEED)
    H, W = board["label"].shape
    z_defect = board["height"] - 22.0                       # fina ytdefekter (mm)
    z_true = warp_height(H, W, rig.board_width_mm, p) + z_defect

    res = simulate_array(z_true, MM_PER_PX, rig, seed=SEED)
    print(f"\nDeformation: {warp_summary(p)}")
    print(f"Array: {rig.n_lasers} lasrar + {rig.n_profile_cams} profilkameror, "
          f"segment {rig.seg_len_mm:.0f} mm, överlapp {rig.overlap_mm:.0f} mm, "
          f"täckning {res['coverage']*100:.0f} %")
    print("\nMätpunkter per bräda (cross-feed), vid olika takt:")
    for bpm in (30, 60, 90):
        v = rig.feed_for_takt(bpm)
        mp = rig.measurement_points(v)
        print(f"  {bpm:3d} brädor/min ({v:.2f} m/s): laser "
              f"{mp['laser_length_pts']}×{mp['laser_width_profiles']} "
              f"= {mp['laser_points_per_board']:,} pkt  |  yta "
              f"{mp['surface_px_across']}×{mp['surface_rows']} px")

    # ägar-/överlappskarta (varje laser en färg; överlapp markeras)
    owner_img = np.repeat(res["owner"][:, None], W, axis=1).astype(float)
    ov_img = np.repeat(res["overlap_rows"][:, None], W, axis=1)

    fig, axes = plt.subplots(4, 1, figsize=(11, 7.5))
    _h(axes[0], z_true, cmap="viridis")
    axes[0].set_title(f"Sann 3D-geometri (höjd, mm) – {warp_summary(p)}", fontsize=9)

    _h(axes[1], owner_img, cmap="tab10", vmin=0, vmax=10)
    # markera överlappszoner med streck
    om = res["overlap_rows"]
    edges = np.where(np.diff(om.astype(int)) != 0)[0]
    for x in edges:
        axes[1].axvline(x, color="k", lw=0.6, alpha=0.5)
    axes[1].set_title(f"Laser-/kamera-array: {rig.n_lasers} moduler à "
                      f"{rig.seg_len_mm:.0f} mm (varje färg = en laser, "
                      f"streck = överlapp)", fontsize=9)

    _h(axes[2], res["z_fused"], cmap="viridis")
    axes[2].set_title(f"Fusionerad uppmätt höjd (höjdupplösning "
                      f"≈ {rig.height_resolution_mm:.2f} mm)", fontsize=9)

    # längsprofiler vid mitten OCH kanterna: vrid syns som gap mellan kanterna,
    # böj som gemensam båge (mittlinjen ensam döljer vrid).
    x_mm = np.arange(H) * MM_PER_PX / 1000.0
    axes[3].plot(x_mm, z_true[:, 1], color="#3f86c4", lw=1.0, label="kant A")
    axes[3].plot(x_mm, z_true[:, W // 2], color="#2f9e6e", lw=1.2, label="mitten (böj)")
    axes[3].plot(x_mm, z_true[:, -2], color="#a060d0", lw=1.0, label="kant B")
    axes[3].plot(x_mm, res["z_fused"][:, W // 2], color="#e8542c", lw=0.7,
                 alpha=0.7, label="uppmätt mitt")
    axes[3].set_xlim(0, x_mm[-1])
    axes[3].set_xlabel("position längs brädan (m)")
    axes[3].set_ylabel("höjd (mm)")
    axes[3].legend(fontsize=7, loc="upper right", ncol=2)
    axes[3].grid(alpha=0.3)
    axes[3].set_title("Längsprofiler: kant A / mitten / kant B "
                      "(kanterna isär = vrid, gemensam båge = böj)", fontsize=9)

    fig.suptitle(f"Linjelaser-array ({rig.laser.name}, {rig.laser.fan_angle_deg:.0f}°, "
                 f"{rig.laser_working_distance_mm:.0f} mm håll) + "
                 f"{rig.profile_cam.name} profilkameror", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT / "9_laser_array.png", dpi=100)
    plt.close(fig)
    print(f"\nFigur skriven: {OUT / '9_laser_array.png'}")


if __name__ == "__main__":
    main()
