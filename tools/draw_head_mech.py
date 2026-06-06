#!/usr/bin/env python3
"""KONSTRUKTIONSRITNING — profilhuvud (mekanik), RÖD 650 nm.
Exakt, måttsatt design: optisk bänk + kamera-tiltfäste + laserklämma + portalfäste.
Sidovy (trianguleringsplan, 1:1), planvy av bänken (hålbild), detaljer på fästena,
monteringsvy (obliquity), fästdonslista, toleranser, ritningshuvud.

  python tools/draw_head_mech.py   # -> head-mech.svg
Geometri: WD 710 slant, konvergens 2×15°=30°, baslinje 368, obliquity 30°.
Grön modul = spegel (520-laser + 525-filter).
"""
from __future__ import annotations
import os, sys, math

# ---- geometri (mm) ----
WD, HALF, OBL = 710.0, 15.0, 30.0          # slant-WD, halv konvergensvinkel, obliquity
BASE = round(2*WD*math.sin(math.radians(HALF)))     # baslinje 368
DEPTH = round(WD*math.cos(math.radians(HALF)))      # vinkelrätt djup 686
PL_L, PL_W, PL_T = 440, 80, 10             # optisk bänk
CAM_X, LAS_X = 40, 408                       # bänk-positioner (pupill / apertur)
PORT_X1, PORT_X2 = 160, 280                  # portalklämmor
CAM_L, CAM_W = 29, 29; LENS_L, LENS_D = 40, 32; FILT_L, FILT_D = 6, 32; LAS_L, LAS_D = 99, 18

INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, GRID, HATCH = "#f7f6f1", "#e6e4dc", "#cfd3d8"
RED, GRN, BLUE = "#e8542c", "#2f9e6e", "#2f6fb0"
ALU, ALU2, ALU3, STEEL, WOOD, BLACK = "#cfd3d8", "#b3b9bf", "#9aa1a8", "#8a9099", "#e9e1cf", "#2b2f35"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=11, anchor="start", fill=INK, weight=400, fam=SANS, rot=None):
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
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts); d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.3, head=7):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2-y1, x2-x1)
    for s in (0.42, -0.42): line(x2, y2, x2-head*math.cos(a-s), y2-head*math.sin(a-s), stroke, w)
def hole(x, y, r, col=INK):
    circ(x, y, r, "#fff", col, 1.2); line(x-r-2, y, x+r+2, y, col, 0.6); line(x, y-r-2, x, y+r+2, col, 0.6)
def hdim(x1, x2, y, label, fill=DIMC, size=11, tick=5):
    line(x1, y-tick, x1, y+tick, fill, 0.8); line(x2, y-tick, x2, y+tick, fill, 0.8)
    arrow((x1+x2)/2, y, x1, y, fill, 0.9); arrow((x1+x2)/2, y, x2, y, fill, 0.9)
    rect((x1+x2)/2-len(label)*size*0.31, y-size*0.72, len(label)*size*0.62, size*1.25, PAPER, "none", 0, op=0.92)
    txt((x1+x2)/2, y+size*0.33, label, size, "middle", fill, 700, MONO)
def vdim(y1, y2, x, label, fill=DIMC, size=11, tick=5):
    line(x-tick, y1, x+tick, y1, fill, 0.8); line(x-tick, y2, x+tick, y2, fill, 0.8)
    arrow(x, (y1+y2)/2, x, y1, fill, 0.9); arrow(x, (y1+y2)/2, x, y2, fill, 0.9)
    txt(x+8, (y1+y2)/2+4, label, size, "start", fill, 700, MONO)
def adim(cx, cy, r, a1, a2, label, fill=INK, size=11):
    p1 = (cx+r*math.cos(math.radians(a1)), cy+r*math.sin(math.radians(a1)))
    p2 = (cx+r*math.cos(math.radians(a2)), cy+r*math.sin(math.radians(a2)))
    large = 1 if abs(a2-a1) > 180 else 0
    add(f'<path d="M {p1[0]:.1f} {p1[1]:.1f} A {r} {r} 0 {large} 1 {p2[0]:.1f} {p2[1]:.1f}" fill="none" stroke="{fill}" stroke-width="1.1"/>')
    am = math.radians((a1+a2)/2); txt(cx+(r+12)*math.cos(am), cy+(r+12)*math.sin(am)+4, label, size, "middle", fill, 700, MONO)
