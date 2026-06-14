"""Tester för automatisk kamerakalibrering (app/core/autocalib.py) — utan hårdvara.

Kör:  python -m app.tests.test_autocalib
"""
from __future__ import annotations

import time

import numpy as np

from ..core import autocalib
from ..core.calibration import CalibrationRunner, CalibrationStore


def _profile_frame(peak=200.0, row=40, rows=80, cols=200, noise=2.0):
    """Syntetisk profil-ROI: gaussisk laserstripe på 'row' + bakgrund + brus."""
    rng = np.random.default_rng(1)
    img = 18.0 + rng.normal(0, noise, (rows, cols))
    r = np.arange(rows)[:, None]
    img = img + peak * np.exp(-((r - row) ** 2) / (2 * 1.8 ** 2))
    return np.clip(img, 0, 255)


# ───────────────────────────── rena mätfunktioner ──────────────────────────────

def test_stripe_peak_and_row_and_fwhm():
    img = _profile_frame(peak=180, row=50)
    assert 150 < autocalib.stripe_peak(img) < 210
    assert abs(autocalib.find_stripe_row(img) - 50) < 1.0
    assert 2.0 <= autocalib.stripe_fwhm(img) <= 8.0
    # tom ram (laser av) → ingen stripe
    flat = 18.0 + np.zeros((80, 200))
    assert not np.isfinite(autocalib.find_stripe_row(flat))


def test_auto_exposure_hits_target():
    state = {"exp": 800.0}
    # kamera där toppintensiteten växer med exponering (800 µs → ~200)
    def grab(): return _profile_frame(peak=min(250.0, state["exp"] * 0.25), row=40)
    def set_exp(us): state["exp"] = us
    res = autocalib.auto_exposure(grab, set_exp, target=200.0)
    assert "fel" not in res
    peak = float(res["toppintensitet"].split("/")[0])
    assert 188 <= peak <= 212                      # nära mål, mättnadsfritt
    assert "µs" in res["exponering"] and "dB" in res["SNR"]


def test_auto_exposure_no_stripe_errors():
    def grab(): return 18.0 + np.zeros((80, 200))   # laser av
    res = autocalib.auto_exposure(grab, lambda us: None)
    assert "fel" in res


def test_dark_stats():
    rng = np.random.default_rng(0)
    def grab(): return np.clip(2.0 + rng.normal(0, 1.0, (80, 200)), 0, 255)
    res = autocalib.dark_stats(grab, n=16)
    assert "medel" in res["bakgrund"] and res["hotspots"].startswith("0 ")


def test_stripe_roi_offset_centers_band():
    # full sensor 2048 rader, stripe vid 1024, band 80 → offset 984 (centrerat)
    full = np.full((2048, 200), 18.0)
    full[1022:1027, :] += 200
    res = autocalib.stripe_roi_offset(full, roi_rows=80)
    assert res["_offset_y"] == 1024 - 40 or abs(res["_offset_y"] - 984) <= 3


def test_white_balance_and_flatfield():
    # vitreferens med R<G<B → gain_r>1>gain_b, grön normaliserad till 1.00
    rows = np.zeros((50, 3)); rows[:, 0] = 100; rows[:, 1] = 120; rows[:, 2] = 140
    wb = autocalib.white_balance(rows)
    assert abs(wb["_gain_g"] - 1.0) < 1e-6
    assert wb["_gain_r"] > 1.0 > wb["_gain_b"]
    # vinjetterad vit rad → ojämnhet minskar efter korrektion
    x = np.linspace(-1, 1, 200)
    vign = 200 * (1 - 0.3 * x ** 2)                 # ljusare i mitten
    ff = autocalib.flat_field(np.tile(vign, (40, 1)))
    before = float(ff["ojämnhet före"].replace(" %", "").replace(",", "."))
    after = float(ff["efter"].replace(" %", "").replace(",", "."))
    assert before > 1.0 and after < 0.5


# ─────────────────────── kontext + registry + runner ───────────────────────────

class _FakeProfileCam:
    def __init__(self, stripe=True):
        self._exp = 800.0; self._roi_rows = 80; self._stripe = stripe; self.offset = None
    def read_stripe(self, y_mm=0.0, n=200):
        peak = min(250.0, self._exp * 0.25) if self._stripe else 0.0
        return _profile_frame(peak=peak, row=40)
    def configure(self, **f):
        if "ExposureTime" in f: self._exp = f["ExposureTime"]
    def configure_roi(self, rows=None, offset_y=None): self.offset = offset_y


