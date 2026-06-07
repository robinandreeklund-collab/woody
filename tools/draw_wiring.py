#!/usr/bin/env python3
"""Komplett kopplingsritning (SVG): FAS 1-layout (rullband + röd-huvud + encoder +
Jetson-styrning) + fullständigt kopplingsschema (alla laser, kameror, punktlaser,
RGB/NIR-strobe, motor, encoder) + Jetson I/O-budget.

    python tools/draw_wiring.py   # -> prototype-wiring.svg i projektroten
"""
from __future__ import annotations
import os, sys, math

W, H = 1700, 1460
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
F1, F2 = "#2f9e6e", "#7a3fb0"          # fas-färger
BELT, SURFC, GOLD = "#444a52", "#7a3fb0", "#b9a96f"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"; SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=13, anchor="start", fill=INK, weight=400, fam=MONO):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')
def line(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def circ(x, y, rr, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.6):
    line(x1, y1, x2, y2, stroke, w); a = math.atan2(y2 - y1, x2 - x1); L = 9
    for s in (0.5, -0.5): line(x2, y2, x2 - L * math.cos(a - s), y2 - L * math.sin(a - s), stroke, w)
def node(x, y, w, h, title, sub, acc):
    rect(x, y, w, h, "#fff", acc, 1.6, 8)
    rect(x, y, w, 22, acc, acc, 0, 8)
    txt(x + 10, y + 16, title, 11, "start", "#fff", 700, SANS)
    txt(x + 10, y + 38, sub, 9, "start", INK, 400, SANS)
def conn(p1, p2, label, color):
    arrow(p1[0], p1[1], p2[0], p2[1], color, 1.8)
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    bw = len(label) * 6.0 + 8
    rect(mx - bw / 2, my - 9, bw, 16, "#fff", color, 0.8, 3)
    txt(mx, my + 3, label, 8.5, "middle", color, 700)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(18, 18, W - 36, H - 36, "none", INK, 2); rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)
txt(48, 64, "VIRKESSKANNER — FAS 1-LAYOUT + KOMPLETT KOPPLINGSSCHEMA", 23, "start", INK, 700, SANS)
txt(48, 90, "Fas 1 = röd-profilerare på 2 transportband (RoboClaw 2x7A synkar banden via 2 rull-encodrar; band B = RS-422 → kamerans Line0 native + 26C32→EN2; anhåll+fotocell=nolla). "
            "Fas 2 = grön modul + 3× LR400 (RS-485) + line-scan-färgyta + vitljus. Alla anslutningar + Jetson I/O-budget.", 13, "start", MUTED, 400, SANS)
line(48, 104, W - 48, 104, INK, 1.5)
# fas-legend
rect(W - 360, 44, 14, 14, F1, F1, 0, 3); txt(W - 342, 56, "Fas 1", 11, "start", F1, 700, SANS)
rect(W - 270, 44, 14, 14, F2, F2, 0, 3); txt(W - 252, 56, "Fas 2 (tillägg)", 11, "start", F2, 700, SANS)

# ===================== FAS 1-LAYOUT (vänster, sidovy) =====================
gx, gy = 48, 130
rect(gx, gy, 540, 590, "#fff", INK, 1.2, 8)
rect(gx, gy, 540, 28, F1, F1, 0, 8); txt(gx + 12, gy + 19, "FAS 1 — FYSISK LAYOUT (sidovy)", 12, "start", "#fff", 700, SANS)
ox, oy = gx + 40, gy + 360                      # golv-referens
# rullband (2 rullar + bana + bräda)
line(ox, oy, ox + 420, oy, INK, 1.5)
for cx in (ox + 70, ox + 350):
    circ(cx, oy - 16, 16, "#cfd2d6", "#7a7f86", 1.4); circ(cx, oy - 16, 4, MUTED, MUTED, 0)
