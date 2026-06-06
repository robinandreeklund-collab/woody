"""Gradering — defektlista + skevhet → kvalitetsklass.

M0 har ett enkelt regelverk (poäng). Byts mot riktigt sorteringsregelverk senare.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..hal.sim.board_gen import DEFECT_INFO


@dataclass
class Grade:
    cls: str          # "A" | "B" | "C" | "V"
    title: str
    color: str        # hex för GUI
    score: int
    reasons: list


def grade_board(defects: list, warp: tuple) -> Grade:
    score = 100.0
    counts: dict[str, int] = {}
    for d in defects:
        counts[d["type"]] = counts.get(d["type"], 0) + 1
        t = d["type"]
        if t == "knot":
            score -= min(14, 3 + d.get("r", 4))
        elif t == "wane":
            score -= 12
        elif t == "crack":
            score -= 10 + d.get("len", 0) * 0.05
        elif t == "stain":
            score -= 6
        elif t == "rot":
            score -= 22
        elif t == "hole":
            score -= 14

    reasons = []
    warp_sum = sum(abs(x) for x in warp)
    if warp_sum > 4:
        score -= (warp_sum - 4) * 4
        reasons.append(f"skevhet {warp_sum:.1f} mm")
    for k, n in counts.items():
        reasons.append(f"{n}× {DEFECT_INFO[k][0].lower()}")

    if score >= 85:
        cls, title, color = "A", "Klass A · A-virke", "#34e6b5"
    elif score >= 68:
        cls, title, color = "B", "Klass B · konstruktion", "#27d3e0"
    elif score >= 48:
        cls, title, color = "C", "Klass C · emballage", "#ffb33d"
    else:
        cls, title, color = "V", "Vrak · kasseras", "#ff4d5e"

    reasons.append(f"poäng {max(0, round(score))}/100")
    return Grade(cls, title, color, max(0, round(score)), reasons)
