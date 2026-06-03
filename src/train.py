"""Träningsloop för segmenteringsnätet.

Körs på CPU mot den syntetiska generatorn för verifiering, och oförändrad på
GPU mot Kodytek (peka loaders dit i dataset.make_loaders och höj configen).

Exempel::

    python -m src.train --smoke          # snabb rökverifiering
    python -m src.train --epochs 20      # längre körning, override av config
"""
from __future__ import annotations

import argparse
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch

from .config import SegConfig, CLASSES
from .dataset import make_loaders
from .losses import ConfusionMatrix, class_weights_from_counts, combined_loss
from .model import build_model, count_params


def evaluate(model, loader, cfg, device) -> ConfusionMatrix:
    model.eval()
    cm = ConfusionMatrix(cfg.n_classes)
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            cm.update(model(x), y)
    return cm


def fit(cfg: SegConfig, verbose: bool = True):
    """Tränar modellen enligt cfg och sparar bästa checkpoint. Returnerar
    (model, best_cm, ckpt_path)."""
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    device = cfg.resolved_device()

    train_loader, val_loader, train_ds = make_loaders(cfg)
    model = build_model(cfg).to(device)

    class_weights = None
    if cfg.use_class_weights:
        class_weights = class_weights_from_counts(
            train_ds.class_pixel_counts(), device=device)

    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr,
                            weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs)

    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(exist_ok=True)
    ckpt_path = out_dir / cfg.ckpt_name

    if verbose:
        src = (f"kodytek ({len(train_ds.files)} bilder)"
               if cfg.dataset == "kodytek" else f"syntetisk ({cfg.n_train_boards} brädor)")
        print(f"Enhet: {device} | parametrar: {count_params(model):,} | "
              f"ruta: {cfg.tile} | data: {src}")
        if class_weights is not None:
            print("Klassvikter: " +
                  ", ".join(f"{CLASSES[i]}={w:.2f}"
                            for i, w in enumerate(class_weights.tolist())))

    best_miou = -1.0
    best_cm = None
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        t0 = time.time()
        running = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = combined_loss(logits, y, cfg.n_classes,
                                 dice_weight=cfg.dice_weight,
                                 class_weights=class_weights)
            loss.backward()
            opt.step()
            running += loss.item()
        sched.step()

        cm = evaluate(model, val_loader, cfg, device)
        miou = cm.mean_iou()
        if verbose:
            print(f"epok {epoch:2d}/{cfg.epochs}  loss={running/len(train_loader):.3f}  "
                  f"val_mIoU={miou:.3f}  pixel_acc={cm.pixel_acc():.3f}  "
                  f"({time.time()-t0:.1f}s)")

        if miou > best_miou:
            best_miou = miou
            best_cm = cm
            torch.save({"model": model.state_dict(),
                        "cfg": cfg.__dict__,
                        "val_miou": miou}, ckpt_path)

    if verbose:
        print(f"\nBästa val-mIoU: {best_miou:.3f}  ->  {ckpt_path}")
        if best_cm is not None:
            print("Per-klass-IoU:")
            for i, v in enumerate(best_cm.iou_per_class()):
                print(f"  {CLASSES[i]:<11} {v:.3f}")
    return model, best_cm, ckpt_path


def _parse_args() -> SegConfig:
    base = SegConfig()
    p = argparse.ArgumentParser(description="Träna segmenteringsnätet")
    p.add_argument("--smoke", action="store_true", help="minimal snabbkörning")
    p.add_argument("--epochs", type=int)
    p.add_argument("--tile", type=int)
    p.add_argument("--base-channels", type=int)
    p.add_argument("--n-train-boards", type=int)
    p.add_argument("--device", choices=["auto", "cpu", "cuda"])
    a = p.parse_args()
    cfg = SegConfig.smoke() if a.smoke else base
    over = {}
    if a.epochs is not None: over["epochs"] = a.epochs
    if a.tile is not None: over["tile"] = a.tile
    if a.base_channels is not None: over["base_channels"] = a.base_channels
    if a.n_train_boards is not None: over["n_train_boards"] = a.n_train_boards
    if a.device is not None: over["device"] = a.device
    return replace(cfg, **over) if over else cfg


if __name__ == "__main__":
    fit(_parse_args())
