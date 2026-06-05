#!/usr/bin/env python3
"""Monteringsritning — ETT profilhuvud (RÖD 650 nm) i dubbel-oblik mätrigg.
Kamera + objektiv + bandpassfilter + linjelaser på vinkelbeslag, med exakt
trianguleringsgeometri (WD 710, baslinje, vinkel 30°), måttsättning, ballong-
callouts, komponentlista, optisk princip, noter och ritningshuvud.

  python tools/draw_profile_head.py   # -> profile-head.svg i projektroten
Grön modul är identisk: byt 650→520-laser + 525-filter.
"""
from __future__ import annotations
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------- mått (mm, databladsbekräftade) ----------
WD       = 710.0   # kamera→bräda, slant
TRI      = 30.0    # trianguleringsvinkel (kamera↔laser)
OBL      = 30.0    # huvudets siktaxel från lod
FAN      = 45.0    # laserns Powell-fläkt → 500 mm linje
LINE     = 500.0
CAM_L, CAM_W = 29.0, 29.0       # MV-CS050-10UM kropp
LENS_L, LENS_D = 40.0, 32.0     # MVL-MF1228M-8MP
FILT_L, FILT_D = 6.0, 32.0      # FS03-BP650 (M30.5)
LAS_L, LAS_D  = 99.0, 18.0      # MZLaser AJPWHF5638
BASE = round(2 * WD * math.sin(math.radians(TRI / 2)))   # baslinje ~368

# ---------- färger ----------
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID, LINEC = "#f7f6f1", "#ecebe4", "#e4e2da", "#dedcd3"
RED, GRN, BLUE, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6"
ALU, ALU2, WOOD, GOLD, BLACK = "#c3c6ca", "#aab0b6", "#e9e1cf", "#b9a96f", "#2b2f35"
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
    """linjärt mått mellan två punkter, etikett i mitten."""
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    ax1, ay1 = x1 + nx * off, y1 + ny * off; ax2, ay2 = x2 + nx * off, y2 + ny * off
    line(x1, y1, ax1, ay1, fill, 0.7); line(x2, y2, ax2, ay2, fill, 0.7)
    arrow(ax1, ay1, ax2, ay2, fill, 1); arrow(ax2, ay2, ax1, ay1, fill, 1)
    mx, my = (ax1 + ax2) / 2, (ay1 + ay2) / 2
    rot = math.degrees(math.atan2(dy, dx)); rot = rot + 180 if rot > 90 or rot < -90 else rot
    rect(mx - len(label) * size * 0.30, my - size * 0.7, len(label) * size * 0.6, size * 1.25, PAPER, "none", 0, 0, op=0.92)
    txt(mx, my + size * 0.34, label, size, "middle", fill, 700, MONO, rot)
def balloon(x, y, n, col=INK):
    circ(x, y, 12, "#fff", col, 1.6); txt(x, y + 4.5, str(n), 12.5, "middle", col, 700, SANS)
def leader(x1, y1, x2, y2, col=MUTED):
    line(x1, y1, x2, y2, col, 1); circ(x2, y2, 2.2, col, col, 0)
def panel(x, y, w, h, title, acc):
    rect(x, y, w, h, "#fff", acc, 1.4, 9); rect(x, y, w, 30, acc, acc, 0, 9)
    rect(x, y + 18, w, 12, acc, acc, 0)
    txt(x + 14, y + 20, title, 13, "start", "#fff", 700, SANS)

W, H = 1720, 1180
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.6">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W - 32, H - 32, "none", INK, 2); rect(24, 24, W - 48, H - 48, "none", MUTED, 0.8)
txt(44, 62, "PROFILHUVUD — RÖD 650 nm  (1 av 2)", 25, "start", INK, 700, SANS)
txt(44, 88, "Dubbel-oblik lasertriangulering · ett mäthuvud: profilkamera (mono) + objektiv + bandpassfilter + Powell-linjelaser på vinkelbeslag. "
            "Grön modul identisk (520-laser + 525-filter).", 13.5, "start", MUTED, 400, SANS)
line(44, 102, W - 44, 102, INK, 1.4)

# =================================================================== HUVUDVY (1 px = 1 mm)
# konvergenspunkt på brädan
Tx, Ty = 600, 980
# kamera-apertur: 30° oblik upp-vänster ;  laser-apertur: lodrätt upp
camx, camy = Tx - WD * math.sin(math.radians(OBL)), Ty - WD * math.cos(math.radians(OBL))
lasx, lasy = Tx, Ty - WD
add(f'<g transform="translate(0,8)">')

