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
    def __init__(self): self.on = True
    def set(self, v): self.on = bool(v)


class _FakeScanner:
    def __init__(self, stripe=True):
        self.profile_red = _FakeProfileCam(stripe)
        self.profile_green = _FakeProfileCam(stripe)
        self.surface = _FakeSurfaceCam()
        self.laser_red = _FakeLaser(); self.laser_green = _FakeLaser()


def test_run_auto_exposure_and_dark_and_wb():
    ctx = autocalib.CalibrationContext(_FakeScanner(stripe=True))
    exp = autocalib.run_auto("prof_red", "exposure", ctx)
    assert "fel" not in exp and "exponering" in exp
    # dark släcker lasern (säkert) före mätning
    dark = autocalib.run_auto("prof_red", "dark", ctx)
    assert "fel" not in dark and ctx.scanner.laser_red.on is False
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