def panel(x, y, w, h, title, acc=INK):
    rect(x, y, w, h, "#fff", acc, 1.4, 8); rect(x, y, w, 28, acc, acc, 0, 8); rect(x, y+16, w, 12, acc, acc, 0)
    txt(x+12, y+19, title, 12.5, "start", "#fff", 700, SANS)
def hatchband(x, y, w, h):  # alu-snitt-markering
    rect(x, y, w, h, ALU, ALU2, 1.4)
    for hx in range(int(x)-int(h), int(x+w), 9):
        line(max(x,hx), min(y+h, y+(x-hx)+h) if hx < x else y+h, min(x+w, hx+h), y if hx+h < x+w+h else y, HATCH, 0.6)

W, H = 1960, 1320
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.55">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W-32, H-32, "none", INK, 2); rect(24, 24, W-48, H-48, "none", MUTED, 0.8)
txt(46, 60, "PROFILHUVUD — KONSTRUKTION (mekanik)", 25, "start", INK, 700, SANS)
txt(46, 86, "Optisk bänk + kamera-tiltfäste + laserklämma + portalfäste. Kamera & laser BÅDA oblika (15°+15°=30° triangulering), "
            "huvudet monterat 30° obliquity. RÖD 650 (grön = spegel, 520/525).", 13, "start", MUTED, 400, SANS)
line(46, 100, W-46, 100, INK, 1.4)

