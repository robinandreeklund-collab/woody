#!/usr/bin/env python3
#coding=utf-8
"""Enkel MJPEG-webbström av linjekameran (Aravis) -> Windows-desktop via webbläsare.

Jetsonen greppar GigE-linjekameran lokalt och serverar live-bild över HTTP på
WiFi-nätet. Öppna http://<jetson-ip>:8080/ i en webbläsare på desktopen.
Ingen install behövs på Windows. Helt oberoende av Jetson-skärmen/DCE.
"""
import threading, time, sys, json, os
import gi
gi.require_version("Aravis", "0.8")
from gi.repository import Aravis
import numpy as np
import cv2
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CAM_ID = "ChinaVision-GELM44C-T2-076060623040"
PORT = 8080
OUT_W = 0          # 0 = native sensorbredd (4096) -> full detalj att zooma in på
HEIGHT = 512       # antal rader som staplas (högre = större bild att titta på)

_latest = None                 # senaste jpeg-bytes
_last_raw = None               # senaste RÅ Bayer-bildruta (för demosaic-test)
_lock = threading.Lock()
_raw_lock = threading.Lock()
_params = {"exposure": 5000.0, "gain": 8.0, "dirty": True, "height": HEIGHT, "reopen": False,
           "wb_request": False, "wb_reset": False, "clean": True}
_wb = {"b": 1.0, "g": 1.0, "r": 1.0}   # mjukvaru-vitbalans (om kameran inte gör det själv)
_auto = {"on": False, "plan": [], "i": 0, "wait": 0, "results": []}
# Bayer-mönster: kamerans GenICam "BayerRG8" = OpenCV:s BG (förskjuten namnkonvention).
# Verifierat mot färgtavla: BG ger rött=rött, blått=blått. EA = kantmedveten (mindre falskfärg).
_DEMOSAIC = getattr(cv2, "COLOR_BAYER_BG2BGR_EA", cv2.COLOR_BAYER_BG2BGR)

CONFIG_PATH = "/home/admin/woody/data/linjekamera_stream.json"


