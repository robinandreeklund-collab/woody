"""Kameror via GenICam (Harvester) — täcker både USB3 Vision (profilkameror) och
GigE Vision (ytkamera) med samma standard-API. Aravis kan användas som alternativ.

Profilkameran ger en mono-ROI runt laserstripen (rader = höjd, kolumner = längs
linjen) → matas rakt in i samma behandlingspipeline som i sim. Harvester/genicam
importeras lazy så appen startar utan SDK.
"""
from __future__ import annotations

import numpy as np

from ..base import DeviceInfo, ProfileCameraIF, SurfaceCameraIF
from ...geometry import RIG

# delad Harvester-instans (laddar GenTL-producent en gång)
_HARVESTER = None


def _harvester():
    global _HARVESTER
    if _HARVESTER is None:
        from harvesters.core import Harvester      # lazy
        import os
        h = Harvester()
        # CTI-fil pekas ut av env GENICAM_GENTL64_PATH (MVS/Aravis levererar en)
        cti = os.environ.get("GENICAM_CTI")
        if cti:
            h.add_file(cti)
        h.update()
        _HARVESTER = h
    return _HARVESTER


class GenICamProfileCamera(ProfileCameraIF):
    def __init__(self, color: str, serial: str | None = None,
                 roi_rows: int = 80, exposure_us: float = 800.0):
        self._color = color
        self._serial = serial
        self._roi_rows = roi_rows
        self._exposure_us = exposure_us
        self._ia = None
        self._connected = False

    def info(self) -> DeviceInfo:
        nm = "RÖD 650" if self._color == "red" else "GRÖN 520"
        return DeviceInfo(f"Profilkamera {nm}", "Hikrobot MV-CS050-10UM", "USB3 Vision", self._connected)

    def open(self) -> None:
        h = _harvester()
        kw = {"serial_number": self._serial} if self._serial else {}
        self._ia = h.create(search_key=kw or None)
        n = self._ia.remote_device.node_map
        try:
            n.ExposureTime.value = self._exposure_us
            n.PixelFormat.value = "Mono8"
        except Exception:
            pass
        self._ia.start()
        self._connected = True

    def read_stripe(self, y_mm: float = 0.0, n: int = 200) -> np.ndarray:
        """Hämta en ram, beskär ett ROI-band runt stripen och skala till (roi_rows, n)."""
        if not self._connected:
            return np.zeros((self._roi_rows, n))
        with self._ia.fetch(timeout=0.5) as buf:
            comp = buf.payload.components[0]
            img = comp.data.reshape(comp.height, comp.width).astype(np.float64)
        # centrera ROI vertikalt; nedsampla längs linjen till n kolumner
        r0 = max(0, img.shape[0] // 2 - self._roi_rows // 2)
        roi = img[r0:r0 + self._roi_rows]
        cols = np.linspace(0, roi.shape[1] - 1, n).astype(int)
        return roi[:, cols]

    def read_profile(self, y_mm: float = 0.0) -> np.ndarray:
        from ...processing.stripe import subpixel_centroid
        from ...processing.triangulate import centroid_to_z
        return centroid_to_z(subpixel_centroid(self.read_stripe(y_mm)))

    def close(self) -> None:
        if self._ia:
            self._ia.stop(); self._ia.destroy()
        self._connected = False


class GenICamSurfaceCamera(SurfaceCameraIF):
    def __init__(self, serial: str | None = None):
        self._serial = serial
        self._ia = None
        self._connected = False
        self._rows: list = []        # ackumulerade rad-skanningar (en bräda)

    def info(self) -> DeviceInfo:
        return DeviceInfo("Ytkamera 4K färg (linjekamera)", "HT-GELM44C-T2 (4096 px, encoder-trig)",
                          "GigE Vision", self._connected)

    def open(self) -> None:
        h = _harvester()
        kw = {"serial_number": self._serial} if self._serial else {}
        self._ia = h.create(search_key=kw or None)
        self._ia.start()
        self._connected = True

    def grab_line(self) -> np.ndarray:
        """En radskanning (RGB) — ackumuleras till en yt-bild medan brädan matas."""
        with self._ia.fetch(timeout=0.5) as buf:
            comp = buf.payload.components[0]
            return comp.data.reshape(-1, 3).astype(np.uint8)

    def surface_image(self) -> np.ndarray:
        return np.array(self._rows, dtype=np.uint8) if self._rows else np.zeros((2, 2, 3), np.uint8)

    def close(self) -> None:
        if self._ia:
            self._ia.stop(); self._ia.destroy()
        self._connected = False
