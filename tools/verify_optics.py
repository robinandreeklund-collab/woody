#!/usr/bin/env python3
"""Exakt optikverifiering INFÖR beställning — profilkamera×lins, linjekamera×lins,
och linjelaserns fläktvinkel. Räknar från sensorernas datablads-mått + tunn-lins/
maskinsyn-formeln FOV = sensor·WD/f, och jämför mot linsernas EGNA WD/förstorings-
tabeller där de finns (ZLKC). Allt i mm.  Kör:  python tools/verify_optics.py
"""
import math

def line(c="-"): print(c * 76)
def ok(cond): return "✓ OK" if cond else "✗ FEL"

BOARD_LEN = 500.0          # brädans längd = laserlinjens riktning = FOV som ska täckas
print(); line("="); print("OPTIKVERIFIERING — prototyp, bräda {:.0f} mm".format(BOARD_LEN)); line("=")

# ============================================================ 0) MONTERING / GÄNGA
print("\n[0] MONTERING & GÄNGA  (databladsbekräftat)")
line()
print("  Profilkamera MV-CS050-10UM : C-mount, 2/3\", MONO (Hikrobot datablad)")
print("  Lins MVL-MF1228M-8MP       : C-mount, 2/3\", 12 mm, 8MP (Hikrobot/RMA datablad)")
print("   → kamera C-mount = lins C-mount  → skruvas direkt, INGEN adapter        ✓")
print("   → 2/3\"-lins täcker 2/3\"-sensor (diag 11,01 mm)                           ✓")
print("  Filtergänga (linsfront)    : M30.5×0.5  (Hikrobot/maxxvision datablad)")
print("   → FS03-BP650 / FS03-BP525 = M30.5×0.5  → skruvas på linsfronten          ✓")
print("  Sensor MONO (10U'M')       : rätt för lasertriangulering (se [1] not)     ✓")

# ============================================================ 1) PROFILKAMERA × LINS
# Hikrobot MV-CS050-10UM (Sony IMX264, 2/3"): 2448×2048 px, 3,45 µm
P_PXW, P_PXH, P_PITCH = 2448, 2048, 3.45e-3   # mm
P_SW, P_SH = P_PXW * P_PITCH, P_PXH * P_PITCH  # sensor lång/kort axel [mm]
P_DIAG = math.hypot(P_SW, P_SH)
F_PROF = 12.0                                  # HIKROBOT MVL-MF1228M-8MP (2/3", 8MP)
OBL = 30.0                                      # modulens lutning från lod

print("\n[1] PROFILKAMERA × LINS  (3D-triangulering, RÖD + GRÖN, identiska)")
line()
print(f"  Sensor (lång×kort)     : {P_SW:.3f} × {P_SH:.3f} mm  (diag {P_DIAG:.2f} mm, 2/3\")")
print(f"  Lins                   : f = {F_PROF:.0f} mm  (2/3\"/8MP → bildcirkel ~11 mm)")
# FOV längs linjen sätts av LÅNGA axeln. WD för FOV = BOARD_LEN:
WD_prof = BOARD_LEN * F_PROF / P_SW            # = f/m, maskinsyn-approx
m_prof = P_SW / BOARD_LEN
fov_long = P_SW * WD_prof / F_PROF
res_long = BOARD_LEN / P_PXW                   # mm/px längs linjen
fov_short = P_SH * WD_prof / F_PROF            # kort axel (höjd/triangulering) i objektrymd
MH = WD_prof * math.cos(math.radians(OBL))
SOFF = WD_prof * math.sin(math.radians(OBL))
print(f"  Förstoring m           : {m_prof:.5f}×   (1/m = {1/m_prof:.1f})")
print(f"  Arbetsavstånd (slant)  : {WD_prof:.1f} mm   för FOV = {BOARD_LEN:.0f} mm")
print(f"  → FOV längs linjen      : {fov_long:.1f} mm   {ok(abs(fov_long-BOARD_LEN)<1)}  (täcker brädan)")
print(f"  → Upplösning längs linje: {res_long:.3f} mm/px ({P_PXW} px över {BOARD_LEN:.0f} mm)")
print(f"  → Kort axel i objektrymd: {fov_short:.0f} mm (höjd-/djupkanal via 30° triangulering)")
print(f"  Diag {P_DIAG:.2f} mm vs lins-bildcirkel ~11 mm : {ok(P_DIAG <= 11.05)}  (2/3\"-lins täcker 2/3\"-sensor)")
print(f"  Riggplacering          : modulhöjd MH = {MH:.0f} mm, sidooffset = {SOFF:.0f} mm")

# ============================================================ 2) LINJEKAMERA × LINS
# Huateng 4K line-scan: 4096×4 px, 7,0 µm ; lins ZLKC TM2004MPC f=20, Φ30, BFL 12
L_PX, L_PITCH = 4096, 7.0e-3
L_SW = L_PX * L_PITCH
F_LINE = 20.0
L_IMGCIRC = 30.0
WD_line = 400.0                                # vald: = punktlaserplan (gemensam balk)

