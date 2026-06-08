#!/usr/bin/env python3
"""KONSTRUKTIONSRITNING — FAST MÄTHUVUD (en oblik kanal).
Verkliga komponenter (Hikrobot MV-CS050 + 12mm/bandpass, MZLaser Ø18×99 Powell),
alu-bottenplatta 50 mm bred, fasta vinklar (kam 20° / laser 40°, θ 20°), centrum-
tiltaxel mellan två 2020-profiler. Vyer: arbetsplan, plan (hålbild), snitt A–A,
dellista, måttabell, ritningshuvud.

    python tools/draw_measure_head.py   # -> measure-head.svg (+ .png)
"""
from __future__ import annotations
import os, math

WD, CAM_A, LAS_A, BASE, TH = 710.0, 20.0, 40.0, 247.0, 10.0
PLATE_L, PLATE_W = 330.0, 50.0
CAM_OFF = (PLATE_L-BASE)/2            # 41.5 mm från vänster datum till kamera-c
LAS_OFF = CAM_OFF+BASE               # 288.5
PIV_OFF = PLATE_L/2                  # 165 (=baslinjens mitt)
INK,MUTED,DIM="#23262b","#6a6e74","#9aa0a6"
PAPER,GRID,PANEL="#f7f6f1","#e6e4dc","#ecebe4"
RED,GRN,BLUE,AMB,ALU,ALU2,STEEL,WOOD="#e8542c","#2f9e6e","#2f6fb0","#c98a16","#d7dadd","#9aa0a6","#7f868d","#e9d8b0"
SANS="'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO="'IBM Plex Mono','DejaVu Sans Mono',monospace"
W,H=1880,1300
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
def ahead(x,y,ang,c=INK,L=7):
    p=[(x,y),(x-L*math.cos(ang-0.4),y-L*math.sin(ang-0.4)),(x-L*math.cos(ang+0.4),y-L*math.sin(ang+0.4))]
    poly(p,c,c,0)
def hdim(x1,x2,y,label,c=INK,ext=0,below=False):
    if ext: ln(x1,y-ext if not below else y,x1,y,DIM,0.7); ln(x2,y-ext if not below else y,x2,y,DIM,0.7)
    ln(x1,y,x2,y,c,0.9); ahead(x1,y,0,c); ahead(x2,y,math.pi,c)
    txt((x1+x2)/2,y-4,label,9,"middle",c,700,MONO)
def vdim(y1,y2,x,label,c=INK):
    ln(x,y1,x,y2,c,0.9); ahead(x,y1,-math.pi/2,c); ahead(x,y2,math.pi/2,c)
    txt(x-4,(y1+y2)/2,label,9,"middle",c,700,MONO,rot=-90)
def hatch(x,y,w,h,c=ALU2,step=7):
    add(f'<defs><clipPath id="cp{len(out)}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs>')
    cid=f"cp{len(out)-1}"; add(f'<g clip-path="url(#{cid})">')
    i=-h
    while i<w+h:
        ln(x+i,y+h,x+i+h,y,c,0.6); i+=step
    add('</g>'); rect(x,y,w,h,"none",INK,1.2)
def rbox(cx,cy,ux,uy,L,Wd,fill,st=INK,sw=1.3):
    px,py=-uy,ux
    p=[(cx-ux*L/2-px*Wd/2,cy-uy*L/2-py*Wd/2),(cx+ux*L/2-px*Wd/2,cy+uy*L/2-py*Wd/2),
       (cx+ux*L/2+px*Wd/2,cy+uy*L/2+py*Wd/2),(cx-ux*L/2+px*Wd/2,cy-uy*L/2+py*Wd/2)]
    poly(p,fill,st,sw)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
rect(14,14,W-28,H-28,"none",INK,2); rect(22,22,W-44,H-44,"none",MUTED,0.7)
txt(44,52,"MÄTHUVUD — FAST OBLIK KANAL (kamera + laser)  ·  KONSTRUKTIONSRITNING",19,"start",INK,700)
txt(44,72,"Alu-bottenplatta 50 mm bred · fasta vinklar (kam 20° / laser 40°, θ 20°, baslinje 247) · centrum-tiltaxel mellan två 2020-profiler · WD 710. Mått i mm. Ej skalenlig mellan vyer.",10.5,"start",MUTED)
ln(44,82,W-44,82,INK,1)

