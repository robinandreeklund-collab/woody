#!/usr/bin/env python3
#coding=utf-8
"""A4 färgtavla för linjekameran (vektor-PDF), LIGGANDE.
Färgfälten löper längs den LÅNGA sidan (297 mm) -> 2 ark i rad täcker ~594 mm av
kamerans 650 mm-linje. Varje fält fyller hela korta sidan (210 mm) så den tunna
linjen alltid korsar alla färger.
Används för: korrekt Bayer-demosaicing (rött=rött), vitbalans (vitt/grått), färgverifiering."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = "/tmp/claude-1000/-home-admin-woody/b3de0ccd-2a3d-4e42-8894-e78e0e18a9e7/scratchpad/fargtavla_A4.pdf"

# (namn, RGB 0-255, textfärg)
FALT = [
    ("VIT",      (255, 255, 255), "k"),
    ("GRA50",    (128, 128, 128), "w"),
    ("SVART",    (0,   0,   0),   "w"),
    ("ROD",      (220, 30,  30),  "w"),
    ("GRON",     (30,  170, 60),  "w"),
    ("BLA",      (30,  60,  200), "w"),
    ("CYAN",     (0,   170, 200), "k"),
    ("MAGENTA",  (200, 30,  140), "w"),
    ("GUL",      (245, 215, 0),   "k"),
    ("TRA",      (205, 160, 110), "k"),
]

# A4 LIGGANDE: 297 mm bred (x, längs linjen) x 210 mm hög (y)
fig = plt.figure(figsize=(11.6929, 8.2677))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 297); ax.set_ylim(0, 210); ax.axis("off")

ax.text(148.5, 204, "FARGTAVLA linjekamera — langa sidan (297mm) langs linjen, 2 ark i rad",
        ha="center", va="center", fontsize=9, fontweight="bold")

x0, x1, ybot, ytop = 6, 291, 7, 196
n = len(FALT); w = (x1 - x0) / n
for i, (namn, (r, g, b), tc) in enumerate(FALT):
    x = x0 + i * w
    ax.add_patch(Rectangle((x, ybot), w, ytop - ybot, facecolor=(r/255, g/255, b/255), edgecolor="none"))
    ax.text(x + w/2, (ybot+ytop)/2, namn, ha="center", va="center", rotation=90,
            fontsize=12, fontweight="bold", color=tc)
    ax.text(x + w/2, ybot + 5, f"{r},{g},{b}", ha="center", va="center", rotation=90,
            fontsize=6, color=tc)

ax.add_patch(Rectangle((x0, ybot), x1 - x0, ytop - ybot, fill=False, edgecolor="k", lw=0.5))
ax.text(148.5, 3, "Skriv ut i 100% (Verklig storlek, LIGGANDE). Lagg 2 ark i rad langs linjen, plant + belyst.",
        ha="center", fontsize=7)

fig.savefig(OUT, format="pdf")
print("sparad:", OUT)
