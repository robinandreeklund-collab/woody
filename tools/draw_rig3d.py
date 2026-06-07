#!/usr/bin/env python3
"""KOMPLETT prototyp-ark (SVG) — allt i ett dokument: 3D-rigg (L-portal, cross-feed),
sensor-legend + mått + styrning, komplett kopplingsschema, Jetson I/O-budget,
40-pin pinout och fasad BOM med priser. Datadriven ur src.hardware + proto_sim.BOM.

    python tools/draw_rig3d.py   # -> prototype-rig-3d.svg i projektroten
"""
from __future__ import annotations
import os, sys, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "prototype"))
from src.hardware import Rig
from proto_sim import BOM, bom_total

BENCH_L, BW = 500, 75
CY = BW / 2
r = Rig(board_length_mm=BENCH_L, board_width_mm=BW, board_thickness_mm=45)
OBL = r.oblique_angle_deg
WD = round(BENCH_L * r.profile_lens_mm / r.profile_cam.sensor_w_mm)
SOFF = round(WD * math.sin(math.radians(OBL))); MH = round(WD * math.cos(math.radians(OBL)))
SEP = 2 * SOFF
RED_NM, GRN_NM = round(r.laser.wavelength_nm), round(r.laser_green.wavelength_nm)
PL_X = [int(f * BENCH_L) for f in (0.1, 0.5, 0.9)]; PLWD = 100; PL_Y = -24
SURF_WD = 400           # ytkamera: ZLKC 20 mm M42 @ ~0,05× → FOV ~570 @ WD 400 (egen balk)

W, H = 2480, 2060
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
RED, GRN, BLUE, PURP, ALU, JET = "#e8542c", "#2f9e6e", "#2f6fb0", "#a23ad6", "#c3c6ca", "#3b7d3b"
BELT, SURFC, WOOD, GOLD = "#444a52", "#7a3fb0", "#e9e1cf", "#b9a96f"
F1, F2 = "#2f9e6e", "#7a3fb0"
P33, P5, GNDc, BUSc = "#e0892b", "#d23b3b", "#3b4046", "#9a9ea4"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"; MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
out = []
def add(s): out.append(s)
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def txt(x, y, s, size=12, anchor="start", fill=INK, weight=400, fam=SANS):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')
def ln(p1, p2, stroke=INK, w=1.2, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{stroke}" stroke-width="{w}"{d} opacity="{op}"/>')
def L(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, op=1): ln((x1, y1), (x2, y2), stroke, w, dash, op)
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, op=1):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def poly(pts, fill, stroke=INK, sw=1.1, op=1):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')
def dot(p, rr, fill, stroke=INK, sw=0):
    add(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(p1, p2, stroke=INK, w=2.0):
    ln(p1, p2, stroke, w); a = math.atan2(p2[1] - p1[1], p2[0] - p1[0]); l = 10
    for s in (0.5, -0.5): ln(p2, (p2[0] - l * math.cos(a - s), p2[1] - l * math.sin(a - s)), stroke, w)
def panel(x, y, w, h, title, acc):
    rect(x, y, w, h, "#fff", acc, 1.4, 8); rect(x, y, w, 28, acc, acc, 0, 8)
    txt(x + 12, y + 19, title, 12.5, "start", "#fff", 700, SANS)

# iso-projektion
S, OX, OY = 0.46, 560, 480
CA, SA = math.cos(math.radians(30)), math.sin(math.radians(30))
def P(x, y, z): return (OX + (x - y) * CA * S, OY + (x + y) * SA * S - z * S)
def box(x0, x1, y0, y1, z0, z1, top, sideL, sideR, stroke=INK, sw=1):
    poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], top, stroke, sw)
    poly([P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0)], sideL, stroke, sw)
    poly([P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0), P(x1, y0, z0)], sideR, stroke, sw)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add('<g opacity="0.5">')
for gx in range(0, W, 40): L(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): L(0, gy, W, gy, GRID, 0.5)
add('</g>')
rect(16, 16, W - 32, H - 32, "none", INK, 2); rect(24, 24, W - 48, H - 48, "none", MUTED, 0.8)
txt(44, 62, "VIRKESSKANNER — KOMPLETT PROTOTYP-ARK (rigg · koppling · I/O · pinout · BOM)", 24, "start", INK, 700, SANS)
txt(44, 88, "L-portal cross-feed, 500×75 mm-bräda, oblik 30°. FAS 1 (solid) = körbar röd-profilerare. FAS 2 (tonad) = grön modul + punktlaser + line-scan-yta.",
    13, "start", MUTED, 400, SANS)
