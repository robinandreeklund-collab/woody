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
    assert RIG.tri_angle_deg == 20.0
    assert RIG.oblique_deg == 30.0
    assert abs(RIG.baseline_mm - 247) < 2
    assert abs(RIG.board_aspect - 500 / 75) < 1e-6
    assert RIG.board_thick_mm == 20.0


def test_grade_clean_vs_reject():
    a = grade_board([], (0.5, 0.3, 0.2))
    assert a.cls == "A" and a.score >= 85
    bad = [{"type": "rot", "r": 30}, {"type": "rot", "r": 30},
           {"type": "wane", "r": 100, "depth": 10}, {"type": "crack", "len": 120, "r": 60}]
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
