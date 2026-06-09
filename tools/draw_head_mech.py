#!/usr/bin/env python3
"""KONSTRUKTIONSRITNING — komplett mätstation, BÅDA profilhuvuden + bräda i mitten.
Skalenlig tvärsnitts-GA med FULL måttsättning (mm + grader): WD, baslinje, höjder,
offset, vinklar, brädmått, portal. Plus detaljer på fästena, fästdonslista, noter,
ritningshuvud. Geometri exakt ur WD + kamera/laser-vinklarna.

  python tools/draw_head_mech.py   # -> head-mech.svg
"""
from __future__ import annotations
import os, sys, math

# ===================== EXAKT GEOMETRI (mm / grader) =====================
WD   = 760.0                      # arbetsavstånd (slant), kamera & laser → laserlinjen
CAM_A = 25.0                      # kamera-arm, vinkel från lod  (θ=25°)
LAS_A = 50.0                      # laser-arm (mer oblik), vinkel från lod
THETA = LAS_A - CAM_A             # trianguleringsvinkel = 25°
OBL   = (CAM_A + LAS_A) / 2       # huvudets obliquity (siktbisektris) = 37,5°
camZ = round(WD * math.cos(math.radians(CAM_A)))    # 689  kamerahöjd ö. brädyta
camY = round(WD * math.sin(math.radians(CAM_A)))    # 321  kamera-offset fr. mitt
lasZ = round(WD * math.cos(math.radians(LAS_A)))    # 489  laserhöjd
lasY = round(WD * math.sin(math.radians(LAS_A)))    # 582  laser-offset
BASE = round(2 * WD * math.sin(math.radians(THETA / 2)))   # 329  baslinje kamera↔laser
CAMCAM = 2 * camY                  # 642  kamera↔kamera (de två huvudena)
LASLAS = 2 * lasY                  # 1164 laser↔laser
PORTZ  = 780                       # ram-topp ö. brädyta (precis ovan kamerorna ~689)
UPX    = 650                        # sidostativens offset (utanför lasrarna ±582)
BW, BT = 75, 45                    # bräda bredd × tjocklek
CAM_L, CAM_W = 29, 29; LENS_L, LENS_D = 40, 32; FILT_L, FILT_D = 6, 32; LAS_L, LAS_D = 99, 18

INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9aa0a6"
PAPER, GRID, HATCH = "#f7f6f1", "#e6e4dc", "#cfd3d8"
RED, GRN, BLUE, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6"
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
def poly(pts, fill="none", stroke=INK, sw=1.2, op=1):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.2, head=8):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2-y1, x2-x1)
    for s in (0.4, -0.4): line(x2, y2, x2-head*math.cos(a-s), y2-head*math.sin(a-s), stroke, w)
def hole(x, y, r, col=INK):
    circ(x, y, r, "#fff", col, 1.2); line(x-r-2, y, x+r+2, y, col, 0.6); line(x, y-r-2, x, y+r+2, col, 0.6)
def dimlin(x1, y1, x2, y2, label, fill=INK, size=12, lblrot=None):
    """rakt mått mellan två punkter, pilar inåt, etikett centrerad."""
    arrow((x1+x2)/2, (y1+y2)/2, x1, y1, fill, 1); arrow((x1+x2)/2, (y1+y2)/2, x2, y2, fill, 1)
    mx, my = (x1+x2)/2, (y1+y2)/2
    rot = lblrot if lblrot is not None else 0
    rect(mx-len(label)*size*0.31, my-size*0.72, len(label)*size*0.62, size*1.26, PAPER, "none", 0, op=0.92)
    txt(mx, my+size*0.34, label, size, "middle", fill, 700, MONO, rot)
def hdim(x1, x2, y, label, fill=DIMC, size=11, ext=0):
    if ext: line(x1, y-ext, x1, y, fill, 0.6); line(x2, y-ext, x2, y, fill, 0.6)
    line(x1, y-5, x1, y+5, fill, 0.8); line(x2, y-5, x2, y+5, fill, 0.8)
    dimlin(x1, y, x2, y, label, INK if fill==DIMC else fill, size)