L(44, 100, W - 44, 100, INK, 1.5)

# ============================================================ 1) 3D-RIGG
panel(40, 116, 1150, 700, "1 · 3D-RIGG (L-portal, cross-feed)", INK)
BX0, BX1 = 0, BENCH_L; BY0, BY1 = 0, BW; BZ = 45
MYL, MYR = CY - SOFF, CY + SOFF; TOPZ = MH + 40
FY0, FY1 = -90, 200; LEGX0, LEGX1 = -80, BENCH_L + 80
box(LEGX0 - 30, LEGX1 + 30, FY0 - 30, FY1 + 30, -16, 0, "#e7e4da", "#cdc9bd", "#d6d2c6", "#b6b2a6", 1)
for bx0, bx1, lab in [(0, 85, "BAND V"), (BENCH_L - 85, BENCH_L, "BAND H")]:
    box(bx0, bx1, FY0 - 8, FY1 + 8, 0, 10, BELT, "#33373d", "#3b4046", "#2b2f35", 1)
    txt(*P((bx0 + bx1) / 2, FY1 + 8, 11), lab, 9, "middle", "#dfe3e8", 700)
box(BX0 - 6, BX1 + 6, FY0 - 4, FY0 + 8, 0, 52, "#9aa0a8", "#7f858c", "#888e95", "#6e747b", 1)
txt(*P(BX0 - 6, FY0 - 6, 64), "ANSLAG (laddläge)", 9, "end", MUTED, 700)
box(BX0 - 13, BX0 - 3, FY0 - 8, FY1 + 8, 0, 42, "#8aa0b0", "#5f7585", "#6e8494", "#566c7c", 1)
txt(*P(BX0 - 12, FY1, 42), "SIDOANSLAG", 9, "end", BLUE, 700)
box(BX0, BX1, BY0, BY1, 0, BZ, WOOD, "#d9cfb0", "#cdbf99", "#9a8c63", 1.2)
txt(*P(250, BY1 + 6, BZ + 4), "bräda 500 × 75 × 45 mm", 10, "middle", "#8a7d4e", 700)
arrow(P(250, FY0 + 24, 17), P(250, FY1 - 16, 17), "#b06", 2.4); arrow(P(310, FY1 - 16, 17), P(310, FY0 + 24, 17), BLUE, 1.8)
txt(*P(250, FY1 + 30, 17), "Jetson: ladda→fram→mät→BACK→upprepa", 10, "middle", "#b06", 700)
# FOTOCELL vid anslaget = nolla/home (bräda läggs an → encodern nollas)
fp = P(BX0 - 10, FY0 - 4, 60)
poly([(fp[0]-2,fp[1]-12),(fp[0]+22,fp[1]-12),(fp[0]+22,fp[1]+9),(fp[0]-2,fp[1]+9)], "#16212e", "#c98a16", 1.4)
txt(fp[0]+10, fp[1]+2, "PC", 8, "middle", "#c98a16", 700); txt(fp[0]+28, fp[1]-2, "fotocell (nolla)", 8.5, "start", "#c98a16", 700)
# RULL-ENCODRAR mot bandens retursida (en per band) → RoboClaw (synk) + ref → kamera
ep = P(BENCH_L - 40, FY0 - 18, 14)
dot(ep, 9, "#bfe6c8", GRN, 1.4); dot(ep, 2.5, GRN)
txt(ep[0]+14, ep[1]+2, "encoder A→RoboClaw EN1 · B (RS-422)→kamera Line0 + 26C32→EN2", 8.5, "start", GRN, 700)
for lx in (LEGX0, LEGX1):
    box(lx - 18, lx + 18, CY - 18, CY + 18, -16, 6, "#bfc3c8", "#a7acb1", "#b0b5ba", "#969ba0", 1)
    box(lx - 14, lx + 14, CY - 14, CY + 14, 0, TOPZ, ALU, "#aeb3b8", "#b8bdc2", "#9aa0a6", 1)
