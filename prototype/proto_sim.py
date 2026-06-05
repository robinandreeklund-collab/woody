"""Prototyp-simulering — ETT dubbel-oblikt mäthuvud, bräda upp till 1 m.

CROSS-FEED (som hela riggen): laserlinjen löper LÄNGS brädans 1 m längd; brädan
matas i SIDLED så att de 150 mm bredden passerar förbi huvudet. Vid varje
matningsläge mäts höjdprofilen längs hela 1 m-linjen; över matningen byggs hela
höjdkartan (längd × bredd) upp.

Återanvänder src.board (defekter+höjd), src.hardware.Rig (dubbel oblik) och
src.laser (dual-oblik triangulering). Producerar rena matplotlib-figurer.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.board import make_board
from src.hardware import Rig
from src.laser import simulate_array
from src.config import CLASSES, CLASS_COLORS

INK, MUTED, PAPER = "#23262b", "#6a6e74", "#f7f6f1"
RED, GRN, BLUE, GOLD, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#b9a96f", "#a23ad6"
MAX_LEN = 1000.0
PL_FRACS = (0.1, 0.5, 0.9)          # 3 punktlaser: V / C / H längs 1 m-linjen


def simulate(length_mm=1000.0, width_mm=150.0, thickness_mm=45.0,
             mm_per_px=0.6, seed=3, subtle=False):
    """Bräda + det dubbel-oblika huvudet. Höjdkarta: axel0=längd, axel1=bredd(matning)."""
    L = float(min(length_mm, MAX_LEN))
    b = make_board(length_mm=L, width_mm=width_mm, thickness_mm=thickness_mm,
                   mm_per_px=mm_per_px, seed=int(seed), subtle_defects=subtle)
    rig = Rig(board_length_mm=L, board_width_mm=width_mm, board_thickness_mm=thickness_mm)
    res = simulate_array(b["height"], mm_per_px, rig, seed=1)
    return {"board": b, "rig": rig, "meas": res, "mm_per_px": mm_per_px,
            "L": L, "width": width_mm, "thickness": thickness_mm}


def _ax(ax, title):
    ax.set_facecolor("#fff")
    for s in ax.spines.values():
        s.set_color(MUTED); s.set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_title(title, color=INK, fontsize=11, fontweight="bold", loc="left", pad=8)


# ---------------------------------------------------- bänkvy (ovanifrån, cross-feed)
def fig_bench(sim, feed_frac, figsize=(7.2, 3.2)):
    L, Wd = sim["L"], sim["width"]
    fig, ax = plt.subplots(figsize=figsize, dpi=120); fig.patch.set_facecolor("#ffffff")
    _ax(ax, "BÄNK — bräda matas i SIDLED förbi 1 m-laserlinjen (ovanifrån)")
    sy = feed_frac * Wd
    ax.add_patch(plt.Rectangle((0, 0), L, Wd, fc="#efe9d8", ec=GOLD, lw=1.4))
    ax.add_patch(plt.Rectangle((0, 0), L, sy, fc=BLUE, ec="none", alpha=0.10))   # skannat
    ax.plot([0, L], [sy, sy], color=INK, lw=2.0)                                 # 1 m laserlinje
    ax.text(L + 8, sy, "laserlinje 1 m\n(röd+grön oblik)", color=INK, fontsize=7.5, va="center")
    for f in PL_FRACS:                                                           # 3 punktlaser längs linjen
        ax.plot(f * L, sy, marker="v", ms=10, color=PURP, mec="k", mew=0.5, zorder=5)
    ax.plot([], [], marker="v", color=PURP, ls="none", label="3 punktlaser (V/C/H)")
    ax.annotate("", xy=(L * 0.5, sy + 46), xytext=(L * 0.5, sy + 8),
                arrowprops=dict(arrowstyle="-|>", color="#b06", lw=2))
    ax.text(L * 0.5 + 10, sy + 28, "matning (bredd)", color="#b06", fontsize=8)
    ax.set_xlim(-20, L + 150); ax.set_ylim(-20, Wd + 20)
    ax.set_xlabel("längd (mm) — laserlinjens riktning"); ax.set_ylabel("bredd (mm) — matning")
    ax.set_aspect("auto"); ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    fig.tight_layout(); return fig


# ------------------------------------------------- live längsprofil + punktlaser
def fig_profile(sim, feed_frac, figsize=(7.2, 3.2)):
    """Det huvudet mäter NU: höjd längs hela 1 m-linjen vid aktuellt bredd-läge.
    3 punktlasrar ger absolut tjocklek (lila) → fusion-ankare mot linjeprofilen."""
    z = sim["meas"]["z_fused"]; btrue = sim["board"]["height"]
    L, T = sim["L"], sim["thickness"]
    Hpx, Wpx = z.shape
    col = int(np.clip(feed_frac * (Wpx - 1), 0, Wpx - 1))
    xs = np.linspace(0, L, Hpx); prof = z[:, col]
    fig, ax = plt.subplots(figsize=figsize, dpi=120); fig.patch.set_facecolor("#ffffff")
    _ax(ax, "LIVE LÄNGSPROFIL (1 m) + punktlaser-ankare")
    ax.fill_between(xs, 0, prof, color=RED, alpha=0.10)
    ax.plot(xs, prof, color=RED, lw=1.5, label="linjelaser (profil)")
    ax.axhline(T, color=MUTED, ls="--", lw=0.8)
    ax.text(L, T + 0.4, f"nominell {T:.0f} mm", color=MUTED, fontsize=7.5, ha="right")
    for f in PL_FRACS:
        li = int(f * (Hpx - 1)); xmm = f * L
        val = float(btrue[li, col] + np.random.default_rng(col + int(f * 100)).normal(0, 0.04))
        ax.plot(xmm, val, marker="v", ms=11, color=PURP, mec="k", mew=0.6, zorder=6)
        ax.annotate(f"{val:.1f}", (xmm, val), textcoords="offset points",
                    xytext=(0, 9), fontsize=7.5, color=PURP, ha="center", fontweight="bold")
    ax.plot([], [], marker="v", color=PURP, ls="none", label="punktlaser (absolut)")
    ax.set_xlim(0, L); ax.set_ylim(0, T * 1.5)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("höjd (mm)")
    ax.legend(loc="lower center", fontsize=7.5, ncol=2, frameon=False)
    fig.tight_layout(); return fig


# --------------------------------------------------- höjdkarta (byggs i bredd)
def fig_heightmap(sim, feed_frac, figsize=(7.2, 3.2)):
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]
    L, Wd = sim["L"], sim["width"]; Hpx, Wpx = z.shape
    cut = int(np.clip(feed_frac * Wpx, 1, Wpx))
    fig, ax = plt.subplots(figsize=figsize, dpi=120); fig.patch.set_facecolor("#ffffff")
    _ax(ax, "HÖJDKARTA (byggs upp i matningsled) + defekter")
    img = np.full_like(z, np.nan); img[:, :cut] = z[:, :cut]
    ax.imshow(img.T, aspect="auto", origin="lower", cmap="viridis",
              extent=[0, L, 0, Wd], vmin=np.nanmin(z), vmax=np.nanmax(z))
    ov = np.zeros((*lbl.shape, 4))
    for cid, c in CLASS_COLORS.items():
        if cid:
            ov[lbl == cid] = (*c, 0.85)
    ov[:, cut:] = 0
    ax.imshow(np.transpose(ov, (1, 0, 2)), aspect="auto", origin="lower", extent=[0, L, 0, Wd])
    ax.axhline(feed_frac * Wd, color=INK, lw=1.2)
    for f in PL_FRACS:
        ax.plot(f * L, feed_frac * Wd, marker="v", ms=7, color=PURP, mec="k", mew=0.4)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("bredd (mm) — matning")
    fig.tight_layout(); return fig


# -------------------------------------------------------------------- enkel 3D
def fig_surface3d(sim, feed_frac=1.0, figsize=(7.2, 3.6), stride=14):
    z = sim["meas"]["z_fused"]; L, Wd = sim["L"], sim["width"]; Hpx, Wpx = z.shape
    cut = int(np.clip(feed_frac * Wpx, 2, Wpx))
    zc = z[::stride, :cut:max(1, cut // 60 or 1)]
    xx = np.linspace(0, L, zc.shape[0]); yy = np.linspace(0, feed_frac * Wd, zc.shape[1])
    X, Y = np.meshgrid(xx, yy, indexing="ij")
    fig = plt.figure(figsize=figsize, dpi=120); fig.patch.set_facecolor("#ffffff")
    ax = fig.add_subplot(111, projection="3d"); ax.set_facecolor(PAPER)
    ax.plot_surface(X, Y, zc, cmap="viridis", linewidth=0, antialiased=True,
                    rcount=zc.shape[0], ccount=zc.shape[1])
    ax.set_title("ENKEL 3D — uppmätt brädyta", color=INK, fontsize=11, fontweight="bold", loc="left")
    ax.set_xlabel("längd (mm)", fontsize=8); ax.set_ylabel("bredd (mm)", fontsize=8)
    ax.set_zlabel("höjd (mm)", fontsize=8); ax.tick_params(colors=MUTED, labelsize=7)
    ax.view_init(elev=42, azim=-62)
    try: ax.set_box_aspect((3, 0.6, 0.4))
    except Exception: pass
    fig.tight_layout(); return fig


def metrics(sim):
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]; btrue = sim["board"]["height"]
    Hpx, Wpx = z.shape
    pls = [float(np.median(btrue[int(f * (Hpx - 1)), :])) for f in PL_FRACS]
    counts = {CLASSES[c]: int((lbl == c).sum()) for c in range(1, 7) if (lbl == c).any()}
    return {
        "tjocklek_punktlaser_mm": round(float(np.mean(pls)), 1),
        "tackning_pct": round(sim["meas"]["coverage"] * 100, 1),
        "langd_mm": round(sim["L"]), "bredd_mm": round(sim["width"]),
        "defekter": counts,
    }


if __name__ == "__main__":
    s = simulate(1000, 150, 45, seed=3)
    print("metrics:", metrics(s))
    for name, f in [("bench", fig_bench(s, 0.55)), ("profile", fig_profile(s, 0.55)),
                    ("heightmap", fig_heightmap(s, 0.55)), ("surface3d", fig_surface3d(s, 1.0))]:
        f.savefig(f"/tmp/proto_{name}.png", facecolor=PAPER, bbox_inches="tight")
    print("renderade 4 figurer")
