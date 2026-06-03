#!/usr/bin/env python3
"""Genererar en teknisk ritning (SVG) över mätramens sensorplacering.

Alla mått/takter hämtas direkt ur src.hardware.Rig så ritningen alltid speglar
den faktiska riggkonfigurationen. Tre vyer: ovanifrån (plan), ändvy/tvärsnitt
(triangulering) och underifrån (transport), plus spec- och takttabell.

    python tools/draw_rig.py            # -> sensor-rig-layout.svg i projektroten
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig

r = Rig()
P = r.placement()
S = r.summary()
M = r.measurement_points(0.25)
SEG = r.segments()

# ---- härledda hjälpvärden ----
surf_needed_hz = round(r.surface_line_rate_at_feed)         # 758 Hz @ 0,25 m/s
surf_fov = r.surface_fov_per_cam_mm                          # 2700 mm
BL = 5400.0                                                  # brädlängd
BW = 150.0                                                   # brädbredd
BT = 22.0                                                    # tjocklek

# ---------- SVG-byggare ----------
W, H = 1720, 2900
INK, MUTED, DIMC = "#23262b", "#6a6e74", "#9a9ea4"
PAPER, PANEL, GRID = "#f7f6f1", "#ecebe4", "#dedcd3"
C_SURF, C_PROF, C_LAS = "#2f6fb0", "#2f9e6e", "#e8542c"
MONO = "'IBM Plex Mono','DejaVu Sans Mono',monospace"
SANS = "'IBM Plex Sans','DejaVu Sans',sans-serif"
out: list[str] = []
def add(s): out.append(s)

def esc(t): return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
def txt(x, y, s, size=13, anchor="start", fill=INK, weight=400, fam=MONO, rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tr}>{esc(s)}</text>')
def line(x1, y1, x2, y2, stroke=INK, w=1.2, dash=None, opacity=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{w}"{d} opacity="{opacity}"/>')
def rect(x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None, opacity=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{opacity}"/>')
def circle(x, y, rr, fill="none", stroke=INK, sw=1.2):
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def poly(pts, fill="none", stroke=INK, sw=1.2):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def arrow(x1, y1, x2, y2, stroke=INK, w=1.4):
    import math
    line(x1, y1, x2, y2, stroke, w)
    a = math.atan2(y2 - y1, x2 - x1); L = 9
    for s in (0.5, -0.5):
        add(f'<line x1="{x2:.1f}" y1="{y2:.1f}" x2="{x2-L*math.cos(a-s):.1f}" '
            f'y2="{y2-L*math.sin(a-s):.1f}" stroke="{stroke}" stroke-width="{w}"/>')

def hdim(x1, x2, y, text, tick=7, fill=DIMC, above=True):
    line(x1, y - tick, x1, y + tick, fill, 1)
    line(x2, y - tick, x2, y + tick, fill, 1)
    arrow((x1 + x2) / 2 - 0.1, y, x1, y, fill, 1)
    arrow((x1 + x2) / 2 + 0.1, y, x2, y, fill, 1)
    ty = y - 6 if above else y + 15
    add(f'<rect x="{(x1+x2)/2-len(text)*4.0:.1f}" y="{ty-11:.1f}" width="{len(text)*8.0:.1f}" '
        f'height="15" fill="{PAPER}" opacity="0.9"/>')
    txt((x1 + x2) / 2, ty, text, 12, "middle", fill)
def vdim(y1, y2, x, text, tick=7, fill=DIMC):
    line(x - tick, y1, x + tick, y1, fill, 1)
    line(x - tick, y2, x + tick, y2, fill, 1)
    arrow(x, (y1 + y2) / 2 - 0.1, x, y1, fill, 1)
    arrow(x, (y1 + y2) / 2 + 0.1, x, y2, fill, 1)
    txt(x + 9, (y1 + y2) / 2 + 4, text, 12, "start", fill)

# ============================================================ DOC
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="{SANS}">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
# fin rutnät i bakgrunden
add('<g opacity="0.5">')
for gx in range(0, W, 40): line(gx, 0, gx, H, GRID, 0.5)
for gy in range(0, H, 40): line(0, gy, W, gy, GRID, 0.5)
add('</g>')
# yttre ram
rect(18, 18, W - 36, H - 36, "none", INK, 2)
rect(26, 26, W - 52, H - 52, "none", MUTED, 0.8)

# ---- rubrik ----
txt(48, 70, "MULTISENSOR VIRKESSKANNER — MÄTRAM & SENSORPLACERING", 26, "start", INK, 700, SANS)
txt(48, 96, "Cross-feed (Alt A): bräda 5400 × 150 × 22 mm matas i SIDLED förbi stationära "
            "moduler. Alla optiska sensorer i portal ÖVER banan.", 14, "start", MUTED, 400, SANS)
line(48, 112, W - 48, 112, INK, 1.5)

def view_label(x, y, tag, name):
    rect(x, y, 24, 20, INK, INK)
    txt(x + 12, y + 15, tag, 13, "middle", PAPER, 700, SANS)
    txt(x + 34, y + 15, name, 15, "start", INK, 700, SANS)

# ============================================================ VY A — PLAN
ax0, ax1 = 170, 1500
def AX(mm): return ax0 + mm * (ax1 - ax0) / BL
gA = 140
add(f'<g transform="translate(0,{gA})">')
view_label(48, 6, "A", "OVANIFRÅN (PLAN) — moduler längs brädans längd")
y_surf, y_las, y_cam, yb0, yb1 = 96, 170, 224, 262, 330

# brädan (längd horisontellt, bredd vertikalt) + matningspil
rect(AX(0), yb0, AX(BL) - AX(0), yb1 - yb0, "#e9e1cf", "#b9a96f", 1.2)
txt(AX(BL) / 1 - 6 + ax0 - ax0, 0, "", 1)  # noop
txt(ax0 + 6, yb0 + 20, "BRÄDA 5400 mm", 12, "start", "#8a7d4e", 700)
arrow(AX(BL) + 28, (yb0 + yb1) / 2, AX(BL) + 28, yb1 + 48, C_LAS, 2)
txt(AX(BL) + 36, (yb0 + yb1) / 2 + 4, "matning", 12, "start", C_LAS, 700)
txt(AX(BL) + 36, (yb0 + yb1) / 2 + 20, "0,25 m/s", 11, "start", C_LAS)

# 2 ytkameror (täcker var sin halva, FOV 2700 mm)
for i, cx in enumerate([1350, 4050]):
    x = AX(cx)
    rect(x - 34, y_surf - 16, 68, 32, "#dce8f4", C_SURF, 1.6, 3)
    txt(x, y_surf + 5, f"YTA {i+1}", 12, "middle", C_SURF, 700)
    line(x, y_surf + 16, x, yb0, C_SURF, 0.8, "3 3")
    a, b = AX(cx - surf_fov / 2), AX(cx + surf_fov / 2)
    line(a, y_surf - 24, b, y_surf - 24, C_SURF, 1)
    line(a, y_surf - 28, a, y_surf - 20, C_SURF, 1); line(b, y_surf - 28, b, y_surf - 20, C_SURF, 1)
    txt(x, y_surf - 30, "FOV 2700 mm", 10, "middle", C_SURF)
txt(AX(0), y_surf - 50, "2× MindVision MV-XGLC83BM-T4-90 · 8192×4 TDI · 10GigE · 0,33 mm/px",
    12, "start", C_SURF, 700)

# 6 laser+kamera-moduler vid segmentcentrum; laserlinjernas extents (överlapp)
txt(AX(0), y_las - 26, "6× modul  (laser + profilkamera)  —  laserlinje LÄNGS sitt segment",
    12, "start", C_PROF, 700)
for (s, e, c) in SEG:                       # laserlinjesegment (visar överlapp)
    rect(AX(s), y_las - 6, AX(e) - AX(s), 12, C_LAS, C_LAS, 0, 0, None, 0.16)
    line(AX(s), y_las, AX(e), y_las, C_LAS, 2)
for k, (s, e, c) in enumerate(SEG):
    x = AX(c)
    circle(x, y_las, 5, "#fff", C_LAS, 2)               # laser
    rect(x - 16, y_cam - 14, 32, 26, "#d8efe3", C_PROF, 1.6, 3)  # profilkamera
    txt(x, y_cam + 3, f"M{k+1}", 11, "middle", C_PROF, 700)
    line(x, y_las + 5, x, y_cam - 14, C_PROF, 0.8, "3 3")
# baslinje laser<->kamera (i matningsled)
vdim(y_las, y_cam, AX(SEG[2][2]) + 70, "baslinje 600 mm")

# dimensioner: ett segment + överlapp + total
s0, e0, _ = SEG[0]; s1, _, _ = SEG[1]
hdim(AX(s0), AX(e0), yb1 + 70, "segment 1098 mm")
hdim(AX(s1), AX(e0), yb1 + 104, "överlapp 150 mm", fill=C_LAS)
hdim(AX(0), AX(BL), yb1 + 138, "total mätbredd 5400 mm (= brädlängd)")
add('</g>')

# ============================================================ VY B — ÄNDVY
gB = 715
add(f'<g transform="translate(0,{gB})">')
view_label(48, 6, "B", "ÄNDVY / TVÄRSNITT — triangulering (sett längs brädan)")
import math
SC = 1 / 4.1                       # px per mm (höjd/sida)
cxL = 470                          # laserns x (mätpunkt)
yb = 470                           # brädans ovansida (lokal y)
def UP(mm): return yb - mm * SC    # höjd över brädan
surf_wd = round(P["surface_wd_mm"]); surf_lens = round(P["surface_lens_mm"])
xs = cxL - 300                     # ytkamerans x (förskjuten i matningsled)
# portalbalk
rect(120, 40, 1000, 22, "#cfd2d6", "#9aa0a6", 1.2, 3)
txt(130, 56, "PORTALBALK", 11, "start", MUTED, 700)
# transportör + bräda (tvärsnitt: bredd 150, tjocklek 22)
bw, bt = BW * SC, BT * SC
rect(cxL - bw / 2, yb, bw, bt, "#e9e1cf", "#b9a96f", 1.4)
txt(cxL, yb + bt + 16, "bräda 150×22 mm", 11, "middle", "#8a7d4e")
bandL, bandR = xs - bw / 2 - 20, cxL + bw / 2 + 40
rect(bandL, yb + bt, bandR - bandL, 16, "#d7d4cc", "#aaa79e", 1)   # band
for dz in (-50, -16, 18, 52):
    circle(cxL + dz, yb + bt + 8, 4, "#cfae3e", "#8a7d4e", 1)
txt(bandL, yb + bt + 42, "kedjetransport + medbringare", 10, "start", MUTED)

# --- ytkamera: SAMMA nivå som lasern, förskjuten i matningsled ---
ys = UP(surf_wd)                   # = laserns nivå
rect(xs - 30, ys - 26, 60, 30, "#dce8f4", C_SURF, 1.8, 3)
txt(xs, ys - 32, "YTKAMERA", 11, "middle", C_SURF, 700)
poly([(xs - 18, ys + 4), (xs + 18, ys + 4), (xs + 6, ys + 16), (xs - 6, ys + 16)], "#dce8f4", C_SURF, 1.4)
rect(xs - bw / 2, yb, bw, bt, "none", C_SURF, 1.1, 0, "4 3")        # egen (förskjuten) avläsningslinje
line(xs - 7, ys + 16, xs - bw / 2, yb, C_SURF, 0.9, "4 3")
line(xs + 7, ys + 16, xs + bw / 2, yb, C_SURF, 0.9, "4 3")
vdim(ys + 4, yb, xs - bw / 2 - 40, f"WD {surf_wd} mm")
txt(xs, yb + bt + 16, "egen avläsningslinje", 9.5, "middle", C_SURF)
txt(xs, yb + bt + 28, "(förskjuten i matningsled)", 9.5, "middle", C_SURF)
# gemensam monteringsnivå (yta + laser på samma höjd)
line(xs, ys - 26, cxL, ys - 26, DIMC, 0.9, "5 3")
txt((xs + cxL) / 2, ys - 31, "yta + laser: samma monteringsnivå", 10, "middle", MUTED, 700)

# --- laser (rakt ner, SAMMA nivå som ytkameran) ---
yl = UP(951)
rect(cxL - 16, yl - 26, 32, 30, "#fde3da", C_LAS, 1.8, 3)
txt(cxL, yl - 32, "LASER", 11, "middle", C_LAS, 700)
add(f'<polygon points="{cxL-2:.1f},{yl+4:.1f} {cxL+2:.1f},{yl+4:.1f} {cxL+9:.1f},{yb:.1f} {cxL-9:.1f},{yb:.1f}" '
    f'fill="{C_LAS}" opacity="0.5"/>')
circle(cxL, yb, 3.5, C_LAS, C_LAS, 0)
vdim(yl + 4, yb, cxL + bw / 2 + 16, "laser-WD 951 mm")

# --- profilkamera (offset = baslinje 600, lutad 30°) ---
cxC = cxL + 600 * SC
yc = UP(1040)
add(f'<g transform="rotate(30 {cxC:.1f} {yc:.1f})">')
rect(cxC - 26, yc - 24, 52, 28, "#d8efe3", C_PROF, 1.8, 3)
txt(cxC, yc - 8, "PROFIL-", 10, "middle", C_PROF, 700)
txt(cxC, yc + 2, "KAMERA", 10, "middle", C_PROF, 700)
add('</g>')
line(cxC, yc + 6, cxL, yb, C_PROF, 1.1, "4 3")        # siktlinje mot mätpunkten
# trianguleringsvinkel (mellan lodlinjen och siktlinjen)
line(cxL, yb, cxL, yb - 120, DIMC, 0.8, "3 3")
add(f'<path d="M {cxL} {yb-70} A 70 70 0 0 1 {cxL+70*0.5:.1f} {yb-70*0.866:.1f}" '
    f'fill="none" stroke="{C_PROF}" stroke-width="1.2"/>')
txt(cxL + 30, yb - 78, "30°", 12, "start", C_PROF, 700)
hdim(cxL, cxC, yc - 60, "baslinje 600 mm", fill=C_PROF)
_ang = math.degrees(math.atan2((yc + 6) - yb, cxC - cxL))
_t = 0.62
_lx, _ly = cxL + _t * (cxC - cxL), yb + _t * ((yc + 6) - yb)
txt(_lx + 16, _ly + 6, "profil-WD 1040 mm", 11, "middle", C_PROF, 700, MONO, rot=_ang)
# höjdmätrange ±25 mm
line(cxL - bw / 2 - 18, UP(0), cxL - bw / 2 - 18, UP(25), C_PROF, 1)
line(cxL - bw / 2 - 18, UP(0), cxL - bw / 2 - 18, UP(-25), C_PROF, 1)
line(cxL - bw / 2 - 22, UP(25), cxL - bw / 2 - 14, UP(25), C_PROF, 1)
line(cxL - bw / 2 - 22, UP(-25), cxL - bw / 2 - 14, UP(-25), C_PROF, 1)
txt(cxL - bw / 2 - 26, UP(0) + 4, "±25 mm", 10, "end", C_PROF)
txt(720, 122,
    "Höjdupplösning 0,78 mm  ·  lateral 0,45 mm/px  ·  djupområde 50 mm", 12, "start", C_PROF, 700)
add('</g>')

# ============================================================ VY C — UNDERIFRÅN
gC = 1245
add(f'<g transform="translate(0,{gC})">')
view_label(48, 6, "C", "UNDERIFRÅN — transport (5 kedjor + medbringare)")
ux0, ux1 = 170, 1500
def UX(mm): return ux0 + mm * (ux1 - ux0) / BL
uy0, uy1 = 70, 250
rect(UX(0), uy0, UX(BL) - UX(0), uy1 - uy0, "none", "#b9a96f", 1.2, 0, "6 4")
txt(UX(0) + 6, uy0 - 8, "brädans yttermått (5400 mm)", 11, "start", "#8a7d4e")
chains = [375, 1500, 2700, 3900, 5025]      # 5 kedjor utspridda över längden
for cz in chains:
    x = UX(cz)
    rect(x - 7, uy0 - 18, 14, uy1 - uy0 + 36, "#d7d4cc", "#9aa0a6", 1)   # kedja (löper i matningsled)
    for d in range(0, 6):
        circle(x, uy0 - 4 + d * (uy1 - uy0 + 24) / 5, 5, "#cfae3e", "#8a7d4e", 1)  # medbringare
# drivaxel + kuggdrev + motor (ena änden)
line(UX(0) - 20, uy0 - 30, UX(BL) + 20, uy0 - 30, "#9aa0a6", 3)
for cz in chains: circle(UX(cz), uy0 - 30, 9, "#cfd2d6", "#7a7f86", 1.4)
rect(UX(0) - 70, uy0 - 44, 40, 28, "#cfd2d6", "#7a7f86", 1.2, 2)
txt(UX(0) - 50, uy0 - 27, "M", 13, "middle", INK, 700)
txt(UX(0) - 70, uy0 - 50, "drivmotor + axel", 10, "start", MUTED)
arrow(UX(BL) + 40, uy0, UX(BL) + 40, uy1, C_LAS, 2)
txt(UX(BL) + 48, (uy0 + uy1) / 2, "matning", 11, "start", C_LAS, 700)
# portalfötter (2)
for fz in (700, 4700):
    rect(UX(fz) - 16, uy1 + 16, 32, 24, "#c9ccd0", "#7a7f86", 1.2, 2)
    txt(UX(fz), uy1 + 52, "portalfot", 10, "middle", MUTED)
hdim(UX(chains[0]), UX(chains[1]), uy1 + 90, "kedjedelning ~1125 mm")
hdim(UX(0), UX(BL), uy1 + 124, "5 kedjor över 5400 mm")
txt(ux0, uy1 + 158, "OBS: alla optiska sensorer sitter i portalen OVANFÖR banan (vy B). "
                    "Undersidan bär enbart transporten.", 11, "start", MUTED)
add('</g>')

# ============================================================ SPEC- & TAKTTABELL
gT = 1670
add(f'<g transform="translate(0,{gT})">')
line(48, 0, W - 48, 0, INK, 1.5)
txt(48, 26, "SPECIFIKATION · TAKTER & UPPDATERINGSFREKVENSER", 17, "start", INK, 700, SANS)

cols = [
    (60, C_SURF, "YTKANAL — FÄRG", [
        ("Kamera", "2× MindVision MV-XGLC83BM-T4-90"),
        ("Sensor", "mono 8192×4 TDI (4-line), 7 µm"),
        ("Gränssnitt", "10GBase-T (10GigE), M72"),
        ("Radtakt (datablad)", "109,89 kHz @8-bit / 87,7 @12-bit"),
        ("Färgtakt (RGB+NIR strobe)", "÷4 → 27,5 kHz effektiv"),
        ("Behövd takt @0,25 m/s", f"{surf_needed_hz} Hz  (stor marginal)"),
        ("Bandbredd @max", "7,2 Gbit/s  (ryms i 10GigE)"),
        ("Upplösning / WD / lins", f"0,33 mm/px · {surf_wd} mm · M72 ~{surf_lens} mm"),
        ("Px tvärs / rader per bräda", "16 384 px · ~455 rader"),
    ]),
    (600, C_PROF, "HÖJD — LASERTRIANGULERING", [
        ("Kamera", "6× Hikrobot MV-CS050-10UC"),
        ("Sensor", "IMX264 2448×2048, 3,45 µm, GS"),
        ("Bildtakt (datablad)", "60 fps @ full bild (USB3)"),
        ("Profiltakt (drift, ROI-band)", "500 profiler/s (~250 rader)"),
        ("Laser", "6× iadiy LM9R650H100L60"),
        ("Laser", "650 nm · 100 mW · 60° · CW"),
        ("Geometri", "WD 1040/951 mm · vinkel 30° · baslinje 600 mm"),
        ("Upplösning", "lateral 0,45 mm/px · höjd 0,78 mm"),
        ("Segment / överlapp / djup", "1098 mm · 150 mm · ±25 mm"),
    ]),
    (1140, C_LAS, "MATNING · GEOMETRI · PUNKTER", [
        ("Upplägg", "cross-feed (Alt A), sidledsmatning"),
        ("Bräda", "5400 × 150 × 22 mm"),
        ("Matningshastighet", "0,25 m/s  (≈ 60 brädor/min)"),
        ("Moduler längs längden", "6 (laser + profilkamera)"),
        ("Ytkameror", "2 (var sin halva, FOV 2700 mm)"),
        ("Profilpunkter / bräda", "≈ 4,41 milj. (14 688 × 300)"),
        ("Profiltäthet längs matning", "0,5 mm/profil @0,25 m/s"),
        ("Ytpixlar / bräda", "≈ 7,46 milj."),
        ("Laser = realtid (CW)", "takten sätts av profilkameran"),
    ]),
]
rowh = 30
for (cx, accent, title, rows) in cols:
    cw = 500
    rect(cx, 44, cw, 30, accent, accent, 0, 4)
    txt(cx + 12, 64, title, 13, "start", PAPER, 700, SANS)
    rect(cx, 74, cw, rowh * len(rows), "#fff", accent, 1)
    for i, (k, v) in enumerate(rows):
        ry = 74 + i * rowh
        if i % 2: rect(cx, ry, cw, rowh, PANEL, "none", 0)
        txt(cx + 12, ry + 19, k, 11, "start", MUTED, 700)
        txt(cx + 215, ry + 19, v, 11, "start", INK)
        line(cx + 208, ry + 6, cx + 208, ry + rowh - 6, GRID, 1)
add('</g>')

# ============================================================ VY D — SÅ FUNKAR DET
gD = 2150
add(f'<g transform="translate(0,{gD})">')
line(48, 0, W - 48, 0, INK, 1.5)
txt(48, 26, "SÅ FUNKAR DET — SIGNAL- & DATABEHANDLINGSKEDJA (bräda → sorterade bitar)",
    17, "start", INK, 700, SANS)

stages = [
    (C_LAS, "1 INMATNING", ["cross-feed 0,25 m/s", "≈ 60 brädor/min (1/s)"]),
    (C_SURF, "2 SENSORSVEP", ["2 färglinjekameror (yta)", "6 laser+profil (höjd) +NIR"]),
    (C_PROF, "3 TRIANGULERING", ["höjd h = lateral/tanθ", "0,78 mm per kamera-px"]),
    (C_SURF, "4 BILDBYGGE", ["rad-för-rad → 2D-karta", "16384×455 px · 4,41 Mpkt"]),
    (C_PROF, "5 SEGMENTERING", ["U-Net: färg+relief+", "ådring+NIR → klasser"]),
    (C_LAS, "6 MÄTNING", ["kvistandel, böj/krok 2 m,", "sprickor, dimension"]),
    (C_PROF, "7 KLASSNING", ["SS 230120 per bit →", "C30/C24/C18/C14/Vrak"]),
    (C_LAS, "8 KAP & SORT", ["DP-optimerad kapplan ·", "fasta klingor + klaffar"]),
]
sx0, sy, sw, sh, sgap = 56, 48, 184, 92, 19
for i, (acc, title, lines) in enumerate(stages):
    x = sx0 + i * (sw + sgap)
    rect(x, sy, sw, sh, "#fff", acc, 1.4, 4)
    rect(x, sy, sw, 24, acc, acc, 0, 4)
    rect(x, sy + 12, sw, 12, acc, acc, 0)               # platta nederkant på rubrikremsa
    txt(x + 10, sy + 17, title, 12, "start", PAPER, 700, SANS)
    for j, ln in enumerate(lines):
        txt(x + 10, sy + 44 + j * 17, ln, 10.5, "start", INK)
    if i < len(stages) - 1:
        arrow(x + sw + 2, sy + sh / 2, x + sw + sgap - 2, sy + sh / 2, MUTED, 1.6)

# ----- tre räkneexempel -----
ey = 168
ew = (W - 96 - 2 * 24) / 3
def ebox(idx, title, accent):
    ex = 48 + idx * (ew + 24)
    rect(ex, ey, ew, 250, "#fff", accent, 1.3, 5)
    rect(ex, ey, ew, 26, accent, accent, 0, 5); rect(ex, ey + 13, ew, 13, accent, accent, 0)
    txt(ex + 12, ey + 18, title, 12, "start", PAPER, 700, SANS)
    return ex

# (A) triangulering
ax = ebox(0, "RÄKNEEXEMPEL — TRIANGULERING (höjd)", C_PROF)
for k, s in enumerate(["lateral 0,449 mm/px  (= FOV 1098 / 2448 px)",
                       "höjd  h = 0,449 / tan 30° = 0,78 mm",
                       "→ 1 px kameraförskjutning ↔ 0,78 mm höjd",
                       "mätrange i höjd: ±25 mm (50 mm)"]):
    txt(ax + 12, ey + 46 + k * 17, s, 10.5, "start", INK)
lx, lyb, ccy = ax + 70, ey + 236, ey + 128       # diagram under texten
line(lx, ccy, lx, lyb, C_LAS, 3)                        # laserstråle ner
circle(lx, lyb, 3.5, C_LAS, C_LAS, 0)
ccx = ax + 210
poly([(ccx - 16, ccy - 12), (ccx + 16, ccy - 12), (ccx + 16, ccy + 8), (ccx - 16, ccy + 8)], "#d8efe3", C_PROF, 1.4)
txt(ccx, ccy - 2, "kamera", 9, "middle", C_PROF, 700)
line(ccx, ccy + 8, lx, lyb, C_PROF, 1.1, "4 3")
line(lx, lyb, lx, lyb - 70, DIMC, 0.8, "3 3")
add(f'<path d="M {lx} {lyb-44} A 44 44 0 0 1 {lx+44*0.5:.1f} {lyb-44*0.866:.1f}" fill="none" stroke="{C_PROF}" stroke-width="1.1"/>')
txt(lx + 22, lyb - 46, "θ=30°", 10, "start", C_PROF, 700)

# (B) kapplan & värde
bx = ebox(1, "RÄKNEEXEMPEL — KAPPLAN & VÄRDE", C_LAS)
bbl, bbr = bx + 20, bx + ew - 20
bby = ey + 58
rect(bbl, bby, bbr - bbl, 26, "none", "#b9a96f", 1.2)
split = bbl + (bbr - bbl) * (3.0 / 5.4)
rect(bbl, bby, split - bbl, 26, "#2f9e6e", "#2f9e6e", 0, 0, None, 0.55)   # C30
rect(split, bby, bbr - split, 26, "#d6a23e", "#d6a23e", 0, 0, None, 0.6)  # C18
circle(split + (bbr - split) * 0.74, bby + 13, 5, "#7a4a2a", "#5a3418", 1.2)  # kvistgrupp
txt((bbl + split) / 2, bby + 17, "C30", 11, "middle", "#1c5e42", 700)
txt((split + bbr) / 2, bby + 17, "C18", 11, "middle", "#7a5a16", 700)
line(split, bby - 8, split, bby + 34, C_LAS, 1.4, "3 2")
txt(bbl, bby - 12, "5,4 m bräda — kvistgrupp i andra halvan", 10.5, "start", MUTED)
txt(split, bby + 48, "↑ kap vid 3,0 m", 9.5, "middle", C_LAS)
for k, s in enumerate(["bit 1  0–3,0 m  ren    → C30 · 3,0×95 = 285 kr",
                       "bit 2  3,0–5,4 m kvist → C18 · 2,4×60 = 144 kr",
                       "SUMMA per bit ............... 429 kr",
                       "hela brädan som C18: 5,4×60 = 324 kr",
                       "→ kapning per bit ger +105 kr"]):
    w = 700 if k in (2, 4) else 400
    txt(bx + 12, ey + 130 + k * 18, s, 10.5, "start", INK if k != 4 else C_PROF, w, MONO)

# (C) takt & data
cx2 = ebox(2, "RÄKNEEXEMPEL — TAKT & DATAMÄNGD", C_SURF)
for k, s in enumerate(["matning 0,25 m/s · delning 250 mm",
                       "→ 60 brädor/min  (1 bräda/s)",
                       "profiltakt 500 Hz → 0,5 mm/profil",
                       "höjd: 14 688 × 300 ≈ 4,41 milj. pkt/bräda",
                       "yta: 16 384 × 455 ≈ 7,46 milj. px/bräda",
                       "ytradtakt: behövs 758 Hz av 27,5 kHz",
                       "höjd-radtakt klaras av 500 fps (ROI)"]):
    txt(cx2 + 12, ey + 60 + k * 24, s, 11, "start", INK, 400, MONO)
add('</g>')

# ---- titelruta nere till höger ----
tb_x, tb_y, tb_w, tb_h = W - 470, H - 120, 420, 84
rect(tb_x, tb_y, tb_w, tb_h, "#fff", INK, 1.4)
line(tb_x, tb_y + 28, tb_x + tb_w, tb_y + 28, INK, 1)
line(tb_x, tb_y + 56, tb_x + tb_w, tb_y + 56, INK, 1)
line(tb_x + 250, tb_y, tb_x + 250, tb_y + tb_h, INK, 1)
txt(tb_x + 10, tb_y + 19, "MULTISENSOR VIRKESSKANNER", 13, "start", INK, 700, SANS)
txt(tb_x + 260, tb_y + 19, "RITNING", 11, "start", MUTED, 700, SANS)
txt(tb_x + 10, tb_y + 47, "Mätram — sensorplacering", 12, "start", INK, 400, SANS)
txt(tb_x + 260, tb_y + 47, "SENSOR-RIG-01", 12, "start", INK, 400)
txt(tb_x + 10, tb_y + 75, "Ej skalenlig · mått i mm", 10, "start", MUTED)
txt(tb_x + 260, tb_y + 75, "auto: src/hardware.py", 10, "start", MUTED)

add('</svg>')

dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sensor-rig-layout.svg")
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("skrev", dst, f"({len(out)} element)")
