"""Multihuvuds-simulering: N läshuvuden över EN lång bräda + fusion mellan huvuden.

Visar hur det är TÄNKT att skala: i den lilla riggen kör ETT huvud över en 500 mm-
bräda, men konceptet är flera Jetson-läshuvuden som var för sig mäter sin sektion av
en lång bräda (t.ex. 6 huvuden × 900 mm = 5400 mm). Alla huvuden delar SAMMA encoder/
matning → deras data ligger i samma koordinatsystem och kan sys ihop (``stitch``) till
en hel bräda. Överlapp mellan grannhuvuden medlas (fusion) och ett absolut
referensankare (3× LR400) tar bort kvarvarande global offset.

Simuleringen lägger en liten **per-huvud kalibrerings-offset** (bias) + brus på varje
huvuds mätning så att fusionen blir meningsfull att visa:
  rå hopfogning  → steg vid skarvarna (varje huvuds bias syns)
  överlappsmedling → skarvarna blendas (steget halveras)
  ankring (LR400) → global offset bort → matchar sanningen

Ren numpy/Python (ingen Qt) → testbar headless. Återanvänder ``stitch_sections``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..geometry import RIG
from .stitch import stitch_sections


@dataclass
class HeadSpec:
    idx: int
    start_mm: float
    end_mm: float
    bias_mm: float = 0.0          # simulerad kalibrerings-offset (fusion ska reducera)

    @property
    def label(self) -> str:
        return f"H{self.idx + 1}"


@dataclass
class MultiHeadResult:
    total_len_mm: float
    width_mm: float
    heads: list                    # list[HeadSpec]
    board: object                  # board_gen.Board (lång)
    sections: list                 # per huvud: {idx,start_mm,end_mm,bias_mm,zmap,profile}
    x_mm: np.ndarray               # längdaxel (mm) för profilerna
    true_profile: np.ndarray       # sann tjocklek (medel över bredd) [mm]
    naive_profile: np.ndarray      # rå hopfogning (ett huvud/kolumn) → steg vid skarv
    fused_profile: np.ndarray      # överlappsmedlad (stitch)
    anchored_profile: np.ndarray   # + LR400-ankring (global offset bort)
    fused_zmap: np.ndarray         # hela brädans fuserade höjdkarta (bredd × längd)
    seams: list = field(default_factory=list)   # per skarv: {x_mm, rms_mm, heads}
    metrics: dict = field(default_factory=dict)


def build_heads(total_len_mm: float, n_heads: int, overlap_mm: float) -> list[HeadSpec]:
    """Dela brädans längd i ``n_heads`` lika sektioner som ÖVERLAPPAR med ``overlap_mm``
    (halva överlappet åt vardera grannen). Yttersta kanterna klamras till brädan."""
    seg = total_len_mm / n_heads
    heads = []
    for i in range(n_heads):
        a = max(0.0, i * seg - overlap_mm / 2.0)
        b = min(total_len_mm, (i + 1) * seg + overlap_mm / 2.0)
        heads.append(HeadSpec(idx=i, start_mm=a, end_mm=b))
    return heads


def simulate(total_len_mm: float = 5400.0, n_heads: int = 6, overlap_mm: float = 80.0,
             seed: int = 20240614, noise_mm: float = 0.04, bias_span_mm: float = 0.45,
             biases=None, px_per_mm: float | None = None) -> MultiHeadResult:
    """Kör multihuvuds-simuleringen och returnera allt som behövs för att visa
    synk + fusion. Genererar en lång bräda, låter varje huvud mäta sin sektion
    (med per-huvud bias + brus), syr ihop och ankrar."""
    from ..hal.sim.board_gen import make_board

    board = make_board(seed, len_mm=total_len_mm, px_per_mm=px_per_mm)
    H, W = board.zmap.shape                       # (bredd_px, längd_px)
    pm = W / total_len_mm                          # FAKTISK px/mm (kan vara nedsamplad)
    true_thick = RIG.board_thick_mm + board.zmap.astype(np.float64)   # absolut tjocklek

    heads = build_heads(total_len_mm, n_heads, overlap_mm)
    if biases is None:
        rb = np.random.default_rng(seed + 777)
        for hd in heads:
            hd.bias_mm = float(rb.uniform(-bias_span_mm, bias_span_mm))
    else:
        for hd, b in zip(heads, biases):
            hd.bias_mm = float(b)

    rn = np.random.default_rng(seed + 999)
    # --- varje huvud mäter sin kolumn-sektion: sann + bias + brus ---
    sections = []
    for hd in heads:
        c0 = max(0, int(round(hd.start_mm * pm)))
        c1 = min(W, int(round(hd.end_mm * pm)))
        meas = true_thick[:, c0:c1] + hd.bias_mm + rn.normal(0, noise_mm, (H, c1 - c0))
        prof = meas.mean(axis=0)                  # medel över bredd → längdprofil
        sections.append({"idx": hd.idx, "start_mm": hd.start_mm, "end_mm": hd.end_mm,
                         "bias_mm": hd.bias_mm, "c0": c0, "c1": c1,
                         "zmap": meas, "profile": prof})

    x_mm = np.linspace(0, total_len_mm, W)
    true_profile = true_thick.mean(axis=0)

    # --- naiv hopfogning: varje kolumn tar SENASTE huvudet som täcker den (→ steg) ---
    naive = np.full(W, np.nan)
    for s in sections:
        naive[s["c0"]:s["c1"]] = s["profile"]
    naive = _fill_nan(naive)

    # --- steg 1: överlappsmedlad stitch UTAN inter-huvud-kalibrering ---
    #     (skarvarna blendas men varje huvuds bias finns kvar i sin egen sektion)
    sec1d = [{"start_mm": s["start_mm"], "end_mm": s["end_mm"], "values": s["profile"]}
             for s in sections]
    fused = _fill_nan(stitch_sections(sec1d, n_out=W, total_start=0.0,
                                      total_end=total_len_mm))

    # --- steg 2: FUSION — skatta per-huvud-offset ur ÖVERLAPPEN (grannhuvuden ser
    #     samma virke → deras skillnad avslöjar relativ bias) → kedja ihop alla
    #     huvuden till en gemensam ram. Detta är kärnan i hur huvudena synkas. ---
    corr = _align_heads(sections)
    sec_corr = [{"start_mm": s["start_mm"], "end_mm": s["end_mm"],
                 "values": s["profile"] + corr[s["idx"]]} for s in sections]
    aligned = _fill_nan(stitch_sections(sec_corr, n_out=W, total_start=0.0,
                                        total_end=total_len_mm))
    # --- steg 3: ankring (3× LR400 absolut referens) → ta bort global offset ---
    aligned, offset = _anchor(x_mm, aligned, true_profile, total_len_mm)

    # --- fuserad 2D-höjdkarta ur de KALIBRERADE sektionerna (hela brädan) ---
    #     varje huvuds sektion ligger redan på brädans kolumnrutnät [c0:c1] → placera
    #     + medla överlapp vektoriserat (inget per-rad-resampling → millisekunder).
    acc = np.zeros((H, W)); cnt = np.zeros((H, W))
    for s in sections:
        acc[:, s["c0"]:s["c1"]] += s["zmap"] + corr[s["idx"]] - offset
        cnt[:, s["c0"]:s["c1"]] += 1.0
    fused_zmap = np.where(cnt > 0, acc / np.maximum(cnt, 1.0), RIG.board_thick_mm)

    # --- skarv-mått: överlappens samstämmighet FÖRE och EFTER kalibrering ---
    seams = []
    for i in range(len(sections) - 1):
        a, b = sections[i], sections[i + 1]
        lo, hi = b["start_mm"], a["end_mm"]       # överlappszon
        if hi <= lo:
            continue
        xa = np.linspace(a["start_mm"], a["end_mm"], len(a["profile"]))
        xb = np.linspace(b["start_mm"], b["end_mm"], len(b["profile"]))
        grid = np.linspace(lo, hi, 64)
        va = np.interp(grid, xa, a["profile"])
        vb = np.interp(grid, xb, b["profile"])
        da, db = corr[a["idx"]], corr[b["idx"]]
        seams.append({"x_mm": 0.5 * (lo + hi), "lo_mm": lo, "hi_mm": hi,
                      "rms_before_mm": float(np.sqrt(np.mean((va - vb) ** 2))),
                      "rms_after_mm": float(np.sqrt(np.mean(((va + da) - (vb + db)) ** 2))),
                      "heads": (a["idx"], b["idx"])})

    def rms(p):
        return float(np.sqrt(np.nanmean((p - true_profile) ** 2)))

    metrics = {
        "n_heads": n_heads, "total_len_mm": total_len_mm, "overlap_mm": overlap_mm,
        "rms_naive_mm": rms(naive), "rms_fused_mm": rms(fused),
        "rms_aligned_mm": rms(aligned), "anchor_offset_mm": offset,
        "bias_span_mm": float(max(h.bias_mm for h in heads) - min(h.bias_mm for h in heads)),
        "seam_rms_before_mm": float(np.mean([s["rms_before_mm"] for s in seams])) if seams else 0.0,
        "seam_rms_after_mm": float(np.mean([s["rms_after_mm"] for s in seams])) if seams else 0.0,
        "corrections_mm": [corr[h.idx] for h in heads],
    }

    return MultiHeadResult(
        total_len_mm=total_len_mm, width_mm=RIG.board_width_mm, heads=heads, board=board,
        sections=sections, x_mm=x_mm, true_profile=true_profile, naive_profile=naive,
        fused_profile=fused, anchored_profile=aligned, fused_zmap=fused_zmap,
        seams=seams, metrics=metrics)


# ---------------------------------------------------------------- hjälpare
def _fill_nan(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64).copy()
    nan = np.isnan(a)
    if nan.any() and (~nan).any():
        idx = np.arange(len(a))
        a[nan] = np.interp(idx[nan], idx[~nan], a[~nan])
    return a


def _align_heads(sections) -> dict:
    """Skatta per-huvud korrektion-offset ur ÖVERLAPPEN. Grannhuvuden mäter samma
    virke i överlappet → medelskillnaden avslöjar relativ bias. Kedja ihop från
    huvud 0 (gauge fixas sen av ankringen). Returnerar {head_idx: offset_mm}.

    Detta är multihuvuds-kalibreringen: utan absoluta referenser PER huvud kan vi
    ändå tvinga alla huvuden till EN gemensam ram bara via överlappen."""
    corr = {sections[0]["idx"]: 0.0}
    for i in range(len(sections) - 1):
        a, b = sections[i], sections[i + 1]
        lo, hi = b["start_mm"], a["end_mm"]
        if hi <= lo:
            corr[b["idx"]] = corr[a["idx"]]
            continue
        xa = np.linspace(a["start_mm"], a["end_mm"], len(a["profile"]))
        xb = np.linspace(b["start_mm"], b["end_mm"], len(b["profile"]))
        grid = np.linspace(lo, hi, 128)
        # vill: prof_a + o_a = prof_b + o_b  →  o_b = o_a + mean(prof_a - prof_b)
        d = float(np.mean(np.interp(grid, xa, a["profile"]) - np.interp(grid, xb, b["profile"])))
        corr[b["idx"]] = corr[a["idx"]] + d
    return corr


def _anchor(x_mm, fused, true_profile, total_len_mm):
    """Simulera LR400-ankring: 3 absoluta referenspunkter (sann tjocklek) → ta bort
    global offset med minsta kvadrat. Returnerar (ankrad profil, offset_mm)."""
    xs = np.array([0.1, 0.5, 0.9]) * total_len_mm
    idx = np.clip((xs / total_len_mm * (len(fused) - 1)).astype(int), 0, len(fused) - 1)
    offset = float(np.mean(fused[idx] - true_profile[idx]))
    return fused - offset, offset
