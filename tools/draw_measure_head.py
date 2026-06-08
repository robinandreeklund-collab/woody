#!/usr/bin/env python3
"""DESIGNFÖRSLAG — FAST MÄTHUVUD (en oblik kanal): aluminiumbottenplatta 50 mm bred,
kamera + laser i FASTA vinklar, centrum-tiltaxel för att rikta HELA huvudet (lås sen).
Geometri från head-mech: WD 710, kam 20°, laser 40°, θ 20°, baslinje 247, obliktet 30°.

    python tools/draw_measure_head.py   # -> measure-head.svg (+ .png)
"""
from __future__ import annotations
import os, math

WD, CAM_A, LAS_A, BASE = 710.0, 20.0, 40.0, 247.0
INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, GRID, PANEL = "#f7f6f1", "#e6e4dc", "#ecebe4"
RED, GRN, BLUE, CY, AMB, ALU, ALU2, WOOD = "#e8542c","#2f9e6e","#2f6fb0","#1597a6","#c98a16","#cfd2d6","#9aa0a6","#e9d8b0"
SANS="'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO="'IBM Plex Mono','DejaVu Sans Mono',monospace"
W,H=1700,1180
out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS,rot=None):
    tr=f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}"{tr}>{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=1.6,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}" stroke-linecap="round"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.6,rx=0,op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def circ(x,y,r,fill="none",st=INK,sw=1.6):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
def poly(pts,fill,st=INK,sw=1.4,op=1):
    d=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def arrow(x1,y1,x2,y2,st=INK,w=1.8,head=9):
    line(x1,y1,x2,y2,st,w); a=math.atan2(y2-y1,x2-x1)
    for s in (0.45,-0.45): line(x2,y2,x2-head*math.cos(a-s),y2-head*math.sin(a-s),st,w)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
txt(40,50,"FAST MÄTHUVUD — designförslag (en oblik kanal: kamera + laser i fasta vinklar)",21,"start",INK,700)
txt(40,74,"Aluminiumplatta 50 mm bred · kamera & laser FASTA (kalibreras en gång) · centrum-tiltaxel riktar HELA huvudet, lås sen. Geometri: WD 710, kam 20°, laser 40°, θ 20°, baslinje 247.",11.5,"start",MUTED)
line(40,86,W-40,86,INK,1.2)

# ===================== VY A: ARBETSPLAN (Y–Z) =====================
txt(60,128,"VY A — sidvy (arbetsplanet): optik + platta + tiltaxel",13,"start",INK,700)
s=0.62
Px,Py=560,860                                   # konvergenspunkt (laserlinje på brädan)
def ray(angle):                                 # endpunkt WD från P, vinkel från lod, åt +x
    a=math.radians(angle); return (Px+WD*s*math.sin(a), Py-WD*s*math.cos(a))