line(ox + 54, oy - 32, ox + 366, oy - 32, BELT, 4)              # bana
txt(ox + 210, oy + 18, "TRANSPORTBAND (svart matt, 24 V, ~50 mm/s)", 9.5, "middle", MUTED, 700)
rect(ox + 150, oy - 56, 150, 22, "#e9e1cf", GOLD, 1.4)          # bräda
txt(ox + 225, oy - 41, "bräda 500×75", 8.5, "middle", "#8a7d4e", 700)
# FAST ANHÅLL (bakkant) + fotocell = nolla
rect(ox + 138, oy - 70, 8, 36, "#9aa0a8", "#6e747b", 1)
txt(ox + 134, oy - 76, "FAST ANHÅLL", 8, "end", MUTED, 700)
rect(ox + 122, oy - 48, 11, 15, "#16212e", "#c98a16", 1.2)
txt(ox + 116, oy - 56, "fotocell", 8, "end", "#c98a16", 700)
txt(ox + 116, oy - 44, "(nolla)", 8, "end", "#c98a16", 700)
# rull-encodrar mot bandens retursida (A single-ended→RoboClaw; B RS-422→kamera+26C32→RoboClaw)
circ(ox + 250, oy + 30, 9, "#bfe6c8", GRN, 1.4); txt(ox + 264, oy + 34, "encoder A (single-end)→EN1 · B (RS-422)→kamera Line0 + 26C32→EN2", 7.5, "start", GRN, 700)
line(ox + 250, oy + 21, ox + 250, oy, GRN, 1, "2 3", 0.7)
# RÖD-HUVUD (oblik 30°): laser+kamera
hx, hy = ox + 120, oy - 230
rect(hx, hy, 120, 46, "#fde9e3", RED, 1.6, 5); rect(hx, hy, 120, 14, RED, RED, 0, 5)
txt(hx + 60, hy + 10, "RÖD-HUVUD", 9, "middle", "#fff", 700, SANS)
txt(hx + 60, hy + 30, "650 laser + CS050", 8, "middle", INK)
arrow(hx + 60, hy + 46, ox + 225, oy - 56, RED, 2)
txt(hx - 6, hy + 70, "30°", 9, "end", RED, 700)
# stativ-ben
line(hx + 10, hy + 46, hx + 10, oy, ALU, 4); line(ox + 360, hy + 70, ox + 360, oy, ALU, 4)
line(hx + 10, hy, ox + 360, hy + 24, ALU, 5)                    # tvärbalk
txt(ox + 360, hy + 14, "stativ", 8, "start", MUTED, 700)
# RoboClaw 2x7A (2 kanaler) + Jetson
rect(ox + 378, oy - 42, 76, 36, "#e9eef5", BLUE, 1.4, 4); txt(ox + 416, oy - 24, "RoboClaw", 8.5, "middle", BLUE, 700); txt(ox + 416, oy - 13, "2x7A (USB)", 8, "middle", BLUE, 700)
arrow(ox + 378, oy - 24, ox + 366, oy - 18, BLUE, 1.6)
rect(ox + 150, oy + 40, 150, 50, "#e6efe6", JET, 1.6, 6)
txt(ox + 225, oy + 62, "JETSON Orin Nano", 10.5, "middle", JET, 700, SANS)
txt(ox + 225, oy + 78, "styr matning + U-Net", 8.5, "middle", MUTED)
for tx, lab in [(hx + 70, "USB3"), (ox + 416, "RoboClaw"), (ox + 128, "fotocell")]:
    line(tx, oy + 40, tx, oy - 4, JET, 0.8, "2 3", 0.6)
# fram/back
arrow(ox + 175, oy - 78, ox + 275, oy - 78, "#b06", 2); arrow(ox + 275, oy - 92, ox + 175, oy - 92, BLUE, 1.6)
txt(ox + 225, oy - 100, "fram / back (multi-pass)", 8.5, "middle", "#b06", 700)

