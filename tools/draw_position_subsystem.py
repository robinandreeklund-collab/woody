#!/usr/bin/env python3
"""SCHEMA — brädposition & nolla, OVANIFRÅN (X–Y). Komplement till head-mech.svg
(tvärsnittet, Y–Z). Visar: FAST ANHÅLL + fotocell i bakkant = stabil, repeterbar
NOLLA (lägg brädan an → encodern nollas; backa till anhållet → auto-omnollning),
encoder-mäthjul mot bandet = inkrement → ABSOLUT position, samt de tre raderna
LR400 / laserlinje / färgkamera. Huvudens vinklar/höjder (WD 760, kam 25°/Z689/Y321,
laser 50°/Z489/Y582, θ25°) finns i head-mech.svg.

  python tools/draw_position_subsystem.py   # -> position-subsystem.svg (+ .png)
"""
from __future__ import annotations
import os, math

WD, CAM_A, LAS_A = 760.0, 25.0, 50.0
camZ, camY = round(WD*math.cos(math.radians(CAM_A))), round(WD*math.sin(math.radians(CAM_A)))  # 689,321
lasZ, lasY = round(WD*math.cos(math.radians(LAS_A))), round(WD*math.sin(math.radians(LAS_A)))  # 489,582
BL, BWF = 500, 75
LR_LEAD, COL_OFF = 45, 40        # COL_OFF: färgkamera-offset (CAD som-byggt 39,75)
LRX = (60, 250, 440)

INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, GRID = "#f7f6f1", "#e6e4dc"
RED, GRN, BLUE, CY, AMB, PURP, STEEL = "#e8542c", "#2f9e6e", "#2f6fb0", "#1597a6", "#c98a16", "#a23ad6", "#8a9099"
WOOD = "#e9d8b0"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
W, H = 1660, 1060
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}">{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=1.4,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.4,rx=0,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}"{d} opacity="{op}"/>')
def circ(x,y,r,fill="none",st=INK,sw=1.4):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
def arrow(x1,y1,x2,y2,st=INK,w=1.6,head=9):
    line(x1,y1,x2,y2,st,w); a=math.atan2(y2-y1,x2-x1)
    for s in (0.45,-0.45): line(x2,y2,x2-head*math.cos(a-s),y2-head*math.sin(a-s),st,w)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
txt(40,52,"BRÄDPOSITION & NOLLA — OVANIFRÅN (X–Y)",22,"start",INK,700)
txt(40,76,"Fast anhåll + fotocell i bakkant = stabil repeterbar nolla · encoder mot bandet = inkrement → ABSOLUT position. Tvärsnitt/optik: head-mech.svg.",12,"start",MUTED)

X0, SX = 400, 1.96
def PX(x): return X0 + x*SX                        # längd X (0..500)
YC = 600                                           # laserlinjen (machine Y=0)
SY = 1.25
def PY(ymm): return YC + ymm*SY                    # +Y nedström (matning ↓)
bx0, bx1 = PX(0), PX(BL)

# ---- FAST ANHÅLL + fotocell (bakkant, uppströms) = ladd-/nolläge ----
yan = 150
rect(bx0-10, yan-14, (bx1-bx0)+20, 16, STEEL, INK, 1.8, 2)        # anhåll-balk längs X
txt(PX(BL/2), yan-22, "FAST ANHÅLL — lägg brädans bakkant emot (kvadrar + nollar)", 12, "middle", INK, 700)
# brädan i ladd-/nolläge (ligger an mot anhållet)
rect(bx0, yan+2, bx1-bx0, 64, WOOD, "#7a5230", 1.4, 0, dash="4 3", op=0.85)
txt(PX(BL/2), yan+40, "ladd-/nolläge (encoder = 0)", 11, "middle", "#7a5230", 700)
# fotocell vid anhållet
rect(bx0-46, yan-12, 20, 24, "#16212e", AMB, 1.4)
txt(bx0-52, yan+4, "FOTOCELL", 10, "end", AMB, 700)
txt(bx0-52, yan+18, "nollar vid anslag", 9, "end", AMB)

# feed
arrow(bx0-90, yan+90, bx0-90, YC-30, INK, 2, 11)
txt(bx0-104, (yan+90+YC)/2, "matning", 12, "end", INK, 700)
# nolloffset-mått anhåll → laserlinje
line(bx1+60, yan, bx1+60, YC, DIM, 0.8)
line(bx1+52, yan, bx1+68, yan, DIM, 0.8); line(bx1+52, YC, bx1+68, YC, DIM, 0.8)
txt(bx1+74, (yan+YC)/2, "inkrement från", 10, "start", MUTED, 700)
txt(bx1+74, (yan+YC)/2+15, "anhålls-nollan", 10, "start", MUTED, 700)

# ---- mätstationen: bräda mid-scan på laserlinjen ----
by0, by1 = PY(-BWF/2), PY(BWF/2)
rect(bx0, by0, bx1-bx0, by1-by0, WOOD, "#7a5230", 1.6)
txt(bx0+8, by0-8, "BRÄDA (500 × 75 mm) — under mätning", 11, "start", "#7a5230", 700)

