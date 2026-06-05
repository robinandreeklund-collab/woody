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
r = Rig(board_length_mm=BENCH_L, board_width_mm=75, board_thickness_mm=45)
OBL = r.oblique_angle_deg
# FOV matchad till 500 mm med SAMMA optik (CS050 + 12 mm-lins) → arbetsavstånd ~710 mm
WD = round(BENCH_L * r.profile_lens_mm / r.profile_cam.sensor_w_mm)        # ~710 mm (slant)
SOFF = round(WD * math.sin(math.radians(OBL)))                              # ~355 mm sidooffset
MH = round(WD * math.cos(math.radians(OBL)))                                # ~615 mm vertikal modulhöjd
PLWD = 400                                                                  # HG-C1400 FAST mätavstånd
SURF_WD = 400           # ytkamera: ZLKC 20 mm M42 @ ~0,05× → FOV ~570 mm; = punktlaserplan (gemensam balk)
RED_NM, GRN_NM = round(r.laser.wavelength_nm), round(r.laser_green.wavelength_nm)
BW, BT = round(r.board_width_mm), round(r.board_thickness_mm)

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
txt(48, 96, "FAS 1: dubbel-oblikt huvud (röd 650 + grön 520) + 2 transportband (cross-feed, closed-loop via motorns Hall). "
            "FAS 2: line-scan-ytkamera + 3 punktlaser. Jetson Orin Nano.", 14, "start", MUTED, 400, SANS)
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
FW = BW * PXMM                                    # bredd i px (75 mm)
y0 = 210                                          # brädans överkant (bredd-axel)
# 2 transportband vid ändarna (löper i matningsled), sticker ut förbi brädan
beltw = 85 * PXMM
for bxmm, lab in [(42, "V"), (BENCH_L - 42, "H")]:
    bxp = AX(bxmm)
    rect(bxp - beltw / 2, y0 - 34, beltw, FW + 78, BELT, "#2b2f35", 1.2, 4)
    for ry in (y0 - 34, y0 + FW + 32): circ(bxp, ry, 5, "#9aa0a8", "#2b2f35", 1)
    txt(bxp, y0 + FW + 60, f"BAND {lab}", 9, "middle", "#dfe3e8", 700)
rect(AX(0), y0, AX(BENCH_L) - AX(0), FW, "#e9e1cf", "#b9a96f", 1.4)   # bräda 500 × 150
txt(AX(14), y0 + FW - 8, "bräda 500 × 75 mm", 11, "start", "#8a7d4e", 700)
sy = y0 + FW * 0.5                                # laserlinjen längs längden
line(AX(0) - 26, sy, AX(BENCH_L) + 26, sy, INK, 2.2)
txt(AX(BENCH_L) + 70, sy - 6, "laserlinje 500 mm", 10, "start", INK, 700)
txt(AX(BENCH_L) + 70, sy + 10, "(röd+grön oblik)", 9, "start", MUTED)
# huvudbalk (T-spår) + 3 punktlaser längs linjen
txt(AX(0.5 * BENCH_L), y0 - 68, "3 punktlaser (V/C/H längs 500 mm → ankrar längsprofil · FAS 2)", 9, "middle", PURP, 700)
rect(AX(-16), y0 - 60, AX(BENCH_L + 16) - AX(-16), 22, ALU, "#8a9099", 1.4, 3)
txt(AX(8), y0 - 45, "MÄTHUVUD-BALK (T-spår) — 2 oblika moduler", 9.5, "start", MUTED, 700)
for f in (0.1, 0.5, 0.9):
    x = AX(f * BENCH_L)
    rect(x - 12, y0 - 36, 24, 16, "#f3e6fb", PURP, 1.4, 2); txt(x, y0 - 24, "PL", 8, "middle", PURP, 700)
    line(x, y0 - 20, x, sy, PURP, 1.3, "2 3"); circ(x, sy, 2.4, PURP, PURP, 0)