# =================================================================== SIDOVY (1:1, trianguleringsplan)
panel(46, 116, 690, 880, "SIDOVY — RÖD huvud · kamera+laser PÅ SAMMA SIDA (NTS)", INK)
# --- bräda (tvärsnitt) med VÄNSTER vankant = den kant huvudet läser ---
bs = 2.1; bcx, btY = 392, 648
bw, bt, wn = 75*bs, 45*bs, 22*bs
poly([(bcx, btY+wn),(bcx+wn, btY),(bcx+bw, btY),(bcx+bw, btY+bt),(bcx, btY+bt)], WOOD, "#b9a96f", 1.8)
for yy in range(int(btY)+18, int(btY+bt)-4, 15): line(bcx+6, yy, bcx+bw-6, yy, "#ddd2b4", 1)
rect(bcx-16, btY+bt, bw+32, 13, BLACK, "#1c1f24", 1, 2)
txt(bcx+bw/2, btY+bt+30, "BRÄDA 75 × 45 (tvärsnitt) på transportband", 9.5, "middle", "#8a7d4e", 700)
txt(bcx-8, btY+wn+28, "VÄNSTER", 8, "end", "#8a7d4e", 700); txt(bcx-8, btY+wn+40, "vankant", 8, "end", "#8a7d4e", 700)
Tp = (bcx+wn*0.45, btY+wn*0.45)               # mät-/laserpunkt på vänstra topphörnet
# --- portal + RÖD huvud (upp-vänster, lutat) — BÅDA på vänster sida ---
rect(150, 150, 360, 15, ALU, ALU2, 1.4, 3); txt(330, 161, "PORTALBALK (T-spår)", 8.5, "middle", MUTED, 700)
camp, lasp = (300, 248), (180, 392)            # kamera brantare, laser mer oblik — BÅDA vänster
def aimT(p): d = math.hypot(Tp[0]-p[0], Tp[1]-p[1]); return ((Tp[0]-p[0])/d, (Tp[1]-p[1])/d)
uc, ul = aimT(camp), aimT(lasp)
cb = (camp[0]-uc[0]*72, camp[1]-uc[1]*72); lb = (lasp[0]-ul[0]*99, lasp[1]-ul[1]*99)
line(cb[0], cb[1], lb[0], lb[1], ALU, 9)        # OPTISK BÄNK (förbinder båda, på samma sida)
midb = ((cb[0]+lb[0])/2, (cb[1]+lb[1])/2)
line(midb[0], midb[1], 330, 165, ALU2, 6); rect(318, 150, 24, 18, ALU3, STEEL, 1.3, 2)   # portalklämma
txt(352, 210, "OPTISK BÄNK", 8.5, "start", MUTED, 700); txt(352, 223, "+ portalklämma", 8.5, "start", MUTED, 700)
# kamera (roterad, pekar ned-höger)
angc = math.degrees(math.atan2(uc[1], uc[0]))-90
add(f'<g transform="translate({camp[0]},{camp[1]}) rotate({angc:.1f})">')
rect(-CAM_W/2,0,CAM_W,CAM_L,"#e9edf1",STEEL,1.6,2); rect(-7,-7,14,7,BLACK,"#1c1f24",1)
rect(-LENS_D/2,CAM_L,LENS_D,LENS_L,"#dfe3e7","#9aa0a6",1.4,2); rect(-FILT_D/2,CAM_L+LENS_L,FILT_D,FILT_L,"#f6d9cf",RED,1.6)
add('</g>')
txt(camp[0]+24, camp[1]-4, "KAMERA + 12 mm + BP650", 8.5, "start", INK, 700); txt(camp[0]+24, camp[1]+9, "(brantare arm)", 8, "start", MUTED, 700)
# laser (roterad, pekar ned-höger, mer oblik)
angl = math.degrees(math.atan2(ul[1], ul[0]))-90
add(f'<g transform="translate({lasp[0]},{lasp[1]}) rotate({angl:.1f})">')
rect(-LAS_D/2,0,LAS_D,LAS_L,"#d7b7b0","#9a5a52",1.5,3); circ(0,LAS_L,3.2,"#fff",RED,1.2)
add('</g>')
txt(lasp[0]+22, lasp[1]+34, "LINJELASER (mer oblik arm)", 8.5, "start", RED, 700)
# strålar → grazar VÄNSTER vankant
line(camp[0]+uc[0]*78, camp[1]+uc[1]*78, Tp[0], Tp[1], "#8a9099", 1.3, "5 4")   # kamerasikt
line(lasp[0]+ul[0]*102, lasp[1]+ul[1]*102, Tp[0], Tp[1], RED, 2.4)              # laserblad
line(Tp[0], Tp[1], bcx, btY+wn, RED, 2.4, op=0.85)                              # laser ned längs vankanten
circ(Tp[0], Tp[1], 4, RED, "#a8331a", 1.2)
# mått (NTS-etiketter)
txt((camp[0]+Tp[0])/2-60, (camp[1]+Tp[1])/2, "WD 710", 11, "middle", INK, 700, MONO, rot=math.degrees(math.atan2(uc[1],uc[0])))
txt(midb[0]-6, midb[1]-12, "BASLINJE 368", 9.5, "middle", INK, 700, MONO, rot=math.degrees(math.atan2(lb[1]-cb[1], lb[0]-cb[0])))
line(Tp[0], Tp[1], Tp[0], Tp[1]-180, DIMC, 0.6, "3 3"); txt(Tp[0]+8, Tp[1]-160, "lod", 8, "start", DIMC, 700)
txt(Tp[0]-128, Tp[1]-92, "huvudet ~30° oblik", 9, "middle", INK, 700); txt(Tp[0]-128, Tp[1]-78, "θ 30° (kamera↔laser)", 8, "middle", MUTED, 700)
# note
txt(391, 920, "Kamera OCH laser sitter PÅ SAMMA SIDA (vänster) och tittar snett in →", 10, "middle", INK, 700)
txt(391, 938, "läser brädans VÄNSTERKANT + höjd. GRÖN huvud = spegel, läser högerkant. NTS.", 9.5, "middle", MUTED, 400)

# =================================================================== PLANVY (bänk ovanifrån)
panel(752, 116, 700, 250, "PLANVY — optisk bänk (hålbild)", BLUE)
px0, py0 = 800, 200; pscale = 1.36
def PX(mm): return px0 + mm*pscale
def PY(mm): return py0 + mm*pscale
rect(PX(0), PY(0), PL_L*pscale, PL_W*pscale, ALU, ALU2, 1.6, 8)
# hål: kamera (x40), laser (x408), portal (x160,280) — c/c 40 i bredd (y20,60)
for (hx, lab) in [(CAM_X, "kamera M4×2"), (LAS_X, "laser M4×2")]:
    for hy in (20, 60): hole(PX(hx), PY(hy), 4)
    txt(PX(hx), PY(80)+16, lab, 8.5, "middle", INK, 700)
