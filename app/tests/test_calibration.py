"""Tester för kalibreringskärnan (katalog, register, lager, körmotor) — headless.

Kör utan pytest:  python -m app.tests.test_calibration
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..core.calibration import (CALIB_METHODS, DEVICE_CATALOG, CalibrationRunner,
                                CalibrationStore, methods_for)


def test_catalog_and_registry_consistent():
    ids = {d[0] for d in DEVICE_CATALOG}
    # alla metod-nycklar pekar på enheter som finns i katalogen
    assert set(CALIB_METHODS).issubset(ids)
    # varje metod har id/title/desc/steps, och stegen har (etikett, sekunder)
    for dev_id, methods in CALIB_METHODS.items():
        mids = [m["id"] for m in methods]
        assert len(mids) == len(set(mids)), f"dubblett-metod i {dev_id}"
        for m in methods:
            assert m["title"] and m["desc"] and m["steps"]
            for label, dur in m["steps"]:
                assert isinstance(label, str) and dur > 0
    # nyckelEnheter har metoder förberedda
    for must in ("prof_red", "prof_green", "surface", "lr400", "conveyor", "rig",
                 "laser_red", "laser_green", "photocell"):
        assert methods_for(must), f"{must} saknar kalibreringsmetoder"
    # 3× LR400 finns i katalogen och har nollning + ankrings-verifiering
    assert "lr400" in {d[0] for d in DEVICE_CATALOG}
    lr_ids = {m["id"] for m in methods_for("lr400")}
    assert {"zero_d0", "anchor"}.issubset(lr_ids)


def test_store_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "calib.json"
        st = CalibrationStore(p)
        assert st.get("prof_red", "exposure") is None
        assert st.count_done("prof_red") == 0
        st.set("prof_red", "exposure", {"exponering": "850 µs"})
        rec = st.get("prof_red", "exposure")
        assert rec["ok"] and rec["values"]["exponering"] == "850 µs" and rec["date"]
        assert st.count_done("prof_red") == 1
        # överlever omläsning från disk
        st2 = CalibrationStore(p)
        assert st2.get("prof_red", "exposure")["ok"]


def test_runner_completes_and_persists():
    with tempfile.TemporaryDirectory() as d:
        st = CalibrationStore(Path(d) / "c.json")
        r = CalibrationRunner(st, sim=True)
        seen = {"pct": [], "msgs": set(), "done": None}
        r.on_progress = lambda pct, msg: (seen["pct"].append(pct), seen["msgs"].add(msg))
        r.on_finished = lambda ok, values: seen.update(done=(ok, values))

        assert r.start("conveyor", "countsmm")
        assert r.running
        for _ in range(200):                      # ticka tills klar
            r.tick(0.1)
            if not r.running:
                break
        assert not r.running
        ok, values = seen["done"]
        assert ok and "counts/mm" in values
        assert st.count_done("conveyor") == 1
        # progress steg monotont och nådde stegen
        assert seen["pct"] == sorted(seen["pct"])
        assert len(seen["msgs"]) >= 3


def test_runner_real_mode_requires_connection():
    with tempfile.TemporaryDirectory() as d:
        st = CalibrationStore(Path(d) / "c.json")
        r = CalibrationRunner(st, sim=False)
        result = {}
        r.on_finished = lambda ok, values: result.update(ok=ok, values=values)
        assert not r.start("prof_red", "exposure", connected=False)
        assert result["ok"] is False and "fel" in result["values"]
        assert st.count_done("prof_red") == 0


def test_runner_cancel():
    with tempfile.TemporaryDirectory() as d:
        st = CalibrationStore(Path(d) / "c.json")
        r = CalibrationRunner(st, sim=True)
        assert r.start("rig", "zeroplane")
        r.tick(0.5)
        r.cancel()
        assert not r.running
        assert st.count_done("rig") == 0          # avbruten körning sparas inte


def test_surface_color_calibration():
    """Ytkamerans färgkalibrering: vitbalans + flat-field + 3×3-matris + apply + persistens."""
    import numpy as np
    from ..hal.real.surface_color import (SurfaceColorCalib, fit_white_balance,
                                          fit_flat_field, fit_color_matrix)
    # vitbalans: blå-svag neutral → blå-gain > 1, grön = 1, neutralt efter
    neutral = np.tile([200.0, 200.0, 160.0], (50, 1))
    wb = fit_white_balance(neutral)
    assert wb[2] > wb[1] and abs(wb[1] - 1.0) < 1e-3
    bal = neutral * wb
    assert abs(bal[:, 0].mean() - bal[:, 2].mean()) < 2

    # flat-field: höger halva mörkare → gain plattar ut
    W = 200
    white = np.ones((30, W, 3)) * 220.0
    white[:, W // 2:, :] *= 0.6
    flat = fit_flat_field(white)
    corr = white[0] * flat
    assert corr.std() / corr.mean() < 0.02

    # 3×3-matris: grön-överhörning → matrisen återställer mot facit
    facit = np.array([[200, 40, 40], [40, 170, 60], [40, 60, 200],
                      [200, 200, 40], [128, 128, 128]], float)
    skew = np.array([[1, 0, 0], [0.1, 1, 0.1], [0, 0, 0.9]])
    meas = facit @ skew.T
    ccm = fit_color_matrix(meas, facit)
    assert np.abs(meas @ ccm.T - facit).mean() < 3

    # full apply-kedja + spara/ladda-roundtrip + identitet
    cal = SurfaceColorCalib(wb=wb, flat=flat, ccm=ccm)
    img = (np.random.RandomState(0).rand(8, W, 3) * 255).astype(np.uint8)
    out = cal.apply(img)
    assert out.shape == img.shape and out.dtype == np.uint8
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "c.npz"); cal.save(p)
        cal2 = SurfaceColorCalib.load(p)
        assert np.allclose(cal2.wb, cal.wb) and np.allclose(cal2.ccm, cal.ccm)
        assert np.array_equal(cal2.apply(img), out)
    assert np.array_equal(SurfaceColorCalib().apply(img), img)   # tom = identitet


def test_surface_color_chart_segmentation():
    """Färgtavle-matchning hittar fälten och matchar mot rätt facit."""
    import numpy as np
    from ..core.autocalib import match_color_chart, _CHART_FACIT
    cols = [(255, 255, 255), (220, 30, 30), (30, 170, 60), (30, 60, 200)]
    line = np.repeat(np.array(cols, float), 80, axis=0)
    pairs = match_color_chart(line)
    name_of = {tuple(v): k for k, v in _CHART_FACIT.items()}
    found = {name_of[tuple(int(x) for x in f)] for _, f in pairs}
    assert {"VIT", "ROD", "GRON", "BLA"}.issubset(found)


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
