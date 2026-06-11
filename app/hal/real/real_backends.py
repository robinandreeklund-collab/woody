"""RealScanner — verklig hårdvara via HAL-gränssnitten (LÅST hårdvara).

Knyter ihop profilkamerorna (Hikrobot MV-CS050-10UM, GenICam/USB3), linjekameran
(HT-GELM44C-T2, GenICam/GigE) och transportören (**RoboClaw 2x7A**, USB packet
serial). Tjocklek/kant kommer ur profilkamerornas LASERTRIANGULERING — de tidigare
LR400-punktlasrarna är UTGÅNGNA ur designen (``point_lasers`` lämnas tom; se
docs/jetson-prep-plan.md §4). open() ansluter varje enhet och rapporterar status
utan att krascha om en SDK/enhet saknas (bring-up i Fas C).

Behandlingspipelinen är densamma som i sim — den läser via dessa gränssnitt.
Det som återstår för full drift är encoder-triggad radackumulering → bräd-bild
(geometri/kalibrering), markerat nedan.
"""
from __future__ import annotations

from ..base import Scanner
from .cameras import GenICamProfileCamera, GenICamSurfaceCamera
from .roboclaw_conveyor import RoboClawConveyor


class RealScanner(Scanner):
    def __init__(self, cfg=None):
        self.profile_red = GenICamProfileCamera("red")
        self.profile_green = GenICamProfileCamera("green")
        self.surface = GenICamSurfaceCamera()
        # tjocklek/kant fås ur profilkamerornas triangulering — inga punktlasrar
        self.point_lasers = []
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
