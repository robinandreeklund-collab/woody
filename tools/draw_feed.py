#!/usr/bin/env python3
"""Matning & styrning — detaljritning (SVG): vad Jetson behöver för att styra
rullbanden, och VAR encodern monteras. -> prototype-feed-control.svg
"""
from __future__ import annotations
import os, math
W, H = 1720, 1180
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
BELT, GOLD, ORANGE = "#444a52", "#b9a96f", "#e0892b"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=12, anchor="start", fill=INK, weight=400, fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')
def L(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def circ(x, y, rr, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=2.0):
    L(x1, y1, x2, y2, stroke, w); a = math.atan2(y2 - y1, x2 - x1); l = 10
    for s in (0.5, -0.5): L(x2, y2, x2 - l * math.cos(a - s), y2 - l * math.sin(a - s), stroke, w)
def panel(x, y, w, h, title, acc):
    rect(x, y, w, h, "#fff", acc, 1.4, 8); rect(x, y, w, 28, acc, acc, 0, 8)
    txt(x + 12, y + 19, title, 12.5, "start", "#fff", 700, SANS)
def badge(x, y, n, c):
    circ(x, y, 13, c, c, 0); txt(x, y + 5, str(n), 13, "middle", "#fff", 700, SANS)
def node(x, y, w, h, t, s, acc):
    rect(x, y, w, h, "#fff", acc, 1.8, 8); rect(x, y, w, 22, acc, acc, 0, 8)
    txt(x + w/2, y + 16, t, 11, "middle", "#fff", 700, SANS)
    if s: txt(x + w/2, y + 40, s, 9.5, "middle", INK, 400, SANS)
def wire(x1, y1, x2, y2, lab, c):
    arrow(x1, y1, x2, y2, c, 2); mx, my = (x1+x2)/2, (y1+y2)/2
    rect(mx - len(lab)*3.6 - 5, my - 9, len(lab)*7.2 + 10, 16, "#fff", c, 0.8, 3); txt(mx, my + 3, lab, 9, "middle", c, 700, MONO)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): L(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): L(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W - 32, H - 32, "none", INK, 2); rect(24, 24, W - 48, H - 48, "none", MUTED, 0.8)
txt(44, 62, "MATNING & STYRNING — så styr Jetson rullbanden + var encodern sitter", 23, "start", INK, 700, SANS)
txt(44, 88, "Rullbandet har en 24 V-motor men ingen fast brädposition. Jetson styr fart+riktning via en motordrivare; encoder + fotcell ger position.",
    13, "start", MUTED, 400, SANS)
L(44, 100, W - 44, 100, INK, 1.5)

# ===================== VÄNSTER: MONTERING (sidovy) =====================
panel(40, 116, 820, 600, "VAR SAKERNA SITTER (sidovy av rullbandet)", INK)
fy = 560                                  # bandets ovansida
# frame base
rect(90, fy + 70, 720, 14, "#cdc9bd", "#a7a394", 1.2, 3); txt(450, fy + 100, "RAM / STATIV (2020-alu)", 9.5, "middle", MUTED, 700)
# rollers + belt
for cx in (190, 690): circ(cx, fy + 30, 30, "#cfd2d6", "#7a7f86", 1.6); circ(cx, fy + 30, 5, MUTED, MUTED)
L(160, fy, 720, fy, BELT, 5); L(160, fy + 60, 720, fy + 60, BELT, 5)
txt(440, fy + 50, "RULLBAND (24 V, 50 mm/s)", 9.5, "middle", "#dfe3e8", 700)
# board on belt
rect(330, fy - 22, 250, 22, "#e9e1cf", GOLD, 1.6); txt(390, fy - 7, "BRÄDA", 10, "middle", "#8a7d4e", 700)
arrow(470, fy - 34, 575, fy - 34, "#b06", 2.2); txt(522, fy - 40, "matning", 9, "middle", "#b06", 700)
# (1) encoder + measuring wheel on spring arm pressing the board
postx = 470
L(postx, fy - 230, postx, fy - 60, ALU, 6)                 # post
L(postx, fy - 200, 430, fy - 70, ALU, 5)                   # hinged arm
# spring (zigzag)
sx, sy = postx + 6, fy - 215
pts = " ".join(f"{sx + (i%2)*14},{sy + i*7}" for i in range(6))
add(f'<polyline points="{pts}" fill="none" stroke="{MUTED}" stroke-width="1.4"/>')
circ(430, fy - 52, 18, "#f3e6fb", PURP, 1.8); circ(430, fy - 52, 4, PURP, PURP)   # measuring wheel
rect(398, fy - 96, 64, 30, "#efe6f7", PURP, 1.6, 4); txt(430, fy - 76, "ENCODER", 9, "middle", PURP, 700)
badge(305, fy - 200, 1, PURP)
txt(285, fy - 204, "Mäthjul mot brädans ovansida (fjäderarm).", 10.5, "end", PURP, 700)
txt(285, fy - 187, "Mäter brädans VERKLIGA väg (immun mot slir).", 9.5, "end", INK, 400)
txt(285, fy - 170, "→ Jetson GPIO A/B (pin 29 / 7).", 9.5, "end", INK, 400)
# (2) entry photoeye
rect(210, fy - 60, 26, 20, "#ffe7d8", RED, 1.5, 3); L(223, fy - 40, 223, fy - 22, RED, 1.4, "4 3")
badge(150, fy - 100, 2, RED)
txt(170, fy - 104, "Fotcell vid INGÅNGEN: framkant bryter", 10, "start", RED, 700)
txt(170, fy - 88, "strålen → nollställer position. → pin 22.", 9.5, "start", INK, 400)
# (3) motor
rect(700, fy + 12, 70, 36, "#e9eef5", BLUE, 1.5, 4); txt(735, fy + 35, "MOTOR", 9.5, "middle", BLUE, 700)
badge(660, fy + 110, 3, BLUE); txt(688, fy + 110, "24 V-motor i rullbandet → matas av motordrivaren.", 10.5, "start", BLUE, 700)