# ===================== KOMPLETT KOPPLINGSSCHEMA (höger) =====================
wx, wy = 612, 130
rect(wx, wy, W - 48 - wx, 590, "#fff", INK, 1.2, 8)
rect(wx, wy, W - 48 - wx, 28, INK, INK, 0, 8); txt(wx + 12, wy + 19, "KOMPLETT KOPPLINGSSCHEMA — allt till Jetson", 12, "start", "#fff", 700, SANS)
# Jetson i mitten
JX, JY, JW, JH = wx + 380, wy + 250, 250, 120
rect(JX, JY, JW, JH, "#e6efe6", JET, 2, 8); rect(JX, JY, JW, 24, JET, JET, 0, 8)
txt(JX + JW / 2, JY + 17, "JETSON ORIN NANO SUPER", 11.5, "middle", "#fff", 700, SANS)
txt(JX + JW / 2, JY + 44, "4× USB3 · 1× GbE (RJ45)", 9.5, "middle", INK, 400, SANS)
txt(JX + JW / 2, JY + 60, "40-pin: GPIO · SPI×2 · I²C×2 · PWM", 9.5, "middle", INK, 400, SANS)
txt(JX + JW / 2, JY + 78, "DC-in 7–25 V · ingen ADC behövs", 9.5, "middle", JET, 700, SANS)
txt(JX + JW / 2, JY + 100, "(LR400 = RS-485 digitalt)", 9, "middle", MUTED, 400, SANS)
Lc = (JX, JY + JH / 2); Rc = (JX + JW, JY + JH / 2)
# vänster: profil-röd + matning/position
left = [
    (wy + 70, "Profilkamera RÖD", "MV-CS050-10UM", F1, "USB3 (egen)"),
    (wy + 150, "Linjelaser RÖD 650", "MZLaser, CW", F1, "5 V + GPIO/TTL"),
    (wy + 230, "RoboClaw 2x7A", "2 bandmotorer, synk", F1, "USB (1 kort)"),
    (wy + 305, "Encoder band A", "E6B2-CWZ6C (single-end)", F1, "→ EN1"),
    (wy + 370, "Encoder band B (ref)", "E6B2-CWZ1X (RS-422 @5V)", F1, "→ kamera+EN2"),
    (wy + 435, "Anhåll-fotocell", "nolla / home", F1, "GPIO"),
]
for (ly, t, s, c, lab) in left:
    node(wx + 20, ly, 230, 46, t, s, c)
    if t == "Encoder band A":                # single-ended → RoboClaw EN1 (closed-loop)
        line(wx + 135, ly, wx + 135, ly - 30, c, 1.8)          # upp till RoboClaw-noden
        txt(wx + 142, ly - 12, "single-ended → RoboClaw EN1", 7.5, "start", c, 700)
    elif "band B" in t:                      # RS-422 diff → kamera IN1±/IN2± (native) + 26C32 → RoboClaw EN2
        line(wx + 250, ly + 12, wx + 286, ly + 12, c, 1.8, "4 3")
        txt(wx + 290, ly + 9, "→ kamera IN1± (pin3/4) · IN2± (pin5/6) · 5V diff", 7.5, "start", c, 700)
        line(wx + 250, ly + 33, wx + 286, ly + 33, MUTED, 1.6)
        txt(wx + 290, ly + 30, "diff→single-modul (26C32-typ, 5V-DC-DC matar enc) → EN2", 7.5, "start", MUTED, 700)
    else:
        conn((wx + 250, ly + 23), (Lc[0], Lc[1] + (ly + 23 - JY - JH / 2) * 0.25), lab, c)
# höger: grön + punktlaser + yta + ljus
right = [
    (wy + 70, "Profilkamera GRÖN", "MV-CS050-10UM", F2, "USB3 (egen)"),
    (wy + 150, "Linjelaser GRÖN 520", "MZLaser, CW", F2, "24 V + GPIO-en"),
    (wy + 230, "3× Punktlaser LR400", "RS-485 Modbus", F2, "Waveshare 4CH ch1–3"),
    (wy + 310, "Ytkamera 4K FÄRG", "Huateng line-scan", F2, "GbE (RJ45)"),
    (wy + 390, "2× Vitt LED-linjeljus", "konstantström", F2, "24 V + GPIO"),
]
for (ly, t, s, c, lab) in right:
    node(JX + JW + 130, ly, 268, 52, t, s, c)
    conn((JX + JW + 130, ly + 26), (Rc[0], Rc[1] + (ly + 26 - JY - JH / 2) * 0.25), lab, c)
