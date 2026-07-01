#!/usr/bin/env python3
"""Full-frame snapshot från profilkamerorna via Hikrobots MVS-SDK (MvImport) — för att
bedöma fokus/exponering/laserlinje med ÖGAT, inte det tunna 60-fps-ROI:t.

Harvesters/genicam-vägen kraschar mot MVS (UnicodeDecodeError i URL-listan), därför
går vi direkt på vendor-SDK:t här. Tar EN ram per ansluten USB3-kamera, fullt
sensorområde, sparar PNG per serienummer.

    .venv/bin/python tools/camera_snapshot.py                  # auto-exponering
    .venv/bin/python tools/camera_snapshot.py --exposure 3000  # 3 ms
    .venv/bin/python tools/camera_snapshot.py --out /sökväg
"""
from __future__ import annotations
import argparse, ctypes, os, sys
from ctypes import POINTER, cast, byref, memmove
import numpy as np

MVS_PY = "/opt/MVS/Samples/aarch64/Python/MvImport"
sys.path.append(MVS_PY)
from MvCameraControl_class import *          # noqa: F401,F403  (MvCamera m.m.)
from CameraParams_header import *            # noqa: F401,F403  (structar/konstanter)
from MvErrorDefine_const import *            # noqa: F401,F403


def _save_png(img: np.ndarray, path: str) -> str:
    try:
        from PIL import Image
        Image.fromarray(img).save(path); return path
    except Exception:
        pass
    try:
        import imageio.v2 as imageio
        imageio.imwrite(path, img); return path
    except Exception:
        pass
    pgm = os.path.splitext(path)[0] + ".pgm"
    with open(pgm, "wb") as f:
        f.write(f"P5\n{img.shape[1]} {img.shape[0]}\n255\n".encode())
        f.write(img.astype(np.uint8).tobytes())
    return pgm


def _serial(info) -> str:
    s = ""
    for c in info.SpecialInfo.stUsb3VInfo.chSerialNumber:
        if c == 0:
            break
        s += chr(c)
    return s


def _set_int(cam, name, value):
    try: cam.MV_CC_SetIntValue(name, int(value))
    except Exception: pass


def _set_enum_str(cam, name, value):
    try: cam.MV_CC_SetEnumValueByString(name, value)
    except Exception: pass


def _get_int_max(cam, name):
    st = MVCC_INTVALUE()
    if cam.MV_CC_GetIntValue(name, st) == 0:
        return st.nMax
    return None


def snap_one(info, exposure_us, out_dir) -> dict:
    serial = _serial(info)
    cam = MvCamera()
    res = {"serial": serial}
    if cam.MV_CC_CreateHandle(info) != 0:
        return {**res, "error": "CreateHandle"}
    if cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0) != 0:
        cam.MV_CC_DestroyHandle(); return {**res, "error": "OpenDevice (upptagen?)"}
    try:
        cam.MV_CC_SetEnumValueByString("TriggerMode", "Off")      # free-run
        # fullt sensorområde: nolla offset → maxa bredd/höjd
        _set_int(cam, "OffsetX", 0); _set_int(cam, "OffsetY", 0)
        wmax = _get_int_max(cam, "Width"); hmax = _get_int_max(cam, "Height")
        if wmax: _set_int(cam, "Width", wmax)
        if hmax: _set_int(cam, "Height", hmax)
        _set_enum_str(cam, "PixelFormat", "Mono8")
        if exposure_us is not None:
            _set_enum_str(cam, "ExposureAuto", "Off")
            try: cam.MV_CC_SetFloatValue("ExposureTime", float(exposure_us))
            except Exception: pass
        else:
            _set_enum_str(cam, "ExposureAuto", "Continuous")

        if cam.MV_CC_StartGrabbing() != 0:
            return {**res, "error": "StartGrabbing"}
        frame = MV_FRAME_OUT()
        ctypes.memset(byref(frame), 0, ctypes.sizeof(frame))
        img = None
        for _ in range(6):                       # kasta ett par ramar (auto-exp stabil)
            if cam.MV_CC_GetImageBuffer(frame, 1500) == 0:
                fi = frame.stFrameInfo
                buf = (ctypes.c_ubyte * fi.nFrameLen)()
                memmove(buf, frame.pBufAddr, fi.nFrameLen)
                img = np.frombuffer(buf, dtype=np.uint8)[:fi.nHeight * fi.nWidth] \
                        .reshape(fi.nHeight, fi.nWidth).copy()
                cam.MV_CC_FreeImageBuffer(frame)
        cam.MV_CC_StopGrabbing()
        if img is None:
            return {**res, "error": "ingen ram (timeout)"}
        path = os.path.join(out_dir, f"snapshot_{serial}.png")
        saved = _save_png(img, path)
        res.update(shape=tuple(img.shape), min=int(img.min()), max=int(img.max()),
                   mean=round(float(img.mean()), 1),
                   saturated_pct=round(100.0 * float((img >= 250).mean()), 2),
                   path=saved)
    finally:
        cam.MV_CC_CloseDevice(); cam.MV_CC_DestroyHandle()
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exposure", type=float, default=None, help="exponering i µs (utelämna=auto)")
    ap.add_argument("--out", default=os.getcwd(), help="mål-katalog för PNG")
    args = ap.parse_args()

    try: MvCamera.MV_CC_Initialize()
    except Exception: pass
    devs = MV_CC_DEVICE_INFO_LIST()
    if MvCamera.MV_CC_EnumDevices(MV_USB_DEVICE, devs) != 0:
        print("MV_CC_EnumDevices misslyckades."); return 1
    if devs.nDeviceNum == 0:
        print("Inga USB-kameror hittade."); return 1
    os.makedirs(args.out, exist_ok=True)
    print(f"Hittade {devs.nDeviceNum} kamera(or).")
    for i in range(devs.nDeviceNum):
        info = cast(devs.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
        r = snap_one(info, args.exposure, args.out)
        if "error" in r:
            print(f"  S/N {r['serial']}: FEL — {r['error']}")
        else:
            print(f"  S/N {r['serial']}: {r['shape']} sparad → {r['path']}")
            print(f"     min/mean/max={r['min']}/{r['mean']}/{r['max']}  mättat={r['saturated_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
