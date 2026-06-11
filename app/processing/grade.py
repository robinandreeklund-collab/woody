"""Gradering — defektlista + skevhet → utseendeklass A/B/C/D (nordisk standard).

Data-driven regel-motor: gränserna ligger i ``grading_rules.NORDIC_ABCD`` (lätta att
tona mot köpt standard). Princip enligt EN 1611-1 / Nordic Timber: varje defekt/feature
ger den BÄSTA grad den klarar; brädans grad = SÄMSTA featuren ("worst governs"). Klarar
inte ens D → "V" (vrak). Returnerar grad + STYRANDE defekt + per-feature-breakdown.

Se docs/grading-nordic.md för analys; grading_rules.py för talen.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..geometry import RIG
from .grading_rules import NORDIC_ABCD, WARP_REF_MM, FEATURE_LABEL

_ORDER = ["A", "B", "C", "D", "V"]
_IDX = {g: i for i, g in enumerate(_ORDER)}
_SCORE = {"A": 92, "B": 75, "C": 58, "D": 45, "V": 25}


@dataclass
class Grade:
    cls: str                                  # "A" | "B" | "C" | "D" | "V"
    title: str
    color: str
    score: int
    reasons: list
    governing: str = ""                       # featuren som satte graden
    breakdown: dict = field(default_factory=dict)   # feature -> {"value","grade"}


def _warp_dict(warp) -> dict:
    if isinstance(warp, dict):
        return warp
    if warp and len(warp) >= 3:               # tuple (bow, cup, twist)
        return {"bow": warp[0], "cup": warp[1], "twist": warp[2], "crook": 0.0}
    return {}


def _features(defects: list, warp, dims) -> dict:
    """Råa feature-värden (samma enhet som gränserna i rulesettet)."""
    BL, BW, BT = dims
    area = max(1.0, BL * BW)

    knot = 0.0
    wane_t = wane_l = 0.0
    crack = 0.0
    stain_a = rot_a = 0.0
    holes = 0
    for d in defects or []:
        t = d.get("type")
        r = float(d.get("r", 0.0))
        if t == "knot":
            knot = max(knot, (2.0 * r) / BW)
        elif t == "wane":
            wane_t = max(wane_t, float(d.get("depth", 0.0)) / max(1.0, BT))
            wane_l = max(wane_l, (2.0 * r) / max(1.0, BL))      # r = längd/2
        elif t == "crack":
            ln = float(d.get("len", 2.0 * r))
            crack = max(crack, ln / max(1.0, BL))
        elif t == "stain":
            stain_a += math.pi * r * (r * 0.7) / area
        elif t == "rot":
            rot_a += math.pi * r * (r * 0.8) / area
        elif t == "hole":
            holes += 1

    w = _warp_dict(warp)
    s = WARP_REF_MM / max(1.0, BL)             # skala uppmätt skevhet → per 2 m
    bow = abs(float(w.get("bow", 0.0))) * s
    crook = abs(float(w.get("crook", w.get("spring", 0.0)))) * s
    twist = abs(float(w.get("twist", 0.0))) * s
    cup = abs(float(w.get("cup", 0.0))) / max(1.0, BW)

    return {
        "knot_frac_width": knot,
        "wane_frac_thick": wane_t, "wane_frac_len": wane_l,
        "crack_frac_len": crack,
        "stain_frac_area": stain_a, "rot_frac_area": rot_a,
        "hole_count": holes,
        "bow_mm_2m": bow, "spring_mm_2m": crook, "twist_mm_2m": twist,
        "cup_frac_width": cup,
    }


def _best_grade(feature_key: str, value, rules: dict) -> str:
    limits = rules[feature_key]
    for g in rules["order"]:                   # A → D
        if value <= limits[g]:
            return g
    return "V"                                 # över D:s gräns → vrak


def grade_board(defects: list, warp=(0.0, 0.0, 0.0), dims=None, rules: dict | None = None) -> Grade:
    """Gradera en bräda. ``warp`` får vara warp_metrics()-dict eller (bow,cup,twist)."""
    rules = rules or NORDIC_ABCD
    if dims is None:
        dims = (RIG.board_len_mm, RIG.board_width_mm, RIG.board_thick_mm)

    feats = _features(defects, warp, dims)
    breakdown, worst = {}, "A"
    for key, val in feats.items():
        g = _best_grade(key, val, rules)
        breakdown[key] = {"value": round(float(val), 3), "grade": g}
        if _IDX[g] > _IDX[worst]:
            worst = g

    # styrande defekt(er) = de features som hamnade på sämsta graden
    gov = [FEATURE_LABEL.get(k, k) for k, b in breakdown.items()
           if b["grade"] == worst and worst != "A"]
    title, color = rules["meta"][worst]

    reasons = []
    if gov:
        reasons.append("styrande: " + ", ".join(sorted(set(gov))))
    n = len([d for d in (defects or [])])
    if n:
        reasons.append(f"{n} defekt(er)")
    worst_warp = max((breakdown[k]["value"] for k in
                      ("bow_mm_2m", "spring_mm_2m", "twist_mm_2m")), default=0.0)
    if worst_warp >= rules["bow_mm_2m"]["A"]:
        reasons.append(f"skevhet ~{worst_warp:.0f} mm/2m")

    score = max(0, _SCORE[worst] - min(8, n))
    reasons.append(f"klass {worst}")
    return Grade(worst, title, color, score, reasons, governing=", ".join(sorted(set(gov))),
                 breakdown=breakdown)