# Waveshare 4CH-nav (ch4 ledig) — antydan vid punktlaser-noden
txt(JX + JW + 130 + 134, wy + 230 + 64, "ch4 LEDIG (Modbus-reserv)", 8, "middle", MUTED, 700)
# PSU
rect(JX - 30, JY + JH + 36, 310, 40, "#fff5e6", "#c89028", 1.4, 6)
txt(JX + 125, JY + JH + 54, "NÄTAGGREGAT — 24 V (band/laser/LED) · 5 V logik · Jetson egen DC", 9, "middle", "#8a6510", 700)
arrow(JX + 125, JY + JH + 36, JX + JW / 2, JY + JH, "#c89028", 1.6)

# ===================== JETSON I/O-BUDGET (botten) =====================
ty = 760
rect(48, ty, W - 96, 360, "#fff", INK, 1.2, 8)
rect(48, ty, W - 96, 30, INK, INK, 0, 8); txt(60, ty + 20, "JETSON ORIN NANO — I/O-BUDGET (räcker till allt, med marginal)", 13, "start", "#fff", 700, SANS)
cols = [(70, "GRÄNSSNITT", 360), (430, "TILLGÄNGLIGT", 230), (660, "ANVÄNDS", 540), (1200, "STATUS", 452)]
for (cx, head, cw) in cols:
    txt(cx, ty + 52, head, 10.5, "start", MUTED, 700, MONO)
line(60, ty + 60, W - 60, ty + 60, DIMC, 1)
rows = [
    ("USB 3.2 Gen2 (Type-A)", "4 st", "4 — RÖD+GRÖN kam + RS-485 4CH + RoboClaw 2x7A", "OK · ingen hubb", F1),
    ("USB → RS-485 4CH", "Waveshare 4CH", "3× LR400 Modbus (ch1–3) · ch4 LEDIG", "OK · reserv kvar", F2),
    ("Gigabit Ethernet (RJ45)", "1 st", "1 — ytkamera FÄRG (Huateng line-scan)", "OK", F2),
    ("Motor + position", "RoboClaw 2x7A", "A:CWZ6C→EN1 · B:CWZ1X→26C32→EN2 → synk", "position via USB", F1),
    ("Encoder → kamera (ref)", "band B RS-422", "CWZ1X → kamera Line0 (diff, terminerad, native)", "pixel-exakt scan", F1),
    ("40-pin GPIO (3,3 V)", "~28", "~5 — fotocell, 2× laser-en, 2× LED-en", "OK · gott om kvar", F1),
    ("Analog in (ADC)", "0 — saknas", "0 — behövs ej (allt digitalt)", "ingen ADC krävs", F1),
    ("DC-in (barrel)", "1", "Jetson 7–25 V; separat 24 V (band/laser/LED) + 5 V logik", "OK", INK),
]
rh = 34
for i, (a, b, c, d, col) in enumerate(rows):
    ry = ty + 70 + i * rh
    if i % 2: rect(60, ry, W - 120, rh, PANEL, "none", 0)
    rect(64, ry + 9, 12, 12, col, col, 0, 2)
    txt(86, ry + 22, a, 10.5, "start", INK, 700, SANS)
    txt(430, ry + 22, b, 10, "start", MUTED, 400)
    txt(660, ry + 22, c, 10, "start", INK, 400, SANS)
    txt(1200, ry + 22, d, 10.5, "start", col if col not in (DIMC, INK) else MUTED, 700, SANS)

tb_x, tb_y = W - 470, H - 86
rect(tb_x, tb_y, 422, 56, "#fff", INK, 1.4)
line(tb_x, tb_y + 28, tb_x + 422, tb_y + 28, INK, 1); line(tb_x + 262, tb_y, tb_x + 262, tb_y + 56, INK, 1)
txt(tb_x + 10, tb_y + 18, "VIRKESSKANNER — KOPPLING + I/O", 11.5, "start", INK, 700, SANS)
txt(tb_x + 272, tb_y + 18, "PROTO-WIRE", 11, "start", INK)
txt(tb_x + 10, tb_y + 46, "Fas 1 körbar · Fas 2 tillägg", 9.5, "start", MUTED)
txt(tb_x + 272, tb_y + 46, "Jetson-I/O verifierad", 9.5, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-wiring.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
