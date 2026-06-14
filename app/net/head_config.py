"""Läshuvudets position (``data/head.json``) — vilken del av brädan huvudet täcker.

Vid flera Jetson-läshuvuden täcker varje sin sektion av brädan. Positionen lagras på
SLAVEN (följer med det fysiska huvudet, överlever auto-discovery) men kan redigeras
från master-GUI:t (kommando ``set_position`` → slaven sparar här).

  * ``label``    — människonamn på sektionen (t.ex. "Vänster", "Mitten 1").
  * ``start_mm`` / ``end_mm`` — täckning längs brädan (matnings-/längdaxeln).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path("data/head.json")
DEFAULTS = {"label": "", "start_mm": 0.0, "end_mm": 0.0}


def load(path: str | Path = DEFAULT_PATH) -> dict:
    cfg = dict(DEFAULTS)
    try:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                cfg.update({k: data[k] for k in cfg if k in data})
        cfg["start_mm"] = float(cfg["start_mm"]); cfg["end_mm"] = float(cfg["end_mm"])
        cfg["label"] = str(cfg["label"])
    except Exception as exc:
        print(f"[head.json] kunde inte läsas ({exc}) — använder defaults")
    return cfg


def save(cfg: dict, path: str | Path = DEFAULT_PATH) -> dict:
    out = dict(DEFAULTS)
    out.update({"label": str(cfg.get("label", "")),
                "start_mm": float(cfg.get("start_mm", 0.0)),
                "end_mm": float(cfg.get("end_mm", 0.0))})
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out
