"""JSON-lines-protokoll för master/slave (rent — inga Qt-beroenden, testbart).

Varje meddelande = ett JSON-objekt + ``\\n``. Tre former:
  * Begäran  (master→slave):  {"id": N, "cmd": "...", "args": {...}}
  * Svar     (slave→master):  {"id": N, "ok": true, "result": ...}
                              {"id": N, "ok": false, "error": "..."}
  * Event    (slave→master):  {"event": "...", "data": {...}}   (utan id, oombett)
"""
from __future__ import annotations

import json

# -- kommandon (master → slave) --
CMD_HELLO = "hello"                 # → {name, mode, version}
CMD_STATUS = "status"               # → aggregerad nodstatus
CMD_DEVICES = "devices"             # → DeviceManager.devices-listan
CMD_METHODS = "methods"            # args {dev} → methodsFor
CMD_START_CALIB = "start_calibration"   # args {dev, method} → bool
CMD_CANCEL_CALIB = "cancel_calibration"
CMD_CALIB_STATE = "calib_state"     # → pågående körnings pct/steg/logg/resultat
CMD_REFRESH = "refresh"             # proba om hårdvaran
CMD_SET_POSITION = "set_position"   # args {label, start_mm, end_mm} → huvudets sektion
CMD_ARM_LASERS = "arm_lasers"      # args {confirm} → bool (klass 3B interlock)
CMD_DISARM_LASERS = "disarm_lasers"

# -- event (slave → master, oombett) --
EV_DEVICES = "devices_changed"
EV_METHODS = "methods_changed"
EV_CALIB = "calib_changed"
EV_HELLO = "hello"                  # skickas när en klient ansluter
EV_TELEMETRY = "telemetry"          # host-stats (CPU/GPU/RAM/disk/temp) var ~2s


def encode(obj: dict) -> bytes:
    """Serialisera ett meddelande till en JSON-rad (bytes)."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def request(msg_id: int, cmd: str, args: dict | None = None) -> bytes:
    return encode({"id": msg_id, "cmd": cmd, "args": args or {}})


def response(msg_id: int, result=None, ok: bool = True, error: str = "") -> bytes:
    out = {"id": msg_id, "ok": ok}
    if ok:
        out["result"] = result
    else:
        out["error"] = error
    return encode(out)


def event(name: str, data=None) -> bytes:
    return encode({"event": name, "data": data if data is not None else {}})


class FrameBuffer:
    """Ackumulerar inkommande bytes och plockar ut hela JSON-rader.

    Tål delade paket (TCP) — ofullständiga rader sparas tills resten kommer.
    """

    def __init__(self):
        self._buf = b""

    def feed(self, data: bytes) -> list[dict]:
        """Lägg till bytes → returnera lista av färdiga, parsade meddelanden."""
        self._buf += data
        out: list[dict] = []
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line.decode("utf-8")))
            except Exception:
                continue            # hoppa trasig rad, fortsätt med resten
        return out
