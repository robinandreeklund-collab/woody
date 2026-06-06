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
    p.add_argument("--probe", action="store_true", help="testa hårdvaruanslutning (real) och avsluta")
    a = p.parse_args(argv)
    cfg = AppConfig(mode=a.mode, feed_mm_s=a.feed, profile_rate_hz=a.rate,
                    fullscreen=a.fullscreen).validate()
    cfg._db = None if a.no_store else a.db
    cfg._save_images = a.save_images
    cfg._probe = a.probe
    return cfg


def probe(cfg: AppConfig) -> int:
    """Testa hårdvaruanslutning och skriv en rapport (bring-up)."""
    from .hal.factory import build_scanner
    scanner = build_scanner(cfg)
    if not hasattr(scanner, "connect_report"):
        print("Probe stöds bara i --mode real."); return 1
    print(f"\nHårdvaruprobe ({cfg.mode}):")
    ok_all = True
    for name, ok, msg in scanner.connect_report():
        print(f"  [{'OK ' if ok else 'FEL'}] {name:28} {msg}")
        ok_all = ok_all and ok
    print("Klart." if ok_all else "Vissa enheter saknas/SDK ej installerad — se docs/jetson-setup.md.")
    return 0 if ok_all else 2


def main(argv=None) -> int:
    cfg = parse_args(argv)
    if getattr(cfg, "_probe", False):
        return probe(cfg)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("VIRKE Kontrollsystem")

    engine = QQmlApplicationEngine()
    provider = LiveImageProvider()
    engine.addImageProvider("live", provider)

    # Qt Quick 3D (GPU) för 3D-vyn — registrera geometrin + känn av om den kan rendera.
    # I offscreen/headless saknas RHI → fall tillbaka till software-3D (Canvas).
    quick3d = False
    if app.platformName() != "offscreen":
        try:
            import PySide6.QtQuick3D  # noqa: F401
            from PySide6.QtQml import qmlRegisterType
            from .ui.board_geometry import BoardGeometry
            qmlRegisterType(BoardGeometry, "Woody3D", 1, 0, "BoardGeometry")
            quick3d = True
        except Exception as exc:
            print("Qt Quick 3D ej tillgängligt (software-3D används):", exc)
    engine.rootContext().setContextProperty("quick3dAvailable", quick3d)

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
