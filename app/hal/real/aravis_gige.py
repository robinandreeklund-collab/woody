"""GigE Vision-ytkamera (linjekamera) via Aravis (GenICam).

Harvesters/genicam-vägen kraschar mot kamerans GenTL-producent (UnicodeDecodeError
i URL-listan — samma bugg som U3V-profilkamerorna). Aravis talar GigE Vision direkt
och enumererar/öppnar HT-GELM44C-T2 (ChinaVision GELM44C-T2) rent. gi/Aravis lazy-
importeras så appen startar på maskiner utan dem.

Kameran måste ligga på samma IPv4-subnät som Jetson-porten (fast IP 192.168.3.189 →
Jetson enP8p1s0 = 192.168.3.10/24, satt permanent via NetworkManager).
"""
from __future__ import annotations

import numpy as np

_ARAVIS = None


def _aravis():
    global _ARAVIS
    if _ARAVIS is None:
        import gi
        gi.require_version("Aravis", "0.8")
        from gi.repository import Aravis        # lazy
        _ARAVIS = Aravis
    return _ARAVIS


def list_devices() -> list[str]:
    """Alla GenICam-enhets-id Aravis ser (inkl. U3V-profilkameror + GigE-ytkamera)."""
    A = _aravis()
    A.update_device_list()
    return [A.get_device_id(i) for i in range(A.get_n_devices())]


class AravisGigeCamera:
    """Tunn wrapper kring en Aravis-kamera: öppna (per serienr/id), sätt noder, greppa
    ramar. set_*-metoderna sväljer fel (okänd nod/typ) och returnerar bool."""

    def __init__(self, serial: str | None = None):
        self._serial = serial
        self._cam = None
        self._dev = None
        self._stream = None
        self._A = None
        self._grabbing = False

    def open(self, pixel_format: str | None = None) -> None:
        A = _aravis()
        self._A = A
        A.update_device_list()
        dev_id = None
        for i in range(A.get_n_devices()):
            did = A.get_device_id(i)
            if self._serial is not None:
                if str(self._serial) in did:
                    dev_id = did
                    break
            else:
                if "U3V" not in did:                  # första icke-USB (= GigE-ytkameran)
                    dev_id = did
                    break
        if dev_id is None:
            raise RuntimeError(f"GigE-kamera {self._serial!r} ej hittad (Aravis)")
        self._cam = A.Camera.new(dev_id)
        self._dev = self._cam.get_device()
        if pixel_format:
            self.set_str("PixelFormat", pixel_format)

    # ---- nod-setters (returnerar True vid OK) ----------------------------------
    def set_str(self, name: str, value: str) -> bool:
        try:
            self._dev.set_string_feature_value(name, value)
            return True
        except Exception:
            return False

    def set_int(self, name: str, value) -> bool:
        try:
            self._dev.set_integer_feature_value(name, int(value))
            return True
        except Exception:
            return False

    def set_float(self, name: str, value) -> bool:
        try:
            self._dev.set_float_feature_value(name, float(value))
            return True
        except Exception:
            return False

    def get_float(self, name: str):
        try:
            return self._dev.get_float_feature_value(name)
        except Exception:
            return None

    # alias så delade _apply_feature (MVS-stil) funkar: GenICam-enum = sträng i Aravis
    def set_enum(self, name: str, value: str) -> bool:
        return self.set_str(name, value)

    def set_bool(self, name: str, value) -> bool:
        try:
            self._dev.set_boolean_feature_value(name, bool(value))
            return True
        except Exception:
            return False

    def set_first(self, candidates, value) -> tuple:
        """Sätt FÖRSTA noden i candidates som accepterar värdet (väljer setter efter typ)."""
        for n in candidates:
            ok = (self.set_str(n, value) if isinstance(value, str)
                  else self.set_int(n, value) if isinstance(value, (int, bool))
                  else self.set_float(n, value))
            if ok:
                return (n, True)
        return (None, False)

    # ---- förvärv ---------------------------------------------------------------
    def start(self, n_buffers: int = 8, height: int | None = None) -> None:
        A = self._A
        if height is not None:
            self.set_int("Height", height)
        payload = self._cam.get_payload()
        self._stream = self._cam.create_stream(None, None)
        for _ in range(n_buffers):
            self._stream.push_buffer(A.Buffer.new_allocate(payload))
        self._cam.start_acquisition()
        self._grabbing = True

    def stop(self) -> None:
        try:
            if self._cam is not None and self._grabbing:
                self._cam.stop_acquisition()
        except Exception:
            pass
        self._grabbing = False
        self._stream = None

    def grab(self, timeout_ms: int = 1000):
        """En ram som numpy (H,W,3) för färg eller (H,W) mono — eller None vid timeout."""
        if self._stream is None:
            return None
        A = self._A
        buf = self._stream.timeout_pop_buffer(int(timeout_ms) * 1000)
        if buf is None:
            return None
        try:
            if buf.get_status() != A.BufferStatus.SUCCESS:
                return None
            w = buf.get_image_width()
            h = buf.get_image_height()
            raw = np.frombuffer(buf.get_data(), dtype=np.uint8)
            n = w * h
            if raw.size >= n * 3:
                return raw[:n * 3].reshape(h, w, 3).copy()
            if raw.size >= n:
                return raw[:n].reshape(h, w).copy()
            return None
        finally:
            self._stream.push_buffer(buf)

    def close(self) -> None:
        self.stop()
        self._cam = None
        self._dev = None