class _FakeSurfaceCam:
    def __init__(self): self.wb = None
    def grab_line(self):
        row = np.zeros((200, 3)); row[:, 0] = 100; row[:, 1] = 120; row[:, 2] = 140
        return row
    def configure(self, **f): self.wb = f


class _FakeLaser:
    def __init__(self): self._on = True; self.armed = False
    @property
    def is_on(self): return self._on
    def arm(self, confirm=False): self.armed = bool(confirm); return self.armed
    def set(self, v):
        self._on = bool(v); return True


class _FakeLED:
    def __init__(self): self.on = False
    def set(self, v): self.on = bool(v); return True


class _FakePhotocell:
    def __init__(self, edges=8): self.edges = edges
    def collect_load_events(self, n=10, timeout_s=30.0):
        return [i * 0.12 for i in range(min(n, self.edges))]


class _FakeScanner:
    def __init__(self, stripe=True):
        self.profile_red = _FakeProfileCam(stripe)
        self.profile_green = _FakeProfileCam(stripe)
        self.surface = _FakeSurfaceCam()
        self.laser_red = _FakeLaser(); self.laser_green = _FakeLaser()
        self.led_white = _FakeLED(); self.photocell = _FakePhotocell()


def test_run_auto_exposure_and_dark_and_wb():
    ctx = autocalib.CalibrationContext(_FakeScanner(stripe=True))
    exp = autocalib.run_auto("prof_red", "exposure", ctx)
    assert "fel" not in exp and "exponering" in exp
    # dark släcker lasern (säkert) före mätning
    dark = autocalib.run_auto("prof_red", "dark", ctx)
    assert "fel" not in dark and ctx.scanner.laser_red.is_on is False
    # stripe_roi sätter ROI-offset i kameran
    roi = autocalib.run_auto("prof_green", "stripe_roi", ctx)
    assert "fel" not in roi and ctx.scanner.profile_green.offset is not None
    # vitbalans skriver gains till ytkameran
    wb = autocalib.run_auto("surface", "whitebal", ctx)
    assert "fel" not in wb and ctx.scanner.surface.wb is not None
    # ej auto-metod → tom dict
    assert autocalib.run_auto("prof_red", "intrinsics", ctx) == {}


def test_run_auto_reports_error_when_laser_off():
    ctx = autocalib.CalibrationContext(_FakeScanner(stripe=False))
    res = autocalib.run_auto("prof_red", "exposure", ctx)
    assert "fel" in res


def test_runner_real_mode_runs_auto_measurement(tmp_path=None):
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        store = CalibrationStore(Path(d) / "c.json")
        ctx = autocalib.CalibrationContext(_FakeScanner(stripe=True))
        runner = CalibrationRunner(store, sim=False, context=ctx)
        out = {}
        runner.on_finished = lambda ok, vals: out.update({"ok": ok, "vals": vals})
        assert runner.start("prof_red", "exposure", connected=True)
        # driv ticks tills klar (auto-tråden hinner mäta klart)
        for _ in range(400):
            runner.tick(0.05)
            if not runner.running:
                break
            time.sleep(0.005)
        assert not runner.running
        assert out.get("ok") is True
        assert "exponering" in out["vals"]                 # RIKTIGT uppmätt värde
        assert store.get("prof_red", "exposure")["ok"] is True


class _FakeConveyor:
    def __init__(self):
        self._counts_per_mm = 100.0; self._sp = 0.0; self._enc = 0; self._n = 0
    def set_speed(self, v): self._sp = v
    def read_speed_mm_s(self):
        self._n += 1
        v = min(52.0, 50.0 * (1 - 2.71828 ** (-self._n / 3.0)))   # ramp mot 50
        return (v, v)
    def encoder_counts(self): return (self._enc, self._enc - 4)    # liten A/B-skillnad
    def zero(self): pass
    def move_mm(self, d, v): self._enc += int(d * self._counts_per_mm)


def test_conveyor_pure_metrics():
    t = [i * 0.05 for i in range(30)]
    v = [min(52.0, 50.0 * (1 - 2.71828 ** (-i * 0.05 / 0.1))) for i in range(30)]
    m = autocalib.step_response_metrics(t, v, 50.0)
    assert "ms" in m["stigtid"] and float(m["översläng"].replace(" %", "")) >= 0
    assert autocalib.belt_drift(200.0, 199.8, 200.0)["status"] == "JUSTERA M2-trim"
    assert autocalib.belt_drift(200.0, 199.98, 200.0)["status"] == "inom tolerans"


