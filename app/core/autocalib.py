"""Automatiska kalibreringsrutiner som MÄTER mot riktiga kameror.

CalibrationRunner kör dessa i real-läge (annars sim-attrapp). Rutinerna är delade
i två lager:

  * **Rena mätfunktioner** (numpy in → värden ut) — testbara helt utan hårdvara.
  * **Kontext-adapter** (``CalibrationContext``) som ger rutinerna kameraåtkomst
    (grab-ramar, sätt exponering, släck laser) via HAL-scannern.

⚠️ LASER-SÄKERHET: ingen rutin TÄNDER lasern (klass 3B). De släcker bara (alltid
säkert) eller förutsätter att operatören tänt den enligt metodens steg (interlock,
skyddsglasögon). Saknas stripen returneras ett fel som ber operatören tända lasern.
"""
from __future__ import annotations

import time

import numpy as np

# ───────────────────────────── rena mätfunktioner ──────────────────────────────

def stripe_profile(img: np.ndarray) -> np.ndarray:
    """Bakgrundssubtraherad intensitet per rad (medel över kolumner). (rows,)"""
    a = np.asarray(img, dtype=np.float64)
    bg = np.median(a, axis=0, keepdims=True)        # bakgrund per kolumn
    sig = np.clip(a - bg, 0, None)
    return sig.mean(axis=1)


def stripe_peak(img: np.ndarray) -> float:
    """Toppintensitet (0–255-skala) för laserstripen i en ROI-ram."""
    a = np.asarray(img, dtype=np.float64)
    bg = np.median(a, axis=0, keepdims=True)
    return float(np.clip(a - bg, 0, None).max())


def find_stripe_row(img: np.ndarray) -> float:
    """Subpixel-rad där stripen ligger (intensitetstyngdpunkt). NaN om ingen stripe."""
    prof = stripe_profile(img)
    if prof.max() < 3.0:                              # ingen tydlig stripe
        return float("nan")
    rows = np.arange(prof.size, dtype=np.float64)
    w = prof ** 2                                     # tyngdpunkt, brusrobust
    return float((rows * w).sum() / w.sum())


def stripe_fwhm(img: np.ndarray) -> float:
    """Stripens bredd (FWHM) i rader, mätt på den kolumn-medlade profilen."""
    prof = stripe_profile(img)
    peak = prof.max()
    if peak < 3.0:
        return float("nan")
    half = peak / 2.0
    above = np.where(prof >= half)[0]
    if above.size < 2:
        return 1.0
    return float(above[-1] - above[0] + 1)


def estimate_snr(img: np.ndarray) -> float:
    """SNR (dB) = topp / brus, där brus = std i bakgrunden (under stripen)."""
    a = np.asarray(img, dtype=np.float64)
    bg = np.median(a, axis=0, keepdims=True)
    resid = a - bg
    peak = np.clip(resid, 0, None).max()
    noise = resid[resid < peak * 0.1].std() or 1e-6
    return float(20.0 * np.log10(max(peak, 1e-6) / noise))


def auto_exposure(grab, set_exposure, target: float = 200.0,
                  lo_us: float = 100.0, hi_us: float = 2000.0, steps: int = 12) -> dict:
    """Svep exponeringstid → välj den där stripens topp ligger närmast ``target``
    (mättnadsfritt). ``grab()`` ger en ROI-ram, ``set_exposure(us)`` ställer kameran.
    Returnerar uppmätta värden eller {'fel': …} om ingen stripe hittas (laser av?)."""
    xs = np.linspace(lo_us, hi_us, steps)
    best = None
    for us in xs:
        set_exposure(float(us))
        peak = stripe_peak(grab())
        # bästa = närmast target men UNDER mättnad (250); straffa övermättnad hårt
        cost = abs(peak - target) + (1000.0 if peak >= 250 else 0.0)
        if best is None or cost < best[0]:
            best = (cost, float(us), peak)
    _, us, peak = best
    set_exposure(us)
    final = np.asarray(grab(), dtype=np.float64)
    # Stripe-närvaro via KOLUMN-MEDLAD profil (brus medlas bort, robust mot enstaka
    # hot-pixels). Lågt = ingen laserstripe → lasern är av.
    if float(stripe_profile(final).max()) < 4.0:
        return {"fel": "ingen laserstripe sedd — tänd lasern (interlock!) och kör om"}
    peak = stripe_peak(final)
    snr = estimate_snr(final)
    return {"exponering": f"{us:.0f} µs", "toppintensitet": f"{peak:.0f}/255",
            "SNR": f"{snr:.0f} dB"}