# =================================================== VY 1: ARBETSPLAN
txt(60,112,"VY 1 — ARBETSPLAN (optik + huvud i läge, obliktet 30°)",12,"start",INK,700)
s=0.52; Px,Py=320,770
def ray(a): r=math.radians(a); return (Px+WD*s*math.sin(r),Py-WD*s*math.cos(r))
C=ray(CAM_A); L=ray(LAS_A)
# bräda + band
rect(Px-150,Py,300,16,WOOD,"#7a5230",1.3); ln(Px-150,Py+24,Px+150,Py+24,"#444a52",4)
txt(Px,Py+44,"BRÄDA (yta) · laserlinje",9,"middle","#7a5230",700)
# lod + strålar
ln(Px,Py,Px,Py-430,DIM,0.7,"5 5")
ln(C[0],C[1],Px,Py,BLUE,1.4,"6 4"); ln(L[0],L[1],Px,Py,RED,2.4); circ(Px,Py,4,"#a23ad6","#7a2fb0",1)
txt(Px+26,Py-66,"20°",9,"middle",BLUE,700); txt(Px+66,Py-46,"40°",9,"middle",RED,700)
# WD-mått längs strålarna
mc=((C[0]+Px)/2,(C[1]+Py)/2); ml=((L[0]+Px)/2,(L[1]+Py)/2)
txt(mc[0]-12,mc[1],"WD 710",8.5,"middle",BLUE,700,MONO,rot=-70)
txt(ml[0]+14,ml[1],"WD 710",8.5,"middle",RED,700,MONO,rot=-50)
# platta längs C-L
ux,uy=(L[0]-C[0]),(L[1]-C[1]); bl=math.hypot(ux,uy); ux,uy=ux/bl,uy/bl
nx,ny=0.5,-0.866; thpx=TH*s+5; extpx=42*s
A0=(C[0]-ux*extpx,C[1]-uy*extpx); A1=(L[0]+ux*extpx,L[1]+uy*extpx)
poly([A0,A1,(A1[0]+nx*thpx,A1[1]+ny*thpx),(A0[0]+nx*thpx,A0[1]+ny*thpx)],ALU,INK,1.4)
txt((A1[0]+nx*16),(A1[1]+ny*16),"ALU-PLATTA",8.5,"start",MUTED,700,rot=34)
# kamera vid C (kub + objektiv + filter) längs kameraxeln
cdx,cdy=(Px-C[0])/(WD*s),(Py-C[1])/(WD*s)
ccx,ccy=C[0]-cdx*16,C[1]-cdy*16
rbox(ccx,ccy,cdx,cdy,26,18,"#e2ecf6",BLUE,1.4)            # kamerakropp
rbox(C[0]+cdx*9,C[1]+cdy*9,cdx,cdy,16,12,"#d8e6f4","#5f8fc0",1.3)  # objektiv
circ(C[0]+cdx*17,C[1]+cdy*17,5,"#cfe0f2","#5f8fc0",1.1)   # bandpass
txt(ccx-40,ccy-40,"KAMERA",9,"middle",BLUE,700); txt(ccx-40,ccy-28,"MV-CS050",7.5,"middle",MUTED,700)
ln(ccx-40,ccy-24,ccx-6,ccy-6,DIM,0.6)
# laser vid L (cylinder Ø18×99) längs laseraxeln
ldx,ldy=(Px-L[0])/(WD*s),(Py-L[1])/(WD*s)
rbox(L[0]-ldx*22,L[1]-ldy*22,ldx,ldy,52,11,"#fde9e3",RED,1.4)      # lasertub
rbox(L[0]+ldx*5,L[1]+ldy*5,ldx,ldy,8,9,"#f6c9bd",RED,1.2)         # Powell-nos
txt(L[0]-ldx*30+18,L[1]-ldy*30,"LASER Ø18×99",8.5,"start",RED,700,rot=34)
# tiltaxel + två profiler + lås
M=((A0[0]+A1[0])/2+nx*thpx/2,(A0[1]+A1[1])/2+ny*thpx/2)
for off in (-1,1):
    bp=(M[0]+nx*thpx*0.5+px if False else M[0]+ (nx*0)+ ( -uy)*off*16, M[1]+ux*off*16)  # profiler längs axeln(X) – visas symmetriskt
