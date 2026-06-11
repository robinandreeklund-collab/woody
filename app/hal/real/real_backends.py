"""RealScanner — verklig hårdvara via HAL-gränssnitten (LÅST hårdvara).

Knyter ihop profilkamerorna (Hikrobot MV-CS050-10UM, GenICam/USB3), linjekameran
(HT-GELM44C-T2, GenICam/GigE), **3× punktlaser LR400** (RS-485 Modbus via Waveshare
USB→4CH, ch1–3) och transportören (**RoboClaw 2x7A**, USB packet serial). Enligt
prototype-wiring.svg: punktlasrarna ger ABSOLUT tjocklek och ankrar trianguleringens
globala offset/tilt (se fusion.anchor) — de kompletterar profilkamerorna, ersätts inte.
open() ansluter varje enhet och rapporterar status utan att krascha om en SDK/enhet
saknas (bring-up i Fas C).

Behandlingspipelinen är densamma som i sim — den läser via dessa gränssnitt.
Det som återstår för full drift är encoder-triggad radackumulering → bräd-bild
(geometri/kalibrering), markerat nedan.
"""
from __future__ import annotations

from ..base import Scanner
from ...geometry import RIG
from .cameras import GenICamProfileCamera, GenICamSurfaceCamera
from .lr400_modbus import LR400ModbusLaser
from .roboclaw_conveyor import RoboClawConveyor


class RealScanner(Scanner):
    def __init__(self, cfg=None):
        self.profile_red = GenICamProfileCamera("red")
        self.profile_green = GenICamProfileCamera("green")
        self.surface = GenICamSurfaceCamera()
        # 3× LR400 över RS-485 Modbus (Waveshare 4CH ch1–3) — absolut tjocklek-ankare
        self.point_lasers = [LR400ModbusLaser(i, x, unit=i + 1)
                             for i, x in enumerate(RIG.point_lasers_x_mm)]
        self.conveyor = RoboClawConveyor()
        self._board = None

    def open(self) -> None:
        for d in self.devices():
            try:
                d.open()
            except Exception as exc:
                print(f"[HAL] {d.info().name}: EJ ansluten — {exc}")

    def connect_report(self) -> list:
        rep = []
        for d in self.devices():
            try:
                d.open(); ok, msg = True, "ansluten"
            except Exception as exc:
                ok, msg = False, str(exc)
            rep.append((d.info().name, ok, msg))
        return rep

    # I verkligt läge styrs bräd-livscykeln av brädnärvaro/encoder. Radackumulering
    # → bräd-bild byggs i Fas 4 (kräver encoder-trigger + kalibrering).
    def new_board(self) -> None:
        self._board = None

    def board(self):
        return self._board

    def devices(self) -> list:
        return [self.profile_red, self.profile_green, self.surface,
                *self.point_lasers, self.conveyor]
