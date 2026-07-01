"""Förlust och utvärderingsmått för segmenteringen.

- combined_loss: viktad cross-entropy + Dice (Dice hanterar klassobalansen
  när clear_wood dominerar pixlarna).
- ConfusionMatrix: ackumulerar över valmängden och ger per-klass-IoU + mIoU.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F


def dice_loss(logits: torch.Tensor, target: torch.Tensor,
              n_classes: int, eps: float = 1.0) -> torch.Tensor:
    """Mjuk multiklass-Dice (1 - medel-Dice över klasser)."""
    probs = F.softmax(logits, dim=1)
    onehot = F.one_hot(target, n_classes).permute(0, 3, 1, 2).float()
    dims = (0, 2, 3)
    inter = (probs * onehot).sum(dims)
    card = probs.sum(dims) + onehot.sum(dims)
    dice = (2 * inter + eps) / (card + eps)
    return 1.0 - dice.mean()


def combined_loss(logits, target, n_classes, dice_weight=0.5, class_weights=None):
    ce = F.cross_entropy(logits, target, weight=class_weights)
    if dice_weight <= 0:
        return ce
    return ce + dice_weight * dice_loss(logits, target, n_classes)


def class_weights_from_counts(counts: np.ndarray, device=None,
                              bg_index: int = 0, max_weight: float = 8.0
                              ) -> torch.Tensor:
    """Vikter för cross-entropy från pixelfrekvenser.

    Inverterad rotfrekvens, men normaliserad mot bakgrundsklassen (bg=1.0) och
    kapad uppåt. Det väger upp sällsynta defekter utan att krossa bakgrunden –
    annars predikterar nätet defekter överallt (pixel_acc kollapsar).
    """
    freq = counts / max(counts.sum(), 1.0)
    w = 1.0 / np.sqrt(freq + 1e-6)
    w = w / w[bg_index]                  # bakgrund -> 1.0
    w = np.clip(w, 1.0, max_weight)      # defekter upp till max_weight x
    return torch.tensor(w, dtype=torch.float32, device=device)


class ConfusionMatrix:
    """Ackumulerar predikterade vs sanna klasser och räknar IoU."""

    def __init__(self, n_classes: int):
        self.n = n_classes
        self.mat = np.zeros((n_classes, n_classes), dtype=np.int64)

    @torch.no_grad()
    def update(self, logits: torch.Tensor, target: torch.Tensor):
        pred = logits.argmax(1).view(-1).cpu().numpy()
        true = target.view(-1).cpu().numpy()
        k = (true >= 0) & (true < self.n)
        idx = self.n * true[k].astype(np.int64) + pred[k].astype(np.int64)
        self.mat += np.bincount(idx, minlength=self.n ** 2).reshape(self.n, self.n)

    def iou_per_class(self) -> np.ndarray:
        tp = np.diag(self.mat).astype(np.float64)
        fp = self.mat.sum(0) - tp
        fn = self.mat.sum(1) - tp
        denom = tp + fp + fn
        with np.errstate(invalid="ignore", divide="ignore"):
            iou = np.where(denom > 0, tp / denom, np.nan)
        return iou

    def mean_iou(self) -> float:
        return float(np.nanmean(self.iou_per_class()))

    def pixel_acc(self) -> float:
        return float(np.diag(self.mat).sum() / max(self.mat.sum(), 1))