# ---- bräda + bälte (brott-markering ovan) ----
bw_seg = 300
rect(Tx - bw_seg/2, Ty, bw_seg, 30, WOOD, GOLD, 1.6)
txt(Tx - bw_seg/2 + 8, Ty + 20, "BRÄDA (yta)", 10, "start", "#8a7d4e", 700)
rect(Tx - bw_seg/2 - 16, Ty + 30, bw_seg + 32, 16, BLACK, "#1c1f24", 1.2, 3)
txt(Tx, Ty + 64, "transportband", 9.5, "middle", MUTED, 700)
# brädytans referenslinje
line(Tx - bw_seg/2 - 30, Ty, Tx + bw_seg/2 + 30, Ty, DIMC, 0.8, "6 4")

# ---- optiska strålar: kamera-FOV (djup) + laserblad ----
# laserblad (i triangulerings­planet = en linje ned till T)
line(lasx, lasy, Tx, Ty, RED, 2.4)
# kamerans siktstråle + tunn FOV-kil (djupband ±25 mm i objektrymd)
def Praydir(ax, ay):  # enhetsriktning apertur->T
    d = math.hypot(Tx - ax, Ty - ay); return (Tx - ax)/d, (Ty - ay)/d
cdx, cdy = Praydir(camx, camy)
line(camx, camy, Tx, Ty, "#8a9099", 1.6, "5 4")          # siktaxel (streckad)
# FOV-kil: ±halv djup-FOV vinkelrätt mot strålen vid T
perp = (-cdy, cdx); half = 16
poly([(camx, camy), (Tx + perp[0]*half, Ty + perp[1]*half), (Tx - perp[0]*half, Ty - perp[1]*half)],
     "#2f6fb0", BLUE, 1, op=0.10)
line(camx, camy, Tx + perp[0]*half, Ty + perp[1]*half, BLUE, 0.8)
line(camx, camy, Tx - perp[0]*half, Ty - perp[1]*half, BLUE, 0.8)
# konvergens-/laserpunkt
circ(Tx, Ty, 4.2, RED, "#a8331a", 1)
txt(Tx + 10, Ty - 8, "laserlinje (tvärsnitt)", 9.5, "start", RED, 700)

# ---- vinkelbeslag (baslinjebalk kamera↔laser) ----
def U(ax, ay):  # enhetsvektor apertur->T
    d = math.hypot(Tx-ax, Ty-ay); return ((Tx-ax)/d, (Ty-ay)/d)
ucx, ucy = U(camx, camy); ulx, uly = U(lasx, lasy)
# beslagets balk: från kamerans baksida till laserns baksida
cbx, cby = camx - ucx*(CAM_L+LENS_L+FILT_L), camy - ucy*(CAM_L+LENS_L+FILT_L)   # bakom kameran
lbx, lby = lasx - ulx*LAS_L, lasy - uly*LAS_L                                   # bakom lasern
# rita balken som ett alu-band
bvx, bvy = (lbx-cbx), (lby-cby); bL = math.hypot(bvx,bvy); bnx,bny = -bvy/bL, bvx/bL
poly([(cbx+bnx*7,cby+bny*7),(lbx+bnx*7,lby+bny*7),(lbx-bnx*7,lby-bny*7),(cbx-bnx*7,cby-bny*7)],
     ALU, ALU2, 1.4)

# ---- portalfäste upp till tvärbalk ----
mxp, myp = (cbx+lbx)/2, (cby+lby)/2
line(mxp, myp, mxp, 150, ALU2, 6)
rect(camx-200, 138, 560, 22, ALU, ALU2, 1.4, 3)
txt(camx-190, 153, "PORTALENS TVÄRBALK (T-spår)", 9.5, "start", MUTED, 700)
rect(mxp-16, 150, 32, 22, ALU2, "#8a9099", 1.4, 3)         # klämfäste
txt(mxp+24, 165, "justerbart portalfäste (vinkel + höjd)", 9, "start", MUTED, 700)

# ---- komponent: KAMERA-stack (kamera+lins+filter), roterad längs siktaxeln ----
def comp_group(apx, apy, ux, uy):
    return math.degrees(math.atan2(uy, ux))
