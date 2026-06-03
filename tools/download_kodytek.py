"""Laddar ner Kodytek-datasetet från Zenodo (record 4694695) och packar upp.

Datasetet är stort (flera GB). Körs lokalt. Endast standardbibliotek.

    python tools/download_kodytek.py --out data/kodytek_raw [--limit-files N]

Resultatet (uppackat) pekas sedan av src.kodytek för rastrering.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

RECORD = "4694695"
API = f"https://zenodo.org/api/records/{RECORD}"


def _get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def _download(url, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  finns redan: {dest.name}")
        return
    print(f"  hämtar {dest.name} ...")
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = 100 * done / total
                sys.stdout.write(f"\r    {done/1e6:.0f}/{total/1e6:.0f} MB ({pct:.0f}%)")
                sys.stdout.flush()
    sys.stdout.write("\n")
    tmp.rename(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/kodytek_raw")
    ap.add_argument("--limit-files", type=int, default=0,
                    help="ladda bara N filer (för test)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Hämtar Zenodo-record {RECORD} ...")
    rec = _get_json(API)
    files = rec.get("files", [])
    if a.limit_files:
        files = files[: a.limit_files]
    print(f"{len(files)} filer att hämta till {out}/")

    for f in files:
        key = f.get("key") or f["links"]["self"].split("/")[-1]
        url = f["links"]["self"]
        dest = out / key
        _download(url, dest)
        if dest.suffix.lower() == ".zip":
            print(f"  packar upp {dest.name} ...")
            with zipfile.ZipFile(dest) as z:
                z.extractall(out)

    print(f"Klart -> {out}")
    print("Nästa: rastrera med  python -m src.kodytek --images <…> --semantic <…> "
          "--bboxes <…> --out data/kodytek")


if __name__ == "__main__":
    main()