def vdim(y1, y2, x, label, fill=DIMC, size=11, ext=0):
    if ext: line(x, y1, x+ext, y1, fill, 0.6); line(x, y2, x+ext, y2, fill, 0.6)
    line(x-5, y1, x+5, y1, fill, 0.8); line(x-5, y2, x+5, y2, fill, 0.8)
    dimlin(x, y1, x, y2, label, INK if fill==DIMC else fill, size, lblrot=-90)
def adim(cx, cy, r, a1, a2, label, fill=INK, size=11, lr=None):
    p1 = (cx+r*math.cos(math.radians(a1)), cy+r*math.sin(math.radians(a1)))
    p2 = (cx+r*math.cos(math.radians(a2)), cy+r*math.sin(math.radians(a2)))
    large = 1 if abs(a2-a1) > 180 else 0
    swp = 1 if a2 > a1 else 0
    add(f'<path d="M {p1[0]:.1f} {p1[1]:.1f} A {r} {r} 0 {large} {swp} {p2[0]:.1f} {p2[1]:.1f}" fill="none" stroke="{fill}" stroke-width="1.2"/>')
    am = math.radians((a1+a2)/2); lx, ly = cx+(r+ (lr or 14))*math.cos(am), cy+(r+(lr or 14))*math.sin(am)
    rect(lx-len(label)*size*0.34, ly-size*0.7, len(label)*size*0.68, size*1.2, PAPER, "none", 0, op=0.9)
    txt(lx, ly+size*0.34, label, size, "middle", fill, 700, MONO)
def panel(x, y, w, h, title, acc=INK):
    rect(x, y, w, h, "#fff", acc, 1.4, 8); rect(x, y, w, 28, acc, acc, 0, 8); rect(x, y+16, w, 12, acc, acc, 0)
    txt(x+12, y+19, title, 12.5, "start", "#fff", 700, SANS)

W, H = 2260, 1580
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W-32, H-32, "none", INK, 2); rect(24, 24, W-48, H-48, "none", MUTED, 0.8)
txt(46, 60, "MÄTSTATION — DUBBELT PROFILHUVUD  (tvärsnitt, skalenlig)", 25, "start", INK, 700, SANS)
txt(46, 86, "Två profilhuvuden (var sitt kamera+laser PÅ SAMMA SIDA) på var sin sida om brädan, lutade inåt mot samma laserlinje "
            "(RÖD=V-kant, GRÖN=H-kant) + YTKAMERA (line-scan) på EGEN rad +40 mm (CAD 39,75) (EJ på laserlinjen → laserlinjen utanför FOV → ingen laser i färgbilden). Kompakt huvud θ=25°. Huvuden HÄNGER från portalens tvärbalk via VINKELADAPTER (åt var sin sida).", 13, "start", MUTED, 400, SANS)
line(46, 100, W-46, 100, INK, 1.4)

# =================================================================== HUVUD-GA (skalenlig)
PX, PY, PW, PH = 46, 116, 1430, 1180
panel(PX, PY, PW, PH, "TVÄRSNITT — BÅDA HUVUDEN + BRÄDA  (skala 1:2,5)", INK)
S = 0.84                                   # px/mm
Ox, Oy = 740, 1050                          # O = brädytans mitt (laserlinje)
def WS(Y, Z): return (Ox + S*Y, Oy - S*Z)   # värld(Y bredd, Z höjd) -> skärm
def adeg(p, q): return math.degrees(math.atan2(q[1]-p[1], q[0]-p[0]))
def uprot(a):
    a = ((a + 180) % 360) - 180
    return a - 180 if a > 90 else (a + 180 if a < -90 else a)
