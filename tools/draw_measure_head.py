#!/usr/bin/env python3
"""KONSTRUKTIONSRITNING — INTEGRERAT MÄTHUVUD (line-laser 3D-kamera-stil).
Kamera + laser inbyggda i ETT vinklat hölje med plan monteringsyta + M6-bultmönster
(à la Hikrobot). Fasta vinklar (kam 20° / laser 40°, θ 20°, baslinje 247), WD 710.
Vyer: arbetsplan (hölje + optik), monteringsyta (baksida, hålbild), gavel/bredd,
dellista, måttabell, ritningshuvud.  Mått i mm.

    python tools/draw_measure_head.py   # -> measure-head.svg (+ .png)
"""
from __future__ import annotations
import os, math

WD,CAM_A,LAS_A,BASE=710.0,20.0,40.0,247.0
ENV_L,ENV_W,ENV_D=330.0,60.0,80.0       # hölje: längd, bredd, djup
INK,MUTED,DIM="#23262b","#6a6e74","#9aa0a6"
PAPER,GRID,PANEL="#f7f6f1","#e6e4dc","#ecebe4"
RED,GRN,BLUE,AMB,SHELL,SHELL2,STEEL,WOOD="#e8542c","#2f9e6e","#2f6fb0","#c98a16","#3a3f45","#5b626a","#7f868d","#e9d8b0"
SANS="'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO="'IBM Plex Mono','DejaVu Sans Mono',monospace"
W,H=1880,1320
out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=11,a="start",f=INK,w=400,fam=SANS,rot=None):
    tr=f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}"{tr}>{esc(s)}</text>')
def ln(x1,y1,x2,y2,st=INK,w=1.3,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}" stroke-linecap="round"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.3,rx=0,op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def circ(x,y,r,fill="none",st=INK,sw=1.3):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
def poly(pts,fill,st=INK,sw=1.3,op=1):
    d=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def path(d,fill,st=INK,sw=1.3):
    add(f'<path d="{d}" fill="{fill}" stroke="{st}" stroke-width="{sw}" stroke-linejoin="round"/>')
def ahead(x,y,ang,c=INK,L=7):
    poly([(x,y),(x-L*math.cos(ang-0.4),y-L*math.sin(ang-0.4)),(x-L*math.cos(ang+0.4),y-L*math.sin(ang+0.4))],c,c,0)
def hdim(x1,x2,y,label,c=INK):
    ln(x1,y,x2,y,c,0.9); ahead(x1,y,0,c); ahead(x2,y,math.pi,c); txt((x1+x2)/2,y-4,label,9,"middle",c,700,MONO)
def vdim(y1,y2,x,label,c=INK):
    ln(x,y1,x,y2,c,0.9); ahead(x,y1,-math.pi/2,c); ahead(x,y2,math.pi/2,c); txt(x-4,(y1+y2)/2,label,9,"middle",c,700,MONO,rot=-90)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
rect(14,14,W-28,H-28,"none",INK,2); rect(22,22,W-44,H-44,"none",MUTED,0.7)
txt(44,52,"INTEGRERAT MÄTHUVUD — line-laser 3D-kamera-stil  ·  KONSTRUKTIONSRITNING",19,"start",INK,700)
txt(44,72,"Kamera + laser i ETT vinklat hölje · fasta vinklar (kam 20° / laser 40°, θ 20°, baslinje 247) · plan monteringsyta + M6-mönster · WD 710. Mått i mm. Ej skalenlig mellan vyer.",10.5,"start",MUTED)
ln(44,82,W-44,82,INK,1)

