#!/usr/bin/env python3
"""EXAKT kopplingsschema för encoder-kedjan: 2 rull-encodrar (band A = E6B2-CWZ6C
single-ended, band B = E6B2-CWZ1X RS-422), diff->single-omvandlarmodul, RoboClaw
2x7A och line-scan-kameran HT-GELM44C-T2. Blockschema + komplett pin-för-pin-netlista.

    python tools/draw_encoder_wiring.py   # -> encoder-wiring.svg (+ .png)
"""
from __future__ import annotations
import os, math

W, H = 1860, 1340
INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, PANEL, GRID = "#f7f6f1", "#eceae2", "#e0ded6"
RED, GRN, BLUE, AMB, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#c98a16", "#a23ad6"
# trådfärger (encoderkablage)
BROWN, BLUEW, BLACK, WHITE, ORANGE, GREY = "#7a5230", "#2f6fb0", "#23262b", "#8a9099", "#e08a2c", "#9aa0a6"
PWR24, PWR5, GNDc = "#d23b3b", "#e0892b", "#3b4046"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}">{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=1.4,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}"/>')
def poly(pts,st,w=2.0,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    p=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    add(f'<polyline points="{p}" fill="none" stroke="{st}" stroke-width="{w}"{d}/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.4,rx=0,op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def circ(x,y,r,fill,st=INK,sw=1):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
def blk(x,y,w,h,title,sub,acc):
    rect(x,y,w,h,"#fff",acc,1.8,9); rect(x,y,w,24,acc,acc,0,9)
    txt(x+10,y+17,title,11.5,"start","#fff",700);
    if sub: txt(x+10,y+40,sub,9,"start",INK,400)
def term(x,y,lbl,col=INK,side="r"):
    circ(x,y,3.2,col,INK,0.8)
    if side=="r": txt(x+8,y+3.5,lbl,8.5,"start",INK,700,MONO)
    elif side=="l": txt(x-8,y+3.5,lbl,8.5,"end",INK,700,MONO)
    else: txt(x,y-7,lbl,8.5,"middle",INK,700,MONO)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
txt(40,50,"ENCODER-KEDJAN — EXAKT KOPPLINGSSCHEMA",22,"start",INK,700)
txt(40,74,"Band A: E6B2-CWZ6C (single-ended) -> RoboClaw EN1.  Band B: E6B2-CWZ1X (RS-422, matas 5V) -> diff parallellt till KAMERA (IN1/IN2) + OMVANDLARE -> RoboClaw EN2.",12,"start",MUTED)
txt(40,92,"Strömväg: 24V PSU -> RoboClaw/omvandlare/kamera. RoboClaws 5V-BEC (>=1A) matar BÅDA encodrarna (240mA). Omvandlarens egen 150mA-5V-utgång OANVÄND (för svag för CWZ1X 160mA). Gemensam GND.",11.5,"start",MUTED)
line(40,104,W-40,104,INK,1.2)

# ---- rails ----
RY24, RYG = 150, 720
line(120,RY24,W-60,RY24,PWR24,3); txt(W-58,RY24+4,"+24 V",10,"start",PWR24,700)
line(120,RYG,W-60,RYG,GNDc,3); txt(W-58,RYG+4,"GND",10,"start",GNDc,700)

# ---- 24V PSU ----
blk(40,160,150,70,"24 V PSU","band/laser/LED",PWR24)
line(115,230,115,RY24,PWR24,2.2); circ(115,RY24,3,PWR24)        # +24 upp
line(150,225,150,RYG,GNDc,2.2); circ(150,RYG,3,GNDc)            # GND ner

# ============ ENCODER A (CWZ6C) ============
ax,ay=40,300; blk(ax,ay,210,118,"ENCODER band A","E6B2-CWZ6C (single-ended, NPN)",GRN)
ea=[("Brown +Vcc 5V",BROWN),("Blue 0V",BLUEW),("Black  A",BLACK),("White  B",WHITE),("Orange Z (n/c)",ORANGE)]
for i,(l,c) in enumerate(ea):
    yy=ay+44+i*15; circ(ax+210,yy,3.2,c); txt(ax+200,yy+3.5,l,8.2,"end",INK,600,MONO)

# ============ ENCODER B (CWZ1X) ============
bx,by=40,500; blk(bx,by,210,150,"ENCODER band B (ref)","E6B2-CWZ1X (RS-422 line-driver)",PURP)
eb=[("Brown +Vcc (5V in)",BROWN),("Blue 0V",BLUEW),("A+ / A-",BLACK),("B+ / B-",WHITE),("Z+ / Z- (n/c)",ORANGE)]
for i,(l,c) in enumerate(eb):
    yy=by+46+i*18; circ(bx+210,yy,3.2,c); txt(bx+200,yy+3.5,l,8.2,"end",INK,600,MONO)

# ============ OMVANDLARE ============
cx,cy=470,470; blk(cx,cy,250,200,"DIFF->SINGLE OMVANDLARE","26C32-typ + 5V/150mA DC-DC",AMB)
# vänster (encoder-sida)
cin=[("+5V UT (OANVÄND)",DIM),("GND",GNDc),("A+  <- enc B",BLACK),("A-  <- enc B",BLACK),("B+  <- enc B",WHITE),("B-  <- enc B",WHITE),("Z+/Z- <- enc B",ORANGE)]
for i,(l,c) in enumerate(cin):
    yy=cy+44+i*16; circ(cx,yy,3.2,c); txt(cx+9,yy+3.5,l,8,"start",INK,600,MONO)
# höger (ut + power-in)
cout=[("VIN 7-35V <-+24",PWR24),("CHA -> EN2 A",GRN),("CHB -> EN2 B",GRN),("GND -> EN2 GND",GNDc)]
for i,(l,c) in enumerate(cout):
    yy=cy+60+i*20; circ(cx+250,yy,3.2,c); txt(cx+241,yy+3.5,l,8,"end",INK,600,MONO)
txt(cx+125,cy+196,"OBS: modulens 5V-UT (150mA) OANVÄND — för svag för CWZ1X (160mA)",7.6,"middle","#8a6510",700)

# ============ ROBOCLAW ============
rx,ry=470,150; blk(rx,ry,250,210,"RoboClaw 2x7A","dual motor + 2 enc, USB",BLUE)
# vänster: power + USB
term(rx,ry+44,"B+  <- +24",PWR24,"r"); term(rx,ry+62,"B-  -> GND",GNDc,"r")
term(rx,ry+86,"USB -> Jetson",BLUE,"r")
# höger: motorer + encodrar
rr=[("M1A/M1B -> motor A","#444a52"),("M2A/M2B -> motor B","#444a52"),
    ("EN1: 5V/GND -> enc A",GRN),("EN1: A/B  <- enc A",GRN),
    ("EN2: 5V/GND (egen)",AMB),("EN2: A/B <- omvandlare",AMB)]
for i,(l,c) in enumerate(rr):
    yy=ry+44+i*26; circ(rx+250,yy,3.2,c); txt(rx+241,yy+3.5,l,8.2,"end",INK,700,MONO)

# ============ KAMERA ============
kx,ky=1180,440; blk(kx,ky,250,240,"KAMERA HT-GELM44C-T2","M12 12-pin + GigE",RED)
kp=[("pin2 PWR+  <- +24",PWR24),("pin1 PWR-  -> GND",GNDc),
    ("pin3 IN1+  <- enc B A+",BLACK),("pin4 IN1-  <- enc B A-",BLACK),
    ("pin5 IN2+  <- enc B B+",WHITE),("pin6 IN2-  <- enc B B-",WHITE),
    ("pin7/8 IN3 (valfri trig)",DIM),("RJ45 GigE -> Jetson",RED)]
for i,(l,c) in enumerate(kp):
    yy=ky+44+i*24; circ(kx,yy,3.2,c); txt(kx+9,yy+3.5,l,8.2,"start",INK,700,MONO)

# ============ MOTORER + JETSON ============
blk(1180,150,250,55,"BANDMOTOR A","24V","#444a52"); blk(1180,225,250,55,"BANDMOTOR B","24V","#444a52")
blk(770,720+0,0,0,"","","#fff")  # spacer no-op
blk(40,1180,0,0,"","","#fff")
jx,jy=820,250; blk(jx,jy,150,70,"JETSON","USB + GbE","#3b7d3b")

# ---------- KOPPLINGAR (linjer) ----------
# Encoder A -> RoboClaw EN1 (brun/blå/svart/vit)
for i,(c,dy) in enumerate([(BROWN,0),(BLUEW,15),(BLACK,30),(WHITE,45)]):
    poly([(ax+210,ay+44+i*15),(380+i*6,ay+44+i*15),(380+i*6,ry+96+min(i,1)*0+ (0 if i<2 else 0)) ],c,1.6)
# simpler: route encoder A four wires into RoboClaw EN1 area (right side rows 3-4); draw as a bundle
rect(372,ay+40,8,70,"none","none",0)  # invisible
# Bundle A -> EN1 (draw labeled bundle)
poly([(ax+210,ay+95),(400,ay+95),(400,ry+96),(rx+250,ry+96)],GRN,1.4,"5 4")
txt(404,ay+90,"band A: 5V·GND·A·B  ->  RoboClaw EN1",8,"start",GRN,700)

# Encoder B diff fan-out: to converter (left side) and to camera (right)
# enc B A+/A- and B+/B- start
ebA=by+82; ebB=by+100
# to converter A/B inputs
poly([(bx+210,ebA),(300,ebA),(300,cy+92),(cx,cy+92)],BLACK,1.6)         # A -> conv A+/-
poly([(bx+210,ebB),(312,ebB),(312,cy+124),(cx,cy+124)],WHITE,1.6)       # B -> conv B+/-
# to camera IN1/IN2 (long run to right) -- tap from same nodes
poly([(bx+210,ebA),(300,ebA),(300,820),(1150,820),(1150,ky+92),(kx,ky+92)],BLACK,1.6)
poly([(bx+210,ebB),(312,ebB),(312,835),(1135,835),(1135,ky+140),(kx,ky+140)],WHITE,1.6)
txt(700,814,"band B  A+/A-  (RS-422)  ->  parallellt KAMERA IN1 + OMVANDLARE",8,"start",BLACK,700)
txt(700,851,"band B  B+/B-  (RS-422)  ->  parallellt KAMERA IN2 + OMVANDLARE",8,"start",WHITE,700)
# encoder B Vcc <- RoboClaw 5V-BEC (stub, EN-header +5V)
line(bx+210,by+46,bx+250,by+46,PWR5,1.8); circ(bx+250,by+46,3,PWR5)
txt(bx+254,by+43,"+5V <- RoboClaw BEC (EN-header +)",7.8,"start","#8a6510",700)
# converter CHA/CHB -> RoboClaw EN2
poly([(cx+250,cy+80),(760,cy+80),(760,ry+200),(rx+250,ry+200)],GRN,1.6)
poly([(cx+250,cy+100),(748,cy+100),(748,ry+200+0),(rx+250,ry+200)],GRN,1.6,"4 3")
txt(764,cy+76,"CHA/CHB  ->  RoboClaw EN2 A/B",8,"start",GRN,700)

# power-in to converter VIN and camera + RoboClaw B+ from +24 rail
line(cx+250,cy+60,cx+300,cy+60,PWR24,1.8); line(cx+300,cy+60,cx+300,RY24,PWR24,1.8); circ(cx+300,RY24,3,PWR24)
line(kx,ky+44,kx-30,ky+44,PWR24,1.8); line(kx-30,ky+44,kx-30,RY24,PWR24,1.8); circ(kx-30,RY24,3,PWR24)
line(rx,ry+44,rx-22,ry+44,PWR24,1.8); line(rx-22,ry+44,rx-22,RY24,PWR24,1.8); circ(rx-22,RY24,3,PWR24)
# GND drops to rail
for gx,gy0 in [(cx+222,cy+60),(kx+10,ky+68),(rx,ry+62),(bx+150,by+64),(ax+150,ay+59)]:
    pass
# RoboClaw B- -> GND
line(rx,ry+62,rx-40,ry+62,GNDc,1.6); line(rx-40,ry+62,rx-40,RYG,GNDc,1.6); circ(rx-40,RYG,3,GNDc)
# converter GND -> rail
line(cx,cy+60,cx-26,cy+60,GNDc,1.6); line(cx-26,cy+60,cx-26,RYG,GNDc,1.6); circ(cx-26,RYG,3,GNDc)
# camera pin1 GND
line(kx,ky+68,kx-46,ky+68,GNDc,1.6); line(kx-46,ky+68,kx-46,RYG,GNDc,1.6); circ(kx-46,RYG,3,GNDc)
# encoder B Blue 0V -> GND
line(bx+210,by+64,bx+250,by+64,GNDc,1.4); line(bx+250,by+64,bx+250,RYG,GNDc,1.4); circ(bx+250,RYG,3,GNDc)
# RoboClaw USB -> Jetson ; Camera RJ45 -> Jetson
poly([(rx+250,ry+86 if False else ry+86)],BLUE)  # noop guard
poly([(rx,ry+86),(jx,jy+30)],BLUE,1.6,"4 3"); txt((rx+jx)/2-10,jy+18,"USB",8,"middle",BLUE,700)
poly([(kx,ky+212),(1150,ky+212),(1150,jy+50),(jx+150,jy+50)],RED,1.6,"4 3"); txt(jx+158,jy+50,"GigE",8,"start",RED,700)
# motors
poly([(rx+250,ry+44),(1150,ry+44),(1150,180),(1180,180)],"#444a52",1.6);
poly([(rx+250,ry+70),(1120,ry+70),(1120,252),(1180,252)],"#444a52",1.6)

# ---- terminering-not ----
rect(1180,700,250,2,"none","none",0)
rect(1180,690,640,40,"#fff5e6","#c89028",1.3,6)
txt(1190,706,"TERMINERING: EN ~120 ohm over A+/A- och B+/B- i far-anden",9,"start","#8a6510",700)
txt(1190,722,"(kamerans inbyggda term ELLER vid omvandlaren — INTE bada).",9,"start","#8a6510",400)

# ============ NETLISTA (tabell) ============
ty=760
rect(40,ty,W-80,540,"#fff",INK,1.4,8); rect(40,ty,W-80,30,INK,INK,0,8)
txt(54,ty+21,"KOMPLETT NETLISTA (pin för pin)",13,"start","#fff",700)
cols=[(58,"FRÅN",470),(540,"TRÅD / PIN",250),(800,"TILL",1020)]
for cxx,h,_ in cols: txt(cxx,ty+52,h,10,"start",MUTED,700,MONO)
line(54,ty+60,W-94,ty+60,DIM,1)
net=[
 ("24 V PSU (+)","röd","RoboClaw B+ · Omvandlare VIN · Kamera pin2 (PWR+)",PWR24),
 ("24 V PSU (−)","svart","GEMENSAM GND (allas GND/0V, se nedan)",GNDc),
 ("— ENCODER A: E6B2-CWZ6C (single-ended) → RoboClaw EN1 —","","",GRN),
 ("Enc A  Brown (+Vcc)","brun","RoboClaw EN1  +5V   (RoboClaw matar enc A)",GRN),
 ("Enc A  Blue (0V)","blå","RoboClaw EN1  GND",GRN),
 ("Enc A  Black (A)","svart","RoboClaw EN1  ENA",GRN),
 ("Enc A  White (B)","vit","RoboClaw EN1  ENB",GRN),
 ("Enc A  Orange (Z)","orange","ej ansluten (RoboClaw nyttjar ej Z)",DIM),
 ("— ENCODER B: E6B2-CWZ1X (RS-422, matas 5V ±5% från RoboClaw-BEC; 160mA) —","","",PURP),
 ("RoboClaw 5V-BEC (≥1A)","röd","Enc B  Brown (+Vcc)   ← RoboClaw matar (EN-header +5V)",PWR5),
 ("Enc B  Blue (0V)","blå","GEMENSAM GND (+ Omvandlare GND)",GNDc),
 ("Enc B  A+ / A−","svart/sv-röd","PARALLELLT: Kamera pin3/pin4 (IN1±)  +  Omvandlare A+/A−",BLACK),
 ("Enc B  B+ / B−","vit/vit-röd","PARALLELLT: Kamera pin5/pin6 (IN2±)  +  Omvandlare B+/B−",MUTED),
 ("Enc B  Z+ / Z−","orange","Omvandlare Z+/Z−  (kamera/RoboClaw nyttjar ej Z)",DIM),
 ("— OMVANDLARE: diff→single (26C32-typ) → RoboClaw EN2 —","","",AMB),
 ("Omvandlare VIN (7–35V)","röd","+24 V   (omvandlarens egen logik/26C32)",PWR24),
 ("Omvandlare +5V UT (150mA)","—","OANVÄND — för svag för CWZ1X (160mA); encodrar matas av RoboClaw-BEC",DIM),
 ("Omvandlare GND","svart","GEMENSAM GND",GNDc),
 ("Omvandlare CHA","grön","RoboClaw EN2  ENA",GRN),
 ("Omvandlare CHB","grön","RoboClaw EN2  ENB",GRN),
 ("Omvandlare GND (ut)","svart","RoboClaw EN2  GND   (EN2 +5V = RoboClaws egen, koppla EJ in modulens 5V)",GNDc),
 ("— KAMERA HT-GELM44C-T2 (M12 12-pin) —","","",RED),
 ("Kamera pin1 (PWR−)","—","GEMENSAM GND",GNDc),
 ("Kamera pin2 (PWR+)","—","+24 V (12–24 V)",PWR24),
 ("Kamera pin3/4 (IN1±)","—","← Enc B  A+/A−  (diff, parallellt med omvandlaren)",BLACK),
 ("Kamera pin5/6 (IN2±)","—","← Enc B  B+/B−  (diff, parallellt med omvandlaren)",MUTED),
 ("Kamera pin7/8 (IN3±)","—","valfritt: anhåll-fotocell som frame/region-trigg",DIM),
 ("Kamera RJ45 (GigE)","Cat6","Jetson GbE",RED),
 ("— ROBOCLAW 2x7A —","","",BLUE),
 ("RoboClaw M1A/M1B","—","Bandmotor A",INK),
 ("RoboClaw M2A/M2B","—","Bandmotor B",INK),
 ("RoboClaw USB","USB","Jetson  (position/fart + styrning)",BLUE),
]
rh=15.4; yy=ty+74
for (a,b,c,col) in net:
    if a.startswith("—"):
        rect(54,yy-11,W-108,16,PANEL,"none",0); txt(58,yy+1,a,9.2,"start",col,700)
    else:
        circ(48,yy-3,3,col,col,0)
        txt(58,yy+1,a,9,"start",INK,600,MONO); txt(540,yy+1,b,8.6,"start",MUTED,400,MONO); txt(800,yy+1,c,9,"start",INK,400)
    yy+=rh

add('</svg>')
svg="\n".join(out)
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(root,"encoder-wiring.svg"),"w",encoding="utf-8").write(svg)
print("skrev encoder-wiring.svg")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(),write_to=os.path.join(root,"encoder-wiring.png"),output_width=W,output_height=H)
    print("skrev encoder-wiring.png")
except Exception as e:
    print("PNG-render hoppover:",e)