# ---- bräda (75×45) med vankant på båda topphörn + transportband ----
wn = 18
bL = WS(-BW/2, 0); bR = WS(BW/2, 0); bBL = WS(-BW/2, -BT); bBR = WS(BW/2, -BT)
wTL = WS(-BW/2+wn, 0); wTR = WS(BW/2-wn, 0); wEL = WS(-BW/2, -wn); wER = WS(BW/2, -wn)
poly([wEL, wTL, wTR, wER, bBR, bBL], WOOD, "#b9a96f", 1.8)
for i in range(1, 5): line(bL[0]+5, bL[1]+i*7, bR[0]-5, bR[1]+i*7, "#ddd2b4", 1)
beltY = bBL[1]
rect(bL[0]-26, beltY, (bR[0]-bL[0])+52, 14, BLACK, "#1c1f24", 1.2, 3)
txt(Ox, beltY+30, "transportband", 9, "middle", MUTED, 700)
circ(Ox, Oy, 4.5, PURP, "#7a2fb0", 1.3); txt(Ox, Oy-12, "laserlinje (mätpunkt)", 9, "middle", PURP, 700)
# ---- PORTAL ÖVER RULLBANDET: topp-TVÄRBALK (ben + huvudbalk vid LÄNGSÄNDARNA, in i bilden) ----
pby = WS(0, PORTZ)[1]
ADPY = camY + (PORTZ-camZ)*(lasY-camY)/(lasZ-camZ)               # där bänken (baslinjen) möter tvärbalken
TVX = round(ADPY) + 35                                            # tvärbalken sträcker sig bara strax förbi fästena
rect(Ox-TVX*S, pby-9, 2*TVX*S, 17, ALU, ALU2, 1.6, 3)            # TVÄRBALK (kort — bär bara adaptrar + ytkamera)
txt(Ox-TVX*S-8, pby+4, "TOPP-TVÄRBALK (T-spår)", 9.5, "end", MUTED, 700)
# huvudbalk + ben går in i bilden (vid längsändarna) — antydan
rect(Ox-16, pby-30, 32, 22, "#c7cbcf", "#9aa0a6", 1.3, 3); txt(Ox+22, pby-22, "HUVUDBALK + ben → in i bilden", 8, "start", MUTED, 700)
txt(Ox, pby-40, "(portalben vid brädans LÄNGSÄNDAR — utanför bandets gång)", 8.5, "middle", MUTED, 700)
# rullbandets gång (matning i bild-led) — visar varför ben ej kan stå vid sidorna
arrow(bL[0]-86, beltY+6, bL[0]-26, beltY+6, "#b06", 1.8)
txt(bL[0]-88, beltY-5, "rullbandets gång (matning) →", 8, "end", "#b06", 700)
# ---- per huvud: kamera + laser + bänk, HÄNGER från tvärbalken via vinkeladapter ----
def head(sign, col, name):
    cam = WS(sign*camY, camZ); las = WS(sign*lasY, lasZ)
    ux, uy = (las[0]-cam[0]), (las[1]-cam[1]); bl = math.hypot(ux,uy); ux,uy = ux/bl, uy/bl
    # OPTISK BÄNK = EN vinklad bar, går från TVÄRBALKEN (vinkeladapter) ned-ut till lasern.
    t_top = (cam[1]-pby)/uy                                          # backa upp längs bänken till tvärbalkshöjd
    p_top = (cam[0]-ux*t_top, cam[1]-uy*t_top)                       # bänkens övre ände = vid tvärbalken
    p_b   = (las[0]+ux*34, las[1]+uy*34)                             # lite förbi lasern
    line(p_top[0], p_top[1], p_b[0], p_b[1], ALU, 9)                 # bänken (en enda bar, i vinkel)
    rect(p_top[0]-11, p_top[1]-3, 22, 16, ALU3, STEEL, 1.4, 2)       # VINKELADAPTER vid tvärbalken
    txt(p_top[0]+sign*15, p_top[1]+5, "vinkeladapter", 8, "start" if sign>0 else "end", STEEL, 700)
    txt(p_top[0]+sign*15, p_top[1]+17, "(bänk i vinkel)", 7.5, "start" if sign>0 else "end", MUTED, 700)
    # rikta-enhetsvektorer mot O
    def U(p): d=math.hypot(Ox-p[0], Oy-p[1]); return ((Ox-p[0])/d,(Oy-p[1])/d)
    uc, ul = U(cam), U(las)
    # laserblad + kamerasikt
    line(las[0]+ul[0]*70, las[1]+ul[1]*70, Ox, Oy, col, 2.4)
    line(cam[0]+uc[0]*58, cam[1]+uc[1]*58, Ox, Oy, "#8a9099", 1.3, "5 4")
    # kamera (roterad)
    ang = adeg(cam, (Ox,Oy))-90
    add(f'<g transform="translate({cam[0]:.1f},{cam[1]:.1f}) rotate({ang:.1f})">')
    rect(-CAM_W*S/2,0,CAM_W*S,CAM_L*S,"#e9edf1",STEEL,1.4,1); rect(-LENS_D*S/2,CAM_L*S,LENS_D*S,LENS_L*S,"#dfe3e7","#9aa0a6",1.2,1)
    rect(-FILT_D*S/2,(CAM_L+LENS_L)*S,FILT_D*S,FILT_L*S,"#f6d9cf",col,1.4)
    add('</g>')
    # laser (roterad)
    angl = adeg(las, (Ox,Oy))-90
    add(f'<g transform="translate({las[0]:.1f},{las[1]:.1f}) rotate({angl:.1f})">')
    rect(-LAS_D*S/2,0,LAS_D*S,LAS_L*S,"#d7b7b0","#9a5a52",1.3,2)
    add('</g>')
    return cam, las, uc, ul
