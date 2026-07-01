"""Löpande flöde (run_mode=flow) — controllern kör scan_stream + BoardGate.

Verifierar att flödesläget startar en flödestråd, segmenterar det virtuella
sim-bandet i enskilda brädor och graderar dem löpande (utan pass-koreografi).

Kör utan pytest:  python -m app.tests.test_flowmode
"""
from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication           # noqa: E402

from ..core.config import AppConfig                  # noqa: E402
from ..core.run_controller import AppController      # noqa: E402
from ..ui.image_provider import LiveImageProvider    # noqa: E402

_app = QGuiApplication.instance() or QGuiApplication([])


def _flow_controller(**cfg):
    c = AppController(AppConfig(mode="sim", run_mode="flow",
                               feed_mm_s=2000.0, gap_mm=20.0, **cfg).validate(),
                      LiveImageProvider())
    return c


def _pump_until(c, pred, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        c._drain_flow()                # konsumera färdiga brädor (GUI-tråden)
        if pred(c):
            return True
        time.sleep(0.01)
    return False


def test_flow_graderar_flera_brador():
    c = _flow_controller()
    assert c.runMode == "flow"
    c.toggleRun()                       # running → startar flödestråden
    try:
        assert c._s.phase == "flow"
        ok = _pump_until(c, lambda c: c._s.board_count >= 2)
        assert ok, f"fick bara {c._s.board_count} brädor i flödet"
        assert c._grade is not None
        assert len(c._history) >= 2
        # varje historikpost är en bräda (1 pass i flöde)
        assert c._history[0]["passes"] == 1
    finally:
        c.toggleRun()                   # stoppar flödestråden snyggt
    assert not c._s.running
    assert c._flow_thread is None


def test_byta_lage_stoppar_flodet():
    c = _flow_controller()
    c.toggleRun()
    _pump_until(c, lambda c: c._s.board_count >= 1)
    c.setRunMode("pass")                # byte mitt i drift → stoppa flöde rent
    assert c._cfg.run_mode == "pass"
    assert not c._s.running
    assert c._flow_thread is None


def test_pass_lage_oforandrat_default():
    # default är pass-läge — flödet får inte ha smittat default-vägen
    c = AppController(AppConfig(mode="sim").validate(), LiveImageProvider())
    assert c.runMode == "pass"
    assert c._cfg.run_mode == "pass"


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
