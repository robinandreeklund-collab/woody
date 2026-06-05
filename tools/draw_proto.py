#!/usr/bin/env python3
"""Prototyp-bänkritning (SVG) — 500 mm-brädor, EN dubbel-oblik mäthuvud + över-
liggande line-scan-ytkamera + 3 punktlaser, 2 mini-transportband (cross-feed),
encoder/mäthjul, Jetson Orin Nano. Stativ/mätram dimensionerat för 500 mm (FOV
matchad → kortare arbetsavstånd med samma optik). Datadriven ur Rig.

    python tools/draw_proto.py   # -> prototype-bench-layout.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

BENCH_L = 500
r = Rig(board_length_mm=BENCH_L, board_width_mm=150, board_thickness_mm=45)
OBL = r.oblique_angle_deg
# FOV matchad till 500 mm med SAMMA optik (CS050 + 8 mm) → kortare arbetsavstånd
WD = round(BENCH_L * r.profile_lens_mm / r.profile_cam.sensor_w_mm)        # ~474 mm
SOFF = round(WD * math.sin(math.radians(OBL)))                              # ~335 mm
MH = round(WD * math.cos(math.radians(OBL)))                                # ~335 mm
SURF_WD = round(55 * BENCH_L / r.surface_cam.sensor_w_mm)                   # ~480 mm (M72 55 mm)
RED_NM, GRN_NM = round(r.laser.wavelength_nm), round(r.laser_green.wavelength_nm)
BW, BT = 150, 45

W, H = 1640, 1660
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
BELT, SURFC = "#444a52", "#7a3fb0"
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
txt(48, 70, "PROTOTYP-BÄNK — 1 MÄTHUVUD, BRÄDOR 500 mm", 25, "start", INK, 700, SANS)
txt(48, 96, "Dubbel-oblikt huvud (röd 650 + grön 520) + överliggande line-scan-ytkamera + 3 punktlaser. "
            "2 mini-transportband (cross-feed), encoder/mäthjul, Jetson Orin Nano.", 14, "start", MUTED, 400, SANS)
line(48, 110, W - 48, 110, INK, 1.5)
def vlabel(x, y, tag, name):
    rect(x, y, 24, 20, INK, INK); txt(x + 12, y + 15, tag, 13, "middle", PAPER, 700, SANS)
    txt(x + 34, y + 15, name, 15, "start", INK, 700, SANS)

# ===================== VY A — BÄNK OVANIFRÅN (CROSS-FEED) =====================
gA = 128
add(f'<g transform="translate(0,{gA})">')
vlabel(48, 6, "A", "BÄNK — ovanifrån (cross-feed: laserlinje längs 500 mm, bräda matas i sidled)")
ax0, ax1 = 210, 1010
def AX(mm): return ax0 + mm * (ax1 - ax0) / BENCH_L
PXMM = (ax1 - ax0) / BENCH_L
FW = 150 * PXMM                                   # 150 mm bredd i px
y0 = 210                                          # brädans överkant (bredd-axel)
# 2 transportband vid ändarna (löper i matningsled), sticker ut förbi brädan
beltw = 85 * PXMM
for bxmm, lab in [(42, "V"), (BENCH_L - 42, "H")]:
    bxp = AX(bxmm)
    rect(bxp - beltw / 2, y0 - 34, beltw, FW + 78, BELT, "#2b2f35", 1.2, 4)
    for ry in (y0 - 34, y0 + FW + 32): circ(bxp, ry, 5, "#9aa0a8", "#2b2f35", 1)
    txt(bxp, y0 + FW + 60, f"BAND {lab}", 9, "middle", "#dfe3e8", 700)
rect(AX(0), y0, AX(BENCH_L) - AX(0), FW, "#e9e1cf", "#b9a96f", 1.4)   # bräda 500 × 150
txt(AX(14), y0 + FW - 8, "bräda 500 × 150 mm", 11, "start", "#8a7d4e", 700)
sy = y0 + FW * 0.5                                # laserlinjen längs längden
line(AX(0) - 26, sy, AX(BENCH_L) + 26, sy, INK, 2.2)
txt(AX(BENCH_L) + 70, sy - 6, "laserlinje 500 mm", 10, "start", INK, 700)
txt(AX(BENCH_L) + 70, sy + 10, "(röd+grön oblik)", 9, "start", MUTED)
# huvudbalk (T-spår) + 3 punktlaser längs linjen
txt(AX(0.5 * BENCH_L), y0 - 68, "3 punktlaser (V/C/H längs 500 mm → ankrar längsprofil)", 9, "middle", PURP, 700)
rect(AX(-16), y0 - 60, AX(BENCH_L + 16) - AX(-16), 22, ALU, "#8a9099", 1.4, 3)
txt(AX(8), y0 - 45, "MÄTHUVUD-BALK (T-spår) — 2 oblika moduler", 9.5, "start", MUTED, 700)
for f in (0.1, 0.5, 0.9):
    x = AX(f * BENCH_L)
    rect(x - 12, y0 - 36, 24, 16, "#f3e6fb", PURP, 1.4, 2); txt(x, y0 - 24, "PL", 8, "middle", PURP, 700)
    line(x, y0 - 20, x, sy, PURP, 1.3, "2 3"); circ(x, sy, 2.4, PURP, PURP, 0)
# matning i sidled (bredd)
arrow(AX(BENCH_L * 0.32), y0 - 6, AX(BENCH_L * 0.32), y0 + FW + 6, "#b06", 2.2)
txt(AX(BENCH_L * 0.32) + 10, y0 + FW - 22, "matning (bredd 150 mm)", 10, "start", "#b06", 700)
# mäthjul/encoder mot brädan
circ(AX(BENCH_L * 0.7), y0 + 10, 8, "#cfd2d6", "#7a7f86", 1.4)
txt(AX(BENCH_L * 0.7) + 13, y0 + 14, "mäthjul (encoder)", 9, "start", MUTED, 700)
# Jetson
rect(AX(BENCH_L) + 64, y0 + FW - 8, 150, 60, "#e6efe6", JET, 1.6, 6)
txt(AX(BENCH_L) + 139, y0 + FW + 14, "JETSON Orin Nano", 11, "middle", JET, 700, SANS)
txt(AX(BENCH_L) + 139, y0 + FW + 30, "edge-compute + U-Net", 8.5, "middle", MUTED)
hdim(AX(0), AX(BENCH_L), y0 + FW + 96, "längd 500 mm (laserlinjens riktning)")
vdim(y0, y0 + FW, AX(0) - 55, "150 mm")
add('</g>')

# ===================== VY B — HUVUD/STATIV ÄNDVY =====================
gB = 690
add(f'<g transform="translate(0,{gB})">')
vlabel(48, 6, "B", "MÄTHUVUD + STATIV — ändvy (för 500 mm, FOV-matchad → kortare avstånd)")
SC = 0.50; bx = 560; yb2 = 300
def UP(mm): return yb2 - mm * SC
bw, bt = BW * SC, BT * SC; bL, bR = bx - bw / 2, bx + bw / 2
mxL, mxR = bx - SOFF * SC, bx + SOFF * SC; myL = myR = UP(MH)
camY = UP(SURF_WD); beamY = camY - 30; legX = SOFF * SC + 70; floorY = yb2 + bt + 96
# stativ: bas + två ben + toppbalk (mätram)
rect(bx - legX - 40, floorY, 2 * (legX + 40), 16, "#bfc3c8", "#8a9099", 1.4, 3)
txt(bx, floorY + 12, "BAS / GOLVPLATTA", 9, "middle", MUTED, 700)
for lx in (bx - legX, bx + legX):
    rect(lx - 9, beamY, 18, floorY - beamY, ALU, "#8a9099", 1.4, 3)
rect(bx - legX - 9, beamY, 2 * legX + 18, 18, ALU, "#8a9099", 1.4, 3)
txt(bx, beamY + 13, "MÄTRAM / PORTALBALK (T-spår)", 9.5, "middle", MUTED, 700)
vdim(beamY, floorY, bx - legX - 36, "stativ-\nhöjd")
# överliggande line-scan ytkamera + RGB/NIR-strobe (rakt ovan)
rect(bx - 54, camY - 16, 108, 26, "#efe6f7", SURFC, 1.6, 5)
txt(bx, camY - 3, "YTKAMERA line-scan", 8.5, "middle", SURFC, 700, SANS)
txt(bx, camY + 7, "M72 + RGB/NIR-strobe", 7.5, "middle", INK)
line(bx, beamY + 18, bx, camY - 16, "#8a9099", 3)             # mast till balk
for sxmm in (-BW / 2, BW / 2):
    line(bx, camY + 10, bx + sxmm * SC, yb2, SURFC, 0.9, "3 3")
vdim(camY, yb2, bR + 150, f"yt-WD ~{SURF_WD} mm")
# 2 oblika moduler (laser+mono), monterade på portalbalken
for mx, col, lab, ang in [(mxL, RED, f"RÖD {RED_NM}", OBL), (mxR, GRN, f"GRÖN {GRN_NM}", -OBL)]:
    line(mx, beamY + 18, mx, myL - 16, "#8a9099", 2.4)        # fäste till balk
    add(f'<g transform="rotate({ang} {mx} {myL})">')
    rect(mx - 44, myL - 17, 88, 34, "#fff", col, 1.6, 4); rect(mx - 44, myL - 17, 88, 12, col, col, 0, 4)
    txt(mx, myL - 7, lab, 9, "middle", PAPER, 700, SANS); txt(mx, myL + 9, "laser+mono", 7.5, "middle", INK)
    add('</g>')
line(mxL + 13, myL + 15, bL, yb2, RED, 3); line(mxR - 13, myR + 15, bR, yb2, GRN, 3)
circ(bL, yb2, 3, RED, RED, 0); circ(bR, yb2, 3, GRN, GRN, 0)
txt(mxL - 6, myL + 64, f"{OBL:.0f}°", 11, "middle", RED, 700); txt(mxR + 6, myR + 64, f"{OBL:.0f}°", 11, "middle", GRN, 700)
# 3 punktlaser (centrerat skott; 3× in i bilden längs 500 mm)
line(bx + 22, UP(MH * 0.5), bx + 22, yb2, PURP, 1.6, "2 3"); circ(bx + 22, yb2, 2.6, PURP, PURP, 0)
rect(bx + 9, UP(MH * 0.5) - 12, 26, 18, "#f3e6fb", PURP, 1.4, 3); txt(bx + 22, UP(MH * 0.5), "PL", 8.5, "middle", PURP, 700)
txt(bx + 40, UP(MH * 0.5) - 2, "3× punktlaser (V/C/H) — in i bilden", 9, "start", PURP, 700)
# bräda på transportband (ändstöd)
rect(bL, yb2, bw, bt, "#e9e1cf", "#b9a96f", 1.4); txt(bx, yb2 + bt + 15, f"bräda {BW}×{BT} mm", 9.5, "middle", "#8a7d4e")
rect(bL - 14, yb2 + bt, bw + 28, 14, BELT, "#2b2f35", 1.2, 3)
for rx in (bL - 6, bR + 6): circ(rx, yb2 + bt + 7, 5, "#9aa0a8", "#2b2f35", 1)
txt(bx, yb2 + bt + 36, "transportband (ändstöd, 24 V · 50 mm/s)", 8.5, "middle", MUTED)
hdim(mxL, bx, myL - 30, f"sidooffset {SOFF}", DIMC)
txt(bx - 6, UP(MH) - 46, f"arbetsavstånd ~{WD} mm (oblik) · modulhöjd {MH} mm", 9.5, "middle", DIMC, 700)
add('</g>')

# ===================== BOM =====================
gT = 1180
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5); txt(48, 26, "KOMPONENTLISTA — fasad uppbyggnad (1 huvud)", 16, "start", INK, 700, SANS)
cols = [
    (60, JET, "FAS 1 · COMPUTE + VÄNSTER", [
        ("Jetson Orin Nano", "Super dev kit (edge+U-Net)"),
        ("Profilkamera V", f"MV-CS050-10UM mono (USB3)"),
        ("Objektiv", "8 mm C-mount + bandpass 650"),
        ("Linjelaser röd", f"iadiy 650 nm 100 mW (oblik)"),
        ("Alu-ram", "enkel ram, putta för hand"),
    ]),
    (430, GRN, "FAS 2 · HÖGER + MATNING", [
        ("Profilkamera H", "MV-CS050-10UM + bandpass 520"),
        ("Linjelaser grön", f"iadiy 520 nm 50 mW (oblik)"),
        ("Transportband", "2× 24 V, 50 mm/s (V/H)"),
        ("Motorregulator", "24 V PWM (trimma takt)"),
        ("Encoder", "mäthjul mot bräda (RS422)"),
    ]),
    (800, SURFC, "FAS 3 · YTA + PUNKTLASER", [
        ("Ytkamera", "MindVision line-scan (NBASE-T)"),
        ("Objektiv M72", "8K 55–60 mm (⌀≥62 mm)"),
        ("Belysning", "850 nm NIR + RGB strobe"),
        ("Punktlaser", "3× HG-C1100 + MCP3008 ADC"),
        ("LED-driver", "strobe via ytkam 3 utgångar"),
    ]),
    (1170, MUTED, "ANSLUTNING (Jetson)", [
        ("2 profilkam", "USB3 (~307 MB/s/st)"),
        ("Ytkamera", "NBASE-T → 1GbE direkt"),
        ("Punktlaser", "analog → MCP3008 (SPI)"),
        ("Encoder", "RS422→ytkam + GPIO"),
        ("Strobe", "ytkamerans 3 strobe-ut"),
    ]),
]
rowh = 30
for (cx, acc, title, rows) in cols:
    cw = 360
    rect(cx, 44, cw, 30, acc, acc, 0, 4); txt(cx + 10, 64, title, 11, "start", PAPER, 700, SANS)
    rect(cx, 74, cw, rowh * len(rows), "#fff", acc, 1)
    for i, (k, v) in enumerate(rows):
        ry = 74 + i * rowh
        if i % 2: rect(cx, ry, cw, rowh, PANEL, "none", 0)
        txt(cx + 10, ry + 19, k, 10, "start", MUTED, 700)
        txt(cx + 145, ry + 19, v, 9, "start", INK)
add('</g>')

tb_x, tb_y, tb_w, tb_h = W - 460, H - 92, 410, 60
rect(tb_x, tb_y, tb_w, tb_h, "#fff", INK, 1.4)
line(tb_x, tb_y + 30, tb_x + tb_w, tb_y + 30, INK, 1); line(tb_x + 250, tb_y, tb_x + 250, tb_y + tb_h, INK, 1)
txt(tb_x + 10, tb_y + 19, "VIRKESSKANNER — PROTOTYP 500 mm", 12, "start", INK, 700, SANS)
txt(tb_x + 260, tb_y + 19, "PROTO-500", 12, "start", INK, 400)
txt(tb_x + 10, tb_y + 49, "Mått i mm · ej skalenlig", 10, "start", MUTED)
txt(tb_x + 260, tb_y + 49, "auto: src/hardware.py", 10, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-bench-layout.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · WD={WD} SOFF={SOFF} MH={MH} SURF_WD={SURF_WD}")
