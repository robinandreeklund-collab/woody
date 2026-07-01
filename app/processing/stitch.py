"""Sy ihop flera läshuvudens sektioner till en HEL bräda (delad encoder-koordinat).

Varje huvud mäter sin del av brädan [start_mm, end_mm]. Eftersom alla huvuden delar
samma encoder/matning ligger deras data i samma koordinatsystem → vi kan resampla in
varje sektion på ett gemensamt rutnät och medla överlapp. Demo-riggen har ETT huvud
över hela 500 mm-brädan → stitch returnerar då bara dess profil (no-op-fall).

``sections`` = lista av {start_mm, end_mm, values}. ``values`` = höjd/tjocklek-array
samplad jämnt över sektionens [start_mm, end_mm].
"""
from __future__ import annotations

import numpy as np


def stitch_sections(sections, n_out: int | None = None,
                    total_start: float | None = None, total_end: float | None = None):
    """Resampla + medla alla sektioner till en array över hela brädan. NaN där ingen
    sektion täcker. Returnerar None om inga giltiga sektioner finns."""
    secs = [s for s in sections
            if s.get("values") is not None and float(s["end_mm"]) > float(s["start_mm"])
            and len(s["values"]) >= 1]
    if not secs:
        return None
    ts = min(float(s["start_mm"]) for s in secs) if total_start is None else float(total_start)
    te = max(float(s["end_mm"]) for s in secs) if total_end is None else float(total_end)
    if te <= ts:
        return None
    if n_out is None:
        # upplösning ur tätaste sektionen, skalat till hela längden
        dens = max(len(s["values"]) / (float(s["end_mm"]) - float(s["start_mm"])) for s in secs)
        n_out = max(2, int(round(dens * (te - ts))))
    x = np.linspace(ts, te, n_out)
    acc = np.zeros(n_out)
    cnt = np.zeros(n_out)
    for s in secs:
        v = np.asarray(s["values"], dtype=np.float64)
        a, b = float(s["start_mm"]), float(s["end_mm"])
        sx = np.linspace(a, b, len(v)) if len(v) > 1 else np.array([0.5 * (a + b)])
        m = (x >= a) & (x <= b)
        if not m.any():
            continue
        acc[m] += np.interp(x[m], sx, v) if len(v) > 1 else v[0]
        cnt[m] += 1.0
    out = np.where(cnt > 0, acc / np.maximum(cnt, 1.0), np.nan)
    return out