ang = comp_group(camx, camy, ucx, ucy)
add(f'<g transform="translate({camx:.1f},{camy:.1f}) rotate({ang:.1f})">')
# lokalt: +x mot brädan (apertur=filterfront vid 0). bakåt = -x.
rect(-FILT_L, -FILT_D/2, FILT_L, FILT_D, "#f6d9cf", RED, 1.4)                       # filter (3)
rect(-FILT_L-LENS_L, -LENS_D/2, LENS_L, LENS_D, "#d9dde1", "#9aa0a6", 1.4, 2)        # objektiv (2)
add(f'<g>')
for gx in range(0, int(LENS_L)-6, 6): line(-FILT_L-gx-3, -LENS_D/2, -FILT_L-gx-3, LENS_D/2, "#c2c7cc", 0.6)
add('</g>')
rect(-FILT_L-LENS_L-CAM_L, -CAM_W/2, CAM_L, CAM_W, "#e9edf1", "#7e8489", 1.6, 2)     # kamera (1)
rect(-FILT_L-LENS_L-CAM_L-7, -7, 8, 6, BLACK, "#1c1f24", 1)                          # USB3
rect(-FILT_L-LENS_L-CAM_L-7, 2, 8, 5, "#caa64a", "#8a6510", 1)                       # power Hirose
add('</g>')

# ---- komponent: LASER, roterad längs laseraxeln ----
anl = comp_group(lasx, lasy, ulx, uly)
add(f'<g transform="translate({lasx:.1f},{lasy:.1f}) rotate({anl:.1f})">')
rect(-LAS_L, -LAS_D/2, LAS_L, LAS_D, "#d7b7b0", "#9a5a52", 1.4, 3)                   # laser (4)
rect(-LAS_L-2, -3, -10, 6, "#444", "#222", 1)                                       # kabel-stub
circ(-2, 0, 3, "#fff", RED, 1.2)                                                    # apertur
add('</g>')

# ---- ballong-callouts ----
for (n, bx, by, lx, ly, col) in [
    (1, camx-150, camy-58, camx-ucx*(FILT_L+LENS_L+CAM_L*0.5), camy-ucy*(FILT_L+LENS_L+CAM_L*0.5), INK),
    (2, camx-150, camy-20, camx-ucx*(FILT_L+LENS_L*0.5), camy-ucy*(FILT_L+LENS_L*0.5), INK),
    (3, camx-150, camy+18, camx-ucx*FILT_L*0.5, camy-ucy*FILT_L*0.5, RED),
    (4, lasx+150, lasy-70, lasx-ulx*LAS_L*0.5, lasy-uly*LAS_L*0.5, RED),
    (5, mxp-150, myp+150, (cbx+lbx)/2, (cby+lby)/2, INK),
    (6, mxp+150, 120, mxp, 161, INK),
]:
    leader(bx, by, lx, ly, MUTED); balloon(bx, by, n, col)

