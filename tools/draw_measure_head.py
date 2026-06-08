#!/usr/bin/env python3
"""KONSTRUKTIONSRITNING — MÄTHUVUD: ALU-BOTTENPLATTA (struktur) + PLASTKÅPA (skydd/look).
Alu-plattan bär kamera + laser i fasta vinklar (kam 20°/laser 40°, θ 20°, baslinje 247,
WD 710) och är kylfläns/kalibreringsbänk. Plastkåpan (3D-print) träs över, EJ bärande,
med aperturer för kamera/laser. Vyer: arbetsplan (monterat), sprängskiss, dellista, mått, ritningshuvud.

    python tools/draw_measure_head.py   # -> measure-head.svg (+ .png)
"""
from __future__ import annotations
import os, math

WD,CAM_A,LAS_A,BASE=710.0,20.0,40.0,247.0
INK,MUTED,DIM="#23262b","#6a6e74","#9aa0a6"
PAPER,GRID,PANEL="#f7f6f1","#e6e4dc","#ecebe4"
RED,GRN,BLUE,AMB,ALU,ALU2,PLAS,PLASE,STEEL,WOOD="#e8542c","#2f9e6e","#2f6fb0","#c98a16","#d7dadd","#9aa0a6","#3a3f45","#23262b","#7f868d","#e9d8b0"
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
def circ(x,y,r,fill="none",st=INK,sw=1.3,op=1):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def poly(pts,fill,st=INK,sw=1.3,op=1):
    d=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def ahead(x,y,ang,c=INK,L=7):
    poly([(x,y),(x-L*math.cos(ang-0.4),y-L*math.sin(ang-0.4)),(x-L*math.cos(ang+0.4),y-L*math.sin(ang+0.4))],c,c,0)
def hdim(x1,x2,y,label,c=INK):
    ln(x1,y,x2,y,c,0.9); ahead(x1,y,0,c); ahead(x2,y,math.pi,c); txt((x1+x2)/2,y-4,label,9,"middle",c,700,MONO)
def vdim(y1,y2,x,label,c=INK):
    ln(x,y1,x,y2,c,0.9); ahead(x,y1,-math.pi/2,c); ahead(x,y2,math.pi/2,c); txt(x-4,(y1+y2)/2,label,9,"middle",c,700,MONO,rot=-90)
def rbox(cx,cy,ux,uy,Ln,Wd,fill,st=INK,sw=1.3,op=1):
    px,py=-uy,ux
    poly([(cx-ux*Ln/2-px*Wd/2,cy-uy*Ln/2-py*Wd/2),(cx+ux*Ln/2-px*Wd/2,cy+uy*Ln/2-py*Wd/2),
          (cx+ux*Ln/2+px*Wd/2,cy+uy*Ln/2+py*Wd/2),(cx-ux*Ln/2+px*Wd/2,cy-uy*Ln/2+py*Wd/2)],fill,st,sw,op)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
rect(14,14,W-28,H-28,"none",INK,2); rect(22,22,W-44,H-44,"none",MUTED,0.7)
txt(44,52,"MÄTHUVUD — ALU-BOTTENPLATTA + PLASTKÅPA  ·  KONSTRUKTIONSRITNING",19,"start",INK,700)
txt(44,72,"Alu-platta = struktur/kylfläns/kalibreringsbänk (bär kamera+laser i fasta vinklar). Plastkåpa (3D-print) = skydd/utseende/ljusskydd, EJ bärande. Fasta vinklar 20°/40°, θ 20°, baslinje 247, WD 710. Mått i mm.",10.5,"start",MUTED)
ln(44,82,W-44,82,INK,1)

