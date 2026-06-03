"""Datakällor för segmenteringsträningen.

SyntheticBoardDataset  – genererar brädor med facit via board.make_board och
                         samplar kvadratiska rutor (defektmedvetet). Används
                         för CPU-verifiering utan nedladdning.
KodytekDataset         – läser riktiga bild/mask-par från disk; samma gränssnitt,
                         så man byter loader utan att röra modell eller träning.

Bilder normaliseras till [-1, 1]. Etiketter är klass-id 0..6 (se config.CLASSES).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

from .board import make_board
from .config import SegConfig
from .features import build_features, zero_filled_features, normalize


def _to_tensors(feat_tile: np.ndarray, label_tile: np.ndarray):
    """HxWxC float ~[0,1] + HxW  ->  (C,H,W) tensor [-1,1], (H,W) long."""
    x = normalize(np.ascontiguousarray(feat_tile))
    y = torch.from_numpy(np.ascontiguousarray(label_tile).astype(np.int64))
    return x, y


def _crop(arr: np.ndarray, r0: int, c0: int, t: int) -> np.ndarray:
    """Beskär t×t och nollpaddar om kanten nås (gäller smala brädor)."""
    h, w = arr.shape[:2]
    r1, c1 = min(r0 + t, h), min(c0 + t, w)
    patch = arr[r0:r1, c0:c1]
    ph, pw = t - (r1 - r0), t - (c1 - c0)
    if ph or pw:
        pad = [(0, ph), (0, pw)] + ([(0, 0)] if arr.ndim == 3 else [])
        patch = np.pad(patch, pad, mode="reflect" if patch.size else "constant")
    return patch


class SyntheticBoardDataset(Dataset):
    """Rutor klippta ur procedurellt genererade brädor."""

    def __init__(self, cfg: SegConfig, split: str = "train"):
        self.cfg = cfg
        self.split = split
        self.tile = cfg.tile
        self.augment = cfg.augment and split == "train"

        if split == "train":
            seeds = range(cfg.train_seed, cfg.train_seed + cfg.n_train_boards)
            self._length = cfg.steps_per_epoch * cfg.batch_size
        else:
            seeds = range(cfg.val_seed, cfg.val_seed + cfg.n_val_boards)
            self._length = None  # sätts av valrutnätet nedan

        self.boards = []          # (feat HxWxC float, label HxW)
        self.defect_coords = []   # (rows, cols) för label>0 per bräda
        for s in seeds:
            b = make_board(length_mm=cfg.board_length_mm, width_mm=cfg.board_width_mm,
                           mm_per_px=cfg.mm_per_px, seed=s,
                           subtle_defects=cfg.subtle_defects)
            feat = build_features(b, cfg.extra_channels)
            self.boards.append((feat, b["label"]))
            ys, xs = np.where(b["label"] > 0)
            self.defect_coords.append((ys, xs))

        self.rng = np.random.default_rng(cfg.seed + (0 if split == "train" else 1))

        if split != "train":
            # Fast rutnät över varje valbräda -> deterministisk, repeterbar metrik
            self.val_index = []
            t = self.tile
            for bi, (feat, _) in enumerate(self.boards):
                h, w = feat.shape[:2]
                rows = list(range(0, max(1, h - t + 1), t))
                cols = list(range(0, max(1, w - t + 1), t)) or [0]
                if rows and rows[-1] != h - t:
                    rows.append(max(0, h - t))
                for r0 in rows:
                    for c0 in cols:
                        self.val_index.append((bi, r0, c0))
            self._length = len(self.val_index)

    def __len__(self) -> int:
        return self._length

    def _sample_train_tile(self):
        bi = int(self.rng.integers(0, len(self.boards)))
        feat, label = self.boards[bi]
        h, w = label.shape
        t = self.tile
        ys, xs = self.defect_coords[bi]
        if len(ys) and self.rng.random() < self.cfg.p_defect_tile:
            # centrera (jittrat) kring en defektpixel för stark inlärningssignal
            k = int(self.rng.integers(0, len(ys)))
            r0 = int(np.clip(ys[k] - t // 2 + self.rng.integers(-t // 4, t // 4 + 1),
                             0, max(0, h - t)))
            c0 = int(np.clip(xs[k] - t // 2 + self.rng.integers(-t // 4, t // 4 + 1),
                             0, max(0, w - t)))
        else:
            r0 = int(self.rng.integers(0, max(1, h - t + 1)))
            c0 = int(self.rng.integers(0, max(1, w - t + 1)))
        return _crop(feat, r0, c0, t), _crop(label, r0, c0, t)

    def __getitem__(self, idx: int):
        if self.split == "train":
            ct, lt = self._sample_train_tile()
            if self.augment:
                if self.rng.random() < 0.5:
                    ct, lt = ct[:, ::-1], lt[:, ::-1]
                if self.rng.random() < 0.5:
                    ct, lt = ct[::-1], lt[::-1]
                k = int(self.rng.integers(0, 4))
                ct, lt = np.rot90(ct, k), np.rot90(lt, k)
        else:
            bi, r0, c0 = self.val_index[idx]
            feat, label = self.boards[bi]
            ct, lt = _crop(feat, r0, c0, self.tile), _crop(label, r0, c0, self.tile)
        return _to_tensors(np.ascontiguousarray(ct), np.ascontiguousarray(lt))

    def class_pixel_counts(self) -> np.ndarray:
        """Pixelantal per klass över träningsbrädorna (för klassvikter)."""
        counts = np.zeros(self.cfg.n_classes, dtype=np.float64)
        for _, label in self.boards:
            binc = np.bincount(label.ravel(), minlength=self.cfg.n_classes)
            counts += binc[: self.cfg.n_classes]
        return counts


class KodytekDataset(Dataset):
    """Riktiga bild/mask-par. Förväntad katalogstruktur::

        root/
          images/ <namn>.png        (RGB)
          masks/  <namn>.png         (gråskala, pixelvärde = klass-id 0..6)

    Kodyteks egna annoteringar (polygoner/boxar) rasteriseras först till
    sådana klass-id-masker; klasserna mappas till config.CLASSES. Byt till
    denna i make_loaders() när data finns på disk.
    """

    def __init__(self, cfg: SegConfig, root: str, split: str = "train"):
        try:
            from PIL import Image
        except ImportError as e:  # pragma: no cover - bara relevant med riktig data
            raise ImportError("KodytekDataset kräver Pillow: pip install pillow") from e
        self._Image = Image
        self.cfg = cfg
        self.split = split
        self.tile = cfg.tile
        self.augment = cfg.augment and split == "train"
        root = Path(root)
        self.images = sorted((root / "images").glob("*.png"))
        self.masks_dir = root / "masks"
        if not self.images:
            raise FileNotFoundError(f"Inga bilder i {root/'images'}")
        self.rng = np.random.default_rng(cfg.seed)

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int):
        img_path = self.images[idx]
        color = np.asarray(self._Image.open(img_path).convert("RGB"))
        label = np.asarray(self._Image.open(self.masks_dir / img_path.name))
        h, w = label.shape[:2]
        t = self.tile
        r0 = int(self.rng.integers(0, max(1, h - t + 1)))
        c0 = int(self.rng.integers(0, max(1, w - t + 1)))
        # Riktig sensordata saknar relief/fiber-lager -> nollfyll extrakanalerna.
        # (Byt till verkliga sensorbilder här när de finns.)
        feat = zero_filled_features(color, self.cfg.extra_channels)
        ct, lt = _crop(feat, r0, c0, t), _crop(label, r0, c0, t)
        if self.augment and self.rng.random() < 0.5:
            ct, lt = ct[:, ::-1], lt[:, ::-1]
        return _to_tensors(np.ascontiguousarray(ct), np.ascontiguousarray(lt))


def make_loaders(cfg: SegConfig):
    """Returnerar (train_loader, val_loader, train_dataset) för syntetisk data."""
    train_ds = SyntheticBoardDataset(cfg, split="train")
    val_ds = SyntheticBoardDataset(cfg, split="val")
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True,
                              num_workers=cfg.num_workers, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                            num_workers=cfg.num_workers)
    return train_loader, val_loader, train_ds
