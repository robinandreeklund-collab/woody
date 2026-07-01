"""Inferens: kör en tränad modell över en hel bräda och syr ihop resultatet.

Brädan är större än modellens ruta, så vi kaklar med överlapp och summerar
logits (overlap-add) innan argmax — ger jämna skarvar utan rutkanter.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from .config import SegConfig, CLASS_COLORS
from .features import build_features, normalize
from .model import build_model


def load_model(ckpt_path: str, device: str | None = None):
    """Laddar checkpoint sparad av train.fit. Returnerar (model, cfg)."""
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg = SegConfig(**ckpt["cfg"])
    device = device or cfg.resolved_device()
    model = build_model(cfg).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, cfg


@torch.no_grad()
def predict_board(model, board: dict, cfg: SegConfig,
                  device: str | None = None, overlap: float = 0.25) -> np.ndarray:
    """board-dict -> label HxW int (argmax av hopsydda logits).

    Bygger samma kanaler (RGB + ev. relief/grain_dev) som vid träning.
    """
    device = device or cfg.resolved_device()
    feat = build_features(board, cfg.extra_channels)   # H,W,C
    H, W = feat.shape[:2]
    t = cfg.tile
    stride = max(1, int(t * (1 - overlap)))
    x = normalize(feat).unsqueeze(0)                   # 1,C,H,W

    logit_sum = torch.zeros(1, cfg.n_classes, H, W)
    weight = torch.zeros(1, 1, H, W)

    rows = list(range(0, max(1, H - t + 1), stride))
    cols = list(range(0, max(1, W - t + 1), stride)) or [0]
    if rows[-1] != H - t:
        rows.append(max(0, H - t))
    if W > t and cols[-1] != W - t:
        cols.append(max(0, W - t))

    for r0 in rows:
        for c0 in cols:
            r1, c1 = min(r0 + t, H), min(c0 + t, W)
            patch = x[:, :, r0:r1, c0:c1].to(device)
            # padda till full ruta om vi nuddar kanten
            ph, pw = t - (r1 - r0), t - (c1 - c0)
            if ph or pw:
                patch = torch.nn.functional.pad(patch, (0, pw, 0, ph), mode="reflect")
            out = model(patch).cpu()[:, :, : r1 - r0, : c1 - c0]
            logit_sum[:, :, r0:r1, c0:c1] += out
            weight[:, :, r0:r1, c0:c1] += 1.0

    logits = logit_sum / weight.clamp_min(1.0)
    return logits.argmax(1)[0].numpy().astype(np.uint8)


def colorize(label: np.ndarray) -> np.ndarray:
    """Klass-id -> RGB-bild i [0,1] enligt CLASS_COLORS."""
    rgb = np.zeros(label.shape + (3,), dtype=np.float32)
    for cid, color in CLASS_COLORS.items():
        rgb[label == cid] = color
    return rgb


def find_checkpoint(cfg: SegConfig) -> Path | None:
    p = Path(cfg.out_dir) / cfg.ckpt_name
    return p if p.exists() else None