# =================================================== VY 1: MONTERAT (arbetsplan)
txt(60,112,"VY 1 — MONTERAT (arbetsplan, obliktet 30°): plastkåpa över alu-platta",12,"start",INK,700)
s=0.5; Px,Py=300,800
def ray(a): r=math.radians(a); return (Px+WD*s*math.sin(r),Py-WD*s*math.cos(r))
C=ray(CAM_A); L=ray(LAS_A)
rect(Px-150,Py,300,16,WOOD,"#7a5230",1.3); ln(Px-150,Py+24,Px+150,Py+24,"#444a52",4); txt(Px,Py+44,"BRÄDA (yta) · laserlinje",9,"middle","#7a5230",700)
ln(Px,Py,Px,Py-450,DIM,0.7,"5 5")
ux,uy=(L[0]-C[0]),(L[1]-C[1]); bl=math.hypot(ux,uy); ux,uy=ux/bl,uy/bl
nx,ny=0.5,-0.866
# PLASTKÅPA (yttre, translucent) över allt
ec=46*s; el=30*s; dk=78*s; dp=14*s
Cf=(C[0]-ux*ec,C[1]-uy*ec); Lf=(L[0]+ux*el,L[1]+uy*el)
poly([(Cf[0]-nx*dp,Cf[1]-ny*dp),(Lf[0]-nx*dp,Lf[1]-ny*dp),(Lf[0]+nx*dk,Lf[1]+ny*dk),(Cf[0]+nx*dk,Cf[1]+ny*dk)],PLAS,PLASE,1.6,0.30)
txt(Cf[0]+nx*dk+6,Cf[1]+ny*dk+2,"PLASTKÅPA (3D-print, translucent visad)",8.5,"start",PLASE,700,rot=34)
# ALU-PLATTA (inre struktur, solid)
ap=20*s; ad=10*s
poly([(Cf[0]+nx*ap,Cf[1]+ny*ap),(Lf[0]+nx*ap,Lf[1]+ny*ap),(Lf[0]+nx*(ap+ad),Lf[1]+ny*(ap+ad)),(Cf[0]+nx*(ap+ad),Cf[1]+ny*(ap+ad))],ALU,INK,1.5)
txt((Cf[0]+Lf[0])/2+nx*(ap+22),(Cf[1]+Lf[1])/2+ny*(ap+22),"ALU-BOTTENPLATTA",8.5,"middle",MUTED,700,rot=34)
# kamera + laser på plattan
cdx,cdy=(Px-C[0])/(WD*s),(Py-C[1])/(WD*s); ldx,ldy=(Px-L[0])/(WD*s),(Py-L[1])/(WD*s)
rbox(C[0]-cdx*14+nx*8,C[1]-cdy*14+ny*8,cdx,cdy,24,16,"#e2ecf6",BLUE,1.3)
rect(C[0]-6,C[1]-6,12,12,"#cfe0f2",BLUE,1.2,2); ln(C[0],C[1],Px,Py,BLUE,1.3,"6 4")
rbox(L[0]-ldx*20+nx*6,L[1]-ldy*20+ny*6,ldx,ldy,46,10,"#fde9e3",RED,1.3); ln(L[0],L[1],Px,Py,RED,2.3)
txt(C[0]-nx*8-20,C[1]-22,"KAMERA",8.5,"end",BLUE,700); txt(L[0]+ux*14+8,L[1]+uy*14,"LASER",8.5,"start",RED,700)
# aperturer i kåpan (gap mot bräda)
txt(Px+40,Py-360,"aperturer i kåpan",8,"start",PLASE,700)
# vinklar/WD/baslinje
txt(Px+26,Py-66,"20°",9,"middle",BLUE,700); txt(Px+66,Py-46,"40°",9,"middle",RED,700)
txt(((C[0]+Px)/2)-12,(C[1]+Py)/2,"WD 710",8.5,"middle",BLUE,700,MONO,rot=-70)
txt(((L[0]+Px)/2)+14,(L[1]+Py)/2,"WD 710",8.5,"middle",RED,700,MONO,rot=-50)
txt(Px-6,Py-300,"obliktet 30°",8.5,"end",MUTED,700)
txt((C[0]+L[0])/2-nx*4,(C[1]+L[1])/2-ny*4-6,"baslinje 247",8.5,"middle",INK,700,MONO,rot=34)

# =================================================== VY 2: SPRÄNGSKISS (utfälld)
EX,EY=780,150
txt(EX,EY-16,"VY 2 — SPRÄNGSKISS (utfälld för tydlighet): kåpa träs över plattan",12,"start",INK,700)
sw=2.6; plen=330*sw/2.6*0.9; plen=300*1.0  # plattlängd i px (skalad fritt)
plen=300; px0=EX+30; pcy=EY+150
# ALU-BOTTENPLATTA (nederst) + kamera/laser-fästen
rect(px0,pcy,plen,18,ALU,INK,1.6,3)
txt(px0+plen/2,pcy+44,"ALU-BOTTENPLATTA — struktur · kylfläns · kalibreringsbänk (styv)",9.5,"middle",MUTED,700)
# kamera-fäste (vinkelkloss) + kamera
poly([(px0+30,pcy),(px0+78,pcy),(px0+78,pcy-26),(px0+44,pcy-40)],ALU2,INK,1.3); txt(px0+40,pcy-46,"10°-kloss",7.5,"start",MUTED,700)
rect(px0+40,pcy-58,30,20,"#e2ecf6",BLUE,1.3,2); txt(px0+55,pcy-64,"KAMERA",7.5,"middle",BLUE,700)
# laser-fäste (V-block) + laser
poly([(px0+plen-90,pcy),(px0+plen-40,pcy),(px0+plen-40,pcy-30),(px0+plen-70,pcy-44)],ALU2,INK,1.3)
rect(px0+plen-86,pcy-54,46,12,"#fde9e3",RED,1.3,3); txt(px0+plen-63,pcy-60,"LASER",7.5,"middle",RED,700)
# pelare/standoff för kåpan
for sx in (px0+12,px0+plen-12):
    rect(sx-4,pcy-6,8,-26 if False else 8,PANEL,STEEL,1.2); circ(sx,pcy-22,3,"#fff",STEEL,1)
    ln(sx,pcy,sx,pcy-22,STEEL,1.2)