def dark_stats(grab, n: int = 32, hot_thresh: float = 30.0) -> dict:
    """Medelvärdesbilda ``n`` ramar (laser AV) → bakgrundsnivå + antal hotspots."""
    acc = None
    for _ in range(max(1, n)):
        f = np.asarray(grab(), dtype=np.float64)
        acc = f if acc is None else acc + f
    mean_img = acc / max(1, n)
    hotspots = int((mean_img > hot_thresh).sum())
    return {"bakgrund": f"{mean_img.mean():.1f}/255 medel",
            "hotspots": f"{hotspots} px > {hot_thresh:.0f}"}


def focus_fwhm(grab, samples: int = 5) -> dict:
    """Mät stripe-FWHM i mitten och vid kanterna (flera ramar) → fokus-utfall."""
    widths = [stripe_fwhm(np.asarray(grab(), dtype=np.float64)) for _ in range(max(1, samples))]
    widths = [w for w in widths if np.isfinite(w)]
    if not widths:
        return {"fel": "ingen stripe — tänd lasern och kör om"}
    return {"FWHM centrum": f"{np.median(widths):.1f} px",
            "FWHM max": f"{np.max(widths):.1f} px"}


def stripe_roi_offset(img: np.ndarray, roi_rows: int, sensor_rows: int | None = None) -> dict:
    """Hitta stripe-raden i en (helst osövergripande) ram → ROI-offset så bandet
    centreras på stripen. Returnerar offset (klippt mot sensorn) + stripe-rad."""
    row = find_stripe_row(img)
    if not np.isfinite(row):
        return {"fel": "ingen stripe — tänd lasern och kör om"}
    full = sensor_rows if sensor_rows is not None else int(np.asarray(img).shape[0])
    offset = int(round(row - roi_rows / 2.0))
    offset = max(0, min(offset, max(0, full - roi_rows)))
    return {"stripe-rad": f"{row:.1f}", "ROI-offset": f"{offset} px",
            "_offset_y": offset}                      # _-prefix: maskinvärde, ej visning


def white_balance(rows: np.ndarray) -> dict:
    """Per-kanal-gain så att en vitreferens blir neutral. ``rows`` = (N,3) RGB."""
    a = np.asarray(rows, dtype=np.float64).reshape(-1, 3)
    means = a.mean(axis=0)
    means[means < 1e-6] = 1e-6
    ref = means.max()                                 # höj de svagare kanalerna till max
    g = ref / means
    g = g / g[1]                                      # normalisera mot grön (=1.00)
    # grov färgtemperatur ur R/B-förhållandet (heuristik)
    cct = int(round(6500 * float(np.clip(means[2] / means[0], 0.5, 1.5))))
    return {"gain R/G/B": f"{g[0]:.2f} / {g[1]:.2f} / {g[2]:.2f}", "CCT": f"{cct} K",
            "_gain_r": float(g[0]), "_gain_g": float(g[1]), "_gain_b": float(g[2])}


def flat_field(rows: np.ndarray) -> dict:
    """Jämn vit yta → per-pixel-gain (vinjettering/PRNU). ``rows`` = (N, W[,3])."""
    a = np.asarray(rows, dtype=np.float64)
    prof = a.reshape(a.shape[0], a.shape[1], -1).mean(axis=(0, 2))   # medel per kolumn
    m = prof.mean() or 1e-6
    before = float(prof.std() / m)                    # relativ ojämnhet före
    gain = m / np.clip(prof, 1e-6, None)              # korrektion
    after = float((prof * gain).std() / m)            # ≈ 0 efter
    return {"ojämnhet före": f"{before*100:.1f} %", "efter": f"{after*100:.2f} %"}