for hx in (PORT_X1, PORT_X2):
    for hy in (20, 60): hole(PX(hx), PY(hy), 5, STEEL)
txt(PX((PORT_X1+PORT_X2)/2), PY(40)+4, "portal M6×4", 8.5, "middle", STEEL, 700)
hdim(PX(0), PX(CAM_X), PY(0)-16, f"{CAM_X}", DIMC, 9); hdim(PX(CAM_X), PX(LAS_X), PY(0)-16, f"{BASE}", INK, 9)
hdim(PX(LAS_X), PX(PL_L), PY(0)-16, f"{PL_L-LAS_X}", DIMC, 9)
hdim(PX(PORT_X1), PX(PORT_X2), PY(80)+38, f"{PORT_X2-PORT_X1}", DIMC, 9)
vdim(PY(20), PY(60), PX(PL_L)+18, "40", DIMC, 9)
txt(PX(PL_L/2), PY(80)+54, "440 × 80 × 10 · ändar R10 · plan ±0,1 · hål ±0,1", 9, "middle", MUTED, 400)

# =================================================================== DETALJ: KAMERA-TILTFÄSTE
panel(752, 382, 342, 326, "DETALJ B — kamera-tiltfäste", INK)
bx, by = 812, 470
poly([(bx,by+120),(bx+150,by+120),(bx+150,by+104),(bx+22,by+104)], ALU, ALU2, 1.5)   # basplatta
hole(bx+40, by+112, 4); hole(bx+110, by+112, 4); txt(bx+75, by+150, "M4 → bänk (c/c 70)", 8.5, "middle", INK, 700)
add(f'<g transform="translate({bx+150},{by+112}) rotate(-105)">')                    # tiltad fläns 15°
rect(0, -8, 110, 16, ALU2, STEEL, 1.5, 2); hole(28, 0, 3, STEEL); hole(78, 0, 3, STEEL)
add('</g>')
txt(bx+200, by+40, "tiltad fläns 15°", 8.5, "start", INK, 700); txt(bx+200, by+54, "(±20° slits, lås)", 8, "start", MUTED, 700)
txt(bx+200, by+82, "2× M3 → kamerans", 8.5, "start", INK, 700); txt(bx+200, by+96, "M3-hålbild (c/c 20)", 8.5, "start", INK, 700)
adim(bx+150, by+112, 40, 180, 195, "15°", INK, 10)
txt(bx, by+186, "Kamera bultas i M3-hålen; flänsen ger 15° och justerslits för optisk inriktning.", 8.5, "start", MUTED, 400)

# =================================================================== DETALJ: LASERKLÄMMA
panel(1110, 382, 342, 326, "DETALJ C — laserklämma Ø18", INK)
lx, ly = 1230, 500
circ(lx, ly, 38, ALU, ALU2, 1.6); circ(lx, ly, 18, "#fff", RED, 1.4)                  # klämma + Ø18 borr
line(lx-2, ly-38, lx+2, ly-38, ALU2, 1); rect(lx-26, ly-46, 52, 10, ALU2, STEEL, 1.2, 2)  # split + skruv
hole(lx-16, ly-41, 3, STEEL); hole(lx+16, ly-41, 3, STEEL)
txt(lx, ly+4, "Ø18", 10, "middle", RED, 700, MONO)
txt(lx+54, ly-20, "split-klämma:", 8.5, "start", INK, 700)
txt(lx+54, ly-6, "• rotera → räta linjen", 8.5, "start", MUTED, 700)
txt(lx+54, ly+8, "• glid → fokus @ 710", 8.5, "start", MUTED, 700)
txt(lx+54, ly+22, "• tiltfäste 15° (som B)", 8.5, "start", MUTED, 700)
poly([(lx-30,ly+58),(lx+30,ly+58),(lx+38,ly+74),(lx-22,ly+74)], ALU, ALU2, 1.4)
hole(lx-14, ly+66, 4); hole(lx+14, ly+66, 4); txt(lx, ly+92, "M4 → bänk", 8.5, "middle", INK, 700)
adim(lx, ly+66, 30, 180, 195, "15°", INK, 9)

