"""Rastrerar Kodytek-datasetets annoteringar till klass-id-masker i GUI:ts
taxonomi (0..6), redo för KodytekDataset / src.train.

Kodytek (Zenodo 10.5281/zenodo.4694695, CC-BY 4.0): produktionsbilder 2800x1024
(≈500x15 cm = en hel bräda) med färgkodade semantiska kartor (BMP) och
bounding-box-textfiler ("label, left, top, right, bottom"). 10 defektklasser.

Två rastreringsvägar:
  - semantic: färgkodad karta -> klass-id via färg→klass-tabell (kan auto-härledas
    ur bbox+semantik, ingen legend behövs). Ger pixelnoggranna masker.
  - bbox:     fyll boxarna med klass-id. Grövre men kräver ingen färgkarta.

Klassmappning Kodytek(10) -> GUI(7) är konfigurerbar (KODYTEK_TO_GUI).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

# GUI-klasser: 1 Kvist, 2 Spricka, 3 Blånad, 4 Vankant, 5 Röta, 6 Hål (0 = frisk)
KODYTEK_TO_GUI = {
    "live_knot": 1, "dead_knot": 1, "knot_with_crack": 1,
    "crack": 2,
    "blue_stain": 3,
    "overgrown": 4,                      # överväxt kant ~ vankant
    "resin": 5, "marrow": 5, "quartzity": 5,   # ingen exakt GUI-motsvarighet
    "knot_missing": 6,                   # saknad kvist = hål
}
# namnvarianter -> kanoniskt namn
ALIASES = {"missing_knot": "knot_missing", "quartzite": "quartzity",
           "blue stain": "blue_stain", "knot with crack": "knot_with_crack"}

# Kodytek-filnamn: bild <id>.bmp, semantisk karta <id>_segm.bmp, bbox <id>_anno.txt.
# Suffixen prövas i tur och ordning (tom sträng = exakt samma stam som fallback).
SEMANTIC_SUFFIXES = ("_segm", "")
BBOX_SUFFIXES = ("_anno", "")


def _canon(name: str) -> str:
    n = name.strip().lower().replace("-", "_").replace(" ", "_")
    n = re.sub(r"_+", "_", n)
    return ALIASES.get(n, n)


def gui_id(kodytek_label: str) -> int:
    return KODYTEK_TO_GUI.get(_canon(kodytek_label), 0)


# ----------------------------- bbox -----------------------------
def parse_bboxes(txt_path: Path):
    """Returnerar [(label, l, t, r, b)] i fraktioner 0..1 (auto-detekterar skala)."""
    rows = []
    raw = []
    for line in Path(txt_path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"[,\s]+", line)
        if len(parts) < 5:
            continue
        label = parts[0]
        try:
            nums = [float(x) for x in parts[1:5]]
        except ValueError:
            continue
        raw.append((label, nums))
    if not raw:
        return rows
    mx = max(max(n) for _, n in raw)
    scale = 1.0 if mx <= 1.0 else (100.0 if mx <= 100.0 else None)
    for label, nums in raw:
        if scale:
            l, t, r, b = [n / scale for n in nums]
        else:                       # pixlar -> normaliseras senare med bildmått
            l, t, r, b = nums
        rows.append((label, l, t, r, b, scale is not None))
    return rows


def rasterize_bboxes(txt_path: Path, h: int, w: int) -> np.ndarray:
    mask = np.zeros((h, w), np.uint8)
    for label, l, t, r, b, normed in parse_bboxes(txt_path):
        gid = gui_id(label)
        if not gid:
            continue
        if normed:
            x0, x1 = int(l * w), int(r * w)
            y0, y1 = int(t * h), int(b * h)
        else:
            x0, x1, y0, y1 = int(l), int(r), int(t), int(b)
        x0, x1 = sorted((max(0, x0), min(w, x1)))
        y0, y1 = sorted((max(0, y0), min(h, y1)))
        mask[y0:y1, x0:x1] = gid
    return mask


# --------------------------- semantic ---------------------------
def _quantize(rgb: np.ndarray) -> np.ndarray:
    """HxWx3 -> HxW packad färg (int) för snabb färgjämförelse."""
    rgb = (rgb[..., :3].astype(np.int64) // 8) * 8     # tolerans mot komprimering
    return rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]


N_GUI_DEFECTS = 6   # antal defektklasser (1..6) som ska täckas


def derive_color_map(pairs, max_images: int = 6000) -> dict:
    """Auto-härleder packad färg -> GUI-klass ur (semantic_bmp, bbox_txt)-par.
    För varje box (känd etikett) röstar den dominerande icke-bakgrundsfärgen i
    boxen på den klassen. Bakgrund = globalt vanligaste färgen. Skannar fler par
    (med tidigt stopp) tills alla 6 defektklasser fått en färg – så sällsynta
    klasser (blånad/vankant/hål) inte tappas."""
    from PIL import Image
    votes = defaultdict(Counter)
    bg_counter = Counter()

    def current_map():
        bg = bg_counter.most_common(1)[0][0] if bg_counter else -1
        return {col: c.most_common(1)[0][0] for col, c in votes.items() if col != bg}

    for i, (sem_path, box_path) in enumerate(pairs[:max_images]):
        q = _quantize(np.asarray(Image.open(sem_path).convert("RGB")))
        bg_counter[int(np.bincount(q.ravel()).argmax())] += 1
        h, w = q.shape
        for label, l, t, r, b, normed in parse_bboxes(box_path):
            gid = gui_id(label)
            if not gid:
                continue
            x0, x1 = (int(l * w), int(r * w)) if normed else (int(l), int(r))
            y0, y1 = (int(t * h), int(b * h)) if normed else (int(t), int(b))
            sub = q[max(0, y0):y1, max(0, x0):x1].ravel()
            if sub.size:
                votes[int(np.bincount(sub).argmax())][gid] += 1
        if i >= 150 and len(set(current_map().values())) >= N_GUI_DEFECTS:
            break       # alla defektklasser täckta -> sluta skanna
    return current_map()


def rasterize_semantic(bmp_path: Path, color_map: dict) -> np.ndarray:
    from PIL import Image
    q = _quantize(np.asarray(Image.open(bmp_path).convert("RGB")))
    mask = np.zeros(q.shape, np.uint8)
    for col, gid in color_map.items():
        mask[q == col] = gid
    return mask


# --------------------------- build ------------------------------
def build_dataset(images_dir, out_root, semantic_dir=None, bbox_dir=None,
                  color_map=None, limit=None):
    """Skriver out_root/images/<namn>.png + out_root/masks/<namn>.png.

    images_dir kan vara en katalog eller en lista av kataloger (t.ex. Kodyteks
    Images1..10), som då slås ihop."""
    from PIL import Image
    import time
    out_root = Path(out_root)
    (out_root / "images").mkdir(parents=True, exist_ok=True)
    (out_root / "masks").mkdir(parents=True, exist_ok=True)

    dirs = [images_dir] if isinstance(images_dir, (str, Path)) else list(images_dir)
    imgs = sorted(p for d in dirs for ext in ("*.bmp", "*.png", "*.jpg", "*.jpeg")
                  for p in Path(d).glob(ext))
    if limit:
        imgs = imgs[:limit]
    total = len(imgs)
    print(f"Rastrerar {total} bilder ...", flush=True)
    t0 = time.time()
    n = 0
    for i, img_path in enumerate(imgs, 1):
        stem = img_path.stem
        im = Image.open(img_path).convert("RGB")
        w, h = im.size
        if semantic_dir is not None:
            sem = _find(Path(semantic_dir), stem, (".bmp", ".png"), SEMANTIC_SUFFIXES)
            if sem is None:
                continue
            mask = rasterize_semantic(sem, color_map or {})
        else:
            box = _find(Path(bbox_dir), stem, (".txt",), BBOX_SUFFIXES)
            if box is None:
                continue
            mask = rasterize_bboxes(box, h, w)
        im.save(out_root / "images" / f"{stem}.png")
        Image.fromarray(mask, "L").save(out_root / "masks" / f"{stem}.png")
        n += 1
        if i % 500 == 0 or i == total:
            el = time.time() - t0
            rate = i / el if el else 0
            eta = (total - i) / rate / 60 if rate else 0
            print(f"  {i}/{total}  ({n} par · {rate:.1f} bild/s · ETA {eta:.1f} min)", flush=True)
    return n


def _find(d: Path, stem: str, exts, suffixes=("",)):
    """Hittar d/<stem><suffix><ext> (prövar suffixen i ordning)."""
    for suf in suffixes:
        for e in exts:
            p = d / f"{stem}{suf}{e}"
            if p.exists():
                return p
    return None


def _pairs(semantic_dir, bbox_dir):
    """(semantisk karta, bbox-fil)-par via gemensam bas-stam (strippar _segm)."""
    sd, bd = Path(semantic_dir), Path(bbox_dir)
    out = []
    for sem in sorted(p for e in ("*.bmp", "*.png") for p in sd.glob(e)):
        base = re.sub(r"_segm$", "", sem.stem)
        box = _find(bd, base, (".txt",), BBOX_SUFFIXES)
        if box:
            out.append((sem, box))
    return out


def auto_discover(root):
    """Hittar (image_dirs, semantic, bbox) i en uppackad Kodytek-mapp.

    Robust mot Kodyteks layout: bilderna ligger i flera Images*-mappar, kartorna
    i 'Semantic Maps' (<id>_segm.bmp) och boxarna i 'Bouding Boxes' (<id>_anno.txt).
    image_dirs returneras som LISTA så alla bildmappar slås ihop."""
    root = Path(root)
    dirs = [root] + [p for p in sorted(root.rglob("*")) if p.is_dir()]
    def has(d, *pats):
        return any(next(d.glob(p), None) for p in pats)
    is_sem = lambda d: bool(re.search(r"semant|\bmap", d.name, re.I))
    semantic = next((d for d in dirs if is_sem(d) and has(d, "*.bmp", "*.png")), None) \
        or next((d for d in dirs if has(d, "*_segm.bmp", "*_segm.png")), None)
    bbox = next((d for d in dirs if re.search(r"bound|\bbox", d.name, re.I) and has(d, "*.txt")), None) \
        or next((d for d in dirs if has(d, "*_anno.txt")), None)
    image_dirs = [d for d in dirs
                  if has(d, "*.bmp", "*.png") and d != semantic and not is_sem(d)]
    return image_dirs, semantic, bbox


def main():
    ap = argparse.ArgumentParser(description="Rastrera Kodytek -> klass-id-masker")
    ap.add_argument("--auto", help="uppackad Kodytek-root; hittar under-kataloger själv")
    ap.add_argument("--images", help="katalog med Kodytek-bilder")
    ap.add_argument("--out", required=True, help="utdata-root (images/ + masks/)")
    ap.add_argument("--semantic", help="katalog med semantiska kartor (BMP)")
    ap.add_argument("--bboxes", help="katalog med bbox-textfiler")
    ap.add_argument("--color-map", help="JSON packad-färg->GUI-klass (annars auto)")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    images = [a.images] if a.images else None
    if a.auto:
        img_dirs, sem, box = auto_discover(a.auto)
        images = images or [str(p) for p in img_dirs]
        a.semantic = a.semantic or (str(sem) if sem else None)
        a.bboxes = a.bboxes or (str(box) if box else None)
        print(f"Auto: {len(img_dirs)} bildmappar\n      semantic={a.semantic}\n      bboxes={a.bboxes}")
    if not images:
        raise SystemExit("Hittade inga bilder. Ange --images eller --auto <root>.")

    color_map = None
    if a.semantic:
        if a.color_map:
            color_map = {int(k): int(v) for k, v in json.load(open(a.color_map)).items()}
        elif a.bboxes:
            print("Auto-härleder färg→klass ur bbox+semantik ...")
            color_map = derive_color_map(_pairs(a.semantic, a.bboxes))
            from .config import CLASSES
            covered = sorted(set(color_map.values()))
            print(f"  hittade {len(color_map)} defektfärger -> klasser "
                  f"{[CLASSES[g] for g in covered]}")
            missing = [CLASSES[g] for g in range(1, 7) if g not in covered]
            if missing:
                print(f"  VARNING: saknar färg för {missing} (finns ev. inte i datan)")
        else:
            raise SystemExit("Semantisk rastrering kräver --color-map eller --bboxes")

    n = build_dataset(images, a.out, semantic_dir=a.semantic,
                      bbox_dir=a.bboxes, color_map=color_map, limit=a.limit)
    print(f"Klart: {n} bild/mask-par -> {a.out}")


if __name__ == "__main__":
    main()
