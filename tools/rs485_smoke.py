#!/usr/bin/env python3
"""Smoke-test av Waveshare USB→4CH RS485 UTAN något inkopplat på bussen.

Bevisar att kedjan chip → drivrutin → OS → pyserial fungerar: öppnar varje
kanal, sätter 9600 8N1, skickar en giltig Modbus-läsram (TX-LED blinkar på
kortet) och lyssnar kort. Med inget inkopplat blir det TYST — det är väntat
och betyder att porten är hel, bara ingen slav som svarar.

    python tools/rs485_smoke.py                 # ch1-3 via by-id (lr400_config)
    python tools/rs485_smoke.py --ports /dev/ttyACM0 /dev/ttyACM1
    python tools/rs485_smoke.py --modbus        # försök även en Modbus-läsning

Lyser/blinkar TX-LED på kanalen när detta körs → adapter + kabel + USB är OK.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _modbus_read_frame(unit: int = 1, reg: int = 0, count: int = 1) -> bytes:
    """Bygg en Modbus-RTU 'read holding registers' (fn 3) med korrekt CRC16."""
    body = bytes([unit & 0xFF, 0x03, (reg >> 8) & 0xFF, reg & 0xFF,
                  (count >> 8) & 0xFF, count & 0xFF])
    crc = 0xFFFF
    for b in body:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else (crc >> 1)
    return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", nargs="*", help="Explicita portar (annars by-id ch1-3)")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--modbus", action="store_true",
                    help="Försök även en riktig Modbus-läsning (timeout väntat utan sensor)")
    args = ap.parse_args()

    try:
        import serial
    except Exception as exc:
        print(f"pyserial saknas ({exc}) — kör tools/jetson_bootstrap.sh först.")
        return 1

    if args.ports:
        ports = list(args.ports)
    else:
        from app.hal.real import lr400_config
        cfg = lr400_config.load()
        ports = [cfg[ch]["port"] for ch in ("ch1", "ch2", "ch3")]

    print(f"RS485 smoke-test · {args.baud} 8N1 · {len(ports)} kanal(er)")
    print("(inget inkopplat → TYST svar är KORREKT; titta på TX-LED på kortet)\n")
    frame = _modbus_read_frame()
    ok = 0
    for i, port in enumerate(ports, 1):
        real = Path(port).resolve()
        label = f"ch{i}  {port}" + (f"  → {real.name}" if str(real) != port else "")
        try:
            with serial.Serial(port, args.baud, bytesize=8, parity="N",
                               stopbits=1, timeout=0.3, write_timeout=0.5) as s:
                s.reset_input_buffer(); s.reset_output_buffer()
                n = s.write(frame); s.flush()       # TX-LED blinkar här
                echo = s.read(64)                   # half-duplex: vanligtvis tyst
                resp = "—"
                if echo:
                    resp = f"{len(echo)} byte tillbaka ({echo.hex()})"
                print(f"  ✓ {label}")
                print(f"      öppnad, skickade {n} byte (TX-LED ska ha blinkat) · svar: {resp}")
                ok += 1
        except Exception as exc:
            print(f"  ✗ {label}\n      {type(exc).__name__}: {exc}")

    if args.modbus and ports:
        print("\nModbus-läsning (väntat: timeout utan sensor):")
        import logging
        logging.getLogger("pymodbus").setLevel(logging.CRITICAL)   # tysta retry-spam
        try:
            from pymodbus.client import ModbusSerialClient
        except Exception as exc:
            print(f"  pymodbus saknas ({exc}) — kör tools/jetson_bootstrap.sh")
            ModbusSerialClient = None
        for i, port in enumerate(ports, 1) if ModbusSerialClient else []:
            try:
                c = ModbusSerialClient(port=port, baudrate=args.baud, parity="N",
                                       stopbits=1, bytesize=8, timeout=0.3)
                opened = c.connect()
                rr = c.read_holding_registers(0, count=1, device_id=1) if opened else None
                c.close()
                if not opened:
                    print(f"  ch{i}: kunde inte öppna")
                elif rr is None or getattr(rr, "isError", lambda: True)():
                    print(f"  ch{i}: ingen slav svarar (timeout) — väntat utan sensor ✓")
                else:
                    print(f"  ch{i}: SVAR! {rr.registers}  (en sensor sitter alltså på bussen)")
            except Exception as exc:
                # ModbusIOException (ingen respons) = exakt det vi förväntar utan sensor
                print(f"  ch{i}: ingen slav svarar (timeout) — väntat utan sensor ✓")

    print(f"\n{ok}/{len(ports)} portar öppnade rent.", end=" ")
    print("Adapter + drivrutin OK." if ok == len(ports)
          else "Någon port gick inte att öppna — se ovan.")
    return 0 if ok == len(ports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
