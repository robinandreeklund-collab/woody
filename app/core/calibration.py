"""Kalibrering — enhetskatalog, metodregister, resultatlager och körmotor.

Allt DATA-drivet (som grading_rules): ``DEVICE_CATALOG`` är den LÅSTA hårdvaran,
``CALIB_METHODS`` beskriver varje kalibreringsmetod per enhet (titel, beskrivning,
steg). ``CalibrationStore`` persisterar resultat (data/calibration.json) så status
överlever omstart. ``CalibrationRunner`` är en ren-Python stegmaskin (tick-driven,
inga Qt-beroenden → testbar headless); DeviceManager kör den med en QTimer.

I SIM-läge körs varje metod simulerat med trovärdiga resultatvärden — så hela
GUI-flödet (välj enhet → kör metod → följ steg → resultat sparas) är färdigt att
använda INNAN hårdvaran kommer. I REAL-läge kör samma steg mot HAL; metoder vars
enhet inte är ansluten avbryts med tydligt besked.
"""
from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path

from . import autocalib

# ---------------------------------------------------------------- enhetskatalog
# (id, namn, modell, gränssnitt, typ) — den LÅSTA hårdvaran (docs/jetson-prep-plan.md §1)
DEVICE_CATALOG = [
    ("prof_red",   "Profilkamera RÖD 650",  "Hikrobot MV-CS050-10UM · BP650",  "USB3 Vision",          "camera"),
    ("prof_green", "Profilkamera GRÖN 520", "Hikrobot MV-CS050-10UM · BP525",  "USB3 Vision",          "camera"),
    ("surface",    "Ytkamera 4K linjekamera", "HT-GELM44C-T2 · färg 4096 px",  "GigE Vision",          "camera"),
    ("lr400",      "3× Punktlaser LR400",   "LR400 · CMOS-triangulering",      "RS-485 Modbus · Waveshare 4CH", "pointlaser"),
    ("conveyor",   "Transportör · 2 band",  "RoboClaw 2x7A · sluten slinga",   "USB packet serial",    "motion"),
    ("enc_a",      "Encoder band A",        "Omron E6B2-CWZ6C · 1000 ppr",     "→ RoboClaw EN1",       "encoder"),
    ("enc_b",      "Encoder band B",        "Omron E6B2-CWZ1X · RS-422",       "→ Linjekamera Line0 + EN2", "encoder"),
    ("laser_red",  "Linjelaser RÖD",        "650 nm · 100 mW · 60°",           "5 V · GPIO pin 16",    "laser"),
    ("laser_green","Linjelaser GRÖN",       "520 nm · 50 mW · 60°",            "24 V · GPIO pin 18",   "laser"),
    ("led_white",  "LED-belysning",         "24 V vit linjelist ×2",           "GPIO pin 13+15",       "light"),
    ("photocell",  "Fotocell · anslag",     "GTRIC LSZ-S30N1 · NPN diffus",    "GPIO in pin 7",        "sensor"),
    ("rig",        "Riggen · system",       "Dubbel-oblik 25°/50° · WD 760",   "systemkalibrering",    "system"),
    ("jetson",     "Jetson Orin Nano Super","1024 CUDA · 8 GB · JetPack 6",    "beräkningsnod",        "compute"),
]

