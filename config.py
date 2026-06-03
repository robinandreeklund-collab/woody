"""Simulerar förvärvet i den tvärmatade riggen.

1) Line-scan: brädan glider i sidled förbi en fast skanningslinje. Varje
   "rad" som kameran läser motsvarar en kolumn i brädbilden (axel 1).
   - encoder-trigger: en kolumn per fast STRÄCKA -> måttriktig bild
   - tids-trigger  : en rad per fast TID, men hastigheten vinglar ->
                     geometrisk distorsion (det här är varför man triggar
                     på pulsgivare och inte på klocka)

2) Laserprofil: höjdkartan ger per kolumn en profil tvärs längden -> mått
   och vankant.
"""
import numpy as np


def jittery_velocity(n, v_mean, jitter=0.18, seed=1):
    """Hastighetsprofil med långsam vingling + brus, normaliserad till v_mean."""
    rng = np.random.default_rng(seed)
    slow = np.sin(np.linspace(0, np.pi * 3, n))
    noise = np.cumsum(rng.normal(0, 0.05, n))
    v = 1.0 + jitter * slow + 0.4 * jitter * (noise - noise.mean())
    v = np.clip(v, 0.4, None)
    return v_mean * v / v.mean()


def acquire_timetrigger(board, v_mean_mps, dt_s, seed=1):
    """Tids-triggad insamling med hastighetsjitter -> distorderad bild."""
    color = board["color"]
    H, W = color.shape[:2]
    mm_per_px = board["mm_per_px"]
    width_mm = W * mm_per_px

    # grovt antal rader för att täcka brädbredden i snitt
    n = int(round(width_mm / 1000.0 / (v_mean_mps * dt_s)))
    n = max(n, 8)
    v = jittery_velocity(n, v_mean_mps, seed=seed)
    x_mm = np.cumsum(v * dt_s) * 1000.0            # tillryggalagd sträcka
    x_mm = x_mm / x_mm[-1] * width_mm              # skala till brädbredden
    src_col = np.clip((x_mm / mm_per_px).astype(int), 0, W - 1)

    # raderna placeras likformigt i utbilden -> distorsion mot facit
    recon = color[:, src_col, :]
    # resampla tillbaka till W kolumner för rättvis jämförelse i figur
    idx = np.linspace(0, n - 1, W).astype(int)
    return recon[:, idx, :]


def acquire_encoder(board):
    """Encoder-triggad insamling: en kolumn per fast sträcka -> identisk."""
    return board["color"].copy()


def laser_profile(board):
    """Geometri ur höjdkartan: tjocklek och vankantbredd per längdposition."""
    h = board["height"]
    mm_per_px = board["mm_per_px"]
    H = h.shape[0]
    thickness = np.median(h[h > h.max() * 0.5])

    wane_px = np.zeros(H)
    thr = h.max() * 0.5
    for ri in range(H):
        row = h[ri]
        low = row < thr
        # räkna sammanhängande låga pixlar från vänsterkanten = vankant
        c = 0
        while c < len(row) and low[c]:
            c += 1
        wane_px[ri] = c
    wane_mm = wane_px * mm_per_px
    return {"thickness_mm": float(thickness),
            "wane_mm": wane_mm,
            "wane_max_mm": float(wane_mm.max()),
            "length_mm": H * mm_per_px}
