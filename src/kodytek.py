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


def derive_color_map(pairs, max_images: int = 200) -> dict:
    """Auto-härleder packad färg -> GUI-klass ur (semantic_bmp, bbox_txt)-par.
    För varje box (känd etikett) röstar den dominerande icke-bakgrundsfärgen i
    boxen på den klassen. Bakgrund = globalt vanligaste färgen."""
    from PIL import Image
    votes = defaultdict(Counter)
    bg_counter = Counter()
    for sem_path, box_path in pairs[:max_images]:
        sem = np.asarray(Image.open(sem_path).convert("RGB"))
        q = _quantize(sem)
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
                col = int(np.bincount(sub).argmax())
                votes[col][gid] += 1
    bg = bg_counter.most_common(1)[0][0] if bg_counter else -1
    color_map = {}
    for col, c in votes.items():
        if col == bg:
            continue
        color_map[col] = c.most_common(1)[0][0]
    return color_map


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
    """Skriver out_root/images/<namn>.png + out_root/masks/<namn>.png."""
    from PIL import Image
    images_dir = Path(images_dir)
    out_root = Path(out_root)
    (out_root / "images").mkdir(parents=True, exist_ok=True)
    (out_root / "masks").mkdir(parents=True, exist_ok=True)

    imgs = sorted(p for ext in ("*.bmp", "*.png", "*.jpg", "*.jpeg")
                  for p in images_dir.glob(ext))
    if limit:
        imgs = imgs[:limit]
    n = 0
    for img_path in imgs:
        stem = img_path.stem
        im = Image.open(img_path).convert("RGB")
        w, h = im.size
        if semantic_dir is not None:
            sem = _find(Path(semantic_dir), stem, (".bmp", ".png"))
            if sem is None:
                continue
            mask = rasterize_semantic(sem, color_map or {})
        else:
            box = _find(Path(bbox_dir), stem, (".txt",))
            if box is None:
                continue
            mask = rasterize_bboxes(box, h, w)
        im.save(out_root / "images" / f"{stem}.png")
        Image.fromarray(mask, "L").save(out_root / "masks" / f"{stem}.png")
        n += 1
    return n


def _find(d: Path, stem: str, exts):
    for e in exts:
        p = d / f"{stem}{e}"
        if p.exists():
            return p
    return None


def _pairs(semantic_dir, bbox_dir):
    sd, bd = Path(semantic_dir), Path(bbox_dir)
    out = []
    for sem in sorted(p for e in ("*.bmp", "*.png") for p in sd.glob(e)):
        box = _find(bd, sem.stem, (".txt",))
        if box:
            out.append((sem, box))
    return out


def auto_discover(root):
    """Hittar (images, semantic, bbox)-kataloger i en uppackad Kodytek-mapp."""
    root = Path(root)
    dirs = [p for p in root.rglob("*") if p.is_dir()]
    dirs.append(root)
    def name_match(pats):
        for d in dirs:
            if any(re.search(p, d.name, re.I) for p in pats):
                if any(d.glob(e) for e in ("*.bmp", "*.png", "*.txt")):
                    return d
        return None
    images = name_match([r"image"]) or next(
        (d for d in dirs if list(d.glob("*.bmp")) or list(d.glob("*.png"))), None)
    semantic = name_match([r"semant", r"\bmap"])
    bbox = name_match([r"bound", r"bbox", r"\bbox"])
    return images, semantic, bbox


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

    if a.auto:
        img, sem, box = auto_discover(a.auto)
        a.images = a.images or (str(img) if img else None)
        a.semantic = a.semantic or (str(sem) if sem else None)
        a.bboxes = a.bboxes or (str(box) if box else None)
        print(f"Auto: images={a.images}\n      semantic={a.semantic}\n      bboxes={a.bboxes}")
    if not a.images:
        raise SystemExit("Hittade inga bilder. Ange --images eller --auto <root>.")

    color_map = None
    if a.semantic:
        if a.color_map:
            color_map = {int(k): int(v) for k, v in json.load(open(a.color_map)).items()}
        elif a.bboxes:
            print("Auto-härleder färg→klass ur bbox+semantik ...")
            color_map = derive_color_map(_pairs(a.semantic, a.bboxes))
            print(f"  hittade {len(color_map)} defektfärger")
        else:
            raise SystemExit("Semantisk rastrering kräver --color-map eller --bboxes")

    n = build_dataset(a.images, a.out, semantic_dir=a.semantic,
                      bbox_dir=a.bboxes, color_map=color_map, limit=a.limit)
    print(f"Klart: {n} bild/mask-par -> {a.out}")


if __name__ == "__main__":
    main()
