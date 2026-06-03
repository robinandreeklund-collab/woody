"""Kapoptimering: avgör var varje bräda ska kapas för maximalt värde.

Efter segmenteringen har vi en kvalitetsprofil längs brädan (klass per pixel).
Optimeraren delar brädan i färdiga längder ur en tillåten uppsättning
(CutConfig.allowed_lengths_m) och får kapa bort defektzoner som spill. Varje bit
klassas (A/B/C/vrak) ur defekterna inom den, klassen × längden ger ett pris, och
en dynamisk programmering hittar den kapplan som maximerar totalvärdet.

Fysiskt motsvarar varje kapposition att knuffarna skjuter brädan i sidled så att
positionen ställs i linje med den fasta kapbalken.
"""
from __future__ import annotations

import math

import numpy as np

from .config import (CutConfig, SEVERE_DEFECTS, MODERATE_DEFECTS, WANE_DEFECT)

GRADE_COLORS = {  # för visualisering (RGB 0-1)
    "A": (0.20, 0.70, 0.25),
    "B": (0.95, 0.82, 0.10),
    "C": (1.00, 0.55, 0.00),
    "reject": (0.72, 0.12, 0.12),
}


def grade_counts(counts: np.ndarray, total_px: int, cfg: CutConfig):
    """Klass + defektpoäng ur pixelantal per klass för en bit."""
    total = max(total_px, 1)
    severe = counts[list(SEVERE_DEFECTS)].sum() / total
    moderate = counts[list(MODERATE_DEFECTS)].sum() / total
    wane = counts[WANE_DEFECT] / total
    score = cfg.w_severe * severe + cfg.w_moderate * moderate + cfg.w_wane * wane
    if severe >= cfg.reject_severe_frac:
        return "reject", score
    if score <= cfg.a_max_score:
        return "A", score
    if score <= cfg.b_max_score:
        return "B", score
    if score <= cfg.c_max_score:
        return "C", score
    return "reject", score


def optimize_cuts(label: np.ndarray, mm_per_px: float, cfg: CutConfig | None = None,
                  n_classes: int = 7) -> dict:
    """Returnerar optimal kapplan för en bräda.

    label: HxW klass-id (axel 0 = längd). Returnerar dict med pieces (start/slut i
    mm, längd, klass, värde), total_value, waste_mm och piece-/spillsegment.
    """
    cfg = cfg or CutConfig()
    H, W = label.shape

    # Prefixsummor av pixelantal per klass och rad -> O(1) per intervall
    row_counts = np.zeros((H, n_classes), dtype=np.int64)
    valid = (label >= 0) & (label < n_classes)
    for c in range(n_classes):
        row_counts[:, c] = ((label == c) & valid).sum(1)
    prefix = np.vstack([np.zeros(n_classes, np.int64), np.cumsum(row_counts, 0)])

    step_px = max(1, round(cfg.step_mm / mm_per_px))
    kerf_steps = max(0, math.ceil(cfg.kerf_mm / cfg.step_mm))
    n_pos = H // step_px
    lengths = [(Lm, round(Lm * 1000.0 / cfg.step_mm)) for Lm in cfg.allowed_lengths_m]

    best = np.zeros(n_pos + 1)
    choice: list = [None] * (n_pos + 1)
    for p in range(n_pos - 1, -1, -1):
        best[p] = best[p + 1]          # trimma ett steg (spill)
        choice[p] = ("trim", p + 1)
        r0 = p * step_px
        for Lm, Lsteps in lengths:
            np_ = p + Lsteps
            r1 = r0 + Lsteps * step_px
            if np_ > n_pos or r1 > H:
                continue
            cnt = prefix[r1] - prefix[r0]
            grade, _ = grade_counts(cnt, Lsteps * step_px * W, cfg)
            value = cfg.grade_prices_per_m[grade] * Lm
            nxt = min(np_ + kerf_steps, n_pos)
            cand = value + best[nxt]
            if cand > best[p]:
                best[p] = cand
                choice[p] = ("cut", Lm, r0, r1, grade, value, nxt)

    pieces, p = [], 0
    while p < n_pos:
        ch = choice[p]
        if ch[0] == "trim":
            p = ch[1]
        else:
            _, Lm, r0, r1, grade, value, nxt = ch
            pieces.append({"start_mm": r0 * mm_per_px, "end_mm": r1 * mm_per_px,
                           "length_m": Lm, "grade": grade, "value": value})
            p = nxt

    board_mm = H * mm_per_px
    used_mm = sum(pc["length_m"] * 1000.0 for pc in pieces)
    return {
        "pieces": pieces,
        "total_value": float(best[0]),
        "board_mm": board_mm,
        "used_mm": used_mm,
        "waste_mm": board_mm - used_mm,
        "yield_frac": used_mm / board_mm if board_mm else 0.0,
    }


