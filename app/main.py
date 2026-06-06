"""VIRKE kontrollsystem — entry point (PySide6 + QML).

    python -m app.main                 # simulering (standard), fönster
    python -m app.main --mode sim
    python -m app.main --fullscreen    # kiosk på bänken
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .core.config import AppConfig
from .core.run_controller import AppController
from .ui.image_provider import LiveImageProvider


def parse_args(argv=None) -> AppConfig:
    p = argparse.ArgumentParser(description="VIRKE kontrollsystem")
    p.add_argument("--mode", choices=["sim", "real"], default="sim")
    p.add_argument("--feed", type=float, default=50.0, help="matning mm/s")
    p.add_argument("--rate", type=float, default=500.0, help="profiltakt Hz")
    p.add_argument("--fullscreen", action="store_true")
    p.add_argument("--db", default="data/woody.db", help="SQLite-loggfil")
    p.add_argument("--no-store", action="store_true", help="logga inte till disk")
    p.add_argument("--save-images", action="store_true", help="spara yt-bild per bräda")
    a = p.parse_args(argv)
    cfg = AppConfig(mode=a.mode, feed_mm_s=a.feed, profile_rate_hz=a.rate,
                    fullscreen=a.fullscreen).validate()
    cfg._db = None if a.no_store else a.db
    cfg._save_images = a.save_images
    return cfg


def main(argv=None) -> int:
    cfg = parse_args(argv)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("VIRKE Kontrollsystem")

    engine = QQmlApplicationEngine()
    provider = LiveImageProvider()
    engine.addImageProvider("live", provider)

    controller = AppController(cfg, provider)
    if getattr(cfg, "_db", None):
        try:
            from .persistence.store import BoardStore
            controller.set_store(BoardStore(cfg._db, save_images=getattr(cfg, "_save_images", False)))
        except Exception as exc:
            print("persistens av:", exc)
    engine.rootContext().setContextProperty("ctrl", controller)
    engine.rootContext().setContextProperty("startFullscreen", cfg.fullscreen)

    qml = Path(__file__).parent / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        print("FEL: kunde inte ladda QML", file=sys.stderr)
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
