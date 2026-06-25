"""Enkla tester för kärnlogiken (geometri, gradering, mätpipeline, persistens).

Kör utan pytest:  python -m app.tests.test_core
Eller med pytest:  pytest app/tests/
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from ..geometry import RIG
from ..processing.grade import grade_board
from ..processing.pipeline import measure_profile
from ..hal.sim.sim_backends import SimScanner
from ..persistence.store import BoardStore


def test_geometry():
    assert RIG.tri_angle_deg == 25.0
    assert RIG.oblique_deg == 37.5
    assert abs(RIG.baseline_mm - 329) < 2
    assert RIG.work_distance_mm == 760.0
    assert abs(RIG.board_aspect - 500 / 75) < 1e-6
    assert RIG.board_thick_mm == 20.0


def test_grade_clean_vs_reject():
    a = grade_board([], (0.5, 0.3, 0.2))
    assert a.cls == "A" and a.score >= 85
    # grov röta (area ≫ D-gränsen) + djup vankant + lång spricka → vrak
    bad = [{"type": "rot", "r": 60}, {"type": "rot", "r": 60},
           {"type": "wane", "r": 100, "depth": 18}, {"type": "crack", "len": 450, "r": 225}]
    v = grade_board(bad, (3, 3, 3))
    assert v.cls == "V" and v.score < a.score


def test_triangulation_recovers_thickness():
    s = SimScanner(); s.new_board(); b = s.board()
    y = RIG.board_width_mm * 0.5
    true = np.array(b.z_profile_row(y, 200))
    # mata pipelinen med korrekta LR-värden (som riktiga punktlasrar skulle ge)
    lr = [b.thickness_at(x, y) for x in RIG.point_lasers_x_mm]
    meas = measure_profile(s, y, lr, RIG.point_lasers_x_mm)
    err = np.abs(meas - true)
    assert err.mean() < 0.4, f"medel-fel {err.mean()*1000:.0f} µm för stort"


def test_stripe_gpu_matches_cpu():
    # GPU-extraktorn (CuPy) och CPU-referensen ska ge samma centroid (här: numpy-fallback)
    from ..processing.stripe import subpixel_centroid
    from ..processing.stripe_gpu import centroid_batch, to_cpu
    rng = np.random.default_rng(3)
    roi = np.clip(20 + rng.normal(0, 4, (80, 200)), 0, 255)
    roi[38:43, :] += 180                      # laserstripe-band
    ref = subpixel_centroid(roi)
    gpu = to_cpu(centroid_batch(roi))         # GPU-array → numpy via .get() (CuPy-säkert)
    both = np.isfinite(ref) & np.isfinite(gpu)
    assert both.sum() > 190                   # nästan alla kolumner hittar stripen
    assert np.nanmax(np.abs(ref[both] - gpu[both])) < 1e-3


def test_acquisition_pipeline_assembles_board():
    # trådad capture∥process → en hel bräda som går att gradera, med rimlig skevhet
    from ..processing.acquisition import AcquisitionPipeline
    s = SimScanner(); s.new_board()
    board, st = AcquisitionPipeline(s, cols=200).scan_board(n_rows=60)
    # ytan normaliseras till board_gen:s kanoniska (bredd_px, längd_px) = (150, 1000)
    # för 75×500 mm @ 2 px/mm → identisk orientering/förhållande i pass & flöde
    assert board.surface.shape == (150, 1000, 3)
    assert board.zmap.shape == (150, 1000)
    assert st.rows == 60 and st.dropped == 0
    wm = board.warp_metrics()
    assert all(k in wm for k in ("bow", "cup", "twist"))
    g = grade_board(board.defects, wm)
    assert g.cls in ("A", "B", "C", "D", "V")


def test_real_hal_complete():
    # Fas 1 + Fas 2 enligt prototype-wiring.svg: 2 profilkameror + linjekamera +
    # 3× LR400 + RoboClaw + 2 laser-enable + LED + fotocell = 11 enheter
    from ..hal.real.real_backends import RealScanner
    rs = RealScanner()
    assert len(rs.devices()) == 11
    assert len(rs.point_lasers) == 3
    ifaces = [d.info().interface for d in rs.devices()]
    assert any("RS-485" in i for i in ifaces)           # LR400 över Waveshare 4CH
    assert any("pin 7" in i for i in ifaces)            # fotocell på GPIO pin 7
    assert any("pin 16" in i for i in ifaces)           # röd laser-enable
    assert hasattr(rs, "arm_photocell")                 # brädladdnings-event
    # GPIO-pinkartan matchar prototype-pinout.svg
    from ..hal.real import gpio_io
    assert (gpio_io.PIN_PHOTOCELL, gpio_io.PIN_LASER_RED,
            gpio_io.PIN_LASER_GREEN, gpio_io.PIN_LED_A, gpio_io.PIN_LED_B) == (7, 16, 18, 13, 15)


def test_persistence_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        st = BoardStore(Path(d) / "t.db")
        st.log_board({"n": 1, "cls": "B", "title": "Klass B", "score": 70,
                      "ndef": 2, "nvision": 3}, [{"type": "knot", "x": 1, "y": 2}])
        assert len(st.recent()) == 1
        assert st.stats().get("B") == 1
        csv = st.export_csv(Path(d) / "e.csv")
        assert csv.exists() and "Klass B" in csv.read_text()
        st.close()


def test_stitch_sections():
    # Flera huvuden delar encoder-koordinaten → stitch syr ihop hela brädan.
    from ..processing.stitch import stitch_sections
    secs = [{"start_mm": 0, "end_mm": 250, "values": [10.0] * 50},
            {"start_mm": 250, "end_mm": 500, "values": [20.0] * 50}]
    out = stitch_sections(secs, n_out=100, total_start=0, total_end=500)
    assert out is not None and len(out) == 100
    assert abs(out[10] - 10.0) < 1e-6 and abs(out[90] - 20.0) < 1e-6   # rätt sektion
    # demo: ett huvud över hela brädan → bara dess profil
    one = stitch_sections([{"start_mm": 0, "end_mm": 500, "values": [15.0] * 20}], n_out=50)
    assert one is not None and abs(np.nanmean(one) - 15.0) < 1e-6
    # överlapp medlas; inga sektioner → None
    ov = stitch_sections([{"start_mm": 0, "end_mm": 100, "values": [10.0] * 10},
                          {"start_mm": 0, "end_mm": 100, "values": [20.0] * 10}], n_out=10)
    assert abs(np.nanmean(ov) - 15.0) < 1e-6
    assert stitch_sections([]) is None


def test_genicam_feature_apply():
    # Settings-lagret ska styra kameran från koden: sätt giltiga features, logga
    # okända/ogiltiga utan att krascha, hoppa över None. (Fejkad GenICam-node-map.)
    from ..hal.real.cameras import (apply_genicam_features, read_genicam_features,
                                    dump_genicam_features, DEFAULT_SURFACE_FEATURES)

    class _Node:
        def __init__(self, v, allowed=None, ro=False):
            self._v, self._a, self._ro = v, allowed, ro
        @property
        def value(self): return self._v
        @value.setter
        def value(self, x):
            if self._ro: raise RuntimeError("read-only")
            if self._a is not None and x not in self._a: raise ValueError("ogiltig enum")
            self._v = x

    class _NodeMap: pass
    nm = _NodeMap()
    nm.PixelFormat = _Node("Mono8", allowed={"Mono8", "RGB8"})
    nm.TriggerMode = _Node("Off", allowed={"On", "Off"})
    nm.ExposureTime = _Node(100.0)
    nm.DeviceVendorName = _Node("HuaTeng", ro=True)

    res = apply_genicam_features(nm, {
        "PixelFormat": "RGB8",        # giltig enum
        "TriggerMode": "On",          # giltig enum
        "ExposureTime": 250.0,        # float
        "DeviceVendorName": "X",      # read-only → loggas, ej krasch
        "SaknasHelt": 1,              # okänd nod → loggas, ej krasch
        "Hoppas": None,               # None → hoppas över
    })
    assert res["PixelFormat"] == (True, "RGB8")
    assert res["TriggerMode"][0] is True
    assert res["ExposureTime"] == (True, 250.0)
    assert res["DeviceVendorName"][0] is False     # read-only fångas
    assert res["SaknasHelt"][0] is False           # okänd nod fångas
    assert "Hoppas" not in res                      # None applicerades aldrig
    assert nm.PixelFormat.value == "RGB8"          # faktiskt satt

    vals = read_genicam_features(nm, ["PixelFormat", "FinnsEj"])
    assert vals["PixelFormat"] == "RGB8" and vals["FinnsEj"] is None

    names = [n for n, _ in dump_genicam_features(nm)]
    assert "PixelFormat" in names and "ExposureTime" in names

    # Linjekameran är färg som standard (trigg sätts separat, se nedan)
    assert DEFAULT_SURFACE_FEATURES["PixelFormat"] == "RGB8"


def test_encoder_line_trigger_resolves_node_names():
    # Encoder-triggad line-scan ska mappa Huatengs ROTARYENC-modell till GenICam
    # via kandidat-namnsupplösning — även om kameran använder tillverkar-egna namn.
    from ..hal.real.cameras import GenICamSurfaceCamera, set_first_available

    # Fejk-kamera (Aravis-stil) som BARA har tillverkar-egna nodnamn (inte SFNC) →
    # kandidatlistan + set_first måste hitta dem ändå. set_str/int/float lyckas bara
    # för kända noder (och giltiga enum-värden), precis som AravisGigeCamera.
    class _Dev:
        def __init__(self):
            self.vals = {}
            self.nodes = {
                "TriggerSelector": {"LineStart", "FrameStart"},
                "TriggerMode": {"On", "Off"},
                "LineSource": {"RotaryEncoder", "Line0"},      # ej "TriggerSource"
                "TriggerActivation": {"RisingEdge", "FallingEdge"},
                "RotaryEncDir": None, "RotaryEncDiv": None, "RotaryEncMul": None,
            }
        def _set(self, name, value, enum=False):
            if name not in self.nodes: return False
            allowed = self.nodes[name]
            if enum and allowed is not None and value not in allowed: return False
            self.vals[name] = value; return True
        def set_str(self, n, v): return self._set(n, v, enum=True)
        def set_int(self, n, v): return self._set(n, int(v))
        def set_float(self, n, v): return self._set(n, float(v))
        def set_first(self, candidates, value):
            for n in candidates:
                ok = (self.set_str(n, value) if isinstance(value, str)
                      else self.set_int(n, value) if isinstance(value, (int, bool))
                      else self.set_float(n, value))
                if ok: return (n, True)
            return (None, False)

    dev = _Dev()
    cam = GenICamSurfaceCamera()
    res = cam._apply_line_trigger(dev)              # offline-applicering mot fejk-kamera
    assert res["selector"] == ("TriggerSelector", True)
    assert res["mode"] == ("TriggerMode", True)
    assert res["source"][1] is True and "LineSource" in res["source"][0]
    assert dev.vals["TriggerMode"] == "On"
    assert dev.vals["RotaryEncDir"] == 1            # forward → medurs (1)
    assert res["divider"][0] == "RotaryEncDiv" and dev.vals["RotaryEncDiv"] == 1

    # divider från kalibrering (linesync) ska nå kameran
    cam.configure_encoder_line_trigger(divider=8, direction="reverse")
    cam._apply_line_trigger(dev)
    assert dev.vals["RotaryEncDiv"] == 8 and dev.vals["RotaryEncDir"] == 2   # reverse → moturs

    # set_first faller tillbaka snyggt när inget namn finns
    assert dev.set_first(["FinnsInte", "HellerInte"], 1) == (None, False)


def test_camera_config_and_profile_roi():
    # Profilkamerorna: serienr binder RÖD≠GRÖN (cameras.json) + hårdvaru-ROI-band.
    from ..hal.real import camera_config
    from ..hal.real.cameras import GenICamProfileCamera

    # Defaults när filen saknas — appen ska funka ändå
    cfg = camera_config.load("/finns/inte/cameras.json")
    assert cfg["profile_red"]["serial"] is None and cfg["profile_red"]["roi_rows"] == 80
    assert cfg["surface"]["direction"] == "forward"

    # Roundtrip; okända fält ignoreras, saknade roller får default
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cameras.json"
        camera_config.save({"profile_red": {"serial": "SN-RED", "roi_rows": 128, "skräp": 9}}, p)
        got = camera_config.load(p)
        assert got["profile_red"]["serial"] == "SN-RED"
        assert got["profile_red"]["roi_rows"] == 128
        assert "skräp" not in got["profile_red"]
        assert got["profile_green"]["serial"] is None

    # skeleton föreslår serienr i ordning (människan bekräftar färg)
    sk = camera_config.skeleton(["A", "B", "C"])
    assert (sk["profile_red"]["serial"], sk["profile_green"]["serial"],
            sk["surface"]["serial"]) == ("A", "B", "C")

    # Hårdvaru-ROI via MVS-SDK: _apply_roi pratar med en MvsU3VCamera (set_int/
    # get_int_max). Fake-dev fångar satta värden. Bandet centreras via HeightMax,
    # offset nollas före höjd.
    class _Dev:
        def __init__(self, wmax=2448, hmax=2048):
            self.vals = {}; self._wmax = wmax; self._hmax = hmax
        def set_int(self, name, value): self.vals[name] = int(value); return True
        def get_int_max(self, name): return {"Width": self._wmax, "Height": self._hmax}.get(name)

    dev = _Dev()
    cam = GenICamProfileCamera("red", roi_rows=128)
    cam._apply_roi(dev)
    assert dev.vals["Height"] == 128
    assert dev.vals["OffsetY"] == (2048 - 128) // 2       # centrerat band

    # Kalibrerat offset (alignment) vinner över centrering
    cam.configure_roi(rows=200, offset_y=500)
    cam._apply_roi(dev)
    assert dev.vals["Height"] == 200 and dev.vals["OffsetY"] == 500

    # roi_rows=None → full sensorram (live-preview vid idrifttagning)
    dev2 = _Dev()
    GenICamProfileCamera("green", roi_rows=None)._apply_roi(dev2)
    assert dev2.vals["Height"] == 2048 and dev2.vals["Width"] == 2448


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  ✓ {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  ✗ {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(fns)} tester gröna")
    raise SystemExit(0 if ok == len(fns) else 1)
