#!/usr/bin/env python3
"""KOMPLETT ELSCHEMA m. HL-PBB-2-10-MINI distributionsblock — exakt terminal-
tilldelning. Buss A = +24V, Buss B = GND/stjärnjord. 24V SMPS matar block-
ingångarna; varje last tappas från en numrerad A- (+24V) och B- (GND) position.
24->5V buck (från A2/B2) matar röd laser. Jetson egen matning, GND→B9 (jord-brygga).

    python tools/draw_power_schema.py   # -> power-schema.svg (+ .png)
"""
from __future__ import annotations
import os

W, H = 1900, 1480
INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, PANEL, GRID = "#f7f6f1", "#eceae2", "#e0ded6"
V24, V5, GND, SIG, DATA = "#d23b3b", "#e0892b", "#23262b", "#2f6fb0", "#2f9e6e"
AROW, BROW = "#fbe4e4", "#e7e7ea"
SANS="'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO="'IBM Plex Mono','DejaVu Sans Mono',monospace"
out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}">{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=2,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} stroke-linecap="round"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.6,rx=7):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
def dot(x,y,r=4,fill=INK):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')
def chip(x,y,s,c):  # terminal-chip
    rect(x-15,y-10,30,20,c,c,0,4); txt(x,y+4,s,9.5,"middle","#fff",700,MONO)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
txt(40,46,"KOMPLETT ELSCHEMA — koppling via HL-PBB-2-10-MINI (buss A=+24V · buss B=GND)",21,"start",INK,700)
txt(40,69,"24V SMPS matar blockets A/B-ingångar. Varje last tappas från en numrerad A-position (+24V) och B-position (GND). 24→5V buck (A2/B2) → röd laser. Jetson egen matning, GND→B9.",11.5,"start",MUTED)
lx=40
for lab,c in [("+24 V (buss A)",V24),("+5 V (buck)",V5),("GND (buss B = stjärnjord)",GND),("styr GPIO",SIG),("data USB/GbE/RS",DATA)]:
    rect(lx,82,16,12,c,c,0,3); txt(lx+22,92,lab,10,"start",c if c!=GND else INK,700); lx+=len(lab)*7.2+50
line(40,104,W-40,104,INK,1.2)

# ---------------- SMPS ----------------
box=lambda x,y,w,h,t,s,acc:(rect(x,y,w,h,"#fff",acc,1.8,9),rect(x,y,w,22,acc,acc,0,9),txt(x+9,y+16,t,11,"start","#fff",700),(txt(x+9,y+37,s,8.6,"start",INK,400) if s else None))
box(40,128,200,72,"NÄT 230VAC → SMPS","24 V / 15 A (360 W)",V24)

# ---------------- PBB BLOCK ----------------
BX,BY,BW=300,150,1560
# buss A bar (+24V)
ay=190; rect(BX,ay-18,BW,36,AROW,V24,2,6); txt(BX+10,ay+5,"BUSS A  =  +24 V",12,"start",V24,800)
# buss B bar (GND)
by=250; rect(BX,by-18,BW,36,BROW,GND,2,6); txt(BX+10,by+5,"BUSS B  =  GND  (STJÄRNJORD)",12,"start",INK,800)
# inputs from SMPS
line(240,164,270,164,V24,3); line(270,164,270,ay,V24,3); dot(270,ay,5,V24); txt(258,150,"V+",9,"end",V24,700)
line(240,188,256,188,GND,3); line(256,188,256,by,GND,3); dot(256,by,5,GND); txt(250,176,"V−",9,"end",INK,700)
txt(BX+250,ay-24,"A-IN ← SMPS V+ (grov tråd)",8.5,"start",V24,700)
txt(BX+250,by+30,"B-IN ← SMPS V−   ·   Jetson-GND hit (B9)",8.5,"start",INK,700)
# 10 numbered taps per bus
TX0=BX+470; STEP=98
for i in range(10):
    tx=TX0+i*STEP
    dot(tx,ay,5,V24); txt(tx,ay-12,f"A{i+1}",9,"middle",V24,700,MONO)
    dot(tx,by,5,GND); txt(tx,by+20,f"B{i+1}",9,"middle",INK,700,MONO)