for o in (-16,16):
    rect(M[0]-uy*o-9+nx*10,M[1]+ux*o-9+ny*10,18,18,PANEL,ALU2,1.2)
circ(M[0]+nx*10,M[1]+ny*10,9,"#fff",INK,1.6); circ(M[0]+nx*10,M[1]+ny*10,3,INK,INK,0)
txt(M[0]+nx*40,M[1]+ny*40,"TILTAXEL (M8)",8.5,"middle",INK,700,rot=34)
# tilt-arc
mc2=(M[0]+nx*10,M[1]+ny*10)
a0,a1=math.radians(-160),math.radians(-110)
ax0,ay0=mc2[0]+40*math.cos(a0),mc2[1]+40*math.sin(a0); ax1,ay1=mc2[0]+40*math.cos(a1),mc2[1]+40*math.sin(a1)
add(f'<path d="M {ax0:.1f} {ay0:.1f} A 40 40 0 0 1 {ax1:.1f} {ay1:.1f}" fill="none" stroke="{AMB}" stroke-width="2"/>')
ahead(ax1,ay1,math.radians(-110+90),AMB,7); txt(mc2[0]-44,mc2[1]-30,"tilt→lås",8.5,"end",AMB,700)
# baslinje-mått
hpx=(C[0]+L[0])/2; vpy=(C[1]+L[1])/2
txt(hpx-nx*42,vpy-ny*42-2,"baslinje 247",8.5,"middle",INK,700,MONO,rot=34)
txt(Px-6,Py-300,"obliktet 30°",8.5,"end",MUTED,700)

# =================================================== VY 2: SNITT A-A (tiltinfästning)
SX,SY=720,150
txt(SX,SY-16,"SNITT A–A — tiltinfästning (sett längs baslinjen, 50 mm bred)",12,"start",INK,700)
sc=2.3
# två 2020-profiler
pw=20*sc; gap=50*sc
plate_x=SX+pw+18
# vänster profil
hatch(SX,SY,pw,pw,ALU2); txt(SX+pw/2,SY+pw+14,"2020",8,"middle",MUTED,700)
# höger profil
rx2=plate_x+50*sc+18
hatch(rx2,SY,pw,pw,ALU2); txt(rx2+pw/2,SY+pw+14,"2020",8,"middle",MUTED,700)
# platta (50 bred x 10 tjock) i snitt
hatch(plate_x,SY+pw/2-TH*sc/2,50*sc,TH*sc,ALU2); txt(plate_x+25*sc,SY+pw+14,"PLATTA 50×10",8.5,"middle",INK,700)
# M8 bult genom allt
boy=SY+pw/2
ln(SX-10,boy,rx2+pw+10,boy,STEEL,3)
circ(SX-10,boy,6,"#fff",INK,1.4)                       # bulthuvud (vänster)
poly([(rx2+pw+4,boy-7),(rx2+pw+16,boy-7),(rx2+pw+16,boy+7),(rx2+pw+4,boy+7)],STEEL,INK,1.2) # mutter
txt((SX+rx2)/2,boy-14,"M8 tiltbult + TANDBRICKA (lås)",8.5,"middle",STEEL,700)
txt(SX-14,boy+22,"profilerna är del av portalen — huvudet tiltar om bulten, dras åt = lås",8,"start",MUTED,400)

