"""Kompakt U-Net för pixelvis segmentering av virkesdefekter.

Encoder–decoder med skip-connections. Storleken styrs av base_channels och
depth i SegConfig — liten nog att tränas på CPU mot den syntetiska
generatorn, men identisk arkitektur skalar upp på GPU mot Kodytek.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from .config import SegConfig


class DoubleConv(nn.Module):
    """(Conv -> BN -> ReLU) x2, behåller spatiala måtten (padding=1)."""

    def __init__(self, c_in: int, c_out: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(c_in, c_out, 3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
            nn.Conv2d(c_out, c_out, 3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class UNet(nn.Module):
    """Liten U-Net. Indata: (B,3,H,W). Utdata: (B,n_classes,H,W) logits."""

    def __init__(self, in_ch: int = 3, n_classes: int = 7,
                 base: int = 24, depth: int = 3):
        super().__init__()
        self.depth = depth
        chans = [base * (2 ** i) for i in range(depth + 1)]  # ex: [24,48,96,192]

        self.downs = nn.ModuleList()
        self.pools = nn.ModuleList()
        c = in_ch
        for i in range(depth):
            self.downs.append(DoubleConv(c, chans[i]))
            self.pools.append(nn.MaxPool2d(2))
            c = chans[i]

        self.bottleneck = DoubleConv(chans[depth - 1], chans[depth])

        self.upconvs = nn.ModuleList()
        self.ups = nn.ModuleList()
        for i in reversed(range(depth)):
            self.upconvs.append(nn.ConvTranspose2d(chans[i + 1], chans[i], 2, stride=2))
            self.ups.append(DoubleConv(chans[i + 1], chans[i]))

        self.head = nn.Conv2d(chans[0], n_classes, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for down, pool in zip(self.downs, self.pools):
            x = down(x)
            skips.append(x)
            x = pool(x)
        x = self.bottleneck(x)
        for upconv, up, skip in zip(self.upconvs, self.ups, reversed(skips)):
            x = upconv(x)
            # säkra exakt matchning mot skip (om udda mått råkat uppstå)
            if x.shape[-2:] != skip.shape[-2:]:
                x = nn.functional.interpolate(x, size=skip.shape[-2:],
                                              mode="bilinear", align_corners=False)
            x = torch.cat([skip, x], dim=1)
            x = up(x)
        return self.head(x)


def build_model(cfg: SegConfig) -> UNet:
    return UNet(in_ch=3, n_classes=cfg.n_classes,
                base=cfg.base_channels, depth=cfg.depth)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
