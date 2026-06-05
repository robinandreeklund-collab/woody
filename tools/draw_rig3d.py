#!/usr/bin/env python3
"""3D/perspektiv (isometrisk) riggritning — L-portal för 500 mm-brädor.

Horisontell matningsbas (2 transportband, cross-feed) + portal som straddlar
matningen: 2 oblika linjelaser+kamera-moduler från VAR SIN sida, överliggande
line-scan-ytkamera, 3 punktlaser (HG-C1400) längs brädan. Alla mått (x=mm) ifyllda,
datadrivna ur src.hardware. Komplett med BOM.

    python tools/draw_rig3d.py   # -> prototype-rig-3d.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

BENCH_L = 500
r = Rig(board_length_mm=BENCH_L, board_width_mm=150, board_thickness_mm=45)
OBL = r.oblique_angle_deg
WD = round(BENCH_L * r.profile_lens_mm / r.profile_cam.sensor_w_mm)        # ~474 mm
SOFF = round(WD * math.sin(math.radians(OBL)))                              # ~335 mm (y-offset)
MH = round(WD * math.cos(math.radians(OBL)))                               # ~335 mm (höjd)
SURF_WD = round(55 * BENCH_L / r.surface_cam.sensor_w_mm)                  # ~480 mm
RED_NM, GRN_NM = round(r.laser.wavelength_nm), round(r.laser_green.wavelength_nm)
SEP = 2 * SOFF                                                              # avstånd mellan modulerna
PL_X = [int(f * BENCH_L) for f in (0.1, 0.5, 0.9)]                          # 50 / 250 / 450
PLWD = 400                                                                  # HG-C1400 mätavstånd

W, H = 1660, 1230
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
BELT, SURFC, WOOD = "#444a52", "#7a3fb0", "#e9e1cf"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"; SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---- isometrisk projektion: x→nedåt-höger, y→nedåt-vänster, z→upp ----
S, OX, OY = 0.52, 740, 320
CA, SA = math.cos(math.radians(30)), math.sin(math.radians(30))
def P(x, y, z):
    return (OX + (x - y) * CA * S, OY + (x + y) * SA * S - z * S)

def txt(x, y, s, size=13, anchor="start", fill=INK, weight=400, fam=MONO, rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tr}>{esc(s)}</text>')
def ln(p1, p2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def poly(pts, fill, stroke=INK, sw=1.1, op=1):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def dot(p, rr, fill, stroke=INK, sw=0):
    add(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(p1, p2, stroke=INK, w=2.0):
    ln(p1, p2, stroke, w); a = math.atan2(p2[1] - p1[1], p2[0] - p1[0]); L = 11
    for s in (0.5, -0.5):
        ln(p2, (p2[0] - L * math.cos(a - s), p2[1] - L * math.sin(a - s)), stroke, w)
def box(x0, x1, y0, y1, z0, z1, top, sideL, sideR, stroke=INK, sw=1):
    poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], top, stroke, sw)       # topp z1
    poly([P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0)], sideL, stroke, sw)     # vänster y=y1
    poly([P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0), P(x1, y0, z0)], sideR, stroke, sw)     # höger x=x1

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): ln((gx, 0), (gx, H), GRID, 0.5)
for gy in range(0, H, 40): ln((0, gy), (W, gy), GRID, 0.5)
add('</g>')
add(f'<rect x="18" y="18" width="{W-36}" height="{H-36}" fill="none" stroke="{INK}" stroke-width="2"/>')
add(f'<rect x="26" y="26" width="{W-52}" height="{H-52}" fill="none" stroke="{MUTED}" stroke-width="0.8"/>')
txt(48, 66, "PROTOTYP-RIGG — 3D (L-portal, cross-feed, 500 mm)", 24, "start", INK, 700, SANS)
txt(48, 92, "Stativets ben står vid LÄNGD-ändarna (ur matningsbanan); tvärbalken åt andra hållet bär modulerna. "
            "2 oblika moduler (var sin sida), överliggande line-scan, 3 punktlaser (HG-C1400). Mått ur src/hardware.py.", 13.5, "start", MUTED, 400, SANS)
add(f'<line x1="48" y1="106" x2="{W-48}" y2="106" stroke="{INK}" stroke-width="1.5"/>')

# ===================== ISO-SCEN =====================
BX0, BX1 = 0, BENCH_L           # bräda x (längd)
BY0, BY1 = 0, 150               # bräda y (bredd/matning)
BZ = 45                         # tjocklek
MYL, MYR = 75 - SOFF, 75 + SOFF # moduler y (var sin sida om mitten y=75)
TOPZ = MH + 80                  # huvudbalkens höjd
FY0, FY1 = -130, 280            # matningsbanans utsträckning (y)
LEGX0, LEGX1 = -80, BENCH_L + 80  # ben vid LÄNGD-ändarna (ur matningsbanan)

# --- bas/golvplatta ---
box(LEGX0 - 30, LEGX1 + 30, FY0 - 30, FY1 + 30, -16, 0, "#e7e4da", "#cdc9bd", "#d6d2c6", "#b6b2a6", 1)
# --- 2 transportband (löper i y/matning vid x-ändarna) ---
for bx0, bx1, lab in [(0, 85, "BAND V"), (BENCH_L - 85, BENCH_L, "BAND H")]:
    box(bx0, bx1, FY0 - 8, FY1 + 8, 0, 10, BELT, "#33373d", "#3b4046", "#2b2f35", 1)
    txt(*P((bx0 + bx1) / 2, FY1 + 8, 11), lab, 9, "middle", "#dfe3e8", 700)
# --- matningspilar (i +y) ---
for ax in (150, 350):
    arrow(P(ax, FY0 + 20, 16), P(ax, FY1 - 20, 16), "#b06", 2.4)
txt(*P(250, FY1 + 32, 16), "matning (bredd 150 mm i sidled)", 11, "middle", "#b06", 700)
# --- bräda ---
box(BX0, BX1, BY0, BY1, 0, BZ, WOOD, "#d9cfb0", "#cdbf99", "#9a8c63", 1.2)
txt(*P(250, BY1 + 6, BZ + 4), "bräda 500 × 150 × 45 mm", 10.5, "middle", "#8a7d4e", 700)

# --- STATIV (vänt 90°): ben vid längd-ändarna, y=75, UR matningsbanan ---
for lx in (LEGX0, LEGX1):
    box(lx - 18, lx + 18, 75 - 18, 75 + 18, -16, 6, "#bfc3c8", "#a7acb1", "#b0b5ba", "#969ba0", 1)  # fotplatta
    box(lx - 14, lx + 14, 75 - 14, 75 + 14, 0, TOPZ, ALU, "#aeb3b8", "#b8bdc2", "#9aa0a6", 1)        # ben
# --- HUVUDBALK längs X (mellan benen, över brädan) ---
box(LEGX0 - 12, LEGX1 + 12, 75 - 12, 75 + 12, TOPZ - 22, TOPZ, ALU, "#aeb3b8", "#b8bdc2", "#9aa0a6", 1)
txt(*P(LEGX1 + 24, 75, TOPZ + 6), "HUVUDBALK (längs 500 mm)", 9, "start", MUTED, 700)
# --- TVÄRBALK åt andra hållet (i Y) där modulerna sitter ---
box(243, 257, MYL - 12, MYR + 12, TOPZ - 42, TOPZ - 20, ALU, "#a6abb0", "#b0b5ba", "#92979c", 1)
txt(*P(250, MYL - 24, TOPZ - 30), "TVÄRBALK (modulfäste, åt andra hållet)", 9, "middle", MUTED, 700)

# --- 2 oblika moduler på tvärbalkens ändar (var sin sida) + laserstrålar ---
mods = [(MYL, RED, f"RÖD {RED_NM}", "laser+mono V"), (MYR, GRN, f"GRÖN {GRN_NM}", "laser+mono H")]
for my, col, lab, sub in mods:
    ln(P(250, my, TOPZ - 31), P(250, my, MH), "#8a9099", 2.6)         # fäste från tvärbalk
    mp = P(250, my, MH)
    for ex in (BX0, BX1):
        ln(mp, P(ex, 75, BZ), col, 2.0, op=0.85)
    ln(P(BX0, 75, BZ + 0.4), P(BX1, 75, BZ + 0.4), col, 3)            # laserlinje på brädan
    poly([(mp[0]-34,mp[1]-30),(mp[0]+34,mp[1]-30),(mp[0]+34,mp[1]+8),(mp[0]-34,mp[1]+8)], "#fff", col, 1.6)
    poly([(mp[0]-34,mp[1]-30),(mp[0]+34,mp[1]-30),(mp[0]+34,mp[1]-18),(mp[0]-34,mp[1]-18)], col, col, 0)
    txt(mp[0], mp[1]-21, lab, 9, "middle", PAPER, 700, SANS)
    txt(mp[0], mp[1]-5, sub, 7.5, "middle", INK)

# --- 3 punktlaser hänger från HUVUDBALKEN längs X ---
for px in PL_X:
    ln(P(px, 75, TOPZ - 12), P(px, 75, PLWD), "#8a9099", 2)
    pt = P(px, 75, PLWD)
    poly([(pt[0]-11,pt[1]-9),(pt[0]+11,pt[1]-9),(pt[0]+11,pt[1]+9),(pt[0]-11,pt[1]+9)], "#f3e6fb", PURP, 1.4)
    txt(pt[0], pt[1]+3, "PL", 8, "middle", PURP, 700)
    ln(pt, P(px, 75, BZ), PURP, 1.5, "3 3"); dot(P(px, 75, BZ), 2.6, PURP)

# --- överliggande line-scan-ytkamera + RGB/NIR-strobe (på balkkorset) ---
cp = P(250, 75, SURF_WD)
ln(P(250, 75, TOPZ), cp, "#8a9099", 3)
poly([(cp[0]-52,cp[1]-16),(cp[0]+52,cp[1]-16),(cp[0]+52,cp[1]+12),(cp[0]-52,cp[1]+12)], "#efe6f7", SURFC, 1.6)
txt(cp[0], cp[1]-2, "YTKAMERA line-scan", 8.5, "middle", SURFC, 700, SANS)
txt(cp[0], cp[1]+9, "M72 + RGB/NIR-strobe", 7.5, "middle", INK)
for ex in (BX0, BX1):
    ln(cp, P(ex, 75, BZ), SURFC, 0.9, "3 3")

# --- Jetson ---
jp = P(BENCH_L + 150, FY1 - 20, 0)
add(f'<rect x="{jp[0]-2:.0f}" y="{jp[1]-30:.0f}" width="150" height="56" rx="6" fill="#e6efe6" stroke="{JET}" stroke-width="1.6"/>')
txt(jp[0]+73, jp[1]-8, "JETSON Orin Nano", 11, "middle", JET, 700, SANS)
txt(jp[0]+73, jp[1]+8, "edge-compute + U-Net", 8.5, "middle", MUTED)

# ===================== FÄRGFÖRKLARING (höger) =====================
lx, ly = 1235, 150
add(f'<rect x="{lx}" y="{ly}" width="372" height="360" rx="8" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
add(f'<rect x="{lx}" y="{ly}" width="372" height="30" rx="8" fill="{INK}"/>')
txt(lx+12, ly+20, "SENSORER / FÄRGFÖRKLARING", 12.5, "start", PAPER, 700, SANS)
leg = [
    (RED, "Linjelaser + kamera RÖD 650", "oblik modul, vänster sida"),
    (GRN, "Linjelaser + kamera GRÖN 520", "oblik modul, höger sida"),
    (PURP, "3× punktlaser HG-C1400 (V/C/H)", "absolut tjocklek, ankrar längsprofil"),
    (SURFC, "Ytkamera line-scan + RGB/NIR", "rakt ovan, yta + defekter"),
    (BELT, "2× transportband", "cross-feed, 50 mm/s"),
    (ALU, "Portal / mätram (T-spår)", "stativ som straddlar matningen"),
]
for i, (c, k, v) in enumerate(leg):
    ry = ly + 40 + i * 44
    add(f'<rect x="{lx+12}" y="{ry}" width="22" height="22" rx="4" fill="{c}" stroke="{INK}" stroke-width="0.8"/>')
    txt(lx+44, ry+11, k, 11, "start", INK, 700, SANS)
    txt(lx+44, ry+25, v, 9.5, "start", MUTED, 400, SANS)
add(f'<rect x="{lx+12}" y="{ly+312}" width="348" height="36" rx="5" fill="{PANEL}" stroke="{DIMC}" stroke-width="0.8"/>')
txt(lx+22, ly+327, "Ben vid längd-ändarna → fri matningsbana. Tvärbalken", 9.5, "start", INK, 700)
txt(lx+22, ly+340, "(åt andra hållet) bär modulerna — en på var sin sida.", 9.5, "start", INK, 700)

# ===================== MÅTT-PANEL (ifyllda x=mm) — nedre vänster =====================
mx, my0 = 70, 452
add(f'<rect x="{mx}" y="{my0}" width="392" height="346" rx="8" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
add(f'<rect x="{mx}" y="{my0}" width="392" height="30" rx="8" fill="{INK}"/>')
txt(mx+12, my0+20, "MÅTT — ifyllda x = mm", 13, "start", PAPER, 700, SANS)
dims = [
    ("Arbetsavstånd modul→bräda (oblik)", f"~{WD} mm"),
    ("Oblik vinkel (triangulering)", f"{OBL:.0f}°"),
    ("Modulhöjd över bräda", f"~{MH} mm"),
    ("Sidooffset (modul ut i sidled)", f"~{SOFF} mm"),
    ("Avstånd mellan modulerna", f"~{SEP} mm"),
    ("Laserlinje (längs brädan)", f"{BENCH_L} mm"),
    ("Brädbredd / matning", "150 mm"),
    ("Punktlaser-läge (V/C/H)", f"{PL_X[0]}/{PL_X[1]}/{PL_X[2]} mm"),
    ("Punktlaser mätavstånd (HG-C1400)", f"{PLWD} mm"),
    ("Ytkamera arbetsavstånd (M72)", f"~{SURF_WD} mm"),
    ("Stativben", "vid längd-ändarna (ur banan)"),
]
for i, (k, v) in enumerate(dims):
    ry = my0 + 38 + i * 28
    if i % 2: add(f'<rect x="{mx}" y="{ry-3}" width="392" height="28" fill="{PANEL}"/>')
    txt(mx+12, ry+14, k, 9.5, "start", MUTED, 700)
    txt(mx+380, ry+14, v, 10, "end", INK, 700)

# ===================== BOM (fasad) =====================
gT = 840
add(f'<g transform="translate(0,{gT})">')
add(f'<line x1="48" y1="0" x2="{W-48}" y2="0" stroke="{INK}" stroke-width="1.5"/>')
txt(48, 26, "KOMPONENTLISTA — fasad uppbyggnad (1 huvud)", 16, "start", INK, 700, SANS)
cols = [
    (60, JET, "FAS 1 · COMPUTE + VÄNSTER", [
        ("Jetson Orin Nano", "Super dev kit"), ("Profilkamera V", "MV-CS050-10UM (USB3)"),
        ("Objektiv", "8 mm C-mount + bp 650"), ("Linjelaser röd", "iadiy 650 nm 100 mW"),
        ("Alu-ram", "putta för hand")]),
    (460, GRN, "FAS 2 · HÖGER + MATNING", [
        ("Profilkamera H", "MV-CS050-10UM + bp 520"), ("Linjelaser grön", "iadiy 520 nm 50 mW"),
        ("Transportband", "2× 24 V, 50 mm/s"), ("Motorregulator", "24 V PWM"),
        ("Encoder", "mäthjul (RS422)")]),
    (860, SURFC, "FAS 3 · YTA + PUNKTLASER", [
        ("Ytkamera", "MindVision line-scan (NBASE-T)"), ("Objektiv M72", "8K 55–60 mm"),
        ("Belysning", "850 nm NIR + RGB strobe"), ("Punktlaser", "3× HG-C1400 + MCP3008"),
        ("LED-driver", "via ytkam strobe-ut")]),
    (1260, MUTED, "ANSLUTNING (Jetson)", [
        ("2 profilkam", "USB3"), ("Ytkamera", "NBASE-T → 1GbE direkt"),
        ("Punktlaser", "analog → MCP3008 (SPI)"), ("Encoder", "RS422→ytkam + GPIO"),
        ("Strobe", "ytkam 3 strobe-ut")]),
]
rowh = 28
for (cx, acc, title, rows) in cols:
    cw = 388
    add(f'<rect x="{cx}" y="44" width="{cw}" height="28" rx="4" fill="{acc}"/>')
    txt(cx+10, 63, title, 10.5, "start", PAPER, 700, SANS)
    add(f'<rect x="{cx}" y="72" width="{cw}" height="{rowh*len(rows)}" fill="#fff" stroke="{acc}" stroke-width="1"/>')
    for i, (k, v) in enumerate(rows):
        ry = 72 + i * rowh
        if i % 2: add(f'<rect x="{cx}" y="{ry}" width="{cw}" height="{rowh}" fill="{PANEL}"/>')
        txt(cx+10, ry+18, k, 9.5, "start", MUTED, 700)
        txt(cx+150, ry+18, v, 9, "start", INK)
add('</g>')

tb_x, tb_y, tb_w, tb_h = W - 470, H - 90, 420, 58
add(f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
add(f'<line x1="{tb_x}" y1="{tb_y+29}" x2="{tb_x+tb_w}" y2="{tb_y+29}" stroke="{INK}" stroke-width="1"/>')
add(f'<line x1="{tb_x+260}" y1="{tb_y}" x2="{tb_x+260}" y2="{tb_y+tb_h}" stroke="{INK}" stroke-width="1"/>')
txt(tb_x+10, tb_y+19, "VIRKESSKANNER — RIGG 3D 500 mm", 12, "start", INK, 700, SANS)
txt(tb_x+270, tb_y+19, "PROTO-3D", 12, "start", INK)
txt(tb_x+10, tb_y+47, "Isometrisk · ej skalenlig", 10, "start", MUTED)
txt(tb_x+270, tb_y+47, "auto: src/hardware.py", 10, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-rig-3d.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · WD={WD} MH={MH} SOFF={SOFF} SEP={SEP} PLWD={PLWD} SURF_WD={SURF_WD}")