# =================================================== VY 1: ARBETSPLAN (hölje + optik)
txt(60,112,"VY 1 — ARBETSPLAN: integrerat hölje i läge (obliktet 30°)",12,"start",INK,700)
s=0.5; Px,Py=300,790
def ray(a): r=math.radians(a); return (Px+WD*s*math.sin(r),Py-WD*s*math.cos(r))
C=ray(CAM_A); L=ray(LAS_A)
# bräda
rect(Px-150,Py,300,16,WOOD,"#7a5230",1.3); ln(Px-150,Py+24,Px+150,Py+24,"#444a52",4); txt(Px,Py+44,"BRÄDA (yta) · laserlinje",9,"middle","#7a5230",700)
ln(Px,Py,Px,Py-440,DIM,0.7,"5 5")
# axlar
ux,uy=(L[0]-C[0]),(L[1]-C[1]); bl=math.hypot(ux,uy); ux,uy=ux/bl,uy/bl       # längs baslinjen
nx,ny=0.5,-0.866                                                            # ut från brädan (mot baksida)
# HÖLJE: svept kropp längs C–L, djup ENV_D åt +n, kamera-pod vid C, laser-nos vid L
dpx=ENV_D*s; ecx=46*s; elx=30*s
Cf=(C[0]-ux*ecx, C[1]-uy*ecx); Lf=(L[0]+ux*elx, L[1]+uy*elx)               # front-hörn (mot bräda)
Cb=(Cf[0]+nx*dpx, Cf[1]+ny*dpx); Lb=(Lf[0]+nx*dpx, Lf[1]+ny*dpx)          # bak-hörn (monteringssida)
# kamera-pod höjer baksidan vid C
podx=(C[0]+nx*(dpx+14), C[1]+ny*(dpx+14))
shell_pts=[Cf,Lf,Lb,(L[0]+nx*dpx,L[1]+ny*dpx),
           ( (C[0]+L[0])/2+nx*dpx, (C[1]+L[1])/2+ny*dpx ),
           (Cb[0]+nx*14,Cb[1]+ny*14),(Cf[0]+nx*14,Cf[1]+ny*14)]
# enklare snyggt hölje: front (Cf->Lf), gavel (Lf->Lb), baksida (Lb->Cb m. pod-bula), gavel (Cb->Cf)
path(f"M {Cf[0]:.1f} {Cf[1]:.1f} L {Lf[0]:.1f} {Lf[1]:.1f} L {Lb[0]:.1f} {Lb[1]:.1f} "
     f"L {(C[0]+nx*dpx):.1f} {(C[1]+ny*dpx):.1f} L {(Cb[0]+nx*12):.1f} {(Cb[1]+ny*12):.1f} "
     f"L {(Cf[0]+nx*12):.1f} {(Cf[1]+ny*12):.1f} Z", SHELL, SHELL2, 1.6)
# kamera-fönster (front vid C) + sikt
cdx,cdy=(Px-C[0])/(WD*s),(Py-C[1])/(WD*s)
rect(C[0]-7,C[1]-7,14,14,"#cfe0f2",BLUE,1.4,2)
ln(C[0],C[1],Px,Py,BLUE,1.3,"6 4"); txt(C[0]-nx*18,C[1]-18,"KAMERA-fönster",8.5,"end",BLUE,700)
# laser-fönster (front vid L) + stråle
rect(L[0]-6,L[1]-6,12,12,"#f6c9bd",RED,1.4,2); ln(L[0],L[1],Px,Py,RED,2.3)
txt(L[0]+ux*16+8,L[1]+uy*16,"LASER-apertur",8.5,"start",RED,700)
# status-LED + kontakt på baksidan
midb=((Cb[0]+Lb[0])/2,(Cb[1]+Lb[1])/2)
for k in range(3): circ(midb[0]+nx*-2+ux*(k-1)*8, midb[1]+ny*-2+uy*(k-1)*8,2.2,"#bfe6c8",GRN,0.8)
txt(midb[0]+nx*14,midb[1]+ny*14,"status-LED",7.5,"middle",MUTED,700,rot=34)
# vinklar/WD
txt(Px+26,Py-66,"20°",9,"middle",BLUE,700); txt(Px+66,Py-46,"40°",9,"middle",RED,700)
txt(((C[0]+Px)/2)-12,(C[1]+Py)/2,"WD 710",8.5,"middle",BLUE,700,MONO,rot=-70)
txt(((L[0]+Px)/2)+14,(L[1]+Py)/2,"WD 710",8.5,"middle",RED,700,MONO,rot=-50)
txt(Px-6,Py-300,"obliktet 30°",8.5,"end",MUTED,700)
# monteringsyta-pil
ln(Lb[0]+nx*6,Lb[1]+ny*6, Lb[0]+nx*30,Lb[1]+ny*30, AMB,1.2)
txt(Lb[0]+nx*36,Lb[1]+ny*36,"MONTERINGSYTA (baksida)",8.5,"start",AMB,700,rot=34)
# baslinje
txt((C[0]+L[0])/2-nx*40,(C[1]+L[1])/2-ny*40,"baslinje 247",8.5,"middle",INK,700,MONO,rot=34)