C=ray(CAM_A); L=ray(LAS_A)
# bräda + band
rect(Px-150,Py,300,16,WOOD,"#7a5230",1.4); txt(Px,Py+34,"BRÄDA (yta)  ·  laserlinje = konvergenspunkt",9.5,"middle","#7a5230",700)
line(Px-150,Py+22,Px+150,Py+22,"#444a52",4)
# lod
line(Px,Py,Px,Py-470,DIM,0.8,"4 4"); txt(Px+6,Py-455,"lod",9,"start",DIM,700)
# strålar
line(C[0],C[1],Px,Py,BLUE,1.6,"6 4"); dot=lambda x,y,r,c: circ(x,y,r,c,c,0)
line(L[0],L[1],Px,Py,RED,2.6)
circ(Px,Py,4,PURP if False else "#a23ad6","#7a2fb0",1)
# vinklar vid P
txt(Px+30,Py-70,"20°",10,"middle",BLUE,700); txt(Px+70,Py-50,"40°",10,"middle",RED,700)
txt(Px+150,Py-150,f"WD {WD:.0f}",10,"middle",RED,700,MONO,rot=-50)
txt(Px+60,Py-150,f"WD {WD:.0f}",10,"middle",BLUE,700,MONO,rot=-70)
# baslinje-platta längs C–L
ux,uy=(L[0]-C[0]),(L[1]-C[1]); blen=math.hypot(ux,uy); ux,uy=ux/blen,uy/blen
nx,ny=0.5,-0.866                                # normal bort från P (≈30° från lod)
th=10*s; ext=70                                 # plattjocklek (skala) + förlängning
A0=(C[0]-ux*ext, C[1]-uy*ext); A1=(L[0]+ux*ext, L[1]+uy*ext)
poly([A0,A1,(A1[0]+nx*th,A1[1]+ny*th),(A0[0]+nx*th,A0[1]+ny*th)],ALU,ALU2,1.6)  # bottenplatta
mid=((A0[0]+A1[0])/2+nx*th/2,(A0[1]+A1[1])/2+ny*th/2)
txt(A1[0]+nx*20,A1[1]+ny*20,"ALU-PLATTA 10 mm",9,"start",MUTED,700,rot=30)
# baslinje-mått
bx,by=(C[0]+L[0])/2,(C[1]+L[1])/2
txt(bx+nx*-26,by+ny*-26,f"baslinje {BASE:.0f}",9.5,"middle",INK,700,MONO,rot=30)
# kamera vid C (10° från plattnormal)
poly([(C[0]-16,C[1]-12),(C[0]+16,C[1]-12),(C[0]+16,C[1]+14),(C[0]-16,C[1]+14)],"#e2ecf6",BLUE,1.6)
rect(C[0]-9,C[1]+12,18,16,"#d8e6f4","#5f8fc0",1.4)         # objektiv+filter
txt(C[0]-22,C[1]-4,"KAMERA",9,"end",BLUE,700); txt(C[0]-22,C[1]+8,"(20°)",8,"end",MUTED,700)
# laser vid L
poly([(L[0]-14,L[1]-10),(L[0]+30,L[1]-10),(L[0]+30,L[1]+10),(L[0]-14,L[1]+10)],"#fde9e3",RED,1.6)
txt(L[0]+34,L[1]-2,"LASER (40°)",9,"start",RED,700)
# fast vinkel-not
txt(C[0]-40,C[1]-40,"FASTA vinklar (±10° mot plattnormal)",8.5,"end",INK,700)
# tiltaxel vid mitten av plattan
M=((A0[0]+A1[0])/2+nx*th/2,(A0[1]+A1[1])/2+ny*th/2)
circ(M[0],M[1],10,"#fff",INK,2); circ(M[0],M[1],3,INK,INK,0)
# två profiler som flankerar (visas som klossar bakom)
rect(M[0]+nx*16-14,M[1]+ny*16-14,28,28,PANEL,ALU2,1.4)
txt(M[0]+nx*52,M[1]+ny*52,"CENTRUM-TILTAXEL",9.5,"middle",INK,700,rot=30)
txt(M[0]+nx*52,M[1]+ny*52+14,"(monteras mellan 2 profiler)",8,"middle",MUTED,400,rot=30)
# tilt-arc
aa0,aa1=math.radians(-150),math.radians(-95)
ax0,ay0=M[0]+44*math.cos(aa0),M[1]+44*math.sin(aa0); ax1,ay1=M[0]+44*math.cos(aa1),M[1]+44*math.sin(aa1)
add(f'<path d="M {ax0:.1f} {ay0:.1f} A 44 44 0 0 1 {ax1:.1f} {ay1:.1f}" fill="none" stroke="{AMB}" stroke-width="2.2"/>')
arrow(ax1-3,ay1-3,ax1,ay1,AMB,2.2,8); txt(M[0]-40,M[1]-78,"TILT hela huvudet → rikta, LÅS sen",9,"middle",AMB,700)

# ===================== VY B: PLATTA (tvärsnitt 50 mm) =====================
txt(1080,128,"VY B — platta sett längs axeln (50 mm bred)",13,"start",INK,700)
qx,qy=1180,300
rect(qx,qy,260,18,ALU,ALU2,1.6)                            # platta 50 mm bred
txt(qx+130,qy-10,"ALU-PLATTA  50 mm bred × 10 mm",9.5,"middle",MUTED,700)
# centrumhål
circ(qx+130,qy+9,7,"#fff",INK,1.6); txt(qx+130,qy+40,"CENTRUMHÅL = tiltaxel (genom båda profiler)",9,"middle",INK,700)
# två profiler flankerar
for px in (qx-34,qx+260):
    rect(px,qy-14,34 if px<qx else 34,46,PANEL,ALU2,1.6)
    txt(px+17,qy-22,"2020-profil",8,"middle",MUTED,700)