# =================================================== VY 3: PLAN (hålbild)
PXp,PYp=80,940; sp=1.5
plw=PLATE_L*sp; plh=PLATE_W*sp
txt(PXp,PYp-18,"VY 3 — PLAN av bottenplatta (hålbild för borrning, datum = vänster kant)",12,"start",INK,700)
rect(PXp,PYp,plw,plh,ALU,INK,1.5,3)
def holx(off): return PXp+off*sp
cy=PYp+plh/2
# kamerafäste 4-hål (M4) runt CAM_OFF
for dx in (-16,16):
    for dy in (-14,14):
        circ(holx(CAM_OFF)+dx*sp,cy+dy*sp,3.4,"#fff",BLUE,1.3)
txt(holx(CAM_OFF),PYp-4,"kamerafäste 4×M4",8,"middle",BLUE,700)
# pivot Ø8.5
circ(holx(PIV_OFF),cy,5,"#fff",INK,1.6); circ(holx(PIV_OFF),cy,7.5,"none",INK,0.8)
txt(holx(PIV_OFF),PYp-4,"Ø8,5 tiltaxel",8,"middle",INK,700)
# laserklämma 2×M4
for dx in (-18,18):
    circ(holx(LAS_OFF)+dx*sp,cy,3.4,"#fff",RED,1.3)
txt(holx(LAS_OFF),PYp-4,"laserklämma 2×M4",8,"middle",RED,700)
# måttsättning
hdim(PXp,PXp+plw,PYp+plh+26,f"{PLATE_L:.0f}",INK,plh+26-(PYp+plh)+0)
ln(PXp,PYp+plh,PXp,PYp+plh+30,DIM,0.7); ln(PXp+plw,PYp+plh,PXp+plw,PYp+plh+30,DIM,0.7)
hdim(holx(CAM_OFF),holx(LAS_OFF),PYp+plh+50,f"baslinje {BASE:.0f}",INK)
ln(holx(CAM_OFF),cy,holx(CAM_OFF),PYp+plh+54,DIM,0.6); ln(holx(LAS_OFF),cy,holx(LAS_OFF),PYp+plh+54,DIM,0.6)
hdim(PXp,holx(CAM_OFF),PYp+plh+72,f"{CAM_OFF:.1f}",MUTED)
hdim(PXp,holx(PIV_OFF),PYp+plh+92,f"{PIV_OFF:.0f}",MUTED)
vdim(PYp,PYp+plh,PXp-22,f"{PLATE_W:.0f}",INK)

# =================================================== DELLISTA
LX=1180
rect(LX,150,660,300,"#fff",INK,1.3,7); rect(LX,150,660,26,INK,INK,0,7)
txt(LX+10,168,"DELLISTA",12,"start","#fff",700)
items=[("1","Bottenplatta, alu 6082/6063","330 × 50 × 10 mm"),
       ("2","Kamera Hikrobot MV-CS050-10UM","29×29×42, C-mount"),
       ("3","Objektiv 12 mm + bandpass 650/525","M30,5-filter"),
       ("4","Kamerafäste, 10°-vinkel (alu)","4× M4"),
       ("5","Linjelaser MZLaser Powell","Ø18 × 99 mm"),
       ("6","Laserklämma / V-block, 10° (alu)","2× M4 + spänn"),
       ("7","Tiltbult M8 + tandbricka (lås)","genom centrumhål"),
       ("8","2× 2020-profil (tiltstöd)","del av portalen"),
       ("9","Skruvar M4 + brickor","fästen")]
txt(LX+14,196,"POS",8.5,"start",MUTED,700,MONO); txt(LX+70,196,"BENÄMNING",8.5,"start",MUTED,700,MONO); txt(LX+470,196,"SPEC",8.5,"start",MUTED,700,MONO)
ln(LX+10,202,LX+650,202,DIM,0.8)
for i,(p,n,sp_) in enumerate(items):
    yy=222+i*24
    if i%2: rect(LX+8,yy-15,644,24,PANEL,"none",0)
    circ(LX+24,yy-4,8,"#fff",INK,1.2); txt(LX+24,yy,p,8.5,"middle",INK,700,MONO)
    txt(LX+70,yy,n,9.5,"start",INK,700); txt(LX+470,yy,sp_,9,"start",MUTED,400)