def test_run_auto_conveyor_speedstep_and_sync():
    saved = autocalib.time.sleep
    autocalib.time.sleep = lambda *a, **k: None          # snabba upp testet
    try:
        sc = _FakeScanner(); sc.conveyor = _FakeConveyor()
        ctx = autocalib.CalibrationContext(sc); ctx.step_n = 12
        ss = autocalib.run_auto("conveyor", "speedstep", ctx)
        assert "fel" not in ss and "stigtid" in ss
        assert sc.conveyor._sp == 0.0                    # bandet ALLTID stoppat efteråt
        bs = autocalib.run_auto("conveyor", "beltsync", ctx)
        assert "fel" not in bs and "drift" in bs
    finally:
        autocalib.time.sleep = saved


def test_roboclaw_driver_wraps_basicmicro():
    # Verifierar drivern mot en INJICERAD fejk-Basicmicro (ingen seriell hårdvara).
    from ..hal.real.roboclaw_conveyor import RoboClawConveyor

    class _FakeMC:
        def __init__(self): self.enc = 1000; self.calls = []; self.closed = False
        def Open(self): return True
        def ReadVersion(self, a): return (True, "USB Roboclaw 2x7a v4.1.34")
        def ReadEncM1(self, a): return (True, self.enc, 0)
        def ReadEncM2(self, a): return (True, self.enc, 0)
        def SpeedM1M2(self, a, m1, m2): self.calls.append(("speed", m1, m2)); return True
        def DutyM1M2(self, a, m1, m2): self.calls.append(("duty", m1, m2)); return True
        def ReadSpeedM1(self, a): return (True, 3000, 0)     # 3000 counts/s → 30 mm/s
        def ReadSpeedM2(self, a): return (True, 3000, 0)
        def SpeedAccelDistanceM1M2(self, a, ac, s1, d1, s2, d2, b):
            self.enc += d1; self.calls.append(("move", d1)); return True
        def ReadMainBatteryVoltage(self, a): return (True, 124)   # 12,4 V
        def ReadTemp(self, a): return (True, 312)                 # 31,2 °C
        def ReadError(self, a): return (True, 0)
        def close(self): self.closed = True

    mc = _FakeMC()
    rc = RoboClawConveyor(controller=mc, counts_per_mm=100.0)
    rc.open()
    assert rc._connected and "Roboclaw" in rc.firmware()
    assert abs(rc.position_mm()) < 1e-9                  # nollreferens vid open
    rc.set_speed(10.0)                                    # 10 mm/s → 1000 counts/s
    assert ("speed", 1000, 1000) in mc.calls
    assert rc.read_speed_mm_s() == (30.0, 30.0)
    rc.move_mm(200, 30)                                   # 200 mm × 100 = 20000 counts
    assert ("move", 20000) in mc.calls
    assert abs(rc.position_mm() - 200.0) < 1e-6
    h = rc.health()
    assert h["battery_v"] == 12.4 and h["temp_c"] == 31.2 and h["enc_m1"] == 21000
    rc.close()
    assert mc.closed and ("speed", 0, 0) in mc.calls     # stoppar bandet vid close


class _FakeModbus:
    def __init__(self, value=9000, err=False):
        self.value, self.err, self.closed = value, err, False
    class _RR:
        def __init__(self, regs, err): self.registers, self._err = regs, err
        def isError(self): return self._err
    def connect(self): return True
    def read_holding_registers(self, address, count, slave):
        return _FakeModbus._RR([] if self.err else [self.value], self.err)
    def read_input_registers(self, address, count, slave):
        return _FakeModbus._RR([] if self.err else [self.value], self.err)
    def close(self): self.closed = True


def test_lr400_config_defaults_and_d0():
    from ..hal.real import lr400_config
    import tempfile
    from pathlib import Path
    # Waveshare 4CH → 4 EGNA portar (en LR400 per port, unit=1)
    d = lr400_config.DEFAULTS
    assert d["ch1"]["port"] == "/dev/ttyUSB0" and d["ch2"]["port"] == "/dev/ttyUSB1"
    assert d["ch1"]["unit"] == 1 and d["ch3"]["unit"] == 1
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "lr400.json"
        lr400_config.save(lr400_config.load(p), p)
        lr400_config.set_d0("ch2", 123.4, p)
        assert lr400_config.load(p)["ch2"]["d0_mm"] == 123.4
        assert lr400_config.load(p)["ch1"]["d0_mm"] == 100.0     # andra orörda