txt(px0+plen/2,pcy-2-90,"",7)  # spacer
# PLASTKÅPA (ovanför, utfälld uppåt)
ky=EY+10
poly([(px0-6,ky+34),(px0+plen+6,ky+34),(px0+plen+6,ky+10),(px0+plen-20,ky-6),(px0+20,ky-6),(px0-6,ky+10)],PLAS,PLASE,1.6,0.85)
txt(px0+plen/2,ky+14,"PLASTKÅPA (3D-print) — skydd · utseende · matt svart insida",9,"middle","#fff",700)
# aperturer (hål i kåpan)
rect(px0+46,ky+24,30,12,"#0d0f12",PLASE,1,2); txt(px0+61,ky+48,"kamera-",7,"middle",PLASE,700); txt(px0+61,ky+56,"apertur",7,"middle",PLASE,700)
rect(px0+plen-86,ky+24,46,10,"#0d0f12",PLASE,1,2); txt(px0+plen-63,ky+48,"laser-slits",7,"middle",PLASE,700)
circ(px0+plen/2+40,ky+30,4,"#16212e",PLASE,1); txt(px0+plen/2+40,ky+48,"LED/kontakt",7,"middle",PLASE,700)
# monteringsarrows + skruvar
for sx in (px0+12,px0+plen-12):
    ln(sx,ky+38,sx,pcy-26,STEEL,1,"4 3"); ahead(sx,pcy-28,math.pi/2,STEEL,7)
    circ(sx,ky+20,2.5,"#fff",STEEL,1)
txt(px0+plen+16,(ky+pcy)/2,"kåpan skruvas till plattans pelare",8,"start",STEEL,700)
txt(px0+plen+16,(ky+pcy)/2+14,"med SPEL runt optiken (ingen förspänning)",7.8,"start",MUTED,400)
# monteringsyta under plattan (M6 mot portal)
rect(px0+plen/2-50,pcy+60,100,16,ALU2,INK,1.3,2)
for hx in (-30,-10,10,30): circ(px0+plen/2+hx,pcy+68,3,"#fff",INK,1.1)
txt(px0+plen/2,pcy+92,"monteringsyta M6 → portal/tiltbracket (under plattan)",8.5,"middle",INK,700)

# =================================================== DELLISTA
LX=1180
rect(LX,150,660,230,"#fff",INK,1.3,7); rect(LX,150,660,26,INK,INK,0,7)
txt(LX+10,168,"DELLISTA",12,"start","#fff",700)
items=[("1","Alu-bottenplatta (struktur)","6082/6063, ≥8–10 mm"),
       ("2","Plastkåpa (3D-print)","PETG/ASA, svart matt"),
       ("3","Kamera Hikrobot MV-CS050-10UM","på 10°-kloss"),
       ("4","Objektiv 12 mm + bandpass 650/525","M30,5"),
       ("5","Linjelaser MZLaser Powell","Ø18×99, V-block 10°"),
       ("6","Kåpskruvar + pelare/standoff","M3, m. spel"),
       ("7","Monteringsyta M6 (mot portal)","tiltbracket")]
txt(LX+14,196,"POS",8.5,"start",MUTED,700,MONO); txt(LX+70,196,"BENÄMNING",8.5,"start",MUTED,700,MONO); txt(LX+470,196,"SPEC",8.5,"start",MUTED,700,MONO)
ln(LX+10,202,LX+650,202,DIM,0.8)
for i,(p,n,sp_) in enumerate(items):
    yy=222+i*23
    if i%2: rect(LX+8,yy-15,644,23,PANEL,"none",0)
    circ(LX+24,yy-4,8,"#fff",INK,1.2); txt(LX+24,yy,p,8.5,"middle",INK,700,MONO)
    txt(LX+70,yy,n,9.3,"start",INK,700); txt(LX+470,yy,sp_,8.8,"start",MUTED,400)

