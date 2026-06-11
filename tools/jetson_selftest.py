#!/usr/bin/env python3
"""Jetson-självtest — probar varje fältenhet och skriver en anslutningsrapport.

Kör efter att du kopplat in en (eller alla) enheter:
    python tools/jetson_selftest.py

Designad för att vara SNÄLL utan hårdvara: saknas en enhet/SDK rapporteras
"EJ ANSLUTEN — <orsak>" istället för att krascha. När en enhet pluggas in ska
raden bli grön ("ANSLUTEN"). Detta är verktyget man kör vid plug-in-fasen
(se docs/jetson-prep-plan.md §5 Fas C).

Probar:
  * Jetson-plattform (modell, JetPack/L4T, ström-läge)
  * GenICam-kameror (Hikrobot profil ×2 + linjekamera) via Aravis och/eller MVS
  * RoboClaw 2x7A (USB packet serial) — port + firmware
  * GPIO (laser-enable, LED, fotocell) — biblioteks-/header-närvaro
  * Real-HAL connect_report() (appens egen enhetsbild)
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

G, R, Y, B, X = "\033[1;32m", "\033[1;31m", "\033[1;33m", "\033[1;36m", "\033[0m"


def ok(label, msg=""):  print(f"  {G}● ANSLUTEN{X}   {label}" + (f"  — {msg}" if msg else ""))
def no(label, msg=""):  print(f"  {R}○ EJ ANSL.{X}   {label}" + (f"  — {msg}" if msg else ""))
def info(label, msg=""): print(f"  {Y}· {X}{label}" + (f"  — {msg}" if msg else ""))
def head(t):            print(f"\n{B}━━ {t} {'━' * max(2, 40 - len(t))}{X}")


# ----------------------------------------------------------------- 1. plattform
def probe_platform():
    head("1. Jetson-plattform")
    model = Path("/proc/device-tree/model")
    if model.exists():
        ok("Modell", model.read_text(errors="ignore").strip("\x00"))
    else:
        no("Modell", "ej en Jetson (saknar device-tree/model)")
    for f, lbl in [("/etc/nv_tegra_release", "L4T/JetPack"),
                   ("/sys/devices/virtual/dmi/id/product_name", "produkt")]:
        p = Path(f)
        if p.exists():
            info(lbl, p.read_text(errors="ignore").splitlines()[0][:80])
    import shutil
    if shutil.which("nvpmodel"):
        info("nvpmodel", "tillgänglig (sätt -m 0 = MAXN)")
    else:
        info("nvpmodel", "saknas (kör du inte på Jetson?)")


# ----------------------------------------------------------------- 2. kameror
def probe_cameras():
    head("2. Kameror (GenICam: profil ×2 USB3 + linjekamera GigE)")
    # 2a. Aravis (täcker både USB3 Vision och GigE Vision)
    try:
        import gi
        gi.require_version("Aravis", "0.8")
        from gi.repository import Aravis
        Aravis.update_device_list()
        n = Aravis.get_n_devices()
        if n:
            ok("Aravis", f"{n} GenICam-enhet(er):")
            for i in range(n):
                info("   →", f"{Aravis.get_device_id(i)}  [{Aravis.get_device_model(i)}]")
        else:
            no("Aravis", "0 kameror hittade (koppla in / kontrollera subnät & jumbo frames)")
    except Exception as exc:
        no("Aravis", f"ej redo — {exc}")

    # 2b. MVS GenTL via Harvester (profilkameror)
    cti = os.environ.get("GENICAM_CTI") or os.environ.get("GENICAM_GENTL64_PATH")
    if not cti:
        info("Harvester/MVS", "GENICAM_CTI / GENICAM_GENTL64_PATH ej satt (se bootstrap §6)")
    else:
        try:
            from harvesters.core import Harvester
            h = Harvester()
            for c in glob.glob(os.path.join(cti, "*.cti")) if os.path.isdir(cti) else [cti]:
                h.add_file(c)
            h.update()
            if h.device_info_list:
                ok("Harvester/MVS", f"{len(h.device_info_list)} enhet(er):")
                for d in h.device_info_list:
                    info("   →", getattr(d, "serial_number", "?"))
            else:
                no("Harvester/MVS", "GenTL laddad men 0 kameror")
            h.reset()
        except Exception as exc:
            no("Harvester/MVS", f"ej redo — {exc}")

    # 2c. rå USB-lista (ser vi Hikrobot på bussen alls?)
    import shutil, subprocess
    if shutil.which("lsusb"):
        try:
            out = subprocess.check_output(["lsusb"], text=True)
            hik = [l for l in out.splitlines() if "hik" in l.lower() or "2bdf" in l.lower()]
            (ok if hik else info)("lsusb", "; ".join(hik) if hik else "ingen Hikrobot-enhet på USB ännu")
        except Exception:
            pass


# ----------------------------------------------------------------- 3. RoboClaw
def probe_roboclaw():
    head("3. RoboClaw 2x7A (bandstyrning, USB packet serial)")
    ports = sorted(set(glob.glob("/dev/ttyACM*") + glob.glob("/dev/roboclaw")))
    if not ports:
        no("Port", "ingen /dev/ttyACM* (koppla in RoboClaw via USB)")
        return
    info("Portar", ", ".join(ports))
    try:
        from app.hal.real.roboclaw_conveyor import RoboClawConveyor
    except Exception as exc:
        no("RoboClaw-backend", f"importfel — {exc}")
        return
    for port in ports:
        rc = RoboClawConveyor(port=port)
        try:
            rc.open()
            ok("RoboClaw", f"{port} — {rc.info().model} ({rc.firmware()})")
            info("   position", f"{rc.position_mm():.1f} mm")
            rc.close()
            return
        except Exception as exc:
            no("RoboClaw", f"{port} svarade inte — {exc}")


# ----------------------------------------------------------------- 4. GPIO
def probe_gpio():
    head("4. GPIO (laser-enable röd/grön, LED, fotocell-in)")
    try:
        import Jetson.GPIO as GPIO  # noqa: F401
        ok("Jetson.GPIO", "bibliotek tillgängligt (40-pin header)")
        info("planerade pinnar", "RÖD-enable, GRÖN-enable, LED-enable (ut) · fotocell (in)")
    except Exception as exc:
        no("Jetson.GPIO", f"ej tillgängligt — {exc}")


# ----------------------------------------------------------------- 5. Real-HAL
def probe_hal():
    head("5. Real-HAL connect_report() (appens enhetsbild)")
    try:
        from app.hal.real.real_backends import RealScanner
        rep = RealScanner().connect_report()
        for name, connected, msg in rep:
            (ok if connected else no)(name, msg)
    except Exception as exc:
        no("RealScanner", f"kunde inte byggas — {exc}")


def main():
    print(f"{B}woody — Jetson självtest{X}  (snäll utan hårdvara; grönt = inkopplat)")
    for fn in (probe_platform, probe_cameras, probe_roboclaw, probe_gpio, probe_hal):
        try:
            fn()
        except Exception as exc:
            print(f"  {R}! {fn.__name__} kraschade: {exc}{X}")
    print(f"\n{B}Klart.{X} Grönt = ansluten. Koppla in enheter och kör igen.\n")


if __name__ == "__main__":
    main()