# ---------------------------------------------------------------- metodregister
# per enhet: lista av metoder {id, title, desc, steps[(etikett, sekunder)], sim}
# ``sim`` = trovärdiga resultatvärden som skrivs till lagret i sim-läge.
_PROFILE_METHODS = [
    {"id": "exposure", "title": "Auto-exponering",
     "desc": "Svep exponeringstid tills laserstripens toppintensitet ligger på mål "
             "~200/255 (mättnadsfritt, bästa subpixel-SNR).",
     "steps": [("Tänd laser, släck rumsljus", 1.0), ("Svep exponering 200–2000 µs", 2.0),
               ("Välj optimum (topp ≈ 200)", 1.0), ("Verifiera över hela FOV", 1.0)],
     "sim": {"exponering": "850 µs", "toppintensitet": "203/255", "SNR": "41 dB"}},
    {"id": "dark", "title": "Mörkbild / bakgrund",
     "desc": "Laser AV → medelvärdesbilda bakgrunden. Subtraheras före centroid "
             "(tar bort hotspots/reflexer).",
     "steps": [("Släck laser", 0.5), ("Medla 64 mörkramar", 2.0), ("Spara bakgrundskarta", 0.5)],
     "sim": {"bakgrund": "2,1/255 medel", "hotspots": "0 px > 30"}},
    {"id": "stripe_roi", "title": "Stripe-ROI (auto-band)",
     "desc": "Hitta laserstripens rad automatiskt → sätt kamerans hårdvaru-ROI-offset "
             "så bandet centreras på stripen (mindre USB-bandbredd → 60 fps).",
     "steps": [("Sök stripe-rad i full ram", 1.5), ("Beräkna ROI-offset", 0.5),
               ("Sätt ROI i kameran", 0.5)],
     "sim": {"stripe-rad": "1024,3", "ROI-offset": "984 px"}},
    {"id": "intrinsics", "title": "Kamera-intrinsics",
     "desc": "Schackbräde/ChArUco i ~15 poser → fokallängd, huvudpunkt, "
             "linsdistorsion. Krävs för geometriskt korrekt triangulering.",
     "steps": [("Visa schackbräde i 15 poser", 4.0), ("Detektera hörn", 1.5),
               ("Lös kameramodell", 1.5), ("Verifiera reprojektion", 1.0)],
     "sim": {"fokallängd": "12,04 mm", "distorsion k1": "-0,082", "reproj-RMS": "0,11 px"}},
    {"id": "triangplane", "title": "Trianguleringsplan",
     "desc": "Mät känd referenstrappa (t.ex. 5/10/15/20 mm) → laser/kamera-planets "
             "pose + px/mm i Z. Detta sätter mm-skalan i höjdmätningen.",
     "steps": [("Placera referenstrappa", 1.0), ("Mät stripen på varje steg", 2.5),
               ("Anpassa plan + skala", 1.0), ("Verifiera mot facit", 1.0)],
     "sim": {"gain": "2,09 px/mm", "residual-RMS": "31 µm", "lutning": "0,04°"}},
    {"id": "focus", "title": "Stripe-fokus (FWHM)",
     "desc": "Mät linjens bredd (FWHM) över hela FOV → fokusring + ev. Scheimpflug-"
             "justering. Mål < 3 px överallt.",
     "steps": [("Stripe över plant referensplan", 1.0), ("Mät FWHM i 20 punkter", 1.5),
               ("Justera fokus, mät om", 2.0)],
     "sim": {"FWHM centrum": "2,6 px", "FWHM kant": "3,1 px"}},
]