# =================================================== VY 2: MONTERINGSYTA (baksida)
MX,MY=820,150; sm=1.45
mlw=ENV_L*sm; mlh=ENV_W*sm
txt(MX,MY-16,"VY 2 — MONTERINGSYTA (baksida) · 8×M6 bultmönster",12,"start",INK,700)
rect(MX,MY,mlw,mlh,SHELL,SHELL2,1.6,6)
# 8-M6 i 2 kolumner × 4 rader, 30 mm-rutnät, centrerat
cxs=[MX+mlw/2-15*sm, MX+mlw/2+15*sm]; rys=[MY+mlh/2+(i-1.5)*30*sm for i in range(4)]
for cx in cxs:
    for ry in rys: circ(cx,ry,4,"#fff",INK,1.4)
txt(MX+mlw/2,MY+mlh+20,"8× M6 ▼8 (30 mm rutnät) — mot portal / tiltbracket",8.5,"middle",INK,700)
hdim(cxs[0],cxs[1],MY+mlh+40,"30",MUTED)
vdim(rys[0],rys[1],MX-18,"30",MUTED)
hdim(MX,MX+mlw,MY-8,f"{ENV_L:.0f}",INK)
vdim(MY,MY+mlh,MX+mlw+18,f"{ENV_W:.0f}",INK)
# kontakt-/kabeluttag
rect(MX+mlw-46,MY+mlh/2-10,30,20,"#16212e",STEEL,1.2,3); txt(MX+mlw-31,MY+mlh+20-40,"kabel",7.5,"middle",MUTED,700)

# =================================================== VY 3: GAVEL (bredd/djup)
GX,GY=820,420; sg=1.45
gw=ENV_W*sg; gd=ENV_D*sg
txt(GX,GY-16,"VY 3 — GAVEL (bredd × djup)",12,"start",INK,700)
poly([(GX,GY),(GX+gw,GY),(GX+gw,GY+gd-18),(GX+gw-14,GY+gd),(GX+14,GY+gd),(GX,GY+gd-18)],SHELL,SHELL2,1.6)
txt(GX+gw/2,GY+gd/2,"hölje",9,"middle","#fff",700)
hdim(GX,GX+gw,GY-8,f"{ENV_W:.0f}  (bredd)",INK)
vdim(GY,GY+gd,GX-18,f"{ENV_D:.0f}  (djup)",INK)
txt(GX+gw+16,GY+10,"front = kamera/laser-apertur",8,"start",MUTED,700)
txt(GX+gw+16,GY+gd-6,"baksida = monteringsyta (M6)",8,"start",MUTED,700)

# =================================================== DELLISTA
LX=1180
rect(LX,150,660,250,"#fff",INK,1.3,7); rect(LX,150,660,26,INK,INK,0,7)
txt(LX+10,168,"DELLISTA",12,"start","#fff",700)
items=[("1","Hölje, integrerat (se NOTER för tillv.)","alu · ~330×60×80"),
       ("2","Kamera Hikrobot MV-CS050-10UM","inbyggd, 20°"),
       ("3","Objektiv 12 mm + bandpass 650/525","M30,5-filter"),
       ("4","Linjelaser MZLaser Powell","Ø18×99, inbyggd, 40°"),
       ("5","Inre vinkelfäste/dog-leg (fasta vinklar)","alu, CNC el. 2 plattor"),
       ("6","Monteringsyta 8×M6 (baksida)","30 mm rutnät"),
       ("7","Kabeluttag (kamera USB3 / laser DC)","baksida/gavel")]
txt(LX+14,196,"POS",8.5,"start",MUTED,700,MONO); txt(LX+70,196,"BENÄMNING",8.5,"start",MUTED,700,MONO); txt(LX+470,196,"SPEC",8.5,"start",MUTED,700,MONO)
ln(LX+10,202,LX+650,202,DIM,0.8)
for i,(p,n,sp_) in enumerate(items):
    yy=222+i*24
    if i%2: rect(LX+8,yy-15,644,24,PANEL,"none",0)
    circ(LX+24,yy-4,8,"#fff",INK,1.2); txt(LX+24,yy,p,8.5,"middle",INK,700,MONO)
    txt(LX+70,yy,n,9.3,"start",INK,700); txt(LX+470,yy,sp_,8.8,"start",MUTED,400)

