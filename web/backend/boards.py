"""Datakontrakt: gör en bräda ur src.board till det format GUI:t konsumerar,
samt U-Net-segmentering ur src.infer. Ersätter prototypens js/textures.js.

Klasstaxonomi: modellen/board.py använder (clear, live_knot, dead_knot, crack,
blue_stain, wane, marrow). GUI:t/cutplan använder (Frisk, Kvist, Spricka, Blånad,
Vankant, Röta, Hål). MODEL_TO_GUI mappar mellan dem – PROVISORISK tills taxonomin
fastställts (marrow -> Röta; GUI:ts Hål används inte av modellen).
"""
from __future__ import annotations

import base64
import io

import numpy as np
from scipy import ndimage

from src.board import make_board
from src.features import build_features
from src.config import SegConfig
from src.photometric import surface_normals, relief_map
from src.infer import find_checkpoint, load_model, predict_board

# modellklass (0..6) -> GUI-klass (0..6)
MODEL_TO_GUI = {0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}

# nedskalning av texturer (full 10800x250 -> hanterbart för webben)
TEX_LEN = 1400


def _png_b64(rgb: np.ndarray) -> str:
    """HxWx3 uint8 -> data-URL PNG (kräver Pillow)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _downscale_rgb(rgb: np.ndarray, target_len: int = TEX_LEN) -> np.ndarray:
    """Nedskala längs längdaxeln (axel 0) till target_len rader (nearest)."""
    H = rgb.shape[0]
    if H <= target_len:
        return rgb
    idx = np.linspace(0, H - 1, target_len).astype(int)
    return rgb[idx]


def _features_from_label(label: np.ndarray, mm_per_px: float):
    """Defektinstanser ur en klasskarta -> [{cls, u, fv, area}] i GUI-taxonomi.
    u = position längs längden (0..1), fv = position längs bredden (0..1)."""
    H, W = label.shape
    counts = [0] * 7
    areas = [0.0] * 7
    features = []
    px_area_mm2 = mm_per_px * mm_per_px
    for model_cls in range(1, 7):
        gui_cls = MODEL_TO_GUI[model_cls]
        mask = label == model_cls
        if not mask.any():
            continue
        lab, n = ndimage.label(mask)
        if n == 0:
            continue
        centroids = ndimage.center_of_mass(mask, lab, range(1, n + 1))
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        for (r, c), sz in zip(centroids, sizes):
            counts[gui_cls] += 1
            area = float(sz) * px_area_mm2
            areas[gui_cls] += area
            features.append({"cls": gui_cls, "u": r / H, "fv": c / W, "area": area})
    return counts, areas, features


def board_payload(board: dict, target_len: int = TEX_LEN) -> dict:
    """Bygger GUI:ts board-datakontrakt ur en make_board-bräda."""
    color = board["color"]
    label = board["label"]
    height = board["height"]
    mm = board["mm_per_px"]
    H, W = label.shape

    # reliefkanal (fotometrisk stereo) som gråskala
    relief = relief_map(surface_normals(height, mm))
    relief_rgb = (np.clip(relief / (np.percentile(relief, 99) + 1e-6), 0, 1)
                  * 255).astype(np.uint8)
    relief_rgb = np.repeat(relief_rgb[..., None], 3, axis=2)

    # höjd som gråskala (för profil + höjdkanal)
    h_norm = np.clip((height - height.min()) / (np.ptp(height) + 1e-6), 0, 1)
    height_rgb = np.repeat((h_norm * 255).astype(np.uint8)[..., None], 3, axis=2)

    counts, areas, features = _features_from_label(label, mm)
    return {
        "id": None,
        "lengthMm": H * mm, "widthMm": W * mm, "mmPerPx": mm,
        "texLen": min(target_len, H),
        "color_png": _png_b64(_downscale_rgb(color, target_len)),
        "relief_png": _png_b64(_downscale_rgb(relief_rgb, target_len)),
        "height_png": _png_b64(_downscale_rgb(height_rgb, target_len)),
        "stats": {
            "counts": counts, "areas": [round(a, 1) for a in areas],
            "features": features,
            "defectArea": round(sum(areas), 1),
        },
    }


def segment_board(board: dict, seg_cfg: SegConfig | None = None):
    """U-Net-segmentering -> GUI-klasskarta + per-klass-stats + mIoU.
    Faller tillbaka på facit om ingen checkpoint finns (dokumenterat)."""
    seg_cfg = seg_cfg or SegConfig()
    ckpt = find_checkpoint(seg_cfg)
    if ckpt is not None:
        model, mcfg = load_model(str(ckpt))
        pred = predict_board(model, board, mcfg)
        source = "unet"
    else:
        pred = board["label"]
        source = "facit"

    gt = board["label"]
    # mIoU mot facit (per modellklass som finns)
    ious = []
    for c in range(7):
        p, g = pred == c, gt == c
        union = (p | g).sum()
        if union:
            ious.append((p & g).sum() / union)
    miou = float(np.mean(ious)) if ious else 1.0

    counts, areas, features = _features_from_label(pred, board["mm_per_px"])
    return {
        "source": source, "miou": round(miou, 3),
        "stats": {"counts": counts, "areas": [round(a, 1) for a in areas],
                  "features": features},
    }


def make_board_for(seed: int, width_mm: float = 125.0, length_m: float = 5.4,
                   mm_per_px: float = 0.5, subtle: bool = False):
    return make_board(length_mm=length_m * 1000, width_mm=width_mm,
                      mm_per_px=mm_per_px, seed=seed, subtle_defects=subtle)
