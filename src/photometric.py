"""Fotometrisk stereo: riktade LED för relief och sprickor.

Flera bilder tas, en per ljusriktning. Ytans skuggning beror på vinkeln mellan
ljuset och ytnormalen, så grunda reliefdefekter (sprickor, intryck, vankantkant)
som är osynliga i platt färg framträder tydligt. Ur bildserien återskapas
ytnormaler och albedo (klassisk minstakvadrat-lösning).

Bygger på höjdkartan i board["height"] (mm över banan).
"""
from __future__ import annotations

import numpy as np

from .config import SensorRig


def surface_normals(height_mm: np.ndarray, mm_per_px: float) -> np.ndarray:
    """Ytnormaler (H,W,3) i (rad, kolumn, z)-basen ur höjdkartan."""
    # gradient i mm höjd per mm yta -> lutning
    gz_r, gz_c = np.gradient(height_mm.astype(np.float64), mm_per_px)
    n = np.stack([-gz_r, -gz_c, np.ones_like(height_mm, dtype=np.float64)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    return n


def light_directions(n_lights: int, elevation_deg: float = 30.0,
                     start_deg: float = 0.0) -> np.ndarray:
    """Enhetsvektorer mot ljuskällorna (K,3), jämnt fördelade i azimut."""
    el = np.radians(elevation_deg)
    az = np.radians(start_deg + 360.0 * np.arange(n_lights) / n_lights)
    L = np.stack([np.cos(az) * np.cos(el),
                  np.sin(az) * np.cos(el),
                  np.full(n_lights, np.sin(el))], axis=-1)
    return L / (np.linalg.norm(L, axis=-1, keepdims=True) + 1e-12)


def capture(board: dict, rig: SensorRig | None = None):
    """Tar bildserien. Returnerar (images (K,H,W), L (K,3), normals, albedo)."""
    rig = rig or SensorRig()
    h = board["height"]
    mm = board["mm_per_px"]
    normals = surface_normals(h, mm)
    albedo = board["color"].astype(np.float64).mean(-1) / 255.0  # gråskalealbedo
    L = light_directions(rig.ps_n_lights, rig.ps_elevation_deg, rig.ps_start_deg)
    ndotl = np.clip(normals @ L.T, 0.0, None)          # (H,W,K)
    images = (albedo[..., None] * ndotl).transpose(2, 0, 1)  # (K,H,W)
    return images, L, normals, albedo


def solve(images: np.ndarray, L: np.ndarray):
    """Återskapa normaler + albedo ur bildserien (minstakvadrat per pixel)."""
    K, H, W = images.shape
    g = np.linalg.lstsq(L, images.reshape(K, -1), rcond=None)[0]  # (3,HW)
    g = g.reshape(3, H, W).transpose(1, 2, 0)
    rho = np.linalg.norm(g, axis=-1)
    normals = g / (rho[..., None] + 1e-8)
    return normals, rho


def relief_map(normals: np.ndarray) -> np.ndarray:
    """Lutning i planet (sqrt(nr^2+nc^2)) – lyser upp sprickor och kanter."""
    return np.sqrt(normals[..., 0] ** 2 + normals[..., 1] ** 2)


def normals_to_rgb(normals: np.ndarray) -> np.ndarray:
    """Visualisera normaler som RGB i [0,1] (standard normal-map-färgning)."""
    return (normals * 0.5 + 0.5).clip(0, 1)