# ---------------- 24→5V BUCK ----------------
box(300,320,210,74,"24→5 V BUCK (5 A)","IN: A2 / B2",V5)
line(330,320,330,ay,V24,2); dot(330,ay,4,V24)        # buck in+ from A-bus (illustrativt)
line(360,394,360,by,GND,2); dot(360,by,4,GND)
line(450,357,520,357,V5,3); dot(520,357,4,V5); txt(524,353,"+5 V → röd laser",9,"start",V5,700)

# ================= KOPPLINGSTABELL (24V-laster) =================
TY=430
rect(40,TY,1820,470,"#fff",INK,1.5,9); rect(40,TY,1820,30,INK,INK,0,9)
txt(54,TY+21,"KOPPLINGSTABELL — exakt terminal per enhet",13,"start","#fff",700)
cols=[(60,"ENHET",430),(470,"+24 V",470),(620,"GND",760),(770,"STYR / DATA",1180),(1240,"NOT",1860)]
heads=[("ENHET",60),("+24V → A",470),("GND → B",600),("STYR / DATA",760),("NOT",1230)]
for h,x in heads: txt(x,TY+52,h,10.5,"start",MUTED,700,MONO)
line(54,TY+60,1846,TY+60,DIM,1)
rows=[
 ("RoboClaw 2x7A  (motorström)","A1","B1","USB → Jetson","B+/B−; M1→bandmotor A, M2→bandmotor B. Grov tråd!"),
 ("24→5 V buck  (IN)","A2","B2","—","OUT +5V → röd laser-modul. GND gemensam (icke-iso)."),
 ("Grön laser → D4184-modul","A3","B3","PWM ← GPIO","Modul bryter 24V; laser-barrel via inline-adapter."),
 ("Vitt LED → D4184-modul","A4","B4","PWM ← GPIO","Dimring via PWM. (LED-modell TBD.)"),
 ("Ytkamera HT-GELM44C-T2","A5","B5","GbE → Jetson","pin2=+24 (A5), pin1=GND (B5); enc A/B in (RS-422)."),
 ("3× LR400  (delad tapp)","A6","B6","RS-485 → Waveshare → USB","Lågström → dela 1 tapp via Wago/Y. ch1–3 (ch4 ledig)."),
 ("Anhåll-fotocell","A7","B7","→ GPIO (pull-up 3,3V)","NPN; ev. även → kamera IN3 som frame-trigg."),
 ("Diff→single omvandlare (VIN)","A8","B8","CHA/CHB → RoboClaw EN2","Tar encoder B diff → single-ended till EN2."),
 ("Jetson  (GND-brygga)","—","B9","egen matning (9–19V/USB-C)","JORD-BRYGGA: Jetson-GND MÅSTE till B9. EJ buss A."),
 ("(reserv)","A9·A10","B10","—","Lediga för framtida givare."),
]
rh=39; yy=TY+74
for i,(en,a,b,sd,nt) in enumerate(rows):
    if i%2: rect(54,yy-13,1792,rh,PANEL,"none",0)
    txt(60,yy+10,en,10.2,"start",INK,700,SANS)
    if a!="—" and a!="A9·A10": chip(485,yy+4,a,V24)
    else: txt(470,yy+8,a,9.5,"start",MUTED,700,MONO)
    if b!="—": chip(615,yy+4,b,GND)
    else: txt(600,yy+8,b,9.5,"start",MUTED,700,MONO)
    txt(770,yy+8,sd,9.6,"start",DATA if ("USB" in sd or "GbE" in sd or "RS-485" in sd or "CHA" in sd) else SIG if "GPIO" in sd or "PWM" in sd else MUTED,700)
    txt(1230,yy+8,nt,8.8,"start",MUTED,400)
    yy+=rh

