"""Slave-entrypoint: kör på varje Jetson (läshuvud) och exponerar dess sensorer
+ kalibrering över nätet för master-desktopen.

    python -m app.net.slave --mode real --name woody-rod --port 8765
    python -m app.net.slave --mode sim                       # test utan hårdvara

Headless (QCoreApplication, ingen GUI). Mastern ansluter via data/nodes.json.
"""
from __future__ import annotations

import argparse
import socket
import sys

from PySide6.QtCore import QCoreApplication

from ..core.config import AppConfig
from ..core.devices import DeviceManager
from ..core.run_controller import AppController
from .slave_server import SlaveServer


class _NoSurface:
    """No-op bild-provider — slaven kör headless (ingen QML-bildcache)."""
    def set_array(self, *a, **k):
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sim", "real"], default="real")
    ap.add_argument("--name", default=socket.gethostname(), help="nodnamn i master-GUI:t")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--feed", type=float, default=50.0)
    ap.add_argument("--no-announce", action="store_true",
                    help="stäng av UDP-broadcast (auto-upptäckt) — använd manuell nodes.json")
    args = ap.parse_args(argv)

    app = QCoreApplication(sys.argv)
    cfg = AppConfig(mode=args.mode, feed_mm_s=args.feed).validate()
    # AppController bygger skannern; DeviceManager DELAR den (en scanner per nod)
    ctrl = AppController(cfg, _NoSurface())
    devmgr = DeviceManager(cfg, scanner=ctrl._scanner)
    ctrl.start()                                  # startar skannings-loopen (sim/real)
    server = SlaveServer(devmgr, name=args.name, port=args.port, controller=ctrl)
    if not server.listen():
        return 1
    beacon = None
    if not args.no_announce:
        from .discovery import DiscoveryBeacon
        beacon = DiscoveryBeacon(args.name, args.port, mode=args.mode)
        beacon.start()
        print(f"[slave] auto-annonserar '{args.name}' på LAN (UDP-broadcast)")
    print(f"[slave] redo som '{args.name}' — master hittar oss automatiskt (eller nodes.json)")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
