"""numpy → QImage-leverantör för live-vyer (snabbt, ingen disk).

Lagrar flera namngivna bilder (t.ex. "surface", "height"). QML laddar via
``image://live/<namn>`` och tvingar omladdning genom att binda källan mot en
revision (cache-bust), t.ex. ``"image://live/surface/" + ctrl.surfaceRev``.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class LiveImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        blank = QImage(2, 2, QImage.Format.Format_RGB888)
        blank.fill(0)
        self._imgs: dict[str, QImage] = {"": blank}

    def set_array(self, arr: np.ndarray, name: str = "surface") -> None:
        """arr: HxWx3 uint8 (RGB)."""
        a = np.ascontiguousarray(arr, dtype=np.uint8)
        h, w, _ = a.shape
        # .copy() → QImage äger sin egen buffert (ingen numpy-livslängdsfälla)
        self._imgs[name] = QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()

    def requestImage(self, image_id, size, requestedSize):
        name = image_id.split("/", 1)[0]          # "surface/3" → "surface"
        img = self._imgs.get(name) or self._imgs[""]
        if size is not None:
            size.setWidth(img.width())
            size.setHeight(img.height())
        return img
