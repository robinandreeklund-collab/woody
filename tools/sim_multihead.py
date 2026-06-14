#!/usr/bin/env python3
"""Visualisera multihuvuds-simuleringen: N läshuvuden över en lång bräda + fusion.

    python tools/sim_multihead.py                 # 6 huvuden, 5400 mm → PNG
    python tools/sim_multihead.py --heads 8 --len 7200 --out demo.png

Visar hur det är TÄNKT att skala från den lilla 500 mm-riggen: flera Jetson-
läshuvuden mäter var sin sektion, delar EN encoder (synk) och fusioneras till en
hel bräda. Renderar brädans toppvy med huvudens täckning + skarvar, tjockleks-
profilerna (sann/naiv/fusion) och hur överlappen kalibrerar bort per-huvud-bias.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec

from app.processing.multihead import simulate

HEAD_CMAP = plt.get_cmap("tab10")


def render(res, out_path: str):
    m = res.metrics
    L, Wmm = res.total_len_mm, res.width_mm
    fig = plt.figure(figsize=(16, 11), dpi=110)
    fig.patch.set_facecolor("#0e1620")
    gs = gridspec.GridSpec(4, 3, height_ratios=[1.1, 1.0, 1.4, 1.2], hspace=0.45, wspace=0.25,
                           left=0.06, right=0.975, top=0.92, bottom=0.06)
    ink, ink2, grid = "#e7eef6", "#9fb2c6", "#27384a"

    fig.suptitle(f"woody · multihuvuds-simulering — {m['n_heads']} läshuvuden över "
                 f"{L:.0f} mm bräda (delad encoder + fusion)",
                 color=ink, fontsize=17, fontweight="bold", y=0.965)

    def style(ax, title):
        ax.set_facecolor("#0b1220")
        ax.set_title(title, color=ink, fontsize=11, fontweight="bold", loc="left")
        ax.tick_params(colors=ink2, labelsize=8)
        for sp in ax.spines.values():
            sp.set_color(grid)

    # --- 1) brädans toppvy + huvudtäckning + skarvar ---
    ax0 = fig.add_subplot(gs[0, :])
    style(ax0, "Brädans yta (toppvy) · varje läshuvud mäter sin sektion · skarvar = överlapp")
    ax0.imshow(res.board.surface, extent=[0, L, 0, Wmm], aspect="auto", origin="lower")
    for hd in res.heads:
        c = HEAD_CMAP(hd.idx % 10)
        ax0.axvspan(hd.start_mm, hd.end_mm, color=c, alpha=0.16)
        ax0.plot([hd.start_mm, hd.end_mm], [Wmm + 4, Wmm + 4], color=c, lw=4,
                 solid_capstyle="butt", clip_on=False)
        ax0.text((hd.start_mm + hd.end_mm) / 2, Wmm + 9,
                 f"{hd.label}\n{hd.bias_mm:+.2f} mm", color=c, ha="center", va="bottom",
                 fontsize=8, fontweight="bold", clip_on=False)
    for s in res.seams:
        ax0.axvspan(s["lo_mm"], s["hi_mm"], color="#ffb33d", alpha=0.25)
    ax0.set_xlim(0, L); ax0.set_ylim(0, Wmm + 22)
    ax0.set_xlabel("längd (mm)", color=ink2, fontsize=9)
    ax0.set_yticks([0, Wmm])

    # --- 2) tjockleksprofiler: sann / naiv / fusion ---
    ax1 = fig.add_subplot(gs[1, :])
    style(ax1, "Tjockleksprofil längs brädan — fusion eliminerar skarvstegen")
    x = res.x_mm
    ax1.plot(x, res.true_profile, color="#34e6b5", lw=2.4, label="sann tjocklek", zorder=3)
    ax1.plot(x, res.naive_profile, color="#ff4d5e", lw=1.0, alpha=0.85,
             label=f"naiv hopfogning (RMS {m['rms_naive_mm']:.3f} mm)")
    ax1.plot(x, res.anchored_profile, color="#27d3e0", lw=1.4, ls="--",
             label=f"FUSION: align + ankra (RMS {m['rms_aligned_mm']:.3f} mm)", zorder=4)
    for s in res.seams:
        ax1.axvline(s["x_mm"], color="#ffb33d", lw=0.8, alpha=0.4)
    ax1.set_xlim(0, L)
    ax1.set_xlabel("längd (mm)", color=ink2, fontsize=9)
    ax1.set_ylabel("tjocklek (mm)", color=ink2, fontsize=9)
    leg = ax1.legend(loc="upper right", fontsize=8, framealpha=0.85, facecolor="#111923",
                     edgecolor=grid, labelcolor=ink)

    # --- 3a) per-huvud bias vs skattad korrektion ---
    ax2 = fig.add_subplot(gs[2, 0])
    style(ax2, "Per-huvud kalibrering")
    labels = [h.label for h in res.heads]
    bias = [h.bias_mm for h in res.heads]
    corr = m["corrections_mm"]
    xb = np.arange(len(labels))
    ax2.bar(xb - 0.2, bias, 0.4, color="#ff4d5e", label="injicerad bias")
    ax2.bar(xb + 0.2, [-c for c in corr], 0.4, color="#27d3e0", label="skattad korr. (−)")
    ax2.axhline(0, color=grid, lw=0.8)
    ax2.set_xticks(xb); ax2.set_xticklabels(labels)
    ax2.set_ylabel("mm", color=ink2, fontsize=9)
    ax2.legend(fontsize=7.5, framealpha=0.85, facecolor="#111923", edgecolor=grid, labelcolor=ink)

    # --- 3b) skarv-samstämmighet före/efter ---
    ax3 = fig.add_subplot(gs[2, 1])
    style(ax3, "Skarv-samstämmighet (överlapp)")
    sl = [f"{res.heads[s['heads'][0]].label}–{res.heads[s['heads'][1]].label}" for s in res.seams]
    xs = np.arange(len(sl))
    ax3.bar(xs - 0.2, [s["rms_before_mm"] for s in res.seams], 0.4, color="#ff4d5e", label="före fusion")
    ax3.bar(xs + 0.2, [s["rms_after_mm"] for s in res.seams], 0.4, color="#34e6b5", label="efter fusion")
    ax3.set_xticks(xs); ax3.set_xticklabels(sl, fontsize=7)
    ax3.set_ylabel("RMS-skillnad (mm)", color=ink2, fontsize=9)
    ax3.legend(fontsize=7.5, framealpha=0.85, facecolor="#111923", edgecolor=grid, labelcolor=ink)

    # --- 3c) synk-schema: en encoder klockar alla huvuden ---
    ax4 = fig.add_subplot(gs[2, 2])
    style(ax4, "Synk: EN encoder klockar alla huvuden")
    ax4.axis("off")
    n = len(res.heads)
    ax4.add_patch(plt.Rectangle((0.05, 0.82), 0.9, 0.12, color="#9a7bff", alpha=0.9))
    ax4.text(0.5, 0.88, "ENCODER (band B)  →  matningsposition", color="#0b0f14",
             ha="center", va="center", fontsize=8.5, fontweight="bold")
    for i, hd in enumerate(res.heads):
        xc = 0.08 + (0.84) * (i + 0.5) / n
        ax4.plot([0.5, xc], [0.82, 0.55], color=grid, lw=1)
        ax4.add_patch(plt.Rectangle((xc - 0.06, 0.40), 0.12, 0.15, color=HEAD_CMAP(i % 10), alpha=0.85))
        ax4.text(xc, 0.475, hd.label, color="#0b0f14", ha="center", va="center",
                 fontsize=8, fontweight="bold")
    ax4.text(0.5, 0.22, "samma encoder-tick → alla huvuden samplar SAMMA rad\n"
                        "→ sektionerna ligger i samma koordinat → kan fusioneras",
             color=ink2, ha="center", va="center", fontsize=8)
    ax4.set_xlim(0, 1); ax4.set_ylim(0, 1)

    # --- 4) fuserad höjdkarta (hela brädan) ---
    ax5 = fig.add_subplot(gs[3, :])
    style(ax5, "Fuserad höjdkarta (hela brädan) — sömlös trots 6 separata huvuden")
    z = res.fused_zmap
    im = ax5.imshow(z, extent=[0, L, 0, Wmm], aspect="auto", origin="lower",
                    cmap="turbo", vmin=np.percentile(z, 1), vmax=np.percentile(z, 99))
    for s in res.seams:
        ax5.axvline(s["x_mm"], color="white", lw=0.6, alpha=0.35, ls="--")
    ax5.set_xlim(0, L); ax5.set_ylim(0, Wmm)
    ax5.set_xlabel("längd (mm)", color=ink2, fontsize=9)
    ax5.set_yticks([0, Wmm])
    cb = fig.colorbar(im, ax=ax5, fraction=0.025, pad=0.01)
    cb.ax.tick_params(colors=ink2, labelsize=7)
    cb.set_label("tjocklek (mm)", color=ink2, fontsize=8)

    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--heads", type=int, default=6)
    ap.add_argument("--len", type=float, default=5400.0, dest="length")
    ap.add_argument("--overlap", type=float, default=80.0)
    ap.add_argument("--seed", type=int, default=20240614)
    ap.add_argument("--out", default="multihead_sim.png")
    a = ap.parse_args(argv[1:])
    res = simulate(total_len_mm=a.length, n_heads=a.heads, overlap_mm=a.overlap, seed=a.seed)
    m = res.metrics
    print(f"{m['n_heads']} huvuden · {m['total_len_mm']:.0f} mm · överlapp {m['overlap_mm']:.0f} mm")
    print(f"RMS vs sann tjocklek:  naiv {m['rms_naive_mm']:.3f} → fusion {m['rms_aligned_mm']:.3f} mm")
    print(f"skarv-samstämmighet:   före {m['seam_rms_before_mm']:.3f} → efter {m['seam_rms_after_mm']:.3f} mm")
    render(res, a.out)
    print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
