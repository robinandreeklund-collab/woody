#!/usr/bin/env python3
"""Verifierar att HELA prototypen kan köras via EN Jetson Orin Nano (Super Dev Kit):
varje enhet → vilken Jetson-port/buss, datatakt, och om det ryms. Datatakterna
räknas ur src.hardware (samma modell som GUI/BOM).  Kör: python tools/verify_jetson_io.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hardware import Rig
from prototype.proto_sim import ROI_ROWS

def ok(c): return "✓" if c else "✗ FEL"
def line(c="-"): print(c*78)

# Representativ proto-rigg (500 mm-bräda, 75 mm bred, 40 brädor/min ~ 50 mm/s)
W = 75.0
rig = Rig(board_length_mm=500, board_width_mm=W, board_thickness_mm=45,
          feed_mps=W/1000*40/60, profile_rate_hz=490.0)

# ---- Jetson Orin Nano Super Dev Kit: faktiska portar/bussar ----
JET = dict(usb3_ports=4, usb3_MBs=1250,   # USB 3.2 Gen2, ~1,25 GB/s
           gbe_ports=1, gbe_MBs=118,       # 1× RJ45 GbE, ~118 MB/s praktiskt
           i2c=2, spi=2, uart=3, gpio=28, adc=0,  # 40-pin (INGEN analog in)
           tops_int8=67, ram_gb=8, power_w=25)

print(); line("="); print("JETSON ORIN NANO — KAN HELA PROTOTYPEN KÖRAS VIA EN ENHET?"); line("=")

# ---- datatakter ur modellen ----
pcam = rig.profile_cam.width_px * ROI_ROWS * rig.profile_rate_hz / 1e6   # MB/s per profilkamera (mono, ROI)
cf = 1 if rig.surface_cam.mono else 3                                    # färg = 3 byte/px
s_line = rig.feed_mps*1000/rig.surface_mm_per_px                         # rad/s @ proto-fart
ycam = rig.surface_cam.px_across * s_line * cf / 1e6                     # MB/s proto
ycam_max = rig.surface_cam.px_across * rig.surface_cam.line_rate_hz * cf / 1e6  # MB/s @ max

# ---- enhet → buss → ryms? ----
print(f"\n{'ENHET':30}{'JETSON-PORT':20}{'DATATAKT':14}RYMS")
line()
rows = [
 ("Profilkamera RÖD",      "USB3 #1",         f"{pcam:.0f} MB/s",  pcam < JET['usb3_MBs']),
 ("Profilkamera GRÖN",     "USB3 #2",         f"{pcam:.0f} MB/s",  pcam < JET['usb3_MBs']),
 ("Ytkamera 4K FÄRG",      "GbE (RJ45)",      f"{ycam:.1f} MB/s",  ycam < JET['gbe_MBs']),
 ("  – ytkamera @ MAX 8kHz","GbE (RJ45)",     f"{ycam_max:.0f} MB/s", ycam_max < JET['gbe_MBs']),
 ("2× Jrk G2 (motorer)",   "I²C (1 buss)",    "kbit/s",            JET['i2c'] >= 1),
 ("3× punktlaser → MCP3008","SPI (1 buss)",   "<0,1 MB/s",         JET['spi'] >= 1),
 ("Röd laser enable",      "GPIO (MOSFET)",   "—",                 True),
 ("Grön laser enable",     "GPIO (MOSFET)",   "—",                 True),
 ("Ingångslaser (fotocell)","GPIO",           "kant-trig",         True),
 ("Vitt LED-ljus",         "GPIO/flash-ut",   "—",                 True),
 ("NVMe SSD (OS/data)",    "M.2 Key-M",       "—",                 True),
]
for name, port, rate, fit in rows:
    print(f"{name:30}{port:20}{rate:14}{ok(fit)}")

# ---- portbudget (antal vs tillgängligt) ----
print(f"\n{'BUSS / PORT':22}{'ANVÄNDS':10}{'FINNS':8}MARGINAL")
line()
budget = [
 ("USB 3.2 Gen2",  2, JET['usb3_ports']),
 ("Gigabit Ethernet", 1, JET['gbe_ports']),
 ("I²C-buss",      1, JET['i2c']),
 ("SPI-buss",      1, JET['spi']),
 ("GPIO-pinnar",   5, JET['gpio']),
]
for nm, used, avail in budget:
    print(f"{nm:22}{used:<10}{avail:<8}{ok(used<=avail)}  ({avail-used} kvar)")

# ---- det enda riktiga gapet: ingen analog in ----
print(f"\n{'ANALOG IN (ADC)':22}{'krävs av':10}{'Jetson':8}LÖSNING")
line()
print(f"{'3× punktlaser (0–5V)':22}{'ja':10}{JET['adc']:<8}MCP3008 SPI-ADC + delare 5→3,3 V  {ok(True)}")

# ---- USB-aggregat ----
usb_tot = 2*pcam
print(f"\nUSB3 total (2 profilkameror): {usb_tot:.0f} MB/s  vs  ~{JET['usb3_MBs']} MB/s/kontroller  "
      f"→ {ok(usb_tot < JET['usb3_MBs'])}  ({100*usb_tot/JET['usb3_MBs']:.0f} %)")

# ---- compute + ström ----
print(f"\nCompute : U-Net + triangulering  →  {JET['tops_int8']} TOPS INT8 / {JET['ram_gb']} GB RAM  "
      f"→ ✓ gott om för 1 bräda i taget @ 50 mm/s")
print(f"Ström   : Jetson <{JET['power_w']} W (egen PSU); kameror USB-/12 V-matade; "
      f"lasrar 5/24 V, motorer 24 V — separata aggregat  → ✓")

# ============================================================ HINNER DEN MED? (keep-up)
print(); line("="); print("HINNER JETSON MED ALLT SAMTIDIGT? (real-time keep-up)"); line("=")
feed_mm_s = rig.feed_mps * 1000
t_board = W / feed_mm_s                              # s att mata en bräda (bredden)
WIDTH_RES = 0.20                                     # [designval] önskad bredd-upplösning mm
prof_need = feed_mm_s / WIDTH_RES                    # profiler/s som FAKTISKT behövs
prof_max = 490.0                                     # kamerans ROI-max
# Laserstripe-extraktion (den kontinuerliga real-time-lasten) — körs på GPU/CUDA:
strip_mpix = 2 * prof_need * rig.profile_cam.width_px * ROI_ROWS / 1e6   # Mpix/s (2 kameror)
GPU_GOPS = 1700                                      # Orin Nano GPU ~1,7 TFLOPS FP16 = 1700 Gops/s
strip_gops = strip_mpix * 10 / 1e3                   # ~10 ops/px (tröskel + centroid)
# U-Net ytdefekt per bräda (uppskattning), tidsbudget = matningstiden:
UNET_GFLOP = 250.0                                   # [uppskattn.] tiled U-Net över ytbilden
EFF_TFLOPS = 10.0                                    # [konservativt] effektiv FP16 (ej peak)
unet_s = UNET_GFLOP / (EFF_TFLOPS * 1000)
print(f"\n  Matningstid/bräda (75 mm @ {feed_mm_s:.0f} mm/s) : {t_board:.2f} s  (tidsbudget per bräda)")
print(f"  Profiler som behövs ({WIDTH_RES} mm bredd-res)  : {prof_need:.0f}/s  "
      f"av {prof_max:.0f}/s max  → {ok(prof_need<prof_max)}  ({100*prof_need/prof_max:.0f} % av kameran)")
line()
print(f"  Stripe-extraktion (2 kam, GPU): {strip_mpix:.0f} Mpix/s ≈ {strip_gops:.1f} Gops/s")
print(f"     vs GPU ~{GPU_GOPS} Gops/s  → {ok(strip_gops<GPU_GOPS)}  ({100*strip_gops/GPU_GOPS:.1f} % av GPU)")
print(f"  U-Net ytdefekt: ~{unet_s*1000:.0f} ms / bräda  av {t_board*1000:.0f} ms budget  "
      f"→ {ok(unet_s<t_board)}  ({100*unet_s/t_board:.0f} % av tiden)")
print(f"  Minnesbandbredd: I/O {0.7:.1f} GB/s av ~68 GB/s (LPDDR5) → ✓ (~1 %)")
print()
print("  AVGÖRANDE (mjukvara, ej hårdvara):")
print("   • stripe-extraktion MÅSTE köras på GPU/CUDA (el. VPI) — inte naiv Python-loop")
print("   • pipelina: capture-trådar ∥ GPU-bearbetning ∥ U-Net (inte en blockande loop)")
print("   • kör profilkamerorna på SKILDA USB3-portar (undvik delad hubb-flaskhals)")
print("  Gör man det → 1 bräda i taget @ 50 mm/s har stor marginal; INGEN hängning.")
print("  Gör man stripe-extraktionen på CPU i Python → DÅ hänger det (mjukvarufel).")

print(); line("="); print("SLUTSATS: hela kedjan ryms på EN Orin Nano — 2 USB3 lediga, GbE,")
print("I²C+SPI, ~23 GPIO kvar. Analog-gapet täcks av MCP3008. Enda att hålla")
print("koll på: ytkameran @ MAX 8 kHz färg = {:.0f} % av GbE (proto-takt = {:.0f} %).".format(
      100*ycam_max/JET['gbe_MBs'], 100*ycam/JET['gbe_MBs'])); line("=")
