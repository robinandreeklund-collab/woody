"""Persistent kamera-identitet + inställningar (``data/cameras.json``).

Med TVÅ identiska profilkameror (Hikrobot MV-CS050-10UM) MÅSTE varje huvud bindas
till sitt **serienummer** — annars kan RÖD/GRÖN förväxlas mellan körningar och
trianguleringen blir fel. Serienummer = hårdvaru-identitet → hör hemma i en sparad
fil, inte i CLI-flaggor. Den här modulen läser/skriver den filen med säkra defaults
så appen funkar även om filen saknas (då används första bästa kamera per roll).

Skapa/uppdatera filen vid idrifttagning:
    python tools/dump_camera_features.py --json > data/cameras.json   # skelett
sen fyll i vilket serienummer som är RÖD resp. GRÖN (BP650 = röd, BP525 = grön).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path("data/cameras.json")

# Säkra defaults per roll (serial=None → första bästa kamera; sätt vid idrifttagning).
DEFAULTS: dict = {
    "profile_red": {
        "serial": None, "exposure_us": 800.0, "roi_rows": 80,
        "roi_offset_y": None, "frame_rate_hz": 60.0,
    },
    "profile_green": {
        "serial": None, "exposure_us": 800.0, "roi_rows": 80,
        "roi_offset_y": None, "frame_rate_hz": 60.0,
    },
    "surface": {
        "serial": None, "divider": 1, "multiplier": 1, "direction": "forward",
        "line_rate_hz": None,
    },
}


def load(path: str | Path = DEFAULT_PATH) -> dict:
    """Läs kamera-config (roll → inställningar). Saknad fil/fält → defaults. Kraschar aldrig."""
    cfg = {role: dict(vals) for role, vals in DEFAULTS.items()}
    try:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            for role, vals in data.items():
                if role in cfg and isinstance(vals, dict):
                    cfg[role].update({k: v for k, v in vals.items() if k in cfg[role]})
    except Exception as exc:                       # trasig fil får aldrig stoppa drift
        print(f"[cameras.json] kunde inte läsas ({exc}) — använder defaults")
    return cfg


def save(cfg: dict, path: str | Path = DEFAULT_PATH) -> None:
    """Skriv kamera-config (skapar data/ vid behov)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def skeleton(found_serials: list[str] | None = None) -> dict:
    """Bygg en cameras.json-skelett; om serienummer hittats, förslå dem (RÖD=första)."""
    cfg = {role: dict(vals) for role, vals in DEFAULTS.items()}
    serials = list(found_serials or [])
    # Förslag: 2 profilkameror + 1 yt — fyll i ordning, människan bekräftar färg.
    if len(serials) >= 1:
        cfg["profile_red"]["serial"] = serials[0]
    if len(serials) >= 2:
        cfg["profile_green"]["serial"] = serials[1]
    if len(serials) >= 3:
        cfg["surface"]["serial"] = serials[2]
    return cfg
