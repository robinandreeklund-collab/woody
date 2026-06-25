"""Persistent LR400-config + nollreferenser (``data/lr400.json``).

3× LR400 punktlaser läses över RS-485 Modbus via **Waveshare USB TO 4CH RS485**
(WCH CH9344, USB-id ``1a86:55d5``) → 4 SEPARATA serieportar. Chipet ger CDC-ACM,
dvs portarna heter ``/dev/ttyACM*`` (INTE ttyUSB). En RS485-buss per port; varje
LR400 sitter ensam på sin port → samma slav-adress (unit=1) men OLIKA ``port``.
Per-kanal ``port`` + ``unit`` täcker även en delad-buss-topologi om man hellre
kedjar dem. Två saker som varierar och hör hemma i fil:

  * **Port-mappning:** bind via stabil ``/dev/serial/by-id/…``-sökväg, INTE
    ``ttyACM0``-numret — RoboClawen enumererar också som ttyACM och kan förskjuta
    numreringen. CH9344:s fyra kanaler = interface ``if00/if02/if04/if06``.
  * **Register-karta:** vilket Modbus-register som håller avståndet + skala är
    sensor-specifikt (verifiera mot LR400-databladet / ``tools/lr400_scan.py``).

``d0_mm`` (nollreferens mot tomt band) skrivs av kalibreringen ``lr400.zero_d0`` —
tjocklek = ``d0_mm − uppmätt avstånd``.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path("data/lr400.json")

# Säkra defaults: Waveshare 4CH ger 4 EGNA portar → en LR400 per port, unit=1.
# Bind via stabil by-id-sökväg (CH9344 if00/if02/if04). Serienr-delen i sökvägen
# (BD650CABCD) är unik per Waveshare-kort — verifierad mot riggen vid idrifttagning.
# Verifiera V/C/H↔kanal-ordningen vid idrifttagning. reg_addr/scale mot databladet.
_BYID = "/dev/serial/by-id/usb-WCH.CN_USB_Quad_Serial_BD650CABCD-if{:02d}"

def _ch(port: str) -> dict:
    return {"port": port, "unit": 1, "baud": 9600,
            # Verifierat mot riggens LR400 (2026-06-25): avstånd i HOLDING reg 1,
            # ×0,1 = mm (757 ⇄ 75,7 mm; 0 = inget mål i mätområdet). reg5 ≈ kvalitet.
            "reg_addr": 1, "reg_kind": "holding", "scale": 0.1,   # register → mm
            "d0_mm": 100.0}

DEFAULTS: dict = {"ch1": _ch(_BYID.format(0)), "ch2": _ch(_BYID.format(2)),
                  "ch3": _ch(_BYID.format(4))}


def load(path: str | Path = DEFAULT_PATH) -> dict:
    """Läs LR400-config (ch1–3). Saknad fil/fält → defaults. Kraschar aldrig."""
    cfg = {ch: dict(vals) for ch, vals in DEFAULTS.items()}
    try:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            for ch, vals in data.items():
                if ch in cfg and isinstance(vals, dict):
                    cfg[ch].update({k: v for k, v in vals.items() if k in cfg[ch]})
    except Exception as exc:
        print(f"[lr400.json] kunde inte läsas ({exc}) — använder defaults")
    return cfg


def save(cfg: dict, path: str | Path = DEFAULT_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def set_d0(channel: str, d0_mm: float, path: str | Path = DEFAULT_PATH) -> None:
    """Uppdatera nollreferensen för en kanal (kalibrering zero_d0) och persistera."""
    cfg = load(path)
    if channel in cfg:
        cfg[channel]["d0_mm"] = float(d0_mm)
        save(cfg, path)
