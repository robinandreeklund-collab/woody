"""Bygger modellens ingångskanaler ur en bräda.

Utöver färg (RGB) kan extra sensorkanaler stackas som ingång till nätet:
  relief     – ytlutning ur fotometrisk stereo (lyfter sprickor/kanter)
  grain_dev  – snedfibrighet ur tracheid (lyfter kvistar/störd fiber)

Båda är skalära magnitud-fält (ej riktade), så de tål speglingar/rotationer i
augmenteringen utan korrigering. Samma byggare används av dataset och inferens
så kanalerna alltid matchar mellan träning och körning.
"""
from __future__ import annotations

import numpy as np

from . import photometric as ps
from . import tracheid as tr


def _relief(board: dict) -> np.ndarray:
    normals = ps.surface_normals(board["height"], board["mm_per_px"])
    return ps.relief_map(normals).astype(np.float32)            # 0..1


def _grain_dev(board: dict) -> np.ndarray:
    return np.clip(tr.grain_deviation_deg(board) / 45.0, 0, 1).astype(np.float32)


def _nir(board: dict) -> np.ndarray:
    """NIR-strobe-kanal (blånad/röta syns bäst här). 0..1."""
    nir = board.get("nir")
    if nir is None:
        return np.zeros(board["label"].shape, np.float32)
    return (nir.astype(np.float32) / 255.0)


CHANNEL_BUILDERS = {"relief": _relief, "grain_dev": _grain_dev, "nir": _nir}


def channel_names(extra_channels=()) -> tuple:
    return ("R", "G", "B") + tuple(extra_channels)


def build_features(board: dict, extra_channels=()) -> np.ndarray:
    """(H,W,3+E) float i ~[0,1]: RGB först, sedan extrakanalerna i ordning."""
    chans = [board["color"].astype(np.float32) / 255.0]
    for name in extra_channels:
        chans.append(CHANNEL_BUILDERS[name](board)[..., None])
    return np.concatenate(chans, axis=-1)


def zero_filled_features(color_u8: np.ndarray, extra_channels=()) -> np.ndarray:
    """RGB ur en bild + nollade extrakanaler (för data utan sensorlager)."""
    color = color_u8.astype(np.float32) / 255.0
    if not extra_channels:
        return color
    zeros = np.zeros(color.shape[:2] + (len(extra_channels),), np.float32)
    return np.concatenate([color, zeros], axis=-1)


def normalize(feat: np.ndarray):
    """(H,W,C) ~[0,1] -> torch-tensor (C,H,W) i [-1,1]."""
    import torch
    x = np.ascontiguousarray(feat.transpose(2, 0, 1))
    x = (x - 0.5) / 0.5
    return torch.from_numpy(x).float()
