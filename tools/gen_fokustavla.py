#!/usr/bin/env python3
#coding=utf-8
"""Genererar en A4-fokustavla för linjekameran (vektor-PDF).
Siemens-stjärnor (alla riktningar + frekvenser) + linjegitter + skala.
Lägg under kameran, vrid fokus tills FOKUS-talet i strömmen toppar."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Rectangle

OUT = "/tmp/claude-1000/-home-admin-woody/b3de0ccd-2a3d-4e42-8894-e78e0e18a9e7/scratchpad/fokustavla_A4.pdf"

fig = plt.figure(figsize=(8.2677, 11.6929))   # A4 stående (tum)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 210); ax.set_ylim(0, 297); ax.set_aspect("equal"); ax.axis("off")


def siemens(cx, cy, r, sectors=72):
    """Siemens-stjärna: fyll varannan vinkel-sektor svart."""
    step = 360.0 / sectors
    for k in range(0, sectors, 2):
        ax.add_patch(Wedge((cx, cy), r, k * step, (k + 1) * step, facecolor="black", edgecolor="none"))
    ax.add_patch(plt.Circle((cx, cy), r * 0.04, color="white", zorder=5))  # liten vit prick i mitten


def grating(x0, y0, w, h, pitch_mm, vertical=True):
    """Linjegitter med given linjedelning (mm)."""
    n = int((w if vertical else h) / pitch_mm)
    for i in range(0, n, 2):
        if vertical:
            ax.add_patch(Rectangle((x0 + i * pitch_mm, y0), pitch_mm, h, color="black"))
        else:
            ax.add_patch(Rectangle((x0, y0 + i * pitch_mm), w, pitch_mm, color="black"))


# --- rubrik ---
ax.text(105, 289, "FOKUSTAVLA  linjekamera  (HT-GELM44C-T2)", ha="center", va="center",
        fontsize=11, fontweight="bold")
ax.text(105, 283.5, "Lagg under kameran. Vrid fokusringen tills FOKUS-talet i strommen ar storst.",
        ha="center", va="center", fontsize=7.5)

# --- rutnät av Siemens-stjärnor (detalj överallt, alla riktningar) ---
cols = [38, 86, 124, 172]
rows = [248, 200, 152, 104]
for ry in rows:
    for cx in cols:
        siemens(cx, ry, 20)

# --- mitten-stjärnor lite förskjutna så det blir detalj även mellan ---
for cx in [62, 148]:
    for ry in [224, 176, 128]:
        siemens(cx, ry, 11, sectors=48)

# --- upplösnings-gitter (lodräta + vågräta band, krympande delning) ---
yb = 56
ax.text(105, yb + 30, "Upplosnings-gitter (linjedelning i mm)", ha="center", fontsize=8, fontweight="bold")
xb = 14
for pitch in [2.0, 1.0, 0.5, 0.3]:
    grating(xb, yb, 40, 22, pitch, vertical=True)
    ax.text(xb + 20, yb - 3, f"{pitch} mm", ha="center", fontsize=7)
    xb += 46

# --- skala-linjal längst ned (10 mm-steg) ---
y0 = 30
for i in range(0, 19):
    x = 15 + i * 10
    ax.add_patch(Rectangle((x, y0), 0.4, 4 if i % 5 else 7, color="black"))
    if i % 5 == 0:
        ax.text(x, y0 - 3, f"{i*10}", ha="center", fontsize=6)
ax.add_patch(Rectangle((15, y0), 180, 0.4, color="black"))
ax.text(105, y0 - 8, "Skala (mm) — vid ~450 mm avstand ser kameran ~650 mm brett, ~0.16 mm/pixel",
        ha="center", fontsize=7)

# --- hörn-markörer ---
for x in (8, 202):
    for y in (8, 289):
        ax.add_patch(plt.Circle((x, y), 2.2, fill=False, lw=1.0))
        ax.add_patch(plt.Circle((x, y), 0.5, color="black"))

fig.savefig(OUT, format="pdf")
print("sparad:", OUT)
