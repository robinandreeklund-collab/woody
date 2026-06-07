#!/usr/bin/env python3
"""Jetson Orin Nano — komplett 40-pin header med prototyp-tilldelning (SVG).
Verifierad pinout (JetsonHacks/NVIDIA). Färgkodad per funktion/fas + sammanfattning
och kopplingsnoter. Aktuellt schema: LR400 på RS-485 (Waveshare 4CH USB), matning via
RoboClaw 2x7A (USB) som driver båda banden + läser 2 rull-encodrar (synk) och rapporterar
position till Jetson; referensbandets encoder → kamerans line-trigg; anhåll+fotocell = nolla
(GPIO), linjelaser/vitljus-enable via MOSFET. Headern används glest — det mesta går via USB.

    python tools/draw_pinout.py   # -> prototype-pinout.svg i projektroten
"""
from __future__ import annotations
import os

W, H = 1680, 1180
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
P33, P5, GND, BUS, F1, F2 = "#e0892b", "#d23b3b", "#3b4046", "#9a9ea4", "#2f9e6e", "#7a3fb0"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=12, anchor="start", fill=INK, weight=400, fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def line(x1, y1, x2, y2, stroke=INK, w=1):
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"/>')

# pin: (default-namn, prototyp-användning, färg)
PINS = {
 1:("3.3V","logik 3.3V",P33),                   2:("5V","ext. 5V (logik)",P5),
 3:("I2C1_SDA","reserv I²C",BUS),               4:("5V","",P5),
 5:("I2C1_SCL","reserv I²C",BUS),               6:("GND","gemensam GND",GND),
 7:("GPIO09","ANHÅLL-FOTOCELL in  (F1)",F1),    8:("UART1_TX","reserv/debug",BUS),
 9:("GND","",GND),                              10:("UART1_RX","reserv/debug",BUS),
 11:("UART1_RTS","reserv",BUS),                 12:("I2S0_SCLK","reserv",DIMC),
 13:("SPI1_SCK","VITT LED A enable  (F2)",F2),  14:("GND","",GND),
 15:("GPIO12·PWM","VITT LED B enable  (F2)",F2),16:("SPI1_CS1","LINJELASER RÖD en  (F1)",F1),
 17:("3.3V","logik 3.3V",P33),                  18:("SPI1_CS0","LINJELASER GRÖN en  (F2)",F2),
 19:("SPI0_MOSI","reserv",DIMC),                20:("GND","",GND),
 21:("SPI0_MISO","reserv",DIMC),                22:("SPI1_MISO","reserv",DIMC),
 23:("SPI0_SCK","reserv",DIMC),                 24:("SPI0_CS0","reserv",DIMC),
 25:("GND","",GND),                             26:("SPI0_CS1","reserv",DIMC),
 27:("I2C0_SDA","reserv I²C",BUS),              28:("I2C0_SCL","reserv I²C",BUS),
 29:("GPIO01","reserv",DIMC),                   30:("GND","",GND),
 31:("GPIO11","reserv",DIMC),                   32:("GPIO07·PWM","reserv",DIMC),
 33:("GPIO13·PWM","reserv",DIMC),               34:("GND","",GND),
 35:("I2S0_FS","KAM-TRIG reserv (HW-enc)",DIMC),36:("UART1_CTS","reserv",DIMC),
 37:("SPI1_MOSI","reserv GPIO",DIMC),           38:("I2S0_SDIN","reserv",DIMC),
 39:("GND","",GND),                             40:("I2S0_SDOUT","reserv",DIMC),
}

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(18, 18, W - 36, H - 36, "none", INK, 2); rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)
txt(48, 64, "JETSON ORIN NANO — 40-PIN HEADER (J12), prototyp-tilldelning", 22, "start", INK, 700, SANS)
txt(48, 90, "Verifierad pinout (JetsonHacks/NVIDIA). Färg = funktion/fas. Pin 1 = övre vänster (fyrkant). RoboClaw 2x7A + LR400 via USB; band-encodrar → RoboClaw.", 13, "start", MUTED, 400)
line(48, 104, W - 48, 104, INK, 1.5)
# färglegend
leg = [("3.3V", P33), ("5V", P5), ("GND", GND), ("Buss/reserv", BUS), ("Fas 1", F1), ("Fas 2", F2)]
lx = 720
for lab, c in leg:
    rect(lx, 46, 13, 13, c, c, 0, 3); txt(lx + 18, 57, lab, 11, "start", c if c not in (BUS, DIMC) else MUTED, 700, SANS)
    lx += len(lab) * 8 + 50