# matning i sidled (bredd)
arrow(AX(BENCH_L * 0.32), y0 - 6, AX(BENCH_L * 0.32), y0 + FW + 6, "#b06", 2.2)
txt(AX(BENCH_L * 0.32) + 10, y0 + FW - 22, f"matning (bredd {BW} mm)", 10, "start", "#b06", 700)
# lägesåterkoppling via motorns Hall (ingen extern encoder)
txt(AX(BENCH_L * 0.58), y0 + 14, "läge: motorns Hall-signal + bakkant-anslag (ingen extern encoder)", 9, "start", MUTED, 700)
# Jetson
rect(AX(BENCH_L) + 64, y0 + FW - 8, 150, 60, "#e6efe6", JET, 1.6, 6)
txt(AX(BENCH_L) + 139, y0 + FW + 14, "JETSON Orin Nano", 11, "middle", JET, 700, SANS)
txt(AX(BENCH_L) + 139, y0 + FW + 30, "edge-compute + U-Net", 8.5, "middle", MUTED)
hdim(AX(0), AX(BENCH_L), y0 + FW + 96, "längd 500 mm (laserlinjens riktning)")
vdim(y0, y0 + FW, AX(0) - 55, f"{BW} mm")
add('</g>')

# ===================== VY B — HUVUD/STATIV ÄNDVY (NEDHÄNG) =====================
gB = 690
add(f'<g transform="translate(0,{gB})">')
vlabel(48, 6, "B", "MÄTHUVUD + STATIV — ändvy: varje sensor hänger med EGET NEDHÄNG → eget arbetsavstånd")
SC = 0.32; bx = 600; yb2 = 360
def UP(mm): return yb2 - mm * SC
BEAM_H = 760                                   # portalbalkens nederkant över brädytan (FAST)
bw, bt = BW * SC, BT * SC; bL, bR = bx - bw / 2, bx + bw / 2
mxL, mxR = bx - SOFF * SC, bx + SOFF * SC; myL = myR = UP(MH)
camY = UP(SURF_WD); plY = UP(PLWD); plx = bx + 52
beamY = UP(BEAM_H); beamB = beamY + 18; legX = SOFF * SC + 96; floorY = yb2 + bt + 96
# stativ: bas + två ben + portalbalk (mätram, FAST höjd)
rect(bx - legX - 40, floorY, 2 * (legX + 40), 16, "#bfc3c8", "#8a9099", 1.4, 3)
txt(bx, floorY + 12, "BAS / GOLVPLATTA", 9, "middle", MUTED, 700)
for lx in (bx - legX, bx + legX):
    rect(lx - 9, beamY, 18, floorY - beamY, ALU, "#8a9099", 1.4, 3)
rect(bx - legX - 9, beamY, 2 * legX + 18, 18, ALU, "#8a9099", 1.4, 3)
txt(bx, beamY + 13, "PORTALBALK / MÄTRAM (T-spår · FAST höjd)", 9.5, "middle", MUTED, 700)
vdim(beamY, floorY, bx - legX - 36, f"~{BEAM_H}")
# brädyta = referens (alla arbetsavstånd mäts härifrån)
line(bx - legX - 9, yb2, bx + legX + 9, yb2, DIMC, 0.9, "6 4")
txt(bx + legX + 13, yb2 + 3, "brädyta = 0", 8.5, "start", DIMC, 700)
# --- FAS 1: 2 oblika moduler (röd/grön) — KORTAST nedhäng, sitter högst (MH) ---
for mx, col, lab, ang in [(mxL, RED, f"RÖD {RED_NM}", OBL), (mxR, GRN, f"GRÖN {GRN_NM}", -OBL)]:
    line(mx, beamB, mx, myL - 15, "#8a9099", 3)              # nedhäng-strut (kort)
    add(f'<g transform="rotate({ang} {mx} {myL})">')
    rect(mx - 42, myL - 15, 84, 30, "#fff", col, 1.6, 4); rect(mx - 42, myL - 15, 84, 10, col, col, 0, 4)
    txt(mx, myL - 6, lab, 8.5, "middle", PAPER, 700, SANS); txt(mx, myL + 8, "laser+mono", 7, "middle", INK)
    add('</g>')