rcam, rlas, ruc, rul = head(-1, RED, "RÖD")
gcam, glas, guc, gul = head(+1, GRN, "GRÖN")
txt(rcam[0]-8, rcam[1]-12, "RÖD: kamera", 8.5, "end", RED, 700)
txt(rlas[0]-8, rlas[1]+4, "RÖD: laser", 8.5, "end", RED, 700)
txt(gcam[0]+8, gcam[1]-12, "GRÖN: kamera", 8.5, "start", GRN, 700)
txt(glas[0]+8, glas[1]+4, "GRÖN: laser", 8.5, "start", GRN, 700)

# ---- LINJEKAMERA (ytkamera) — EGEN rad, FÖRSKJUTEN +30 mm (EJ på laserlinjen) ----
SURF_WD = 400
COL_OFF = 40                                          # mm: färgraden förskjuten i feed (Y); CAD som-byggt 39,75
lc = WS(COL_OFF, SURF_WD)                             # över färgraden, inte över laserlinjen
cp = WS(COL_OFF, 0)                                   # färgkamerans EGNA mätpunkt på brädytan
lcw, lcl, lld, lll = 36, 40, 44, 50                   # kamera-hus + M42-objektiv (mm)
line(lc[0], pby+8, lc[0], lc[1]-(lcl+lll)*S, ALU2, 5)            # bär-stag från topp-tvärbalk
add(f'<g transform="translate({lc[0]:.1f},{lc[1]:.1f})">')
rect(-lcw*S/2, -(lcl+lll)*S, lcw*S, lcl*S, "#e2ecf6", BLUE, 1.6, 2)        # kamera-hus
rect(-lld*S/2, -lll*S, lld*S, lll*S, "#d8e6f4", "#5f8fc0", 1.4, 2)         # M42-objektiv
add('</g>')
line(lc[0], lc[1], cp[0], cp[1], BLUE, 1.3, "6 4")                        # siktlinje till EGEN rad (ej laserlinjen)
circ(cp[0], cp[1], 4, BLUE, "#1d5fa0", 1.4); txt(cp[0]+9, cp[1]+15, "färgrad (+40 mm)", 8.5, "start", BLUE, 700)
hdim(Ox, cp[0], Oy+22, f"{COL_OFF}", DIMC, 9)                              # offset laserlinje → färgrad
rect(lc[0]+lld*S/2+10, lc[1]-lll*S-2, 28, 9, "#fff8e0", "#c9a13a", 1.3, 2) # vit LED-list
txt(lc[0]+lld*S/2+24, lc[1]-lll*S-8, "vitt LED", 7.5, "middle", "#8a6510", 700)
txt(lc[0]+lcw*S/2+10, lc[1]-(lcl+lll)*S+10, "YTKAMERA (line-scan)", 9, "start", BLUE, 700)
txt(lc[0]+lcw*S/2+10, lc[1]-(lcl+lll)*S+23, "4K färg · M42 · EGEN rad +40 mm (CAD 39,75)", 8, "start", MUTED, 700)
txt(lc[0]+lcw*S/2+10, lc[1]-(lcl+lll)*S+36, "EJ på laserlinjen → ingen laser i färgbilden", 8, "start", MUTED, 700)
vdim(Oy, lc[1], Ox+62, f"{SURF_WD}", BLUE, 11); txt(Ox+78, (Oy+lc[1])/2, "yt-WD", 8.5, "start", BLUE, 700, rot=-90)
# ---- färgkamerans laser-frihet (ingen baffel — offset + osynligt laserplan räcker) ----
txt(lc[0]+lcw*S/2+10, lc[1]-(lcl+lll)*S+49, "laserlinjen utanför FOV → ingen laser i färgbilden", 7.5, "start", "#8a6510", 700)
txt(lc[0]+lcw*S/2+10, lc[1]-(lcl+lll)*S+60, "(laserplan osynligt i ren luft; baffel ej nödv. — add vid damm/glimt)", 7, "start", MUTED, 400)