def _save_cfg():
    """Spara inställningarna så de överlever omstart av strömmen."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"exposure": _params["exposure"], "gain": _params["gain"],
                       "wb": dict(_wb)}, f, indent=2)
    except Exception as e:
        print("kan ej spara cfg:", e)


def _load_cfg():
    try:
        with open(CONFIG_PATH) as f:
            d = json.load(f)
        _params["exposure"] = float(d.get("exposure", _params["exposure"]))
        _params["gain"] = float(d.get("gain", _params["gain"]))
        if isinstance(d.get("wb"), dict):
            _wb.update({k: float(v) for k, v in d["wb"].items()})
        print("laddade sparade installningar:", d)
    except FileNotFoundError:
        print("ingen sparad config an - default")
    except Exception as e:
        print("kan ej ladda cfg:", e)


def _apply_exposure(cam, dev, exp):
    """Sätt exponering OCH koppla linjehastigheten så den aldrig klipper exponeringen."""
    # rad-perioden måste rymma exponeringen -> linjehastighet <= 1e6/exp
    line_rate = max(40.0, min(2000.0, 1_000_000.0 / (exp * 1.15)))
    try: dev.set_boolean_feature_value("AcquisitionLineRateEnable", True)
    except Exception: pass
    try: dev.set_float_feature_value("AcquisitionLineRate", line_rate)
    except Exception: pass
    try: cam.set_exposure_time(exp)
    except Exception: pass
_stats = {"mean": 0.0, "w": 0, "h": 0, "fps": 0.0}


def _camera_thread():
    """Självläkande: öppnar kameran, strömmar, och åter-öppnar om kanalen är
    upptagen (GigE-heartbeat) eller om strömmen tappas."""
    global _latest
    while True:
        try:
            _stream_once()
        except Exception as e:
            print("kamera-fel, åter-öppnar om 5s:", str(e)[:120])
            time.sleep(5)


def _stream_once():
    global _latest, _last_raw
    cam = Aravis.Camera.new(CAM_ID)
    dev = cam.get_device()

    def tset(fn, *a):
        try: fn(*a)
        except Exception: pass

    tset(dev.set_string_feature_value, "PixelFormat", "BayerRG8")
    tset(dev.set_string_feature_value, "TriggerMode", "Off")
    tset(cam.set_integer, "Height", int(_params["height"]))
    tset(cam.set_gain, _params["gain"])
    _apply_exposure(cam, dev, _params["exposure"])

    stream = cam.create_stream(None)   # kastar om kanalen är upptagen -> retry i _camera_thread
    payload = cam.get_payload()
    for _ in range(8):
        stream.push_buffer(Aravis.Buffer.new_allocate(payload))
    cam.start_acquisition()
    print("strömmar kameran")

    last_t = time.monotonic(); frames = 0
    try:
        while True:
            if _params["reopen"]:
                _params["reopen"] = False
                return            # öppna om med nya height/exposure (fokus-/full-läge)
            if _params["dirty"]:
                tset(cam.set_gain, _params["gain"])
                _apply_exposure(cam, dev, _params["exposure"])
                _params["dirty"] = False
            buf = stream.timeout_pop_buffer(2_000_000)
            if buf is None:
                continue
            try:
                if buf.get_status() == Aravis.BufferStatus.SUCCESS:
                    w = buf.get_image_width(); h = buf.get_image_height()
                    raw = np.frombuffer(buf.get_data(), dtype=np.uint8)[:w*h].reshape(h, w)
                    with _raw_lock:
                        _last_raw = raw.copy()             # spara rå Bayer för demosaic-test
                    bgr = cv2.cvtColor(raw, _DEMOSAIC)     # kantmedveten demosaicing
                    # --- vitbalans ---
                    if _params["wb_reset"]:
                        _params["wb_reset"] = False
                        _wb.update(b=1.0, g=1.0, r=1.0)
                        try: dev.set_string_feature_value("BalanceWhiteAuto", "Off")
                        except Exception: pass
                        _save_cfg()
                    if _params["wb_request"]:
                        _params["wb_request"] = False
                        # mjukvaru-vitbalans: neutralisera de ljusaste (vita) pixlarna -> R=G=B
                        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                        thr = float(np.percentile(gray, 80))
                        m = gray >= max(thr, 30)
                        if int(m.sum()) > 200:
                            mb = float(bgr[:, :, 0][m].mean()); mg = float(bgr[:, :, 1][m].mean()); mr = float(bgr[:, :, 2][m].mean())
                            _wb.update(b=mg / max(mb, 1), g=1.0, r=mg / max(mr, 1))
                            print(f"vitbalans: gains b={_wb['b']:.2f} g=1 r={_wb['r']:.2f} (fran {int(m.sum())} ljusa pixlar)")
                            _save_cfg()
                        else:
                            print("vitbalans: inga ljusa pixlar - rikta mot nagot vitt och ljust")
                    if _wb["b"] != 1.0 or _wb["r"] != 1.0:
                        bgr = np.clip(bgr.astype(np.float32) * (_wb["b"], _wb["g"], _wb["r"]), 0, 255).astype(np.uint8)
                    if _params["clean"]:                   # false-color suppression: jämna krominansen, behåll ljus-skärpan
                        ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
                        ycc[:, :, 1] = cv2.medianBlur(np.ascontiguousarray(ycc[:, :, 1]), 5)
                        ycc[:, :, 2] = cv2.medianBlur(np.ascontiguousarray(ycc[:, :, 2]), 5)
                        bgr = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)
                    # skärpe-mått (fokus): variansen av horisontell gradient längs sensor-raden.
                    # Mäts ENBART i bredd-led (det rumsliga axeln) på en mittrad — robust mot tid-axeln.
                    # FOKUS = LJUS-OBEROENDE skärpa: gradient-varians normerad mot ljusstyrkan^2.
                    # Då ändras talet INTE när exponeringen ändras — bara när linsens skärpa ändras.
                    midrow = raw[h // 2].astype(np.float32)
                    mrow = float(midrow.mean())
                    focus = float(np.diff(midrow).var() / max(mrow * mrow, 1.0) * 1e4)
                    # --- auto-exponering: hill-climb mot högsta kontrast/skärpe-tal ---
                    if _auto["on"]:
                        if _auto["wait"] > 0:
                            _auto["wait"] -= 1                      # vänta in att exponeringen satt sig
                        else:
                            # mätt och klar vid nuvarande plan-exponering -> spara resultat
                            clip = float((raw >= 252).mean())
                            _auto["results"].append((_params["exposure"], focus, clip))
                            _auto["i"] += 1
                            if _auto["i"] < len(_auto["plan"]):    # gå till nästa exponering i sveptet
                                _params["exposure"] = float(_auto["plan"][_auto["i"]])
                                _apply_exposure(cam, dev, _params["exposure"]); _auto["wait"] = 4
                            else:                                  # klar -> välj LJUSASTE exponering utan vitbränning
                                valid = [r for r in _auto["results"] if r[2] < 0.01]
                                best = max(valid, key=lambda r: r[0]) if valid else min(_auto["results"], key=lambda r: r[2])
                                _params["exposure"] = float(best[0])
                                _apply_exposure(cam, dev, _params["exposure"])
                                _auto["on"] = False; _save_cfg()
                                tab = ", ".join(f"{int(e)}{'*vit' if c >= 0.01 else ''}" for e, f, c in _auto["results"])
                                print(f"auto svep [{tab}]us -> valde exp={int(best[0])}us (ljusast utan vitbranning)")
                    if OUT_W and OUT_W < w:
                        disp = cv2.resize(bgr, (OUT_W, max(1, int(OUT_W * h / w))))
                    else:
                        disp = bgr.copy()                      # full sensorbredd -> zoombart
                    fs = max(0.6, disp.shape[1] / 1800.0)      # skala texten mot bildbredden
                    frames += 1
                    now = time.monotonic()
                    if now - last_t >= 1.0:
                        _stats["fps"] = frames / (now - last_t); frames = 0; last_t = now
                    _stats.update(mean=float(raw.mean()), w=w, h=h, focus=focus)
                    cv2.putText(disp, f"FOKUS={focus:7.0f}  {'AUTO-EXP kor...' if _auto['on'] else '(vrid tills storst)'}",
                                (12, int(34 * fs)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 220, 255), max(2, int(fs * 1.5)))
                    cv2.putText(disp, f"exp={_params['exposure']:.0f}us gain={_params['gain']:.0f} mean={raw.mean():.0f} {w}x{h} {_stats['fps']:.1f}fps",
                                (12, int(70 * fs)), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.75, (0, 255, 0), max(1, int(fs)))
                    ok, jpg = cv2.imencode(".jpg", disp, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ok:
                        with _lock:
                            _latest = jpg.tobytes()
            finally:
                stream.push_buffer(buf)
    finally:
        try: cam.stop_acquisition()
        except Exception: pass


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=8, user-scalable=yes">
<title>Linjekamera</title>
<style>
*{{box-sizing:border-box}}
body{{background:#0b0b0b;color:#eee;font-family:sans-serif;text-align:center;margin:0;padding:8px}}
h3{{margin:6px 0;font-size:16px}}
.bar{{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:8px 0}}
a.btn{{flex:1 1 40%;max-width:160px;padding:14px 8px;background:#2a8a4a;color:#fff;text-decoration:none;border-radius:8px;font-size:18px;font-weight:bold}}
a.btn:active{{background:#1f6e3a}}
a.btn.foc{{background:#b8742a}}a.btn.foc:active{{background:#8f5a1f}}
a.btn.wb{{background:#3a6ea5}}a.btn.wb:active{{background:#2c5580}}
a.btn.auto{{background:#7a4ea5}}a.btn.auto:active{{background:#5c3a80}}
a.btn.clean{{background:#555}}a.btn.clean:active{{background:#333}}
.frame{{width:100%;overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #333;border-radius:6px;background:#000}}
img{{display:block;width:100%;height:auto;touch-action:pinch-zoom}}
.hint{{color:#888;font-size:13px;margin:8px 6px}}
</style></head><body>
<h3>Linjekamera (HT-GELM44C-T2) &mdash; live via Jetson</h3>
<div class="bar">
<a class="btn foc" href="/focus">Fokus-lage (snabb)</a><a class="btn foc" href="/full">Full bild</a>
</div>
<div class="bar">
<a class="btn auto" href="/auto">Auto exp (max skarpa)</a>
<a class="btn wb" href="/wb">Vitbalans (rikta mot vitt)</a><a class="btn wb" href="/wb/reset">Aterstall farg</a>
</div>
<div class="bar">
<a class="btn clean" href="/clean">Falskfarg-rensning pa/av</a>
</div>
<div class="bar">
<a class="btn" href="/exp?d=1.5">Exp +</a><a class="btn" href="/exp?d=0.66">Exp -</a>
<a class="btn" href="/gain?d=1.5">Gain +</a><a class="btn" href="/gain?d=0.66">Gain -</a>
</div>
<div class="frame"><img src="/stream"></div>
<p class="hint">Nyp/dra for att zooma in. Gult FOKUS-tal: vrid fokusringen tills det blir storst.<br>
Linjekamera: stillastaende scen = lodrata strack &mdash; en skarp 2D-bild kraver att foremalet ror sig forbi (band+encoder).</p>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            body = PAGE.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body)
        elif p in ("/exp", "/gain"):
            try:
                d = float(self.path.split("d=")[1])
            except Exception:
                d = 1.0
            if p == "/exp":
                _params["exposure"] = min(max(_params["exposure"] * d, 50.0), 50000.0)
            else:
                _params["gain"] = min(max(_params["gain"] * d, 0.0), 8.0)
            _params["dirty"] = True
            _save_cfg()
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/focus":
            # snabbt fokus-läge: liten bild + kort exponering -> manga fps, talet reagerar direkt
            _params.update(height=128, exposure=800.0, dirty=True, reopen=True)
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/full":
            _params.update(height=512, exposure=5000.0, dirty=True, reopen=True)
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/wb":
            _params["wb_request"] = True
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/wb/reset":
            _params["wb_reset"] = True
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/auto":
            plan = [400.0, 700.0, 1100.0, 1700.0, 2600.0, 4000.0, 6000.0, 9000.0, 13000.0]
            _auto.update(on=True, plan=plan, i=0, wait=5, results=[])
            _params["exposure"] = plan[0]; _params["dirty"] = True   # börja sveptet på första exponeringen
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/clean":
            _params["clean"] = not _params["clean"]   # toggla falskfärg-rensning
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        elif p == "/raw.png":
            with _raw_lock:
                rw = None if _last_raw is None else _last_raw.copy()
            if rw is None:
                self.send_response(503); self.end_headers(); return
            ok, png = cv2.imencode(".png", rw)
            self.send_response(200); self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png))); self.end_headers()
            self.wfile.write(png.tobytes())
        elif p == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    with _lock:
                        frame = _latest
                    if frame is None:
                        time.sleep(0.05); continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame); self.wfile.write(b"\r\n")
                    time.sleep(0.03)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404); self.end_headers()


if __name__ == "__main__":
    _load_cfg()
    t = threading.Thread(target=_camera_thread, daemon=True)
    t.start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"strom igang: http://0.0.0.0:{PORT}/  (oppna fran Windows)")
    srv.serve_forever()