line(mxL + 13, myL + 14, bL, yb2, RED, 3); line(mxR - 13, myR + 14, bR, yb2, GRN, 3)
circ(bL, yb2, 3, RED, RED, 0); circ(bR, yb2, 3, GRN, GRN, 0)
txt(mxL - 4, myL + 58, f"{OBL:.0f}°", 11, "middle", RED, 700); txt(mxR + 4, myR + 58, f"{OBL:.0f}°", 11, "middle", GRN, 700)
vdim(beamB, myL - 15, mxL - 26, f"{BEAM_H-MH}")              # nedhäng oblik
# --- FAS 2: GEMENSAM balk på 400 mm — ytkamera (20 mm M42) + 3 punktlaser samma höjd ---
# ZLKC TM2004MPC 20 mm @ ~0,05× → FOV ~570 mm @ WD 400 mm = HG-C1400:s mätavstånd,
# så ytkamera och punktlaser hänger på SAMMA balk. Oblika huvuden sitter högre.
shY = UP(SURF_WD)
plx = bx + 66
for sxk in (bx - 28, plx + 4):                             # två nedhäng-struts till gemensam balk
    line(sxk, beamB, sxk, shY - 7, "#8a9099", 3)
rect(bx - 64, shY - 7, (plx + 4) - (bx - 64) + 12, 9, ALU, "#8a9099", 1.3, 3)   # gemensam balk
txt(bx, shY - 11, "GEMENSAM BALK 400 mm", 7.5, "middle", MUTED, 700)
rect(bx - 54, shY + 2, 108, 26, "#efe6f7", SURFC, 1.6, 5)  # ytkamera (center)
txt(bx, shY + 14, "YTKAMERA 4K färg", 8.5, "middle", SURFC, 700, SANS)
txt(bx, shY + 24, "20 mm M42 + vitt LED-ljus", 7.5, "middle", INK)
for sxmm in (-BW / 2, BW / 2):
    line(bx, shY + 28, bx + sxmm * SC, yb2, SURFC, 0.9, "3 3")
rect(plx - 13, shY + 3, 26, 18, "#f3e6fb", PURP, 1.4, 3); txt(plx, shY + 16, "PL", 8.5, "middle", PURP, 700)
line(plx, shY + 21, bx + 9, yb2, PURP, 1.4, "3 3"); circ(bx + 9, yb2, 2.6, PURP, PURP, 0)
txt(plx + 18, shY + 11, "3× HG-C1400", 8.5, "start", PURP, 700)
txt(plx + 18, shY + 22, "(längs brädan, in i bilden)", 7.5, "start", MUTED)
# arbetsavstånd (höger, med ledarstreck) — TVÅ plan: oblik 615 + gemensam 400
for (syv, x0, xd, lab, c) in [(myR, mxR + 42, 792, f"oblik {MH}", RED),
                              (shY, plx + 14, 876, f"yta+punkt {SURF_WD}", SURFC)]:
    line(x0, syv, xd, syv, c, 0.8, "3 3"); vdim(syv, yb2, xd, lab, c)
# bräda på transportband (ändstöd)
rect(bL, yb2, bw, bt, "#e9e1cf", "#b9a96f", 1.4); txt(bx, yb2 + bt + 15, f"bräda {BW}×{BT} mm", 9.5, "middle", "#8a7d4e")
rect(bL - 14, yb2 + bt, bw + 28, 14, BELT, "#2b2f35", 1.2, 3)
for rx in (bL - 6, bR + 6): circ(rx, yb2 + bt + 7, 5, "#9aa0a8", "#2b2f35", 1)
txt(bx, yb2 + bt + 36, "transportband (ändstöd, 24 V · 50 mm/s)", 8.5, "middle", MUTED)
hdim(mxL, mxR, beamB + 8, f"modulspann {2*SOFF}", DIMC)
# --- sammanfattningsruta: nedhäng vs arbetsavstånd ---
sx, sy, sw = 1000, 132, 562
rect(sx, sy, sw, 30, INK, INK, 0, 5)
txt(sx + 12, sy + 20, "TVÅ PLAN (mm) — ytkamera + punktlaser delar balk", 12, "start", PAPER, 700, SANS)
rect(sx, sy + 30, sw, 26, PANEL, INK, 1)
for t, hx in [("PLAN / SENSOR", sx + 12), ("NEDHÄNG (balk→)", sx + 290), ("ARB.AVSTÅND (→bräda)", sx + 420)]:
    txt(hx, sy + 47, t, 9, "start", INK, 700, SANS)
