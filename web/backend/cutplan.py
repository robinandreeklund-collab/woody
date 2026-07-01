"""Kapoptimering – trogen port av claude_code_woody/js/cutplan.js till Python.

Algoritm och parametrar (SEV/FOOT/GRADE/priser) är identiska med prototypen och
verifieras mot JS-originalet (se tests/test_cutplan_parity). DP:n väljer var
brädan kapas i tillåtna längder för maximalt värde; defekter sänker bitens
kvalitet (A/B/C) eller klipps bort som spill.
"""
from __future__ import annotations

L_M = 5.4
CM = round(L_M * 100)

# klass -> svårighetsgrad (0 frisk .. 3 allvarlig)  [GUI-taxonomi]
SEV = {1: 1, 3: 1, 4: 2, 2: 3, 5: 3, 6: 3}
# klass -> defektens utbredning längs brädan (cm)
FOOT = {1: 9, 2: 32, 3: 38, 4: 75, 5: 42, 6: 7}
# svårighet -> kvalitet
GRADE = ["A", "B", "C", "C"]
PRICE = {"A": 58, "B": 40, "C": 24}      # kr/m
COLOR = {"A": "#4aa86a", "B": "#d6a23e", "C": "#cf6b46"}


def plan(features, lengths=None):
    """features: [{cls, u, ...}] med u = position längs längden 0..1.
    Returnerar {pieces, totalValue, yield, trimM, L, lengths} (samma form som JS)."""
    lens = sorted((lengths or [3.0, 2.7, 2.4]), reverse=True)
    len_cm = [round(l * 100) for l in lens]

    # svårighetsprofil längs brädan
    sev = [0.0] * CM
    for f in features:
        s = SEV.get(f["cls"], 0)
        if not s:
            continue
        c = round(f["u"] * CM)
        r = round(FOOT.get(f["cls"], 10) / 2)
        for i in range(max(0, c - r), min(CM, c + r)):
            if s > sev[i]:
                sev[i] = s

    def grade_of(a, b):
        w = 0
        for i in range(a, b):
            if sev[i] > w:
                w = int(sev[i])
        return GRADE[w]

    # DP: best[i] = max värde av första i cm
    best = [0.0] * (CM + 1)
    choice = [None] * (CM + 1)
    for i in range(1, CM + 1):
        best[i] = best[i - 1]
        choice[i] = {"trim": True}
        for lc in len_cm:
            if i - lc < 0:
                continue
            g = grade_of(i - lc, i)
            v = best[i - lc] + PRICE[g] * (lc / 100)
            if v > best[i] + 1e-9:
                best[i] = v
                choice[i] = {"a": i - lc, "b": i, "g": g}

    # backtrack
    pieces_raw, i = [], CM
    while i > 0:
        c = choice[i]
        if not c:
            break
        if c.get("trim"):
            i -= 1
        else:
            pieces_raw.append(c)
            i = c["a"]
    pieces_raw.reverse()

    used = 0
    pieces = []
    for p in pieces_raw:
        length = (p["b"] - p["a"]) / 100
        used += p["b"] - p["a"]
        pieces.append({
            "aU": p["a"] / CM, "bU": p["b"] / CM, "lenM": length, "grade": p["g"],
            "value": round(PRICE[p["g"]] * length), "color": COLOR[p["g"]],
        })
    return {
        "pieces": pieces,
        "totalValue": round(best[CM]),
        "yield": used / CM,
        "trimM": (CM - used) / 100,
        "L": L_M, "lengths": lens,
    }


# ============================================================
# Hållfasthetssortering driver värdet: varje kapbit klassas C14..C30 (SS 230120)
# och prissätts per C-klass. Defekterna är lokala (per bit), deformationerna
# board-nivå (samma för alla bitar). Se docs/strength-grading.md.
# ============================================================
import math as _math
from src.grading import grade_board, GradeInput

C_PRICE = {"C30": 95.0, "C24": 80.0, "C18": 60.0, "C14": 40.0, "Vrak": 8.0}  # kr/m
C_COLOR = {"C30": "#2f9e6e", "C24": "#5fae6a", "C18": "#d6a23e",
           "C14": "#cf6b46", "Vrak": "#8a8f96"}


def _piece_cclass(features, a_cm, b_cm, deform, width_mm):
    """C-klass för biten [a_cm, b_cm] (cm) ur lokala defekter + board-deformation."""
    aU, bU = a_cm / CM, b_cm / CM
    seg_len_mm = (b_cm - a_cm) / 100.0 * 1000.0
    knot = crack = wane_area = 0.0
    rot = False
    for f in features:
        if f["u"] < aU or f["u"] >= bU:
            continue
        c = f["cls"]
        if c == 1:
            knot = max(knot, 2 * _math.sqrt(f["area"] / _math.pi) / width_mm)
        elif c == 2:
            crack = max(crack, f["area"] / 5.0 / 1000.0)
        elif c == 4:
            wane_area += f["area"]
        elif c == 5:
            rot = True
    g = grade_board(GradeInput(
        knot_w_ratio=knot, width_mm=width_mm,
        wane_frac=(wane_area / seg_len_mm / width_mm) if seg_len_mm else 0.0,
        crack_len_m=crack, rot_present=rot, rot_in_knot_only=False, **deform))
    return g["cclass"]


def plan_by_strength(features, lengths=None, deform=None, width_mm=150.0):
    """DP som maximerar värdet med C-klass-priser per kapbit."""
    deform = deform or {"bow_mm_2m": 0, "spring_mm_2m": 0, "twist_mm": 0}
    lens = sorted((lengths or [3.0, 2.7, 2.4]), reverse=True)
    len_cm = [round(l * 100) for l in lens]

    best = [0.0] * (CM + 1)
    choice = [None] * (CM + 1)
    for i in range(1, CM + 1):
        best[i] = best[i - 1]
        choice[i] = {"trim": True}
        for lc in len_cm:
            if i - lc < 0:
                continue
            cc = _piece_cclass(features, i - lc, i, deform, width_mm)
            v = best[i - lc] + C_PRICE[cc] * (lc / 100.0)
            if v > best[i] + 1e-9:
                best[i] = v
                choice[i] = {"a": i - lc, "b": i, "g": cc}

    pieces, i = [], CM
    while i > 0:
        c = choice[i]
        if not c:
            break
        if c.get("trim"):
            i -= 1
        else:
            pieces.append(c); i = c["a"]
    pieces.reverse()

    used = 0
    out = []
    for p in pieces:
        length = (p["b"] - p["a"]) / 100.0
        used += p["b"] - p["a"]
        out.append({"aU": p["a"] / CM, "bU": p["b"] / CM, "lenM": length,
                    "grade": p["g"], "value": round(C_PRICE[p["g"]] * length),
                    "color": C_COLOR[p["g"]]})
    return {"pieces": out, "totalValue": round(best[CM]), "yield": used / CM,
            "trimM": (CM - used) / 100.0, "L": L_M, "lengths": lens}
