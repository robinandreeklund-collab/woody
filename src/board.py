"""Genererar en syntetisk bräda: procedurell träyta + defekter.

Returnerar lager som motsvarar de fysiska kanalerna i riggen:
  - color       : HxWx3 uint8   (färgkamera -> kvist, blånad, märg)
  - label       : HxW   uint8   (facit/ground truth, klass-id enligt config.CLASSES)
  - height      : HxW   float   (laserprofil -> mått, vankant; mm över banan)
  - fiber_angle : HxW   float32 (fiberriktning för tracheid; vinkel mot längdaxeln)
  - knots       : lista (r, c, radie_px, dead) – kvistarnas lägen

color/height/fiber_angle matar i sin tur de kompletterande sensorkanalerna:
fotometrisk stereo (photometric.py), tracheid (tracheid.py) och undersidan
(underside.py).

Axlar: axel 0 = längs brädans LÄNGD (raderna), axel 1 = tvärs BREDDEN (kolumnerna).
Kolumnaxeln är samma som matningsriktningen i sidled -> blir skanningsaxeln.
"""
import numpy as np


def _box_blur(a: np.ndarray, k: int) -> np.ndarray:
    """Enkel separabel box-blur utan externa beroenden."""
    if k <= 1:
        return a
    ker = np.ones(k) / k
    out = a.astype(float)
    out = np.apply_along_axis(lambda m: np.convolve(m, ker, mode="same"), 0, out)
    out = np.apply_along_axis(lambda m: np.convolve(m, ker, mode="same"), 1, out)
    return out


def _ellipse_mask(H, W, r0, c0, ra, rc):
    rr, cc = np.ogrid[:H, :W]
    return ((rr - r0) / ra) ** 2 + ((cc - c0) / rc) ** 2 <= 1.0


