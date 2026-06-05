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
# (1) FAST ANSLAG (bakkant = nollposition)
L(300, fy - 58, 300, fy, ALU, 6); L(300, fy - 58, 324, fy - 58, ALU, 5)
rect(320, fy - 58, 8, 36, "#9aa0a8", "#6e747b", 1.3)
badge(120, fy - 232, 1, GRN)
txt(140, fy - 236, "FAST ANSLAG (ramen) = känd nollposition.", 11, "start", GRN, 700)
txt(140, fy - 219, "Brädan läggs mot det vid laddning; encodern", 9.5, "start", INK, 400)
txt(140, fy - 202, "räknar bandets väg därifrån → vi vet alltid", 9.5, "start", INK, 400)
txt(140, fy - 185, "var brädan är (antar ingen slir bräda↔band).", 9.5, "start", INK, 400)
L(150, fy - 178, 322, fy - 40, GRN, 1, "3 3")
# (2) Motorns INBYGGDA Hall (Signal-pin) — finns redan på drivenheten
rect(700, fy + 12, 60, 34, "#e9eef5", BLUE, 1.5, 4); txt(730, fy + 33, "MOTOR", 9, "middle", BLUE, 700)
rect(763, fy + 13, 30, 32, "#dfe9d8", "#5a7a4a", 1.4, 3); txt(778, fy + 26, "Hall", 7.5, "middle", "#3a5a2a", 700); txt(778, fy + 38, "PCB", 7, "middle", "#5a7a4a")
txt(800, fy + 20, "Signal", 7.5, "start", PURP, 700); txt(800, fy + 32, "24V−", 7, "start", MUTED); txt(800, fy + 43, "24V+", 7, "start", MUTED)
badge(470, fy - 232, 2, PURP)
txt(490, fy - 236, "MOTORNS INBYGGDA HALL (Signal-pin) — finns redan!", 10.5, "start", PURP, 700)
txt(490, fy - 219, "3 terminaler: Signal / 24V− / 24V+. Signal = puls", 9.5, "start", INK, 400)
txt(490, fy - 202, "∝ varvtal → Jrk G2 frekvens-FB (closed-loop fart).", 9.5, "start", INK, 400)
txt(490, fy - 185, "Ingen extern encoder. Verifiera Signal-spänning!", 9.5, "start", "#b00", 700)
L(792, fy - 178, 792, fy + 14, PURP, 1, "3 3")
# (3) fotcell (valfri backup / brädetektering)
rect(360, fy - 60, 24, 18, "#ffe7d8", RED, 1.4, 3); L(372, fy - 42, 372, fy - 22, RED, 1.3, "4 3")
badge(120, fy - 150, 3, RED)
txt(140, fy - 146, "Fotcell (valfri): brädetektering + om-nollning.", 10, "start", RED, 700)
L(150, fy - 142, 372, fy - 52, RED, 1, "3 3")

# ===================== HÖGER: STYRKEDJA =====================
panel(880, 116, 800, 600, "STYRKEDJA — Jetson → Jrk G2 → rullband", INK)
node(910, 175, 190, 120, "JETSON Orin Nano", "", JET)
txt(1005, 226, "USB / UART / I²C", 9.5, "middle", INK)
txt(1005, 244, "→ Jrk G2: målfart", 9, "middle", MUTED, 700, MONO)
txt(1005, 260, "in: fotcell (pin 22)", 9, "middle", MUTED, 700, MONO)
node(1230, 180, 215, 110, "JRK G2 24v13", "closed-loop FART · frekvens-FB", ORANGE)
node(1560, 200, 110, 70, "MOTOR ×2", "rullband", BLUE)
node(1175, 360, 150, 50, "24 V-PSU", "motorström", "#c89028")
node(1350, 360, 175, 50, "Motorns Hall 'Signal'", "inbyggd, 1-kanal", PURP)
node(910, 360, 175, 50, "FOTCELL (valfri)", "E3F-DS30C4", RED)
wire(1100, 235, 1230, 235, "USB/I²C: målfart", JET)
wire(1445, 235, 1560, 235, "M+ / M−", ORANGE)
arrow(1245, 360, 1290, 290, "#c89028", 2); txt(1232, 332, "24 V", 9, "end", "#c89028", 700, MONO)
arrow(1437, 360, 1400, 290, PURP, 2); txt(1450, 332, "Signal (FB)", 9, "start", PURP, 700, MONO)
wire(1085, 385, 1010, 295, "pin 22", RED)
gy = 560; L(940, gy, 1620, gy, INK, 2.2); txt(944, gy - 8, "GEMENSAM GND (Jetson ↔ Jrk G2 ↔ 24 V-PSU ↔ motorns Signal-GND) — KRITISKT", 10, "start", INK, 700)
for gx, y0 in ((1005, 295), (1250, 410), (1640, 270)): L(gx, y0, gx, gy, INK, 1, "3 3")