def test_lr400_driver_reads_thickness():
    from ..hal.real.lr400_modbus import LR400ModbusLaser
    from ..geometry import RIG
    mc = _FakeModbus(value=9000)                     # 9000 × 0,01 = 90,0 mm avstånd
    las = LR400ModbusLaser(0, 0.0, d0_mm=100.0, scale=0.01, client=mc)
    las.open()
    assert las.read_distance_mm() == 90.0
    assert abs(las.read_mm() - 10.0) < 1e-9          # tjocklek = 100 − 90
    mean, rms, n = las.read_distance_avg(5)
    assert mean == 90.0 and n == 5 and rms == 0.0
    las.set_d0(95.0)
    assert abs(las.read_mm() - 5.0) < 1e-9
    mc.err = True                                    # sensorn ser inget mål
    assert las.read_distance_mm() is None
    assert las.read_mm() == RIG.board_thick_mm       # pipeline-fallback, ingen krasch


class _FakeLR400:
    def __init__(self, dist): self.dist, self.d0 = dist, 100.0
    def read_distance_avg(self, n=50): return (self.dist, 0.005, n)   # 5 µm RMS
    def set_d0(self, v): self.d0 = v


def test_run_auto_lr400_zero_d0():
    from ..hal.real import lr400_config
    sc = _FakeScanner()
    sc.point_lasers = [_FakeLR400(100.2), _FakeLR400(99.8), _FakeLR400(100.1)]
    saved = lr400_config.set_d0
    lr400_config.set_d0 = lambda *a, **k: None        # rör inte riktiga data/lr400.json
    try:
        ctx = autocalib.CalibrationContext(sc)
        res = autocalib.run_auto("lr400", "zero_d0", ctx)
    finally:
        lr400_config.set_d0 = saved
    assert "fel" not in res and "D0 ch1/2/3" in res
    assert res["kanaler ok"] == "3/3"
    assert sc.point_lasers[0].d0 == 100.2             # D0 satt till uppmätt avstånd


class _FakeGPIO:
    BOARD = 1; OUT = 2; IN = 3; LOW = 0; HIGH = 1; FALLING = 4
    def __init__(self, seq=None): self.state = {}; self._seq = list(seq or [])
    def setmode(self, m): pass
    def setwarnings(self, b): pass
    def setup(self, p, mode, initial=None): self.state[p] = initial if initial is not None else 1
    def output(self, p, v): self.state[p] = v
    def input(self, p): return self._seq.pop(0) if self._seq else self.state.get(p, 1)
    def add_event_detect(self, *a, **k): pass
    def remove_event_detect(self, *a, **k): pass


def test_gpio_field_io_arm_gate():
    # Lasersäkerhet kodlåst: enable VÄGRAS tills arm(confirm=True). LED behöver ingen arm.
    from app.hal.real import gpio_io
    gpio_io._GPIO = _FakeGPIO()
    laser, laser_g, led, pc = gpio_io.make_field_io()
    laser.open(); led.open()
    assert laser.requires_arm and not led.requires_arm
    assert laser.set(True) is False and laser.is_on is False     # vägrad — ej armad
    assert laser.arm(confirm=True) is True
    assert laser.set(True) is True and laser.is_on is True        # nu tillåten
    laser.close()
    assert laser.is_on is False and laser.is_armed is False       # close släcker + avarmar
    assert led.set(True) is True and led.is_on is True            # LED kräver ingen arm
    gpio_io._GPIO = None


def test_photocell_collect_load_events():
    from app.hal.real import gpio_io
    from app.hal.real.gpio_io import PhotocellInput, PIN_PHOTOCELL
    # sekvens som ger 3 fallande flanker (1→0)
    gpio_io._GPIO = _FakeGPIO(seq=[1, 1, 0, 1, 0, 1, 0])
    pc = PhotocellInput(PIN_PHOTOCELL); pc.open()
    stamps = pc.collect_load_events(n=3, timeout_s=1.0, poll_dt=0.0)
    assert len(stamps) == 3
    gpio_io._GPIO = None