# -- linjelaser (profilkamera) + fotocell --

def line_straightness(img: np.ndarray) -> dict:
    """Laserstripens rakhet: stripe-rad per kolumn → linjeanpassning → bow (px) + vridning."""
    a = np.asarray(img, dtype=np.float64)
    bg = np.median(a, axis=0, keepdims=True)
    sig = np.clip(a - bg, 0, None)
    rows = np.arange(a.shape[0], dtype=np.float64)[:, None]
    w = sig ** 2
    denom = w.sum(axis=0)
    m = denom > (float(sig.max()) ** 2) * 0.05 if sig.max() > 0 else np.zeros(a.shape[1], bool)
    if m.sum() < 2:
        return {"fel": "ingen stripe — tänd lasern (interlock!) och kör om"}
    centroid = (rows * w).sum(axis=0) / np.where(denom > 0, denom, 1.0)
    cols = np.arange(a.shape[1], dtype=np.float64)
    coef = np.polyfit(cols[m], centroid[m], 1)
    bow = float(np.max(np.abs(centroid[m] - np.polyval(coef, cols[m]))))
    angle = float(np.degrees(np.arctan(coef[0])))
    return {"bow": f"{bow:.2f} px", "vridning": f"{angle:.2f}°"}


def laser_power_stability(grab, n: int = 30) -> dict:
    """Mät laserstripens toppintensitet över n ramar → medel + drift (% av medel).
    Driver/optik-stabilitet. ``grab`` ger en profil-ROI (lasern ska redan lysa)."""
    a = np.asarray([stripe_peak(np.asarray(grab(), np.float64)) for _ in range(max(2, n))])
    if a.max() < 5.0:
        return {"fel": "ingen laserstripe — kontrollera laser/optik/exponering"}
    drift = float((a.max() - a.min()) / a.mean() * 100.0)
    return {"toppintensitet": f"{a.mean():.0f}/255", "intensitetsdrift": f"{drift:.1f} %"}


def detection_stats(stamps, n_target: int, bounce_ms: float = 50.0) -> dict:
    """Fotocell-flanker → antal detektioner + dubbeltriggar (kortare än debounce)."""
    k = len(stamps)
    if k == 0:
        return {"fel": "inga detektioner — kontrollera fotocell/polaritet (pin 7)"}
    intervals = np.diff(np.asarray(stamps, dtype=np.float64)) * 1000.0 if k > 1 else np.array([])
    doubles = int((intervals < bounce_ms).sum()) if intervals.size else 0
    min_iv = f"{intervals.min():.0f} ms" if intervals.size else "—"
    return {"detektioner": f"{k}/{n_target}", "min-intervall": min_iv,
            "dubbeltrigg": str(doubles)}


# -- rigg (nollplan, huvud-alignment, referensbräda) --

def belt_baseline(profiles) -> dict:
    """Tomt-band-profiler → nollplan B(x) (medel per X) + repeterbarhet (RMS) +
    bandets platthet (std). ``profiles`` = lista av tjocklek-arrayer (samma längd)."""
    a = np.asarray(profiles, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] < 1:
        return {"fel": "för få profiler"}
    bx = a.mean(axis=0)
    rms = float(np.sqrt(((a - bx) ** 2).mean())) * 1000.0      # µm, profil-till-profil
    flat = float(bx.max() - bx.min())                          # mm, bandets ojämnhet
    return {"_bx": bx.tolist(), "bandprofil RMS": f"{rms:.0f} µm",
            "platthet": f"{flat:.2f} mm"}


