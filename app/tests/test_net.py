"""Master/slave-nätverk: protokoll, kommandohanterare och full loopback (sim).

Kör:  python -m app.tests.test_net
"""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QCoreApplication

from ..net import protocol as p

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)


def _pump(predicate, timeout=4.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        _app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return False


# ----------------------------------------------------------------- protokoll
def test_protocol_framing():
    fb = p.FrameBuffer()
    # två hela meddelanden + en delad svans
    data = p.encode({"a": 1}) + p.encode({"b": 2})
    msgs = fb.feed(data[:5]) + fb.feed(data[5:])
    assert {"a": 1} in msgs and {"b": 2} in msgs
    # trasig rad hoppas, giltig efteråt tas
    out = fb.feed(b"{trasig}\n" + p.encode({"c": 3}))
    assert {"c": 3} in out
    # hjälpfunktionerna
    import json
    assert json.loads(p.request(7, "x", {"k": 1}).decode())["cmd"] == "x"
    assert json.loads(p.response(7, [1, 2]).decode())["result"] == [1, 2]
    assert json.loads(p.event("e", {"d": 1}).decode())["event"] == "e"


# ----------------------------------------------------------- kommandohanterare
def test_command_handler_sim():
    from ..core.config import AppConfig
    from ..core.devices import DeviceManager
    from ..net.command_handler import CommandHandler
    dm = DeviceManager(AppConfig(mode="sim"))
    h = CommandHandler(dm, name="testnod")
    assert h.handle({"id": 1, "cmd": p.CMD_HELLO})["result"]["mode"] == "sim"
    devs = h.handle({"id": 2, "cmd": p.CMD_DEVICES})["result"]
    assert isinstance(devs, list) and any(d["id"] == "prof_red" for d in devs)
    methods = h.handle({"id": 3, "cmd": p.CMD_METHODS, "args": {"dev": "prof_red"}})["result"]
    assert any(m["id"] == "exposure" for m in methods)
    started = h.handle({"id": 4, "cmd": p.CMD_START_CALIB,
                        "args": {"dev": "prof_red", "method": "exposure"}})
    assert started["ok"] and started["result"] is True
    st = h.handle({"id": 5, "cmd": p.CMD_CALIB_STATE})["result"]
    assert st["running"] is True and st["device"] == "prof_red"
    dm.cancelCalibration()
    # okänt kommando → ok=False, ingen krasch
    assert h.handle({"id": 6, "cmd": "nonsens"})["ok"] is False


# ------------------------------------------------------------- full loopback
def test_loopback_master_slave():
    from ..core.config import AppConfig
    from ..core.devices import DeviceManager
    from ..net.slave_server import SlaveServer
    from ..net.remote_node import RemoteNode

    dm = DeviceManager(AppConfig(mode="sim"))
    server = SlaveServer(dm, name="loop-nod", port=0)         # port 0 = valfri ledig
    assert server.listen()
    port = server._server.serverPort()

    node = RemoteNode("loop-nod", "127.0.0.1", port)
    node.connectNode()
    assert _pump(lambda: node.connected), "RemoteNode anslöt aldrig"
    assert _pump(lambda: len(node.devices) > 0), "fick aldrig enhetslistan"
    assert node.mode == "sim"
    assert any(d["id"] == "prof_red" for d in node.devices)

    # methodsFor: första anropet tomt (begär async) → cache fylls via event
    node.methodsFor("prof_red")
    assert _pump(lambda: len(node.methodsFor("prof_red")) > 0), "fick aldrig metoder"

    # starta kalibrering på distans → progress strömmar tillbaka
    node.startCalibration("prof_red", "dark")
    assert _pump(lambda: node.calibRunning), "kalibrering startade inte på distans"
    assert node.calibDevice == "prof_red"
    node.cancelCalibration()
    server._server.close()


def test_head_config_position():
    from ..net import head_config
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "head.json"
        assert head_config.load(p)["label"] == ""           # defaults när filen saknas
        head_config.save({"label": "Vänster", "start_mm": 0, "end_mm": 250}, p)
        c = head_config.load(p)
        assert c["label"] == "Vänster" and c["start_mm"] == 0.0 and c["end_mm"] == 250.0


def test_command_handler_set_position():
    from ..core.config import AppConfig
    from ..core.devices import DeviceManager
    from ..net.command_handler import CommandHandler
    from ..net import head_config
    saved = head_config.save
    head_config.save = lambda cfg, *a, **k: {                # mät utan att skriva repo-fil
        "label": str(cfg.get("label", "")),
        "start_mm": float(cfg.get("start_mm", 0)), "end_mm": float(cfg.get("end_mm", 0))}
    try:
        h = CommandHandler(DeviceManager(AppConfig(mode="sim")), name="x")
        assert "position" in h.handle({"id": 1, "cmd": p.CMD_STATUS})["result"]
        res = h.handle({"id": 2, "cmd": p.CMD_SET_POSITION,
                        "args": {"label": "Mitten", "start_mm": 100, "end_mm": 350}})
        assert res["ok"] and res["result"]["label"] == "Mitten"
        st = h.handle({"id": 3, "cmd": p.CMD_STATUS})["result"]
        assert st["position"]["label"] == "Mitten" and st["position"]["end_mm"] == 350.0
    finally:
        head_config.save = saved


def test_discovery_parse():
    from ..net import discovery as d
    info = d.parse_announce(d.announce_packet("rod", 8765, "real"), "10.0.0.5")
    assert info["name"] == "rod" and info["host"] == "10.0.0.5"
    assert info["port"] == 8765 and info["mode"] == "real"
    assert d.parse_announce(b"garbage", "x") is None
    assert d.parse_announce(b'{"magic":"fel"}', "x") is None


def test_discovery_listener_receives():
    from ..net import discovery as d
    from PySide6.QtNetwork import QHostAddress, QUdpSocket
    lis = d.DiscoveryListener()
    if not lis.start():
        print("    (UDP-porten upptagen — hoppar listener-test)"); return
    got = []
    lis.discovered.connect(lambda name, host, port, mode: got.append((name, port)))
    s = QUdpSocket()
    s.writeDatagram(d.announce_packet("testnod", 8765, "sim"),
                    QHostAddress("127.0.0.1"), d.DISCOVERY_PORT)
    assert _pump(lambda: len(got) > 0), "listener fick ingen annons"
    assert got[0] == ("testnod", 8765)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  ✓ {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  ✗ {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(fns)} tester gröna")
    raise SystemExit(0 if ok == len(fns) else 1)