def test_line_straightness_and_detection_stats():
    s = autocalib.line_straightness(_profile_frame(peak=180, row=40))
    assert "bow" in s and float(s["bow"].split()[0]) < 3.0
    d = autocalib.detection_stats([0.0, 0.12, 0.24, 0.36], 4)
    assert d["detektioner"] == "4/4" and d["dubbeltrigg"] == "0"
    assert "fel" in autocalib.detection_stats([], 10)


def test_run_auto_gpio_led_photocell_laser():
    sc = _FakeScanner(stripe=True)
    ctx = autocalib.CalibrationContext(sc)
    u = autocalib.run_auto("led_white", "uniform", ctx)
    assert "fel" not in u and "ojämnhet före" in u
    assert sc.led_white.on is False                       # LED släckt efteråt
    pcr = autocalib.run_auto("photocell", "trigger", ctx)
    assert "fel" not in pcr and "detektioner" in pcr
    # laser GRINDAT: släckt → vägrar mäta (tänder aldrig själv)
    sc.laser_red.set(False)
    assert "fel" in autocalib.run_auto("laser_red", "width", ctx)
    sc.laser_red.arm(confirm=True); sc.laser_red.set(True)    # operatör + interlock
    assert "FWHM centrum" in autocalib.run_auto("laser_red", "width", ctx)
    assert "bow" in autocalib.run_auto("laser_red", "straight", ctx)


def test_rig_pure_functions():
    # nollplan: nästan identiska profiler → låg RMS
    prof = [np.full(200, 1.2) + 0.001 * i for i in range(10)]
    bx = autocalib.belt_baseline(prof)
    assert "_bx" in bx and "bandprofil RMS" in bx and len(bx["_bx"]) == 200
    # huvud-alignment: identiska → ~0 offset; +0,5 mm → 0,5 mm offset
    z = np.linspace(10, 12, 50)
    a0 = autocalib.head_alignment(z, z.copy())
    assert abs(a0["_z_offset_mm"]) < 1e-6
    a1 = autocalib.head_alignment(z + 0.5, z.copy())
    assert abs(a1["_z_offset_mm"] - 0.5) < 1e-6
    assert "fel" in autocalib.head_alignment([1, 2], [1, 2])      # för få punkter
    # bräddimensioner + facit-jämförelse
    z = np.zeros(200); z[60:140] = 20.04
    dims = autocalib.board_profile_dims(z, mm_per_px=0.9)
    assert abs(dims["_thick"] - 20.04) < 1e-6 and dims["_width"] > 0
    diffs = autocalib.compare_to_facit({"_thick": 20.04, "_width": 75.2},
                                       {"tjocklek": 20.0, "bredd": 75.0})
    assert diffs["tjocklek-fel"] == "0.04 mm" and diffs["bredd-fel"] == "0.20 mm"
    assert "fel" in autocalib.board_profile_dims(np.zeros(200), 0.9)   # ingen bräda


def test_run_auto_rig_gated_and_measures():
    sc = _FakeScanner(stripe=True)
    ctx = autocalib.CalibrationContext(sc)
    # GRINDAT: lasrar släckta → vägrar mäta
    sc.laser_red.set(False); sc.laser_green.set(False)
    assert "fel" in autocalib.run_auto("rig", "zeroplane", ctx)
    assert "fel" in autocalib.run_auto("rig", "align", ctx)
    # tänd båda (simulerar interlock-bekräftelse)
    for la in (sc.laser_red, sc.laser_green):
        la.arm(confirm=True); la.set(True)
    saved_s, saved_l = autocalib._save_json, autocalib._load_json
    autocalib._save_json = lambda *a, **k: None          # rör inte riktiga data/-filer
    autocalib._load_json = lambda *a, **k: None
    try:
        zp = autocalib.run_auto("rig", "zeroplane", ctx)
        assert "fel" not in zp and "bandprofil RMS" in zp and "_bx" not in zp
        al = autocalib.run_auto("rig", "align", ctx)
        assert "fel" not in al and "Z-offset" in al and "_z_offset_mm" not in al
        rb = autocalib.run_auto("rig", "refboard", ctx)
        assert isinstance(rb, dict)                       # mäter el. ber om facit, kraschar ej
    finally:
        autocalib._save_json, autocalib._load_json = saved_s, saved_l


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