# ---- måttsättning ----
dim(camx, camy, Tx, Ty, f"WD {WD:.0f} (slant)", 46, INK, 12)          # arbetsavstånd
dim(cbx, cby, lbx, lby, f"baslinje {BASE}", -26, INK, 11)             # baslinje
# trianguleringsvinkel vid T
line(Tx, Ty, camx, camy, DIMC, 0.6); line(Tx, Ty, lasx, lasy, DIMC, 0.6)
add(f'<path d="M {Tx-ucx*70:.1f} {Ty-ucy*70:.1f} A 70 70 0 0 1 {Tx-ulx*70:.1f} {Ty-uly*70:.1f}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
txt(Tx-50, Ty-78, f"θ = {TRI:.0f}°", 13, "middle", INK, 700, MONO)
txt(Tx-50, Ty-62, "triangulering", 8.5, "middle", MUTED, 700)
# obliquity (siktaxel vs lod) vid kameran? visa lod vid T
line(Tx, Ty, Tx, Ty-140, DIMC, 0.8, "3 3")
add(f'<path d="M {Tx:.1f} {Ty-110:.1f} A 110 110 0 0 0 {Tx-ucx*110:.1f} {Ty-ucy*110:.1f}" fill="none" stroke="{MUTED}" stroke-width="1"/>')
txt(Tx-40, Ty-120, f"{OBL:.0f}° oblik", 10.5, "middle", MUTED, 700, MONO)
add('</g>')

# =================================================================== DETALJ A — optisk stack (2,5×)
dax, day, daw, dah = 670, 540, 480, 296
panel(dax, day, daw, dah, "DETALJ A — optisk stack  (2,5×)", BLUE)
sc = 2.6; scy = day + 150; x = dax + 64
cw, cl = CAM_W*sc, CAM_L*sc; ll, ld = LENS_L*sc, LENS_D*sc; fl, fd = FILT_L*sc, FILT_D*sc
# kamera
rect(x, scy-cw/2, cl, cw, "#e9edf1", "#7e8489", 1.8, 3)
rect(x-17, scy-17, 17, 13, BLACK, "#1c1f24", 1.2, 2); txt(x-8, scy-22, "USB3", 7.5, "middle", MUTED, 700)
rect(x-17, scy+3, 17, 12, "#caa64a", "#8a6510", 1.2, 2); txt(x-8, scy+26, "5V/IO", 7.5, "middle", MUTED, 700)
txt(x+cl/2, scy+cw/2+18, "① MV-CS050-10UM · C-mount", 9, "middle", INK, 700)
x += cl
rect(x, scy-12, 9, 24, ALU2, "#8a9099", 1.4); x += 9
# objektiv
rect(x, scy-ld/2, ll, ld, "#d9dde1", "#9aa0a6", 1.8, 3)
for gx in range(0, int(ll)-12, 16): line(x+gx+8, scy-ld/2, x+gx+8, scy+ld/2, "#c2c7cc", 0.8)
txt(x+ll/2, scy-ld/2-10, "② MVL-MF1228M-8MP · 12 mm", 9, "middle", INK, 700)
txt(x+ll/2, scy+ld/2+16, "fokus + iris F2.8–16", 8, "middle", MUTED, 700)
x += ll
txt(x+1, scy-ld/2-26, "M30.5×0.5 filtergänga", 8.5, "middle", BLUE, 700)
line(x, scy-ld/2-20, x, scy-ld/2-4, BLUE, 0.8)
# filter
rect(x, scy-fd/2, fl, fd, "#f6d9cf", RED, 1.9, 2)
txt(x+fl+8, scy-2, "③ FS03-BP650", 9.5, "start", RED, 700)
txt(x+fl+8, scy+12, "650 nm bandpass", 8, "start", MUTED, 700)
arrow(x+fl+90, scy+46, x+fl+8, scy+6, RED, 1.6); txt(x+fl+30, scy+58, "laser 650 nm in", 8.5, "start", RED, 700)
txt(dax+16, day+dah-14, "Filtret skruvas på objektivets front → mono-kameran ser i princip BARA laserlinjen.", 8.8, "start", MUTED, 400)

# =================================================================== HÖGER KOLUMN
CX = 1196; CW = 488
# ---- komponentlista ----
panel(CX, 120, CW, 250, "KOMPONENTER", INK)
items = [
    (1, INK, "Profilkamera", "Hikrobot MV-CS050-10UM", "mono, USB3, 2/3″ IMX264, C-mount, 60 fps"),
    (2, "#7e8489", "Objektiv", "HIKROBOT MVL-MF1228M-8MP", "12 mm F2.8, C-mount, M30.5-filtergänga"),
    (3, RED, "Bandpassfilter", "FS03-BP650", "650 nm, FWHM 40, M30.5×0.5, T≥90 %"),
    (4, RED, "Linjelaser", "MZLaser AJPWHF5638", "638 nm Powell, 45°, 100 mW, 5 V ACC"),
    (5, MUTED, "Vinkelbeslag", "alu, justerbar vinkel/baslinje", "låser kamera + laser i 30° triangulering"),
    (6, MUTED, "Portalfäste", "klämma mot T-spår-balk", "justerbar höjd + obliquity 30°"),
]
yy = 158
for (n, col, role, prod, spec) in items:
    balloon(CX + 22, yy + 8, n, col)
    txt(CX + 44, yy + 2, role, 11.5, "start", MUTED, 700, SANS)
    txt(CX + 44, yy + 18, prod, 11.5, "start", INK, 700, SANS)
    txt(CX + 44, yy + 32, spec, 9.5, "start", MUTED, 400, SANS)
    yy += 42

# ---- måttabell ----
panel(CX, 384, CW, 150, "MÅTT & GEOMETRI", BLUE)
dims = [("Arbetsavstånd WD (slant)", f"{WD:.0f} mm"), ("Trianguleringsvinkel θ", f"{TRI:.0f}°"),
        ("Baslinje kamera↔laser", f"{BASE} mm"), ("Huvudets obliquity (från lod)", f"{OBL:.0f}°"),
        ("Laser-fläkt (Powell)", f"{FAN:.0f}° → linje {LINE:.0f} mm"), ("Kamera-FOV @ WD", f"{LINE:.0f} mm (0,204 mm/px)")]
yy = 420
for k, v in dims:
    txt(CX + 16, yy, k, 10.5, "start", INK, 400, SANS); txt(CX + CW - 16, yy, v, 11, "end", INK, 700, MONO)
    yy += 19

# ---- optisk princip ----
panel(CX, 548, CW, 150, "OPTISK PRINCIP — höjd → pixelförskjutning", PURP)
ox, oy = CX + 40, 668
rect(ox, oy-70, 92, 16, "#e9edf1", "#7e8489", 1.4, 2); txt(ox+46, oy-58, "sensor", 8.5, "middle", MUTED, 700)
for i in range(5): line(ox+10+i*18, oy-54, ox+10+i*18, oy-50, MUTED, 0.8)
line(ox+46, oy-54, ox+46, oy, BLUE, 1, "3 3")
arrow(ox+250, oy-30, ox+250, oy, GOLD, 1.4); txt(ox+258, oy-14, "Δz (höjd)", 9.5, "start", "#8a7d4e", 700)
line(ox+150, oy, ox+260, oy, GOLD, 2)
line(ox+46, oy-54, ox+205, oy, RED, 1.6); line(ox+64, oy-54, ox+235, oy, RED, 1.0, "3 2")
txt(ox+30, oy+18, "Δz → spot flyttas Δp på sensorn:  δz = subpixel·0,204 / sin θ", 9.5, "start", INK, 400, SANS)
txt(ox+30, oy+33, "→ ~0,02–0,04 mm teoretiskt · ~0,05–0,15 mm på virke", 9.5, "start", MUTED, 700, SANS)

# ---- noter ----
panel(CX, 712, CW, 250, "NOTER", INK)
notes = [
    "A.  Rikta kamera + laser så de KONVERGERAR på samma linje på brädan vid WD 710 mm; lås beslaget.",
    "B.  Skärpa: fokusera laserlinjen skarp vid 710 mm. Blända ner objektivet (F8–F11) för djup­skärpa",
    "     över mätrange ±25 mm — alt. Scheimpflug-tilt på sensorn för skarp linje i hela djupet.",
    "C.  Filtret (FS03-BP650, M30.5) skruvas på objektivets front → kameran ser i princip bara lasern.",
    "D.  Laser = Klass 3B (100 mW) → kåpa + varningsskylt + skyddsglasögon 650 nm. Enable via GPIO/MOSFET.",
    "E.  Kabel: kamera USB3 → Jetson; laser 5 V + enable. Dragavlastning vid beslaget.",
    "F.  GRÖN modul (spegelvänd, andra hållet): identisk — byt till 520-laser + 525-filter (FS03-BP525).",
    "G.  Mått i mm. Ej skalenlig i detalj; huvudvyn 1 px = 1 mm.",
]
yy = 740
for ln_ in notes:
    txt(CX + 14, yy, ln_, 9.6, "start", INK if ln_[3:4] != " " else INK, 400, SANS)
    yy += 19 if not ln_.startswith("     ") else 16

# ---- ritningshuvud ----
tbx, tby, tbw, tbh = CX, 978, CW, 168
rect(tbx, tby, tbw, tbh, "#fff", INK, 1.6)
line(tbx, tby+92, tbx+tbw, tby+92, INK, 1); line(tbx+tbw*0.56, tby, tbx+tbw*0.56, tby+92, INK, 1)
line(tbx, tby+46, tbx+tbw*0.56, tby+46, INK, 0.8)
txt(tbx+14, tby+22, "VIRKESSKANNER — PROFILHUVUD", 12.5, "start", INK, 700, SANS)
txt(tbx+14, tby+38, "Dubbel-oblik · 1 mäthuvud (RÖD 650 nm)", 9.5, "start", MUTED, 400)
txt(tbx+14, tby+66, "Triangulering 30° · WD 710 · baslinje "+str(BASE), 9.5, "start", INK, 400)
txt(tbx+14, tby+82, "FOV 500 mm · 0,204 mm/px · Z ~0,05–0,15 mm", 9.5, "start", MUTED, 400)
txt(tbx+tbw*0.56+12, tby+22, "RITN. NR", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+22, "PH-650-01", 11, "end", INK, 700, MONO)
txt(tbx+tbw*0.56+12, tby+46, "SKALA", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+46, "1:1 (detalj NTS)", 11, "end", INK, 400, MONO)
txt(tbx+tbw*0.56+12, tby+70, "ENHET", 8.5, "start", MUTED, 700); txt(tbx+tbw-12, tby+70, "mm", 11, "end", INK, 400, MONO)
txt(tbx+14, tby+112, "Källa: src/hardware.py · verifiera med tools/verify_optics.py", 9, "start", MUTED, 400)
txt(tbx+14, tby+132, "Profilkamera/lins/filter databladsbekräftade (Hikrobot · FS03 · MZLaser)", 9, "start", MUTED, 400)
txt(tbx+14, tby+152, "Grön modul = spegel, 520-laser + 525-filter", 9, "start", MUTED, 400)

add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profile-head.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · WD={WD:.0f} baslinje={BASE} θ={TRI:.0f}° oblik={OBL:.0f}°")
