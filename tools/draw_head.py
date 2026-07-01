#!/usr/bin/env python3
"""Monteringsritning (SVG) för ett MÄTHUVUD med DUBBEL OBLIK, färgseparerad
triangulering: 2 laser+kamera-moduler per huvud (vänster RÖD 650 nm, höger GRÖN
520 nm) som svepar brädans tvärsnitt via matningen → topp + 2 sidor i 3D.
Alla mått/vinklar hämtas ur src.hardware.Rig.

    python tools/draw_head.py     # -> measurement-head-layout.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

r = Rig()
SEG = r.segments()
OBL = r.oblique_angle_deg                  # 45
STAND = round(r.module_standoff_mm)        # 1040 (längs oblik axel)
SOFF = round(r.module_side_offset_mm)      # 735
MH = round(r.module_height_mm)             # 735
TRI = r.tri_angle_deg                      # 30 (intern triangulering)
SEGLEN = round(r.seg_len_mm)               # 1098
OVL = round(r.overlap_mm)                  # 150
STEP = round(SEG[1][2] - SEG[0][2])        # 948
N = r.n_lasers                             # 6
DEPTH = r.depth_range_mm                   # 50
BW = round(r.board_width_mm)               # 150
BT = round(r.board_thickness_mm)           # 22
BOARD_L = round(r.board_length_mm)         # 5400
RED_NM = round(r.laser.wavelength_nm)      # 650
GRN_NM = round(r.laser_green.wavelength_nm)  # 520
SURF_FOV = round(r.surface_fov_per_cam_mm)
SURF_WD = round(r.surface_wd_mm)

W, H = 1700, 2240
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, C_SURF, ALU = "#e8542c", "#2f9e6e", "#2f6fb0", "#c3c6ca"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=13, anchor="start", fill=INK, weight=400, fam=MONO, rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tr}>{esc(s)}</text>')
def line(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
        f'stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')
def circ(x, y, rr, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.4):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2 - y1, x2 - x1); L = 9
    for s in (0.5, -0.5):
        line(x2, y2, x2 - L * math.cos(a - s), y2 - L * math.sin(a - s), stroke, w)
def hdim(x1, x2, y, text, fill=DIMC):
    line(x1, y - 6, x1, y + 6, fill, 1); line(x2, y - 6, x2, y + 6, fill, 1)
    arrow((x1 + x2) / 2, y, x1, y, fill, 1); arrow((x1 + x2) / 2, y, x2, y, fill, 1)
    add(f'<rect x="{(x1+x2)/2-len(text)*4:.1f}" y="{y-11:.1f}" width="{len(text)*8:.1f}" height="15" fill="{PAPER}" opacity="0.9"/>')
    txt((x1 + x2) / 2, y - 1, text, 12, "middle", fill)
def vdim(y1, y2, x, text, fill=DIMC):
    line(x - 6, y1, x + 6, y1, fill, 1); line(x - 6, y2, x + 6, y2, fill, 1)
    arrow(x, (y1 + y2) / 2, x, y1, fill, 1); arrow(x, (y1 + y2) / 2, x, y2, fill, 1)
    txt(x + 9, (y1 + y2) / 2 + 4, text, 12, "start", fill)
def dimlabel(x, y, text, fill, ang):
    txt(x, y, text, 11, "middle", fill, 700, MONO, rot=ang)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(18, 18, W - 36, H - 36, "none", INK, 2); rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)
txt(48, 70, "MÄTHUVUD — DUBBEL OBLIK FÄRGSEPARERAD TRIANGULERING (RÖD + GRÖN)", 24, "start", INK, 700, SANS)
txt(48, 96, f"{N} huvuden på en T-spårsram. Per huvud: 2 laser+mono-kamera-moduler "
            f"(V {RED_NM} nm / H {GRN_NM} nm). De svepar tvärsnittet via matningen → topp + 2 sidor i 3D.",
            14, "start", MUTED, 400, SANS)
line(48, 110, W - 48, 110, INK, 1.5)

def vlabel(x, y, tag, name):
    rect(x, y, 24, 20, INK, INK); txt(x + 12, y + 15, tag, 13, "middle", PAPER, 700, SANS)
    txt(x + 34, y + 15, name, 15, "start", INK, 700, SANS)

def module(mx, my, col, head, sub, ang):
    """ett laser+kamera-modulblock (lutat ang grader)."""
    add(f'<g transform="rotate({ang} {mx} {my})">')
    rect(mx - 58, my - 26, 116, 48, "#fff", col, 1.8, 5)
    rect(mx - 58, my - 26, 116, 17, col, col, 0, 5); rect(mx - 58, my - 17, 116, 8, col, col, 0)
    txt(mx, my - 14, head, 10.5, "middle", PAPER, 700, SANS)
    # laser + kamera bredvid varandra (intern baslinje)
    rect(mx - 48, my - 4, 40, 22, "#fde3da" if col == RED else "#d8efe3", col, 1.4, 3)
    txt(mx - 28, my + 10, "LASER", 8.5, "middle", col, 700)
    rect(mx + 6, my - 4, 46, 22, "#eef1f4", "#5a5f66", 1.4, 3)
    txt(mx + 29, my + 6, "MONO", 8, "middle", INK, 700)
    txt(mx + 29, my + 15, sub, 7.5, "middle", MUTED)
    add('</g>')

# ===================== VY A — MÄTHUVUD (ändvy, dubbel oblik) =====================
gA = 128
add(f'<g transform="translate(0,{gA})">')
vlabel(48, 6, "A", "MÄTHUVUD — ändvy (dubbel oblik, sett längs brädan)")
SC = 0.31
bx, yb = 470, 540
def UP(mm): return yb - mm * SC
bw, bt = BW * SC, BT * SC
bL, bR = bx - bw / 2, bx + bw / 2
# T-spårsram (två sidoposter + topp-balk)
tphy = UP(MH) - 60
rect(bx - 360, tphy, 720, 26, ALU, "#8a9099", 1.4, 4)                 # topp-balk (ram)
txt(bx - 354, tphy + 17, "T-SPÅRSRAM", 11, "start", MUTED, 700)
# moduler vänster (röd) + höger (grön), lutade OBL grader mot brädan
mxL, mxR = bx - SOFF * SC, bx + SOFF * SC
myL = myR = UP(MH)
rect(mxL - 8, tphy + 26, 16, myL - tphy - 26, "#9aa0a6", "#7a7f86", 1)  # post V
rect(mxR - 8, tphy + 26, 16, myR - tphy - 26, "#9aa0a6", "#7a7f86", 1)  # post H
module(mxL, myL, RED, f"RÖD {RED_NM} nm", f"+{RED_NM} filter", OBL)
module(mxR, myR, GRN, f"GRÖN {GRN_NM} nm", f"+{GRN_NM} filter", -OBL)
# laserstrålar (oblika) mot kanterna
line(mxL + 22 * math.cos(math.radians(OBL)), myL + 22, bL, yb, RED, 3)
line(mxR - 22 * math.cos(math.radians(OBL)), myR + 22, bR, yb, GRN, 3)
circ(bL, yb, 3.5, RED, RED, 0); circ(bR, yb, 3.5, GRN, GRN, 0)
# bräda (tvärsnitt) + matning in i planet
rect(bL, yb, bw, bt, "#e9e1cf", "#b9a96f", 1.4)
txt(bx, yb + bt + 18, f"bräda {BW}×{BT} mm (matas in i ritplanet)", 10, "middle", "#8a7d4e")
line(bL, UP(-DEPTH/2), bL - 14, UP(-DEPTH/2), DIMC, 1); line(bL, UP(DEPTH/2), bL - 14, UP(DEPTH/2), DIMC, 1)
txt(bL - 18, yb + 4, f"±{DEPTH/2:.0f}", 9, "end", MUTED)
# oblik vinkel (lod vs strålen) vid vänster modul
line(mxL, myL, mxL, myL + 150, DIMC, 0.8, "3 3")
add(f'<path d="M {mxL} {myL+90} A 90 90 0 0 0 {mxL-90*math.sin(math.radians(OBL)):.1f} '
    f'{myL+90*math.cos(math.radians(OBL)):.1f}" fill="none" stroke="{RED}" stroke-width="1.3"/>')
txt(mxL - 64, myL + 96, f"{OBL:.0f}°", 13, "start", RED, 700)
# mått: standoff längs strålen + sidooffset + höjd
midx, midy = (mxL + bL) / 2, (myL + yb) / 2
dimlabel(midx - 14, midy + 10, f"WD {STAND} mm", RED, math.degrees(math.atan2(yb - myL, bL - mxL)))
hdim(mxL, bx, UP(MH) - 36, f"sidooffset {SOFF} mm", DIMC)
vdim(UP(MH), yb, bx + bw / 2 + 240, f"modulhöjd {MH} mm")
txt(bx - 60, yb + bt + 42, f"intern triangulering {TRI:.0f}° (laser↔kamera i varje modul) · "
    f"laserlinje {SEGLEN} mm längs brädan", 11, "start", INK, 700)

# ---- ZOOM-inset: tvärsnittssvep (topp + 2 sidor) ----
ix, iy, iw, ih = 980, 250, 320, 150
rect(ix, iy, iw, ih, "#fff", INK, 1.4, 6)
txt(ix + 12, iy + 18, "ZOOM — tvärsnittssvep via matningen", 12, "start", INK, 700, SANS)
zbw, zbt = 200, 40
zx, zy = ix + iw / 2 - zbw / 2, iy + 64
rect(zx, zy, zbw, zbt, "#e9e1cf", "#b9a96f", 1.4)            # bräda förstorad
# röd sveper vänster sida + vänster halva av toppen
add(f'<path d="M {zx-2} {zy+zbt+2} Q {zx-2} {zy} {zx+zbw*0.42} {zy-3}" fill="none" stroke="{RED}" stroke-width="2.4"/>')
# grön sveper höger sida + höger halva av toppen
add(f'<path d="M {zx+zbw+2} {zy+zbt+2} Q {zx+zbw+2} {zy} {zx+zbw*0.58} {zy-3}" fill="none" stroke="{GRN}" stroke-width="2.4"/>')
txt(zx - 6, zy + zbt + 18, "RÖD: V-sida+topp", 8.5, "start", RED, 700)
txt(zx + zbw + 6, zy + zbt + 18, "GRÖN: H-sida+topp", 8.5, "end", GRN, 700)
for k in range(4):
    ax = zx + 30 + k * 45
    arrow(ax + 16, zy + zbt + 36, ax - 4, zy + zbt + 36, "#b06", 2)
txt(ix + iw / 2, iy + ih - 8, "matning → varje sida + topp registreras (encoder)", 9.5, "middle", MUTED)
add('</g>')

# ===================== VY B — RAM MED 6 HUVUDEN (ovanifrån) =====================
gB = 770
add(f'<g transform="translate(0,{gB})">')
vlabel(48, 6, "B", f"RAM MED {N} HUVUDEN — ovanifrån (2 sidoskenor längs {BOARD_L} mm)")
ax0, ax1 = 150, 1520
def AX(mm): return ax0 + mm * (ax1 - ax0) / BOARD_L
yR, yG, yb2 = 70, 250, 160
rect(AX(0), yR, AX(BOARD_L) - AX(0), 22, RED, RED, 0, 3, None, 0.20)     # röd skena (V)
rect(AX(0), yG, AX(BOARD_L) - AX(0), 22, GRN, GRN, 0, 3, None, 0.20)     # grön skena (H)
txt(AX(0), yR - 8, f"RÖD sidoskena ({RED_NM} nm) — {N} moduler", 11, "start", RED, 700)
txt(AX(0), yG + 38, f"GRÖN sidoskena ({GRN_NM} nm) — {N} moduler", 11, "start", GRN, 700)
rect(AX(0) - 8, yb2, AX(BOARD_L) - AX(0) + 16, 24, "#e9e1cf", "#b9a96f", 1.2)   # bräda mellan skenorna
txt(AX(0) + 6, yb2 + 16, f"BRÄDA {BOARD_L} mm", 10, "start", "#8a7d4e", 700)
for k, (s, e, c) in enumerate(SEG):
    x = AX(c)
    rect(x - 13, yR + 2, 26, 18, "#fde3da", RED, 1.4, 2); txt(x, yR + 15, f"R{k+1}", 9, "middle", RED, 700)
    rect(x - 13, yG + 2, 26, 18, "#d8efe3", GRN, 1.4, 2); txt(x, yG + 15, f"G{k+1}", 9, "middle", GRN, 700)
    line(x, yR + 20, x, yb2, RED, 0.7, "3 3"); line(x, yG, x, yb2 + 24, GRN, 0.7, "3 3")
arrow(AX(BOARD_L) + 24, yb2, AX(BOARD_L) + 24, yb2 + 24, "#b06", 2)
txt(AX(BOARD_L) + 30, yb2 + 16, "matning", 10, "start", "#b06", 700)
for i, cc in enumerate([1350, 4050]):
    x = AX(cc); rect(x - 30, yR - 52, 60, 24, "#dce8f4", C_SURF, 1.5, 3)
    txt(x, yR - 36, f"YTA {i+1}", 11, "middle", C_SURF, 700)
txt(AX(0), yR - 52 - 8, f"2 ytkameror (färg) — FOV {SURF_FOV} mm, WD {SURF_WD} mm", 11, "start", C_SURF, 700)
hdim(AX(SEG[0][2]), AX(SEG[1][2]), yG + 64, f"centrumavstånd {STEP} mm")
hdim(AX(SEG[0][0]), AX(SEG[0][1]), yG + 94, f"segment {SEGLEN} mm (överlapp {OVL})")
hdim(AX(0), AX(BOARD_L), yG + 124, f"{BOARD_L} mm")
add('</g>')

# ===================== VY C — T-SPÅR MONTERING =====================
gC = 1230
add(f'<g transform="translate(0,{gC})">')
vlabel(48, 6, "C", "T-SPÅRSMONTERING — modulen glider & låses i sidoskenan")
ex, ey, SCx = 240, 70, 1.7
bw_mm, bh_mm = 90, 120
bwp, bhp = bw_mm * SCx, bh_mm * SCx
rect(ex, ey, bwp, bhp, ALU, "#8a9099", 1.6, 4)
def tslot(x, y, horiz):
    if horiz: rect(x - 10, y, 20, 8, PAPER, "#8a9099", 1.2); rect(x - 5, y + 8, 10, 10, PAPER, "#8a9099", 1.2)
    else: rect(x, y - 10, 8, 20, PAPER, "#8a9099", 1.2); rect(x + 8, y - 5, 10, 10, PAPER, "#8a9099", 1.2)
tslot(ex + bwp / 4, ey, True); tslot(ex + bwp / 2, ey, True); tslot(ex + 3 * bwp / 4, ey, True)
tslot(ex, ey + bhp / 2, False); tslot(ex + bwp - 8, ey + bhp / 2, False)
rect(ex + bwp / 2 - 56, ey - 18, 112, 16, "#d7d4cc", "#7a7f86", 1.4, 2)
txt(ex + bwp / 2, ey - 24, "modulens basplatta", 10, "middle", MUTED, 700)
for dx in (-32, 0, 32):
    circ(ex + bwp / 2 + dx, ey - 10, 4, "#cfd2d6", "#5a5f66", 1.2)
    line(ex + bwp / 2 + dx, ey - 6, ex + bwp / 2 + dx, ey + 14, "#5a5f66", 2)
    rect(ex + bwp / 2 + dx - 9, ey + 8, 18, 8, "#b9bdc2", "#5a5f66", 1)
txt(ex + bwp / 2 + 66, ey + 12, "M8 bult + T-mutter → steglös", 11, "start", INK)
txt(ex + bwp / 2 + 66, ey + 28, "vinkel/läge per modul", 11, "start", MUTED)
hdim(ex, ex + bwp, ey + bhp + 20, f"{bw_mm} mm"); vdim(ey, ey + bhp, ex - 24, f"{bh_mm} mm")
txt(ex + bwp + 30, ey + bhp - 22, "En sidoskena (röd resp. grön) per sida av brädan.", 11, "start", INK)
txt(ex + bwp + 30, ey + bhp - 6, "Modulerna lutas ~45° och låses i T-spåret.", 11, "start", MUTED)
add('</g>')

# ===================== SPEC =====================
gT = 1620
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5)
txt(48, 26, "MÄTHUVUD — SPECIFIKATION (DUBBEL OBLIK, FÄRGSEPARERAD)", 16, "start", INK, 700, SANS)
cols = [
    (60, RED, "PER MODUL (2 / huvud)", [
        ("Laser V / H", f"RÖD {RED_NM} nm  /  GRÖN {GRN_NM} nm"),
        ("Kamera", "MV-CS050-10UM mono · lins 8 mm"),
        ("Filter", f"bandpass {RED_NM} resp. {GRN_NM} nm"),
        ("Oblik vinkel", f"{OBL:.0f}° från lod"),
        ("Intern triangulering", f"{TRI:.0f}° (laser↔kamera)"),
        ("Standoff / höjd", f"{STAND} / {MH} mm"),
        ("Sidooffset", f"{SOFF} mm"),
    ]),
    (600, GRN, "RAM & LAYOUT", [
        ("Konfig", "2 oblika moduler / huvud → topp+2 sidor"),
        ("Huvuden", f"{N} (× 2 moduler = {2*N} st)"),
        ("Skenor", "2 (V röd, H grön) T-spår längs brädan"),
        ("Segment / överlapp", f"{SEGLEN} / {OVL} mm"),
        ("Centrumavstånd", f"{STEP} mm"),
        ("Ytkameror", f"2 (FOV {SURF_FOV} mm)"),
        ("Djupområde", f"±{DEPTH/2:.0f} mm"),
    ]),
    (1140, C_SURF, "VARFÖR / VINST", [
        ("Topp+2 sidor", "svep via matning ger 3D-tvärsnitt"),
        ("Vankant/bredd", "mäts i 3D ur sidoprofilen"),
        ("Ocklusion", "motsatta håll fyller skuggor (~100%)"),
        ("Färgseparation", "ingen förväxling, full takt"),
        ("Mono+filter", "ser bara sin laser (brusfritt)"),
        ("Kalibrering", "oblik geometri → verkliga koord."),
        ("Undersida", "separat (skyms av bandet)"),
    ]),
]
rowh = 30
for (cx, acc, title, rows) in cols:
    cw = 500
    rect(cx, 44, cw, 30, acc, acc, 0, 4); txt(cx + 12, 64, title, 13, "start", PAPER, 700, SANS)
    rect(cx, 74, cw, rowh * len(rows), "#fff", acc, 1)
    for i, (k, v) in enumerate(rows):
        ry = 74 + i * rowh
        if i % 2: rect(cx, ry, cw, rowh, PANEL, "none", 0)
        txt(cx + 12, ry + 19, k, 11, "start", MUTED, 700)
        txt(cx + 188, ry + 19, v, 11, "start", INK)
        line(cx + 182, ry + 6, cx + 182, ry + rowh - 6, GRID, 1)
add('</g>')

tb_x, tb_y, tb_w, tb_h = W - 470, H - 96, 420, 64
rect(tb_x, tb_y, tb_w, tb_h, "#fff", INK, 1.4)
line(tb_x, tb_y + 32, tb_x + tb_w, tb_y + 32, INK, 1); line(tb_x + 250, tb_y, tb_x + 250, tb_y + tb_h, INK, 1)
txt(tb_x + 10, tb_y + 20, "MULTISENSOR VIRKESSKANNER", 12, "start", INK, 700, SANS)
txt(tb_x + 260, tb_y + 20, "MÄTHUVUD-02", 12, "start", INK, 400)
txt(tb_x + 10, tb_y + 52, "Mått i mm · ej skalenlig", 10, "start", MUTED)
txt(tb_x + 260, tb_y + 52, "auto: src/hardware.py", 10, "start", MUTED)
add('</svg>')

dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "measurement-head-layout.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
