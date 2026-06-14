"""RemoteNode — en master-sidans proxy för EN Jetson (läshuvud).

Speglar ``DeviceManager``:s QML-gränssnitt (devices, methodsFor, startCalibration,
calib*-properties + samma signaler) men backas av en QTcpSocket mot slavens
SlaveServer. Därför kan de BEFINTLIGA Sensorer/Kalibrering-vyerna driva en fjärrnod
oförändrade — sätt bara ``devmgr`` till en RemoteNode i st f den lokala DeviceManager.

Nät-anrop är asynkrona: methodsFor returnerar cache och begär uppdatering i bakgrunden;
när svaret kommer emittas methodsChanged → vyn hämtar om. Kalibrerings­progress
strömmar via calib_changed-event → calibChanged.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket

from . import protocol as p


class RemoteNode(QObject):
    devicesChanged = Signal()
    methodsChanged = Signal()
    calibChanged = Signal()
    connectionChanged = Signal()

    def __init__(self, name: str, host: str, port: int = 8765, parent=None):
        super().__init__(parent)
        self._name, self._host, self._port = name, host, port
        self._mode = "?"
        self._connected = False
        self._devices: list = []
        self._status: dict = {}
        self._methods: dict = {}             # dev_id -> metodlista (cache)
        self._methods_pending: set = set()
        self._calib = {"running": False, "device": "", "title": "", "pct": 0.0,
                       "step": "", "log": [], "result": "", "ok": True}
        self._next_id = 1
        self._pending: dict = {}             # msg_id -> callback(result, ok)
        self._fb = p.FrameBuffer()
        self._sock = QTcpSocket(self)
        self._sock.connected.connect(self._on_connected)
        self._sock.disconnected.connect(self._on_disconnected)
        self._sock.readyRead.connect(self._on_ready)
        self._sock.errorOccurred.connect(lambda *_: self._on_disconnected())
        self._retry = QTimer(self); self._retry.setInterval(3000)
        self._retry.timeout.connect(self._maybe_connect)

    # ------------------------------------------------------------ anslutning
    @Slot()
    def connectNode(self):
        self._retry.start()
        self._maybe_connect()

    def _maybe_connect(self):
        if self._sock.state() == QAbstractSocket.UnconnectedState:
            self._sock.connectToHost(self._host, self._port)

    def _on_connected(self):
        self._connected = True
        self.connectionChanged.emit()
        self._send(p.CMD_STATUS, callback=lambda r, ok: self._apply_status(r) if ok else None)

    def _on_disconnected(self):
        if self._connected:
            self._connected = False
            self.connectionChanged.emit()
        self._pending.clear()

    def _on_ready(self):
        for msg in self._fb.feed(bytes(self._sock.readAll().data())):
            if "event" in msg:
                self._on_event(msg["event"], msg.get("data") or {})
            elif "id" in msg:
                cb = self._pending.pop(msg["id"], None)
                if cb:
                    cb(msg.get("result"), msg.get("ok", False))

    def _send(self, cmd: str, args: dict | None = None, callback=None):
        if self._sock.state() != QAbstractSocket.ConnectedState:
            return
        mid = self._next_id; self._next_id += 1
        if callback:
            self._pending[mid] = callback
        self._sock.write(p.request(mid, cmd, args))

    # ------------------------------------------------------------ event in
    def _on_event(self, name: str, data: dict):
        if name == p.EV_HELLO:
            self._mode = data.get("mode", "?")
            self.connectionChanged.emit()
        elif name == p.EV_DEVICES:
            self._devices = data.get("devices", [])
            self._apply_status(data.get("status"))
            self.devicesChanged.emit()
        elif name == p.EV_METHODS:
            self._methods.clear(); self._methods_pending.clear()
            self.methodsChanged.emit()
        elif name == p.EV_CALIB:
            self._calib = data or self._calib
            self.calibChanged.emit()

    def _apply_status(self, status):
        if isinstance(status, dict):
            self._status = status
            self._mode = status.get("mode", self._mode)

    # ------------------------------------------------------------ DeviceManager-API
    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        return list(self._devices)

    @Property("QVariantMap", notify=devicesChanged)
    def statusMap(self):
        return {d.get("id"): {"connected": d.get("connected"), "status": d.get("status")}
                for d in self._devices}

    @Property(str, notify=connectionChanged)
    def mode(self):
        return self._mode

    @Slot(str, result="QVariantList")
    def methodsFor(self, dev_id: str):
        if dev_id not in self._methods and dev_id not in self._methods_pending:
            self._methods_pending.add(dev_id)
            self._send(p.CMD_METHODS, {"dev": dev_id},
                       callback=lambda r, ok, d=dev_id: self._got_methods(d, r, ok))
        return list(self._methods.get(dev_id, []))

    def _got_methods(self, dev_id, result, ok):
        self._methods_pending.discard(dev_id)
        if ok and isinstance(result, list):
            self._methods[dev_id] = result
            self.methodsChanged.emit()

    @Slot(str, str, result=bool)
    def startCalibration(self, dev_id: str, method_id: str) -> bool:
        self._send(p.CMD_START_CALIB, {"dev": dev_id, "method": method_id})
        return True                         # verkligt utfall kommer via calib-event

    @Slot()
    def cancelCalibration(self):
        self._send(p.CMD_CANCEL_CALIB)

    @Slot()
    def refresh(self):
        self._send(p.CMD_REFRESH)

    @Slot(bool, result=bool)
    def armLasers(self, confirm: bool) -> bool:
        self._send(p.CMD_ARM_LASERS, {"confirm": bool(confirm)})
        return True

    @Slot()
    def disarmLasers(self):
        self._send(p.CMD_DISARM_LASERS)

    @Property(bool, notify=devicesChanged)
    def lasersArmed(self) -> bool:
        return bool(self._status.get("lasers_armed", False))

    # ------------------------------------------------------------ calib-properties
    @Property(bool, notify=calibChanged)
    def calibRunning(self): return bool(self._calib.get("running"))
    @Property(str, notify=calibChanged)
    def calibDevice(self): return self._calib.get("device", "")
    @Property(str, notify=calibChanged)
    def calibTitle(self): return self._calib.get("title", "")
    @Property(float, notify=calibChanged)
    def calibPct(self): return float(self._calib.get("pct", 0.0))
    @Property(str, notify=calibChanged)
    def calibStep(self): return self._calib.get("step", "")
    @Property("QVariantList", notify=calibChanged)
    def calibLog(self): return list(self._calib.get("log", []))
    @Property(str, notify=calibChanged)
    def calibResult(self): return self._calib.get("result", "")
    @Property(bool, notify=calibChanged)
    def calibOk(self): return bool(self._calib.get("ok", True))

    # ------------------------------------------------------------ nodöversikt
    @Property(bool, notify=connectionChanged)
    def connected(self): return self._connected
    @Property(str, constant=True)
    def nodeName(self): return self._name
    @Property(str, constant=True)
    def host(self): return self._host
    @Property("QVariantMap", notify=devicesChanged)
    def summary(self):
        s = dict(self._status)
        s.update({"name": self._name, "host": self._host, "connected": self._connected,
                  "mode": self._mode})
        return s

    # ------------------------------------------------------------ position (sektion)
    def _pos(self) -> dict:
        return self._status.get("position") or {}

    @Property(str, notify=devicesChanged)
    def posLabel(self): return str(self._pos().get("label", ""))
    @Property(float, notify=devicesChanged)
    def posStart(self): return float(self._pos().get("start_mm", 0.0))
    @Property(float, notify=devicesChanged)
    def posEnd(self): return float(self._pos().get("end_mm", 0.0))

    @Slot(str, float, float)
    def setPosition(self, label: str, start_mm: float, end_mm: float):
        self._send(p.CMD_SET_POSITION,
                   {"label": label, "start_mm": start_mm, "end_mm": end_mm})

    @Property(bool, notify=devicesChanged)
    def hasConveyor(self) -> bool:
        """True = denna nod äger encodern/motorn (lead). False = ren-sensor-huvud."""
        return bool(self._status.get("has_conveyor", True))
