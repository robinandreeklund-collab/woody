"""Tester för multihuvuds-simuleringen (N huvuden över en lång bräda + fusion).

Kör utan pytest:  python -m app.tests.test_multihead
"""
from __future__ import annotations

import numpy as np

from ..processing.multihead import build_heads, simulate
from ..processing.stitch import stitch_sections


def test_heads_tile_and_overlap():
    heads = build_heads(5400.0, 6, overlap_mm=80.0)
    assert len(heads) == 6
    assert heads[0].start_mm == 0.0 and heads[-1].end_mm == 5400.0
    # grannhuvuden överlappar (end_i > start_{i+1})
    for a, b in zip(heads, heads[1:]):
        assert a.end_mm > b.start_mm, "huvuden måste överlappa för fusion"


def test_fusion_beats_naive_and_matches_truth():
    res = simulate(total_len_mm=5400.0, n_heads=6, overlap_mm=80.0, seed=20240614)
    m = res.metrics
    # fusion (överlapp-align + ankring) ska vara klart bättre än naiv hopfogning
    assert m["rms_aligned_mm"] < m["rms_naive_mm"] * 0.25
    # och nära sanningen (brusgolvet), klart under 0,05 mm
    assert m["rms_aligned_mm"] < 0.05
    # skarvarna ska bli mycket mer samstämmiga efter fusion
    assert m["seam_rms_after_mm"] < m["seam_rms_before_mm"] * 0.25


def test_corrections_recover_relative_bias():
    # skattad korrektion ska upphäva per-huvud-bias (relativt huvud 1)
    res = simulate(seed=7)
    corr = res.metrics["corrections_mm"]
    b0 = res.heads[0].bias_mm
    for hd, c in zip(res.heads, corr):
        # bias_i + corr_i ≈ bias_0 (alla huvuden i samma ram)
        assert abs((hd.bias_mm + c) - b0) < 0.03


def test_fused_zmap_covers_whole_board():
    res = simulate(total_len_mm=3600.0, n_heads=4, overlap_mm=60.0, seed=3)
    H, W = res.fused_zmap.shape
    assert W == res.board.zmap.shape[1] and H == res.board.zmap.shape[0]
    assert np.isfinite(res.fused_zmap).all(), "ingen lucka i den fuserade brädan"


def test_stitch_noop_single_head():
    # ETT huvud över hela brädan → stitch returnerar dess egen profil (lilla riggen)
    v = np.linspace(20, 22, 50)
    out = stitch_sections([{"start_mm": 0.0, "end_mm": 500.0, "values": v}], n_out=50)
    assert out is not None and np.allclose(out[0], 20, atol=0.1) and np.allclose(out[-1], 22, atol=0.1)


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
