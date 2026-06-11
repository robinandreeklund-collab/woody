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
