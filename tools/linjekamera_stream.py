#!/usr/bin/env python3
#coding=utf-8
"""MJPEG-webbström av riggens kameror (Jetson headless -> desktop/mobil via webbläsare).

Serverar ALLA kameror i samma ström så man kan justera fokus/exponering vid
idrifttagning utan Jetson-skärm:
  * Linjekameran (yta/färg, HT-GELM44C-T2) via **Aravis** (GigE Vision).
  * Profilkamerorna RÖD/GRÖN (Hikrobot MV-CS050, mono) via **MVS-SDK** (USB3).

Öppna  http://<jetson-wifi-ip>:8080/  i en webbläsare. Översikten visar alla
inkopplade kameror; klicka en för fullskärm + kontroller (fokus-tal, exp ±, gain ±,
auto-exp; vitbalans/falskfärg-rensning bara för färg-linjekameran).

Varje kamera har en EGEN självläkande tråd: en kamera som inte är inkopplad visar
"ej ansluten" och försöker igen, utan att störa de andra. Ingen install på Windows.
Helt oberoende av Jetson-skärmen/DCE.

Profilkamerorna sitter bakom bandpassfilter (BP650/BP525) → de ser bara sin egen
färg och är mörka utan tänd laser, därför lång exponering (~200 ms) som default.
"""
import threading, time, sys, json, os
import numpy as np
import cv2
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
LINE_CAM_ID = "ChinaVision-GELM44C-T2-076060623040"
CAMERAS_JSON = "/home/admin/woody/data/cameras.json"
CFG_DIR = "/home/admin/woody/data"
SCAN_DIR = "/home/admin/woody/data/scans"     # sparade skanningar (rådata .npy + render .png)

# Bayer-mönster: kamerans GenICam "BayerRG8" = OpenCV:s BG (förskjuten namnkonvention).
# Verifierat mot färgtavla: BG ger rött=rött, blått=blått. EA = kantmedveten (mindre falskfärg).
_DEMOSAIC = getattr(cv2, "COLOR_BAYER_BG2BGR_EA", cv2.COLOR_BAYER_BG2BGR)