def head_alignment(z_red, z_green) -> dict:
    """Två huvuds höjdprofiler av SAMMA referenskloss → relativ Z-offset, lutning
    (X-rotation) och residual. Perfekt uppriktning ⇒ skillnaden ≈ 0 överallt."""
    zr, zg = np.asarray(z_red, np.float64), np.asarray(z_green, np.float64)
    m = np.isfinite(zr) & np.isfinite(zg)
    if m.sum() < 4:
        return {"fel": "för få giltiga punkter — syns klossen i BÅDA huvuden?"}
    x = np.arange(zr.size, dtype=np.float64)[m]
    diff = zr[m] - zg[m]
    slope, intercept = np.polyfit(x, diff, 1)
    z_off = float(intercept + slope * x.mean())                # medel-Z-offset (mm)
    resid = float(np.std(diff - (slope * x + intercept))) * 1000.0   # µm
    tilt = float(slope * (zr.size - 1) * 1000.0)               # µm över hela linjen
    return {"_z_offset_mm": z_off, "_slope": float(slope),
            "Z-offset": f"{z_off:.3f} mm", "lutning": f"{tilt:.0f} µm/linje",
            "residual": f"{resid:.0f} µm"}


def board_profile_dims(z, mm_per_px: float) -> dict:
    """Fused tjocklek-profil → brädans tjocklek (median av höjda regionen) + bredd
    (pixlar över tröskel × mm/px). Längd kräver Y-svep (guidat)."""
    a = np.asarray(z, np.float64)
    peak = float(np.nanmax(a)) if a.size else 0.0
    if peak < 2.0:
        return {"fel": "ingen bräda i profilen — mata referensbrädan till mätzonen"}
    on = a > max(2.0, 0.3 * peak)
    thick = float(np.median(a[on]))
    width = float(on.sum() * mm_per_px)
    return {"_thick": thick, "_width": width,
            "tjocklek": f"{thick:.2f} mm", "bredd": f"{width:.1f} mm"}


def compare_to_facit(measured: dict, facit: dict) -> dict:
    """Jämför uppmätta dimensioner mot facit (mm) → fel per dimension."""
    out = {}
    for key, mkey in (("tjocklek", "_thick"), ("bredd", "_width"), ("längd", "_length")):
        if key in facit and mkey in measured:
            out[f"{key}-fel"] = f"{abs(float(measured[mkey]) - float(facit[key])):.2f} mm"
    return out


# -- transportör (RoboClaw) --

def step_response_metrics(times, speeds, target: float) -> dict:
    """Hastighets-stegsvar → stigtid (till 90 %), översläng (%), ripple (% av mål).
    ``times`` (s) och ``speeds`` (mm/s) samplade efter steget till ``target`` mm/s."""
    t = np.asarray(times, dtype=np.float64)
    v = np.asarray(speeds, dtype=np.float64)
    if t.size < 3 or target <= 0:
        return {"fel": "för få sampel för stegsvar"}
    # stigtid: första gången hastigheten når 90 % av målet
    reach = np.where(v >= 0.9 * target)[0]
    rise_ms = float((t[reach[0]] - t[0]) * 1000.0) if reach.size else float("nan")
    overshoot = float(max(0.0, (v.max() - target) / target * 100.0))
    steady = v[t >= t[0] + 0.6 * (t[-1] - t[0])]      # sista ~40 % = inställt läge
    ripple = float(steady.std() / target * 100.0) if steady.size else float("nan")
    return {"stigtid": f"{rise_ms:.0f} ms", "översläng": f"{overshoot:.1f} %",
            "ripple": f"±{ripple:.1f} %"}


def belt_drift(mm_a: float, mm_b: float, distance_mm: float) -> dict:
    """Bandsynk: två band kör samma kommando → drift (mm/m) mellan dem (encoder A/B)."""
    if distance_mm <= 0:
        return {"fel": "ogiltig sträcka"}
    drift_per_m = abs(mm_a - mm_b) / (distance_mm / 1000.0)
    status = "inom tolerans" if drift_per_m < 0.5 else "JUSTERA M2-trim"
    return {"drift": f"{drift_per_m:.2f} mm/m", "band A/B": f"{mm_a:.1f} / {mm_b:.1f} mm",
            "status": status}