# =================================================== MÅTTABELL
rect(LX,470,660,250,"#fff",INK,1.3,7); rect(LX,470,660,26,INK,INK,0,7)
txt(LX+10,488,"FASTA MÅTT & VINKLAR",12,"start","#fff",700)
dims=[("Arbetsavstånd WD (var optik)","710 mm"),("Kameravinkel / laservinkel (lod)","20° / 40°"),
      ("Triangulering θ (kam↔laser)","20°"),("Optik ↔ plattnormal","±10°"),
      ("Baslinje (kam↔laser-c)","247 mm"),("Obliktet (plattnormal↔lod)","30°"),
      ("Platta L×B×T","330 × 50 × 10 mm"),("Kamera-c / laser-c från datum","41,5 / 288,5 mm"),
      ("Tiltaxel (centrumhål) från datum","165 mm · Ø8,5")]
for i,(k,v) in enumerate(dims):
    yy=510+i*22
    if i%2: rect(LX+8,yy-15,644,22,PANEL,"none",0)
    txt(LX+14,yy,k,9.6,"start",MUTED,700); txt(LX+646,yy,v,9.8,"end",INK,700,MONO)

# =================================================== NOTER + RITNINGSHUVUD
rect(LX,740,660,150,"#fff",INK,1.3,7); rect(LX,740,660,24,INK,INK,0,7)
txt(LX+10,757,"NOTER",12,"start","#fff",700)
for i,n in enumerate([
 "Vinklar kam/laser FASTA (kalibreras en gång, lås). Tilt = hela huvudet om M8-axeln för inriktning, dras åt = lås.",
 "Kamera + laser på SAMMA styva platta → geometrin rör sig aldrig relativt varandra (stabil kalibrering).",
 "Termik: laser i metallklämma mot plattan (+ värmepasta) = kylfläns. INGEN fläkt. Kamera på samma platta.",
 "Storleksbyte (bredd/längd/tjocklek) = bara mjukvara inom mätområdet — ingen tilt. Spegla huvudet för grön kanal.",
 "Plattjocklek ≥10 mm; ev. förstyvningsklack vid laserklämman. Tiltaxel nära optiklinjen.",
]): txt(LX+14,778+i*22,"• "+n,9.2,"start",INK,400)

tb_x,tb_y=LX,910; rect(tb_x,tb_y,660,150,"#fff",INK,1.5,7)
ln(tb_x,tb_y+96,tb_x+660,tb_y+96,INK,1); ln(tb_x+400,tb_y,tb_x+400,tb_y+96,INK,1); ln(tb_x+400,tb_y+30,tb_x+660,tb_y+30,INK,1); ln(tb_x+400,tb_y+63,tb_x+660,tb_y+63,INK,1)
txt(tb_x+16,tb_y+34,"VIRKESSKANNER",14,"start",INK,700); txt(tb_x+16,tb_y+58,"FAST MÄTHUVUD — oblik kanal",12,"start",INK,700)
txt(tb_x+16,tb_y+82,"Material: alu 6082/6063 · skruv M4/M8",9.5,"start",MUTED)
txt(tb_x+410,tb_y+20,"RITN-NR",8,"start",MUTED,700); txt(tb_x+648,tb_y+22,"MH-001",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+52,"MÅTT",8,"start",MUTED,700); txt(tb_x+648,tb_y+54,"mm",11,"end",INK,700,MONO)
txt(tb_x+410,tb_y+85,"VINKLAR",8,"start",MUTED,700); txt(tb_x+648,tb_y+87,"20°/40° fasta",10,"end",INK,700,MONO)
txt(tb_x+16,tb_y+118,"Ej skalenlig mellan vyer · vinklar/baslinje per head-mech-geometri",9,"start",MUTED,400)
txt(tb_x+16,tb_y+138,"Tilt = enda frihetsgrad (låses). Allt övrigt fast.",9,"start",MUTED,400)

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
