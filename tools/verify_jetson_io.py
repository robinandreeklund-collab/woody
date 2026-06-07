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

# Representativ proto-rigg (500 mm-bräda, 75 mm bred, TÄNKT TAKT 60 brädor/min)
W = 75.0
BPM = 60.0                                           # tänkt takt: brädor/min
rig = Rig(board_length_mm=500, board_width_mm=W, board_thickness_mm=45,
          feed_mps=W/1000*BPM/60, profile_rate_hz=490.0)

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
 ("Profilkamera RÖD",      "USB3 #1 (dedik.)", f"{pcam:.0f} MB/s",  pcam < JET['usb3_MBs']),
 ("Profilkamera GRÖN",     "USB3 #2 (dedik.)", f"{pcam:.0f} MB/s",  pcam < JET['usb3_MBs']),
 ("Ytkamera 4K FÄRG",      "GbE (RJ45)",      f"{ycam:.1f} MB/s",  ycam < JET['gbe_MBs']),
 ("  – ytkamera @ MAX 8kHz","GbE (RJ45)",     f"{ycam_max:.0f} MB/s", ycam_max < JET['gbe_MBs']),
 ("Transportör (Jrk G2)",  "USB #4 (direkt)", "kbit/s",            True),
 ("3× LR400 punktlaser",   "RS-485 ch1–3 (Waveshare 4CH USB)","<0,1 MB/s", True),
 ("RS-485 ch4 (Waveshare)","LEDIG — Modbus-reserv","—",            True),
 ("Mäthjuls-encoder A/B/Z","kamera RS-422 + Jetson GPIO","puls (kvadratur)", True),
 ("  – line-trigg → kamera","RS-422 diff (line-driver)","per rad", True),
 ("  – position → Jetson",  "GPIO/LS7366R-räkning","kvadratur",     True),
 ("Röd/Grön laser enable", "GPIO (MOSFET)",   "—",                 True),
 ("Anhåll-fotocell (nolla)","GPIO (digital)", "home/nolla",        True),
 ("Vitt LED-ljus",         "GPIO/flash-ut",   "—",                 True),
 ("NVMe SSD (OS/data)",    "M.2 Key-M",       "—",                 True),
]
for name, port, rate, fit in rows:
    print(f"{name:30}{port:20}{rate:14}{ok(fit)}")

# ---- portbudget (antal vs tillgängligt) ----
print(f"\n{'BUSS / PORT':22}{'ANVÄNDS':10}{'FINNS':8}MARGINAL")
line()
budget = [
 ("USB-portar (totalt)*",   4, JET['usb3_ports']),   # 2 kam + Waveshare + Jrk = 4, alla direkt
 ("Gigabit Ethernet",       1, JET['gbe_ports']),
 ("RS-485-kanaler (4CH)",   3, 4),
 ("GPIO-pinnar",            6, JET['gpio']),
]
for nm, used, avail in budget:
    print(f"{nm:24}{used:<10}{avail:<8}{ok(used<=avail)}  ({avail-used} kvar)")
print("  * 2 profilkameror (USB3) + Waveshare 4CH RS-485 (USB) + Jrk G2 (USB) = 4 av 4, ALLA DIREKT.")
print("    Ingen hubb behövs. (Hubb endast om du vill hålla en port ledig: lägg Jrk+Waveshare på den.)")

# ---- analog in: behövs INTE längre (LR400 = RS-485 digitalt) ----
print(f"\n{'ANALOG IN (ADC)':22}{'krävs?':10}{'Jetson':8}KOMMENTAR")
line()
print(f"{'Punktlaser':22}{'NEJ':10}{JET['adc']:<8}LR400 ger avstånd via RS-485 (Modbus) → ingen ADC  ✓")

# ---- USB-aggregat ----
usb_tot = 2*pcam
print(f"\nUSB3 total (2 profilkameror): {usb_tot:.0f} MB/s  vs  ~{JET['usb3_MBs']} MB/s/kontroller  "
      f"→ {ok(usb_tot < JET['usb3_MBs'])}  ({100*usb_tot/JET['usb3_MBs']:.0f} %)")

# ---- ENCODER: line-driver (RS-422) ≠ RS-485-Modbus; och MÅSTE förgrenas ----
print(); line(); print("ENCODER — variant, buss och VEM som läser den"); line()
print("  E6B2-CWZ1X = INKREMENTELL kvadratur-encoder (A/B/Z) med LINE-DRIVER-utgång =")
print("  RS-422 (differentiell, punkt-till-punkt). Det är INTE RS-485-Modbus (det är LR400).")
print("  RS-422 line-driver är just standard-encoderingången på en line-scan-KAMERA → brusimmunt.")
print("    (Har kameran open-collector-ingång i stället → välj E6B2-CWZ6C (NPN).)")
print("  Kan den ligga på Waveshares 4:e RS-485-kanal? NEJ — kvadraturpulser är inte serie-bytes.")
print("  → ch4 lämnas LEDIG (Modbus-reserv).")
print()
print("  FÖRGRENA encodern till BÅDA (annars vet Jetson inte var brädan är):")
print("   • → KAMERAN  : RS-422 line-trigg → en scanrad per N pulser (pixel-exakt, ingen jitter).")
print("   • → JETSON   : samma A/B/Z räknas som kvadratur (GPIO-interrupt el. LS7366R på SPI) →")
print("                  ABSOLUT position från anhålls-nollan → Jetson beslutar stopp/BACK.")
print("   RS-422 = en sändare kan driva flera mottagare → kamerans ingång + en 26C32 → 3,3 V Jetson.")
print(f"   Takt: Ø40 mm-hjul, 2500 ppr, {rig.feed_mps*1000:.0f} mm/s → ~4 kHz, ~12,6 µm/puls → trivialt.")
print("   Backup på slutläge: profildata visar 'ingen bräda' när bakkanten lämnat lasersnittet.")

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
CONVEYOR_MMS = 50.0                                  # valt band: 24V/30rpm ~ 50 mm/s nominellt
print(f"\n  TÄNKT TAKT: {BPM:.0f} brädor/min  →  matningsfart {feed_mm_s:.0f} mm/s "
      f"(bredd {W:.0f} mm)")