# ───────────────────────────── kontext-adapter ─────────────────────────────────

class CalibrationContext:
    """Ger auto-rutinerna kameraåtkomst via HAL-scannern. Pure-Python, ingen Qt."""

    def __init__(self, scanner):
        self.scanner = scanner
        self.conveyor = getattr(scanner, "conveyor", None)
        self.point_lasers = getattr(scanner, "point_lasers", []) or []
        self.led = getattr(scanner, "led_white", None)
        self.photocell = getattr(scanner, "photocell", None)
        self.laser_red = getattr(scanner, "laser_red", None)
        self.laser_green = getattr(scanner, "laser_green", None)
        self.laser_settle = 0.5             # s att låta dioden stabilisera efter tändning
        # Stegsvars-sampling (kort i test via monkeypatch av time.sleep)
        self.step_target_mm_s = 50.0
        self.step_dt = 0.05
        self.step_n = 30
        self.sync_distance_mm = 200.0
        self.sync_speed_mm_s = 30.0

    def _profile(self, dev_id: str):
        return (self.scanner.profile_red if dev_id == "prof_red"
                else self.scanner.profile_green)

    # -- profilkamera --
    def grab_profile(self, dev_id: str) -> np.ndarray:
        return self._profile(dev_id).read_stripe()

    def set_profile_exposure(self, dev_id: str, us: float) -> None:
        self._profile(dev_id).configure(ExposureTime=float(us))

    def laser_off(self, dev_id: str) -> None:
        """Släck huvudets laser (ALLTID säkert). Tänder aldrig."""
        las = (getattr(self.scanner, "laser_red", None) if dev_id == "prof_red"
               else getattr(self.scanner, "laser_green", None))
        try:
            if las is not None:
                las.set(False) if hasattr(las, "set") else las.close()
        except Exception:
            pass

    def set_profile_roi_offset(self, dev_id: str, offset_y: int) -> None:
        self._profile(dev_id).configure_roi(offset_y=int(offset_y))

    # -- ytkamera (linjekamera) --
    def grab_surface_rows(self, n: int = 100) -> np.ndarray:
        rows = [self.scanner.surface.grab_line() for _ in range(max(1, n))]
        return np.asarray(rows, dtype=np.float64)

    def set_surface_wb(self, gr: float, gg: float, gb: float) -> None:
        self.scanner.surface.configure(BalanceRatioRed=gr, BalanceRatioGreen=gg,
                                       BalanceRatioBlue=gb)

    # -- fält-IO (LED / laser / fotocell) --
    def led_on(self) -> bool:
        return bool(self.led.set(True)) if self.led is not None else False

    def led_off(self) -> None:
        if self.led is not None:
            self.led.set(False)

    def laser_for(self, dev_id: str):
        return self.laser_red if dev_id == "laser_red" else self.laser_green

    def cam_for_laser(self, dev_id: str) -> str:
        return "prof_red" if dev_id == "laser_red" else "prof_green"

    def laser_measure(self, dev_id: str, fn):
        """Säker kameramätning på en laser. Om lasern redan lyser → mät direkt. Om
        ARMAD men släckt → tänd (bara för mätningen), låt stabilisera, mät, SLÄCK
        alltid efter (finally). Ej armad → vägra (klass 3B kräver människo-interlock)."""
        las = self.laser_for(dev_id)
        if las is None:
            return {"fel": "ingen laser i HAL"}
        owned = False
        if not getattr(las, "is_on", False):
            if not getattr(las, "is_armed", False):
                return {"fel": "arma lasern via interlock-kontrollen först (klass 3B)"}
            if not las.set(True):
                return {"fel": "kunde inte tända lasern (arm/HW)"}
            owned = True
            if self.laser_settle:
                time.sleep(self.laser_settle)
        try:
            return fn()
        finally:
            if owned:
                las.set(False)             # släck alltid det rutinen tände

    # -- rigg (kräver BÅDA linjelasrarna tända; tänds aldrig av rutinen) --
    def lasers_on(self) -> bool:
        return bool(getattr(self.laser_red, "is_on", False)
                    and getattr(self.laser_green, "is_on", False))

    def head_profiles(self, n: int = 200):
        """(z_red, z_green) = de två huvudenas tjocklek-profiler längs X."""
        from ..processing.stripe import subpixel_centroid
        from ..processing.triangulate import centroid_to_z
        zr = centroid_to_z(subpixel_centroid(self.scanner.profile_red.read_stripe(0.0, n)))
        zg = centroid_to_z(subpixel_centroid(self.scanner.profile_green.read_stripe(0.0, n)))
        return zr, zg

    def fused_profile(self, n: int = 200):
        from ..processing.fusion import fuse
        zr, zg = self.head_profiles(n)
        return fuse(zr, zg)