# ---- header-graf: 2 kolumner (udda vänster, jämn höger) ----
cy0 = 170; rh = 44; padR = 11
colL, colR = 690, 760            # pad-kolumner (udda / jämn)
rect(colL - 26, cy0 - 22, (colR - colL) + 52, 20 * rh + 14, "#eceae2", "#cfccc1", 1.4, 8)  # PCB
txt((colL + colR) / 2, cy0 - 28, "J12", 11, "middle", MUTED, 700, MONO)
def pad(cx, cy, n, name, use, col, left):
    sq = (n == 1)
    if sq: rect(cx - padR, cy - padR, 2 * padR, 2 * padR, col, INK, 1.2, 2)
    else:  add(f'<circle cx="{cx}" cy="{cy}" r="{padR}" fill="{col}" stroke="{INK}" stroke-width="1.1"/>')
    txt(cx, cy + 4, str(n), 10, "middle", "#fff" if col != BUS else INK, 700, MONO)
    tx = cx - padR - 12 if left else cx + padR + 12
    an = "end" if left else "start"
    txt(tx, cy - 2, name, 10.5, an, INK, 700, MONO)
    if use:
        txt(tx, cy + 12, use, 10, an, col if col not in (BUS, DIMC, GND) else MUTED, 700 if col in (F1, F2) else 400, SANS)
for i in range(20):
    cy = cy0 + i * rh
    nl, nr = 2 * i + 1, 2 * i + 2
    dl, ul, cl = PINS[nl]; dr, ur, cr = PINS[nr]
    pad(colL, cy, nl, dl, ul, cl, True)
    pad(colR, cy, nr, dr, ur, cr, False)

# ---- sammanfattning (höger) ----
sx = 1130
def block(y, title, acc, rows):
    rect(sx, y, 500, 30 + len(rows) * 26 + 6, "#fff", acc, 1.4, 8)
    rect(sx, y, 500, 26, acc, acc, 0, 8); txt(sx + 10, y + 18, title, 12, "start", "#fff", 700, SANS)
    for j, (a, b) in enumerate(rows):
        ry = y + 32 + j * 26
        if j % 2: rect(sx, ry - 4, 500, 26, PANEL, "none", 0)
        txt(sx + 12, ry + 13, a, 11, "start", INK, 700 if a[0].isalpha() else 400, SANS)
        txt(sx + 488, ry + 13, b, 11, "end", acc, 700, MONO)
    return y + 30 + len(rows) * 26 + 22

y = 130
y = block(y, "FAS 1 — matning + position + röd", F1, [
    ("Anhåll-fotocell (nolla/home) in", "pin 7"),
    ("Linjelaser RÖD enable (→ MOSFET)", "pin 16"),
    ("RoboClaw 2x7A (2 motorer+2 enc) → USB", "USB"),
    ("Band-encodrar → RoboClaw (ej header)", "kvadr."),
    ("Profilkamera RÖD → USB3", "USB3"),
])
y = block(y, "FAS 2 — grön + punktlaser + yta + ljus", F2, [
    ("Linjelaser GRÖN enable (→ MOSFET)", "pin 18"),
    ("2× Vitt LED-linjeljus enable", "pin 13 · 15"),
    ("3× LR400 → RS-485 (Waveshare 4CH)", "USB ch1–3"),
    ("Ytkamera FÄRG (Huateng) → GbE", "RJ45"),
    ("Profilkamera GRÖN → USB3", "USB3"),
])
y = block(y, "STRÖM / GND", P33, [
    ("3.3V (logik)", "pin 1 · 17"),
    ("5V (header)", "pin 2 · 4"),
    ("GND (gemensam)", "6·9·14·20·25·30·34·39"),
])
# noter
rect(sx, y, 500, 240, "#fff", INK, 1.2, 8)
rect(sx, y, 500, 26, INK, INK, 0, 8); txt(sx + 10, y + 18, "KOPPLINGSNOTER", 12, "start", "#fff", 700, SANS)
notes = [
    "RoboClaw 2x7A (USB) DRIVER BÅDA bandmotorerna +",
    "  läser 2 kvadratur-encodrar (1/band) → closed-loop-",
    "  synk; rapporterar position/fart till Jetson via USB.",
    "  → Jetson behöver INTE räkna encoder på GPIO.",
    "Referensbandets A/B tappas till KAMERANS line-trigg",
    "  (single-ended; AM26LS31→RS-422 om kameran kräver).",
    "Encoder single-ended 5 V (E6B2-CWZ6C) → RoboClaw-in.",
    "LR400 = RS-485 (Waveshare USB 4CH, ch1–3, ch4 ledig).",
    "Anhåll+fotocell = nolla (pin 7); lasrar/LED via MOSFET.",
    "Gemensam GND: Jetson + 24 V-PSU + logik.",
]
for k, n in enumerate(notes):
    txt(sx + 12, y + 46 + k * 21, n, 10.3, "start", INK if not n.startswith("  ") else MUTED, 400, SANS)

tb_x, tb_y = W - 470, H - 80
rect(tb_x, tb_y, 422, 52, "#fff", INK, 1.4)
line(tb_x, tb_y + 26, tb_x + 422, tb_y + 26, INK, 1); line(tb_x + 262, tb_y, tb_x + 262, tb_y + 52, INK, 1)
txt(tb_x + 10, tb_y + 17, "VIRKESSKANNER — 40-PIN PINOUT", 11.5, "start", INK, 700, SANS)
txt(tb_x + 272, tb_y + 17, "PROTO-PIN", 11, "start", INK)
txt(tb_x + 10, tb_y + 43, "Verifierad J12-pinout", 9.5, "start", MUTED)
txt(tb_x + 272, tb_y + 43, "3,3 V logik", 9.5, "start", MUTED)
add('</svg>')
dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype-pinout.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