# ---- LOD-referens + vinklar vid O ----
line(Ox, Oy, Ox, Oy-int(camZ*S)-40, DIMC, 0.7, "4 4"); txt(Ox+8, Oy-int(camZ*S)-30, "lod", 8.5, "start", DIMC, 700)
# röd sida: 15° (lod->kam), 30° (kam->laser); grön spegel
a_lod = -90
a_rcam = adeg((Ox,Oy), rcam); a_rlas = adeg((Ox,Oy), rlas)
a_gcam = adeg((Ox,Oy), gcam); a_glas = adeg((Ox,Oy), glas)
adim(Ox, Oy, 116, a_lod, a_rcam, f"{CAM_A:.0f}°", RED, 11)
adim(Ox, Oy, 158, a_rcam, a_rlas, f"θ {THETA:.0f}°", RED, 11)
adim(Ox, Oy, 116, a_gcam, a_lod, f"{CAM_A:.0f}°", GRN, 11)
adim(Ox, Oy, 158, a_glas, a_gcam, f"θ {THETA:.0f}°", GRN, 11)
txt(Ox-int(lasY*S)-4, Oy-int(lasZ*S)-26, f"laser {LAS_A:.0f}° fr lod", 8.5, "end", RED, 700)
txt(Ox+int(lasY*S)+4, Oy-int(lasZ*S)-26, f"laser {LAS_A:.0f}° fr lod", 8.5, "start", GRN, 700)

# ---- WD-mått (på röd laser + grön kamera) ----
txt((rlas[0]+Ox)/2-16, (rlas[1]+Oy)/2, f"WD {WD:.0f}", 12, "middle", RED, 700, MONO, rot=uprot(adeg(rlas,(Ox,Oy))))
txt((gcam[0]+Ox)/2+16, (gcam[1]+Oy)/2, f"WD {WD:.0f}", 12, "middle", INK, 700, MONO, rot=uprot(adeg(gcam,(Ox,Oy))))
# ---- baslinje per huvud ----
txt((rcam[0]+rlas[0])/2-10, (rcam[1]+rlas[1])/2-12, f"BASLINJE {BASE}", 10, "middle", INK, 700, MONO, rot=uprot(adeg(rcam, rlas)))
txt((gcam[0]+glas[0])/2+10, (gcam[1]+glas[1])/2-12, f"BASLINJE {BASE}", 10, "middle", INK, 700, MONO, rot=uprot(adeg(gcam, glas)))