# ─────────────────────────────── rutin-registret ───────────────────────────────
# (dev_id, method_id) → callable(ctx) -> values-dict. Saknas en post = ej auto
# (guidad/manuell metod, t.ex. intrinsics/triangplane som kräver fysiska mål).

def _prof_exposure(ctx, dev):
    return auto_exposure(lambda: ctx.grab_profile(dev),
                         lambda us: ctx.set_profile_exposure(dev, us))

def _prof_dark(ctx, dev):
    ctx.laser_off(dev)                                # säkert: släck före mörkbild
    return dark_stats(lambda: ctx.grab_profile(dev))

def _prof_focus(ctx, dev):
    return focus_fwhm(lambda: ctx.grab_profile(dev))

def _prof_stripe_roi(ctx, dev):
    cam = ctx._profile(dev)
    res = stripe_roi_offset(ctx.grab_profile(dev), roi_rows=cam._roi_rows)
    if "_offset_y" in res:
        ctx.set_profile_roi_offset(dev, res.pop("_offset_y"))
    return res

def _surf_whitebal(ctx, _dev):
    res = white_balance(ctx.grab_surface_rows(100))
    ctx.set_surface_wb(res.pop("_gain_r"), res.pop("_gain_g"), res.pop("_gain_b"))
    return res

def _surf_flatfield(ctx, _dev):
    return flat_field(ctx.grab_surface_rows(200))

def _conv_speedstep(ctx, _dev):
    """Mät hastighets-stegsvar (0→mål mm/s) → stigtid/översläng/ripple. Bandet rör
    sig bundet (operatörsinitierat); stoppas alltid efteråt."""
    conv = ctx.conveyor
    if conv is None:
        return {"fel": "ingen transportör i HAL"}
    target = ctx.step_target_mm_s
    try:
        conv.set_speed(0.0); time.sleep(0.2)
        conv.set_speed(target)
        times, speeds = [], []
        for i in range(ctx.step_n):
            time.sleep(ctx.step_dt)
            times.append(i * ctx.step_dt)
            speeds.append(conv.read_speed_mm_s()[0])
        return step_response_metrics(times, speeds, target)
    finally:
        conv.set_speed(0.0)                            # stoppa ALLTID

def _led_uniform(ctx, _dev):
    """LED-belysningsjämnhet längs linjekamerans FOV (LED är OFARLIG → tänds auto)."""
    if ctx.led is None:
        return {"fel": "inget LED i HAL"}
    try:
        if not ctx.led_on():
            return {"fel": "kunde inte tända LED"}
        rows = ctx.grab_surface_rows(50)
        res = flat_field(rows)
        res["rekommendation"] = ("OK — flat-field räcker"
                                 if float(res["ojämnhet före"].split()[0].replace(",", ".")) < 30
                                 else "ÅTGÄRDA mekaniskt (> 30 %)")
        return res
    finally:
        ctx.led_off()