box(LEGX0 - 12, LEGX1 + 12, CY - 12, CY + 12, TOPZ - 22, TOPZ, ALU, "#aeb3b8", "#b8bdc2", "#9aa0a6", 1)
txt(*P(LEGX1 + 24, CY, TOPZ + 6), "HUVUDBALK", 9, "start", MUTED, 700)
box(243, 257, MYL - 12, MYR + 12, TOPZ - 42, TOPZ - 20, ALU, "#a6abb0", "#b0b5ba", "#92979c", 1)
txt(*P(250, MYL - 24, TOPZ - 30), "TVÄRBALK (modulfäste)", 9, "middle", MUTED, 700)
for my, col, lab, fas in [(MYL, RED, f"RÖD {RED_NM}", 1), (MYR, GRN, f"GRÖN {GRN_NM}", 1)]:
    if fas == 2: add('<g opacity="0.5">')
    ln(P(250, my, TOPZ - 31), P(250, my, MH), "#8a9099", 2.4); mp = P(250, my, MH)
    for ex in (BX0, BX1): ln(mp, P(ex, CY, BZ), col, 1.8, op=0.85)
    ln(P(BX0, CY, BZ + 0.4), P(BX1, CY, BZ + 0.4), col, 3)
    poly([(mp[0]-32,mp[1]-26),(mp[0]+32,mp[1]-26),(mp[0]+32,mp[1]+7),(mp[0]-32,mp[1]+7)], "#fff", col, 1.6)
    poly([(mp[0]-32,mp[1]-26),(mp[0]+32,mp[1]-26),(mp[0]+32,mp[1]-15),(mp[0]-32,mp[1]-15)], col, col, 0)
    txt(mp[0], mp[1]-18, lab, 8.5, "middle", "#fff", 700, SANS); txt(mp[0], mp[1]-3, f"FAS {fas}", 7, "middle", INK)
    if fas == 2: add('</g>')
add('<g opacity="0.5">')
# punktlaser LR400 — EGEN låg balk UPPSTRÖMS (PL_Y före brädan), ~100 mm
ln(P(PL_X[0], PL_Y, PLWD), P(PL_X[2], PL_Y, PLWD), "#8a9099", 2.0)        # låg punktlaser-balk
for px in PL_X:
    ln(P(px, PL_Y, PLWD + 70), P(px, PL_Y, PLWD), "#8a9099", 1.6); pt = P(px, PL_Y, PLWD)
    poly([(pt[0]-10,pt[1]-8),(pt[0]+10,pt[1]-8),(pt[0]+10,pt[1]+8),(pt[0]-10,pt[1]+8)], "#f3e6fb", PURP, 1.3)
    txt(pt[0], pt[1]+3, "PL", 7.5, "middle", PURP, 700); ln(pt, P(px, PL_Y, BZ), PURP, 1.4, "3 3"); dot(P(px, PL_Y, BZ), 2.4, PURP)
txt(*P(PL_X[1], PL_Y, PLWD + 95), "PUNKTLASER LR400 — uppströms ~100 mm", 8, "middle", PURP, 700)
cp = P(250, CY, SURF_WD); ln(P(250, CY, TOPZ), cp, "#8a9099", 2.6)
poly([(cp[0]-48,cp[1]-14),(cp[0]+48,cp[1]-14),(cp[0]+48,cp[1]+11),(cp[0]-48,cp[1]+11)], "#efe6f7", SURFC, 1.5)
txt(cp[0], cp[1]-1, "YTKAMERA line-scan", 8, "middle", SURFC, 700, SANS); txt(cp[0], cp[1]+9, "4K färg · 20 mm M42 + vitt ljus", 7, "middle", INK)
for ex in (BX0, BX1): ln(cp, P(ex, CY, BZ), SURFC, 0.8, "3 3")
add('</g>')
jp = P(BENCH_L + 150, FY1 - 30, 0)
rect(jp[0], jp[1] - 26, 150, 50, "#e6efe6", JET, 1.6, 6)
txt(jp[0] + 75, jp[1] - 6, "JETSON Orin Nano", 10, "middle", JET, 700, SANS); txt(jp[0] + 75, jp[1] + 10, "edge-compute + U-Net", 8, "middle", MUTED)