# laserlinje (röd+grön) längs X — huvuden konvergerar hit (offset i head-mech)
line(bx0, YC-1.5, bx1, YC-1.5, RED, 3); line(bx0, YC+1.5, bx1, YC+1.5, GRN, 3)
for x in (0, BL): circ(PX(x), YC, 3, PURP, "#7a2fb0", 1)
rect(PX(BL/2)-235, YC-22, 470, 16, PAPER, "none", 0, op=0.95)
txt(PX(BL/2), YC-10, "laserlinje 500 mm — RÖD+GRÖN konvergerar hit (huvuden Y±582 / Z489 — se head-mech)", 9.5, "middle", PURP, 700)

# LR400-rad (−45 mm)
ylr = PY(-LR_LEAD)
line(bx0, ylr, bx1, ylr, CY, 1.4, dash="6 4")
for x in LRX: circ(PX(x), ylr, 4, CY, CY, 1); circ(PX(x), ylr, 7, "none", CY, 1)
rect(PX(BL/2)-175, ylr-21, 350, 15, PAPER, "none", 0, op=0.95)
txt(PX(BL/2), ylr-10, "3× LR400 · −45 mm — tjocklek-ankare (+ kant/skevhet)", 9.5, "middle", CY, 700)

# färg-linjekamera (+40 mm)
ycol = PY(COL_OFF)
line(bx0, ycol, bx1, ycol, BLUE, 1.6, dash="3 3")
rect(PX(BL/2)-165, ycol+8, 330, 15, PAPER, "none", 0, op=0.95)
txt(PX(BL/2), ycol+20, "FÄRG-LINJEKAMERA · +40 mm — ren färg (+ 2× vitljus)", 9.5, "middle", BLUE, 700)

# encoder-mäthjul mot bandet (inkrement)
ex = bx0-175
circ(ex, YC, 22, "#bfe6c8", GRN, 2); circ(ex, YC, 4, GRN, GRN, 1)
rect(ex-44, YC+26, 58, 22, "#16212e", INK, 1.4)
txt(ex, YC-30, "MÄTHJUL-ENCODER", 9.5, "middle", GRN, 700)
txt(ex, YC+64, "mot bandet → inkrement", 9.5, "middle", GRN)
txt(ex, YC+78, "(dubbelriktad, utanför FOV)", 9, "middle", GRN)

# offset-mått i feed (LR-lead 45 / färg 30)
xd = bx0-66
line(xd, ylr, bx0, ylr, DIM, 0.6); line(xd, YC, bx0, YC, DIM, 0.6); line(xd, ycol, bx0, ycol, DIM, 0.6)
def vd(y1,y2,lbl):
    arrow(xd,(y1+y2)/2,xd,y1,DIM,1); arrow(xd,(y1+y2)/2,xd,y2,DIM,1)
    line(xd-5,y1,xd+5,y1,DIM,0.8); line(xd-5,y2,xd+5,y2,DIM,0.8)
    rect(xd-52,(y1+y2)/2-9,46,18,PAPER,"none",0,op=0.95); txt(xd-29,(y1+y2)/2+5,lbl,9.5,"middle",INK,700,MONO)
vd(ylr, YC, "45"); vd(YC, ycol, "40")
txt(PX(10), by1+18, "0", 9, "start", MUTED); txt(PX(BL-10), by1+18, "500 mm (X)", 9, "end", MUTED)

# noter
nx, ny = 40, 905
rect(nx, ny, W-80, 124, "#fff", GRID, 1.4, rx=8)
notes = [
 "NOLLA = FAST ANHÅLL + FOTOCELL i bakkant. Lägg brädans bakkant mot anhållet → fotocellen ser anslag → encodern NOLLAS. Anhållet kvadrar dessutom brädan (ingen skevhet vid iladdning).",
 "ABSOLUT POSITION = encoder-inkrement (mäthjul mot bandet, dubbelriktad) räknat FRÅN anhålls-nollan. Stabil eftersom nollan är ett mekaniskt anslag du alltid kan återgå till.",
 "DUBBELRIKTAT: kör fram (encoder räknar upp), backa tillbaka (räknar ned). Når du anhållet igen → fotocell → AUTO-OMNOLLNING. Driftfri, repeterbar nolla varje cykel.",
 "Tre RADER nedström: LR400 −45 mm (tjocklek-ankare/kant/skevhet) · laserlinje 0 (profil, röd+grön) · färgkamera +40 mm (ren färg, ingen laser). Sys ihop via encoderpositionen.",
 "Huvudens exakta geometri (WD 760, kam 25°/Z689/Y321, laser 50°/Z489/Y582, θ25°, vankant, ytkamera) finns i head-mech.svg (tvärsnittet). Mäthjul mäter bandet → slir mildras med griff + mjukvarukant-korr.",
]
for i,l in enumerate(notes):
    txt(nx+14, ny+22+i*19, l, 10.2, "start", INK, 700 if i<3 else 400)

add('</svg>')
svg = "\n".join(out)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(root,"position-subsystem.svg"),"w",encoding="utf-8").write(svg)
print("skrev position-subsystem.svg")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(root,"position-subsystem.png"), output_width=W, output_height=H)
    print("skrev position-subsystem.png")
except Exception as e:
    print("PNG-render hoppover:", e)
