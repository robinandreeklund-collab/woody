#!/usr/bin/env python3
"""Monteringsritning (SVG) för ett MÄTHUVUD (laser + profilkamera) och hur 6 st
sitter på en T-spårs-aluminiumbalk. Alla mått/vinklar hämtas ur src.hardware.Rig.

    python tools/draw_head.py     # -> measurement-head-layout.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

r = Rig()
SEG = r.segments()
LASER_WD = round(r.laser_working_distance_mm)      # 951
PROF_WD = round(r.profile_wd_mm)                    # 1040 (lodrät höjd)
BASE = round(r.baseline_mm)                         # 600
TRI = r.tri_angle_deg                               # 30
SEGLEN = round(r.seg_len_mm)                        # 1098
OVL = round(r.overlap_mm)                           # 150
STEP = round(SEG[1][2] - SEG[0][2])                 # 948 (centrumavstånd)
N = r.n_lasers                                      # 6
DEPTH = r.depth_range_mm                            # 50 (±25)
FAN = r.laser.fan_angle_deg                         # 60
BOARD_L = round(r.board_length_mm)                  # 5400
SURF_WD = round(r.surface_wd_mm)                    # 951
SURF_FOV = round(r.surface_fov_per_cam_mm)          # 2700

W, H = 1680, 2180
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
C_LAS, C_PROF, C_SURF, ALU = "#e8542c", "#2f9e6e", "#2f6fb0", "#c3c6ca"
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
def poly(pts, fill="none", stroke=INK, sw=1.2, op=1):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
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

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(18, 18, W - 36, H - 36, "none", INK, 2); rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)
txt(48, 70, "MÄTHUVUD — LASER + PROFILKAMERA · MONTERING PÅ T-SPÅRSBALK", 25, "start", INK, 700, SANS)
txt(48, 96, f"{N} identiska huvuden på en styv aluminiumbalk (T-spår). Varje huvud täcker "
            f"ett {SEGLEN} mm-segment med {OVL} mm överlapp.", 14, "start", MUTED, 400, SANS)
line(48, 110, W - 48, 110, INK, 1.5)

def vlabel(x, y, tag, name):
    rect(x, y, 24, 20, INK, INK); txt(x + 12, y + 15, tag, 13, "middle", PAPER, 700, SANS)
    txt(x + 34, y + 15, name, 15, "start", INK, 700, SANS)

# ===================== VY A — MÄTHUVUD (ändvy, triangulering) =====================
gA = 130
add(f'<g transform="translate(0,{gA})">')
vlabel(48, 6, "A", "MÄTHUVUD — ändvy (triangulering, sett längs brädan)")
SC = 0.30                       # px/mm
bx = 360                        # laserns mätpunkt P (x)
yb = 470                        # brädans ovansida (y)
def UP(mm): return yb - mm * SC
cxC = bx + BASE * SC            # kamerans x (offset = baslinje)
# T-spårsbalk (tvärsnitt) längst upp – ovanför det HÖGSTA elementet (kameran 1040)
beam_y = UP(PROF_WD) - 90
rect(bx - 70, beam_y, 360, 50, ALU, "#8a9099", 1.4, 4)
txt(bx - 60, beam_y + 18, "T-SPÅRSBALK", 11, "start", MUTED, 700)
for sx in (bx - 40, bx + 40, bx + 120, bx + 220):   # T-spår
    rect(sx, beam_y + 36, 22, 10, PAPER, "#8a9099", 1)
# huvudets stomme: basplatta i balken -> lodrät laserpelare + utliggararm till kameran
bbot = beam_y + 50
rect(bx - 26, bbot - 4, 52, 10, "#d7d4cc", "#8a9099", 1.2)     # basplatta
line(bx, bbot, bx, UP(LASER_WD) - 4, "#7a7f86", 4)            # laserpelare (rakt ner)
line(bx, bbot, cxC, bbot, "#7a7f86", 4)                       # utliggararm (matningsled)
line(cxC, bbot, cxC, UP(PROF_WD) - 4, "#7a7f86", 4)           # kamerafäste
# laser (rakt ner) + solfjäder
rect(bx - 16, UP(LASER_WD) - 22, 32, 24, "#fde3da", C_LAS, 1.8, 3)
txt(bx, UP(LASER_WD) - 28, "LASER", 10, "middle", C_LAS, 700)
add(f'<polygon points="{bx-2:.1f},{UP(LASER_WD)+2:.1f} {bx+2:.1f},{UP(LASER_WD)+2:.1f} '
    f'{bx+9:.1f},{yb:.1f} {bx-9:.1f},{yb:.1f}" fill="{C_LAS}" opacity="0.5"/>')
circ(bx, yb, 3.5, C_LAS, C_LAS, 0)
# profilkamera (lutad TRI grader)
add(f'<g transform="rotate({TRI} {cxC:.1f} {UP(PROF_WD):.1f})">')
rect(cxC - 26, UP(PROF_WD) - 26, 52, 30, "#d8efe3", C_PROF, 1.8, 3)
txt(cxC, UP(PROF_WD) - 14, "PROFIL-", 10, "middle", C_PROF, 700)
txt(cxC, UP(PROF_WD) - 3, "KAMERA", 10, "middle", C_PROF, 700)
add('</g>')
line(cxC, UP(PROF_WD) + 4, bx, yb, C_PROF, 1.1, "4 3")        # siktlinje
# vinkel
line(bx, yb, bx, yb - 130, DIMC, 0.8, "3 3")
add(f'<path d="M {bx} {yb-80} A 80 80 0 0 1 {bx+80*math.sin(math.radians(TRI)):.1f} '
    f'{yb-80*math.cos(math.radians(TRI)):.1f}" fill="none" stroke="{C_PROF}" stroke-width="1.3"/>')
txt(bx + 30, yb - 92, f"{TRI:.0f}°", 13, "start", C_PROF, 700)
# bräda + djupområde
rect(bx - 90, yb, 300, 16, "#e9e1cf", "#b9a96f", 1.2)
txt(bx - 90, yb + 34, "bräda (matas vinkelrätt mot ritplanet)", 10, "start", "#8a7d4e")
line(bx - 70, UP(0), bx - 70, UP(DEPTH/2), C_PROF, 1); line(bx - 70, UP(0), bx - 70, UP(-DEPTH/2), C_PROF, 1)
txt(bx - 76, UP(0) + 4, f"±{DEPTH/2:.0f} mm", 10, "end", C_PROF)
# mått
vdim(UP(LASER_WD), yb, bx - 120, f"laser-WD {LASER_WD} mm")
vdim(UP(PROF_WD), yb, cxC + 150, f"kamera-höjd {PROF_WD} mm")
hdim(bx, cxC, yb + 70, f"baslinje {BASE} mm")
txt(bx - 70, yb + 96, f"laserlinje {SEGLEN} mm (60° solfjäder) löper LÄNGS brädan, in i ritplanet",
    11, "start", C_LAS, 700)
txt(cxC + 26, UP(PROF_WD) + 74, "mono + 650 nm filter", 9.5, "start", C_PROF)
# --- FÖRSLAG (ditt): +2 sidolaser som profilerar kanterna/vankanten ---
for sxL, edge in [(150, bx - 86), (792, bx + 206)]:
    lys = UP(870)
    rect(sxL - 15, lys - 12, 30, 24, "#fde3da", C_LAS, 1.6, 3)
    txt(sxL, lys + 3, "LASER", 8.5, "middle", C_LAS, 700)
    line(sxL, lys + 12, edge, yb, C_LAS, 3)               # röd sidostråle mot kanten
    circ(edge, yb, 4, C_LAS, C_LAS, 0)
txt(140, yb + 116, "FÖRSLAG (ditt): +2 sidolaser profilerar kanterna/vankanten → full tvärsnitt "
    "(topp + 2 sidor). Kräver egen mono-kamera per sida.", 11, "start", C_LAS, 700)
add('</g>')

# ===================== VY B — BALK MED 6 HUVUDEN (ovanifrån) =====================
gB = 760
add(f'<g transform="translate(0,{gB})">')
vlabel(48, 6, "B", f"BALK MED {N} MÄTHUVUDEN — ovanifrån (längs brädans {BOARD_L} mm)")
ax0, ax1 = 150, 1520
def AX(mm): return ax0 + mm * (ax1 - ax0) / BOARD_L
ybeam = 150
rect(AX(0), ybeam, AX(BOARD_L) - AX(0), 40, ALU, "#8a9099", 1.4, 4)   # balken
line(AX(0), ybeam + 20, AX(BOARD_L), ybeam + 20, "#8a9099", 0.8, "6 4")  # T-spår
txt(AX(0) + 6, ybeam - 8, f"aluminium T-spårsbalk ≈ {BOARD_L} mm", 11, "start", MUTED, 700)
# 6 huvuden (laser på balken) + kamera utliggande (offset i matningsled)
for k, (s, e, c) in enumerate(SEG):
    x = AX(c)
    rect(x - 16, ybeam - 4, 32, 48, "#d7d4cc", "#8a9099", 1.2, 2)    # huvudets fäste i spåret
    circ(x, ybeam + 64, 6, "#fff", C_LAS, 2)                          # laser
    line(x, ybeam + 44, x, ybeam + 64, "#7a7f86", 2)
    rect(x - 14, ybeam + 96, 28, 22, "#d8efe3", C_PROF, 1.6, 3)       # kamera (offset i matning)
    txt(x, ybeam + 111, f"M{k+1}", 10, "middle", C_PROF, 700)
    line(x, ybeam + 70, x, ybeam + 96, C_PROF, 0.8, "3 3")
    # segmentstäckning
    rect(AX(s), ybeam + 130, AX(e) - AX(s), 12, C_LAS, C_LAS, 0, 0, None, 0.16)
    line(AX(s), ybeam + 136, AX(e), ybeam + 136, C_LAS, 2)
txt(AX(0), ybeam + 64 - 16, "lasrar på balken", 10, "start", C_LAS, 700)
txt(AX(0), ybeam + 111 + 22, "profilkameror (utliggare, baslinje i matningsled)", 10, "start", C_PROF, 700)
# matningspil
arrow(AX(BOARD_L) + 24, ybeam + 70, AX(BOARD_L) + 24, ybeam + 118, "#b06", 2)
txt(AX(BOARD_L) + 30, ybeam + 96, "matning", 10, "start", "#b06", 700)
# 2 ytkameror
for i, cc in enumerate([1350, 4050]):
    x = AX(cc); rect(x - 30, ybeam - 56, 60, 26, "#dce8f4", C_SURF, 1.6, 3)
    txt(x, ybeam - 39, f"YTA {i+1}", 11, "middle", C_SURF, 700)
    line(x, ybeam - 30, x, ybeam, C_SURF, 0.8, "3 3")
txt(AX(0), ybeam - 56 - 8, f"2 ytkameror (färg) — var sin halva, FOV {SURF_FOV} mm", 11, "start", C_SURF, 700)
# mått
hdim(AX(SEG[0][2]), AX(SEG[1][2]), ybeam + 175, f"centrumavstånd {STEP} mm")
hdim(AX(SEG[0][0]), AX(SEG[0][1]), ybeam + 205, f"segment {SEGLEN} mm")
hdim(AX(0), AX(BOARD_L), ybeam + 235, f"{BOARD_L} mm (= brädlängd)")
add('</g>')

# ===================== VY C — T-SPÅR MONTERING (balktvärsnitt) =====================
gC = 1300
add(f'<g transform="translate(0,{gC})">')
vlabel(48, 6, "C", "T-SPÅRSMONTERING — balktvärsnitt (huvudet glider & låses var som helst)")
ex, ey = 220, 70
SCx = 1.7
bw_mm, bh_mm = 90, 180          # balkens tvärsnitt (90×180 för styvhet över 5,4 m)
bw, bh = bw_mm * SCx, bh_mm * SCx
rect(ex, ey, bw, bh, ALU, "#8a9099", 1.6, 4)
# T-spår på topp + sidor
def tslot(x, y, horiz):
    if horiz:
        rect(x - 10, y, 20, 8, PAPER, "#8a9099", 1.2); rect(x - 5, y + 8, 10, 10, PAPER, "#8a9099", 1.2)
    else:
        rect(x, y - 10, 8, 20, PAPER, "#8a9099", 1.2); rect(x + 8, y - 5, 10, 10, PAPER, "#8a9099", 1.2)
tslot(ex + bw / 2, ey, True)
tslot(ex + bw / 4, ey, True)
tslot(ex + 3 * bw / 4, ey, True)
tslot(ex, ey + bh / 2, False)
tslot(ex + bw - 8, ey + bh / 2, False)
# basplatta + T-mutter + bult ovanpå
rect(ex + bw / 2 - 60, ey - 18, 120, 16, "#d7d4cc", "#7a7f86", 1.4, 2)
txt(ex + bw / 2, ey - 24, "huvudets basplatta", 10, "middle", MUTED, 700)
for dx in (-36, 0, 36):
    circ(ex + bw / 2 + dx, ey - 10, 4, "#cfd2d6", "#5a5f66", 1.2)         # bultskalle
    line(ex + bw / 2 + dx, ey - 6, ex + bw / 2 + dx, ey + 14, "#5a5f66", 2)  # bult ner i spåret
    rect(ex + bw / 2 + dx - 9, ey + 8, 18, 8, "#b9bdc2", "#5a5f66", 1)    # T-mutter i spåret
txt(ex + bw / 2 + 70, ey + 12, "M8 bult + T-mutter (glider i spåret →", 11, "start", INK)
txt(ex + bw / 2 + 70, ey + 28, "steglös inställning av läge/överlapp)", 11, "start", MUTED)
hdim(ex, ex + bw, ey + bh + 20, f"{bw_mm} mm")
vdim(ey, ey + bh, ex - 24, f"{bh_mm} mm")
txt(ex + bw + 30, ey + bh - 24, "Styv balk (90×180) bär utliggarmomentet från", 11, "start", INK)
txt(ex + bw + 30, ey + bh - 8, f"profilkameran ({BASE} mm hävarm). Alt: andra balk för kamerorna.", 11, "start", MUTED)
add('</g>')

# ===================== SPEC =====================
gT = 1690
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5)
txt(48, 26, "MÄTHUVUD — SPECIFIKATION & MONTERING", 16, "start", INK, 700, SANS)
cols = [
    (60, C_LAS, "PER HUVUD (×%d)" % N, [
        ("Laser (topp)", "iadiy LM9R650H100L60 · 650 nm · 60°"),
        ("Laser-WD (lodrät)", f"{LASER_WD} mm  → linje {SEGLEN} mm"),
        ("Profilkamera", "MV-CS050-10UM MONO · lins 8 mm"),
        ("Filter", "650 nm bandpass (ser bara lasern)"),
        ("Kamerahöjd / vinkel", f"{PROF_WD} mm · {TRI:.0f}° från lod"),
        ("Baslinje laser↔kamera", f"{BASE} mm (i matningsled)"),
        ("Höjd-/lateraluppl.", "0,78 mm · 0,45 mm/px · djup ±25 mm"),
    ]),
    (600, C_PROF, "BALK & LAYOUT", [
        ("Balk", "alu T-spår ≈ 90×180 mm, ~5,5 m"),
        ("Antal huvuden", f"{N} (laser+profilkamera)"),
        ("Segment / överlapp", f"{SEGLEN} mm / {OVL} mm"),
        ("Centrumavstånd", f"{STEP} mm"),
        ("Infästning", "M8 bult + T-mutter (steglös)"),
        ("Ytkameror", f"2 (FOV {SURF_FOV} mm), WD {SURF_WD} mm"),
        ("Kalibrering", "laserlinje ⟂ matning, vinkel exakt"),
    ]),
    (1140, C_LAS, "FÖRSLAG: +2 SIDOLASER", [
        ("Syfte", "profilera kanterna + vankant"),
        ("Mäter", "vankantdjup, exakt bredd, kantspr."),
        ("Vinst", "full tvärsnitt: topp + 2 sidor"),
        ("Kostnad", "+2 laser & kamera / huvud"),
        ("Kalibrering", "3 laserplan → ett tvärsnitt"),
        ("Finns redan", "bredd/krok ur silhuetten"),
        ("Rek.", "värt om vankant ska mätas exakt"),
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
        txt(cx + 196, ry + 19, v, 11, "start", INK)
        line(cx + 190, ry + 6, cx + 190, ry + rowh - 6, GRID, 1)
add('</g>')

tb_x, tb_y, tb_w, tb_h = W - 470, H - 96, 420, 64
rect(tb_x, tb_y, tb_w, tb_h, "#fff", INK, 1.4)
line(tb_x, tb_y + 32, tb_x + tb_w, tb_y + 32, INK, 1); line(tb_x + 250, tb_y, tb_x + 250, tb_y + tb_h, INK, 1)
txt(tb_x + 10, tb_y + 20, "MULTISENSOR VIRKESSKANNER", 12, "start", INK, 700, SANS)
txt(tb_x + 260, tb_y + 20, "MÄTHUVUD-01", 12, "start", INK, 400)
txt(tb_x + 10, tb_y + 52, "Mått i mm · ej skalenlig", 10, "start", MUTED)
txt(tb_x + 260, tb_y + 52, "auto: src/hardware.py", 10, "start", MUTED)
add('</svg>')

dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "measurement-head-layout.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
