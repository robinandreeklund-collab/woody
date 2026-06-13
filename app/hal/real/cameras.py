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
    "ExposureAuto": "Off",
    "GainAuto": "Off",
    "BalanceWhiteAuto": "Off",
}


def set_first_available(node_map, candidates, value, log_prefix: str = ""):
    """Sätt 'value' på FÖRSTA noden i 'candidates' som finns och accepterar värdet.

    GenICam-nodnamn varierar mellan modeller/producenter (SFNC-standard vs
    tillverkar-egna). Vi provar en prioriterad lista och använder den som funkar.
    Returnerar (nodnamn, ok). Kör tools/dump_camera_features.py för exakta namn."""
    last = None
    for name in candidates:
        try:
            getattr(node_map, name).value = value
            return (name, True)
        except Exception as exc:               # okänd nod / fel typ / ogiltigt värde
            last = (name, str(exc))
    print(f"[kamera{log_prefix}] ingen av {candidates} gick att sätta={value!r}"
          + (f" (sista fel: {last[1]})" if last else ""))
    return (None, False)


# ── Encoder-triggad line-scan (linjekameran HT-GELM44C-T2, GigE Vision) ──────────
# Huatengs SDK-modell (CameraDefine.h / CameraApi.h):
#   snap-läge ROTARYENC_TRIGGER(3): en bildrad per encoderpuls (band B → Line0).
#   CameraSetRotaryEncDir(dir):  0=båda riktn., 1=medurs (A före B), 2=moturs.
#   CameraSetRotaryEncFreq(mul, div): radtakt = encoderpuls × mul / div (radavstånd).
# På GenICam-standardvägen heter detta enligt SFNC, MEN exakta nodnamn varierar →
# vi provar kandidatlistor (set_first_available) och verifierar mot dump-verktyget.
# Riktnings-värden mappas: "forward"->medurs(1), "reverse"->moturs(2), "both"->0.
_TRIG_CANDS = {
    "selector":   ["TriggerSelector"],                         # -> "LineStart"
    "mode":       ["TriggerMode"],                             # -> "On"
    "source":     ["TriggerSource", "LineSource"],            # encoder-källa
    "activation": ["TriggerActivation"],                       # flank
    "enc_sel":    ["EncoderSelector"],                         # -> "Encoder0"
    "enc_src_a":  ["EncoderSourceA", "RotaryEncoderSourceA"],
    "enc_src_b":  ["EncoderSourceB", "RotaryEncoderSourceB"],
    "enc_mode":   ["EncoderMode", "RotaryEncoderMode"],
    "enc_dir":    ["EncoderDirection", "RotaryEncoderDirection", "RotaryEncDir"],
    "divider":    ["EncoderDivider", "RotaryEncoderDivider", "RotaryEncDiv"],
    "multiplier": ["EncoderMultiplier", "RotaryEncoderMultiplier", "RotaryEncMul"],
    "line_rate":  ["AcquisitionLineRate", "LineRate"],
}
_TRIG_SOURCE_CANDS = ["Encoder0", "RotaryEncoder", "FrequencyConverter", "Line0"]
_TRIG_DIR_VALUES = {"forward": 1, "reverse": 2, "both": 0}


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
        # GenICam-inställningar: defaults + overrides (vitbalans, exponering, gain …)
        self._features = {**DEFAULT_SURFACE_FEATURES, **(features or {})}
        # Encoder-triggad line-scan PÅ som standard (rigg matar förbi → en rad/puls).
        # Parametrar tonas av kalibreringen 'linesync' (divider = rader/mm).
        self._line_trigger: dict | None = dict(
            divider=1, multiplier=1, direction="forward", line_rate_hz=None)

    def info(self) -> DeviceInfo:
        return DeviceInfo("Ytkamera 4K färg (linjekamera)", "HT-GELM44C-T2 (4096 px, encoder-trig)",
                          "GigE Vision", self._connected)

    def open(self) -> None:
        h = _harvester()
        kw = {"serial_number": self._serial} if self._serial else {}
        self._ia = h.create(search_key=kw or None)
        nm = self._ia.remote_device.node_map
        apply_genicam_features(nm, self._features, log_prefix=" yta")
        if self._line_trigger is not None:
            self._apply_line_trigger(nm)
        self._ia.start()
        self._connected = True

    def configure(self, **features) -> dict:
        """Uppdatera kamerainställningar (exponering, gain, vitbalans, ROI …) —
        appliceras direkt om ansluten. Källa: kalibrering/kod."""
        self._features.update(features)
        if self._connected and self._ia is not None:
            return apply_genicam_features(self._ia.remote_device.node_map, features,
                                          log_prefix=" yta")
        return {}

    def configure_encoder_line_trigger(self, *, divider: int = 1, multiplier: int = 1,
                                       direction: str = "forward",
                                       line_rate_hz: float | None = None) -> dict:
        """Ställ encoder-triggad line-scan (band B-encoder → kamerans Line0).

        Mappar Huatengs ROTARYENC_TRIGGER-modell till GenICam-noder med
        kandidat-namnsupplösning. ``divider`` (rader per encoderpuls) kommer från
        kalibreringen 'linesync'; ``direction`` ∈ {forward, reverse, both};
        ``line_rate_hz`` sätter ev. maxradtakt. Appliceras direkt om ansluten,
        annars vid nästa open(). Returnerar {logiskt-namn: (nod, ok)}."""
        self._line_trigger = dict(divider=int(divider), multiplier=int(multiplier),
                                  direction=direction, line_rate_hz=line_rate_hz)
        if self._connected and self._ia is not None:
            return self._apply_line_trigger(self._ia.remote_device.node_map)
        return {}

    def disable_line_trigger(self) -> dict:
        """Stäng av trigg (fri ström) — t.ex. för fokus/justering utan matning."""
        self._line_trigger = None
        if self._connected and self._ia is not None:
            return {"mode": set_first_available(
                self._ia.remote_device.node_map, _TRIG_CANDS["mode"], "Off", " yta")}
        return {}

    def _apply_line_trigger(self, nm) -> dict:
        """Översätt encoder-trigg-parametrarna till GenICam-noder (best-effort)."""
        p = self._line_trigger or {}
        res: dict = {}
        # 1) line-scan-trigg: en rad (LineStart) per puls, flank-triggad
        res["selector"]   = set_first_available(nm, _TRIG_CANDS["selector"], "LineStart", " yta")
        res["mode"]       = set_first_available(nm, _TRIG_CANDS["mode"], "On", " yta")
        res["source"]     = self._set_source(nm)
        res["activation"] = set_first_available(nm, _TRIG_CANDS["activation"], "RisingEdge", " yta")
        # 2) encoder: A/B-faser på Line-ingångar, riktning, divider/multiplikator
        set_first_available(nm, _TRIG_CANDS["enc_sel"], "Encoder0", " yta")
        set_first_available(nm, _TRIG_CANDS["enc_src_a"], "Line0", " yta")
        set_first_available(nm, _TRIG_CANDS["enc_src_b"], "Line1", " yta")
        res["direction"]  = set_first_available(
            nm, _TRIG_CANDS["enc_dir"], _TRIG_DIR_VALUES.get(p.get("direction"), 1), " yta")
        res["divider"]    = set_first_available(nm, _TRIG_CANDS["divider"], p.get("divider", 1), " yta")
        res["multiplier"] = set_first_available(nm, _TRIG_CANDS["multiplier"], p.get("multiplier", 1), " yta")
        if p.get("line_rate_hz"):
            res["line_rate"] = set_first_available(nm, _TRIG_CANDS["line_rate"], p["line_rate_hz"], " yta")
        return res

    def _set_source(self, nm):
        """Encoder-triggkälla: prova nodnamn × värde-kandidater, tyst tills allt fallit."""
        for node in _TRIG_CANDS["source"]:
            for src in _TRIG_SOURCE_CANDS:
                try:
                    getattr(nm, node).value = src
                    return (f"{node}={src}", True)
                except Exception:
                    continue
        print(f"[kamera yta] kunde inte sätta triggkälla "
              f"({_TRIG_CANDS['source']} × {_TRIG_SOURCE_CANDS})")
        return (None, False)

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
