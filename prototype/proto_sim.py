"""Prototyp-simulering — ETT dubbel-oblikt mäthuvud, bräda upp till 1 m.

Återanvänder repo-roten: src.board (defekter + höjd), src.hardware.Rig (dubbel
oblik geometri) och src.laser (dual-oblik triangulering). Producerar rena
matplotlib-figurer som prototyp-GUI:t (Streamlit) visar – tänkt att senare köra
på själva prototyp-bänken (Jetson Orin Nano).
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
RED, GRN, BLUE, GOLD = "#e8542c", "#2f9e6e", "#2f6fb0", "#b9a96f"
MAX_LEN = 1000.0


def simulate(length_mm=1000.0, width_mm=150.0, thickness_mm=45.0,
             mm_per_px=0.6, seed=3, subtle=False):
    """Genererar en prototypbräda + kör det dubbel-oblika huvudet."""
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


# ---------------------------------------------------------------- bänkvy (topp)
def fig_bench(sim, feed_frac, figsize=(7.2, 3.0)):
    """Topp-schema: brädan åker förbi huvudets skannlinje. Röd modul vid ena
    långsidan, grön vid den andra. Visar matning + hur mycket som skannats."""
    L, Wd = sim["L"], sim["width"]
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    fig.patch.set_facecolor(PAPER)
    _ax(ax, "BÄNK — bräda passerar mäthuvudet (ovanifrån)")
    sx = feed_frac * L
    ax.add_patch(plt.Rectangle((0, 0), L, Wd, fc="#efe9d8", ec=GOLD, lw=1.4))
    ax.add_patch(plt.Rectangle((0, 0), sx, Wd, fc=BLUE, ec="none", alpha=0.10))   # skannat
    ax.plot([sx, sx], [-22, Wd + 22], color=INK, lw=1.6)                          # skannlinje
    ax.text(sx, Wd + 30, "skannlinje", color=INK, fontsize=8, ha="center")
    # oblika moduler vid var sin långsida
    ax.add_patch(plt.Rectangle((sx - 40, -40), 80, 22, fc="#fde3da", ec=RED, lw=1.4))
    ax.text(sx, -29, f"RÖD 650", color=RED, fontsize=7.5, ha="center", va="center", fontweight="bold")
    ax.add_patch(plt.Rectangle((sx - 40, Wd + 18), 80, 22, fc="#d8efe3", ec=GRN, lw=1.4))
    ax.text(sx, Wd + 29, f"GRÖN 520", color=GRN, fontsize=7.5, ha="center", va="center", fontweight="bold")
    ax.annotate("", xy=(L * 0.62, Wd + 60), xytext=(L * 0.42, Wd + 60),
                arrowprops=dict(arrowstyle="-|>", color="#b06", lw=2))
    ax.text(L * 0.52, Wd + 70, "matning", color="#b06", fontsize=8, ha="center")
    ax.set_xlim(-60, L + 60); ax.set_ylim(-70, Wd + 90)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("bredd (mm)")
    ax.set_aspect("equal"); fig.tight_layout()
    return fig


# ------------------------------------------------------------- tvärsnittsprofil
def fig_profile(sim, feed_frac, figsize=(7.2, 3.0)):
    """Live tvärsnitt vid skannlinjen: höjd vs bredd. Röd halva mäts av röd modul,
    grön halva av grön. Visar topp + kanter/vankant."""
    z = sim["meas"]["z_fused"]; Wd = sim["width"]; T = sim["thickness"]
    H, Wpx = z.shape
    row = int(np.clip(feed_frac * (H - 1), 0, H - 1))
    xs = np.linspace(0, Wd, Wpx)
    prof = z[row]
    half = Wpx // 2
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    fig.patch.set_facecolor(PAPER)
    _ax(ax, "TVÄRSNITT vid skannlinjen — höjdprofil (topp + kanter)")
    ax.fill_between(xs[:half + 1], 0, prof[:half + 1], color=RED, alpha=0.18)
    ax.fill_between(xs[half:], 0, prof[half:], color=GRN, alpha=0.18)
    ax.plot(xs[:half + 1], prof[:half + 1], color=RED, lw=1.8, label="röd linjelaser (V)")
    ax.plot(xs[half:], prof[half:], color=GRN, lw=1.8, label="grön linjelaser (H)")
    ax.axhline(T, color=MUTED, ls="--", lw=0.8)
    ax.text(Wd, T + 0.5, f"nominell {T:.0f} mm", color=MUTED, fontsize=7.5, ha="right")
    # 3 PUNKTLASRAR (absolut tjocklek) – V / C / H, fusion-ankare mot linjeprofilen
    btrue = sim["board"]["height"][row]
    for frac in (0.12, 0.5, 0.88):
        xi = int(frac * (Wpx - 1)); xmm = frac * Wd
        val = float(btrue[xi] + np.random.default_rng(row + int(frac * 100)).normal(0, 0.05))
        ax.plot(xmm, val, marker="v", ms=10, color="#a23ad6", mec="k", mew=0.6, zorder=6)
        ax.annotate(f"{val:.1f}", (xmm, val), textcoords="offset points",
                    xytext=(0, 9), fontsize=7, color="#a23ad6", ha="center", fontweight="bold")
    ax.plot([], [], marker="v", color="#a23ad6", ls="none", label="punktlaser (absolut)")
    ax.set_xlim(0, Wd); ax.set_ylim(0, T * 1.5)
    ax.set_xlabel("bredd (mm)"); ax.set_ylabel("höjd (mm)")
    ax.legend(loc="lower center", fontsize=7.5, ncol=3, frameon=False)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ höjdkarta
def fig_heightmap(sim, feed_frac, figsize=(7.2, 3.2)):
    """Uppbyggd höjdkarta (längd×bredd) + defekt-overlay till skannlinjen."""
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]
    L, Wd = sim["L"], sim["width"]
    H, Wpx = z.shape
    cut = int(np.clip(feed_frac * H, 1, H))
    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    fig.patch.set_facecolor(PAPER)
    _ax(ax, "HÖJDKARTA (skannas uppifrån) + defekter")
    img = np.full_like(z, np.nan)
    img[:cut] = z[:cut]
    ax.imshow(img.T, aspect="auto", origin="lower", cmap="viridis",
              extent=[0, L, 0, Wd], vmin=np.nanmin(z), vmax=np.nanmax(z))
    # defekt-overlay
    ov = np.zeros((*lbl.shape, 4))
    for cid, col in CLASS_COLORS.items():
        if cid == 0:
            continue
        m = (lbl == cid)
        ov[m] = (*col, 0.85)
    ov[cut:] = 0
    ax.imshow(np.transpose(ov, (1, 0, 2)), aspect="auto", origin="lower", extent=[0, L, 0, Wd])
    ax.axvline(feed_frac * L, color=INK, lw=1.2)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("bredd (mm)")
    fig.tight_layout()
    return fig


# -------------------------------------------------------------------- enkel 3D
def fig_surface3d(sim, feed_frac=1.0, figsize=(7.2, 3.6), stride=14):
    """Enkel 3D-yta av uppmätt höjd (nedsamplad för fart)."""
    z = sim["meas"]["z_fused"]; L, Wd = sim["L"], sim["width"]
    H, Wpx = z.shape
    cut = int(np.clip(feed_frac * H, 2, H))
    zc = z[:cut:stride, ::max(1, Wpx // 60)]
    xx = np.linspace(0, feed_frac * L, zc.shape[0])
    yy = np.linspace(0, Wd, zc.shape[1])
    X, Y = np.meshgrid(xx, yy, indexing="ij")
    fig = plt.figure(figsize=figsize, dpi=120); fig.patch.set_facecolor(PAPER)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(PAPER)
    ax.plot_surface(X, Y, zc, cmap="viridis", linewidth=0, antialiased=True,
                    rcount=zc.shape[0], ccount=zc.shape[1])
    ax.set_title("ENKEL 3D — uppmätt brädyta", color=INK, fontsize=11, fontweight="bold", loc="left")
    ax.set_xlabel("längd (mm)", fontsize=8); ax.set_ylabel("bredd (mm)", fontsize=8)
    ax.set_zlabel("höjd (mm)", fontsize=8)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.view_init(elev=42, azim=-62)
    try:
        ax.set_box_aspect((3, 1, 0.5))
    except Exception:
        pass
    fig.tight_layout()
    return fig


def metrics(sim):
    """Nyckeltal för panelen."""
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]
    cov = sim["meas"]["coverage"]
    mid = z[:, z.shape[1] // 2]
    counts = {CLASSES[c]: int((lbl == c).sum()) for c in range(1, 7) if (lbl == c).any()}
    return {
        "tjocklek_mm": round(float(np.median(mid)), 1),
        "tackning_pct": round(cov * 100, 1),
        "langd_mm": round(sim["L"]),
        "bredd_mm": round(sim["width"]),
        "defekter": counts,
    }


if __name__ == "__main__":   # snabb dashboard-render (verifiering)
    s = simulate(length_mm=1000, width_mm=150, thickness_mm=45, seed=3)
    print("metrics:", metrics(s))
    figs = [("bench", fig_bench(s, 0.55)), ("profile", fig_profile(s, 0.55)),
            ("heightmap", fig_heightmap(s, 0.55)), ("surface3d", fig_surface3d(s, 1.0))]
    for name, f in figs:
        f.savefig(f"/tmp/proto_{name}.png", facecolor=PAPER, bbox_inches="tight")
    print("renderade 4 figurer till /tmp/proto_*.png")