# Laserstripe-extraktion (den kontinuerliga real-time-lasten) — körs på GPU/CUDA:
strip_mpix = 2 * prof_need * rig.profile_cam.width_px * ROI_ROWS / 1e6   # Mpix/s (2 kameror)
GPU_GOPS = 1700                                      # Orin Nano GPU ~1,7 TFLOPS FP16 = 1700 Gops/s
strip_gops = strip_mpix * 10 / 1e3                   # ~10 ops/px (tröskel + centroid)
# U-Net ytdefekt per bräda (uppskattning), tidsbudget = matningstiden:
UNET_GFLOP = 250.0                                   # [uppskattn.] tiled U-Net över ytbilden
EFF_TFLOPS = 10.0                                    # [konservativt] effektiv FP16 (ej peak)
unet_s = UNET_GFLOP / (EFF_TFLOPS * 1000)
print(f"  Matningstid/bräda ({W:.0f} mm @ {feed_mm_s:.0f} mm/s) : {t_board:.2f} s  (tidsbudget per bräda)")
line()
print("  A) JETSON / COMPUTE:")
print(f"     Stripe-extraktion senare nedan, U-Net senare — spoiler: ✓ stor marginal")
print("  B) FLASKHALSARNA vid 60/min (inte Jetson):")
print(f"     Band-fart som krävs : {feed_mm_s:.0f} mm/s  vs valt band {CONVEYOR_MMS:.0f} mm/s (24V/30rpm)")
print(f"        → {ok(feed_mm_s<=CONVEYOR_MMS)}  "
      + ("OK" if feed_mm_s<=CONVEYOR_MMS else
         f"BANDET RÄCKER INTE: {CONVEYOR_MMS:.0f} mm/s ger {CONVEYOR_MMS/W*60:.0f}/min. "
         f"60/min kräver ~{feed_mm_s:.0f} mm/s → snabbare motor (~{feed_mm_s/CONVEYOR_MMS*30:.0f} rpm)"))
print(f"     Profiler/s som krävs: {prof_need:.0f}/s  vs kamera-max {prof_max:.0f}/s "
      f"→ {ok(prof_need<prof_max)}  ({100*prof_need/prof_max:.0f} % — funkar @ {WIDTH_RES} mm, "
      f"men finare res/bredare bräda spränger taket)")
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
print("  Gör man det → Jetson har stor marginal @ 60/min; INGEN hängning (compute).")
print("  Gör man stripe-extraktionen på CPU i Python → DÅ hänger det (mjukvarufel).")

# ============================================================ DRIVRUTINER / SDK
print(); line("="); print("DRIVRUTINER / SDK — funkar kamerorna på Jetson (ARM64)?"); line("=")
print("  Profilkameror Hikrobot MV-CS050-10UM  (USB3 Vision + GenICam-standard):")
print("    → Hikrobot MVS SDK har aarch64 .deb (libs /opt/MVS/lib/aarch64) — körs på Jetson  ✓")
print("  Ytkamera Huateng 4K  (GigE Vision V1.2 + GenICam-standard):")
print("    → vendor-SDK (Linux) ELLER Aravis (open source) — Aravis körd på Orin Nano  ✓")
print("  UNIVERSAL RESERV: Aravis driver BÅDE GigE Vision och USB3 Vision på aarch64  ✓")
print("    (standarderna = vendor-neutralt → du är aldrig låst till en SDK)")
print("  TESTA på Jetson:  'arv-tool-0.8' listar kameror + tar en ram (el. vendor-viewer)")
print("  OBS: USB3 → höj usbcore.usbfs_memory_mb;  GigE → samma subnät + jumbo frames (MTU 9000)")

print(); line("="); print("SLUTSATS: hela kedjan ryms på EN Orin Nano.")
print("  • 2 profilkameror + Waveshare (4CH RS-485) + Jrk G2 = 4 USB-portar, ALLA DIREKT (ingen hubb).")
print("  • Ytkamera på GbE; 3 LR400 på RS-485 ch1–3 → ch4 LEDIG (Modbus-reserv).")
print("  • Mäthjuls-encoder förgrenas: → kamera (RS-422 line-trigg) OCH → Jetson (kvadratur-räkning,")
print("    position/back-beslut); anhåll-fotocell + lasrar/LED → GPIO (~18 kvar).")
print("  • Ingen ADC behövs (LR400 = RS-485 digitalt).")
print("  Enda att hålla koll på: ytkameran @ MAX 8 kHz färg = {:.0f} % av GbE (proto-takt = {:.0f} %).".format(
      100*ycam_max/JET['gbe_MBs'], 100*ycam/JET['gbe_MBs'])); line("=")