# ---- legend + mått + styrning (rad 1 höger) ----
panel(1210, 116, 410, 372, "SENSORER / FAS", INK)
leg = [(RED, "Linjelaser+kamera RÖD 650", 1), (GRN, "Linjelaser+kamera GRÖN 520", 1),
       (PURP, "3× punktlaser LR400 (RS-485)", 2), (SURFC, "Ytkamera 4K färg + vitt ljus", 2),
       (BELT, "2 transportband + RoboClaw 2x7A (USB)", 1), (ALU, "Stativ · anhåll+fotocell · enc A→EN1 · B(RS-422)→kamera", 1)]
for i, (c, k, fas) in enumerate(leg):
    ry = 160 + i * 40; rect(1224, ry, 20, 20, c, INK, 0.8, 4)
    txt(1252, ry + 14, k, 11, "start", INK, 700, SANS)
    fc = F1 if fas == 1 else F2; rect(1530, ry + 2, 78, 16, fc, fc, 0, 8); txt(1569, ry + 14, f"FAS {fas}", 9, "middle", "#fff", 700, SANS)
rect(1224, 408, 384, 70, PANEL, DIMC, 0.8, 5)
txt(1234, 426, "FAS 1 (solid) = full 3D-mätrigg:", 10, "start", F1, 700)
txt(1234, 442, "röd + grön modul + rullband + Jetson → 3D-profil.", 9.5, "start", INK, 400)
txt(1234, 462, "FAS 2 (tonad) = punktlaser + line-scan-yta.", 10, "start", F2, 700)

panel(1640, 116, 410, 372, "MÅTT (mm)", INK)
dims = [("Arbetsavstånd (oblik)", f"~{WD}"), ("Oblik vinkel", f"{OBL:.0f}°"), ("Modulhöjd", f"~{MH}"),
        ("Sidooffset", f"~{SOFF}"), ("Avstånd modul↔modul", f"~{SEP}"), ("Laserlinje (längs)", f"{BENCH_L}"),
        ("Brädbredd (matning)", f"{BW}"), ("Punktlaser V/C/H", f"{PL_X[0]}/{PL_X[1]}/{PL_X[2]}"),
        ("Punktlaser standoff (uppströms)", f"~{PLWD}"), ("Ytkamera-WD (20 mm M42)", f"{SURF_WD}")]
for i, (k, v) in enumerate(dims):
    ry = 152 + i * 30
    if i % 2: rect(1640, ry - 4, 410, 30, PANEL, "none", 0)
    txt(1652, ry + 14, k, 10.5, "start", MUTED, 700); txt(2038, ry + 14, v, 11, "end", INK, 700, MONO)

panel(2070, 116, 370, 372, "STYRNING (Jetson)", JET)
for i, n in enumerate(["Fast anhåll + fotocell = mekanisk NOLLA/home", "(bräda läggs an → encoder-nollan sätts).",
                       "RoboClaw 2x7A driver BÅDA banden + 2 enc:", "closed-loop hastighet → banden i SYNK.",
                       "Position/fart → Jetson via RoboClaw-USB →", "fram → mät → BACK; band B (RS-422) → kamera Line0.",
                       "Ytkamera GigE → Jetson 1GbE direkt (ingen switch).", "Punktlaser LR400 → RS-485 (digitalt, ingen ADC)."]):
    txt(2082, 158 + i * 28, "• " + n if not n.startswith("(") and not n.startswith("+") and not n.startswith("(rull") else "  " + n,
        9.6, "start", INK if not (n.startswith("(") or n.startswith("+")) else MUTED, 400)

# ============================================================ 2) KOPPLINGSSCHEMA + I/O
panel(40, 832, 1480, 540, "2 · KOMPLETT KOPPLINGSSCHEMA", INK)
JX, JY, JW, JH = 700, 1050, 240, 120
rect(JX, JY, JW, JH, "#e6efe6", JET, 2, 8); rect(JX, JY, JW, 24, JET, JET, 0, 8)
txt(JX + JW/2, JY + 17, "JETSON ORIN NANO SUPER", 11, "middle", "#fff", 700, SANS)
txt(JX + JW/2, JY + 44, "4× USB3 · 1× GbE (RJ45)", 9.5, "middle", INK)
txt(JX + JW/2, JY + 62, "40-pin: GPIO · I²C×2 · SPI×2", 9.5, "middle", INK)
txt(JX + JW/2, JY + 80, "Ingen analog/ADC behövs", 9.5, "middle", JET, 700)
txt(JX + JW/2, JY + 100, "LR400 → RS-485 (USB 4CH, ch4 ledig)", 9, "middle", MUTED)
def node(x, y, w, t, s, acc):
    rect(x, y, w, 50, "#fff", acc, 1.5, 7); rect(x, y, w, 20, acc, acc, 0, 7)
    txt(x + 9, y + 15, t, 10, "start", "#fff", 700, SANS); txt(x + 9, y + 36, s, 8.5, "start", INK)