# ---- höjder (vänster) ----
vdim(Oy, rcam[1], PX+74, f"{camZ}", DIMC, 11, ext=0); txt(PX+58, (Oy+rcam[1])/2-60, "kamerahöjd", 8.5, "middle", MUTED, 700, rot=-90)
vdim(Oy, rlas[1], PX+128, f"{lasZ}", DIMC, 11); txt(PX+112, (Oy+rlas[1])/2-50, "laserhöjd", 8.5, "middle", MUTED, 700, rot=-90)
line(rcam[0], rcam[1], PX+64, rcam[1], DIMC, 0.5, "3 3"); line(rlas[0], rlas[1], PX+118, rlas[1], DIMC, 0.5, "3 3")
line(bL[0], Oy, PX+138, Oy, DIMC, 0.5, "3 3")
# ---- offset (horisontella, ovanför) ----
hdim(rcam[0], gcam[0], rcam[1]-54, f"{CAMCAM}  (kamera↔kamera)", DIMC, 11, ext=44)
hdim(rlas[0], glas[0], rlas[1]+150, f"{LASLAS}  (laser↔laser)", DIMC, 11, ext=20)
hdim(Ox, rcam[0], rcam[1]-22, f"{camY}", DIMC, 10, ext=14)
hdim(Ox, rlas[0], rlas[1]+96, f"{lasY}", DIMC, 10, ext=14)
# ---- brädmått ----
hdim(bL[0], bR[0], beltY+52, f"{BW}", INK, 11, ext=10)
vdim(bR[1], bBR[1], bR[0]+44, f"{BT}", INK, 11, ext=10)
line(bR[0], bR[1], bR[0]+50, bR[1], DIMC, 0.5, "3 3"); line(bBR[0], bBR[1], bR[0]+50, bBR[1], DIMC, 0.5, "3 3")
# portalhöjd
vdim(Oy, pby, gcam[0]+int(camY*S)+90, f"{PORTZ}", DIMC, 10); txt(gcam[0]+int(camY*S)+74, (Oy+pby)/2, "ramhöjd", 8.5, "middle", MUTED, 700, rot=-90)
txt(Ox, PY+PH-16, f"Allt skalenligt 1:2,5 · mått i mm · vinklar i grader · geometri exakt ur WD 760 + armvinklar {CAM_A:.0f}°/{LAS_A:.0f}° (θ {THETA:.0f}°).", 9.5, "middle", MUTED, 400)

# =================================================================== HÖGER: MÅTT-TABELL
CXr = 1496; CWr = 720
panel(CXr, 116, CWr, 360, "MÅTTLISTA (exakt)", BLUE)
tab = [
    ("Arbetsavstånd WD (slant)", f"{WD:.0f} mm", "kamera & laser → laserlinjen"),
    ("Trianguleringsvinkel θ", f"{THETA:.0f}°", "mellan kamera & laser (per huvud)"),
    ("Kamera-arm fr. lod", f"{CAM_A:.0f}°", "brantare armen"),
    ("Laser-arm fr. lod", f"{LAS_A:.0f}°", "mer oblika armen (grazar kanten)"),
    ("Obliquity (siktbisektris)", f"{OBL:.0f}°", "huvudets lutning fr. lod"),
    ("Baslinje kamera↔laser", f"{BASE} mm", "= 2·WD·sin(θ/2)"),
    ("Kamerahöjd ö. brädyta", f"{camZ} mm", "= WD·cos 25°"),
    ("Kamera-offset fr. mitt", f"{camY} mm", "= WD·sin 25°"),
    ("Laserhöjd ö. brädyta", f"{lasZ} mm", "= WD·cos 50°"),
    ("Laser-offset fr. mitt", f"{lasY} mm", "= WD·sin 50°"),
    ("Kamera ↔ kamera", f"{CAMCAM} mm", "de två huvudena"),
    ("Laser ↔ laser", f"{LASLAS} mm", "de två huvudena"),
    ("Ramhöjd (topp-tvärbalk)", f"{PORTZ} mm", "precis ovan kamerorna ~733"),
    ("Ytkamera-WD (line-scan)", f"{400} mm", "rakt ned · avbildar längden"),
    ("Bräda (prototyp)", f"{BW} × {BT} mm", "tvärsnitt, på band"),
]
yy = 156
for k, v, c in tab:
    txt(CXr+16, yy, k, 10.5, "start", INK, 700); txt(CXr+330, yy, v, 11, "start", INK, 700, MONO); txt(CXr+470, yy, c, 9.2, "start", MUTED, 400)
    yy += 22.7

# =================================================================== HÖGER: DETALJER (fästen)
def detbracket(x, y, w, h, title, acc, draw):
    panel(x, y, w, h, title, acc); draw(x, y)
