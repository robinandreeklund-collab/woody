"""Ablation: hjälper sensorkanalerna (relief + snedfibrighet) segmenteringen?

Tränar samma U-Net med och utan extrakanalerna, i två dataregimer:

  färgtydlig  – defekterna har distinkt färg (generatorns standard)
  subtil      – spricka/kvist nästan osynliga i färg, full signatur i
                höjd/fiber (subtle_defects=True)

Förväntan: i den färgtydliga regimen räcker RGB (sensorerna tillför mest brus);
i den subtila blir sensorkanalerna avgörande.

Kör:  python run_ablation.py            # full (4 träningar, ~5 min CPU)
      python run_ablation.py --quick    # snabbare, färre epoker
"""
import argparse
from dataclasses import replace

from src.config import SegConfig, CLASSES
from src.train import fit


def run(base: SegConfig):
    results = {}
    for regime, subtle in [("färgtydlig", False), ("subtil", True)]:
        for tag, extra in [("RGB", ()), ("RGB+sensorer", ("relief", "grain_dev"))]:
            cfg = replace(base, subtle_defects=subtle, extra_channels=extra,
                          ckpt_name="abl.pt")
            print(f"-> tränar [{regime} | {tag}] ...")
            _, cm, _ = fit(cfg, verbose=False)
            results[(regime, tag)] = cm
    return results


def report(results):
    for regime in ("färgtydlig", "subtil"):
        a = results[(regime, "RGB")]
        b = results[(regime, "RGB+sensorer")]
        print(f"\n=== Regim: {regime} – per-klass-IoU ===")
        print(f"{'klass':<12}{'RGB':>8}{'+sensorer':>12}{'delta':>9}")
        for i in range(len(CLASSES)):
            ia, ib = a.iou_per_class()[i], b.iou_per_class()[i]
            print(f"{CLASSES[i]:<12}{ia:>8.3f}{ib:>12.3f}{ib-ia:>+9.3f}")
        da, db = a.mean_iou(), b.mean_iou()
        print(f"{'mIoU':<12}{da:>8.3f}{db:>12.3f}{db-da:>+9.3f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    a = p.parse_args()
    base = SegConfig(tile=128, base_channels=16, depth=3, n_train_boards=8,
                     epochs=6 if a.quick else 10, steps_per_epoch=40, batch_size=8)
    report(run(base))


if __name__ == "__main__":
    main()
