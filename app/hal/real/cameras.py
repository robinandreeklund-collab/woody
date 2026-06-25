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


def _apply_feature(dev, name: str, value) -> bool:
    """Sätt en GenICam-nod på en MvsU3VCamera; väljer setter efter Python-typ.
    bool→SetBool, str→SetEnumByString, int→SetInt (fallback enum), float→SetFloat."""
    if isinstance(value, bool):
        return dev.set_bool(name, value)
    if isinstance(value, str):
        return dev.set_enum(name, value)
    if isinstance(value, int):
        return dev.set_int(name, value) or dev.set_enum(name, str(value))
    if isinstance(value, float):
        return dev.set_float(name, value)
    return False


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
                 roi_offset_y: int | None = None, frame_rate_hz: float | None = 60.0,
                 features: dict | None = None):
        self._color = color
        self._serial = serial          # BIND varje huvud till sitt serienr (RÖD≠GRÖN!)
        self._roi_rows = roi_rows
        self._exposure_us = exposure_us
        self._roi_offset_y = roi_offset_y   # None = centrera bandet; annars kalibrerat
        self._frame_rate_hz = frame_rate_hz
        self._dev = None              # MvsU3VCamera (MVS-SDK, sätts i open())
        self._connected = False
        self._extractor = None        # GPU/CPU stripe-extraktor (lazy)
        self._meas_rows = int(roi_rows) if roi_rows else 80   # mät-band för read_stripe
        # GenICam-inställningar: defaults + overrides (från config/kalibrering)
        self._features = {**DEFAULT_PROFILE_FEATURES, **(features or {})}

    def info(self) -> DeviceInfo:
        nm = "RÖD 650" if self._color == "red" else "GRÖN 520"
        return DeviceInfo(f"Profilkamera {nm}", "Hikrobot MV-CS050-10UM", "USB3 Vision", self._connected)

    def open(self) -> None:
        if self._connected and self._dev is not None:    # idempotent: dubbel-open läcker handtag
            return
        from .mvs_u3v import MvsU3VCamera               # lazy: vendor-SDK
        dev = MvsU3VCamera(self._serial)
        dev.open(pixel_format=self._features.get("PixelFormat", "Mono8"))
        # 1) ROI: roi_rows satt → hårdvaru-ROI (smalt band, 60 fps); None → full ram
        #    (live-preview/idrifttagning så man ser HELA bilden i GUI:t)
        self._apply_roi(dev)
        # 2) exponering + övriga GenICam-features (defaults + overrides)
        dev.set_enum("ExposureAuto", "Off")
        dev.set_float("ExposureTime", float(self._exposure_us))
        for k, v in self._features.items():
            _apply_feature(dev, k, v)
        # 3) bildtakt (free-run): 60 fps per kamera (designkrav vid smalt ROI)
        if self._frame_rate_hz:
            dev.set_bool("AcquisitionFrameRateEnable", True)
            dev.set_float("AcquisitionFrameRate", float(self._frame_rate_hz))
        dev.start()
        self._dev = dev
        self._connected = True

    def _apply_roi(self, dev) -> dict:
        """Sätt sensorområdet. Ordning: nollställ offset → maxa bredd → sätt höjd →
        sätt offset. ``roi_rows`` satt → smalt mät-band (centrerat/kalibrerat) för
        60 fps; ``roi_rows`` None/0 → full höjd (hela bilden, för live-preview)."""
        res: dict = {}
        dev.set_int("OffsetX", 0)
        dev.set_int("OffsetY", 0)
        wmax = dev.get_int_max("Width")
        hmax = dev.get_int_max("Height")
        if wmax:
            res["width"] = dev.set_int("Width", wmax)
        if self._roi_rows and hmax and int(self._roi_rows) < hmax:
            res["height"] = dev.set_int("Height", int(self._roi_rows))
            off = self._roi_offset_y
            if off is None:                            # centrera bandet vertikalt
                off = max(0, (hmax - int(self._roi_rows)) // 2)
            res["offset_y"] = dev.set_int("OffsetY", int(off))
        elif hmax:                                     # full ram
            res["height"] = dev.set_int("Height", hmax)
        return res

    def configure(self, **features) -> dict:
        """Uppdatera kamerainställningar (defaults + nu) — appliceras direkt om ansluten."""
        self._features.update(features)
        if self._connected and self._dev is not None:
            return {k: _apply_feature(self._dev, k, v) for k, v in features.items()}
        return {}

    def configure_roi(self, rows: int | None = None, offset_y: int | None = None) -> dict:
        """Ställ ROI-bandet (höjd + vertikal position) — från alignment-kalibreringen.
        ROI kräver stoppat förvärv → vi stoppar/startar greppet runt omsättningen."""
        if rows is not None:
            self._roi_rows = int(rows)
        self._roi_offset_y = offset_y
        self._meas_rows = int(self._roi_rows) if self._roi_rows else 80
        if self._connected and self._dev is not None:
            self._dev.stop()
            res = self._apply_roi(self._dev)
            self._dev.start()
            return res
        return {}

    def read_stripe(self, y_mm: float = 0.0, n: int = 200) -> np.ndarray:
        """Hämta en ram, beskär mät-bandet runt stripen och skala till (meas_rows, n)."""
        if not self._connected or self._dev is None:
            return np.zeros((self._meas_rows, n))
        arr = self._dev.grab(timeout_ms=500)
        if arr is None:
            return np.zeros((self._meas_rows, n))
        img = arr.astype(np.float64)
        # centrera mät-bandet vertikalt; nedsampla längs linjen till n kolumner
        rows = min(self._meas_rows, img.shape[0])
        r0 = max(0, img.shape[0] // 2 - rows // 2)
        roi = img[r0:r0 + rows]
        cols = np.linspace(0, roi.shape[1] - 1, n).astype(int)
        return roi[:, cols]

    def grab_preview(self, y_mm: float = 0.0, max_dim: int = 600) -> np.ndarray:
        """HELA sensorramen (mono, nedskalad) för live-preview i GUI:t — inte mätning.
        Slaven färglägger den (röd/grön tint) och streamar som cam_red/cam_green."""
        if not self._connected or self._dev is None:
            return np.zeros((2, 2), dtype=np.uint8)
        arr = self._dev.grab(timeout_ms=800)
        if arr is None:
            return np.zeros((2, 2), dtype=np.uint8)
        h, w = arr.shape
        step = max(1, max(h, w) // int(max_dim))
        return arr[::step, ::step]

    def read_profile(self, y_mm: float = 0.0) -> np.ndarray:
        # GPU-accelererad stripe-extraktion (CuPy på Jetson, numpy fallback) — keep-up
        # @ 60 fps kräver GPU vid full upplösning (se docs/jetson-prep-plan.md §Fas B).
        from ...processing.triangulate import centroid_to_z
        if self._extractor is None:
            from ...processing.stripe_gpu import StripeExtractor
            self._extractor = StripeExtractor()
            self._extractor.warmup(self._meas_rows, 2448)
        return centroid_to_z(self._extractor.process(self.read_stripe(y_mm)))

    def close(self) -> None:
        if self._dev is not None:
            self._dev.close()
        self._dev = None
        self._connected = False


class GenICamSurfaceCamera(SurfaceCameraIF):
    def __init__(self, serial: str | None = None, features: dict | None = None):
        self._serial = serial
        self._dev = None             # AravisGigeCamera (GigE Vision via Aravis)
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
        if self._connected and self._dev is not None:   # idempotent
            return
        from .aravis_gige import AravisGigeCamera       # lazy (gi/Aravis)
        dev = AravisGigeCamera(self._serial)
        dev.open(pixel_format=self._features.get("PixelFormat"))
        for k, v in self._features.items():             # exponering/gain/vitbalans (best-effort)
            if k != "PixelFormat":
                _apply_feature(dev, k, v)
        # Encoder-triggad line-scan om konfigurerad — men _apply_line_trigger faller
        # tillbaka på FREE-RUN om kamerans trigg-noder saknas (okända på HT-GELM44C)
        # eller ingen encoder finns → kameran greppar/previewar ändå vid idrifttagning.
        if self._line_trigger is not None:
            self._apply_line_trigger(dev)
        else:
            dev.set_str("TriggerMode", "Off")
        # säkerställ att free-run faktiskt STRÖMMAR (annars greppar preview ingen ram):
        # kontinuerligt läge + exponering + radtakt. Trigg-läget (om encodern finns)
        # överstyr radtakten ändå.
        dev.set_enum("AcquisitionMode", "Continuous")
        dev.set_enum("ExposureAuto", "Off")
        # ljus free-run-preview vid idrifttagning (linjekamera samlar lite ljus/rad
        # utan linjeljus). Liten strip-höjd så ramen ändå hinner bli klar snabbt.
        # OBS: encoder-trigg-läget (riktig skanning) överstyr radtakt/exponering.
        _exp = float(self._features.get("ExposureTime", 50000.0))
        dev.set_float("ExposureTime", _exp) or dev.set_float("ExposureTimeAbs", _exp)
        dev.set_float("Gain", 8.0)
        for _en in ("AcquisitionLineRateEnable", "AcquisitionFrameRateEnable"):
            dev.set_bool(_en, True)
        dev.set_float("AcquisitionLineRate", 2000.0)
        dev.set_float("AcquisitionFrameRate", 100.0)
        dev.start(height=12)                            # liten strip → snabb preview-grab
        self._dev = dev
        self._connected = True

    def configure(self, **features) -> dict:
        """Uppdatera kamerainställningar (exponering, gain, vitbalans, ROI …) —
        appliceras direkt om ansluten. Källa: kalibrering/kod."""
        self._features.update(features)
        if self._connected and self._dev is not None:
            return {k: _apply_feature(self._dev, k, v) for k, v in features.items()}
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
        if self._connected and self._dev is not None:
            return self._apply_line_trigger(self._dev)
        return {}

    def disable_line_trigger(self) -> dict:
        """Stäng av trigg (fri ström) — t.ex. för fokus/justering utan matning."""
        self._line_trigger = None
        if self._connected and self._dev is not None:
            return {"mode": self._dev.set_first(_TRIG_CANDS["mode"], "Off")}
        return {}

    def _apply_line_trigger(self, dev) -> dict:
        """Översätt encoder-trigg-parametrarna till GenICam-noder (best-effort, via Aravis).
        Faller tillbaka på FREE-RUN om triggkällan inte går att sätta (okända noder på
        HT-GELM44C) — annars skulle kameran vänta på obefintliga pulser och aldrig greppa."""
        p = self._line_trigger or {}
        res: dict = {}
        res["selector"]   = dev.set_first(_TRIG_CANDS["selector"], "LineStart")
        res["mode"]       = dev.set_first(_TRIG_CANDS["mode"], "On")
        res["source"]     = self._set_source(dev)
        res["activation"] = dev.set_first(_TRIG_CANDS["activation"], "RisingEdge")
        dev.set_first(_TRIG_CANDS["enc_sel"], "Encoder0")
        dev.set_first(_TRIG_CANDS["enc_src_a"], "Line0")
        dev.set_first(_TRIG_CANDS["enc_src_b"], "Line1")
        res["direction"]  = dev.set_first(_TRIG_CANDS["enc_dir"],
                                          _TRIG_DIR_VALUES.get(p.get("direction"), 1))
        res["divider"]    = dev.set_first(_TRIG_CANDS["divider"], p.get("divider", 1))
        res["multiplier"] = dev.set_first(_TRIG_CANDS["multiplier"], p.get("multiplier", 1))
        if p.get("line_rate_hz"):
            res["line_rate"] = dev.set_first(_TRIG_CANDS["line_rate"], p["line_rate_hz"])
        if not res["source"][1]:                       # ingen triggkälla → free-run
            dev.set_str("TriggerMode", "Off")
            print("[kamera yta] encoder-trigg-noder ej tillgängliga → free-run (preview)")
        return res

    def _set_source(self, dev):
        """Encoder-triggkälla: prova nodnamn × värde-kandidater, tyst tills allt fallit."""
        for node in _TRIG_CANDS["source"]:
            for src in _TRIG_SOURCE_CANDS:
                if dev.set_str(node, src):
                    return (f"{node}={src}", True)
        return (None, False)

    def grab_line(self) -> np.ndarray:
        """En radskanning (RGB) — ackumuleras till en yt-bild medan brädan matas."""
        if not self._connected or self._dev is None:
            return np.zeros((0, 3), np.uint8)
        frame = self._dev.grab(timeout_ms=500)
        if frame is None:
            return np.zeros((0, 3), np.uint8)
        if frame.ndim == 2:                            # mono → 3 kanaler
            frame = np.dstack([frame, frame, frame])
        return frame.reshape(-1, 3).astype(np.uint8)

    def surface_image(self) -> np.ndarray:
        """Live yt-strip (H×4096×3) för preview — greppar en färsk ram om ansluten."""
        if self._connected and self._dev is not None:
            frame = self._dev.grab(timeout_ms=800)
            if frame is not None:
                return np.dstack([frame] * 3) if frame.ndim == 2 else frame.astype(np.uint8)
        return np.array(self._rows, dtype=np.uint8) if self._rows else np.zeros((2, 2, 3), np.uint8)

    def close(self) -> None:
        if self._dev is not None:
            self._dev.close()
        self._dev = None
        self._connected = False