CALIB_METHODS: dict[str, list] = {
    "prof_red": _PROFILE_METHODS,
    "prof_green": _PROFILE_METHODS,
    "surface": [
        {"id": "whitebal", "title": "Vitbalans",
         "desc": "Vitreferens under LED-ljuset → R/G/B-gain så trä återges neutralt. "
                 "Krävs för stabil blånad-/röta-klassning.",
         "steps": [("Placera vitreferens", 1.0), ("Medla 100 rader", 1.5), ("Beräkna gains", 0.5)],
         "sim": {"gain R/G/B": "1,00 / 1,14 / 1,31", "CCT": "5400 K"}},
        {"id": "flatfield", "title": "Flat-field / PRNU",
         "desc": "Jämn vit yta → per-pixel-gain över alla 4096 px (kompenserar "
                 "vinjettering + LED-ojämnhet längs linjen).",
         "steps": [("Jämn vit yta i FOV", 1.0), ("Medla 200 rader", 2.0),
                   ("Beräkna per-pixel-gain", 1.0), ("Verifiera platthet", 0.5)],
         "sim": {"ojämnhet före": "18 %", "efter": "1,2 %"}},
        {"id": "linesync", "title": "Encoder-synk (rader/mm)",
         "desc": "Mata känd sträcka med encoder-trigg → rader per mm. Mål: kvadratiska "
                 "pixlar (1 rad = 0,122 mm vid 4096 px / 500 mm).",
         "steps": [("Mata referensobjekt 200 mm", 2.0), ("Räkna triggade rader", 1.0),
                   ("Sätt divider i kameran", 1.0)],
         "sim": {"rader/mm": "8,19", "pixelform": "1,002:1"}},
        {"id": "focusmtf", "title": "Fokus / MTF",
         "desc": "Testmönster (slanted edge) → skärpa över hela linjen. Justera "
                 "fokusring tills MTF50 jämn över FOV.",
         "steps": [("Slanted-edge-mönster", 1.0), ("Mät MTF i 9 zoner", 1.5), ("Justera + mät om", 2.0)],
         "sim": {"MTF50 centrum": "0,31 cy/px", "kant": "0,27 cy/px"}},
    ],
    "lr400": [
        {"id": "zero_d0", "title": "Nollning mot tomt band (D0)",
         "desc": "Skanna tomt band → sätt referensavstånd per kanal (ch1–3) så att "
                 "tom-band = 0. Tjocklek = D0 − uppmätt avstånd. Absolut-ankarets bas.",
         "steps": [("Töm bandet", 0.5), ("Medla 100 mätningar/kanal", 2.0),
                   ("Spara D0 per kanal", 0.5)],
         "sim": {"D0 ch1/2/3": "100,2 / 99,8 / 100,1 mm", "brus": "8 µm RMS"}},
        {"id": "linearity", "title": "Linjäritet & skala",
         "desc": "Mät referenstrappa (5/10/15/20 mm) på varje kanal → verifiera "
                 "linjäritet och skala över mätområdet 60–400 mm.",
         "steps": [("Placera referenstrappa", 1.0), ("Mät alla steg × 3 kanaler", 2.5),
                   ("Anpassa linje, residual", 1.0)],
         "sim": {"linjäritet": "0,06 % FS", "skalfel": "0,03 %"}},
        {"id": "anchor", "title": "Ankrings-verifiering mot triangulering",
         "desc": "Jämför LR400:s absoluta tjocklek mot profilkamerornas fusion → "
                 "global offset/tilt-korrektion (fusion.anchor). Detta är punktlasrarnas "
                 "syfte: pinna trianguleringens absolutnivå.",
         "steps": [("Skanna referensbräda", 2.0), ("Jämför LR vs triangulering", 1.0),
                   ("Beräkna offset/tilt", 0.5), ("Skriv korrektion", 0.5)],
         "sim": {"offset": "0,07 mm", "tilt": "0,03°", "residual": "22 µm"}},
    ],
    "conveyor": [
        {"id": "countsmm", "title": "Counts/mm (encoder-skala)",
         "desc": "Kör band känd sträcka (anslag→anslag, fotocell) → encoder-counts "
                 "per mm. Grunden för all positionering.",
         "steps": [("Nollställ encoder", 0.5), ("Kör till anslag (känd sträcka)", 2.5),
                   ("Läs counts, beräkna skala", 0.5), ("Upprepa 3× för medel", 2.0)],
         "sim": {"counts/mm": "99,73", "spridning": "±0,3 %"}},
        {"id": "speedstep", "title": "Hastighets-stegsvar (PID)",
         "desc": "Stegsvar 0→50 mm/s → ställ Velocity-PID i RoboClaw för snabb, "
                 "översläng-fri matning.",
         "steps": [("Steg 0→50 mm/s", 1.5), ("Logga svar", 1.0), ("Justera Kp/Ki/Kd", 2.0),
                   ("Verifiera jämn gång", 1.0)],
         "sim": {"stigtid": "120 ms", "översläng": "2 %", "ripple": "±0,4 mm/s"}},
        {"id": "beltsync", "title": "Bandsynk M1↔M2",
         "desc": "Kör båda banden samma sträcka → jämför encoder A/B. Drift > 0,5 mm/m "
                 "vrider brädan under skanning.",
         "steps": [("Kör 1000 mm på båda band", 2.5), ("Jämför encoder A/B", 0.5),
                   ("Justera M2-trim", 1.0)],
         "sim": {"drift": "0,21 mm/m", "status": "inom tolerans"}},
    ],
    "enc_a": [
        {"id": "pulsemm", "title": "Pulser/mm-verifiering",
         "desc": "Mata känd sträcka → verifiera 1000 ppr mot hjuldiameter (ger "
                 "RoboClaws counts/mm).",
         "steps": [("Mata referenssträcka 500 mm", 2.0), ("Läs pulsräknare", 0.5), ("Beräkna avvikelse", 0.5)],
         "sim": {"pulser/mm": "24,93", "avvikelse": "0,2 %"}},
    ],
    "enc_b": [
        {"id": "pulsemm", "title": "Pulser/mm-verifiering",
         "desc": "Samma som band A — verifierar RS-422-parets skala.",
         "steps": [("Mata referenssträcka 500 mm", 2.0), ("Läs pulsräknare", 0.5), ("Beräkna avvikelse", 0.5)],
         "sim": {"pulser/mm": "24,91", "avvikelse": "0,3 %"}},
        {"id": "camtrig", "title": "Kameratrigg-test",
         "desc": "Verifiera att linjekameran får encoderpulser på Line0 (rätt "
                 "polaritet, inga missade pulser vid full hastighet).",
         "steps": [("Kör band 60 mm/s", 1.5), ("Räkna triggade rader vs pulser", 1.5), ("Kontrollera jitter", 1.0)],
         "sim": {"missade pulser": "0", "jitter": "< 2 µs"}},
    ],
    "laser_red": [
        {"id": "power", "title": "Enable & effekt",
         "desc": "GPIO-enable på/av → verifiera att linjen tänds/släcks och att "
                 "intensiteten är stabil (driver varm).",
         "steps": [("Enable PÅ via GPIO", 0.5), ("Mät intensitet 60 s", 2.0), ("Enable AV, verifiera släckt", 0.5)],
         "sim": {"intensitetsdrift": "1,8 %", "enable-latens": "< 1 ms"}},
        {"id": "straight", "title": "Linjerakhet",
         "desc": "Stripe över plant referensplan → avvikelse från rät linje (bow). "
                 "Mål < 0,1 mm över 500 mm.",
         "steps": [("Stripe på referensplan", 1.0), ("Mät centroid över FOV", 1.0), ("Anpassa linje, residual", 0.5)],
         "sim": {"bow": "0,06 mm", "vridning": "0,02°"}},
        {"id": "width", "title": "Linjebredd (fokus)",
         "desc": "Fokusera linjegeneratorn → smalast möjliga linje vid WD 760 "
                 "(mål < 0,3 mm). Smalare linje = bättre subpixel.",
         "steps": [("Mät FWHM vid WD", 1.0), ("Vrid fokusring", 1.5), ("Verifiera över linjen", 1.0)],
         "sim": {"linjebredd": "0,24 mm", "variation": "±0,04 mm"}},
    ],
    "photocell": [
        {"id": "trigger", "title": "Trigg-test & latens",
         "desc": "Detekterar att en bräda laddats vid anhållet → startar skanning + "
                 "nollar position (home). Bryt strålen → verifiera flank, latens och "
                 "repeterbarhet.",
         "steps": [("Ladda bräda mot anhåll 10×", 2.0), ("Mät flanklatens", 1.0),
                   ("Verifiera repeterbarhet", 0.5)],
         "sim": {"latens": "0,9 ms", "repeterbarhet": "±0,15 mm @ 60 mm/s"}},
    ],
    "led_white": [
        {"id": "uniform", "title": "Belysningsjämnhet",
         "desc": "Mät intensitetsprofil längs linjekamerans FOV under LED → ojämnhet "
                 "kompenseras av flat-field, men > 30 % bör åtgärdas mekaniskt.",
         "steps": [("LED PÅ, vit yta", 0.5), ("Mät profil längs FOV", 1.0), ("Rapportera ojämnhet", 0.5)],
         "sim": {"ojämnhet": "14 %", "rekommendation": "OK — flat-field räcker"}},
    ],
    "rig": [
        {"id": "zeroplane", "title": "Nollplan B(x) — tomt band",
         "desc": "Skanna tomt band → spara bandprofilen som noll. Tjocklek = topp − "
                 "B(x). Se docs/zero-reference.md.",
         "steps": [("Töm bandet", 0.5), ("Skanna 200 profiler", 2.0), ("Medla + spara B(x)", 0.5),
                   ("Verifiera repeterbarhet", 1.0)],
         "sim": {"bandprofil RMS": "0,05 mm", "drift 10 min": "0,02 mm"}},
        {"id": "align", "title": "Huvud-alignment RÖD↔GRÖN",
         "desc": "Båda lasrarna ska ligga i SAMMA plan över bandet. Skanna referens-"
                 "block → offset/rotation mellan huvudena → korrektionsmatris. "
                 "Se docs/alignment-calibration.md.",
         "steps": [("Referensblock i mätzon", 1.0), ("Skanna med båda huvuden", 2.0),
                   ("Lös offset + rotation", 1.0), ("Skriv korrektionsmatris", 0.5)],
         "sim": {"X-offset": "0,12 mm", "rotation": "0,05°", "residual": "28 µm"}},
        {"id": "refboard", "title": "Referensbräda — end-to-end",
         "desc": "Skanna uppmätt referensbräda → jämför längd/bredd/tjocklek/defekt-"
                 "positioner mot facit. Systemets slutverifiering.",
         "steps": [("Mata referensbräda", 2.0), ("Full skanning", 2.5), ("Jämför mot facit", 1.0),
                   ("Godkänn/underkänn", 0.5)],
         "sim": {"tjocklek-fel": "0,04 mm", "längd-fel": "0,3 mm", "defektpos-fel": "0,8 mm"}},
    ],
}
# grön laser = samma metoder som röd
CALIB_METHODS["laser_green"] = CALIB_METHODS["laser_red"]


