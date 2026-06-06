"""Simulerad brädgenerering (numpy).

Skapar EN bräda per styck: en RGB-yttextur (trä + defekter) och en höjdkarta
(tjockleksavvikelse i mm) plus en defektlista. Allt i RÄTT proportion — bufferten
är ``len_mm × width_mm`` skalad med ``PX_PER_MM`` så längd:bredd alltid stämmer.

Detta är simuleringens "fysik" och byts mot riktiga kameraramar i real-HAL.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ...geometry import RIG

PX_PER_MM = 2.0          # bufferupplösning (1000×150 för 500×75 mm)


# trä-/defektfärger (RGB 0–255)
DEFECT_INFO = {
    "knot":  ("Kvist",   (180, 120, 50)),
    "wane":  ("Vankant", (122, 82, 48)),
    "crack": ("Spricka", (40, 30, 28)),
    "stain": ("Blånad",  (74, 120, 170)),
    "rot":   ("Röta",    (107, 122, 58)),
    "hole":  ("Hål",     (30, 24, 18)),
}


@dataclass
class Board:
    seed: int
    w: int                                   # buffertbredd (px) = längs X (längd)
    h: int                                   # buffertHöjd (px) = längs Y (bredd)
    surface: np.ndarray                      # (h, w, 3) uint8
    zmap: np.ndarray                         # (h, w) float32 — tjockleksavvikelse [mm]
    defects: list = field(default_factory=list)
    warp: tuple = (0.0, 0.0, 0.0)            # (bow, cup, twist) mm

    def thickness_at(self, x_mm: float, y_mm: float) -> float:
        xx = int(np.clip(x_mm * PX_PER_MM, 0, self.w - 1))
        yy = int(np.clip(y_mm * PX_PER_MM, 0, self.h - 1))
        return float(RIG.board_thick_mm + self.zmap[yy, xx])

    def z_profile_row(self, y_mm: float, n: int = 200) -> np.ndarray:
        """Tjocklek längs X vid given matningsposition y (mm) — n samplingar."""
        yy = int(np.clip(y_mm * PX_PER_MM, 0, self.h - 1))
        xs = np.linspace(0, self.w - 1, n).astype(int)
        return RIG.board_thick_mm + self.zmap[yy, xs]


def _hsl_to_rgb(h, s, l):
    """h∈[0,1], s,l∈[0,1] → (r,g,b) 0–255 ints."""
    def f(n):
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))
    return tuple(int(round(255 * x)) for x in (f(0), f(8), f(4)))


def make_board(seed: int) -> Board:
    rng = np.random.default_rng(seed)
    BL, BW, BT = RIG.board_len_mm, RIG.board_width_mm, RIG.board_thick_mm
    w, h = int(BL * PX_PER_MM), int(BW * PX_PER_MM)
    yy, xx = np.mgrid[0:h, 0:w]
    fx, fy = xx / w, yy / h

    # --- grundton trä + längsgående gradient ---
    base_h = (28 + rng.uniform(0, 10)) / 360.0
    base_l = (0.58 + rng.uniform(0, 0.10))
    top = np.array(_hsl_to_rgb(base_h, 0.42, base_l), float)
    bot = np.array(_hsl_to_rgb(base_h - 0.011, 0.40, base_l - 0.08), float)
    surf = (top[None, None, :] * (1 - fy[..., None]) + bot[None, None, :] * fy[..., None])

    # --- ådring (böljande längsgående linjer, mörkare) ---
    grain = np.zeros((h, w), float)
    for _ in range(46):
        y0 = rng.uniform(0, h)
        amp = rng.uniform(2, 9) * PX_PER_MM
        frq = rng.uniform(0.004, 0.014) / PX_PER_MM
        phase = rng.uniform(0, 7)
        line_y = y0 + np.sin(xx * frq + phase) * amp
        grain += np.exp(-((yy - line_y) ** 2) / (2 * (1.4 * PX_PER_MM) ** 2)) * rng.uniform(0.12, 0.30)
    surf *= (1 - 0.5 * np.clip(grain, 0, 1))[..., None]

    # --- höjdkarta: global skevhet + mikro-sträv ---
    bow = float(rng.uniform(-1.5, 1.5))
    cup = float(rng.uniform(-1.2, 1.2))
    twist = float(rng.uniform(-1.3, 1.3))
    z = (bow * np.sin(np.pi * fx)
         + cup * (np.cos(np.pi * (fy - 0.5)) - 0.6)
         + twist * (fx - 0.5) * (fy - 0.5) * 2.0
         + np.sin(fx * 70 + fy * 9) * 0.18).astype(np.float32)

    defects = []

    def stamp_ellipse(cx, cy, rx, ry, color, alpha, zdip=0.0):
        m = (((xx - cx * PX_PER_MM) / (rx * PX_PER_MM)) ** 2
             + ((yy - cy * PX_PER_MM) / (ry * PX_PER_MM)) ** 2)
        inside = m <= 1.0
        a = np.clip(1.0 - m, 0, 1) * alpha
        for c in range(3):
            surf[..., c] = np.where(inside, surf[..., c] * (1 - a) + color[c] * a, surf[..., c])
        if zdip:
            z[inside] -= (np.clip(1.0 - m, 0, 1) * zdip)[inside]

    # kvistar
    for _ in range(int(rng.integers(0, 5))):
        cx, cy = rng.uniform(40, BL - 40), rng.uniform(10, BW - 10)
        r = rng.uniform(4, 13)
        stamp_ellipse(cx, cy, r, r * 0.8, DEFECT_INFO["knot"][1], 0.85, zdip=0.8)
        defects.append({"type": "knot", "x": cx, "y": cy, "r": r})

    # vankant (kant saknas över ett parti → Z faller mot kanten)
    if rng.random() < 0.55:
        side = int(rng.random() < 0.5)
        x0 = rng.uniform(0, BL * 0.5)
        length = rng.uniform(80, 280)
        depth = rng.uniform(4, BT * 0.5)
        x1 = x0 + length
        in_x = (xx / PX_PER_MM >= x0) & (xx / PX_PER_MM <= x1)
        if side:
            edgef = np.clip((yy / PX_PER_MM - (BW - depth)) / depth, 0, 1)
        else:
            edgef = np.clip((depth - yy / PX_PER_MM) / depth, 0, 1)
        mask = in_x & (edgef > 0)
        col = np.array(DEFECT_INFO["wane"][1], float)
        for c in range(3):
            surf[..., c] = np.where(mask, surf[..., c] * (1 - 0.7 * edgef) + col[c] * 0.7 * edgef, surf[..., c])
        z[mask] -= (edgef * depth * 0.9)[mask]
        defects.append({"type": "wane", "x": (x0 + x1) / 2, "y": (BW if side else 0),
                        "r": length / 2, "depth": depth})

    # sprickor (mörka tunna linjer)
    for _ in range(int(rng.integers(0, 3))):
        cx, cy = rng.uniform(30, BL - 30), rng.uniform(8, BW - 8)
        length = rng.uniform(30, 140)
        ang = rng.uniform(-0.25, 0.25)
        t = np.linspace(0, 1, 40)
        px = (cx + np.cos(ang) * length * t) * PX_PER_MM
        py = (cy + np.sin(ang) * length * t) * PX_PER_MM + rng.normal(0, 1, t.size)
        for X, Y in zip(px, py):
            stamp_ellipse(X / PX_PER_MM, Y / PX_PER_MM, 0.8, 0.8, DEFECT_INFO["crack"][1], 0.7)
        defects.append({"type": "crack", "x": cx, "y": cy, "r": length / 2, "len": length})

    # blånad (blåaktiga partier)
    for _ in range(int(rng.integers(0, 3))):
        cx, cy = rng.uniform(0, BL), rng.uniform(0, BW)
        r = rng.uniform(20, 60)
        stamp_ellipse(cx, cy, r, r * 0.7, DEFECT_INFO["stain"][1], 0.45)
        defects.append({"type": "stain", "x": cx, "y": cy, "r": r})

    # röta (sällsynt)
    if rng.random() < 0.25:
        cx, cy = rng.uniform(0, BL), rng.uniform(0, BW)
        r = rng.uniform(25, 60)
        stamp_ellipse(cx, cy, r, r * 0.8, DEFECT_INFO["rot"][1], 0.5)
        defects.append({"type": "rot", "x": cx, "y": cy, "r": r})

    # hål (sällsynt)
    if rng.random() < 0.2:
        cx, cy = rng.uniform(30, BL - 30), rng.uniform(10, BW - 10)
        r = rng.uniform(2, 5)
        stamp_ellipse(cx, cy, r, r, DEFECT_INFO["hole"][1], 0.92, zdip=BT * 0.5)
        defects.append({"type": "hole", "x": cx, "y": cy, "r": r})

    surface = np.clip(surf, 0, 255).astype(np.uint8)
    return Board(seed=seed, w=w, h=h, surface=np.ascontiguousarray(surface),
                 zmap=z, defects=defects, warp=(bow, cup, twist))
