#!/usr/bin/env python3
"""Skanna en LR400:s Modbus-register för att hitta avstånds-registret vid idrifttagning.

Register-kartan är sensor-specifik. Ställ ett känt mål framför LR400:n (t.ex. 100,0 mm),
kör detta och leta upp registret vars värde × skala ≈ 100,00 (eller 10000 om skala 0,01).
Skriv sedan reg_addr/reg_kind/scale i data/lr400.json (se app/hal/real/lr400_config.py).

    python tools/lr400_scan.py --port /dev/ttyUSB0 --unit 1
    python tools/lr400_scan.py --port /dev/ttyUSB0 --unit 1 --kind input --count 32
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--unit", type=int, default=1, help="Modbus slav-adress")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--kind", choices=["holding", "input", "both"], default="both")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=16)
    args = ap.parse_args()

    try:
        from pymodbus.client import ModbusSerialClient
    except Exception as exc:
        print(f"pymodbus saknas ({exc}) — kör bootstrap först."); return 1

    client = ModbusSerialClient(port=args.port, baudrate=args.baud, parity="N",
                                stopbits=1, bytesize=8, timeout=0.2)
    if not client.connect():
        print(f"Kunde inte öppna {args.port}. Koppla in Waveshare 4CH / kontrollera port.")
        return 1
    kinds = ["holding", "input"] if args.kind == "both" else [args.kind]
    print(f"LR400 @ {args.port} unit={args.unit} — register {args.start}..{args.start+args.count-1}\n")
    try:
        for kind in kinds:
            print(f"== {kind} registers ==")
            for addr in range(args.start, args.start + args.count):
                try:
                    if kind == "input":
                        rr = client.read_input_registers(address=addr, count=1, slave=args.unit)
                    else:
                        rr = client.read_holding_registers(address=addr, count=1, slave=args.unit)
                    if rr is None or rr.isError() or not getattr(rr, "registers", None):
                        continue
                    raw = rr.registers[0]
                    print(f"  [{addr:3}] = {raw:6}   (×0,01={raw*0.01:8.2f}  ×0,1={raw*0.1:8.1f})")
                except Exception:
                    continue
            print()
        print("Leta upp registret vars skalade värde matchar din kända målsträcka.")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
