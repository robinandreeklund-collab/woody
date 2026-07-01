"""Slumpad 3D-brädgeometri: de verkliga virkesdeformationerna.

Producerar en höjdavvikelse z(längd, bredd) i mm relativt ett plant referensplan –
det som linjelasern (src/laser.py) sedan läser via triangulering. Texturen
(Kodytek eller syntetisk) drapereras ovanpå denna geometri i 3D.

Deformationstyper (svenska virkestermer):
  bow    – planböj: båge längs längden i tjockleksled
  spring – kantkrok: båge längs längden i sidled (lateral, påverkar ej höjd)
  twist  – vridning: tvärsnittet vrids längs längden
  cup    – skålning: båge tvärs bredden
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class WarpParams:
    bow_mm: float = 0.0       # planböj, max i mitten
    spring_mm: float = 0.0    # kantkrok (lateral)
    twist_deg: float = 0.0    # total vridning ände till ände
    cup_mm: float = 0.0       # skålning tvärs bredden


def random_warp(rng: np.random.Generator, defect_prob: float = 0.3) -> WarpParams:
    """Slumpar realistiska deformationer (mestadels milda, ibland kraftiga).
    Magnituderna är i mm – synliga i datan/höjdkartan, men små mot 5,4 m
    (därför överdrivs de i 3D-vyn för synlighet, se scene.js)."""
    scale = 3.0 if rng.random() < defect_prob else 1.0   # ibland en "skräpbräda"
    return WarpParams(
        bow_mm=float(abs(rng.normal(0, 6.0)) * scale),
        spring_mm=float(abs(rng.normal(0, 5.0)) * scale),
        twist_deg=float(rng.normal(0, 3.0) * scale),
        cup_mm=float(rng.normal(0, 1.2) * scale),
    )


def warp_height(H: int, W: int, board_width_mm: float, p: WarpParams) -> np.ndarray:
    """z-avvikelse (H,W) i mm. H = längd (rader), W = bredd (kolumner)."""
    u = np.linspace(0.0, 1.0, H)[:, None]      # längdposition 0..1
    v = np.linspace(0.0, 1.0, W)[None, :]      # breddposition 0..1
    z = np.zeros((H, W), np.float64)
    # planböj: parabel, 0 vid ändarna, max i mitten
    z = z + p.bow_mm * (1.0 - (2 * u - 1.0) ** 2)
    # skålning: båge tvärs bredden (nollmedel)
    z = z + p.cup_mm * ((2 * v - 1.0) ** 2 - 1.0 / 3.0)
    # vridning: tvärsnittet roteras linjärt längs längden
    theta = np.radians(p.twist_deg) * (u - 0.5)            # per rad
    z = z + (board_width_mm * (v - 0.5)) * np.sin(theta)
    return z


def lateral_offset(H: int, p: WarpParams) -> np.ndarray:
    """Lateral förskjutning per längdrad (mm) från kantkrok – för 3D-meshen."""
    u = np.linspace(0.0, 1.0, H)
    return p.spring_mm * (1.0 - (2 * u - 1.0) ** 2)


def warp_summary(p: WarpParams) -> str:
    return (f"böj {p.bow_mm:.1f} mm · krok {p.spring_mm:.1f} mm · "
            f"vrid {p.twist_deg:.1f}° · skål {p.cup_mm:.1f} mm")