# ===================== HÖGER: STYRKEDJA =====================
panel(880, 116, 800, 600, "STYRKEDJA — Jetson → rullband", INK)
node(910, 170, 200, 130, "JETSON Orin Nano", "", JET)
txt(1010, 222, "PWM + GPIO (40-pin)", 9.5, "middle", INK)
txt(1010, 240, "ut: EN·RPWM·LPWM", 9, "middle", MUTED, 700, MONO)
txt(1010, 256, "in: enc A/B · fotcell", 9, "middle", MUTED, 700, MONO)
node(1230, 178, 200, 96, "MOTORDRIVARE", "BTS7960 (H-brygga)", ORANGE)
node(1530, 192, 120, 70, "MOTOR ×2", "rullband", BLUE)
node(1230, 330, 200, 56, "NÄTAGGREGAT 24 V", "matar motorn", "#c89028")
node(910, 360, 180, 56, "ENCODER + mäthjul", "LPD3806", PURP)
node(910, 450, 180, 56, "FOTCELL (ingång)", "E3F-DS30C4", RED)
wire(1110, 226, 1230, 226, "EN·RPWM·LPWM", JET)
wire(1430, 226, 1530, 226, "M+ / M−", ORANGE)
arrow(1330, 330, 1330, 274, "#c89028", 2); txt(1342, 304, "24 V (B+/B−)", 9, "start", "#c89028", 700, MONO)
wire(1090, 388, 1010, 300, "A→29 · B→7", PURP)
wire(1090, 478, 1010, 300, "→ pin 22", RED)
# GND-rail
gy = 560; L(940, gy, 1620, gy, INK, 2.2); txt(944, gy - 8, "GEMENSAM GND (Jetson ↔ drivare ↔ 24 V-PSU) — KRITISKT", 10.5, "start", INK, 700)
for gx in (1010, 1330, 1590): L(gx, 300 if gx==1010 else (386 if gx==1330 else 262), gx, gy, INK, 1, "3 3")

# ===================== BOTTEN: DELLISTA =====================
panel(40, 736, 1640, 380, "DELAR FÖR JETSON-STYRD MATNING (allt ligger i Fas 1)", INK)
rows = [
    ("Motordrivare", "BTS7960 H-brygga (43 A)", "Jetson PWM+GPIO → motorns fart & riktning. Pin 31 EN · 32 RPWM (fram) · 33 LPWM (back).", "~80 kr"),
    ("Nätaggregat 24 V", "24 V 5 A", "Matar motordrivaren (motorns ström). Jetson-GPIO orkar INTE driva motorn direkt.", "~150 kr"),
    ("Encoder + mäthjul", "LPD3806-600BM + gummihjul Ø64", "Mäter brädans väg → position. Pin 29 (A) / 7 (B). MONTERAS på fjäderarm mot brädans ovansida.", "~250 kr"),
    ("Fotcell (ingång)", "E3F-DS30C4 (NPN)", "Brädans framkant bryter strålen → nollställer position (rullband har ingen fast pos). Pin 22.", "~80 kr"),
    ("Kablar + GND", "dupont/terminal", "3 styrtrådar Jetson→drivare, 2 motortrådar, 2× 24 V. GEMENSAM GND mellan allt.", "~100 kr"),
]
ty = 770
txt(60, ty, "DEL", 10.5, "start", MUTED, 700, MONO); txt(300, ty, "MODELL", 10.5, "start", MUTED, 700, MONO)
txt(600, ty, "VAD DEN GÖR / KOPPLING", 10.5, "start", MUTED, 700, MONO); txt(1620, ty, "PRIS", 10.5, "end", MUTED, 700, MONO)
L(60, ty + 8, 1660, ty + 8, DIMC, 1)
for i, (a, b, c, d) in enumerate(rows):
    ry = ty + 20 + i * 56
    if i % 2: rect(50, ry, 1620, 56, PANEL, "none", 0)
    txt(60, ry + 24, a, 11.5, "start", INK, 700, SANS)
    txt(300, ry + 24, b, 10.5, "start", MUTED, 400, SANS)
    txt(600, ry + 24, c, 10.5, "start", INK, 400, SANS)
    txt(1620, ry + 24, d, 11, "end", INK, 700, MONO)
txt(60, ty + 312, "OBS: kontrollera att rullbandets motor går att koppla direkt (2 terminaler). Många kommer med en fast regulator — "
    "byt ut den mot BTS7960 så Jetson får full fram/back+fart-styrning.", 10.5, "start", "#b00", 700)

tb_x, tb_y = W - 470, H - 70
rect(tb_x, tb_y, 426, 48, "#fff", INK, 1.4); L(tb_x, tb_y + 24, tb_x + 426, tb_y + 24, INK, 1); L(tb_x + 264, tb_y, tb_x + 264, tb_y + 48, INK, 1)
txt(tb_x + 10, tb_y + 16, "VIRKESSKANNER — MATNING/STYRNING", 11, "start", INK, 700, SANS); txt(tb_x + 274, tb_y + 16, "PROTO-FEED", 10.5, "start", INK)
txt(tb_x + 10, tb_y + 40, "encoder = mäthjul mot brädan", 9.5, "start", MUTED); txt(tb_x + 274, tb_y + 40, "allt i Fas 1", 9.5, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-feed-control.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