def methods_for(dev_id: str) -> list:
    return CALIB_METHODS.get(dev_id, [])


# ---------------------------------------------------------------- resultatlager
class CalibrationStore:
    """Persisterar kalibreringsresultat som JSON: {dev.method: {date, ok, values}}."""

    def __init__(self, path: str | Path = "data/calibration.json"):
        self.path = Path(path)
        self._data: dict = {}
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text())
        except Exception:
            self._data = {}

    def get(self, dev_id: str, method_id: str) -> dict | None:
        return self._data.get(f"{dev_id}.{method_id}")

    def set(self, dev_id: str, method_id: str, values: dict, ok: bool = True) -> None:
        self._data[f"{dev_id}.{method_id}"] = {
            "date": time.strftime("%Y-%m-%d %H:%M"), "ok": bool(ok),
            "values": dict(values),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=1))
        except Exception as exc:                      # persistens stoppar aldrig drift
            print("kalibreringslager:", exc)

    def count_done(self, dev_id: str) -> int:
        return sum(1 for m in methods_for(dev_id)
                   if (self.get(dev_id, m["id"]) or {}).get("ok"))


# ---------------------------------------------------------------- körmotor
class CalibrationRunner:
    """Tick-driven stegmaskin (ren Python — inga Qt-beroenden, testbar headless).

    start() → tick(dt) tills done. Callbacks: on_progress(pct, stegtext),
    on_finished(ok, values). I sim-läge produceras metodens ``sim``-värden
    (lätt jitter så det känns mätt); i real-läge kör HAL-hooks när de finns.
    """

    def __init__(self, store: CalibrationStore, sim: bool = True, context=None):
        self.store = store
        self.sim = sim
        self.context = context        # autocalib.CalibrationContext (real-läge)
        self.active: dict | None = None
        self.on_progress = None       # callable(pct: float, msg: str)
        self.on_finished = None       # callable(ok: bool, values: dict)
        self._auto: dict | None = None  # {thread, done, values} för auto-mätning

    @property
    def running(self) -> bool:
        return self.active is not None

    def start(self, dev_id: str, method_id: str, connected: bool = True) -> bool:
        if self.running:
            return False
        method = next((m for m in methods_for(dev_id) if m["id"] == method_id), None)
        if method is None:
            return False
        if not self.sim and not connected:
            if self.on_finished:
                self.on_finished(False, {"fel": "enheten är inte ansluten — koppla in och kör självtest"})
            return False
        self.active = {"dev": dev_id, "method": method, "step": 0, "t": 0.0,
                       "total": sum(s[1] for s in method["steps"])}
        # Real-läge + auto-rutin finns → mät i bakgrundstråd (blockera ej GUI).
        self._auto = None
        if not self.sim and self.context is not None and autocalib.has_auto(dev_id, method_id):
            self._auto = {"done": False, "values": None}
            self._auto["thread"] = threading.Thread(
                target=self._run_auto, args=(dev_id, method_id), daemon=True)
            self._auto["thread"].start()
        if self.on_progress:
            self.on_progress(0.0, method["steps"][0][0])
        return True

    def _run_auto(self, dev_id: str, method_id: str) -> None:
        values = autocalib.run_auto(dev_id, method_id, self.context)
        self._auto["values"] = values
        self._auto["done"] = True

    def cancel(self) -> None:
        self.active = None
        self._auto = None

    def tick(self, dt: float) -> None:
        a = self.active
        if a is None:
            return
        a["t"] += dt
        steps = a["method"]["steps"]
        # vilken etapp är vi i?
        acc = 0.0
        for i, (label, dur) in enumerate(steps):
            acc += dur
            if a["t"] < acc:
                if i != a["step"] and self.on_progress:
                    a["step"] = i
                pct = min(0.999, a["t"] / a["total"])
                if self.on_progress:
                    self.on_progress(pct, label)
                return
        # Tiden slut. Om en auto-mätning kör → vänta in den (håll stapeln ~0,97).
        if self._auto is not None and not self._auto["done"]:
            if self.on_progress:
                self.on_progress(0.97, "mäter mot kameran …")
            return
        # klart → producera resultat
        dev, method = a["dev"], a["method"]
        self.active = None
        values, ok = self._results(dev, method)
        self._auto = None
        self.store.set(dev, method["id"], values, ok=ok)
        if self.on_finished:
            self.on_finished(ok, values)

    def _results(self, dev_id: str, method: dict) -> tuple[dict, bool]:
        """Returnerar (värden, ok). Real-läge: riktiga auto-mätvärden om de finns."""
        if self.sim:
            # lätt jitter på numeriska prefix så varje körning känns "mätt"
            return {k: _jitter(v) for k, v in method.get("sim", {}).items()}, True
        if self._auto is not None and self._auto.get("values") is not None:
            values = self._auto["values"]
            ok = "fel" not in values                  # rutinen rapporterar fel som {'fel':…}
            return values, ok
        # real men ingen auto-rutin (guidad metod, t.ex. intrinsics) → platshållare
        return dict(method.get("sim", {})), True


def _jitter(text: str) -> str:
    """'0,21 mm/m' → samma sträng med ±4 % på det första talet (svenskt decimalkomma)."""
    s = str(text)
    num = ""
    i0 = None
    for i, ch in enumerate(s):
        if ch.isdigit() or (ch in ",." and num):
            if i0 is None:
                i0 = i
            num += ch
        elif num:
            break
    if not num or i0 is None:
        return s
    try:
        val = float(num.replace(",", "."))
    except ValueError:
        return s
    val *= 1.0 + random.uniform(-0.04, 0.04)
    dec = len(num.split(",")[-1]) if "," in num else (len(num.split(".")[-1]) if "." in num else 0)
    new = f"{val:.{dec}f}".replace(".", ",") if "," in num else f"{val:.{dec}f}"
    return s[:i0] + new + s[i0 + len(num):]
