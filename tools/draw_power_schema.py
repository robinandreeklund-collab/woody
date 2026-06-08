#!/usr/bin/env python3
"""KOMPLETT ELSCHEMA (ström + jord + styr) — övertydligt. EN 24V SMPS-huvudrail
matar allt; 24->5V buck till röd laser; Jetson egen matning men GND bondad till
gemensam stjärnjord. Färg: röd=+24V, orange=+5V, svart=GND, blå streck=styr/data.

    python tools/draw_power_schema.py   # -> power-schema.svg (+ .png)
"""
from __future__ import annotations
import os

W, H = 2040, 1480
INK, MUTED, DIM = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, PANEL, GRID = "#f7f6f1", "#eceae2", "#e0ded6"
V24, V5, GND, SIG, DATA = "#d23b3b", "#e0892b", "#23262b", "#2f6fb0", "#2f9e6e"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">']
def add(s): out.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,sz=12,a="start",f=INK,w=400,fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{sz}" font-weight="{w}" fill="{f}" text-anchor="{a}">{esc(s)}</text>')
def line(x1,y1,x2,y2,st=INK,w=2,dash=None,op=1):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{w}"{d} opacity="{op}" stroke-linecap="round"/>')
def rect(x,y,w,h,fill="none",st=INK,sw=1.6,rx=8,op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{st}" stroke-width="{sw}" opacity="{op}"/>')
def dot(x,y,r=4,fill=INK):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')
def box(x,y,w,h,title,sub,acc):
    rect(x,y,w,h,"#fff",acc,1.8,9); rect(x,y,w,22,acc,acc,0,9)
    txt(x+9,y+16,title,11,"start","#fff",700)
    if sub: txt(x+9,y+37,sub,8.6,"start",INK,400)

add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
txt(40,48,"KOMPLETT ELSCHEMA — VIRKESSKANNER (ström · jord · styr)",22,"start",INK,700)
txt(40,72,"EN 24V SMPS-huvudrail matar ALLT · 24→5V buck till röd laser · Jetson egen matning (GND bondad till gemensam jord). Tänd/släck via MOSFET (low-side) / buck.",12,"start",MUTED)
# legend
lx=40;
for lab,c,d in [("+24 V",V24,None),("+5 V",V5,None),("GND (gemensam jord)",GND,None),("styr (GPIO)",SIG,"5 4"),("data (USB/GbE/RS)",DATA,"5 4")]:
    line(lx,90,lx+26,90,c,3,d); txt(lx+32,94,lab,10,"start",c if c!=GND else INK,700); lx+=len(lab)*7.0+70
line(40,108,W-40,108,INK,1.2)

# ---------- RAILS ----------
R24=260; RG=1180                      # +24V-rail Y, GND-rail Y
line(300,R24,W-40,R24,V24,4); txt(W-40,R24-8,"+24 V RAIL",11,"end",V24,700)
line(40,RG,W-40,RG,GND,5);    txt(W-40,RG+20,"GEMENSAM JORD (stjärnjord) — ALLA GND möts här",12,"end",INK,700)

# ---------- 230V -> SMPS ----------
box(40,150,210,90,"NÄT 230 V AC → SMPS","24 V / 15 A (360 W)",V24)
line(250,180,300,180,GND,2); line(300,180,300,R24,V24,3); dot(300,R24,4,V24)   # +24 to rail
line(150,240,150,RG,GND,3); dot(150,RG,4,GND)                                  # V- to GND rail
txt(154,300,"V+ → rail",8.5,"start",V24,700); txt(120,300,"V− → jord",8.5,"end",INK,700)

# ---------- BUCK 24->5V ----------
bx=360; box(bx,300,170,74,"24→5 V BUCK","≥2–3 A",V5)
line(bx+30,300,bx+30,R24,V24,2.5); dot(bx+30,R24,4,V24); txt(bx+34,296,"in +24",8,"start",V24,700)
line(bx+85,374,bx+85,RG,GND,2); dot(bx+85,RG,4,GND)
line(bx+140,338,bx+185,338,V5,3); V5X=bx+185
line(V5X,338,V5X,392,V5,3)                        # ner till +5V-minirail
line(V5X,392,1090,392,V5,3)                       # +5V-MINIRAIL (endast röd laser)
txt(1094,389,"+5 V (endast röd laser)",8.5,"start",V5,700)

# ---------- helper: consumer between rails ----------
def consumer(x,w,title,sub,acc,vin="24",switch=None,sig=None,extra=None):
    y=420; h=96
    box(x,y,w,h,title,sub,acc)
    # power in (top)
    src = R24 if vin=="24" else None
    midx=x+w*0.30
    if vin=="24":
        line(midx,y,midx,R24,V24,2.5); dot(midx,R24,4,V24); txt(midx+3,R24+16,"+24",7.5,"start",V24,700)
    else:  # +5V tappas från +5V-minirailen (y=392)
        line(midx,y,midx,392,V5,2.5); dot(midx,392,4,V5); txt(midx+3,388,"+5",7.5,"start",V5,700)
    # GND return (bottom) — through switch box if given
    gx=x+w*0.70
    if switch:
        sy=y+h+70; rect(gx-55,sy,110,42,"#fff",switch[1],1.6,6); txt(gx,sy+16,switch[0],8.2,"middle",switch[1],700)
        txt(gx,sy+33,switch[2],7.4,"middle",MUTED,400)
        line(gx,y+h,gx,sy,GND,2.2)                 # load- -> switch
        line(gx,sy+42,gx,RG,GND,2.2); dot(gx,RG,4,GND)   # switch -> GND
        # GPIO signal to switch
        line(gx+55,sy+21,gx+95,sy+21,SIG,2,"5 4"); txt(gx+99,sy+18,"GPIO",7.5,"start",SIG,700)
        add(f'<text x="{gx+99:.1f}" y="{sy+30:.1f}" font-family="{SANS}" font-size="7" fill="{MUTED}">{esc("(tänd/släck)")}</text>')
    else:
        line(gx,y+h,gx,RG,GND,2.2); dot(gx,RG,4,GND); txt(gx+3,RG-6,"GND",7.5,"start",INK,700)
    # data/signal stub
    if sig:
        line(x+w,y+30,x+w+34,y+30,DATA,2,"5 4"); txt(x+w+38,y+33,sig,7.8,"start",DATA,700)
    if extra:
        txt(x+9,y+58,extra,7.8,"start",INK,400)
    return x,y,w,h

# ---------- consumers ----------
# RoboClaw (bredare — motorer + encodrar + USB + 5V-BEC)
rx=300; box(rx,420,250,150,"RoboClaw 2x7A","motorer + encodrar",V24)
line(rx+40,420,rx+40,R24,V24,2.5); dot(rx+40,R24,4,V24); txt(rx+44,R24+16,"B+ +24",7.5,"start",V24,700)
line(rx+40,570,rx+40,RG,GND,2.5); dot(rx+40,RG,4,GND); txt(rx+44,RG-6,"B− GND",7.5,"start",INK,700)
txt(rx+9,482,"M1A/B → bandmotor A",8,"start",INK,400)
txt(rx+9,498,"M2A/B → bandmotor B",8,"start",INK,400)
txt(rx+9,514,"5V-BEC → encoder A & B",8,"start",V5,700)
txt(rx+9,530,"EN1←enc A · EN2←omvandlare",8,"start",INK,400)
line(rx+250,440,rx+290,440,DATA,2,"5 4"); txt(rx+294,443,"USB → Jetson",7.8,"start",DATA,700)

consumer(620,150,"Grön laser","12/24 V (barrel)",V24,switch=("AOD4184 opto","#a23ad6","bryter 24V low-side"),sig=None)
consumer(830,150,"Vitt LED-ljus","(TBD, 12/24 V)",V24,switch=("AOD4184 opto","#a23ad6","PWM-dimring"),sig=None)
consumer(1040,150,"Röd laser","5 V (barrel)",V24 and "5",vin="5",switch=("AO3400 MOSFET","#c98a16","bryter 5V low-side"))
consumer(1250,160,"Ytkamera HT-GELM44C","12–24 V (pin2/1)",RED if False else "#e8542c",vin="24",sig="GbE → Jetson",extra="enc A/B ← encoder B (RS-422 diff)")
consumer(1470,170,"3× LR400 + Waveshare","RS-485 4CH",V24,vin="24",sig="USB → Jetson",extra="ch1–3 (ch4 ledig)")
consumer(1700,150,"Anhåll-fotocell","NPN, 24 V",V24,vin="24",sig="→ GPIO (pull-up 3,3V)")
consumer(40,150,"Diff→single omv.","VIN 24 V",V24,vin="24",extra="enc B diff → CHA/CHB → EN2")

# ---------- ENCODERS (matas av RoboClaw 5V-BEC, ej 24V-railen) ----------
txt(rx+9,592,"ENCODER A & B → matas av RoboClaw 5V-BEC (ej 24V-railen):",7.8,"start","#2f9e6e",700)
txt(rx+9,605,"A→EN1 · B (RS-422)→kamera IN1/IN2 + omvandlare→EN2.",7.6,"start",MUTED,400)

# ---------- JETSON + egen matning ----------
jx=980; box(jx,1240,260,120,"JETSON ORIN NANO","EGEN matning (orig. brick)","#3b7d3b")
box(jx-300,1250,230,70,"Jetson-nät (egen)","9–19 V / USB-C-PD","#3b7d3b")
line(jx-70,1285,jx,1285,V24,2,"2 4"); txt(jx-66,1280,"egen DC (ej 24V-railen)",7.6,"start",MUTED,700)
# GROUND BOND (viktig!)
line(jx+130,1240,jx+130,RG,GND,4); dot(jx+130,RG,5,GND)
txt(jx+136,1215,"JORD-BRYGGA → gemensam jord (MÅSTE)",9,"start",INK,700)
txt(jx+9,1340,"GPIO → 3× MOSFET (laser/LED) · GPIO ← fotocell · USB-hub · GbE",8,"start",INK,400)

# ---------- profilkameror ----------
box(1280,1250,250,60,"2× Profilkamera RÖD/GRÖN","USB3 → Jetson (5V via USB)","#2f6fb0")
line(1280,1280,jx+260,1280,DATA,2,"5 4")

# ---------- GROUND CALLOUT ----------
cy=1390
rect(40,cy,1100,70,"#fff5e6","#c89028",1.6,8)
txt(54,cy+24,"GEMENSAM JORD (stjärnpunkt):",12,"start","#8a6510",700)
txt(54,cy+44,"Alla V−/GND möts i EN punkt: SMPS V− · buck GND · RoboClaw B− · alla givare/laser/kamera-GND · OCH Jetsons GND (jord-bryggan).",9.4,"start",INK,400)
txt(54,cy+60,"Jetson har egen matning men GND MÅSTE bondas hit — annars är GPIO-signalerna referenslösa. USB-enheter jordas via USB-kabeln.",9.4,"start",INK,400)

rect(1170,cy,830,70,"#fff",INK,1.4,8)
txt(1184,cy+24,"STRÖMKÄLLOR:",12,"start",INK,700)
txt(1184,cy+44,"1× SMPS 24 V/15 A → +24V-rail (RoboClaw/motorer, grön laser, LED, kamera, LR400, fotocell, omvandlare).",9.4,"start",INK,400)
txt(1184,cy+60,"1× 24→5 V buck → röd laser.  Encodrar ← RoboClaw 5V-BEC.  Jetson ← egen brick.  Inget 12V behövs.",9.4,"start",INK,400)

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
