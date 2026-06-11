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
    from ..processing.stripe_gpu import centroid_batch
    rng = np.random.default_rng(3)
    roi = np.clip(20 + rng.normal(0, 4, (80, 200)), 0, 255)
    roi[38:43, :] += 180                      # laserstripe-band
    ref = subpixel_centroid(roi)
    gpu = np.asarray(centroid_batch(roi))
    both = np.isfinite(ref) & np.isfinite(gpu)
    assert both.sum() > 190                   # nästan alla kolumner hittar stripen
    assert np.nanmax(np.abs(ref[both] - gpu[both])) < 1e-3


def test_acquisition_pipeline_assembles_board():
    # trådad capture∥process → en hel bräda som går att gradera, med rimlig skevhet
    from ..processing.acquisition import AcquisitionPipeline
    s = SimScanner(); s.new_board()
    board, st = AcquisitionPipeline(s, cols=200).scan_board(n_rows=60)
    assert board.zmap.shape == (60, 200)
    assert board.surface.shape == (60, 200, 3)
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
