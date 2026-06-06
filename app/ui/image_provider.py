"""numpy → QImage-leverantör för live-vyer (snabbt, ingen disk).

QML laddar bilden via ``image://live/surface`` och tvingar omladdning genom att
binda källan mot ``ctrl.surfaceRev`` (cache-bust).
"""
from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class LiveImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._img = QImage(2, 2, QImage.Format.Format_RGB888)
        self._img.fill(0)

    def set_array(self, arr: np.ndarray) -> None:
        """arr: HxWx3 uint8 (RGB)."""
        a = np.ascontiguousarray(arr, dtype=np.uint8)
        h, w, _ = a.shape
        # .copy() → QImage äger sin egen buffert (ingen numpy-livslängdsfälla)
        self._img = QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()

    def requestImage(self, image_id, size, requestedSize):
        if size is not None:
            size.setWidth(self._img.width())
            size.setHeight(self._img.height())
        return self._img