# ================= 5V-sida + matningar som EJ går via blocket =================
TY2=930
rect(40,TY2,1820,150,"#fff","#3b7d3b",1.5,9); rect(40,TY2,1820,28,"#3b7d3b","#3b7d3b",0,9)
txt(54,TY2+20,"MATAS UTANFÖR BLOCKET (egen källa)",12,"start","#fff",700)
sub=[
 ("Röd laser → D4184-modul","+5 V från BUCK","GND via buck → buss B (B2)","PWM ← GPIO   ·   IN+=5V, OUT→laser; modul bryter (5–36V, icke-iso)"),
 ("Encoder A (CWZ6C) & B (CWZ1X)","+5 V från RoboClaw 5V-BEC","RoboClaw GND","A→EN1 · B (RS-422)→kamera IN1/IN2 + omvandlare→EN2"),
 ("2× Profilkamera RÖD/GRÖN","USB 5 V (Jetson)","USB-GND","USB3 → Jetson (ström + data i samma kabel)"),
]
yy=TY2+50
for i,(en,p,g,nt) in enumerate(sub):
    if i%2: rect(54,yy-15,1792,32,PANEL,"none",0)
    txt(60,yy+6,en,10,"start",INK,700); txt(560,yy+6,p,9.5,"start",V5,700); txt(940,yy+6,g,9.5,"start",INK,700); txt(1230,yy+6,nt,9,"start",MUTED,400)
    yy+=32

# ================= JORD + NOTER =================
cy=1110
rect(40,cy,900,120,"#fff5e6","#c89028",1.6,9)
txt(54,cy+24,"GEMENSAM JORD = BUSS B (stjärnpunkt)",12,"start","#8a6510",700)
for i,t in enumerate([
 "ALLA GND möts på buss B: SMPS V−, RoboClaw B−, buck GND, alla modul-/givar-GND.",
 "Jetson har EGEN matning men dess GND MÅSTE till B9 — annars funkar inga GPIO-signaler.",
 "USB-enheter (RoboClaw, kameror, Waveshare) jordas via USB-kabeln till Jetson.",
 "Buck icke-isolerad → dess 5V-retur ligger på samma jord (via B2).",
]): txt(54,cy+44+i*18,"• "+t,9.2,"start",INK,400)

rect(960,cy,900,120,"#fff",INK,1.5,9)
txt(974,cy+24,"VIKTIGT VID KOPPLING",12,"start",INK,700)
for i,t in enumerate([
 "GROV tråd: SMPS→A-IN/B-IN och RoboClaw (A1/B1) — de bär mest ström (~5–8A, motorstart högre).",
 "Klenare tråd OK till laser/kamera/LR400/fotocell (lågström).",
 "Verifiera blockets ampere-rating ≥ total. 3× LR400 delar en tapp (Wago) — lågström.",
 "Endast +24V & GND går via blocket. +5V (buck), encoder-5V (BEC) och USB-5V matas separat.",
]): txt(974,cy+44+i*18,"• "+t,9.2,"start",INK,400)

# Jetson + brick (visuell)
box(40,1250,250,90,"JETSON ORIN NANO","egen brick (9–19V/USB-C)","#3b7d3b")
line(165,1340,165,1300,GND,3,"3 3")  # symbolic
txt(300,1278,"GPIO → 3× D4184/AOD4184 (laser/LED) · GPIO ← fotocell · USB-hub (RoboClaw+2 kam+Waveshare) · GbE ← ytkamera",10,"start",INK,400)
txt(300,1300,"GND → B9 (jord-brygga).  Matas av egen brick — INTE från buss A.",10,"start","#8a6510",700)
txt(300,1330,"PROFILKAMEROR & RoboClaw & LR400-Waveshare = USB → Jetson (ström+data).",9.4,"start",MUTED,400)

add('</svg>')
svg="\n".join(out)
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(root,"power-schema.svg"),"w",encoding="utf-8").write(svg)
print("skrev power-schema.svg")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(),write_to=os.path.join(root,"power-schema.png"),output_width=W,output_height=H)
    print("skrev power-schema.png")
except Exception as e:
    print("PNG-render hoppover:",e)
