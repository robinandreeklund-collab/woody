#!/usr/bin/env python3
"""Lista en ANSLUTEN GenICam-kameras alla features (namn + aktuellt värde).

Används för att mappa appens inställningar/kalibrering mot kamerans EXAKTA
nodnamn — de varierar per modell, så defaults i app/hal/real/cameras.py
(SFNC-standardnamn) kan behöva tonas mot vad just denna kamera exponerar.

Kräver MVS- eller Aravis-GenTL-producent (sätt GENICAM_GENTL64_PATH) + inkopplad
kamera. Profilkameror = USB3, linjekameran = GigE (kontrollera IP/subnät först).

    python tools/dump_camera_features.py                 # första kameran, alla features
    python tools/dump_camera_features.py --serial 1234   # specifik kamera
    python tools/dump_camera_features.py --grep trigger  # bara matchande namn
    python tools/dump_camera_features.py --list          # lista hittade kameror
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.hal.real.cameras import _harvester, dump_genicam_features  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", help="kamera-serienummer (annars första)")
    ap.add_argument("--grep", help="filtrera feature-namn (skiftlägesokänsligt)")
    ap.add_argument("--trigger", action="store_true",
                    help="förinställt filter: trigger/encoder/line/acquisition + enum-värden")
    ap.add_argument("--enum", action="store_true",
                    help="visa tillåtna enum-värden per nod (för att mappa trigger/encoder)")
    ap.add_argument("--list", action="store_true", help="lista bara hittade kameror")
    ap.add_argument("--json", action="store_true",
                    help="skriv ut data/cameras.json-skelett (roll→serienr) från hittade kameror")
    args = ap.parse_args()

    h = _harvester()
    devs = h.device_info_list
    if not devs:
        print("Ingen kamera hittad. Koppla in + sätt GENICAM_GENTL64_PATH "
              "(MVS) eller installera Aravis. För GigE: kontrollera IP/subnät.")
        return 1

    if args.json:                       # skelett att spara som data/cameras.json
        import json
        from app.hal.real import camera_config
        serials = [str(getattr(d, "serial_number", "")) for d in devs]
        print(json.dumps(camera_config.skeleton(serials), indent=2, ensure_ascii=False))
        return 0

    print(f"Hittade {len(devs)} kamera(or):")
    for d in devs:
        print(f"  · {getattr(d, 'model', '?')}  serienr={getattr(d, 'serial_number', '?')}")
    if args.list:
        return 0

    kw = {"serial_number": args.serial} if args.serial else {}
    ia = h.create(search_key=kw or None)
    nm = ia.remote_device.node_map
    # --trigger: visa allt som rör encoder-triggad line-scan + enum-värden
    trig_terms = ("trigger", "encoder", "line", "acquisition", "rotaryenc")
    show_enum = args.enum or args.trigger
    try:
        rows = dump_genicam_features(nm)
        g = (args.grep or "").lower()
        shown = 0
        print()
        for name, val in rows:
            low = name.lower()
            if g and g not in low:
                continue
            if args.trigger and not any(t in low for t in trig_terms):
                continue
            line = f"  {name:42} = {val!r}"
            if show_enum:                       # lista tillåtna värden för enum-noder
                try:
                    allowed = list(getattr(nm, name).symbolics)
                    if allowed:
                        line += f"   ∈ {allowed}"
                except Exception:
                    pass
            print(line)
            shown += 1
        flt = args.grep or ("trigger/encoder/line" if args.trigger else None)
        print(f"\n{shown}/{len(rows)} features" + (f' (filter: {flt!r})' if flt else ''))
    finally:
        ia.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
