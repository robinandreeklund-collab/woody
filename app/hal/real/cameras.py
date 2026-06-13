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
        import os, glob
        h = Harvester()
        # GenTL-producenter (.cti): MVS delar upp dem per buss — MvProducerU3V.cti
        # (USB3-profilkameror) och MvProducerGEV.cti (GigE-linjekamera). Ladda BÅDA
        # så hela kamerakedjan hittas. GENICAM_CTI = enskild fil; GENICAM_GENTL64_PATH
        # = katalog vi scannar efter alla *.cti (MVS/Aravis levererar dem).
        ctis: list[str] = []
        single = os.environ.get("GENICAM_CTI")
        if single:
            ctis.append(single)
        gentl_dir = os.environ.get("GENICAM_GENTL64_PATH")
        if gentl_dir and os.path.isdir(gentl_dir):
            ctis += sorted(glob.glob(os.path.join(gentl_dir, "*.cti")))
        for cti in dict.fromkeys(ctis):            # dedupe, behåll ordning
            if os.path.exists(cti):
                h.add_file(cti)
        h.update()
        _HARVESTER = h
    return _HARVESTER


# ───────────────────── GenICam-inställningar (styr kameran från koden) ──────────
# Vendor-neutralt: varje kamerafunktion (exponering, gain, line-rate, trigger,
# vitbalans …) är en namngiven GenICam-nod enligt SFNC-standarden. Vi sätter dem
# säkert — fel/okänt namn loggas och hoppas över, så samma kod funkar mot olika
# modeller. Kör tools/dump_camera_features.py mot ansluten kamera för de EXAKTA
# nodnamnen den exponerar (de varierar; defaults nedan är SFNC-standardnamn).

def apply_genicam_features(node_map, features: dict, log_prefix: str = "") -> dict:
    """Sätt varje {feature: värde} på kamerans node-map. None-värden hoppas över.
    Returnerar {feature: (ok, värde-eller-feltext)} för loggning/verifiering."""
    results: dict = {}
    for name, value in features.items():
        if value is None:
            continue
        try:
            getattr(node_map, name).value = value
            results[name] = (True, getattr(node_map, name).value)
        except Exception as exc:                # okänd nod / fel typ / read-only
            results[name] = (False, str(exc))
            print(f"[kamera{log_prefix}] kunde inte sätta {name}={value!r}: {exc}")
    return results


def read_genicam_features(node_map, names) -> dict:
    """Läs aktuella värden för en lista features (None om noden saknas)."""
    out: dict = {}
    for name in names:
        try:
            out[name] = getattr(node_map, name).value
        except Exception:
            out[name] = None
    return out


def dump_genicam_features(node_map) -> list:
    """Lista (namn, värde) för alla läsbara features — för upptäckt/kalibrering.
    Harvester exponerar feature-noder som attribut på node-mapen."""
    rows = []
    for name in sorted(n for n in dir(node_map) if n[:1].isupper()):
        try:
            rows.append((name, getattr(getattr(node_map, name), "value", None)))
        except Exception:
            continue
    return rows


# Standard-features (SFNC). Slås ihop med per-kamera-overrides från config/kalibrering.
# Profilkamera: mono höghastighet, fri ström @60fps (laserstripe i Mono8).
DEFAULT_PROFILE_FEATURES = {
    "PixelFormat": "Mono8",
    "AcquisitionMode": "Continuous",
    "TriggerMode": "Off",
    "ExposureAuto": "Off",
    "GainAuto": "Off",
}
# Linjekamera: färg, encoder-triggad line-scan (encoder band B → Line0).
DEFAULT_SURFACE_FEATURES = {
    "PixelFormat": "RGB8",
    "TriggerMode": "On",
    "TriggerSource": "Line0",
    "TriggerActivation": "RisingEdge",
    "ExposureAuto": "Off",
    "GainAuto": "Off",
    "BalanceWhiteAuto": "Off",
}


class GenICamProfileCamera(ProfileCameraIF):
    def __init__(self, color: str, serial: str | None = None,
                 roi_rows: int = 80, exposure_us: float = 800.0,
                 features: dict | None = None):
        self._color = color
        self._serial = serial
        self._roi_rows = roi_rows
        self._exposure_us = exposure_us
        self._ia = None
        self._connected = False
        self._extractor = None        # GPU/CPU stripe-extraktor (lazy)
        # GenICam-inställningar: defaults + overrides (från config/kalibrering)
        self._features = {**DEFAULT_PROFILE_FEATURES, **(features or {})}

    def info(self) -> DeviceInfo:
        nm = "RÖD 650" if self._color == "red" else "GRÖN 520"
        return DeviceInfo(f"Profilkamera {nm}", "Hikrobot MV-CS050-10UM", "USB3 Vision", self._connected)

    def open(self) -> None:
        h = _harvester()
        kw = {"serial_number": self._serial} if self._serial else {}
        self._ia = h.create(search_key=kw or None)
        # ExposureTime drivs av self._exposure_us men kan överstyras via features
        feats = {"ExposureTime": self._exposure_us, **self._features}
        apply_genicam_features(self._ia.remote_device.node_map, feats,
                               log_prefix=f" {self._color}")
        self._ia.start()
        self._connected = True

    def configure(self, **features) -> dict:
        """Uppdatera kamerainställningar (defaults + nu) — appliceras direkt om ansluten."""
        self._features.update(features)
        if self._connected and self._ia is not None:
            return apply_genicam_features(self._ia.remote_device.node_map, features,
                                          log_prefix=f" {self._color}")
        return {}

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
        # GPU-accelererad stripe-extraktion (CuPy på Jetson, numpy fallback) — keep-up
        # @ 60 fps kräver GPU vid full upplösning (se docs/jetson-prep-plan.md §Fas B).
        from ...processing.triangulate import centroid_to_z
        if self._extractor is None:
            from ...processing.stripe_gpu import StripeExtractor
            self._extractor = StripeExtractor()
            self._extractor.warmup(self._roi_rows, 2448)
        return centroid_to_z(self._extractor.process(self.read_stripe(y_mm)))

    def close(self) -> None:
        if self._ia:
            self._ia.stop(); self._ia.destroy()
        self._connected = False


class GenICamSurfaceCamera(SurfaceCameraIF):
    def __init__(self, serial: str | None = None, features: dict | None = None):
        self._serial = serial
        self._ia = None
        self._connected = False
        self._rows: list = []        # ackumulerade rad-skanningar (en bräda)
        # GenICam-inställningar: defaults + overrides (encoder-trig, vitbalans, line-rate …)
        self._features = {**DEFAULT_SURFACE_FEATURES, **(features or {})}

    def info(self) -> DeviceInfo:
        return DeviceInfo("Ytkamera 4K färg (linjekamera)", "HT-GELM44C-T2 (4096 px, encoder-trig)",
                          "GigE Vision", self._connected)

    def open(self) -> None:
        h = _harvester()
        kw = {"serial_number": self._serial} if self._serial else {}
        self._ia = h.create(search_key=kw or None)
        apply_genicam_features(self._ia.remote_device.node_map, self._features,
                               log_prefix=" yta")
        self._ia.start()
        self._connected = True

    def configure(self, **features) -> dict:
        """Uppdatera kamerainställningar (encoder-trig, exponering, gain, vitbalans,
        line-rate, ROI …) — appliceras direkt om ansluten. Källa: kalibrering/kod."""
        self._features.update(features)
        if self._connected and self._ia is not None:
            return apply_genicam_features(self._ia.remote_device.node_map, features,
                                          log_prefix=" yta")
        return {}

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
