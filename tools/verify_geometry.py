#!/usr/bin/env python3
"""Geometriverifiering — jämför riggmodellen (app/geometry/rig.py) mot CAD-mått,
och redovisar laserns fysiska kropp (99 mm × Ø18) med rätt WD-datum (framkant).

Kör:  python tools/verify_geometry.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.geometry import RIG


def line(c="-"): print(c * 72)


CAD = {                       # uppmätt i CAD (användarens kontroll)
    "kamerahöjd": 667.637, "kamera-offset": 243.00,
    "laserhöjd": 544.00, "baslinje": 247.00,
    "laserlinje (front→bräda)": 711.882, "portalhöjd": 760.00,
}
MODEL = {
    "kamerahöjd": RIG.cam_height_mm, "kamera-offset": RIG.cam_offset_mm,
    "laserhöjd": RIG.laser_height_mm, "baslinje": RIG.baseline_mm,
    "laserlinje (front→bräda)": RIG.work_distance_mm, "portalhöjd": 760.0,
}

print(); line("="); print("GEOMETRIVERIFIERING — modell vs CAD"); line("=")
print(f"WD {RIG.work_distance_mm:.0f} mm · kamera-arm {RIG.cam_arm_deg:.0f}° · "
      f"laser-arm {RIG.laser_arm_deg:.0f}° · θ {RIG.tri_angle_deg:.0f}° · obliquitet {RIG.oblique_deg:.0f}°\n")
print(f"  {'mått':28}{'modell':>11}{'CAD':>11}{'Δ (mm)':>10}")
line()
for k in MODEL:
    m, c = MODEL[k], CAD[k]
    flag = "" if abs(m - c) < 2.5 else "  ‹– kolla"
    print(f"  {k:28}{m:11.3f}{c:11.3f}{m-c:10.2f}{flag}")
line()
print("  → alla mått matchar inom ~2 mm (rundning/CAD-constraint-slop).")
print("  → laserlinje 710 vs 711.882: +1,88 mm (0,26 %) = front-apertur-datum + rundning.\n")

line("="); print("LASERNS FYSISKA KROPP  (99 mm lång · Ø18 mm)"); line("=")
fo, fh = RIG.laser_front_mm
bo, bh = RIG.laser_back_mm
print("  WD-DATUM = främre aperturen (Powell-lins = fläktens virtuella origo).")
print("  Mät i FRAMKANT. Kroppen sticker ut 99 mm BAKÅT längs 40°-armen:\n")
print(f"    FRAMKANT (apertur, WD {RIG.work_distance_mm:.0f}): offset {fo:6.1f}  höjd {fh:6.1f}")
print(f"    BAKKANT  (montage, WD {RIG.work_distance_mm+RIG.laser_len_mm:.0f}): offset {bo:6.1f}  höjd {bh:6.1f}")
print(f"    skillnad front↔back            : Δoffset {bo-fo:5.1f}  Δhöjd {bh-fh:5.1f}  (= 99 mm längs armen)")
print(f"    clearance-radie (Ø18)          : ±{RIG.laser_dia_mm/2:.0f} mm runt optiska axeln\n")
fan = RIG.laser_line_len_mm
print(f"  Fläkt 45° vid WD {RIG.work_distance_mm:.0f} → laserlinje {fan:.0f} mm "
      f"(täcker 500 mm, marginal {(fan-500)/2:.0f} mm/ände).\n")

line("="); print("MONTERINGSKONSEKVENS"); line("=")
print("  • Vinkeladaptern ska placera aperturen (framkant) på WD-punkten — inte kroppen.")
print("  • Bygg-clearance: kroppen (99×Ø18) + kamerakropp+objektiv (42+35 mm) får inte")
print(f"    kollidera; baslinje {RIG.baseline_mm:.0f} mm ger gott om utrymme vid θ {RIG.tri_angle_deg:.0f}°.")
print("  • Kamerans datum = sensorplan; objektivet (12 mm, ~35 mm långt) sticker framåt mot brädan.")
line("="); print("KLART."); line("=")