def greedy_plan(label: np.ndarray, mm_per_px: float,
                cfg: CutConfig | None = None, n_classes: int = 7) -> dict:
    """Naiv referens: ta längsta tillåtna bit som får plats, från ena änden, utan
    att trimma bort defektzoner. Visar värdet av att optimera kappositionerna."""
    cfg = cfg or CutConfig()
    H, W = label.shape
    lengths = sorted((round(Lm * 1000.0 / mm_per_px) for Lm in cfg.allowed_lengths_m),
                     reverse=True)
    len_m = {round(Lm * 1000.0 / mm_per_px): Lm for Lm in cfg.allowed_lengths_m}
    kerf_px = round(cfg.kerf_mm / mm_per_px)
    pieces, r0, total = [], 0, 0.0
    while True:
        placed = next((Lpx for Lpx in lengths if r0 + Lpx <= H), None)
        if placed is None:
            break
        r1 = r0 + placed
        cnt = np.array([((label[r0:r1] == c)).sum() for c in range(n_classes)])
        grade, _ = grade_counts(cnt, placed * W, cfg)
        value = cfg.grade_prices_per_m[grade] * len_m[placed]
        pieces.append({"start_mm": r0 * mm_per_px, "end_mm": r1 * mm_per_px,
                       "length_m": len_m[placed], "grade": grade, "value": value})
        total += value
        r0 = r1 + kerf_px
    return {"pieces": pieces, "total_value": total}


def defect_fraction_per_row(label: np.ndarray, n_classes: int = 7) -> np.ndarray:
    """Andel icke-clear_wood per längdrad (för att visa var defekterna sitter)."""
    return (label != 0).mean(1)


def plot_cut_plan(board: dict, label: np.ndarray, plan: dict, naive: dict,
                  source: str, path) -> None:
    """Ritar kapplanen: brädan med kapsnitt + bitarnas klass/längd/värde, och en
    defektkurva som visar varför kapen ligger där de gör. Lazy matplotlib-import
    så att kärnan i modulen kan användas utan plottberoenden."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    color = board["color"].astype(np.float32) / 255.0
    H, W = label.shape
    mm = board["mm_per_px"]
    board_m = H * mm / 1000.0
    dev = defect_fraction_per_row(label)
    x_m = np.arange(H) * mm / 1000.0

    fig, axes = plt.subplots(2, 1, figsize=(11, 5),
                             gridspec_kw={"height_ratios": [2, 1]})
    axes[0].imshow(np.transpose(color, (1, 0, 2)), aspect="auto",
                   extent=(0, board_m, 0, W))
    for pc in plan["pieces"]:
        x0, x1 = pc["start_mm"] / 1000, pc["end_mm"] / 1000
        axes[0].axvspan(x0, x1, color=GRADE_COLORS[pc["grade"]], alpha=0.32)
        axes[0].axvline(x0, color="k", lw=1.2)
        axes[0].axvline(x1, color="k", lw=1.2)
        axes[0].text((x0 + x1) / 2, W * 0.5,
                     f"{pc['length_m']:.1f} m\nklass {pc['grade']}\n{pc['value']:.0f} kr",
                     ha="center", va="center", fontsize=8, weight="bold")
    axes[0].set_yticks([])
    axes[0].set_xlabel("position längs brädan (m)")
    gain = plan["total_value"] - naive["total_value"]
    axes[0].set_title(f"Kapplan ({source}) – totalt {plan['total_value']:.0f} kr "
                      f"(+{gain:.0f} kr mot naiv längsta-först), "
                      f"utbyte {plan['yield_frac']*100:.0f} %, "
                      f"spill {plan['waste_mm']/1000:.2f} m")

    axes[1].fill_between(x_m, dev, color="#c0392b", alpha=0.5)
    for pc in plan["pieces"]:
        axes[1].axvspan(pc["start_mm"] / 1000, pc["end_mm"] / 1000,
                        color=GRADE_COLORS[pc["grade"]], alpha=0.18)
    axes[1].set_xlim(0, board_m)
    axes[1].set_ylabel("defektandel")
    axes[1].set_xlabel("position längs brädan (m)")
    axes[1].grid(alpha=0.3)

    handles = [Patch(facecolor=GRADE_COLORS[g], edgecolor="0.3", label=f"klass {g}")
               for g in ("A", "B", "C", "reject")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def format_plan(plan: dict) -> str:
    lines = [f"Kapplan: {len(plan['pieces'])} bitar, totalvärde "
             f"{plan['total_value']:.0f} kr, utbyte {plan['yield_frac']*100:.0f} %"]
    for i, pc in enumerate(plan["pieces"], 1):
        lines.append(f"  {i}. {pc['start_mm']/1000:.2f}–{pc['end_mm']/1000:.2f} m  "
                     f"{pc['length_m']:.1f} m  klass {pc['grade']:<6} "
                     f"{pc['value']:.0f} kr")
    if plan["waste_mm"] > 1:
        lines.append(f"  spill: {plan['waste_mm']/1000:.2f} m")
    return "\n".join(lines)