# =================================================================== DETALJ D — MONTERING: BÅDA HUVUDEN
panel(1468, 116, 446, 360, "MONTERING — BÅDA HUVUDEN (tvärsnitt)", INK)
cxm, cym = 1690, 382
rect(1496, 150, 388, 15, ALU, ALU2, 1.4, 3); txt(1690, 161, "PORTALBALK", 8, "middle", MUTED, 700)
rect(cxm-44, cym, 88, 18, WOOD, "#b9a96f", 1.4); rect(cxm-54, cym+18, 108, 8, BLACK, "#1c1f24", 1, 2)
txt(cxm, cym+40, "SAMMA laserlinje", 8.5, "middle", "#8a7d4e", 700)
# RÖD huvud (vänster) — komplett bänk+kamera+laser, lutat ~30° inåt
rhx, rhy = 1556, 232
add(f'<g transform="translate({rhx},{rhy}) rotate(32)">')
rect(0,-7,116,14, ALU, ALU2, 1.5); rect(4,-22,26,15,"#e9edf1",STEEL,1.3,2); rect(86,-22,22,15,"#d7b7b0",RED,1.4,2)
add('</g>')
line(rhx+18, rhy+18, cxm-7, cym, "#8a9099", 1.1, "4 3"); line(rhx+88, rhy+58, cxm-7, cym, RED, 2.3)
txt(rhx-6, rhy-30, "RÖD HUVUD (vänster)", 9, "start", RED, 700); txt(rhx-6, rhy-17, "kamera+laser+bänk", 7.5, "start", MUTED, 700)
txt(cxm-150, cym+8, "→ topp + V vankant", 8, "start", RED, 700)
# GRÖN huvud (höger) — spegel
ghx, ghy = 1824, 232
add(f'<g transform="translate({ghx},{ghy}) rotate(-32)">')
rect(-116,-7,116,14, ALU, ALU2, 1.5); rect(-30,-22,26,15,"#e9edf1",STEEL,1.3,2); rect(-108,-22,22,15,"#d7b7b0",GRN,1.4,2)
add('</g>')
line(ghx-18, ghy+18, cxm+7, cym, "#8a9099", 1.1, "4 3"); line(ghx-88, ghy+58, cxm+7, cym, GRN, 2.3)
txt(ghx+6, ghy-30, "GRÖN HUVUD (höger)", 9, "end", GRN, 700); txt(ghx+6, ghy-17, "spegelvänd kopia", 7.5, "end", MUTED, 700)
txt(cxm+150, cym+8, "→ topp + H vankant", 8, "end", GRN, 700)
circ(cxm, cym, 4.2, "#a23ad6", "#7a2fb0", 1.2)
txt(1690, cym+62, "Var sitt KOMPLETT huvud (bänk+kamera+laser, baslinje 368),", 8.6, "middle", INK, 400)
txt(1690, cym+76, "monterat lutat ~30° på VAR SIN sida → samma laserlinje.", 8.6, "middle", INK, 400)
txt(1690, cym+90, "Olika färg (650/520) + matchande filter → stör ej varandra.", 8.6, "middle", INK, 400)

# =================================================================== FÄSTDON / DELAR
panel(1468, 492, 446, 286, "FÄSTDON & DELAR (per huvud)", BLUE)
parts = [
    ("Optisk bänk", "alu-platta 440×80×10 (6082-T6)", "1"),
    ("Kamera-tiltfäste", "vinkel m. 15°-fläns + justerslits", "1"),
    ("Laserklämma", "Ø18 split + 15°-tiltfäste", "1"),
    ("Portalklämma", "T-spår, höjd/vinkel-justering", "2"),
    ("Skruv M3×6", "kamera → fäste", "2"),
    ("Skruv M4×10", "fästen → bänk", "4"),
    ("Skruv M6×16 + T-mutter", "portalklämma → balk", "4"),
    ("Optik (separat BOM)", "MV-CS050 · MVL-MF1228M · BP650 · MZLaser", "—"),
]
yy = 540
for nm, sp, q in parts:
    txt(1482, yy, nm, 9.5, "start", INK, 700); txt(1660, yy, sp, 8.8, "start", MUTED, 400); txt(1900, yy, q, 9.5, "end", INK, 700, MONO)
    yy += 21

