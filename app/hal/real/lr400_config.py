"""Persistent LR400-config + nollreferenser (``data/lr400.json``).

3× LR400 punktlaser läses över RS-485 Modbus via **Waveshare USB TO 4CH RS485**
(industriell, FT4232-baserad) → 4 SEPARATA serieportar (`/dev/ttyUSB0..3`), en
RS485-buss per port. Varje LR400 sitter ensam på sin port, så samma slav-adress
(unit=1) men OLIKA ``port``. Per-kanal ``port`` + ``unit`` täcker även en delad-buss-
topologi om man hellre kedjar dem. Två saker som varierar och hör hemma i fil:

  * **Port-mappning:** vilken fysisk RS485-1/2/3 → vilken ttyUSB (ordningen kan
    behöva verifieras; FT4232 ger stabila men inte alltid 1:1-numrerade portar).
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
# Verifiera port↔kanal-ordningen vid idrifttagning. reg_addr/scale mot databladet.
def _ch(port: str) -> dict:
    return {"port": port, "unit": 1, "baud": 9600,
            "reg_addr": 0, "reg_kind": "holding", "scale": 0.01,  # register → mm
            "d0_mm": 100.0}

DEFAULTS: dict = {"ch1": _ch("/dev/ttyUSB0"), "ch2": _ch("/dev/ttyUSB1"),
                  "ch3": _ch("/dev/ttyUSB2")}


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
