"""NodeManager — masterns samling av RemoteNode (en per Jetson ur data/nodes.json).

Exponerar nodöversikten till QML och ger drill-in: ``node(index)`` returnerar en
RemoteNode som (tack vare samma gränssnitt som DeviceManager) driver de befintliga
Sensorer/Kalibrering-vyerna.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import nodes_config
from .remote_node import RemoteNode


class NodeManager(QObject):
    nodesChanged = Signal()

    def __init__(self, path="data/nodes.json", parent=None):
        super().__init__(parent)
        self._path = path
        self._nodes: list[RemoteNode] = []
        for n in nodes_config.load(path):
            self._add(n["name"], n["host"], n["port"], connect=True)

    def _add(self, name, host, port, connect=False):
        node = RemoteNode(name, host, int(port), parent=self)
        node.connectionChanged.connect(self.nodesChanged)
        node.devicesChanged.connect(self.nodesChanged)
        node.calibChanged.connect(self.nodesChanged)
        self._nodes.append(node)
        if connect:
            node.connectNode()
        return node

    @Property(int, notify=nodesChanged)
    def count(self):
        return len(self._nodes)

    @Property("QVariantList", notify=nodesChanged)
    def nodeSummaries(self):
        return [n.summary for n in self._nodes]

    @Slot(int, result=QObject)
    def node(self, index: int):
        return self._nodes[index] if 0 <= index < len(self._nodes) else None

    @Slot(str, str, int)
    def addNode(self, name: str, host: str, port: int = 8765):
        self._add(name, host, port, connect=True)
        self._persist()
        self.nodesChanged.emit()

    @Slot(int)
    def removeNode(self, index: int):
        if 0 <= index < len(self._nodes):
            self._nodes.pop(index).deleteLater()
            self._persist()
            self.nodesChanged.emit()

    def _persist(self):
        nodes_config.save([{"name": n.nodeName, "host": n.host, "port": n._port}
                           for n in self._nodes], self._path)