# kamera-tiltfäste
def d_cam(x, y):
    bx, by = x+40, y+118
    poly([(bx,by),(bx+150,by),(bx+150,by-14),(bx+22,by-14)], ALU, ALU2, 1.5)
    hole(bx+40, by-7, 4); hole(bx+110, by-7, 4); txt(bx+75, by+18, "M4 → bänk (c/c 70)", 8.5, "middle", INK, 700)
    add(f'<g transform="translate({bx+150},{by-7}) rotate(-105)">')
    rect(0,-8,104,16,ALU2,STEEL,1.5,2); hole(26,0,3,STEEL); hole(74,0,3,STEEL); add('</g>')
    txt(bx+196, y+72, f"fläns {THETA/2:.0f}° fr. bänk-", 8.5, "start", INK, 700); txt(bx+196, y+86, "normal · justerslits", 8.5, "start", MUTED, 700)
    txt(bx+196, y+110, "2× M3 → kamerans", 8.5, "start", INK, 700); txt(bx+196, y+124, "M3-hålbild (c/c 20)", 8.5, "start", INK, 700)
    adim(bx+150, by-7, 36, 180, 190, f"{THETA/2:.0f}°", INK, 10)
detbracket(CXr, 492, 354, 222, "DETALJ B — kamera-tiltfäste", INK, d_cam)
# laserklämma
def d_las(x, y):
    lx, ly = x+120, y+108
    circ(lx, ly, 38, ALU, ALU2, 1.6); circ(lx, ly, 18, "#fff", RED, 1.4); txt(lx, ly+4, "Ø18", 10, "middle", RED, 700, MONO)
    rect(lx-26, ly-46, 52, 10, ALU2, STEEL, 1.2, 2); hole(lx-16, ly-41, 3, STEEL); hole(lx+16, ly-41, 3, STEEL)
    txt(lx+54, ly-18, "split-klämma:", 8.5, "start", INK, 700)
    txt(lx+54, ly-4, "rotera → räta linjen", 8.5, "start", MUTED, 700)
    txt(lx+54, ly+10, "glid → fokus @ 760", 8.5, "start", MUTED, 700)
    poly([(lx-30,ly+58),(lx+30,ly+58),(lx+38,ly+74),(lx-22,ly+74)], ALU, ALU2, 1.4); hole(lx-14,ly+66,4); hole(lx+14,ly+66,4)
    txt(lx, ly+92, f"M4 → bänk · tilt {THETA/2:.0f}° fr normal", 8.5, "middle", INK, 700)
detbracket(CXr+366, 492, 354, 222, "DETALJ C — laserklämma Ø18", INK, d_las)
# portalfäste
def d_port(x, y):
    mx, my = x+90, y+92
    rect(mx-60, my-60, 80, 80, ALU, ALU2, 1.6, 4); txt(mx-20, my-68, "sidostativ", 8.5, "middle", MUTED, 700)
    for s in range(int(my-56), int(my+12), 11): line(mx-60, s, mx-38, s, HATCH, 0.6)
    rect(mx+20, my-50, 20, 64, ALU3, STEEL, 1.5, 2); hole(mx+30, my-26, 4, STEEL)
    add(f'<g transform="translate({mx+40},{my+14}) rotate(30)"><rect x="0" y="0" width="150" height="15" fill="{ALU}" stroke="{ALU2}" stroke-width="1.6"/></g>')
    txt(mx+150, my+96, "OPTISK BÄNK", 8.5, "middle", INK, 700)
    line(mx+40, my+14, mx+40, my+120, DIMC, 0.6, "3 3")
    line(mx+40, my+14, mx+40+120*math.cos(math.radians(30)), my+14+120*math.sin(math.radians(30)), DIMC, 0.6)
    adim(mx+40, my+14, 78, 90, 60, f"{OBL:.0f}°", INK, 11)
    txt(x+14, y+200, "Vinkeladaptern (justerbar) mot sidostativet ger obliquity. Bänkens normal 30° fr. lod.", 8.5, "start", MUTED, 400)
detbracket(CXr, 730, CWr, 222, "DETALJ D — vinkeladapter & obliquity", INK, d_port)

# =================================================================== HÖGER: FÄSTDON + NOTER + HUVUD
panel(CXr, 968, 354, 196, "FÄSTDON (per huvud)", BLUE)
parts = [("Optisk bänk", "alu ~320×80×10", "1"), ("Kamera-tiltfäste", "θ/2-fläns (10°)", "1"),
         ("Laserklämma Ø18", "split + 10°-tilt", "1"), ("Vinkeladapter", "justerbar, T-spår", "2"),
         ("M3×6 / M4×10 / M6×16", "+ T-muttrar", "set")]
