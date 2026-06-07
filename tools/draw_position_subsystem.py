#!/usr/bin/env python3
"""SCHEMA — brädposition: hur mäthjuls-encoder, fotocell och LR400 ger position,
sett FRÅN SIDAN längs matningen (Y horisontellt, Z vertikalt; brädans längd X går
in i bilden). Visar att positions-/ankargivarna sitter UPPSTRÖMS, utanför den
optiska FOV:n, så de inte stör linjekamerans rad eller de oblika laserstrålarna.

  python tools/draw_position_subsystem.py   # -> position-subsystem.svg (+ .png)
"""
from __future__ import annotations
import os, math

INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, GRID = "#f7f6f1", "#e6e4dc"
RED, GRN, BLUE, CY, AMB, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#1597a6", "#c98a16", "#a23ad6"
WOOD, BELT, ALU = "#e9d8b0", "#2b2f35", "#cfd3d8"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
W, H = 1640, 1020
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS,rot=None):
    tr=f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}"{tr}>{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=1.4,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.4,rx=0,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}"{d} opacity="{op}"/>')
def circ(x,y,r,fill="none",st=INK,sw=1.4,op=1):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def poly(pts,fill="none",st=INK,sw=1.4,op=1):
    p=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    add(f'<polygon points="{p}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def arrow(x1,y1,x2,y2,st=INK,w=1.6,head=9):
    line(x1,y1,x2,y2,st,w); a=math.atan2(y2-y1,x2-x1)
    for s in (0.45,-0.45): line(x2,y2,x2-head*math.cos(a-s),y2-head*math.sin(a-s),st,w)
def beam(x1,y1,x2,y2,col): line(x1,y1,x2,y2,col,1.3,dash="5 4",op=0.85)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
# rubrik
txt(40, 52, "BRÄDPOSITION — SIDOVY LÄNGS MATNINGEN", 22, "start", INK, 700)
txt(40, 76, "Y = matning (horisontellt) · Z = höjd · brädans längd X går IN i bilden (laserlinjen + kamerorad löper in i bilden, 500 mm)", 12.5, "start", MUTED)

BELT_Y = 720
BT = 30                         # bräd-tjocklek i px (~20 mm)
BOARD_L, BOARD_R = 470, 1230    # brädans utbredning (75 mm bredd — schematiskt utdraget)
# transportband
circ(150, BELT_Y+22, 24, ALU, INK, 1.6); circ(1490, BELT_Y+22, 24, ALU, INK, 1.6)
line(150, BELT_Y, 1490, BELT_Y, INK, 2.2)
line(150, BELT_Y+44, 1490, BELT_Y+44, INK, 2.2)
txt(150, BELT_Y+78, "transportband (24 V motor + Jrk G2 = hastighet)", 11, "start", MUTED)
# bräda
rect(BOARD_L, BELT_Y-BT, BOARD_R-BOARD_L, BT, WOOD, "#7a5230", 1.6)
txt(770, BELT_Y-BT-9, "BRÄDA — matas →", 12, "middle", "#7a5230", 700)
arrow(720, 120, 900, 120, INK, 2, 11); txt(810, 108, "matning", 13, "middle", INK, 700)
# ledande kant
line(BOARD_R, BELT_Y-BT-30, BOARD_R, BELT_Y+10, DIM, 1, dash="3 3")
txt(BOARD_R+6, BELT_Y-BT-18, "ledande kant", 10.5, "start", DIM)

def station_label(x, top, lines, col=INK):
    for i,(t,w) in enumerate(lines):
        txt(x, top+i*16, t, 10.5, "middle", col, w)

# ---- UPPSTRÖMS POSITIONS-/ANKARGIVARE (vänster, utanför FOV) ----
zoneU = (430, 150, 560, 760)
rect(zoneU[0], zoneU[1], zoneU[2], zoneU[3]-zoneU[1], "none", CY, 1.3, rx=10, dash="7 5", op=0.7)
txt(zoneU[0]+12, zoneU[1]+20, "UPPSTRÖMS — POSITION & ANKARE (utanför optisk FOV)", 12, "start", CY, 700)

# 1) Mäthjuls-encoder
ex = 540
circ(ex, BELT_Y-BT-30, 30, "#bfe6c8", GRN, 2)          # mäthjul mot brädans ovansida
circ(ex, BELT_Y-BT-30, 5, GRN, GRN, 2)
line(ex, BELT_Y-BT, ex, BELT_Y-BT-0.1, GRN, 1)         # kontaktpunkt
rect(ex+26, BELT_Y-BT-150, 56, 30, "#16212e", INK, 1.5)  # encoderkropp
line(ex+22, BELT_Y-BT-60, ex, BELT_Y-BT-44, INK, 2)      # fjäderarm
line(ex+54, BELT_Y-BT-120, ex+30, BELT_Y-BT-58, INK, 2)
station_label(ex, 250, [("MÄTHJUL-ENCODER",700),("E6B2-CWZ1X (line-driver)",400),
                        ("Ø40 + 1000P → 0,126 mm/puls",400),("rullar mot BRÄDAN",400)], GRN)
# 2) Fotocell (valfri)
px = 700
rect(px-8, BELT_Y-BT-86, 22, 30, "#16212e", INK, 1.4)
beam(px+3, BELT_Y-BT-70, px+3, BELT_Y-BT, AMB)
station_label(px+3, 250+74, [("FOTOCELL (valfri)",700),("ledande-kant-nolla",400)], AMB)
# 3) LR400 ankare
lx = 880
rect(lx-30, 150+150, 60, 34, "#16212e", INK, 1.6)
beam(lx, 150+184, lx, BELT_Y-BT, CY)
circ(lx, BELT_Y-BT, 3.2, CY, CY, 1)
station_label(lx, 150+128, [("3× LR400 (in i bilden)",700),("absolut tjocklek-ankare",400),
                            ("ger även kant + skevhet",400)], CY)

# ---- OPTISK MÄTZON (höger) ----
zoneO = (1010, 150, 470, 760)
rect(zoneO[0], zoneO[1], zoneO[2], zoneO[3]-zoneO[1], "none", PURP, 1.3, rx=10, dash="7 5", op=0.55)
txt(zoneO[0]+12, zoneO[1]+20, "OPTISK MÄTZON", 12, "start", PURP, 700)
laser_x = 1150
# dubbel-oblik laser: RÖD uppströms-sida, GRÖN nedströms-sida, samma linje
rx_, gx_ = laser_x-70, laser_x+70
rrect = (rx_-26, 300, 52, 26); grect = (gx_-26, 300, 52, 26)
rect(*rrect, "#16212e", RED, 1.6); rect(*grect, "#16212e", GRN, 1.6)
line(rx_, 326, laser_x, BELT_Y-BT, RED, 2)
line(gx_, 326, laser_x, BELT_Y-BT, GRN, 2)
circ(laser_x, BELT_Y-BT, 4, AMB, AMB, 1)               # laserlinjen (in i bilden)
txt(rx_, 292, "RÖD 650", 10.5, "middle", RED, 700)
txt(gx_, 292, "GRÖN 520", 10.5, "middle", GRN, 700)
txt(laser_x, BELT_Y-BT-12, "laserlinje (in i bilden, 500 mm)", 10, "middle", AMB, 700)
# ytkamera (linjekamera) + 2 vitljus
sx = laser_x
rect(sx-22, 180, 44, 34, "#16212e", INK, 1.6)
line(sx, 214, sx, BELT_Y-BT, BLUE, 1.6, dash="2 3")
rect(sx-150, 250, 40, 22, "#fff7d6", AMB, 1.4); rect(sx+110, 250, 40, 22, "#fff7d6", AMB, 1.4)
line(sx-118, 272, sx-6, BELT_Y-BT, AMB, 1.2, dash="4 3"); line(sx+128, 272, sx+6, BELT_Y-BT, AMB, 1.2, dash="4 3")
txt(sx-30, 200, "ytkamera", 11, "end", BLUE, 700); txt(sx-30, 215, "(linjerad + 2× vitljus)", 9.3, "end", BLUE)
txt(sx, BELT_Y+78, "ser bara sin rad → uppströms-givare syns aldrig i bilden", 10.5, "middle", BLUE)

# offset-mått (Y) mellan givare och laserlinjen
ydim = BELT_Y+120
def hd(x1,x2,lbl):
    line(x1,ydim-6,x1,ydim+6,DIM,0.9); line(x2,ydim-6,x2,ydim+6,DIM,0.9)
    arrow((x1+x2)/2,ydim,x1,ydim,DIM,1); arrow((x1+x2)/2,ydim,x2,ydim,DIM,1)
    rect((x1+x2)/2-len(lbl)*4, ydim-9, len(lbl)*8, 18, PAPER, "none", 0, op=0.95)
    txt((x1+x2)/2, ydim+5, lbl, 11, "middle", INK, 700, MONO)
line(ex, BELT_Y+30, ex, ydim, DIM, 0.7); line(lx, BELT_Y+30, lx, ydim, DIM, 0.7); line(laser_x, BELT_Y+30, laser_x, ydim, DIM, 0.7)
hd(lx, laser_x, "LR-lead ~45 mm"); hd(ex, lx, "encoder-offset (fast)")

# noter
nx, ny = 40, 880
rect(nx, ny, W-80, 110, "#fff", GRID, 1.4, rx=8)
notes = [
 "POSITION(rad)  =  encoder-pulser sedan LEDANDE-KANT-nollan  ×  mm/puls  +  fast offset givare→laserlinje.   Encodern = kontinuerlig förflyttning; nollan = kant-händelsen.",
 "LR400 svarar på din fråga: JA — när ledande kanten når LR-planet ser alla 3 brädan 'dyka upp' → det ger kant-nollan OCH skevnad. Så LR400 kan ERSÄTTA fotocellen som nolla.",
 "MEN LR400 ger bara tjocklek vid sina punkter, inte hur långt brädan färdats efteråt → encodern behövs ändå för positionen mellan/efter kanten.",
 "Alla uppströms-givare (mäthjul · fotocell · LR400) sitter FÖRE den optiska zonen och utanför FOV. Linjekameran exponerar EN rad och de oblika lasrarna träffar bara sin linje",
 "→ mäthjulet stör aldrig bilden (din poäng stämmer). Håll klustret inom brädans 75 mm så brädan täcker givarna under hela skanningen (här schematiskt utdraget).",
]
for i,l in enumerate(notes):
    txt(nx+14, ny+24+i*18, l, 10.6, "start", INK, 700 if i==0 else 400)

add('</svg>')
svg = "\n".join(out)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dst = os.path.join(root, "position-subsystem.svg")
open(dst, "w", encoding="utf-8").write(svg)
print("skrev", dst)
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(root, "position-subsystem.png"), output_width=W, output_height=H)
    print("skrev position-subsystem.png")
except Exception as e:
    print("PNG-render hoppover:", e)
