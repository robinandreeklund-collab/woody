#!/usr/bin/env python3
"""Offscreen-smoke: ladda en QML-rot (master eller lokal) utan display och
verifiera att den PARSAR + binder utan fel. Avslutar direkt (200 ms).

    QT_QPA_PLATFORM=offscreen python tools/qml_smoke.py master
    QT_QPA_PLATFORM=offscreen python tools/qml_smoke.py local

Fångar QML-varningar/fel via en message-handler → exit 1 om något skrek.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QUrl, QTimer, qInstallMessageHandler, QtMsgType
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

_ERRORS: list[str] = []


def _handler(mode, ctx, msg):
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        # filtrera bort kända offscreen-bruskällor (RHI/GPU saknas headless)
        if any(s in msg for s in ("Quick3D", "RHI", "QRhi", "createRhi", "No QQmlEngine")):
            return
        _ERRORS.append(msg)
    print(msg, file=sys.stderr)


def main(argv):
    which = argv[1] if len(argv) > 1 else "master"
    qInstallMessageHandler(_handler)
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    root = Path(__file__).resolve().parent.parent / "app" / "ui" / "qml"

    if which == "comp":
        # parsa en enskild komponent (node/ctrl = null) via en temp-wrapper
        comp = argv[2] if len(argv) > 2 else "ScanView"
        wrap = root / "_smoke_wrap.qml"
        wrap.write_text(
            'import QtQuick\nimport QtQuick.Window\n'
            'Window { width: 1200; height: 800; visible: true\n'
            f'  {comp} {{ anchors.fill: parent }} }}\n')
        engine.rootContext().setContextProperty("quick3dAvailable", False)
        try:
            engine.load(QUrl.fromLocalFile(str(wrap)))
            ok = bool(engine.rootObjects())
        finally:
            wrap.unlink(missing_ok=True)
        if not ok:
            print("FEL: komponenten kunde inte laddas", file=sys.stderr)
            return 2
        QTimer.singleShot(250, app.quit); app.exec()
        if _ERRORS:
            print(f"\n✗ {len(_ERRORS)} QML-fel/varningar", file=sys.stderr); return 1
        print(f"✓ {comp} laddade rent (offscreen)"); return 0

    if which == "master":
        from app.net.node_manager import NodeManager
        from app.net.remote_image_provider import RemoteImageProvider
        nm = NodeManager()
        engine.addImageProvider("remote", RemoteImageProvider(nm))
        engine.rootContext().setContextProperty("nodeManager", nm)
        engine.rootContext().setContextProperty("startFullscreen", False)
        engine.rootContext().setContextProperty("quick3dAvailable", False)
        qml = root / "MasterMain.qml"
    else:
        from app.core.config import AppConfig
        from app.core.run_controller import AppController
        from app.core.devices import DeviceManager
        from app.ui.image_provider import LiveImageProvider
        cfg = AppConfig(); cfg.mode = "sim"
        prov = LiveImageProvider()
        engine.addImageProvider("live", prov)
        ctrl = AppController(cfg, prov)
        engine.rootContext().setContextProperty("ctrl", ctrl)
        engine.rootContext().setContextProperty("devmgr", DeviceManager(cfg, scanner=ctrl._scanner))
        engine.rootContext().setContextProperty("startFullscreen", False)
        engine.rootContext().setContextProperty("quick3dAvailable", False)
        qml = root / "Main.qml"

    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        print("FEL: roten kunde inte laddas", file=sys.stderr)
        return 2
    QTimer.singleShot(250, app.quit)
    app.exec()
    if _ERRORS:
        print(f"\n✗ {len(_ERRORS)} QML-fel/varningar", file=sys.stderr)
        return 1
    print(f"✓ {qml.name} laddade rent (offscreen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