# ===================== BOTTEN: DELLISTA =====================
panel(40, 736, 1640, 380, "DELAR FÖR JETSON-STYRD MATNING (allt ligger i Fas 1)", INK)
rows = [
    ("Motorstyrning", "Pololu Jrk G2 24v13 (#3147)", "6,5–40 V (täcker 24 V), 13 A. TACHOMETER/FREKVENS-FB → tar motorns Hall-Signal direkt. Jetson → USB/UART/I²C: målfart.", "~900 kr"),
    ("Position", "motorns Hall 'Signal' (1-kanal)", "Finns REDAN på motorn → Jrk G2 frekvens-FB (closed-loop fart). Position: pulsräkning + anslag-noll. Ev. nivåanpassning.", "~30 kr"),
    ("Fast anslag", "alu-vinkel (bakkant)", "Brädans bakkant vilar mot ramen vid laddning → KÄND nollposition.", "~150 kr"),
    ("Nätaggregat 24 V", "24 V 5 A", "Matar Jrk G2/motorn (ingår om rullbandet köps 'with Power Supply').", "~150 kr"),
    ("Fotcell (valfri)", "E3F-DS30C4 (NPN)", "Brädetektering + ev. om-nollning → Jetson pin 22. Anslag+Hall = primär position.", "~80 kr"),
    ("Kablar + GND", "USB/UART + ström", "Jetson↔Jrk G2, motorns Signal→Jrk, 24 V, motortrådar. GEMENSAM GND.", "~100 kr"),
]
ty = 770
txt(60, ty, "DEL", 10.5, "start", MUTED, 700, MONO); txt(300, ty, "MODELL", 10.5, "start", MUTED, 700, MONO)
txt(600, ty, "VAD DEN GÖR / KOPPLING", 10.5, "start", MUTED, 700, MONO); txt(1620, ty, "PRIS", 10.5, "end", MUTED, 700, MONO)
L(60, ty + 8, 1660, ty + 8, DIMC, 1)
for i, (a, b, c, d) in enumerate(rows):
    ry = ty + 18 + i * 48
    if i % 2: rect(50, ry, 1620, 48, PANEL, "none", 0)
    txt(60, ry + 20, a, 11.5, "start", INK, 700, SANS)
    txt(300, ry + 20, b, 10.5, "start", MUTED, 400, SANS)
    txt(600, ry + 20, c, 10.5, "start", INK, 400, SANS)
    txt(1620, ry + 20, d, 11, "end", INK, 700, MONO)
txt(60, ty + 314, "OBS: motorns 3 trådar → 24V± på Jrk-utgången, Signal till Jrk:s FB-ingång. Jrk G2 sköter fartloopen från Hall-Signalen; "
    "Jetson skickar bara målfart. Verifiera Signal-nivå (om open-collector mot 24 V → nivåanpassa till 3,3 V).", 10.5, "start", "#b00", 700)

tb_x, tb_y = W - 470, H - 70
rect(tb_x, tb_y, 426, 48, "#fff", INK, 1.4); L(tb_x, tb_y + 24, tb_x + 426, tb_y + 24, INK, 1); L(tb_x + 264, tb_y, tb_x + 264, tb_y + 48, INK, 1)
txt(tb_x + 10, tb_y + 16, "VIRKESSKANNER — MATNING/STYRNING", 11, "start", INK, 700, SANS); txt(tb_x + 274, tb_y + 16, "PROTO-FEED", 10.5, "start", INK)
txt(tb_x + 10, tb_y + 40, "encoder = mäthjul mot brädan", 9.5, "start", MUTED); txt(tb_x + 274, tb_y + 40, "allt i Fas 1", 9.5, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-feed-control.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
