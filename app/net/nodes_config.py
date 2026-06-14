"""Nodlista för mastern (``data/nodes.json``) — varje Jetson (läshuvud) du ansluter till.

Format:
    [
      {"name": "RÖD-huvud",  "host": "100.64.0.11", "port": 8765},
      {"name": "GRÖN-huvud", "host": "woody-gron.local", "port": 8765}
    ]
``host`` = IP eller hostname (LAN eller Tailscale). Saknas filen → tom lista (lägg
till noder i master-GUI:t eller skapa filen).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path("data/nodes.json")


def load(path: str | Path = DEFAULT_PATH) -> list[dict]:
    try:
        p = Path(path)
        if not p.exists():
            return []
        data = json.loads(p.read_text())
        out = []
        for n in data if isinstance(data, list) else []:
            if isinstance(n, dict) and n.get("host"):
                out.append({"name": str(n.get("name") or n["host"]),
                            "host": str(n["host"]), "port": int(n.get("port", 8765))})
        return out
    except Exception as exc:
        print(f"[nodes.json] kunde inte läsas ({exc}) — tom nodlista")
        return []


def save(nodes: list[dict], path: str | Path = DEFAULT_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(nodes, indent=2, ensure_ascii=False))
