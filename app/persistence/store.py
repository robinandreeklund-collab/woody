"""Persistens — per bräda loggas resultat till SQLite + valfritt yt-bildarkiv.

Robust: får aldrig stoppa drift (anropas i try/except från controllern). Ger en
sökbar historik och CSV-export. Bilder sparas som PNG om Qt finns tillgängligt.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path


class BoardStore:
    def __init__(self, db_path: str | Path = "data/woody.db", save_images: bool = False):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.img_dir = self.path.parent / "boards"
        self.save_images = save_images
        if save_images:
            self.img_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path))
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS boards (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        TEXT NOT NULL,
                n         INTEGER,
                cls       TEXT,
                title     TEXT,
                score     INTEGER,
                n_defects INTEGER,
                n_vision  INTEGER,
                defects   TEXT,
                image     TEXT
            )""")
        self._db.commit()

    def log_board(self, entry: dict, defects: list, board=None) -> None:
        img_path = ""
        if self.save_images and board is not None:
            img_path = self._save_image(board, entry.get("n", 0))
        self._db.execute(
            "INSERT INTO boards (ts,n,cls,title,score,n_defects,n_vision,defects,image)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), entry.get("n"),
             entry.get("cls"), entry.get("title"), entry.get("score"),
             entry.get("ndef"), entry.get("nvision", 0),
             json.dumps([{k: d[k] for k in ("type", "x", "y") if k in d} for d in defects]),
             img_path))
        self._db.commit()

    def _save_image(self, board, n: int) -> str:
        try:
            from PySide6.QtGui import QImage
            import numpy as np
            a = np.ascontiguousarray(board.surface)
            h, w, _ = a.shape
            img = QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
            p = self.img_dir / f"board_{n:05d}.png"
            img.save(str(p))
            return str(p)
        except Exception:
            return ""

    def recent(self, limit: int = 200) -> list:
        cur = self._db.execute(
            "SELECT n,ts,cls,title,score,n_defects,n_vision FROM boards ORDER BY id DESC LIMIT ?",
            (limit,))
        cols = ["n", "ts", "cls", "title", "score", "ndef", "nvision"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def stats(self) -> dict:
        cur = self._db.execute("SELECT cls, COUNT(*) FROM boards GROUP BY cls")
        return {row[0]: row[1] for row in cur.fetchall()}

    def export_csv(self, csv_path: str | Path | None = None) -> Path:
        if csv_path is None:
            csv_path = self.path.parent / f"export_{datetime.now():%Y%m%d_%H%M%S}.csv"
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        rows = self._db.execute(
            "SELECT ts,n,cls,title,score,n_defects,n_vision FROM boards ORDER BY id").fetchall()
        with open(csv_path, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["tid", "nr", "klass", "titel", "poäng", "defekter", "vision"])
            wr.writerows(rows)
        return csv_path

    def close(self):
        self._db.close()
