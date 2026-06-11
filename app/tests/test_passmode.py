"""Pass-läge (single/multi) — tillståndsmaskin: skanna → backa till anhåll → analys.

Liten rigg: en bräda skannas framåt, backar till fotocellen (nollar), och i multi
körs flera pass på SAMMA bräda. Single = 1 pass + notis "ladda ny" + analys.

Kör utan pytest:  python -m app.tests.test_passmode
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


def _run_until(ctrl, pred, max_ticks=4000):
    for _ in range(max_ticks):
        ctrl._last_ns = time.perf_counter() - 0.05   # tvinga dt≈0.05 s/tick
        ctrl._tick()
        if pred(ctrl):
            return True
    return False


def _controller(**cfg):
    c = AppController(AppConfig(mode="sim", **cfg).validate(), LiveImageProvider())
    c._s.running = True
    c._new_board()
    return c


def test_single_pass_one_pass_then_reload():
    c = _controller(pass_mode="single")
    assert c._s.phase == "scanning"
    assert _run_until(c, lambda c: c._s.phase == "reload"), "nådde aldrig reload"
    assert c._s.pass_count == 1
    assert c._s.board_count == 1
    assert c._grade is not None
    assert "Ladda" in c.notifyText                    # notis om att ladda ny bräda


def test_single_reload_then_next_board_resets():
    c = _controller(pass_mode="single")
    _run_until(c, lambda c: c._s.phase == "reload")
    c.nextBoard()
    assert c._s.phase == "scanning"
    assert c._s.pass_count == 0
    assert c.notifyText == ""


def test_multi_pass_rescans_same_board():
    c = _controller(pass_mode="multi", passes_target=3)
    saw_returning = {"v": False}

    def step(cc):
        if cc._s.phase == "returning":
            saw_returning["v"] = True
        return cc._s.phase == "reload"

    assert _run_until(c, step), "multi nådde aldrig reload"
    assert saw_returning["v"], "multi backade aldrig till anhåll"
    assert c._s.pass_count == 3                        # 3 pass
    assert c._s.board_count == 1                       # men EN bräda
    assert len(c._pass_grades) == 3


def test_returning_decreases_then_homes():
    c = _controller(pass_mode="single")
    # kör till vändpunkten
    assert _run_until(c, lambda c: c._s.phase == "returning")
    pos_at_turn = c._s.feed_pos_mm
    assert pos_at_turn > 0
    # under återgång minskar positionen mot 0
    _run_until(c, lambda c: c._s.feed_pos_mm < pos_at_turn - 1)
    assert c._s.feed_pos_mm < pos_at_turn


def test_combine_grades_worst_governs():
    from ..processing.grade import Grade
    c = _controller(pass_mode="multi", passes_target=2)
    c._pass_grades = [Grade("B", "t", "#fff", 75, []), Grade("D", "t", "#fff", 45, [])]
    g = c._combine_grades()
    assert g.cls == "D"                                # sämsta klassen styr
    assert g.score == 60                               # medel (75+45)/2


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