def _photocell_trigger(ctx, _dev):
    """Fotocell: räkna laddnings-flanker + debounce medan operatören laddar bräda 10×."""
    pc = ctx.photocell
    if pc is None or not hasattr(pc, "collect_load_events"):
        return {"fel": "ingen fotocell i HAL"}
    stamps = pc.collect_load_events(n=10, timeout_s=30.0)
    return detection_stats(stamps, n_target=10)

def _laser_power(ctx, dev):
    """Effekt/intensitetsstabilitet via profilkameran (tänd→mät→släck om armad)."""
    return ctx.laser_measure(dev, lambda: laser_power_stability(
        lambda: ctx.grab_profile(ctx.cam_for_laser(dev))))

def _laser_width(ctx, dev):
    """Stripe-bredd (FWHM) via profilkameran (tänd→mät→släck om armad)."""
    return ctx.laser_measure(dev, lambda: focus_fwhm(
        lambda: ctx.grab_profile(ctx.cam_for_laser(dev))))

def _laser_straight(ctx, dev):
    """Linjerakhet (bow) via profilkameran (tänd→mät→släck om armad)."""
    return ctx.laser_measure(dev, lambda: line_straightness(
        ctx.grab_profile(ctx.cam_for_laser(dev))))

def _save_json(path: str, obj) -> None:
    import json, os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def _load_json(path: str):
    import json, os
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _rig_zeroplane(ctx, _dev):
    """Nollplan B(x): medla tomma-band-profiler → spara data/zero.json. GRINDAT
    på tända lasrar; operatören tömmer mätzonen (guidat steg)."""
    if not ctx.lasers_on():
        return {"fel": "tänd båda linjelasrarna via interlock-kontrollen först (klass 3B)"}
    profiles = [ctx.fused_profile() for _ in range(50)]
    res = belt_baseline(profiles)
    if "fel" in res:
        return res
    _save_json("data/zero.json", {"bx": res.pop("_bx"), "n": len(profiles)})
    return res

def _rig_align(ctx, _dev):
    """Huvud-alignment RÖD↔GRÖN mot referenskloss → korrektion i data/align.json.
    GRINDAT på tända lasrar; operatören lägger klossen i mätzonen (guidat)."""
    if not ctx.lasers_on():
        return {"fel": "tänd båda linjelasrarna via interlock-kontrollen först (klass 3B)"}
    zr, zg = ctx.head_profiles()
    res = head_alignment(zr, zg)
    if "fel" in res:
        return res
    _save_json("data/align.json", {"z_offset_mm": res.pop("_z_offset_mm"),
                                   "slope": res.pop("_slope")})
    return res

def _rig_refboard(ctx, _dev):
    """Referensbräda end-to-end: mät tjocklek + bredd → jämför mot facit
    (data/refboard.json). GRINDAT på tända lasrar; operatören matar brädan (guidat)."""
    if not ctx.lasers_on():
        return {"fel": "tänd båda linjelasrarna via interlock-kontrollen först (klass 3B)"}
    from ..geometry import RIG
    meas = board_profile_dims(ctx.fused_profile(), RIG.profile_lat_mm_per_px)
    if "fel" in meas:
        return meas
    facit = _load_json("data/refboard.json")
    if not facit:
        meas["facit"] = "saknas — skapa data/refboard.json {tjocklek,bredd,längd}"
        return {k: v for k, v in meas.items() if not k.startswith("_")}
    out = {k: v for k, v in meas.items() if not k.startswith("_")}
    out.update(compare_to_facit(meas, facit))
    out["längd"] = "verifieras i Y-svep (guidat)"
    return out

