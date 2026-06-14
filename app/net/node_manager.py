"""NodeManager — masterns samling av RemoteNode (en per Jetson ur data/nodes.json).

Exponerar nodöversikten till QML och ger drill-in: ``node(index)`` returnerar en
RemoteNode som (tack vare samma gränssnitt som DeviceManager) driver de befintliga
Sensorer/Kalibrering-vyerna.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import nodes_config
from .discovery import DiscoveryListener
from .remote_node import RemoteNode


class NodeManager(QObject):
    nodesChanged = Signal()

    def __init__(self, path="data/nodes.json", discover=True, parent=None):
        super().__init__(parent)
        self._path = path
        self._nodes: list[RemoteNode] = []
        self._seen: set = set()              # (host, port) vi redan har
        self._manual: set = set()            # (host, port) ur nodes.json (persisteras)
        for n in nodes_config.load(path):
            self._manual.add((n["host"], n["port"]))
            self._add(n["name"], n["host"], n["port"], connect=True)
        # Auto-upptäckt på LAN: slavar som broadcastar läggs till automatiskt.
        self._listener = None
        if discover:
            self._listener = DiscoveryListener(self)
            self._listener.discovered.connect(self._on_discovered)
            self._listener.start()

    def _add(self, name, host, port, connect=False):
        key = (host, int(port))
        if key in self._seen:
            return None
        self._seen.add(key)
        node = RemoteNode(name, host, int(port), parent=self)
        node.connectionChanged.connect(self.nodesChanged)
        node.devicesChanged.connect(self.nodesChanged)
        node.calibChanged.connect(self.nodesChanged)
        self._nodes.append(node)
        if connect:
            node.connectNode()
        return node

    def _on_discovered(self, name, host, port, mode):
        if (host, int(port)) in self._seen:
            return                            # redan känd (manuell eller upptäckt)
        print(f"[discovery] hittade '{name}' på {host}:{port} ({mode})")
        self._add(name, host, port, connect=True)
        self.nodesChanged.emit()

    @Property(int, notify=nodesChanged)
    def count(self):
        return len(self._nodes)

    @Property("QVariantList", notify=nodesChanged)
    def nodeSummaries(self):
        return [n.summary for n in self._nodes]

    @Slot(int, result=QObject)
    def node(self, index: int):
        return self._nodes[index] if 0 <= index < len(self._nodes) else None

    def node_by_host(self, host: str):
        for n in self._nodes:
            if n.host == host:
                return n
        return None

    @Slot(str, str, int)
    def addNode(self, name: str, host: str, port: int = 8765):
        if self._add(name, host, port, connect=True) is not None:
            self._manual.add((host, int(port)))
            self._persist()
            self.nodesChanged.emit()

    @Slot(int)
    def removeNode(self, index: int):
        if 0 <= index < len(self._nodes):
            n = self._nodes.pop(index)
            self._seen.discard((n.host, n._port))
            self._manual.discard((n.host, n._port))
            n.deleteLater()
            self._persist()
            self.nodesChanged.emit()

    def _persist(self):
        # Persistera BARA manuellt tillagda noder (auto-upptäckta återfinns vid start).
        nodes_config.save([{"name": n.nodeName, "host": n.host, "port": n._port}
                           for n in self._nodes if (n.host, n._port) in self._manual],
                          self._path)
