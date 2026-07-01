"""Ärlig per-klass-IoU ENBART på Kodyteks validering (utan syntet-uppblåsning).

Combined-träningens val_mIoU blandar in lätta syntetpatchar och blåser upp
siffran (särskilt blånad/vankant). Det här kör checkpointen på Kodyteks egen
val-delmängd så vi ser den VERKLIGA prestandan på äkta trä.

    python tools/eval_kodytek.py                      # outputs/seg_combined.pt
    python tools/eval_kodytek.py outputs/seg_kodytek.pt
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from torch.utils.data import DataLoader

from src.config import CLASSES
from src.dataset import KodytekDataset
from src.infer import load_model
from src.train import evaluate


def main():
    ckpt = sys.argv[1] if len(sys.argv) > 1 else "outputs/seg_combined.pt"
    data_root = sys.argv[2] if len(sys.argv) > 2 else None
    model, cfg = load_model(ckpt)
    cfg.dataset = "kodytek"
    cfg.num_workers = 0
    cfg.data_root = data_root or cfg.data_root or "data/kodytek"
    device = cfg.resolved_device()
    print(f"Utvärderar {ckpt} ENBART på Kodytek-val ({cfg.data_root}, "
          f"device={device}) ...", flush=True)

    val = KodytekDataset(cfg, cfg.data_root, "val")
    loader = DataLoader(val, batch_size=max(1, cfg.batch_size), num_workers=0)
    cm = evaluate(model, loader, cfg, device)

    print("\nKodytek-ENBART per-klass-IoU:")
    for i, v in enumerate(cm.iou_per_class()):
        print(f"  {CLASSES[i]:<11} {v:.3f}")
    print(f"\n  mIoU (Kodytek) = {cm.mean_iou():.3f}  ·  pixel_acc = {cm.pixel_acc():.3f}")


if __name__ == "__main__":
    main()