# =================================================================== NOTER / TOLERANSER
panel(1468, 794, 446, 240, "NOTER & TOLERANSER", INK)
notes = [
    "1.  Mått i mm. Bänk plan ±0,1; hålläge ±0,1; allmän ±0,3.",
    "2.  Vinklar (15°+15°, 30°) NOMINELLA → finjustera optiskt:",
    "     rikta så kamera+laser KONVERGERAR på samma linje @ 710 mm,",
    "     lås sedan slits/klämmor.",
    "3.  Laserlinje skarp @ 710 mm (glid laser i klämman). Blända F8–F11",
    "     för djupskärpa, alt. Scheimpflug-tilt på sensorn.",
    "4.  Filter FS03-BP650 (M30.5) på objektivfronten.",
    "5.  Laser Klass 3B (100 mW) → kåpa + skylt + glasögon.",
    "6.  GRÖN modul = spegelvänd: 520-laser + 525-filter.",
]
yy = 822
for ln_ in notes:
    txt(1482, yy, ln_, 9.2, "start", INK, 400); yy += 17 if not ln_.startswith("     ") else 15

# =================================================================== RITNINGSHUVUD
tbx, tby, tbw = 752, 794, 700
rect(tbx, tby, tbw, 240, "#fff", INK, 1.6)
line(tbx, tby+150, tbx+tbw, tby+150, INK, 1)
for fx in (0.30, 0.58, 0.80): line(tbx+tbw*fx, tby, tbx+tbw*fx, tby+150, INK, 0.9)
txt(tbx+16, tby+34, "VIRKESSKANNER", 15, "start", INK, 700, SANS)
txt(tbx+16, tby+56, "PROFILHUVUD — KONSTRUKTION", 12, "start", INK, 700)
txt(tbx+16, tby+78, "Dubbel-oblik · RÖD 650 nm (1 av 2)", 10, "start", MUTED, 400)
txt(tbx+16, tby+104, "Kamera & laser BÅDA oblika (15°+15°)", 10, "start", INK, 400)
txt(tbx+16, tby+124, "monterade 30° obliquity på portalen", 10, "start", INK, 400)
def cell(fx, fw, k, v):
    x = tbx+tbw*fx; txt(x+10, tby+20, k, 8.5, "start", MUTED, 700)
    txt(x+10, tby+42, v, 12, "start", INK, 700, MONO)
cell(0.30, 0.28, "WD (slant)", f"{WD:.0f}"); cell(0.30, 0, "θ / obliquity", f"30° / {OBL:.0f}°")
cell(0.58, 0.22, "BASLINJE", f"{BASE}"); cell(0.58, 0, "DJUP", f"{DEPTH}")
cell(0.80, 0.20, "RITN. NR", "PH-650-M1"); cell(0.80, 0, "SKALA", "1:1 / NTS")
txt(tbx+tbw*0.30+10, tby+72, "ENHET", 8.5, "start", MUTED, 700); txt(tbx+tbw*0.30+10, tby+94, "mm", 12, "start", INK, 700, MONO)
txt(tbx+tbw*0.58+10, tby+72, "BÄNK", 8.5, "start", MUTED, 700); txt(tbx+tbw*0.58+10, tby+94, "440×80×10", 11, "start", INK, 700, MONO)
txt(tbx+tbw*0.80+10, tby+96, "verify_optics.py", 9, "start", MUTED, 400)
txt(tbx+16, tby+176, "Databladsbekräftad optik (Hikrobot · FS03 · MZLaser) · geometri ur src/hardware.py.", 9, "start", MUTED, 400)
txt(tbx+16, tby+198, "Bänk/fästen = tillverkningsdelar (alu). Grön modul spegelvänd (520-laser + 525-filter).", 9, "start", MUTED, 400)
txt(tbx+16, tby+220, "Vinklar nominella; slutlig inriktning optiskt mot konvergens @ 710 mm.", 9, "start", MUTED, 400)

add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "head-mech.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · WD={WD:.0f} baslinje={BASE} djup={DEPTH} obliquity={OBL:.0f}°")
