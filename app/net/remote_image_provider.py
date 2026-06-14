"""QML-bildprovider för fjärrnodernas yt-/höjdbilder (master).

QML refererar ``image://remote/<host>/<namn>?<rev>`` → providern slår upp noden på
host och returnerar dess senaste QImage för namnet ('surface' / 'height').
"""
from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class RemoteImageProvider(QQuickImageProvider):
    def __init__(self, node_manager):
        super().__init__(QQuickImageProvider.Image)
        self._nm = node_manager

    def requestImage(self, image_id: str, size, requested_size):
        key = image_id.split("?", 1)[0]            # släpp ev. ?rev-cachebrytare
        host, _, name = key.partition("/")
        node = self._nm.node_by_host(host)
        img = node.image(name) if node is not None else None
        if img is None or img.isNull():
            return QImage(2, 2, QImage.Format_RGB888)
        return img
