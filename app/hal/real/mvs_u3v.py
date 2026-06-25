"""Hikrobot MVS-SDK-wrapper (USB3 Vision) för profilkamerorna.

Harvesters/genicam-vägen kraschar mot MVS GenTL-producenten (UnicodeDecodeError i
``Port__get_url_info_list`` — producentens URL-sträng är inte ren UTF-8). Därför kör
profilkamerorna via Hikrobots egna Python-SDK (``/opt/MVS/Samples/.../MvImport``),
som hanterar sin egen teckenkodning. Ytkameran (GigE) ligger kvar på harvesters.

SDK:t lazy-importeras så appen startar på dev-maskiner utan MVS installerat.
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading

import numpy as np

# MvImport-katalogen som MVS installerar (aarch64 på Jetson)
_MVS_PY_CANDIDATES = [
    "/opt/MVS/Samples/aarch64/Python/MvImport",
    "/opt/MVS/Samples/64/Python/MvImport",
]
_SDK = None


def _sdk():
    """(MvCameraControl_class, CameraParams_header) — laddas en gång, lazy."""
    global _SDK
    if _SDK is None:
        # MvImport/MvCameraControl_class kräver MVS-miljövariabler VID IMPORT
        # (check_sys_and_update_dll gör os.getenv('MVCAM_COMMON_RUNENV') + "...").
        # Saknas de (systemd/cron utan profil-källning) → None+str-TypeError. Sätt
        # säkra defaults om de inte redan finns, så importen funkar i alla kontexter.
        os.environ.setdefault("MVCAM_COMMON_RUNENV", "/opt/MVS/lib")
        os.environ.setdefault("MVCAM_SDK_PATH", "/opt/MVS")
        os.environ.setdefault("GENICAM_GENTL64_PATH", "/opt/MVS/lib/aarch64")
        for d in _MVS_PY_CANDIDATES:
            if os.path.isdir(d) and d not in sys.path:
                sys.path.append(d)
        import MvCameraControl_class as cc      # lazy (vendor-SDK)
        import CameraParams_header as hdr
        try:
            cc.MvCamera.MV_CC_Initialize()       # nyare MVS; äldre saknar den
        except Exception:
            pass
        _SDK = (cc, hdr)
    return _SDK


def _decode_serial(char_array) -> str:
    """Serienummer ur ctypes-char-array (NUL-terminerad ASCII)."""
    s = ""
    for c in char_array:
        if c == 0:
            break
        s += chr(c)
    return s


def list_serials() -> list[str]:
    """Serienummer för alla anslutna USB3-kameror (för cameras.json-bindning)."""
    cc, hdr = _sdk()
    devs = hdr.MV_CC_DEVICE_INFO_LIST()
    if cc.MvCamera.MV_CC_EnumDevices(hdr.MV_USB_DEVICE, devs) != 0:
        return []
    out = []
    for i in range(devs.nDeviceNum):
        info = ctypes.cast(devs.pDeviceInfo[i],
                           ctypes.POINTER(hdr.MV_CC_DEVICE_INFO)).contents
        out.append(_decode_serial(info.SpecialInfo.stUsb3VInfo.chSerialNumber))
    return out


class MvsU3VCamera:
    """Tunn wrapper kring en MVS-kamera: öppna (per serienr), sätt noder, greppa ramar.

    Alla set_*-metoder sväljer fel och returnerar bool — GenICam-nodnamn/typer
    varierar, koden ska aldrig krascha på en okänd nod (samma princip som
    set_first_available i cameras.py)."""

    def __init__(self, serial: str | None = None):
        self._serial = serial
        self._cam = None
        self._hdr = None
        self._grabbing = False
        self._lock = threading.Lock()      # serialisera grab över trådar (preview∥förvärv)

    def open(self, pixel_format: str = "Mono8") -> None:
        cc, hdr = _sdk()
        self._hdr = hdr
        devs = hdr.MV_CC_DEVICE_INFO_LIST()
        if cc.MvCamera.MV_CC_EnumDevices(hdr.MV_USB_DEVICE, devs) != 0:
            raise RuntimeError("MV_CC_EnumDevices misslyckades")
        if devs.nDeviceNum == 0:
            raise RuntimeError("inga USB3-kameror hittade")
        chosen = None
        for i in range(devs.nDeviceNum):
            info = ctypes.cast(devs.pDeviceInfo[i],
                               ctypes.POINTER(hdr.MV_CC_DEVICE_INFO)).contents
            if self._serial is None or \
                    _decode_serial(info.SpecialInfo.stUsb3VInfo.chSerialNumber) == self._serial:
                chosen = info
                break
        if chosen is None:
            raise RuntimeError(f"kamera S/N {self._serial} ej ansluten")
        cam = cc.MvCamera()
        if cam.MV_CC_CreateHandle(chosen) != 0:
            raise RuntimeError("MV_CC_CreateHandle misslyckades")
        if cam.MV_CC_OpenDevice(hdr.MV_ACCESS_Exclusive, 0) != 0:
            cam.MV_CC_DestroyHandle()
            raise RuntimeError("MV_CC_OpenDevice misslyckades (kamera upptagen?)")
        self._cam = cam
        cam.MV_CC_SetEnumValueByString("TriggerMode", "Off")      # free-run
        self.set_enum("PixelFormat", pixel_format)

    # ---- nod-setters (returnerar True vid OK) ----------------------------------
    def set_enum(self, name: str, value: str) -> bool:
        try:
            return self._cam.MV_CC_SetEnumValueByString(name, value) == 0
        except Exception:
            return False

    def set_float(self, name: str, value: float) -> bool:
        try:
            return self._cam.MV_CC_SetFloatValue(name, float(value)) == 0
        except Exception:
            return False

    def set_int(self, name: str, value: int) -> bool:
        try:
            return self._cam.MV_CC_SetIntValue(name, int(value)) == 0
        except Exception:
            return False

    def set_bool(self, name: str, value: bool) -> bool:
        try:
            return self._cam.MV_CC_SetBoolValue(name, bool(value)) == 0
        except Exception:
            return False

    def get_int_max(self, name: str):
        try:
            st = self._hdr.MVCC_INTVALUE()
            if self._cam.MV_CC_GetIntValue(name, st) == 0:
                return int(st.nMax)
        except Exception:
            pass
        return None

    # ---- förvärv ---------------------------------------------------------------
    def start(self) -> None:
        if self._cam is not None and not self._grabbing:
            self._cam.MV_CC_StartGrabbing()
            self._grabbing = True

    def stop(self) -> None:
        if self._cam is not None and self._grabbing:
            try:
                self._cam.MV_CC_StopGrabbing()
            except Exception:
                pass
            self._grabbing = False

    def grab(self, timeout_ms: int = 1000):
        """En mono-ram som numpy (H, W) uint8 — eller None vid timeout.
        Låst: preview-tråden och förvärvsloopen kan greppa samma handle utan race."""
        hdr = self._hdr
        with self._lock:
            if self._cam is None:
                return None
            frame = hdr.MV_FRAME_OUT()
            ctypes.memset(ctypes.byref(frame), 0, ctypes.sizeof(frame))
            if self._cam.MV_CC_GetImageBuffer(frame, int(timeout_ms)) != 0:
                return None
            try:
                fi = frame.stFrameInfo
                n = fi.nHeight * fi.nWidth
                buf = (ctypes.c_ubyte * fi.nFrameLen)()
                ctypes.memmove(buf, frame.pBufAddr, fi.nFrameLen)
                return np.frombuffer(buf, dtype=np.uint8)[:n].reshape(fi.nHeight, fi.nWidth).copy()
            finally:
                try:
                    self._cam.MV_CC_FreeImageBuffer(frame)
                except Exception:
                    pass

    def close(self) -> None:
        if self._cam is not None:
            self.stop()
            try:
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
            except Exception:
                pass
        self._cam = None
        self._grabbing = False