srows = [(RED, "Oblika huvuden RÖD/GRÖN (FAS 1)", f"{BEAM_H-MH}", f"{MH} vert · ~{WD} slant"),
         (SURFC, "Ytkamera 4K färg · 20 mm M42 (FAS 2)", f"{BEAM_H-SURF_WD}", f"{SURF_WD}  (FOV ~570)"),
         (PURP, "3× punktlaser HG-C1400 (FAS 2)", f"{BEAM_H-PLWD}", f"{PLWD}  (FAST, samma balk)")]
for i, (c, k, nh, wd) in enumerate(srows):
    ry = sy + 56 + i * 30
    if i % 2: rect(sx, ry, sw, 30, "#fff", "none", 0)
    rect(sx + 8, ry + 9, 12, 12, c, c, 0, 2)
    txt(sx + 28, ry + 20, k, 9.5, "start", INK, 700)
    txt(sx + 290, ry + 20, nh, 11, "start", MUTED, 700)
    txt(sx + 420, ry + 20, wd, 10, "start", INK, 700)
rect(sx, sy + 146, sw, 3, INK, INK, 0)
for i, ln_ in enumerate([
        "ZLKC 20 mm-linsen @ ~0,05× → FOV ~570 mm @ WD ~400 mm = punktlaserns",
        "plan → ytkamera + 3 punktlaser på SAMMA balk (inom linsens spec).",
        "Oblika huvuden sitter högre (615 mm). NIR = separat modul senare."]):
    txt(sx + 4, sy + 168 + i * 16, ln_, 9.5, "start", MUTED, 400, SANS)
add('</g>')

# ===================== BOM =====================
gT = 1180
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5); txt(48, 26, "KOMPONENTLISTA — fasad uppbyggnad (1 huvud)", 16, "start", INK, 700, SANS)
cols = [
    (60, JET, "FAS 1 · COMPUTE + RÖD MODUL", [
        ("Jetson Orin Nano", "Super dev kit (edge+U-Net)"),
        ("Profilkamera RÖD", "MV-CS050-10UM mono (USB3)"),
        ("Objektiv 12 mm", "MVL-MF1228M + bandpass 650"),
        ("Linjelaser röd", "iadiy 650 nm 100 mW (oblik 30°)"),
        ("Alu-portalram", "T-spår, fast höjd ~760 mm"),
    ]),
    (430, GRN, "FAS 1 · GRÖN MODUL + MATNING", [
        ("Profilkamera GRÖN", "MV-CS050-10UM + bandpass 520"),
        ("Linjelaser grön", "iadiy 520 nm 50 mW (oblik 30°)"),
        ("Transportband ×2", "24 V, 50 mm/s (V/H, cross-feed)"),
        ("Motorstyrning ×2", "Pololu Jrk G2 (frekvens-FB)"),
        ("Lägesgivare", "motorns Hall-signal + anslag"),
    ]),
    (800, SURFC, "FAS 2 · YTA + PUNKTLASER", [
        ("Ytkamera", "Huateng 4K färg (M42, GigE)"),
        ("Objektiv M42", "ZLKC TM2004MPC 20 mm (Φ30)"),
        ("Belysning", "vitt LED-linjeljus (1 pass)"),
        ("Punktlaser ×3", "HG-C1400 (400 mm) + MCP3008"),
        ("NIR (valfri)", "mono-NIR + 850 nm, senare"),
    ]),
    (1170, MUTED, "ANSLUTNING (Jetson)", [
        ("2 profilkam", "USB3 (~307 MB/s/st)"),
        ("Ytkamera", "GigE → 1GbE direkt"),
        ("Punktlaser", "analog → MCP3008 (SPI)"),
        ("Motorstyrning", "I²C ↔ 2× Jrk G2"),
        ("Belysning", "vitt ljus (kont./flash)"),
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
