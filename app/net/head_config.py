"""Läshuvudets nod-config (``data/head.json``) — position + roll i den delade riggen.

VIKTIGT: vid flera Jetson-läshuvuden delar de **EN** encoder + **EN** motordrivare
(RoboClaw) — de är INTE separata per huvud. Exakt ETT huvud äger conveyorn/encodern
(``has_conveyor=true``, "lead"); övriga är ren-sensor-huvuden som får matnings-
positionen från lead (samma encoder-koordinat → fusion kan sy ihop hela brädan).

Fält:
  * ``label``        — sektionens namn (t.ex. "Vänster").
  * ``start_mm`` / ``end_mm`` — vilken del av brädan huvudet täcker.
  * ``has_conveyor`` — äger detta huvud RoboClaw/encodern? (default True; sätt False
                       på sensor-huvuden — de bygger då ingen egen RoboClaw).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path("data/head.json")
DEFAULTS = {"label": "", "start_mm": 0.0, "end_mm": 0.0, "has_conveyor": True}


def load(path: str | Path = DEFAULT_PATH) -> dict:
    cfg = dict(DEFAULTS)
    try:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                cfg.update({k: data[k] for k in cfg if k in data})
        cfg["start_mm"] = float(cfg["start_mm"]); cfg["end_mm"] = float(cfg["end_mm"])
        cfg["label"] = str(cfg["label"]); cfg["has_conveyor"] = bool(cfg["has_conveyor"])
    except Exception as exc:
        print(f"[head.json] kunde inte läsas ({exc}) — använder defaults")
    return cfg


def save(cfg: dict, path: str | Path = DEFAULT_PATH) -> dict:
    cur = load(path)                          # bevara fält som inte skickas med
    cur.update({k: cfg[k] for k in DEFAULTS if k in cfg})
    out = {"label": str(cur["label"]), "start_mm": float(cur["start_mm"]),
           "end_mm": float(cur["end_mm"]), "has_conveyor": bool(cur["has_conveyor"])}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out
