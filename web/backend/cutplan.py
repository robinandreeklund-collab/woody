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