def _placeholder_jpeg(text, sub=""):
    """Svart ruta med text — visas när en kamera inte är inkopplad/öppnad."""
    img = np.zeros((240, 960, 3), np.uint8)
    cv2.putText(img, text, (24, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (60, 160, 255), 3)
    if sub:
        cv2.putText(img, sub, (24, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return jpg.tobytes() if ok else b""


class CamSource:
    """En kamera i strömmen: egna parametrar, statistik, jpeg-buffert och kontroller.

    Subklasser implementerar capture-loopen (Aravis resp. MVS); den GEMENSAMMA
    efterbehandlingen (fokus-tal, auto-exp, overlay, jpeg-encode) ligger här."""

    def __init__(self, name, label, color, exposure, gain,
                 exp_range, gain_range, auto_plan, tint=(0, 255, 0)):
        self.name = name              # url-nyckel: line / red / green
        self.label = label            # visningsnamn
        self.color = color            # True = debayra+vitbalans (linjekamera)
        self.tint = tint              # overlay-textfärg (BGR)
        self.exp_range = exp_range
        self.gain_range = gain_range
        self.params = {"exposure": float(exposure), "gain": float(gain),
                       "height": 512, "dirty": True, "reopen": False,
                       "wb_request": False, "wb_reset": False, "clean": True,
                       "stripe": False, "binning": 1, "scan_req": 0}
        self.scan = {"active": False, "rows": [], "target": 0, "png": None, "msg": "ingen skanning an"}
        self.wb = {"b": 1.0, "g": 1.0, "r": 1.0}
        self.auto = {"on": False, "plan": list(auto_plan), "i": 0, "wait": 0, "results": []}
        self.stats = {"mean": 0.0, "w": 0, "h": 0, "fps": 0.0, "focus": 0.0}
        self.connected = False
        self.note = "startar…"
        self._latest = _placeholder_jpeg(self.label, "startar…")
        self._last_raw = None
        self._lock = threading.Lock()
        self._raw_lock = threading.Lock()
        self.cfg_path = os.path.join(CFG_DIR, f"stream_{self.name}.json")
        self._frames = 0
        self._last_t = time.monotonic()

    # ---- persistens -----------------------------------------------------------
    def save_cfg(self):
        try:
            os.makedirs(CFG_DIR, exist_ok=True)
            with open(self.cfg_path, "w") as f:
                json.dump({"exposure": self.params["exposure"], "gain": self.params["gain"],
                           "wb": dict(self.wb), "binning": int(self.params["binning"])}, f, indent=2)
        except Exception as e:
            print(f"[{self.name}] kan ej spara cfg:", e)

    def load_cfg(self):
        try:
            with open(self.cfg_path) as f:
                d = json.load(f)
            self.params["exposure"] = float(d.get("exposure", self.params["exposure"]))
            self.params["gain"] = float(d.get("gain", self.params["gain"]))
            self.params["binning"] = int(d.get("binning", self.params["binning"]))
            if isinstance(d.get("wb"), dict):
                self.wb.update({k: float(v) for k, v in d["wb"].items()})
            print(f"[{self.name}] laddade sparade installningar:", d)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[{self.name}] kan ej ladda cfg:", e)

    # ---- jpeg-buffert (HTTP läser) --------------------------------------------
    def set_latest(self, jpg_bytes):
        with self._lock:
            self._latest = jpg_bytes

    def get_latest(self):
        with self._lock:
            return self._latest

    def get_raw_png(self):
        with self._raw_lock:
            rw = None if self._last_raw is None else self._last_raw.copy()
        if rw is None:
            return None
        ok, png = cv2.imencode(".png", rw)
        return png.tobytes() if ok else None

    # ---- kontroller (anropas från HTTP) ---------------------------------------
    def bump_exp(self, d):
        lo, hi = self.exp_range
        self.params["exposure"] = min(max(self.params["exposure"] * d, lo), hi)
        self.params["dirty"] = True
        self.save_cfg()

    def bump_gain(self, d):
        lo, hi = self.gain_range
        self.params["gain"] = min(max(self.params["gain"] * d, lo), hi)
        self.params["dirty"] = True
        self.save_cfg()

    def start_auto(self):
        if not self.auto["plan"]:
            return
        self.auto.update(on=True, i=0, wait=5, results=[])
        self.params["exposure"] = float(self.auto["plan"][0])
        self.params["dirty"] = True

    # ---- gemensam efterbehandling ---------------------------------------------
    def _focus(self, raw, h):
        """LJUS-OBEROENDE skärpa på den SKARPASTE raden i bilden.

        Per rad: gradient-varians normerad mot ljus² (oberoende av exponering).
        Tar p98 över alla tillräckligt ljusa rader → talet reagerar på det mest
        kontrastrika föremålet (kant/laserlinje) oavsett VAR i bilden det ligger,
        inte bara mittraden (som ofta hamnar på slät brädyta = lågt tal). Vrid
        fokusringen tills talet toppar."""
        f = raw.astype(np.float32)
        rvar = np.diff(f, axis=1).var(axis=1)          # gradient-varians per rad
        rmean = f.mean(axis=1)
        valid = rmean >= max(15.0, 0.3 * float(f.mean()))   # hoppa mörka/brus-rader
        if not valid.any():
            valid = rmean > 0
        score = rvar[valid] / np.maximum(rmean[valid] ** 2, 1.0) * 1e4
        return float(np.percentile(score, 98))         # skarpaste raden, robust mot brus

    def _auto_step(self, raw, focus, set_exp):
        """Auto-exp-svep: mät klipp vid varje plan-exponering, välj ljusaste utan vitbränning."""
        if not self.auto["on"]:
            return
        if self.auto["wait"] > 0:
            self.auto["wait"] -= 1
            return
        clip = float((raw >= 252).mean())
        self.auto["results"].append((self.params["exposure"], focus, clip))
        self.auto["i"] += 1
        if self.auto["i"] < len(self.auto["plan"]):
            self.params["exposure"] = float(self.auto["plan"][self.auto["i"]])
            set_exp(self.params["exposure"]); self.auto["wait"] = 4
        else:
            valid = [r for r in self.auto["results"] if r[2] < 0.01]
            best = max(valid, key=lambda r: r[0]) if valid else min(self.auto["results"], key=lambda r: r[2])
            self.params["exposure"] = float(best[0]); set_exp(self.params["exposure"])
            self.auto["on"] = False; self.save_cfg()
            tab = ", ".join(f"{int(e)}{'*vit' if c >= 0.01 else ''}" for e, f, c in self.auto["results"])
            print(f"[{self.name}] auto svep [{tab}]us -> valde exp={int(best[0])}us")

    def _overlay_stripe(self, raw, disp):
        """Extrahera laserstripens profil (samma subpixel_centroid som mätpipelinen)
        och rita den: tracker-kurva ovanpå stripen + förstorad profil-panel under.
        RELATIV/okalibrerad (radposition, ej mm) — bevisar att profilen plockas ut."""
        from app.processing.stripe import subpixel_centroid    # appens riktiga extraktion
        h, w = raw.shape
        step = max(1, w // 1400)                  # subsampla kolumner för fart
        cols = np.arange(0, w, step)
        cen = subpixel_centroid(raw[:, ::step].astype(np.float32))   # (cols,) rad eller NaN
        valid = ~np.isnan(cen)
        nval = int(valid.sum())
        # 1) rita spårad centroid direkt på stripen (röd kurva ska ligga PÅ linjen)
        idx = np.where(valid)[0]
        for a, b in zip(idx[:-1], idx[1:]):
            if b - a == 1:
                cv2.line(disp, (int(cols[a]), int(cen[a])), (int(cols[b]), int(cen[b])), (0, 0, 255), 2)
        # linjebredd (FWHM, px) = direkt fokusmått: minimera för skarpast linje.
        # Mäts på samma subsamplade kolumner; halvmax-bredd runt toppen, median.
        fwhm = float("nan")
        if nval > 10:
            sub = raw[:, ::step].astype(np.float32)
            ssig = np.clip(sub - np.median(sub, axis=0, keepdims=True), 0, None)
            sample = idx[:: max(1, len(idx) // 80)]      # ~80 kolumner räcker för stabil median
            widths = []
            for c in sample:
                col = ssig[:, c]; m = float(col.max())
                if m < 8:
                    continue
                above = np.where(col > m * 0.5)[0]
                if above.size:
                    widths.append(int(above[-1] - above[0] + 1))
            if widths:
                fwhm = float(np.median(widths))
        # 2) förstorad profil-panel nederst (visar plankans form)
        ph = max(180, h // 6)
        panel = np.full((ph, w, 3), 25, np.uint8)
        if nval > 10:
            lo = float(np.nanmin(cen)); hi = float(np.nanmax(cen)); rng = max(hi - lo, 1e-3)
            ynorm = (1.0 - (cen - lo) / rng) * (ph - 60) + 50
            for a, b in zip(idx[:-1], idx[1:]):
                if b - a == 1:
                    cv2.line(panel, (int(cols[a]), int(ynorm[a])), (int(cols[b]), int(ynorm[b])), (80, 220, 80), 2)
            cv2.putText(panel, f"PROFIL (relativ)  spann={rng:.1f}px  giltig={100 * nval / len(cols):.0f}%",
                        (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            # fokusmått: grönt <12 (skarpt), gult 12-22, rött >22 (suddigt)
            if fwhm == fwhm:   # ej NaN
                fcol = (80, 230, 80) if fwhm < 12 else (40, 210, 230) if fwhm < 22 else (60, 60, 255)
                tag = "SKARP" if fwhm < 12 else "ok" if fwhm < 22 else "SUDDIG - fokusera"
                cv2.putText(panel, f"FOKUS linjebredd {fwhm:.0f}px  [{tag}]  <-- minimera",
                            (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.9, fcol, 2)
        else:
            cv2.putText(panel, "ingen stripe - tand GRON-laser + sank exponering (Exp -)",
                        (10, ph // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2)
        return np.vstack([disp, panel])

    def process(self, raw, w, h, set_exp):
        """Gör en jpeg av en rå ram (mono eller Bayer) + uppdatera fokus/auto/stats."""
        with self._raw_lock:
            self._last_raw = raw.copy()
        if self.color:
            bgr = cv2.cvtColor(raw, _DEMOSAIC)
            # --- vitbalans (mjukvara; kameran har ingen ISP) ---
            if self.params["wb_reset"]:
                self.params["wb_reset"] = False
                self.wb.update(b=1.0, g=1.0, r=1.0); self.save_cfg()
            if self.params["wb_request"]:
                self.params["wb_request"] = False
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                thr = float(np.percentile(gray, 80))
                m = gray >= max(thr, 30)
                if int(m.sum()) > 200:
                    mb = float(bgr[:, :, 0][m].mean()); mg = float(bgr[:, :, 1][m].mean()); mr = float(bgr[:, :, 2][m].mean())
                    self.wb.update(b=mg / max(mb, 1), g=1.0, r=mg / max(mr, 1))
                    print(f"[{self.name}] vitbalans: b={self.wb['b']:.2f} g=1 r={self.wb['r']:.2f} ({int(m.sum())} ljusa pixlar)")
                    self.save_cfg()
                else:
                    print(f"[{self.name}] vitbalans: inga ljusa pixlar - rikta mot nagot vitt")
            if self.wb["b"] != 1.0 or self.wb["r"] != 1.0:
                bgr = np.clip(bgr.astype(np.float32) * (self.wb["b"], self.wb["g"], self.wb["r"]), 0, 255).astype(np.uint8)
            if self.params["clean"]:
                ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
                ycc[:, :, 1] = cv2.medianBlur(np.ascontiguousarray(ycc[:, :, 1]), 5)
                ycc[:, :, 2] = cv2.medianBlur(np.ascontiguousarray(ycc[:, :, 2]), 5)
                bgr = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)
        else:
            bgr = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)   # mono → BGR så overlay-text blir färgad

        focus = self._focus(raw, h)
        self._auto_step(raw, focus, set_exp)

        disp = bgr
        fs = max(0.6, disp.shape[1] / 1800.0)
        self._frames += 1
        now = time.monotonic()
        if now - self._last_t >= 1.0:
            self.stats["fps"] = self._frames / (now - self._last_t)
            self._frames = 0; self._last_t = now
        self.stats.update(mean=float(raw.mean()), w=w, h=h, focus=focus)
        cv2.putText(disp, f"{self.label}", (12, int(30 * fs)),
                    cv2.FONT_HERSHEY_SIMPLEX, fs * 0.8, self.tint, max(2, int(fs * 1.3)))
        cv2.putText(disp, f"FOKUS={focus:7.0f}  {'AUTO-EXP...' if self.auto['on'] else '(vrid tills storst)'}",
                    (12, int(64 * fs)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 220, 255), max(2, int(fs * 1.5)))
        cv2.putText(disp, f"exp={self.params['exposure']:.0f}us gain={self.params['gain']:.0f} mean={raw.mean():.0f} {w}x{h} {self.stats['fps']:.1f}fps",
                    (12, int(98 * fs)), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.7, (0, 255, 0), max(1, int(fs)))
        if not self.color and self.params.get("stripe"):    # laserprofil-läge (profilkameror)
            try:
                disp = self._overlay_stripe(raw, disp)
            except Exception as e:
                cv2.putText(disp, f"stripe-fel: {str(e)[:40]}", (12, int(130 * fs)),
                            cv2.FONT_HERSHEY_SIMPLEX, fs * 0.6, (0, 140, 255), 2)
        # --- skanning: stapla profiler till en höjdkarta (profilkameror) ---
        if not self.color:
            self._scan_step(raw)

        ok, jpg = cv2.imencode(".jpg", disp, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.set_latest(jpg.tobytes())

    def _scan_step(self, raw):
        """Samla en profil per ram medan en skanning pågår; rendera vid mål."""
        sr = int(self.params.get("scan_req", 0))
        if sr > 0 and not self.scan["active"]:
            self.scan.update(active=True, rows=[], target=sr, png=None, msg="skannar…")
            self.params["scan_req"] = 0
        if not self.scan["active"]:
            return
        from app.processing.stripe import subpixel_centroid
        self.scan["rows"].append(subpixel_centroid(raw.astype(np.float32)))
        self.scan["msg"] = f"skannar… {len(self.scan['rows'])}/{self.scan['target']}"
        if len(self.scan["rows"]) >= self.scan["target"]:
            n = len(self.scan["rows"])
            try:
                self.scan["png"] = _render_scan(self.scan["rows"])
                saved = self._save_scan()          # rådata + png till disk
                self.scan["msg"] = f"klar: {n} profiler  (sparad: {os.path.basename(saved)})"
            except Exception as e:
                self.scan["msg"] = f"render/spar-fel: {str(e)[:40]}"
            self.scan["active"] = False

    def _save_scan(self):
        """Spara skanningen (rådata .npy + render .png) med tidsstämpel för analys."""
        os.makedirs(SCAN_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        base = os.path.join(SCAN_DIR, f"scan_{self.name}_{ts}")
        np.save(base + ".npy", np.array(self.scan["rows"], dtype=np.float32))   # (F, W) centroid-rader
        if self.scan.get("png"):
            with open(base + ".png", "wb") as f:
                f.write(self.scan["png"])
        self.scan["saved"] = base
        print(f"[{self.name}] skanning sparad: {base}.npy ({len(self.scan['rows'])} profiler)")
        return base

    def run(self):
        """Självläkande capture-loop — subklass implementerar _stream_once()."""
        while True:
            try:
                self._stream_once()
            except Exception as e:
                self.connected = False
                self.note = f"fel: {str(e)[:80]}"
                self.set_latest(_placeholder_jpeg(self.label, self.note))
                print(f"[{self.name}] {self.note} — aterforsoker om 5s")
                time.sleep(5)

    def _stream_once(self):
        raise NotImplementedError


class LineCamSource(CamSource):
    """Färg-linjekameran via Aravis (GigE Vision)."""

    def __init__(self):
        super().__init__("line", "Linjekamera (HT-GELM44C-T2)", color=True,
                         exposure=5000.0, gain=8.0,
                         exp_range=(50.0, 50000.0), gain_range=(0.0, 8.0),
                         auto_plan=[400, 700, 1100, 1700, 2600, 4000, 6000, 9000, 13000],
                         tint=(0, 230, 230))

    def _apply_exposure(self, cam, dev, exp):
        line_rate = max(40.0, min(2000.0, 1_000_000.0 / (exp * 1.15)))
        try: dev.set_boolean_feature_value("AcquisitionLineRateEnable", True)
        except Exception: pass
        try: dev.set_float_feature_value("AcquisitionLineRate", line_rate)
        except Exception: pass
        try: cam.set_exposure_time(exp)
        except Exception: pass

    def _stream_once(self):
        import gi
        gi.require_version("Aravis", "0.8")
        from gi.repository import Aravis
        cam = Aravis.Camera.new(LINE_CAM_ID)
        dev = cam.get_device()

        def tset(fn, *a):
            try: fn(*a)
            except Exception: pass

        tset(dev.set_string_feature_value, "PixelFormat", "BayerRG8")
        tset(dev.set_string_feature_value, "TriggerMode", "Off")
        tset(cam.set_integer, "Height", int(self.params["height"]))
        tset(cam.set_gain, self.params["gain"])
        self._apply_exposure(cam, dev, self.params["exposure"])

        stream = cam.create_stream(None)
        payload = cam.get_payload()
        for _ in range(8):
            stream.push_buffer(Aravis.Buffer.new_allocate(payload))
        cam.start_acquisition()
        self.connected = True; self.note = "strömmar"
        print(f"[{self.name}] strömmar")
        set_exp = lambda e: self._apply_exposure(cam, dev, e)
        try:
            while True:
                if self.params["reopen"]:
                    self.params["reopen"] = False
                    return
                if self.params["dirty"]:
                    tset(cam.set_gain, self.params["gain"])
                    self._apply_exposure(cam, dev, self.params["exposure"])
                    self.params["dirty"] = False
                buf = stream.timeout_pop_buffer(2_000_000)
                if buf is None:
                    continue
                try:
                    if buf.get_status() == Aravis.BufferStatus.SUCCESS:
                        w = buf.get_image_width(); h = buf.get_image_height()
                        raw = np.frombuffer(buf.get_data(), dtype=np.uint8)[:w * h].reshape(h, w)
                        self.process(raw, w, h, set_exp)
                finally:
                    stream.push_buffer(buf)
        finally:
            try: cam.stop_acquisition()
            except Exception: pass


def _render_scan(rows):
    """Stapla laserprofiler (lista av (W,) centroid-rader, NaN=ocklusion) till en
    PNG: höjdkarta (topp-vy, turbo) + 3D-relief (hillshade). Ren OpenCV/numpy."""
    cen = np.array(rows, dtype=np.float32)          # (F, W)
    F, W = cen.shape
    Z = -(cen - np.nanmedian(cen))                  # mindre rad = högre
    for i in range(F):                              # fyll ocklusion radvis
        m = ~np.isnan(Z[i])
        Z[i] = np.interp(np.arange(W), np.where(m)[0], Z[i][m]) if m.sum() >= 2 else 0.0
    Z = cv2.GaussianBlur(Z, (0, 0), 1.2)
    zmin, zmax = float(Z.min()), float(Z.max()); rng = max(zmax - zmin, 1e-3)
    heat = cv2.applyColorMap(np.clip((Z - zmin) / rng * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    # hillshade: yt-normal (-gx,-gy,1) · ljusriktning
    gy, gx = np.gradient(Z.astype(np.float32))
    nn = np.sqrt(gx * gx + gy * gy + 1.0)
    L = np.array([-0.6, -0.6, 0.52]); L /= np.linalg.norm(L)
    illum = np.clip((-gx * L[0] - gy * L[1] + L[2]) / nn, 0, 1)
    shade = cv2.applyColorMap((illum * 255).astype(np.uint8), cv2.COLORMAP_BONE)

    def fit(img):
        h, w = img.shape[:2]
        return cv2.resize(img, (900, max(120, int(h * 900.0 / w))), interpolation=cv2.INTER_NEAREST)

    def label(img, t):
        img = fit(img); cv2.rectangle(img, (0, 0), (img.shape[1], 34), (0, 0, 0), -1)
        cv2.putText(img, t, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 2); return img

    out = np.vstack([label(heat, f"Hojdkarta (topp-vy) - {F} profiler, hojdspann {zmax - zmin:.0f}px"),
                     label(shade, "3D-relief (hillshade)")])
    okk, png = cv2.imencode(".png", out)
    return png.tobytes() if okk else None


def _soft_bin(raw, b):
    """Mjukvaru-binning: summerar b×b-block (mono). Ger ~b² gånger signal
    (klippt till 255) och b× mindre upplösning. Höjer svag laserlinje över
    tröskeln så den detekteras vid kortare exponering."""
    h, w = raw.shape
    h2, w2 = h // b * b, w // b * b
    r = raw[:h2, :w2].astype(np.uint16).reshape(h2 // b, b, w2 // b, b).sum(axis=(1, 3))
    return np.clip(r, 0, 255).astype(np.uint8)


class ProfileCamSource(CamSource):
    """Profilkamera (Hikrobot MV-CS050, mono) via MVS-SDK (USB3 Vision)."""

    def __init__(self, name, label, serial, tint):
        # bakom bandpassfilter → mörk utan laser → lång exponering som default.
        super().__init__(name, label, color=False,
                         exposure=200000.0, gain=15.0,
                         exp_range=(100.0, 1_000_000.0), gain_range=(0.0, 24.0),
                         auto_plan=[50000, 100000, 200000, 350000, 500000],
                         tint=tint)
        self.serial = serial
        self.params["binning"] = 2      # 2×2 Sum → ~4× ljus (ljussvag bakom bandpass)

    def _stream_once(self):
        # importera HAL:ens MVS-wrapper (sätter MVS-miljövariabler + laddar SDK lazy)
        sys.path.insert(0, "/home/admin/woody")
        from app.hal.real.mvs_u3v import MvsU3VCamera, list_serials
        present = list_serials()
        if self.serial not in present:
            self.connected = False
            self.note = f"ej ansluten (S/N {self.serial})"
            self.set_latest(_placeholder_jpeg(self.label, self.note))
            time.sleep(4)
            return
        dev = MvsU3VCamera(self.serial)
        dev.open(pixel_format="Mono8")
        # MV-CS050 stöder INTE hårdvaru-binning (Sony global-shutter). Binning görs
        # därför i mjukvara per ram (_soft_bin) — 2×2-summa lyfter den ljussvaga
        # laserlinjen över tröskeln så den detekteras vid kortare exponering.
        # full sensorram så man kan rikta/fokusera; offset nollställt
        dev.set_int("OffsetX", 0); dev.set_int("OffsetY", 0)
        wmax = dev.get_int_max("Width"); hmax = dev.get_int_max("Height")
        if wmax: dev.set_int("Width", wmax)
        if hmax: dev.set_int("Height", hmax)
        dev.set_enum("ExposureAuto", "Off"); dev.set_enum("GainAuto", "Off")
        dev.set_float("ExposureTime", self.params["exposure"])
        dev.set_float("Gain", self.params["gain"])
        dev.start()
        self.connected = True; self.note = "strömmar"
        print(f"[{self.name}] strömmar (S/N {self.serial})")
        set_exp = lambda e: dev.set_float("ExposureTime", e)
        try:
            while True:
                if self.params["dirty"]:
                    dev.set_float("Gain", self.params["gain"])
                    dev.set_float("ExposureTime", self.params["exposure"])
                    self.params["dirty"] = False
                # timeout > exponering (annars timeout vid lång exp)
                tmo = int(self.params["exposure"] / 1000 + 800)
                raw = dev.grab(timeout_ms=tmo)
                if raw is None:
                    continue
                b = max(1, int(self.params["binning"]))
                if b > 1:
                    raw = _soft_bin(raw, b)     # mjukvaru-binning (kameran saknar hw-binning)
                h, w = raw.shape
                self.process(raw, w, h, set_exp)
        finally:
            try: dev.close()
            except Exception: pass


# ───────────────────── källor (byggs vid start) ───────────────────────────────
SOURCES = {}        # name -> CamSource


def _build_sources():
    line = LineCamSource()
    SOURCES[line.name] = line
    # profilkameror från cameras.json (serienr-bindning RÖD/GRÖN)
    try:
        with open(CAMERAS_JSON) as f:
            cfg = json.load(f)
    except Exception as e:
        print("kan ej läsa cameras.json:", e); cfg = {}
    for key, name, label, tint in (
        ("profile_red", "red", "Profilkamera RÖD 650", (0, 80, 255)),
        ("profile_green", "green", "Profilkamera GRÖN 520", (0, 230, 80))):
        serial = (cfg.get(key) or {}).get("serial")
        if serial:
            SOURCES[name] = ProfileCamSource(name, label, serial, tint)
    for s in SOURCES.values():
        s.load_cfg()
        threading.Thread(target=s.run, daemon=True).start()


# ───────────────────── HTTP ────────────────────────────────────────────────────
def _overview_html():
    cards = []
    for s in SOURCES.values():
        cards.append(
            f'<div class="card"><h4>{s.label}</h4>'
            f'<a href="/cam/{s.name}"><div class="thumb"><img src="/stream?cam={s.name}"></div></a>'
            f'<a class="btn" href="/cam/{s.name}">Öppna &amp; justera</a></div>')
    return ("<!doctype html><html><head><meta charset=utf-8>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Woody kameror</title><style>"
            "body{background:#0b0b0b;color:#eee;font-family:sans-serif;margin:0;padding:10px;text-align:center}"
            "h3{margin:8px 0}.grid{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}"
            ".card{background:#161616;border:1px solid #2a2a2a;border-radius:10px;padding:10px;flex:1 1 320px;max-width:560px}"
            ".card h4{margin:4px 0 8px}.thumb{background:#000;border-radius:6px;overflow:hidden}"
            ".thumb img{width:100%;height:auto;display:block}"
            "a.btn{display:inline-block;margin-top:8px;padding:10px 14px;background:#2a8a4a;color:#fff;"
            "text-decoration:none;border-radius:8px;font-weight:bold}a{color:#7ab}"
            "</style></head><body><h3>Woody &mdash; kameror (live via Jetson)</h3>"
            f"<div class='grid'>{''.join(cards)}</div>"
            "<p style='color:#888;font-size:13px'>Klicka en kamera för att justera fokus/exponering. "
            "Nyp/dra för att zooma in i fullskärm.</p></body></html>")


def _scanview_html(s):
    active = s.scan["active"]; ready = s.scan.get("png") is not None
    refresh = "<meta http-equiv=refresh content=1>" if active else ""
    if ready and not active:
        body = (f"<img src='/scan.png?cam={s.name}&t={int(time.monotonic())}' "
                f"style='max-width:100%;border-radius:8px'>")
    else:
        body = "<p style='font-size:18px;color:#8fd'>Skannar — rör brädan under laserlinjen…</p>"
    return ("<!doctype html><html><head><meta charset=utf-8>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"{refresh}<title>Skanning {s.label}</title><style>"
            "body{background:#0b0b0b;color:#eee;font-family:sans-serif;text-align:center;margin:0;padding:10px}"
            ".bar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:10px 0}"
            "a.btn{flex:1 1 40%;max-width:200px;padding:14px 8px;background:#b8742a;color:#fff;"
            "text-decoration:none;border-radius:8px;font-size:17px;font-weight:bold}"
            "a.btn.back{background:#3a6ea5}</style></head><body>"
            f"<h3>3D-skanning — {s.label}</h3>"
            f"<p style='color:#888'>{s.scan['msg']}</p>{body}"
            f"<div class='bar'><a class='btn' href='/scan?cam={s.name}&n=150'>Skanna igen</a>"
            f"<a class='btn back' href='/cam/{s.name}'>Tillbaka till kameran</a></div>"
            "</body></html>")


def _cam_html(s):
    color_bar = ""
    if s.color:
        color_bar = (
            f'<div class="bar"><a class="btn foc" href="/focus?cam={s.name}">Fokus-lage (snabb)</a>'
            f'<a class="btn foc" href="/full?cam={s.name}">Full bild</a></div>'
            f'<div class="bar"><a class="btn wb" href="/wb?cam={s.name}">Vitbalans (rikta mot vitt)</a>'
            f'<a class="btn wb" href="/wb/reset?cam={s.name}">Aterstall farg</a>'
            f'<a class="btn clean" href="/clean?cam={s.name}">Falskfarg-rensning</a></div>')
    else:
        binlabel = f"Binning {s.params['binning']}x{s.params['binning']} (pa/av)"
        color_bar = (
            f'<div class="bar"><a class="btn auto" href="/stripe?cam={s.name}">'
            f'Laserprofil pa/av</a>'
            f'<a class="btn wb" href="/bin?cam={s.name}">{binlabel}</a></div>'
            f'<div class="bar"><a class="btn foc" href="/scan?cam={s.name}&n=150">'
            f'SKANNA (fanga 150 profiler)</a></div>')
    return ("<!doctype html><html><head><meta charset=utf-8>"
            "<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=8, user-scalable=yes'>"
            f"<title>{s.label}</title><style>"
            "*{box-sizing:border-box}body{background:#0b0b0b;color:#eee;font-family:sans-serif;text-align:center;margin:0;padding:8px}"
            "h3{margin:6px 0;font-size:16px}.bar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:8px 0}"
            "a.btn{flex:1 1 40%;max-width:160px;padding:14px 8px;background:#2a8a4a;color:#fff;text-decoration:none;border-radius:8px;font-size:17px;font-weight:bold}"
            "a.btn.foc{background:#b8742a}a.btn.wb{background:#3a6ea5}a.btn.auto{background:#7a4ea5}a.btn.clean{background:#555}"
            "a.btn.back{background:#333;flex:1 1 100%;max-width:none}"
            ".frame{width:100%;overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #333;border-radius:6px;background:#000}"
            "img{display:block;width:100%;height:auto;touch-action:pinch-zoom}.hint{color:#888;font-size:13px;margin:8px 6px}"
            "</style></head><body>"
            f"<h3>{s.label} &mdash; live</h3>"
            f'<div class="bar"><a class="btn back" href="/">&larr; Alla kameror</a></div>'
            f'<div class="bar"><a class="btn auto" href="/auto?cam={s.name}">Auto exp (ljusast)</a></div>'
            f"{color_bar}"
            f'<div class="bar"><a class="btn" href="/exp?cam={s.name}&d=1.5">Exp +</a>'
            f'<a class="btn" href="/exp?cam={s.name}&d=0.66">Exp -</a>'
            f'<a class="btn" href="/gain?cam={s.name}&d=1.5">Gain +</a>'
            f'<a class="btn" href="/gain?cam={s.name}&d=0.66">Gain -</a></div>'
            f'<div class="frame"><img src="/stream?cam={s.name}"></div>'
            '<p class="hint">Nyp/dra for att zooma. Gult FOKUS-tal: vrid fokusringen tills det blir storst.<br>'
            'Profilkamera sitter bakom bandpassfilter → mork utan laser, hog exponering behovs.</p>'
            "</body></html>")


def _query(path):
    out = {}
    if "?" in path:
        for kv in path.split("?", 1)[1].split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1); out[k] = v
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _redirect(self, to):
        self.send_response(303); self.send_header("Location", to); self.end_headers()

    def _html(self, body):
        b = body.encode()
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)

    def _src(self, q):
        return SOURCES.get(q.get("cam", "line"))

    def do_GET(self):
        p = self.path.split("?")[0]
        q = _query(self.path)

        if p == "/":
            return self._html(_overview_html())
        if p.startswith("/cam/"):
            s = SOURCES.get(p[len("/cam/"):])
            return self._html(_cam_html(s)) if s else (self.send_response(404), self.end_headers())

        if p in ("/exp", "/gain", "/focus", "/full", "/wb", "/wb/reset", "/auto", "/clean", "/stripe", "/bin"):
            s = self._src(q)
            if s is None:
                self.send_response(404); self.end_headers(); return
            if p == "/exp":
                s.bump_exp(float(q.get("d", 1.0)))
            elif p == "/gain":
                s.bump_gain(float(q.get("d", 1.0)))
            elif p == "/focus" and s.color:
                s.params.update(height=128, exposure=800.0, dirty=True, reopen=True)
            elif p == "/full" and s.color:
                s.params.update(height=512, exposure=5000.0, dirty=True, reopen=True)
            elif p == "/wb":
                s.params["wb_request"] = True
            elif p == "/wb/reset":
                s.params["wb_reset"] = True
            elif p == "/auto":
                s.start_auto()
            elif p == "/clean":
                s.params["clean"] = not s.params["clean"]
            elif p == "/stripe":
                s.params["stripe"] = not s.params.get("stripe")
            elif p == "/bin":
                # växla 1 ↔ 2 (eller sätt ?d=N); capture-loopen öppnar om kameran
                nb = int(float(q["d"])) if "d" in q else (1 if int(s.params["binning"]) > 1 else 2)
                s.params["binning"] = max(1, nb)
                s.params["dirty"] = True
                s.save_cfg()
            return self._redirect(f"/cam/{s.name}")

        if p == "/scan":
            s = self._src(q)
            if s is None:
                self.send_response(404); self.end_headers(); return
            s.params["scan_req"] = max(10, int(q.get("n", 150)))
            return self._redirect(f"/scanview?cam={s.name}")

        if p == "/scanview":
            s = self._src(q)
            return self._html(_scanview_html(s)) if s else (self.send_response(404), self.end_headers())

        if p == "/scan.png":
            s = self._src(q)
            png = s.scan.get("png") if s else None
            if png is None:
                self.send_response(503); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(png))); self.end_headers()
            self.wfile.write(png); return

        if p == "/raw.png":
            s = self._src(q)
            png = s.get_raw_png() if s else None
            if png is None:
                self.send_response(503); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png))); self.end_headers()
            self.wfile.write(png); return

        if p == "/stream":
            s = self._src(q)
            if s is None:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache"); self.end_headers()
            try:
                while True:
                    frame = s.get_latest()
                    if frame is None:
                        time.sleep(0.05); continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame); self.wfile.write(b"\r\n")
                    time.sleep(0.04)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    _build_sources()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"strom igang: http://0.0.0.0:{PORT}/  ({len(SOURCES)} kameror: {', '.join(SOURCES)})")
    srv.serve_forever()
