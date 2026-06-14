"""Slave-server: exponerar en Jetsons DeviceManager över TCP (Qt Network, JSON-lines).

Kör på varje läshuvud. Tar emot kommandon (CommandHandler) och broadcastar event
när enhetsstatus/kalibrering ändras → mastern får live-uppdateringar utan polling.
"""
from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QHostAddress, QTcpServer

from . import protocol as p
from .command_handler import CommandHandler


class SlaveServer(QObject):
    def __init__(self, devmgr, name: str = "woody-node", port: int = 8765, parent=None):
        super().__init__(parent)
        self._handler = CommandHandler(devmgr, name=name)
        self._devmgr = devmgr
        self._port = port
        self._clients: dict = {}                 # QTcpSocket -> FrameBuffer
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_connect)
        # DeviceManager-signaler → event till alla anslutna master-klienter
        devmgr.devicesChanged.connect(self._emit_devices)
        devmgr.methodsChanged.connect(lambda: self._broadcast(p.event(p.EV_METHODS)))
        devmgr.calibChanged.connect(self._emit_calib)

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
