"""Slave-server: exponerar en Jetsons DeviceManager över TCP (Qt Network, JSON-lines).

Kör på varje läshuvud. Tar emot kommandon (CommandHandler) och broadcastar event
när enhetsstatus/kalibrering ändras → mastern får live-uppdateringar utan polling.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtNetwork import QHostAddress, QTcpServer

from . import protocol as p
from .command_handler import CommandHandler
from .telemetry import HostTelemetry


class SlaveServer(QObject):
    def __init__(self, devmgr, name: str = "woody-node", port: int = 8765,
                 controller=None, surface=None, parent=None):
        super().__init__(parent)
        self._handler = CommandHandler(devmgr, name=name, controller=controller)
        self._devmgr = devmgr
        self._ctrl = controller
        self._surface = surface             # _NetSurface (yt-/höjdbilder)
        self._img_sent: dict = {}           # name -> senast skickad rev
        self._port = port
        self._clients: dict = {}                 # QTcpSocket -> FrameBuffer
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_connect)
        # DeviceManager-signaler → event till alla anslutna master-klienter
        devmgr.devicesChanged.connect(self._emit_devices)
        devmgr.methodsChanged.connect(lambda: self._broadcast(p.event(p.EV_METHODS)))
        devmgr.calibChanged.connect(self._emit_calib)
        # Host-telemetri (RIKTIG, oavsett sim/real) → push var 2s
        self._tele = HostTelemetry()
        self._tele_last: dict = {}
        self._tele_timer = QTimer(self); self._tele_timer.setInterval(2000)
        self._tele_timer.timeout.connect(self._emit_telemetry)
        self._tele_timer.start()
        # Skanntillstånd (AppController) → push ~4 Hz (throttlat; stateChanged är per-frame)
        if controller is not None:
            self._scan_timer = QTimer(self); self._scan_timer.setInterval(250)
            self._scan_timer.timeout.connect(self._emit_scan)
            self._scan_timer.timeout.connect(self._emit_images)
            self._scan_timer.start()

    def listen(self) -> bool:
        ok = self._server.listen(QHostAddress.Any, self._port)
        if ok:
            print(f"[slave] lyssnar på 0.0.0.0:{self._port} "
                  f"({self._handler.name}, läge {self._devmgr.mode})")
        else:
            print(f"[slave] kunde INTE lyssna på {self._port}: {self._server.errorString()}")
        return ok

    # ---- anslutningar ----
    def _on_connect(self):
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._clients[sock] = p.FrameBuffer()
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            sock.disconnected.connect(lambda s=sock: self._clients.pop(s, None))
            peer = sock.peerAddress().toString()
            print(f"[slave] master ansluten: {peer}")
            # initialt: hälsning + nuläge så mastern direkt har full bild
            sock.write(p.event(p.EV_HELLO, self._handler._dispatch(p.CMD_HELLO, {})))
            sock.write(p.event(p.EV_DEVICES, {"devices": list(self._devmgr.devices),
                                              "status": self._handler._status()}))
            sock.write(p.event(p.EV_CALIB, self._handler._calib_state()))
            if self._tele_last:
                sock.write(p.event(p.EV_TELEMETRY, self._tele_last))
            if self._ctrl is not None:
                sock.write(p.event(p.EV_SCAN, self._handler.scan_state()))
            for pkt in self._image_packets(force=True):
                sock.write(pkt)

    def _on_ready(self, sock):
        fb = self._clients.get(sock)
        if fb is None:
            return
        for msg in fb.feed(bytes(sock.readAll().data())):
            if "cmd" not in msg:
                continue
            resp = self._handler.handle(msg)
            if resp is not None:
                sock.write(p.encode(resp))
            # positionsändring → broadcasta ny status till alla master-klienter
            if msg.get("cmd") == p.CMD_SET_POSITION and resp and resp.get("ok"):
                self._emit_devices()

    # ---- event-broadcast ----
    def _broadcast(self, data: bytes):
        for sock in list(self._clients):
            try:
                sock.write(data)
            except Exception:
                self._clients.pop(sock, None)

    def _emit_devices(self):
        self._broadcast(p.event(p.EV_DEVICES, {"devices": list(self._devmgr.devices),
                                               "status": self._handler._status()}))

    def _emit_calib(self):
        self._broadcast(p.event(p.EV_CALIB, self._handler._calib_state()))

    def _emit_telemetry(self):
        self._tele_last = self._tele.collect()
        if self._clients:
            self._broadcast(p.event(p.EV_TELEMETRY, self._tele_last))

    def _emit_scan(self):
        if self._clients and self._ctrl is not None:
            self._broadcast(p.event(p.EV_SCAN, self._handler.scan_state()))

    def _image_packets(self, force: bool = False):
        """Bygg EV_IMAGE-paket för bilder vars rev ändrats (zlib + base64)."""
        out = []
        if self._surface is None:
            return out
        import base64, zlib
        for name, val in list(self._surface.imgs.items()):
            raw, w, h, rev = val
            if not force and self._img_sent.get(name) == rev:
                continue
            self._img_sent[name] = rev
            data = base64.b64encode(zlib.compress(raw, 6)).decode("ascii")
            out.append(p.event(p.EV_IMAGE, {"name": name, "w": w, "h": h, "rev": rev, "data": data}))
        return out

    def _emit_images(self):
        if not self._clients:
            return
        for pkt in self._image_packets():
            self._broadcast(pkt)