# =================================================== MÅTTABELL
rect(LX,420,660,220,"#fff",INK,1.3,7); rect(LX,420,660,26,INK,INK,0,7)
txt(LX+10,438,"FASTA MÅTT & VINKLAR",12,"start","#fff",700)
dims=[("Arbetsavstånd WD","710 mm"),("Kameravinkel / laservinkel (lod)","20° / 40°"),
      ("Triangulering θ","20°"),("Baslinje (kam↔laser)","247 mm"),("Obliktet (front↔lod)","30°"),
      ("Hölje L×B×D (ca)","330 × 60 × 80 mm"),("Monteringsmönster","8× M6, 30 mm rutnät")]
for i,(k,v) in enumerate(dims):
    yy=460+i*23
    if i%2: rect(LX+8,yy-15,644,23,PANEL,"none",0)
    txt(LX+14,yy,k,9.6,"start",MUTED,700); txt(LX+646,yy,v,9.8,"end",INK,700,MONO)

# =================================================== NOTER
rect(LX,660,660,230,"#fff",INK,1.3,7); rect(LX,660,660,24,INK,INK,0,7)
txt(LX+10,677,"NOTER — tillverkning & funktion",12,"start","#fff",700)
for i,n in enumerate([
 "TILLVERKNING — två vägar:",
 "  A) Produktlik: CNC-fräst aluminiumhölje (dyrt, snyggast).",
 "  B) Prototyp (rek.): inre VINKELFÄSTE (dog-leg) i alu som låser kam 20° /",
 "     laser 40°, + lätt 3D-printad/plåt-KÅPA för utseendet. Samma funktion.",
 "Vinklar kam/laser FASTA (kalibreras en gång). Kamera+laser på samma styva",
 "  inre fäste → geometrin rör sig aldrig relativt varandra (stabil kalibrering).",
 "Monteras via baksidans 8×M6 mot portal/tiltbracket (slits för fin-aim, lås sen).",
 "Termik: laser i metallkontakt mot inre fästet/höljet = kylfläns. INGEN fläkt.",
 "Storleksbyte (bredd/längd/tjocklek) = bara mjukvara inom mätområdet. Spegla för grön.",
]): txt(LX+14,700+i*20,("• "+n if not n.startswith("  ") else n),9.0,"start",INK,400)

tb_x,tb_y=LX,910; rect(tb_x,tb_y,660,150,"#fff",INK,1.5,7)
ln(tb_x,tb_y+96,tb_x+660,tb_y+96,INK,1); ln(tb_x+400,tb_y,tb_x+400,tb_y+96,INK,1); ln(tb_x+400,tb_y+30,tb_x+660,tb_y+30,INK,1); ln(tb_x+400,tb_y+63,tb_x+660,tb_y+63,INK,1)
txt(tb_x+16,tb_y+34,"VIRKESSKANNER",14,"start",INK,700); txt(tb_x+16,tb_y+58,"INTEGRERAT MÄTHUVUD",12,"start",INK,700)
txt(tb_x+16,tb_y+82,"alu-hölje · M6-montering",9.5,"start",MUTED)
txt(tb_x+410,tb_y+20,"RITN-NR",8,"start",MUTED,700); txt(tb_x+648,tb_y+22,"MH-002",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+52,"MÅTT",8,"start",MUTED,700); txt(tb_x+648,tb_y+54,"mm",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+85,"VINKLAR",8,"start",MUTED,700); txt(tb_x+648,tb_y+87,"20°/40° fasta",10,"end",INK,700,MONO)
txt(tb_x+16,tb_y+118,"Optik-geometri per head-mech. Tilt/aim via monteringsyta, lås sen.",9,"start",MUTED,400)
txt(tb_x+16,tb_y+138,"Allt övrigt fast — integrerat hus som en kommersiell sensor.",9,"start",MUTED,400)

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
