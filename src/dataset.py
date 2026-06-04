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


_IMG_EXTS = ("*.png", "*.bmp", "*.jpg", "*.jpeg")


class KodytekDataset(Dataset):
    """Riktiga Kodytek-bilder + rastrerade klass-id-masker. Katalogstruktur::

        root/
          images/ <namn>.(png|bmp|jpg)   (RGB-foton, t.ex. 2800x1024)
          masks/  <namn>.png              (gråskala, pixelvärde = klass-id 0..6)

    Masker skapas av src/kodytek.py (Kodyteks semantiska kartor/boxar -> GUI:ts
    7 klasser). Tränings-/valdelning sker deterministiskt per filnamn.
    """

    def __init__(self, cfg: SegConfig, root: str, split: str = "train"):
        try:
            from PIL import Image
        except ImportError as e:  # pragma: no cover
            raise ImportError("KodytekDataset kräver Pillow: pip install pillow") from e
        self._Image = Image
        self.cfg = cfg
        self.split = split
        self.tile = cfg.tile
        self.augment = cfg.augment and split == "train"
        # resampling till riggens mm/px (a): >0 => rutorna skalas så att 1 px
        # motsvarar target_mm_per_px, oavsett Kodyteks egna pixelmått.
        self.target = float(getattr(cfg, "target_mm_per_px", 0.0) or 0.0)
        self.src_len_mm = float(getattr(cfg, "kodytek_len_mm", 5000.0))
        self.src_w_mm = float(getattr(cfg, "kodytek_width_mm", 150.0))
        root = Path(root)
        self.masks_dir = root / "masks"
        files = []
        for ext in _IMG_EXTS:
            files += (root / "images").glob(ext)
        files = sorted(p for p in files if (self.masks_dir / (p.stem + ".png")).exists())
        if not files:
            raise FileNotFoundError(f"Inga bild/mask-par i {root}")

        # deterministisk split per filnamn (hash) -> stabil mellan körningar
        import hashlib
        def in_val(p):
            h = int(hashlib.md5(p.stem.encode()).hexdigest(), 16) % 1000
            return h < cfg.val_frac * 1000
        self.files = [p for p in files if in_val(p) == (split == "val")] or files
        self.rng = np.random.default_rng(cfg.seed + (0 if split == "train" else 1))

    def __len__(self) -> int:
        if self.split == "train":
            return self.cfg.steps_per_epoch * self.cfg.batch_size
        return len(self.files)

    def _load(self, path):
        color = np.asarray(self._Image.open(path).convert("RGB"))
        label = np.asarray(self._Image.open(self.masks_dir / (path.stem + ".png")))
        if label.ndim == 3:
            label = label[..., 0]
        return color, label

    def _tile_origin(self, label, H, W, ch, cw):
        """Övre vänstra hörnet för ett ch×cw-utsnitt (ev. defektcentrerat)."""
        if self.split == "train":
            ys, xs = np.where(label > 0)
            if len(ys) and self.rng.random() < self.cfg.p_defect_tile:
                k = int(self.rng.integers(0, len(ys)))
                return (int(np.clip(ys[k] - ch // 2, 0, max(0, H - ch))),
                        int(np.clip(xs[k] - cw // 2, 0, max(0, W - cw))))
            return (int(self.rng.integers(0, max(1, H - ch + 1))),
                    int(self.rng.integers(0, max(1, W - cw + 1))))
        return max(0, (H - ch) // 2), max(0, (W - cw) // 2)

    def _sample_tile(self, color, label):
        """En tile×tile-ruta. Med target>0 beskärs ett källutsnitt vars fysiska
        storlek = tile·target_mm_per_px och skalas till tile×tile (crop-then-resize,
        billigt och korrekt även för Kodyteks anisotropa upplösning)."""
        H, W = label.shape
        t = self.tile
        if self.target > 0:
            longer = max(W, H)
            mm_long, mm_short = self.src_len_mm / longer, self.src_w_mm / min(W, H)
            mm_x, mm_y = (mm_long, mm_short) if W >= H else (mm_short, mm_long)
            cw = max(2, min(W, int(round(t * self.target / mm_x))))
            ch = max(2, min(H, int(round(t * self.target / mm_y))))
        else:
            ch = cw = t
        r0, c0 = self._tile_origin(label, H, W, ch, cw)
        cc = color[r0:r0 + ch, c0:c0 + cw]
        ll = label[r0:r0 + ch, c0:c0 + cw]
        if cc.shape[0] != t or cc.shape[1] != t:
            Image = self._Image
            cc = np.asarray(Image.fromarray(cc).resize((t, t), Image.BILINEAR))
            ll = np.asarray(Image.fromarray(ll.astype(np.uint8)).resize((t, t), Image.NEAREST))
        return cc, ll

    def __getitem__(self, idx: int):
        if self.split == "train":
            path = self.files[int(self.rng.integers(0, len(self.files)))]
        else:
            path = self.files[idx % len(self.files)]
        color, label = self._load(path)
        cc, lt = self._sample_tile(color, label)
        ct = zero_filled_features(cc, self.cfg.extra_channels)
        if self.augment:
            if self.rng.random() < 0.5:
                ct, lt = ct[:, ::-1], lt[:, ::-1]
            if self.rng.random() < 0.5:
                ct, lt = ct[::-1], lt[::-1]
        return _to_tensors(np.ascontiguousarray(ct), np.ascontiguousarray(lt))

    def class_pixel_counts(self, sample: int = 200) -> np.ndarray:
        """Klassfrekvens från ett urval masker (snabbt även för stora dataset)."""
        counts = np.zeros(self.cfg.n_classes, dtype=np.float64)
        for path in self.files[:sample]:
            _, label = self._load(path)
            binc = np.bincount(label.ravel(), minlength=self.cfg.n_classes)
            counts += binc[: self.cfg.n_classes]
        return counts


class CombinedDataset(Dataset):
    """Blandar syntetiska rigg-rutor (NIR + riggens mm/px) och riktiga Kodytek-
    rutor (resamplade till samma mm/px). Modellen ser både verklig appearance och
    sensorernas upplösning/NIR. Kanalantalet är gemensamt (RGB + extra_channels);
    syntetiken ger riktig NIR, Kodytek nollfylld NIR."""

    def __init__(self, cfg: SegConfig, split: str = "train"):
        self.cfg = cfg
        self.split = split
        self.synth = SyntheticBoardDataset(cfg, split=split)
        self.kod = KodytekDataset(cfg, cfg.data_root, split=split)
        self.p_synth = float(getattr(cfg, "synth_frac", 0.5))
        self.rng = np.random.default_rng(cfg.seed + (5 if split == "val" else 4))

    def __len__(self) -> int:
        if self.split == "train":
            return len(self.synth)
        return len(self.synth) + len(self.kod.files)

    def __getitem__(self, idx: int):
        if self.split == "train":
            if self.rng.random() < self.p_synth:
                return self.synth[int(self.rng.integers(0, len(self.synth)))]
            return self.kod[int(self.rng.integers(0, len(self.kod.files)))]
        ns = len(self.synth)                       # val: deterministiskt, syntet först
        return self.synth[idx] if idx < ns else self.kod[(idx - ns) % len(self.kod.files)]

    def class_pixel_counts(self) -> np.ndarray:
        """Klassvikter ur båda källorna (syntet + Kodytek)."""
        return self.synth.class_pixel_counts() + self.kod.class_pixel_counts()


def make_loaders(cfg: SegConfig):
    """Returnerar (train_loader, val_loader, train_dataset) enligt cfg.dataset."""
    if cfg.dataset == "kodytek":
        if not cfg.data_root:
            raise ValueError("cfg.data_root måste peka på rastrerad Kodytek-root")
        train_ds = KodytekDataset(cfg, cfg.data_root, "train")
        val_ds = KodytekDataset(cfg, cfg.data_root, "val")
    elif cfg.dataset == "combined":
        if not cfg.data_root:
            raise ValueError("cfg.data_root måste peka på rastrerad Kodytek-root")
        train_ds = CombinedDataset(cfg, "train")
        val_ds = CombinedDataset(cfg, "val")
    else:
        train_ds = SyntheticBoardDataset(cfg, split="train")
        val_ds = SyntheticBoardDataset(cfg, split="val")
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True,
                              num_workers=cfg.num_workers, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                            num_workers=cfg.num_workers)
    return train_loader, val_loader, train_ds