def conn(p1, p2, lab, c):
    arrow(p1, p2, c, 1.7); mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
    rect(mx - len(lab)*3.2 - 4, my - 8, len(lab)*6.4 + 8, 15, "#fff", c, 0.8, 3); txt(mx, my + 3, lab, 8, "middle", c, 700)
left = [(880, "Profilkamera RÖD", "MV-CS050-10UM", F1, "USB3"), (960, "Linjelaser röd+grön", "röd 5V·TTL / grön 12-24V", F1, "GPIO-en"),
        (1040, "RoboClaw 2x7A", "2 bandmotorer, synk", F1, "USB (1 kort)"), (1120, "Encoder A/B (band)", "A:CWZ6C · B:CWZ1X", F1, "→ RoboClaw"),
        (1200, "Anhåll-fotocell", "nolla / home", F1, "GPIO")]
for (ly, t, s, c, lab) in left:
    node(70, ly, 240, t, s, c)
    if lab == "→ RoboClaw":              # A single-ended→EN1; B RS-422→kamera Line0 + 26C32→EN2
        L(190, ly, 190, ly - 30, c, 1.7)                 # upp till RoboClaw-noden
        txt(196, ly - 14, "A single-end→EN1", 8, "start", c, 700, SANS)
        L(310, ly + 28, 360, ly + 28, c, 1.7, "4 3")
        txt(366, ly + 26, "B RS-422 → kamera IN1±/IN2± (pin3-6, 5V diff) + diff→single-modul→EN2", 8, "start", c, 700, SANS)
    else:
        conn((310, ly + 25), (JX, JY + JH/2 + (ly - JY - JH/2) * 0.2), lab, c)
SCY = 980
right = [(880, "Profilkamera GRÖN", "MV-CS050-10UM (Fas 1)", F1, "USB3"), (SCY, "Ytkamera line-scan", "Huateng 4K färg (Fas 2)", F2, "GigE"),
         (1080, "3× Punktlaser LR400", "Waveshare 4CH ch1–3 (ch4 ledig)", F2, "RS-485"), (1180, "2× Vitt LED-linjeljus", "konstantström (Fas 2)", F2, "24V+GPIO")]
for (ly, t, s, c, lab) in right:
    node(JX + JW + 120, ly, 250, t, s, c)
    conn((JX + JW + 120, ly + 25), (JX + JW, JY + JH/2 + (ly - JY - JH/2) * 0.2), lab, c)
rect(JX - 20, JY + JH + 26, 280, 34, "#fff5e6", "#c89028", 1.3, 6)
txt(JX + 120, JY + JH + 48, "PSU 24 V (band/laser/LED) · 5 V logik · DC-in (Jetson)", 9, "middle", "#8a6510", 700)

# I/O-budget
panel(1540, 832, 900, 540, "JETSON I/O-BUDGET (räcker med marginal)", INK)
io = [("USB-portar (×4)", "4 — RÖD+GRÖN kam + RS-485 4CH + RoboClaw 2x7A", "OK · ingen hubb", F1),
      ("Gigabit Ethernet", "1 — ytkamera (GigE 1GbE direkt)", "OK", F2),
      ("RS-485 (USB 4CH)", "3× LR400 (ch1–3) · ch4 LEDIG", "OK · reserv", F2),
      ("RoboClaw 2x7A (USB)", "A:CWZ6C→EN1 · B:CWZ1X→26C32→EN2 → synk + position", "via USB", F1),
      ("Encoder band B → kamera", "CWZ1X RS-422 @5V → kamera IN1± (pin3/4) + IN2± (pin5/6) diff", "native, pixel-exakt", F1),
      ("40-pin GPIO (~28)", "~5 — anhåll-fotocell, 2 laser-en, 2 LED-en", "OK · gott om", F1),
      ("Analog in (ADC)", "0 — behövs EJ (allt digitalt)", "✓ digitalt", JET),
      ("DC-in / 24 V / 5 V", "Jetson 7–25 V + separat 24/5 V", "OK", INK)]
