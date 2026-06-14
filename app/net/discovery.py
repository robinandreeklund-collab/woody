"""Auto-discovery på LAN via UDP-broadcast — master hittar slavar utan IP-pyssel.

Varje slave skickar regelbundet ett litet UDP-broadcast ("annons") med sitt namn +
TCP-port. Mastern lyssnar och lägger till noder automatiskt. Mastern läser avsändarens
IP ur datagrammet → slaven behöver inte veta sin egen adress.

Broadcast når bara det LOKALA subnätet — för Tailscale/andra subnät används den
manuella ``data/nodes.json`` (de två kompletterar varandra).
"""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QUdpSocket

DISCOVERY_PORT = 8766
MAGIC = "woody-disco-1"


def announce_packet(name: str, tcp_port: int, mode: str = "?") -> bytes:
    return json.dumps({"magic": MAGIC, "name": name, "port": int(tcp_port),
                       "mode": mode}, ensure_ascii=False).encode("utf-8")


def parse_announce(data: bytes, sender_host: str) -> dict | None:
    """Validera ett annons-datagram → {name, host, port, mode} eller None."""
    try:
        d = json.loads(bytes(data).decode("utf-8"))
        if d.get("magic") != MAGIC or not d.get("port"):
            return None
        return {"name": str(d.get("name") or sender_host), "host": sender_host,
                "port": int(d["port"]), "mode": str(d.get("mode", "?"))}
    except Exception:
        return None


class DiscoveryBeacon(QObject):
    """Slave-sida: broadcasta annons var ``interval_ms`` så mastern hittar oss."""

    def __init__(self, name: str, tcp_port: int, mode: str = "?",
                 interval_ms: int = 2000, parent=None):
        super().__init__(parent)
        self._name, self._port, self._mode = name, tcp_port, mode
        self._sock = QUdpSocket(self)
        self._timer = QTimer(self); self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._beacon)

    def start(self):
        self._beacon()
        self._timer.start()

    def _beacon(self):
        pkt = announce_packet(self._name, self._port, self._mode)
        self._sock.writeDatagram(pkt, QHostAddress.Broadcast, DISCOVERY_PORT)


class DiscoveryListener(QObject):
    """Master-sida: lyssna på annonser → emit discovered(name, host, port, mode)."""

    discovered = Signal(str, str, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sock = QUdpSocket(self)
        self._sock.readyRead.connect(self._on_ready)

    def start(self) -> bool:
        ok = self._sock.bind(QHostAddress.AnyIPv4, DISCOVERY_PORT,
                             QAbstractSocket.ShareAddress | QAbstractSocket.ReuseAddressHint)
        if not ok:
            print(f"[discovery] kunde inte binda UDP {DISCOVERY_PORT} — auto-upptäckt av")
        return ok

    def _on_ready(self):
        while self._sock.hasPendingDatagrams():
            dg = self._sock.receiveDatagram()
            info = parse_announce(dg.data().data(), dg.senderAddress().toString())
            if info:
                # IPv6-mappad IPv4 (::ffff:1.2.3.4) → ren IPv4
                host = info["host"].split(":")[-1] if info["host"].startswith("::ffff:") else info["host"]
                self.discovered.emit(info["name"], host, info["port"], info["mode"])
