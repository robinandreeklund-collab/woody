"""Grind/segmentering för löpande flöde — BoardGate + scan_stream.

Tillståndsmaskinen testas helt utan hårdvara (syntetisk position/närvaro), och
scan_stream-wiringen mot en minimal fejk-scanner.

Kör utan pytest:  python -m app.tests.test_segmentation
"""
from __future__ import annotations

import threading

import numpy as np

from ..processing.segmentation import BoardGate, GateConfig
from ..processing.acquisition import AcquisitionPipeline
from ..processing.triangulate import STRIPE_ROWS


def _drive(gate: BoardGate, present_windows, total, step=1.0):
    """Mata gaten med pos 0..total och present enligt fönster. Returnera händelser."""
    ev = []
    p = 0.0
    while p < total:
        present = any(s <= p < e for s, e in present_windows)
        ev.extend(gate.update(p, present))
        p += step
    return ev


# ----------------------------------------------------------------- ren tillståndsmaskin
def test_tva_brador_olika_gap():
    g = BoardGate(GateConfig(row_pitch_mm=1.0, sensor_offset_mm=0.0,
                             min_gap_mm=5.0, min_board_mm=10.0))
    ev = _drive(g, [(0, 60), (95, 160)], 200)        # gap = 35 mm
    slut = [e for e in ev if e.kind == "slut"]
    assert len(slut) == 2, f"förväntade 2 brädor, fick {len(slut)}"
    assert {e.board_id for e in slut} == {1, 2}


def test_godtyckligt_gap_andra_bradan_tatare():
    g = BoardGate(GateConfig(row_pitch_mm=1.0, min_gap_mm=5.0, min_board_mm=10.0))
    # samma två brädor men bara 8 mm mellanrum andra gången
    ev = _drive(g, [(0, 50), (58, 110)], 160)
    assert len([e for e in ev if e.kind == "slut"]) == 2


def test_kort_dropout_splittrar_inte():
    g = BoardGate(GateConfig(row_pitch_mm=1.0, min_gap_mm=5.0, min_board_mm=10.0))
    # en bräda 0..100 med en 2 mm-glipa (< min_gap) vid 50 → ska förbli EN bräda
    ev = _drive(g, [(0, 50), (52, 100)], 140)
    assert len([e for e in ev if e.kind == "slut"]) == 1


def test_for_kort_segment_kasseras():
    g = BoardGate(GateConfig(row_pitch_mm=1.0, min_gap_mm=5.0, min_board_mm=20.0))
    ev = _drive(g, [(0, 8)], 40)                      # 8 mm < 20 mm
    assert [e for e in ev if e.kind == "slut"] == []
    assert g.board_id == 0                            # id:t återlämnat


def test_sensor_offset_forskjuter_men_bevarar_langd():
    cfg = GateConfig(row_pitch_mm=1.0, sensor_offset_mm=20.0, min_gap_mm=5.0,
                     min_board_mm=10.0)
    g = BoardGate(cfg)
    ev = _drive(g, [(0, 60)], 140)                    # bräda 60 mm vid givaren
    rader = [e for e in ev if e.kind == "rad"]
    slut = [e for e in ev if e.kind == "slut"]
    assert len(slut) == 1
    # imaging-linjen ser brädan förskjuten 20 mm: ~20..80
    assert rader[0].position_mm >= 20.0
    assert 78.0 <= slut[0].position_mm <= 82.0        # bakkant ~ 80 mm
    # längden bevaras (~60 mm)
    assert 58.0 <= (slut[0].position_mm - rader[0].position_mm + 1) <= 62.0


def test_rad_takt_foljer_row_pitch():
    g = BoardGate(GateConfig(row_pitch_mm=2.0, min_gap_mm=5.0, min_board_mm=10.0))
    ev = _drive(g, [(0, 40)], 80, step=0.5)
    rader = [e for e in ev if e.kind == "rad"]
    # ~40 mm / 2 mm = ~20 rader (±1)
    assert 19 <= len(rader) <= 21
    # jämnt fördelade ~2 mm isär
    steps = np.diff([e.position_mm for e in rader])
    assert np.allclose(steps, 2.0, atol=1e-6)


# ----------------------------------------------------------------- scan_stream-wiring
class _FakeCam:
    """Profilkamera-stub: syntetisk laserstripe (ljus rad i mitten)."""
    def read_stripe(self, y_mm, n=200):
        rr = np.arange(STRIPE_ROWS)[:, None]
        img = np.exp(-((rr - STRIPE_ROWS / 2) ** 2) / (2 * 1.6 ** 2)) * 220.0
        return np.clip(np.repeat(img, n, axis=1), 0, 255)


class _FakeSurface:
    def surface_image(self):
        return np.full((20, 67, 3), 150, np.uint8)


class _FakeScanner:
    """Minimal scanner för löpande flöde: bandet rör sig, brädor i givar-fönster."""
    def __init__(self, windows, step=1.0):
        self._pos = 0.0
        self._windows = windows
        self._step = step
        self.profile_red = _FakeCam()
        self.profile_green = _FakeCam()
        self.surface = _FakeSurface()

    def feed_position_mm(self):
        p = self._pos
        self._pos += self._step
        return p

    def board_present(self):
        p = self._pos - self._step          # samma pos som senast returnerad
        return any(s <= p < e for s, e in self._windows)


def test_scan_stream_yieldar_en_board_per_brada():
    scanner = _FakeScanner(windows=[(20, 120), (160, 240)])
    pipe = AcquisitionPipeline(scanner, cols=64, queue_size=8)
    gate = BoardGate(GateConfig(row_pitch_mm=1.0, min_gap_mm=5.0, min_board_mm=20.0))
    stop = threading.Event()

    boards = []
    gen = pipe.scan_stream(gate, stop)
    try:
        for board in gen:
            boards.append(board)
            if len(boards) == 2:
                break
    finally:
        gen.close()

    assert len(boards) == 2, f"förväntade 2 brädor, fick {len(boards)}"
    for b in boards:
        assert b.surface.shape[1] == 64                # cols
        assert b.zmap.shape[0] > 50                    # rader ackumulerade
        assert b.h == b.zmap.shape[0]


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