txt(1556, 884, "GRÄNSSNITT", 10.5, "start", MUTED, 700, MONO); txt(1820, 884, "ANVÄNDS", 10.5, "start", MUTED, 700, MONO); txt(2300, 884, "STATUS", 10.5, "start", MUTED, 700, MONO)
L(1556, 892, 2424, 892, DIMC, 1)
for i, (a, b, c, col) in enumerate(io):
    ry = 900 + i * 36
    if i % 2: rect(1548, ry, 884, 36, PANEL, "none", 0)
    rect(1556, ry + 11, 12, 12, col, col, 0, 2); txt(1576, ry + 23, a, 10.5, "start", INK, 700, SANS)
    txt(1820, ry + 23, b, 10, "start", INK, 400); txt(2300, ry + 23, c, 10.5, "start", col if col not in (DIMC, INK) else MUTED, 700)

# ============================================================ 3) PINOUT + BOM
panel(40, 1388, 1000, 640, "3 · JETSON 40-PIN (J12) — prototyp-tilldelning", INK)
PINS = {1:("3.3V","logik",P33),2:("5V","ext logik",P5),3:("I2C1_SDA","reserv",BUSc),4:("5V","",P5),
 5:("I2C1_SCL","reserv",BUSc),6:("GND","",GNDc),7:("GPIO09","ANHÅLL-FOTOCELL",F1),8:("UART1_TX","reserv",BUSc),
 9:("GND","",GNDc),10:("UART1_RX","reserv",BUSc),11:("UART1_RTS","reserv",BUSc),12:("I2S0_SCLK","reserv",DIMC),
 13:("SPI1_SCK","VITT LED A en",F2),14:("GND","",GNDc),15:("GPIO12·PWM","VITT LED B en",F2),16:("SPI1_CS1","LASER RÖD en",F1),
 17:("3.3V","logik",P33),18:("SPI1_CS0","LASER GRÖN en",F2),19:("SPI0_MOSI","reserv",DIMC),20:("GND","",GNDc),
 21:("SPI0_MISO","reserv",DIMC),22:("SPI1_MISO","reserv",DIMC),23:("SPI0_SCK","reserv",DIMC),24:("SPI0_CS0","reserv",DIMC),
 25:("GND","",GNDc),26:("SPI0_CS1","reserv",DIMC),27:("I2C0_SDA","reserv",BUSc),28:("I2C0_SCL","reserv",BUSc),
 29:("GPIO01","reserv",DIMC),30:("GND","",GNDc),31:("GPIO11","reserv",DIMC),32:("GPIO07·PWM","reserv",DIMC),
 33:("GPIO13·PWM","reserv",DIMC),34:("GND","",GNDc),35:("I2S0_FS","KAM-TRIG reserv",DIMC),36:("UART1_CTS","reserv",DIMC),
 37:("SPI1_MOSI","reserv",DIMC),38:("I2S0_SDIN","reserv",DIMC),39:("GND","",GNDc),40:("I2S0_SDOUT","reserv",DIMC)}
cl, cr, py0, prh = 470, 540, 1430, 29
rect(cl - 24, py0 - 18, (cr - cl) + 48, 20 * prh + 10, "#eceae2", "#cfccc1", 1.2, 6)
for i in range(20):
    cy = py0 + i * prh; nl, nr = 2 * i + 1, 2 * i + 2
    for cx, n, left_ in [(cl, nl, True), (cr, nr, False)]:
        dn, us, col = PINS[n]
        if n == 1: rect(cx - 9, cy - 9, 18, 18, col, INK, 1.1, 2)
        else: dot((cx, cy), 9, col, INK, 1.1)
        txt(cx, cy + 3.5, str(n), 8.5, "middle", "#fff" if col != BUSc else INK, 700, MONO)
        tx = cx - 21 if left_ else cx + 21; an = "end" if left_ else "start"
        txt(tx, cy - 1, dn, 9, an, INK, 700, MONO)
        if us: txt(tx, cy + 11, us, 8.5, an, col if col not in (BUSc, DIMC, GNDc) else MUTED, 700 if col in (F1, F2) else 400, SANS)
