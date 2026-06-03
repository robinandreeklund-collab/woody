"""Visuell hållfasthetssortering av konstruktionsvirke enligt SS 230120.

Sorteringsklasser T0–T3 -> hållfasthetsklasser C14/C18/C24/C30 (EN 338).
Klassen sätts av den STRÄNGASTE (begränsande) egenskapen. Blånad ingår inte –
den påverkar inte hållfastheten. Maskinklass C35 (SS-EN 14081-1) kräver täthets-/
E-modulmätning och ingår inte här.

Se docs/strength-grading.md. Exakta tabellvärden bör verifieras mot SS 230120.
"""
from __future__ import annotations

from dataclasses import dataclass

T_TO_C = {3: "C30", 2: "C24", 1: "C18", 0: "C14", -1: "Vrak"}

# Enstaka kvist: tillåten andel av BREDDEN per T-klass (T3 strängast)
KNOT_W_RATIO = {3: 1 / 6, 2: 1 / 4, 1: 2 / 5, 0: 1 / 2}
# Deformationer (mm per 2 m mätsträcka)
BOW_MM_2M = {3: 10, 2: 10, 1: 20, 0: 20}      # planböj/flatböj
SPRING_MM_2M = {3: 8, 2: 8, 1: 12, 0: 12}     # kantkrok
TWIST_MM_PER_25MM = 2.0                        # skevhet, alla klasser
WANE_MAX_FRAC = 1 / 3                           # vankant, alla klasser
CRACK_MAX_M = {3: 0.3, 2: 0.5, 1: 1.0, 0: 2.0}  # spricklängd (C24 ≈ 0,5 m)


def _highest_class(value: float, limits: dict) -> int:
    """Högsta T-klass (3..0) vars gräns value klarar; -1 = under T0 (vrak)."""
    for t in (3, 2, 1, 0):
        if value <= limits[t]:
            return t
    return -1


@dataclass
class GradeInput:
    knot_w_ratio: float = 0.0      # största enstaka kvist / brädbredd
    bow_mm_2m: float = 0.0         # planböj per 2 m
    spring_mm_2m: float = 0.0      # kantkrok per 2 m
    twist_mm: float = 0.0          # skevhet (hörnlyft) över referenslängden
    width_mm: float = 150.0        # brädbredd (för skevhetsgränsen)
    wane_frac: float = 0.0         # vankant som andel av sidan
    crack_len_m: float = 0.0       # längsta spricka
    rot_present: bool = False      # röta finns
    rot_in_knot_only: bool = True  # rötan sitter bara i kvist


def grade_board(g: GradeInput) -> dict:
    """Returnerar {tclass, cclass, limiting, perCriterion}."""
    twist_limit = TWIST_MM_PER_25MM * g.width_mm / 25.0
    crit = {
        "kvist": _highest_class(g.knot_w_ratio, KNOT_W_RATIO),
        "planböj": _highest_class(g.bow_mm_2m, BOW_MM_2M),
        "kantkrok": _highest_class(g.spring_mm_2m, SPRING_MM_2M),
        "skevhet": 3 if g.twist_mm <= twist_limit else -1,
        "vankant": 3 if g.wane_frac <= WANE_MAX_FRAC else -1,
        "spricka": _highest_class(g.crack_len_m, CRACK_MAX_M),
    }
    # röta: fast röta endast i kvist för C24+ -> annars max C14; lös/utbredd -> vrak
    if g.rot_present:
        crit["röta"] = 0 if g.rot_in_knot_only is False else 2
        if not g.rot_in_knot_only:
            crit["röta"] = 0          # utanför kvist -> högst C14
    else:
        crit["röta"] = 3

    t = min(crit.values())
    limiting = min(crit, key=lambda k: crit[k])
    return {"tclass": f"T{t}" if t >= 0 else "—", "cclass": T_TO_C[t],
            "limiting": limiting, "perCriterion": {k: T_TO_C[v] for k, v in crit.items()}}
