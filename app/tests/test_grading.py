"""Tester för den nordiska A/B/C/D-graderingsmotorn (grade.py + grading_rules.py).

Princip som testas: "worst governs" — sämsta featuren avgör graden; ren bräda → A;
varje defekttyp kan ensam driva ned graden; styrande defekt rapporteras.

Kör utan pytest:  python -m app.tests.test_grading
Eller med pytest:  pytest app/tests/test_grading.py
"""
from __future__ import annotations

from ..geometry import RIG
from ..processing.grade import grade_board, Grade
from ..processing.grading_rules import NORDIC_ABCD, FEATURE_LABEL

DIMS = (RIG.board_len_mm, RIG.board_width_mm, RIG.board_thick_mm)
BL, BW, BT = DIMS


def test_clean_board_is_A():
    g = grade_board([], {"bow": 0.2, "cup": 0.1, "twist": 0.1, "crook": 0.1})
    assert isinstance(g, Grade)
    assert g.cls == "A"
    assert g.score >= 85
    assert g.governing == ""          # inget styr ned en ren bräda


def test_small_knot_stays_A_large_knot_drops():
    # liten kvist (2r/BW = 6/75 = 0.08 < 0.20) → A
    small = grade_board([{"type": "knot", "r": 3.0}], {})
    assert small.cls == "A"
    # stor kvist (2r/BW = 40/75 = 0.53 → ligger i C-spannet)
    big = grade_board([{"type": "knot", "r": 20.0}], {})
    assert big.cls == "C"
    assert "kvist" in big.governing


def test_knot_over_D_limit_is_reject():
    # 2r/BW > 0.85 → V (vrak). r = 35 → 70/75 = 0.93
    g = grade_board([{"type": "knot", "r": 35.0}], {})
    assert g.cls == "V"
    assert "kvist" in g.governing


def test_wane_depth_drives_grade():
    # vankantdjup 8 mm / 20 mm tjocklek = 0.40 → C-gräns
    g = grade_board([{"type": "wane", "r": 50.0, "depth": 8.0}], {})
    assert g.cls in ("C", "D")           # djup styr (0.40 ≤ C)
    assert "vankant" in g.governing


def test_crack_length_drives_grade():
    # spricka 200 mm / 500 mm = 0.40 → ligger i D-spannet (>0.33)
    g = grade_board([{"type": "crack", "len": 200.0, "r": 100.0}], {})
    assert g.cls == "D"
    assert "spricka" in g.governing


def test_rot_is_strict():
    # röta tillåts inte i A/B alls; även en liten fläck → minst C
    g = grade_board([{"type": "rot", "r": 20.0}], {})
    assert g.cls in ("C", "D", "V")
    assert g.cls != "A" and g.cls != "B"
    assert "röta" in g.governing


def test_warp_drives_grade():
    # flatböj 30 mm på 500 mm bräda → skalas *2000/500 = ×4 → 120 mm/2m ≫ D(40) → V
    g = grade_board([], {"bow": 30.0, "cup": 0.0, "twist": 0.0, "crook": 0.0})
    assert g.cls == "V"
    assert "flatböj" in g.governing
    # måttlig böj: 2 mm → 8 mm/2m = A-gräns
    g2 = grade_board([], {"bow": 2.0, "cup": 0.0, "twist": 0.0, "crook": 0.0})
    assert g2.cls == "A"


def test_twist_drives_grade():
    # vridning 3 mm /500 → 12 mm/2m = C-gräns för twist
    g = grade_board([], {"bow": 0.0, "cup": 0.0, "twist": 3.0, "crook": 0.0})
    assert g.cls == "C"
    assert "vridning" in g.governing


def test_worst_governs():
    # liten kvist (A) + grov spricka (D) → brädan blir D
    defects = [{"type": "knot", "r": 3.0},
               {"type": "crack", "len": 200.0, "r": 100.0}]
    g = grade_board(defects, {})
    assert g.cls == "D"
    assert "spricka" in g.governing
    # kvist ska INTE vara styrande (den klarade A)
    assert "kvist" not in g.governing


def test_holes_counted():
    # 4 hål → ligger i D-spannet (C tillåter 2, D tillåter 6)
    defects = [{"type": "hole", "r": 3.0} for _ in range(4)]
    g = grade_board(defects, {})
    assert g.cls == "D"
    assert g.breakdown["hole_count"]["value"] == 4


def test_breakdown_and_meta_consistent():
    g = grade_board([{"type": "knot", "r": 20.0}], {})
    # varje feature i rulesettet ska finnas i breakdown
    for key in NORDIC_ABCD:
        if key in ("order", "meta"):
            continue
        assert key in g.breakdown
        assert "value" in g.breakdown[key] and "grade" in g.breakdown[key]
    # titel/färg kommer från rulesettets meta
    assert g.title == NORDIC_ABCD["meta"][g.cls][0]
    assert g.color == NORDIC_ABCD["meta"][g.cls][1]


def test_tuple_warp_backward_compatible():
    # gammalt anrop med (bow, cup, twist)-tuple ska fortfarande funka
    g = grade_board([], (0.2, 0.1, 0.1))
    assert g.cls == "A"


def test_grade_ordering_monotone():
    # högre defektnivå får aldrig BÄTTRE grad
    order = ["A", "B", "C", "D", "V"]
    last = -1
    for r in (5.0, 10.0, 20.0, 30.0, 40.0):
        g = grade_board([{"type": "knot", "r": r}], {})
        idx = order.index(g.cls)
        assert idx >= last, f"r={r} gav {g.cls} efter index {last}"
        last = idx


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