# bult genom
line(qx-34,qy+9,qx+294,qy+9,INK,2.4); txt(qx+130,qy+58,"bult/axel genom centrumhål → tiltlager + LÅS (bricka/klamma)",9,"middle",MUTED,400)
# längd-not
qy2=qy+120
txt(qx+130,qy2,"PLATTANS LÄNGD (längs baslinjen):",10,"middle",INK,700)
txt(qx+130,qy2+18,"baslinje 247 + monteringsklackar ≈ 320 mm",9.5,"middle",MUTED,400)
# kamera/laser footprints på plattan (schematiskt)
rect(qx,qy2+40,70,40,"#e2ecf6",BLUE,1.5,4); txt(qx+35,qy2+64,"KAMERA",8.5,"middle",BLUE,700)
rect(qx+190,qy2+40,70,40,"#fde9e3",RED,1.5,4); txt(qx+225,qy2+64,"LASER",8.5,"middle",RED,700)
circ(qx+130,qy2+60,7,"#fff",INK,1.4); txt(qx+130,qy2+96,"← centrumhål (tiltaxel) mellan kamera & laser →",8.5,"middle",MUTED,400)

# ===================== MÅTT + NOTER =====================
panelx=1080
rect(panelx,560,560,250,"#fff",INK,1.4,8); rect(panelx,560,560,26,INK,INK,0,8)
txt(panelx+12,578,"MÅTT (fasta)",12,"start","#fff",700)
dims=[("Arbetsavstånd WD (var optik)","710 mm"),("Kameravinkel (från lod)","20°"),("Laservinkel (från lod)","40°"),
      ("Triangulering θ (kam↔laser)","20°"),("Baslinje (kam↔laser)","247 mm"),("Obliktet (plattnormal/lod)","30°"),
      ("Plattbredd","50 mm"),("Plattlängd ca","320 mm"),("Vinkel optik↔plattnormal","±10°")]
for i,(k,v) in enumerate(dims):
    yy=600+i*23
    if i%2: rect(panelx,yy-15,560,23,PANEL,"none",0)
    txt(panelx+12,yy,k,10,"start",MUTED,700); txt(panelx+548,yy,v,10.5,"end",INK,700,MONO)

rect(40,920,1600,230,"#fff",INK,1.4,8); rect(40,920,1600,26,INK,INK,0,8)
txt(52,938,"NOTER — bygg & montering",12,"start","#fff",700)
notes=[
 "FASTA vinklar: kamera och laser sitter permanent ±10° mot plattans normal (→ θ=20°). Kalibrera EN gång, lås. De ändras aldrig.",
 "TILT: hela huvudet vrids om CENTRUM-tiltaxeln (genom centrumhålet, mellan två profiler) för att rikta laserlinjen rätt på brädan + sätta obliktet ~30°. LÅS efter inriktning.",
 "Eftersom kamera+laser sitter på SAMMA styva platta rör sig deras geometri aldrig relativt varandra → stabil kalibrering (som en kommersiell sensor).",
 "TERMIK: laser i metallklämma med god kontakt mot plattan (+ ev. värmepasta) → plattan = kylfläns. INGEN fläkt (vibration!). 100 mW klarar plattkontakt med marginal.",
 "Montera kameran på samma platta (hjälper även dess värmeavledning). Plattjocklek ≥10 mm för styvhet; gärna förstyvningsklack vid laserklämman.",
 "Tiltaxeln bör ligga nära plattans tyngdpunkt/optiklinje → tilt = mest omriktning, lite translation. Lås med bult + tandbricka eller klämkloss.",
 "Spegla samma huvud för andra kanalen (grön) → båda konvergerar på samma laserlinje.",
 "BRÄDSTORLEK: bredd/längd = bara mjukvara (antal rader). Tjocklek mäts direkt inom mätområdet → INGEN tilt vid storleksbyte (bara om WD/bandhöjd ändras). Dimensionera djupfönstret för tjockleksspannet.",
]
for i,n in enumerate(notes):
    txt(52,962+i*25,"• "+n,10,"start",INK,400)

add('</svg>')
svg="\n".join(out)
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(root,"measure-head.svg"),"w",encoding="utf-8").write(svg)
print("skrev measure-head.svg")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(),write_to=os.path.join(root,"measure-head.png"),output_width=W,output_height=H)
    print("skrev measure-head.png")
except Exception as e:
    print("PNG-render hoppover:",e)