# =================================================== MÅTTABELL
rect(LX,400,660,180,"#fff",INK,1.3,7); rect(LX,400,660,26,INK,INK,0,7)
txt(LX+10,418,"FASTA MÅTT & VINKLAR",12,"start","#fff",700)
dims=[("Arbetsavstånd WD","710 mm"),("Kamera / laser (lod)","20° / 40°"),("Triangulering θ","20°"),
      ("Baslinje","247 mm"),("Obliktet","30°"),("Plattjocklek","≥8–10 mm")]
for i,(k,v) in enumerate(dims):
    yy=440+i*23
    if i%2: rect(LX+8,yy-15,644,23,PANEL,"none",0)
    txt(LX+14,yy,k,9.6,"start",MUTED,700); txt(LX+646,yy,v,9.8,"end",INK,700,MONO)

# =================================================== NOTER
rect(LX,600,660,290,"#fff",INK,1.3,7); rect(LX,600,660,24,INK,INK,0,7)
txt(LX+10,617,"NOTER — funktion & bygg",12,"start","#fff",700)
for i,n in enumerate([
 "ALU-PLATTAN bär ALLT: kamera + laser i fasta vinklar (kalibreras en gång, lås).",
 "  Den är kylfläns (laser i metallkontakt) OCH kalibreringsbänk → måste vara styv.",
 "PLASTKÅPAN är EJ bärande: skyddar mot damm/ljus + ger looken. Skruvas till",
 "  plattans pelare med SPEL runt optiken → ingen kraft/förspänning på optiken",
 "  → påverkar ALDRIG kalibreringen.",
 "Kåpa: matt SVART insida (strökljus-/reflexskydd). Material PETG/ASA, svart.",
 "  Lämna apertur/ventilation öppen så laserns värme inte byggs upp (100 mW ok).",
 "Aperturer: kamera-fönster + laser-slits (öppna; bandpass sitter på objektivet).",
 "  I dammig miljö ev. skyddsglas — då LUTAT för att undvika reflex.",
 "Montering: plattans M6-yta mot portal/tiltbracket (slits för aim, lås sen).",
 "JUSTERING: bara (1) HELA huvudet tiltas (aim → lås) + (2) lasern ROTERAS om egen axel",
 "  (linje längs X, parallellt kamerans rader → lås). Kameran HELT FAST. Finkalib.= MJUKVARA. Spegla för grön.",
]): txt(LX+14,640+i*19,("• "+n if not n.startswith("  ") else n),8.8,"start",INK,400)

tb_x,tb_y=LX,910; rect(tb_x,tb_y,660,150,"#fff",INK,1.5,7)
ln(tb_x,tb_y+96,tb_x+660,tb_y+96,INK,1); ln(tb_x+400,tb_y,tb_x+400,tb_y+96,INK,1); ln(tb_x+400,tb_y+30,tb_x+660,tb_y+30,INK,1); ln(tb_x+400,tb_y+63,tb_x+660,tb_y+63,INK,1)
txt(tb_x+16,tb_y+34,"VIRKESSKANNER",14,"start",INK,700); txt(tb_x+16,tb_y+58,"MÄTHUVUD — alu-platta + plastkåpa",11.5,"start",INK,700)
txt(tb_x+16,tb_y+82,"Alu 6082/6063 + 3D-print PETG/ASA",9.5,"start",MUTED)
txt(tb_x+410,tb_y+20,"RITN-NR",8,"start",MUTED,700); txt(tb_x+648,tb_y+22,"MH-003",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+52,"MÅTT",8,"start",MUTED,700); txt(tb_x+648,tb_y+54,"mm",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+85,"VINKLAR",8,"start",MUTED,700); txt(tb_x+648,tb_y+87,"20°/40° fasta",10,"end",INK,700,MONO)
txt(tb_x+16,tb_y+118,"Struktur = alu (styv). Kåpa = plast (ej bärande, fri från optiken).",9,"start",MUTED,400)
txt(tb_x+16,tb_y+138,"Optik-geometri per head-mech. Tilt/aim via monteringsyta, lås sen.",9,"start",MUTED,400)

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