def _lr400_zero_d0(ctx, _dev):
    """Nolla LR400 mot TOMT band: medelavstånd per kanal → D0 (tjocklek = D0 − avstånd).
    Sätter D0 i drivern + persisterar till data/lr400.json."""
    lasers = ctx.point_lasers
    if not lasers:
        return {"fel": "inga LR400 i HAL"}
    from ..hal.real import lr400_config             # lazy: undvik core→hal vid import
    d0s, noises, ok = [], [], 0
    for i, las in enumerate(lasers):
        mean, rms, n = las.read_distance_avg(100)
        if mean is None:
            d0s.append(None); continue
        las.set_d0(mean); ok += 1
        d0s.append(mean); noises.append(rms or 0.0)
        try:
            lr400_config.set_d0(f"ch{i + 1}", mean)
        except Exception:
            pass
    if ok == 0:
        return {"fel": "ingen LR400 svarade — kontrollera RS-485/adresser och töm bandet"}
    d0str = " / ".join(f"{d:.1f}" if d is not None else "—" for d in d0s) + " mm"
    noise_um = (sum(noises) / len(noises)) * 1000.0 if noises else 0.0
    return {"D0 ch1/2/3": d0str, "brus": f"{noise_um:.0f} µm RMS",
            "kanaler ok": f"{ok}/{len(lasers)}"}

def _conv_beltsync(ctx, _dev):
    """Kör båda banden en känd sträcka → jämför encoder A/B → drift mm/m."""
    conv = ctx.conveyor
    if conv is None:
        return {"fel": "ingen transportör i HAL"}
    dist = ctx.sync_distance_mm
    cpm = getattr(conv, "_counts_per_mm", 100.0)
    try:
        conv.zero()
        m1_0, m2_0 = conv.encoder_counts()
        conv.move_mm(dist, ctx.sync_speed_mm_s)
        time.sleep(dist / max(1.0, ctx.sync_speed_mm_s) + 0.5)   # vänta in rörelsen
        m1_1, m2_1 = conv.encoder_counts()
        return belt_drift((m1_1 - m1_0) / cpm, (m2_1 - m2_0) / cpm, dist)
    finally:
        conv.set_speed(0.0)


AUTO_ROUTINES: dict = {
    ("prof_red", "exposure"):    _prof_exposure,
    ("prof_red", "dark"):        _prof_dark,
    ("prof_red", "focus"):       _prof_focus,
    ("prof_red", "stripe_roi"):  _prof_stripe_roi,
    ("prof_green", "exposure"):  _prof_exposure,
    ("prof_green", "dark"):      _prof_dark,
    ("prof_green", "focus"):     _prof_focus,
    ("prof_green", "stripe_roi"): _prof_stripe_roi,
    ("surface", "whitebal"):     _surf_whitebal,
    ("surface", "flatfield"):    _surf_flatfield,
    ("conveyor", "speedstep"):   _conv_speedstep,
    ("conveyor", "beltsync"):    _conv_beltsync,
    ("lr400", "zero_d0"):        _lr400_zero_d0,
    ("led_white", "uniform"):    _led_uniform,
    ("photocell", "trigger"):    _photocell_trigger,
    # Laser-mätningar: ARM-grindade (tänder bara om operatören armat; släcker alltid).
    ("laser_red", "power"):      _laser_power,
    ("laser_red", "width"):      _laser_width,
    ("laser_red", "straight"):   _laser_straight,
    ("laser_green", "power"):    _laser_power,
    ("laser_green", "width"):    _laser_width,
    ("laser_green", "straight"): _laser_straight,
    # Rigg: GRINDADE på tända lasrar; operatören sätter upp fysiskt (guidat).
    ("rig", "zeroplane"):        _rig_zeroplane,
    ("rig", "align"):            _rig_align,
    ("rig", "refboard"):         _rig_refboard,
}


def has_auto(dev_id: str, method_id: str) -> bool:
    return (dev_id, method_id) in AUTO_ROUTINES


def run_auto(dev_id: str, method_id: str, ctx: CalibrationContext) -> dict:
    """Kör auto-rutinen för (dev, method). Returnerar uppmätta värden eller {'fel':…}.
    Kraschar aldrig — fångar HAL-fel och returnerar dem som text."""
    fn = AUTO_ROUTINES.get((dev_id, method_id))
    if fn is None:
        return {}
    try:
        return fn(ctx, dev_id)
    except Exception as exc:
        return {"fel": f"mätfel: {exc}"}