yy = 1000
for nm, sp, q in parts:
    txt(CXr+14, yy, nm, 9.5, "start", INK, 700); txt(CXr+200, yy, sp, 8.6, "start", MUTED); txt(CXr+340, yy, q, 9, "end", INK, 700, MONO); yy += 22
panel(CXr+366, 968, 354, 196, "NOTER", INK)
notes = ["1.  Mått mm · vinklar grader · skala 1:2,5.",
         "2.  Vinklar nominella → finjustera optiskt:",
         "     kamera+laser ska KONVERGERA på linjen @ 760.",
         "3.  Filter på objektivfronten (M30.5).",
         "4.  Laser Klass 3B → kåpa + skylt + glasögon.",
         "5.  RÖD=V-kant, GRÖN=H-kant (spegel)."]
yy = 998
for ln_ in notes:
    txt(CXr+380, yy, ln_, 9.2, "start", INK, 400); yy += 17 if not ln_.startswith("     ") else 15

tbx, tby, tbw, tbh = CXr, 1180, CWr, 280
rect(tbx, tby, tbw, tbh, "#fff", INK, 1.6)
line(tbx, tby+150, tbx+tbw, tby+150, INK, 1)
for fx in (0.30, 0.58, 0.80): line(tbx+tbw*fx, tby, tbx+tbw*fx, tby+150, INK, 0.9)
txt(tbx+16, tby+34, "VIRKESSKANNER", 16, "start", INK, 700)
txt(tbx+16, tby+58, "MÄTSTATION — DUBBELT PROFILHUVUD", 12.5, "start", INK, 700)
txt(tbx+16, tby+80, "Dubbel-oblik · RÖD 650 + GRÖN 520", 10.5, "start", MUTED, 400)
txt(tbx+16, tby+106, "Kamera+laser samma sida per huvud;", 10, "start", INK, 400)
txt(tbx+16, tby+124, "två huvuden, var sin sida, samma laserlinje.", 10, "start", INK, 400)
def cell(fx, k, v):
    x = tbx+tbw*fx; txt(x+10, tby+22, k, 8.5, "start", MUTED, 700); txt(x+10, tby+44, v, 12, "start", INK, 700, MONO)
cell(0.30, "WD", f"{WD:.0f}"); cell(0.58, "θ / OBLIK", f"{THETA:.0f}°/{OBL:.0f}°"); cell(0.80, "RITN", "PH-650-M2")
cell(0.30, "BASLINJE", "")  # placeholder spacing
txt(tbx+tbw*0.30+10, tby+72, "BASLINJE", 8.5, "start", MUTED, 700); txt(tbx+tbw*0.30+10, tby+94, f"{BASE}", 12, "start", INK, 700, MONO)
txt(tbx+tbw*0.58+10, tby+72, "KAM/LAS-H", 8.5, "start", MUTED, 700); txt(tbx+tbw*0.58+10, tby+94, f"{camZ}/{lasZ}", 12, "start", INK, 700, MONO)
txt(tbx+tbw*0.80+10, tby+72, "SKALA", 8.5, "start", MUTED, 700); txt(tbx+tbw*0.80+10, tby+94, "1:2,5", 12, "start", INK, 700, MONO)
txt(tbx+tbw*0.80+10, tby+120, "ENHET mm", 9, "start", MUTED, 400)
txt(tbx+16, tby+178, "Geometri exakt ur WD + armvinklar (src/hardware.py · verify_optics.py). Databladsbekräftad optik.", 9, "start", MUTED, 400)
txt(tbx+16, tby+200, "Optik: MV-CS050-10UM · MVL-MF1228M-8MP · FS03-BP650/525 · MZLaser AJPWHF (638/520).", 9, "start", MUTED, 400)
txt(tbx+16, tby+222, "Bänk + fästen = tillverkningsdelar (alu). Grön = spegelvänd.", 9, "start", MUTED, 400)
txt(tbx+16, tby+250, "© Virkesskanner — konstruktionsunderlag", 9, "start", MUTED, 400)

add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "head-mech.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} el) · WD={WD:.0f} θ={THETA:.0f}° baslinje={BASE} camZ={camZ} lasZ={lasZ} cam↔cam={CAMCAM} las↔las={LASLAS}")