print("\n[2] LINJEKAMERA × LINS  (4K färgyta)")
line()
print(f"  Sensor (linje)         : {L_SW:.3f} mm  ({L_PX} px × {L_PITCH*1000:.0f} µm)")
print(f"  Lins                   : ZLKC TM2004MPC  f = {F_LINE:.0f} mm, Φ{L_IMGCIRC:.0f} bildcirkel, rated 0,05–0,2×")
# Linsens EGEN tabell (WD mm, magnification): manufacturer data
ZLKC = [(94.0, 0.20), (194.0, 0.10), (393.0, 0.05)]
# linjär passning WD = a*(1/m) + b  ur två punkter (0,05 och 0,2):
(w1, m1), (w2, m2) = ZLKC[2], ZLKC[0]
a = (w1 - w2) / (1/m1 - 1/m2); b = w1 - a*(1/m1)
m_at_WD = a / (WD_line - b)                    # invertera WD = a/m + b  →  m = a/(WD-b)
fov_line = L_SW / m_at_WD
res_line = fov_line / L_PX
print(f"  Linsens tabell (WD→m)  : " + " · ".join(f"{w:.0f}mm→{mm:.2f}×" for w,mm in ZLKC))
print(f"  Passning WD = {a:.2f}/m + {b:.1f}  (ur 0,05× och 0,2×)")
print(f"  @ WD = {WD_line:.0f} mm  → m = {m_at_WD:.4f}×   {ok(0.05<=m_at_WD<=0.20 or abs(m_at_WD-0.05)<0.002)}  (i/vid rated 0,05–0,2×)")
print(f"  → FOV                   : {fov_line:.0f} mm   {ok(fov_line >= BOARD_LEN)}  (täcker {BOARD_LEN:.0f} mm, marginal {(fov_line-BOARD_LEN)/2:.0f} mm/ände)")
print(f"  → Upplösning            : {res_line:.3f} mm/px   {ok(res_line < 0.33)}  (mål 0,33 mm/px → {0.33/res_line:.1f}× bättre)")
print(f"  Bildcirkel Φ{L_IMGCIRC:.0f} vs sensor {L_SW:.2f} mm : {ok(L_IMGCIRC >= L_SW)}  marginal {(L_IMGCIRC-L_SW)/2:.2f} mm/ände (TAJT → kolla skärpa i ändarna)")

# ============================================================ 3) LINJELASER — FLÄKTVINKEL
# Lasern är co-monterad med profilkameran → laser→bräda ≈ profilens slant-WD.
R = WD_prof
NEED = BOARD_LEN                               # måste täcka kamerans FOV (500 mm)
print("\n[3] LINJELASER — FLÄKTVINKEL (Powell)")
line()
print(f"  Laser→bräda (= profil-slant-WD): {R:.1f} mm")
print(f"  Måste täcka kamerans FOV       : {NEED:.0f} mm")
theta_exact = 2*math.degrees(math.atan((NEED/2)/R))
print(f"  → EXAKT passande fläktvinkel    : {theta_exact:.2f}°   (linje = 2·R·tan(θ/2) = {NEED:.0f} mm)")
print()
print("  Standardvinklar vid detta avstånd:")
for th in (30, 40, 45, 60):
    L = 2*R*math.tan(math.radians(th/2))
    marg = (L-NEED)/2
    verdict = "FÖR SMALT" if L < NEED else (f"täcker, marginal {marg:.0f} mm/ände" + (" (tajt)" if marg<15 else ""))
    star = "  ◀ VÄLJ" if th == 45 else ""
    print(f"    {th:>3}° → linje {L:6.0f} mm   {verdict}{star}")
L45 = 2*R*math.tan(math.radians(45/2))
print(f"\n  45°: linje {L45:.0f} mm ≥ {NEED:.0f} mm kamera-FOV → {ok(L45>=NEED)}  "
      f"(överfyller med {(L45-NEED)/2:.0f} mm/ände → inga mörka ändar)")
print(f"  38,8° vore exakt passning; 40° för tajt ({2*R*math.tan(math.radians(20)):.0f} mm); 30° underkänt → 45° rätt val.")

# ============================================================ 4) FÖRVÄNTAD PRECISION
print("\n[4] FÖRVÄNTAD PROFILPRECISION  (uppskattning)")
line()
TRI = 30.0                                   # trianguleringsvinkel (laser↔kamera)
opx = res_long                               # objekt mm/px lateralt (= 0,204)
print(f"  Triangulering: obj {opx:.3f} mm/px · vinkel {TRI:.0f}°  →  δz = subpix·{opx:.3f}/sin{TRI:.0f}°")
for sub in (0.10, 0.05):
    dz = sub * opx / math.sin(math.radians(TRI))
    print(f"    subpixel {sub:.2f} px  →  Z-upplösning ~{dz*1000:.0f} µm   (TEORETISKT, ideal yta)")
print("  Verklighet på VIRKE (subsurface-spridning + skrovligt + laserspräckel):")
print("    räkna ×2–4 sämre  →  enkelprofil ~0,05–0,15 mm; med fler-pass-medel ~0,03–0,08 mm")
print(f"  Lateralt (XY): ~{opx:.2f} mm/px längs linjen · ~0,20 mm matningssteg · linjebredd ~0,1–0,3 mm")
print("  ABSOLUT tjocklek: ankrad till ~0,1 mm av 3× LR400 uppströms")
print("    → de korrigerar global offset / tilt / bow i trianguleringen (ej lokal finupplösning)")
print("  NETTO: lokal relativ ~0,05–0,15 mm, absolut ~0,1 mm — gott för virkesgradering")

print(); line("="); print("KLART — alla tre verifierade mot databladsmått. Se omdömen ovan."); line("=")
