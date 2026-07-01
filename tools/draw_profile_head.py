#!/usr/bin/env python3
"""Monteringsritning — profilhuvud i DUBBEL-OBLIK mätrigg.
Huvudvy: mätprincipen i tvärsnitt — RÖD modul (vänster) + GRÖN modul (höger),
BÅDA skjuter snett INÅT (laser+kamera oblikt) → topp + respektive kant/vankant,
och fyller varandras skuggor. Inset: ETT huvud (kamera+objektiv+filter+laser på
beslag, oblikt) + optisk stack. Komponentlista, noter, ritningshuvud.

  python tools/draw_profile_head.py   # -> profile-head.svg
Grön modul identisk: 520-laser + 525-filter.
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WD, TRI, OBL, FAN = 710.0, 20.0, 30.0, 45.0          # slant-WD, triangulering, obliquity, Powell-fläkt
BW, BT = 75.0, 45.0                                   # brädans tvärsnitt (bredd × tjocklek)
CAM_L, CAM_W = 29.0, 29.0
LENS_L, LENS_D = 40.0, 32.0
FILT_L, FILT_D = 6.0, 32.0
LAS_L, LAS_D  = 99.0, 18.0
BASE = round(2 * WD * math.sin(math.radians(TRI / 2)))

INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#e4e2da"
RED, GRN, BLUE, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6"
ALU, ALU2, WOOD, WOOD2, GOLD, BLACK = "#c3c6ca", "#aab0b6", "#e9e1cf", "#ddd2b4", "#b9a96f", "#2b2f35"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=12, anchor="start", fill=INK, weight=400, fam=SANS, rot=None):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tr}>{esc(s)}</text>')
def line(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')
def circ(x, y, r, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def poly(pts, fill="none", stroke=INK, sw=1.2, op=1, dash=None):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.4, head=8):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2 - y1, x2 - x1)
    for s in (0.42, -0.42): line(x2, y2, x2 - head * math.cos(a - s), y2 - head * math.sin(a - s), stroke, w)
def dim(x1, y1, x2, y2, label, off=0, fill=DIMC, size=11):
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
    ax1, ay1 = x1 + nx*off, y1 + ny*off; ax2, ay2 = x2 + nx*off, y2 + ny*off
    line(x1, y1, ax1, ay1, fill, 0.7); line(x2, y2, ax2, ay2, fill, 0.7)
    arrow(ax1, ay1, ax2, ay2, fill, 1); arrow(ax2, ay2, ax1, ay1, fill, 1)
    mx, my = (ax1+ax2)/2, (ay1+ay2)/2
    rot = math.degrees(math.atan2(dy, dx)); rot = rot+180 if rot > 90 or rot < -90 else rot
    rect(mx-len(label)*size*0.30, my-size*0.7, len(label)*size*0.6, size*1.25, PAPER, "none", 0, 0, op=0.92)
    txt(mx, my+size*0.34, label, size, "middle", fill, 700, MONO, rot)
def balloon(x, y, n, col=INK):
    circ(x, y, 12, "#fff", col, 1.6); txt(x, y+4.5, str(n), 12.5, "middle", col, 700, SANS)
def leader(x1, y1, x2, y2, col=MUTED):
    line(x1, y1, x2, y2, col, 1); circ(x2, y2, 2.2, col, col, 0)
def panel(x, y, w, h, title, acc):
    rect(x, y, w, h, "#fff", acc, 1.4, 9); rect(x, y, w, 30, acc, acc, 0, 9); rect(x, y+18, w, 12, acc, acc, 0)
    txt(x+14, y+20, title, 13, "start", "#fff", 700, SANS)

W, H = 1740, 1180
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.6">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W-32, H-32, "none", INK, 2); rect(24, 24, W-48, H-48, "none", MUTED, 0.8)
txt(44, 60, "PROFILHUVUD — DUBBEL-OBLIK", 25, "start", INK, 700, SANS)
txt(44, 86, "Två moduler skjuter snett INÅT från motsatta håll → topp + BÅDA kanter/vankant, och fyller varandras skuggor. "
            "RÖD 650 (vänster) · GRÖN 520 (höger). Lasern sitter oblik — inte lodrät.", 13.5, "start", MUTED, 400, SANS)
line(44, 100, W-44, 100, INK, 1.4)

# =================================================================== HUVUDVY: DUBBEL-OBLIK TVÄRSNITT
panel(44, 118, 700, 740, "MÄTPRINCIP — tvärsnitt (varför två oblika håll)", INK)
ms = 4.0
mcx, topY = 394, 560                       # brädans topp-mitt
bx0, bx1 = mcx - BW*ms/2, mcx + BW*ms/2     # bredd-kanter
botY = topY + BT*ms                          # underkant (på band)
wane = 22*ms                                  # vankant-fasning på topphörnen
# bräda med vankant (fasade topphörn) + en kvist-bula på toppen
board = [(bx0, topY+wane), (bx0+wane, topY), (mcx-26, topY), (mcx-12, topY-12), (mcx+12, topY-12), (mcx+26, topY),
         (bx1-wane, topY), (bx1, topY+wane), (bx1, botY), (bx0, botY)]
poly(board, WOOD, GOLD, 1.8)
# ådring
for yy in range(int(topY)+18, int(botY)-6, 16): line(bx0+6, yy, bx1-6, yy, WOOD2, 1)
txt(mcx, botY-10, f"BRÄDA  {BW:.0f} × {BT:.0f} mm (tvärsnitt)", 11, "middle", "#8a7d4e", 700)
rect(bx0-20, botY, (bx1-bx0)+40, 16, BLACK, "#1c1f24", 1.2, 3); txt(mcx, botY+34, "transportband", 9.5, "middle", MUTED, 700)
# vankant-etiketter
txt(bx0+10, topY+wane+22, "vankant V", 9, "start", GOLD, 700)
txt(bx1-10, topY+wane+22, "vankant H", 9, "end", GOLD, 700)
txt(mcx, topY-20, "kvist/bula", 8.5, "middle", MUTED, 700)

# lodrät referensvy (missar vankantens underkurva)
line(mcx+90, topY-150, mcx+90, topY-4, DIMC, 1, "4 4"); arrow(mcx+90, topY-30, mcx+90, topY-6, DIMC, 1)
txt(mcx+96, topY-120, "en LOD-vy ser bara", 8.5, "start", DIMC, 700)
txt(mcx+96, topY-107, "toppen — missar", 8.5, "start", DIMC, 700)
txt(mcx+96, topY-94, "vankantens kurva", 8.5, "start", DIMC, 700)

# ---- RÖD modul (vänster, oblik) → ser topp + VÄNSTER vankant ----
Rlx, Rly = 120, 250
# laser (solid) grazar vänster vankant + topp ; kamera (streckad) bredvid
line(Rlx, Rly, bx0+8, topY+wane-6, RED, 2.6)             # laser-blad mot vänster vankant
line(Rlx, Rly, mcx-30, topY-2, RED, 1.4, op=0.55)        # laser även över toppen
line(Rlx+40, Rly-26, bx0+18, topY+wane-12, RED, 1.2, "4 3")   # kamerasikt (streckad)
poly([(Rlx-36,Rly-16),(Rlx+36,Rly-16),(Rlx+36,Rly+16),(Rlx-36,Rly+16)], "#fde9e3", RED, 1.6)
txt(Rlx, Rly-2, "RÖD modul", 10, "middle", RED, 700, SANS); txt(Rlx, Rly+12, "650 nm · oblik", 8, "middle", INK)
txt(Rlx-6, Rly+58, "ser TOPP +", 9.5, "start", RED, 700); txt(Rlx-6, Rly+72, "VÄNSTER vankant", 9.5, "start", RED, 700)
# obliquity-vinkel mot lod vid vänster kant
line(bx0+8, topY+wane-6, bx0+8, topY+wane-90, DIMC, 0.7, "3 3")
txt(bx0+30, topY-44, f"{OBL:.0f}°", 11, "middle", RED, 700, MONO)

# ---- GRÖN modul (höger, oblik) → ser topp + HÖGER vankant ----
Grx, Gry = 668, 250
line(Grx, Gry, bx1-8, topY+wane-6, GRN, 2.6)
line(Grx, Gry, mcx+30, topY-2, GRN, 1.4, op=0.55)
line(Grx-40, Gry-26, bx1-18, topY+wane-12, GRN, 1.2, "4 3")
poly([(Grx-38,Gry-16),(Grx+38,Gry-16),(Grx+38,Gry+16),(Grx-38,Gry+16)], "#e3f3ea", GRN, 1.6)
txt(Grx, Gry-2, "GRÖN modul", 10, "middle", GRN, 700, SANS); txt(Grx, Gry+12, "520 nm · oblik", 8, "middle", INK)
txt(Grx+6, Gry+58, "ser TOPP +", 9.5, "end", GRN, 700); txt(Grx+6, Gry+72, "HÖGER vankant", 9.5, "end", GRN, 700)
line(bx1-8, topY+wane-6, bx1-8, topY+wane-90, DIMC, 0.7, "3 3")
txt(bx1-30, topY-44, f"{OBL:.0f}°", 11, "middle", GRN, 700, MONO)

# skugga bakom kvisten: röd skuggad höger om bulan, grön fyller (och tvärtom)
txt(mcx, botY+58, "Oblikt = man ser 'runt' kanten. Två håll → topp + båda vankanter,", 10, "middle", INK, 400)
txt(mcx, botY+74, "och bakom kvist/bula fyller den ena modulen den andras skugga.", 10, "middle", INK, 400)
# legend solid/streckad
line(60, 836, 92, 836, INK, 2.4); txt(98, 840, "laserblad", 9, "start", MUTED, 700)
line(230, 836, 262, 836, INK, 1.4, "4 3"); txt(268, 840, "kamerasikt (triangulering)", 9, "start", MUTED, 700)

# =================================================================== INSET: ETT HUVUD (assembly)
hx, hy, hw, hh = 762, 118, 458, 392
panel(hx, hy, hw, hh, "ETT HUVUD — kamera + laser, BÅDA oblika", BLUE)
# liten bräda nere till höger; huvudet uppe till vänster, skjuter snett ned-höger
Tx, Ty = hx+330, hy+330
b2 = 70
rect(Tx-b2, Ty, b2*2, 26, WOOD, GOLD, 1.4); rect(Tx-b2-8, Ty+26, b2*2+16, 10, BLACK, "#1c1f24", 1, 2)
txt(Tx, Ty+20, "bräda", 8.5, "middle", "#8a7d4e", 700)
# kamera-arm (oblik ~25°) och laser-arm (oblik ~45°), båda från övre vänster
def aim(px, py):
    d = math.hypot(Tx-px, Ty-py); return (Tx-px)/d, (Ty-py)/d
camx, camy = hx+70, hy+120
lasx, lasy = hx+40, hy+210
ucx, ucy = aim(camx, camy); ulx, uly = aim(lasx, lasy)
# beslag (förbinder kamera-bak och laser-bak) + portalfäste
cbx, cby = camx-ucx*70, camy-ucy*70; lbx, lby = lasx-ulx*40, lasy-uly*40
line(cbx, cby, lbx, lby, ALU, 7)
line((cbx+lbx)/2, (cby+lby)/2, (cbx+lbx)/2, hy+44, ALU2, 5)
rect(hx+50, hy+38, 200, 14, ALU, ALU2, 1.2, 2); txt(hx+60, hy+48, "portalbalk", 8.5, "start", MUTED, 700)
# laserblad (oblik) + kamerasikt (oblik), konvergerar på brädan
line(lasx, lasy, Tx, Ty, RED, 2.6); circ(Tx, Ty, 3.4, RED, "#a8331a", 1)
line(camx, camy, Tx, Ty, "#8a9099", 1.4, "5 4")
# kamera-stack (liten, roterad) + laser (liten, roterad)
ang = math.degrees(math.atan2(ucy, ucx))
add(f'<g transform="translate({camx:.1f},{camy:.1f}) rotate({ang:.1f})">')
rect(-FILT_L*0.7, -FILT_D*0.35, FILT_L*0.7, FILT_D*0.7, "#f6d9cf", RED, 1.2)
rect(-(FILT_L+LENS_L)*0.7, -LENS_D*0.35, LENS_L*0.7, LENS_D*0.7, "#d9dde1", "#9aa0a6", 1.2, 2)
rect(-(FILT_L+LENS_L+CAM_L)*0.7, -CAM_W*0.35, CAM_L*0.7, CAM_W*0.7, "#e9edf1", "#7e8489", 1.4, 2)
add('</g>')
anl = math.degrees(math.atan2(uly, ulx))
add(f'<g transform="translate({lasx:.1f},{lasy:.1f}) rotate({anl:.1f})">')
rect(-LAS_L*0.7, -LAS_D*0.45, LAS_L*0.7, LAS_D*0.9, "#d7b7b0", "#9a5a52", 1.2, 2)
add('</g>')
txt(camx+18, camy-8, "kamera+lins+filter (oblik)", 8.5, "start", INK, 700)
txt(lasx-6, lasy+24, "linjelaser (oblik)", 8.5, "start", RED, 700)
# mått
dim(camx, camy, Tx, Ty, f"WD {WD:.0f}", 30, INK, 10)
line(Tx, Ty, camx, camy, DIMC, 0.5); line(Tx, Ty, lasx, lasy, DIMC, 0.5)
add(f'<path d="M {Tx-ucx*46:.1f} {Ty-ucy*46:.1f} A 46 46 0 0 1 {Tx-ulx*46:.1f} {Ty-uly*46:.1f}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
txt(Tx-44, Ty-54, f"θ={TRI:.0f}°", 11, "middle", INK, 700, MONO)
txt(hx+14, hy+hh-14, f"Baslinje kamera↔laser ~{BASE} mm · obliquity {OBL:.0f}° · θ {TRI:.0f}° · ej skalenlig", 9, "start", MUTED, 400)

# =================================================================== INSET: DETALJ optisk stack
dax, day, daw, dah = 762, 524, 458, 294
panel(dax, day, daw, dah, "DETALJ — optisk stack  (2,4×)", BLUE)
sc = 2.4; scy = day+150; x = dax+58
cw, cl = CAM_W*sc, CAM_L*sc; ll, ld = LENS_L*sc, LENS_D*sc; fl, fd = FILT_L*sc, FILT_D*sc
rect(x, scy-cw/2, cl, cw, "#e9edf1", "#7e8489", 1.8, 3)
rect(x-16, scy-16, 16, 12, BLACK, "#1c1f24", 1.2, 2); txt(x-8, scy-21, "USB3", 7.5, "middle", MUTED, 700)
rect(x-16, scy+4, 16, 11, "#caa64a", "#8a6510", 1.2, 2); txt(x-8, scy+25, "5V/IO", 7.5, "middle", MUTED, 700)
txt(x+cl/2, scy+cw/2+17, "① MV-CS050-10UM · C-mount", 9, "middle", INK, 700)
x += cl; rect(x, scy-12, 9, 24, ALU2, "#8a9099", 1.4); x += 9
rect(x, scy-ld/2, ll, ld, "#d9dde1", "#9aa0a6", 1.8, 3)
for gx in range(0, int(ll)-12, 15): line(x+gx+8, scy-ld/2, x+gx+8, scy+ld/2, "#c2c7cc", 0.8)
txt(x+ll/2, scy-ld/2-9, "② MVL-MF1228M-8MP · 12 mm", 9, "middle", INK, 700)
txt(x+ll/2, scy+ld/2+17, "fokus + iris F2.8–16", 8, "middle", MUTED, 700)
x += ll; txt(x+1, scy-ld/2-24, "M30.5×0.5", 8.5, "middle", BLUE, 700)
rect(x, scy-fd/2, fl, fd, "#f6d9cf", RED, 1.9, 2)
txt(x+fl+8, scy-2, "③ FS03-BP650", 9.5, "start", RED, 700); txt(x+fl+8, scy+12, "650 nm BP", 8, "start", MUTED, 700)
arrow(x+fl+78, scy+44, x+fl+8, scy+6, RED, 1.5); txt(x+fl+24, scy+56, "laser in", 8.5, "start", RED, 700)
txt(dax+16, day+dah-13, "Filtret på objektivets front → mono-kameran ser i princip BARA laserlinjen.", 8.7, "start", MUTED, 400)

# =================================================================== HÖGER KOLUMN
CX = 1244; CW = 452
panel(CX, 118, CW, 244, "KOMPONENTER (per huvud)", INK)
items = [
    (1, INK, "Profilkamera", "Hikrobot MV-CS050-10UM", "mono, USB3, 2/3″ IMX264, C-mount"),
    (2, "#7e8489", "Objektiv", "HIKROBOT MVL-MF1228M-8MP", "12 mm F2.8, C-mount, M30.5-gänga"),
    (3, RED, "Bandpassfilter", "FS03-BP650  (grön: BP525)", "650 nm, FWHM 40, M30.5×0.5"),
    (4, RED, "Linjelaser", "MZLaser AJPWHF5638", "638 nm Powell, 45°, 100 mW, 5 V"),
    (5, MUTED, "Vinkelbeslag", "alu — låser kamera+laser oblikt", "obliquity 30° · triangulering 30°"),
]
yy = 156
for (n, col, role, prod, spec) in items:
    balloon(CX+22, yy+8, n, col)
    txt(CX+44, yy+2, role, 11.5, "start", MUTED, 700); txt(CX+44, yy+18, prod, 11.5, "start", INK, 700)
    txt(CX+44, yy+32, spec, 9.5, "start", MUTED, 400); yy += 42

panel(CX, 376, CW, 132, "MÅTT & GEOMETRI", BLUE)
dims = [("Arbetsavstånd WD (slant)", f"{WD:.0f} mm"), ("Obliquity (laser+kamera fr. lod)", f"{OBL:.0f}°"),
        ("Trianguleringsvinkel θ", f"{TRI:.0f}°"), ("Baslinje kamera↔laser", f"{BASE} mm"),
        ("Laser Powell-fläkt → linje", f"{FAN:.0f}° → 500 mm")]
yy = 412
for k, v in dims:
    txt(CX+16, yy, k, 10.5, "start", INK); txt(CX+CW-16, yy, v, 11, "end", INK, 700, MONO); yy += 19

panel(CX, 522, CW, 296, "NOTER", INK)
notes = [
    "A.  Lasern sitter OBLIKT (~30° fr. lod) och skjuter INÅT → träffar topp + den",
    "     närmaste kanten/vankanten. En lodrät laser hade bara sett toppen.",
    "B.  Två moduler från motsatta håll = topp + BÅDA vankanter, och den ena fyller",
    "     den andras skugga bakom kvist/bula. Det är hela syftet med dubbel-oblik.",
    "C.  Kamera + laser i samma huvud, vinklade mot varandra (θ = 30°) → höjd via",
    "     triangulering. Rikta så bägge KONVERGERAR på samma laserlinje vid WD 710.",
    "D.  Skärpa: laserlinjen skarp vid 710 mm; blända F8–F11 för djup (alt. Scheimpflug).",
    "E.  Filter FS03-BP650 (M30.5) på objektivfronten. Laser Klass 3B → glasögon + kåpa.",
    "F.  GRÖN modul = spegel: 520-laser + 525-filter (FS03-BP525). Mått i mm.",
]
yy = 550
for ln_ in notes:
    txt(CX+14, yy, ln_, 9.5, "start", INK, 400); yy += 18 if not ln_.startswith("     ") else 15

tbx, tby, tbw, tbh = CX, 832, CW, 314
rect(tbx, tby, tbw, 168, "#fff", INK, 1.6)
line(tbx, tby+92, tbx+tbw, tby+92, INK, 1); line(tbx+tbw*0.56, tby, tbx+tbw*0.56, tby+92, INK, 1); line(tbx, tby+46, tbx+tbw*0.56, tby+46, INK, 0.8)
txt(tbx+14, tby+22, "VIRKESSKANNER — PROFILHUVUD", 12.5, "start", INK, 700)
txt(tbx+14, tby+38, "Dubbel-oblik · RÖD 650 (1 av 2)", 9.5, "start", MUTED, 400)
txt(tbx+14, tby+66, f"Oblik {OBL:.0f}° · θ {TRI:.0f}° · WD {WD:.0f} · baslinje {BASE}", 9.5, "start", INK, 400)
txt(tbx+14, tby+82, "Topp + båda vankanter · Z ~0,1–0,2 mm (θ 20°)", 9.5, "start", MUTED, 400)
txt(tbx+tbw*0.56+12, tby+22, "RITN. NR", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+22, "PH-650-02", 11, "end", INK, 700, MONO)
txt(tbx+tbw*0.56+12, tby+46, "SKALA", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+46, "NTS", 11, "end", INK, 400, MONO)
txt(tbx+tbw*0.56+12, tby+70, "ENHET", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+70, "mm", 11, "end", INK, 400, MONO)
txt(tbx+14, tby+186, "Databladsbekräftat (Hikrobot · FS03 · MZLaser) · src/hardware.py", 9, "start", MUTED, 400)
txt(tbx+14, tby+206, "Verifiera: tools/verify_optics.py", 9, "start", MUTED, 400)

add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profile-head.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · WD={WD:.0f} oblik={OBL:.0f}° θ={TRI:.0f}° baslinje={BASE}")
