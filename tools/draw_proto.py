#!/usr/bin/env python3
"""Prototyp-bänkritning (SVG): EN dubbel-oblik mäthuvud + 3 punktlasrar,
brädor upp till 1 m, Jetson Orin Nano som edge-compute. Datadriven ur Rig.

    python tools/draw_proto.py   # -> prototype-bench-layout.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

r = Rig(board_length_mm=1000, board_width_mm=150, board_thickness_mm=45)
OBL = r.oblique_angle_deg; STAND = round(r.module_standoff_mm); MH = round(r.module_height_mm)
SOFF = round(r.module_side_offset_mm); RED_NM = round(r.laser.wavelength_nm); GRN_NM = round(r.laser_green.wavelength_nm)
BW, BT = round(r.board_width_mm), round(r.board_thickness_mm); BENCH_L = 1000

W, H = 1640, 2040
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"; SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=13, anchor="start", fill=INK, weight=400, fam=MONO, rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tr}>{esc(s)}</text>')
def line(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')
def circ(x, y, rr, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.4):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2 - y1, x2 - x1); L = 9
    for s in (0.5, -0.5): line(x2, y2, x2 - L * math.cos(a - s), y2 - L * math.sin(a - s), stroke, w)
def hdim(x1, x2, y, text, fill=DIMC):
    line(x1, y - 6, x1, y + 6, fill, 1); line(x2, y - 6, x2, y + 6, fill, 1)
    arrow((x1 + x2) / 2, y, x1, y, fill, 1); arrow((x1 + x2) / 2, y, x2, y, fill, 1)
    add(f'<rect x="{(x1+x2)/2-len(text)*4:.1f}" y="{y-11:.1f}" width="{len(text)*8:.1f}" height="15" fill="{PAPER}" opacity="0.9"/>')
    txt((x1 + x2) / 2, y - 1, text, 12, "middle", fill)
def vdim(y1, y2, x, text, fill=DIMC):
    line(x - 6, y1, x + 6, y1, fill, 1); line(x - 6, y2, x + 6, y2, fill, 1)
    arrow(x, (y1 + y2) / 2, x, y1, fill, 1); arrow(x, (y1 + y2) / 2, x, y2, fill, 1)
    txt(x + 9, (y1 + y2) / 2 + 4, text, 12, "start", fill)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(18, 18, W - 36, H - 36, "none", INK, 2); rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)
txt(48, 70, "PROTOTYP-BÄNK — 1 MÄTHUVUD, BRÄDOR ≤ 1 m", 25, "start", INK, 700, SANS)
txt(48, 96, "Ett dubbel-oblikt huvud (röd 650 + grön 520) + 3 punktlasrar (absolut tjocklek), "
            "edge-compute på Jetson Orin Nano. Billig & testbar på 1 m-längder.", 14, "start", MUTED, 400, SANS)
line(48, 110, W - 48, 110, INK, 1.5)
def vlabel(x, y, tag, name):
    rect(x, y, 24, 20, INK, INK); txt(x + 12, y + 15, tag, 13, "middle", PAPER, 700, SANS)
    txt(x + 34, y + 15, name, 15, "start", INK, 700, SANS)

# ===================== VY A — BÄNK OVANIFRÅN (CROSS-FEED) =====================
gA = 130
add(f'<g transform="translate(0,{gA})">')
vlabel(48, 6, "A", "BÄNK — ovanifrån (cross-feed: laserlinje längs 1 m, bräda matas i sidled)")
ax0, ax1 = 150, 1150
def AX(mm): return ax0 + mm * (ax1 - ax0) / BENCH_L
FW = 150 * (ax1 - ax0) / BENCH_L                 # 150 mm bredd i px
y0 = 220                                          # brädans överkant (bredd-axel)
rect(AX(0), y0, AX(BENCH_L) - AX(0), FW, "#e9e1cf", "#b9a96f", 1.4)   # bräda 1 m × 150 mm
txt(AX(BENCH_L) / 1 - 6, 0, "", 1)
txt(AX(20), y0 + FW + 22, "bräda 1000 × 150 mm", 11, "start", "#8a7d4e", 700)
sy = y0 + FW * 0.5                                # laserlinjen (skannläge) längs längden
line(AX(0) - 30, sy, AX(BENCH_L) + 30, sy, INK, 2.2)
txt(AX(BENCH_L) + 36, sy - 6, "laserlinje 1 m", 10, "start", INK, 700)
txt(AX(BENCH_L) + 36, sy + 10, "(röd+grön oblik)", 9, "start", MUTED)
# huvudbalk (T-spår) över hela längden + 3 punktlaser längs linjen
rect(AX(-20), y0 - 64, AX(BENCH_L + 20) - AX(-20), 24, ALU, "#8a9099", 1.4, 3)
txt(AX(10), y0 - 48, "MÄTHUVUD-BALK (T-spår) — 2 oblika linjelaser längs 1 m", 10, "start", MUTED, 700)
for f in (0.1, 0.5, 0.9):
    x = AX(f * BENCH_L)
    rect(x - 13, y0 - 38, 26, 18, "#f3e6fb", PURP, 1.4, 2); txt(x, y0 - 25, "PL", 8.5, "middle", PURP, 700)
    line(x, y0 - 20, x, sy, PURP, 1.4, "2 3"); circ(x, sy, 2.6, PURP, PURP, 0)
txt(AX(0.5 * BENCH_L), y0 - 48, "3 punktlaser (V/C/H)", 9, "middle", PURP, 700)
# matning i sidled (bredd)
arrow(AX(BENCH_L * 0.5), y0 - 8, AX(BENCH_L * 0.5), y0 + FW + 8, "#b06", 2.4)
txt(AX(BENCH_L * 0.5) + 12, y0 + FW + 6, "matning (bredd 150 mm)", 10, "start", "#b06", 700)
# Jetson + encoder
rect(AX(BENCH_L) + 30, y0 + FW + 40, 150, 64, "#e6efe6", JET, 1.6, 6)
txt(AX(BENCH_L) + 105, y0 + FW + 62, "JETSON Orin Nano", 11, "middle", JET, 700, SANS)
txt(AX(BENCH_L) + 105, y0 + FW + 78, "edge-compute + U-Net", 8.5, "middle", MUTED)
rect(AX(-10), y0 + FW + 40, 64, 28, "#cfd2d6", "#7a7f86", 1.2, 2); txt(AX(20), y0 + FW + 58, "ENC", 10, "middle", INK, 700)
txt(AX(-10), y0 + FW + 84, "encoder (matningsläge)", 9, "start", MUTED)
hdim(AX(0), AX(BENCH_L), y0 + FW + 110, "längd 1000 mm (laserlinjens riktning)")
vdim(y0, y0 + FW, AX(0) - 36, "150 mm")
add('</g>')

# ===================== VY B — HUVUD ÄNDVY (oblika + punktlaser) =====================
gB = 560
add(f'<g transform="translate(0,{gB})">')
vlabel(48, 6, "B", "MÄTHUVUD — ändvy: 2 oblika linjelaser + 3 punktlaser")
SC = 0.34; bx, yb2 = 470, 470
def UP(mm): return yb2 - mm * SC
bw, bt = BW * SC, BT * SC; bL, bR = bx - bw / 2, bx + bw / 2
tphy = UP(MH) - 40
rect(bx - 330, tphy, 660, 24, ALU, "#8a9099", 1.4, 4); txt(bx - 324, tphy + 16, "PORTAL / T-SPÅR", 10, "start", MUTED, 700)
mxL, mxR = bx - SOFF * SC, bx + SOFF * SC; myL = myR = UP(MH)
for mx, col, lab, ang in [(mxL, RED, f"RÖD {RED_NM}", OBL), (mxR, GRN, f"GRÖN {GRN_NM}", -OBL)]:
    add(f'<g transform="rotate({ang} {mx} {myL})">')
    rect(mx - 46, myL - 18, 92, 36, "#fff", col, 1.6, 4); rect(mx - 46, myL - 18, 92, 13, col, col, 0, 4)
    txt(mx, myL - 8, lab, 9.5, "middle", PAPER, 700, SANS); txt(mx, myL + 9, "laser+mono", 8, "middle", INK)
    add('</g>')
line(mxL + 14, myL + 16, bL, yb2, RED, 3); line(mxR - 14, myR + 16, bR, yb2, GRN, 3)
circ(bL, yb2, 3, RED, RED, 0); circ(bR, yb2, 3, GRN, GRN, 0)
# 3 punktlaser rakt ner (V/C/H)
for frac, nm in [(0.12, "V"), (0.5, "C"), (0.88, "H")]:
    xx = bL + frac * bw
    rect(xx - 13, UP(MH * 0.62) - 12, 26, 22, "#f3e6fb", PURP, 1.4, 3)
    txt(xx, UP(MH * 0.62) + 2, nm, 9, "middle", PURP, 700)
    line(xx, UP(MH * 0.62) + 10, xx, yb2, PURP, 1.8, "2 3"); circ(xx, yb2, 2.6, PURP, PURP, 0)
txt(bx, UP(MH * 0.62) - 22, "3 punktlaser (absolut tjocklek V/C/H)", 10.5, "middle", PURP, 700)
rect(bL, yb2, bw, bt, "#e9e1cf", "#b9a96f", 1.4); txt(bx, yb2 + bt + 16, f"bräda {BW}×{BT} mm", 10, "middle", "#8a7d4e")
hdim(mxL, bx, UP(MH) - 18, f"sidooffset {SOFF}", DIMC); vdim(UP(MH), yb2, bx + bw / 2 + 210, f"höjd {MH} mm")
txt(mxL - 50, myL + 70, f"{OBL:.0f}° oblik", 11, "start", RED, 700)
add('</g>')

# ===================== BOM =====================
gT = 1090
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5); txt(48, 26, "PROTOTYP — KOMPONENTLISTA (1 HUVUD)", 16, "start", INK, 700, SANS)
cols = [
    (60, JET, "COMPUTE", [
        ("Jetson Orin Nano Super", "1× dev kit (edge + U-Net)"),
        ("NVMe SSD", "1× 256–512 GB M.2"),
        ("Kyl/PSU", "ingår i Super-kit (19 V)"),
        ("USB3-hubb (ev.)", "för 2 kameror"),
    ]),
    (430, RED, "OPTIK / SENSOR", [
        ("Mono-kameror", f"2× MV-CS050-10UM (USB3)"),
        ("Objektiv", "2× 8 mm C-mount"),
        ("Bandpassfilter", f"650 nm + {GRN_NM} nm"),
        ("Linjelaser", f"röd 650 + grön {GRN_NM} (oblika)"),
        ("Punktlaser", "3× avstånd (V/C/H), abs. tjocklek"),
    ]),
    (800, BLUE, "MEKANIK / I/O", [
        ("Ram", "alu T-spår (portal) ~1,2 m"),
        ("Transport", "band/linjärsläde, 1 m + motor"),
        ("Encoder", "kvadratur (matningsläge → GPIO)"),
        ("Lasermontage", "fästen + ev. drivare"),
        ("Kablage/kåpa", "USB3, ström, dammskydd"),
    ]),
    (1170, MUTED, "ANSLUTNING (Jetson)", [
        ("2 mono-kam", "USB 3.2 (dev kit har 4)"),
        ("3 punktlaser", "analog→ADC el. digital/IO"),
        ("Encoder", "40-pin GPIO"),
        ("Lasertrigg", "GPIO"),
        ("OBS 10GigE", "ytfärgkam ej på Jetson"),
    ]),
]
rowh = 30
for (cx, acc, title, rows) in cols:
    cw = 360
    rect(cx, 44, cw, 30, acc, acc, 0, 4); txt(cx + 10, 64, title, 12, "start", PAPER, 700, SANS)
    rect(cx, 74, cw, rowh * len(rows), "#fff", acc, 1)
    for i, (k, v) in enumerate(rows):
        ry = 74 + i * rowh
        if i % 2: rect(cx, ry, cw, rowh, PANEL, "none", 0)
        txt(cx + 10, ry + 19, k, 10, "start", MUTED, 700)
        txt(cx + 150, ry + 19, v, 9.5, "start", INK)
add('</g>')

tb_x, tb_y, tb_w, tb_h = W - 460, H - 92, 410, 60
rect(tb_x, tb_y, tb_w, tb_h, "#fff", INK, 1.4)
line(tb_x, tb_y + 30, tb_x + tb_w, tb_y + 30, INK, 1); line(tb_x + 250, tb_y, tb_x + 250, tb_y + tb_h, INK, 1)
txt(tb_x + 10, tb_y + 19, "VIRKESSKANNER — PROTOTYP", 12, "start", INK, 700, SANS)
txt(tb_x + 260, tb_y + 19, "PROTO-01", 12, "start", INK, 400)
txt(tb_x + 10, tb_y + 49, "Mått i mm · ej skalenlig", 10, "start", MUTED)
txt(tb_x + 260, tb_y + 49, "auto: src/hardware.py", 10, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-bench-layout.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