txt(60, 2002, "Matning: RoboClaw 2x7A (1 USB) driver BÅDA bandmotorerna → closed-loop synk; position/fart → Jetson via USB. Encoder band A=E6B2-CWZ6C (single-ended)→EN1; band B=E6B2-CWZ1X (RS-422 @5V)→kamerans diff encoder A/B (IN1± pin3/4, IN2± pin5/6, native) + 26C32 (diff→single)→EN2 (sluter B:s loop). Anhåll+fotocell=nolla. LR400→RS-485 (ch4 ledig). Gemensam GND.", 9.3, "start", MUTED, 400)

# ---- BOM ----
panel(1060, 1388, 1380, 640, "4 · KOMPLETT BOM (priser SEK)", INK)
RH = 20
def bomcol(items, x, head, acc):
    rect(x, 1428, 670, 24, acc, acc, 0, 5); txt(x + 8, 1445, head, 10, "start", "#fff", 700, SANS)
    tot = 0
    for j, (m, q, p, src) in enumerate(items):
        ry = 1454 + j * RH; tot += q * p
        if j % 2: rect(x, ry, 670, RH, PANEL, "none", 0)
        name = ((f"{q}× " if q > 1 else "") + m)[:42]
        txt(x + 7, ry + 14, name, 8, "start", INK, 700, SANS)
        txt(x + 470, ry + 14, src[:18], 7.5, "start", MUTED, 400, SANS)
        txt(x + 662, ry + 14, f"{q*p:,}".replace(",", " "), 8.5, "end", INK, 700, MONO)
    return tot
f1items = [(m, q, p, src) for (k, m, q, r, i, u, p, f, src) in BOM if f == 1]
f2items = [(m, q, p, src) for (k, m, q, r, i, u, p, f, src) in BOM if f == 2]
bomcol(f1items, 1078, "FAS 1 — FULL 3D-MÄTRIGG (röd+grön+matning)", F1)
bomcol(f2items, 1762, "FAS 2 — LINE-SCAN-YTA + PUNKTLASER", F2)
ry1 = 1454 + len(f1items) * RH + 8
rect(1078, ry1, 670, 30, "#eaf5ee", F1, 1.2, 5); txt(1086, ry1 + 20, "SUMMA FAS 1", 11, "start", F1, 700, SANS)
txt(1740, ry1 + 20, f"{bom_total(1):,} kr".replace(",", " "), 12, "end", F1, 700, MONO)
ry2 = 1454 + len(f2items) * RH + 8
rect(1762, ry2, 670, 30, "#f1eaf7", F2, 1.2, 5); txt(1770, ry2 + 20, "FAS 2-tillägg", 11, "start", F2, 700, SANS)
txt(2424, ry2 + 20, f"+{bom_total(2)-bom_total(1):,} kr".replace(",", " "), 12, "end", F2, 700, MONO)
rect(1762, ry2 + 38, 670, 32, INK, INK, 0, 5); txt(1770, ry2 + 60, "FULL SVIT (Fas 1+2)", 12, "start", "#fff", 700, SANS)
txt(2424, ry2 + 60, f"{bom_total(2):,} kr".replace(",", " "), 13, "end", "#fff", 700, MONO)

tb_x, tb_y = W - 470, H - 78
rect(tb_x, tb_y, 426, 52, "#fff", INK, 1.4); L(tb_x, tb_y + 26, tb_x + 426, tb_y + 26, INK, 1); L(tb_x + 264, tb_y, tb_x + 264, tb_y + 52, INK, 1)
txt(tb_x + 10, tb_y + 17, "VIRKESSKANNER — PROTOTYP-ARK", 11.5, "start", INK, 700, SANS); txt(tb_x + 274, tb_y + 17, "PROTO-ALL", 11, "start", INK)
txt(tb_x + 10, tb_y + 43, "allt i ett · auto ur src+BOM", 9.5, "start", MUTED); txt(tb_x + 274, tb_y + 43, "ej skalenlig", 9.5, "start", MUTED)
add('</svg>')
dst = os.path.join(ROOT, "prototype-rig-3d.svg")
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("skrev", dst, f"({len(out)} element) · Fas1={bom_total(1)} Full={bom_total(2)}")
