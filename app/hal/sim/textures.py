"""Trätextur-bank — använder ÄKTA virke ur Kodytek-datasetet (om det finns lokalt)
för att klä brädornas yta. Faller tillbaka till procedurell textur när datasetet
saknas (t.ex. i CI), så simuleringen alltid fungerar.

Kodytek: produktionsbilder 2800×1024 (≈ en hel bräda) — perfekta som yttextur.
Vi använder bara FÄRGBILDEN här (suffix _segm/_anno hoppas över); höjd/defekter
genereras fortfarande syntetiskt så mät-simuleringen har känt facit.

Sökväg: env WOODY_TEXTURES, annars data/kodytek_raw, data/kodytek, data/textures
samt toppnivå-mappar som heter ~kodytek/wood/veneer/texture/dataset.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

_EXTS = (".bmp", ".png", ".jpg", ".jpeg")
_SKIP = ("_segm", "_anno", "mask", "label")
_MAX_SCAN = 4000
_bank = None


def _default_roots() -> list[Path]:
    cands: list[Path] = []
    env = os.environ.get("WOODY_TEXTURES")
    if env:
        cands.append(Path(env))
    cwd = Path.cwd()
    cands += [cwd / "data" / "kodytek_raw", cwd / "data" / "kodytek",
              cwd / "data" / "textures", cwd / "data"]
    if cwd.exists():
        for p in cwd.iterdir():
            if p.is_dir() and any(k in p.name.lower()
                                  for k in ("kodytek", "wood", "veneer", "texture", "dataset")):
                cands.append(p)
    return cands


class TextureBank:
    def __init__(self, roots=None):
        self.files: list[Path] = []
        self._cache: dict[str, np.ndarray] = {}
        seen = set()
        for root in (roots or _default_roots()):
            root = Path(root)
            if not root.exists() or str(root) in seen:
                continue
            seen.add(str(root))
            for f in root.rglob("*"):
                if len(self.files) >= _MAX_SCAN:
                    break
                if f.suffix.lower() in _EXTS and not any(s in f.name.lower() for s in _SKIP):
                    self.files.append(f)
        if self.files:
            print(f"[textur] {len(self.files)} virkesbilder från datasetet — äkta yttextur på")

    def available(self) -> bool:
        return len(self.files) > 0

    def _load(self, f: Path) -> np.ndarray:
        key = str(f)
        if key in self._cache:
            return self._cache[key]
        from PySide6.QtGui import QImage                       # lazy
        qi = QImage(str(f))
        if qi.isNull():
            raise ValueError(f"kunde inte läsa {f}")
        qi = qi.convertToFormat(QImage.Format.Format_RGB888)
        W, H, bpl = qi.width(), qi.height(), qi.bytesPerLine()
        arr = np.frombuffer(memoryview(qi.constBits()), np.uint8)
        arr = arr.reshape(H, bpl)[:, : W * 3].reshape(H, W, 3).copy()
        if len(self._cache) < 8:
            self._cache[key] = arr
        return arr

    def random_patch(self, rng, w: int, h: int):
        """Slumpat utsnitt ur en äkta virkesbild, skalat till (h, w, 3)."""
        if not self.files:
            return None
        try:
            arr = self._load(self.files[int(rng.integers(len(self.files)))])
        except Exception:
            return None
        H, W = arr.shape[:2]
        aspect = w / h
        cw = W
        ch = int(round(cw / aspect))
        if ch > H:
            ch, cw = H, int(round(H * aspect))
        x0 = int(rng.integers(0, max(1, W - cw + 1)))
        y0 = int(rng.integers(0, max(1, H - ch + 1)))
        crop = arr[y0:y0 + ch, x0:x0 + cw]
        ys = np.linspace(0, crop.shape[0] - 1, h).astype(int)
        xs = np.linspace(0, crop.shape[1] - 1, w).astype(int)
        return crop[np.ix_(ys, xs)].copy()


def texture_bank() -> TextureBank:
    global _bank
    if _bank is None:
        _bank = TextureBank()
    return _bank