def make_board(length_mm=1200.0, width_mm=125.0, thickness_mm=22.0,
               mm_per_px=0.5, seed=0):
    rng = np.random.default_rng(seed)
    H = int(round(length_mm / mm_per_px))
    W = int(round(width_mm / mm_per_px))

    clear = np.array([200, 170, 120], float)
    grain_dark = np.array([150, 110, 70], float)

    # --- Grundton med ådring som löper längs längden ---
    rr, cc = np.mgrid[0:H, 0:W]
    phase = np.cumsum(rng.normal(0, 0.02, H))          # ådringen vinglar sakta
    lowfreq = _box_blur(rng.normal(0, 1.0, (H, W)), 9)  # mjukt brus
    wl = max(3.0, 6.0 / mm_per_px)                     # ådringens våglängd i px
    grain = 0.5 + 0.5 * np.sin(2 * np.pi * cc / wl + phase[:, None] + 0.6 * lowfreq)
    t = (0.30 * grain + 0.08 * (lowfreq - lowfreq.min()) /
         (np.ptp(lowfreq) + 1e-9))[..., None]
    color = clear * (1 - t) + grain_dark * t
    color += rng.normal(0, 4, (H, W, 3))               # sensorbrus

    label = np.zeros((H, W), np.uint8)
    height = np.full((H, W), thickness_mm, float)

    # --- Kvistar (levande + döda) ---
    knots = []  # (r0, c0, radie_px, dead) – används för fiberriktningen nedan
    n_knots = rng.integers(3, 6)
    for _ in range(n_knots):
        r0 = rng.integers(int(0.05 * H), int(0.95 * H))
        c0 = rng.integers(int(0.2 * W), int(0.8 * W))
        ra = rng.integers(int(8 / mm_per_px), int(20 / mm_per_px))
        rc = int(ra * rng.uniform(0.6, 1.0))
        dead = rng.random() < 0.4
        knots.append((r0, c0, max(ra, rc), dead))
        m = _ellipse_mask(H, W, r0, c0, ra, rc)
        if dead:
            color[m] = np.array([70, 45, 30], float)
            ring = _ellipse_mask(H, W, r0, c0, ra, rc) & ~_ellipse_mask(
                H, W, r0, c0, ra * 0.8, rc * 0.8)
            color[ring] = np.array([35, 25, 20], float)
            label[m] = 2
        else:
            color[m] = np.array([130, 85, 45], float)
            label[m] = 1

    # --- Spricka längs längden (vinglig tunn linje) + fördjupning i höjd ---
    if rng.random() < 0.8:
        c_base = rng.integers(int(0.25 * W), int(0.75 * W))
        amp = rng.uniform(2, 8) / mm_per_px
        freq = rng.uniform(2, 5) / H
        r = np.arange(H)
        c_center = c_base + amp * np.sin(2 * np.pi * freq * r * 50) + \
            np.cumsum(rng.normal(0, 0.2, H))
        half = max(1, int(0.6 / mm_per_px))
        for ri in range(H):
            lo = int(np.clip(c_center[ri] - half, 0, W - 1))
            hi = int(np.clip(c_center[ri] + half, 0, W - 1)) + 1
            color[ri, lo:hi] = np.array([40, 30, 25], float)
            label[ri, lo:hi] = 3
            height[ri, lo:hi] -= 4.0  # sprickan ger en grop laserprofilen ser

    # --- Blånad (mjuk blågrå blotch, ådringen skiner igenom) ---
    if rng.random() < 0.7:
        r0 = rng.integers(int(0.1 * H), int(0.9 * H))
        c0 = rng.integers(int(0.2 * W), int(0.8 * W))
        ra = rng.integers(int(40 / mm_per_px), int(90 / mm_per_px))
        rc = rng.integers(int(15 / mm_per_px), int(40 / mm_per_px))
        m = _ellipse_mask(H, W, r0, c0, ra, rc).astype(float)
        m = _box_blur(m, 11)
        blue = np.array([120, 130, 145], float)
        a = (0.55 * m)[..., None]
        color = color * (1 - a) + blue * a
        label[m > 0.4] = np.where(label[m > 0.4] == 0, 4, label[m > 0.4])

    # --- Vankant längs ena långsidan (saknat material -> höjd faller mot 0) ---
    if rng.random() < 0.6:
        prof = (rng.uniform(4, 14) / mm_per_px) * (
            0.6 + 0.4 * np.sin(np.linspace(0, np.pi * rng.uniform(1, 3), H)))
        bark = np.array([110, 90, 70], float)
        for ri in range(H):
            wpx = int(prof[ri])
            if wpx <= 0:
                continue
            color[ri, :wpx] = bark
            label[ri, :wpx] = 5
            height[ri, :wpx] = np.linspace(0, thickness_mm, wpx)  # ramp upp inåt

    # --- Märg/pith (mörk strimma längs längden + småchecks) ---
    if rng.random() < 0.4:
        c0 = rng.integers(int(0.4 * W), int(0.6 * W))
        half = max(1, int(1.2 / mm_per_px))
        color[:, c0 - half:c0 + half] = np.array([90, 60, 40], float)
        label[:, c0 - half:c0 + half] = 6

    # --- Fiberriktning (grund för tracheid-effekten) ---
    # Ådringen löper längs längden (axel 0) men böjer av kring kvistar som
    # strömlinjer kring ett hinder. fiber_angle = vinkel mot längdaxeln (rad);
    # 0 = perfekt längs längden, |vinkel| stor nära kvist = störd fiber.
    fiber_angle = 0.05 * np.sin(2 * np.pi * rr / max(40.0, H / 5.0))  # mild vingling
    for (kr, kc, kR, _dead) in knots:
        dr = rr - kr
        dc = cc - kc
        falloff = (kR * kR) / (dr * dr + dc * dc + kR * kR)   # 1 vid centrum -> 0 (1/r^2)
        swirl = np.arctan2(dc, dr)                            # radiell vinkel
        fiber_angle += np.radians(40.0) * falloff * np.sin(swirl)
    fiber_angle = fiber_angle.astype(np.float32)

    color = np.clip(color, 0, 255).astype(np.uint8)
    return {"color": color, "label": label, "height": height,
            "fiber_angle": fiber_angle, "knots": knots,
            "mm_per_px": mm_per_px}
