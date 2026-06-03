"""Räknar och skriver ut förvärvsparametrar för olika konfigurationer."""
from dataclasses import replace
from .config import LineConfig


def acquisition_table(base: LineConfig):
    rows = []
    for length_m, label in [(1.2, "Prototyp (sektion)"), (5.4, "Full längd")]:
        for mmpx in (0.66, 0.33, 0.16):
            cfg = replace(base, board_length_m=length_m, target_mm_per_px=mmpx)
            rows.append({
                "scenario": label,
                "length_m": length_m,
                "mm_per_px": mmpx,
                "pixels_across": cfg.pixels_across_length,
                "line_rate_hz": round(cfg.line_rate_hz),
                "data_rate_mb_s": round(cfg.data_rate_mb_s, 1),
                "sideways_mps": round(cfg.sideways_speed_mps, 3),
            })
    return rows


def print_table(base: LineConfig):
    print(f"Sidledshastighet genom zonen: {base.sideways_speed_mps:.3f} m/s "
          f"({base.boards_per_min} brädor/min, {base.board_spacing_m} m delning)\n")
    hdr = f"{'Scenario':<20}{'Längd':>7}{'mm/px':>8}{'px tvärs':>11}{'rad/s':>9}{'MB/s':>9}"
    print(hdr)
    print("-" * len(hdr))
    for r in acquisition_table(base):
        print(f"{r['scenario']:<20}{r['length_m']:>6}m{r['mm_per_px']:>8}"
              f"{r['pixels_across']:>11}{r['line_rate_hz']:>9}{r['data_rate_mb_s']:>9}")
