"""Delad transportör för SENSOR-huvuden — encodern/motorn ägs av lead-noden.

Vid flera läshuvuden finns bara EN RoboClaw + EN encoder (på lead-noden). Sensor-
huvuden bygger ingen egen RoboClaw; de använder den här klienten som:
  * ``set_speed`` = no-op (bara lead-noden driver motorn),
  * ``position_mm`` = senast inmatade matningsposition (matas av lead via nät-sync,
    eller av encoderns hårdvarutrigg på linjekameran — samma delade koordinat).

Det ger fusion en GEMENSAM koordinat över alla huvuden utan att duplicera motorn.
"""
from __future__ import annotations

from ..base import ConveyorIF, DeviceInfo


class SharedConveyorClient(ConveyorIF):
    def __init__(self):
        self._pos = 0.0
        self._connected = False

    def info(self) -> DeviceInfo:
        return DeviceInfo("Transportör (delad · lead-nod)", "RoboClaw på lead",
                          "delad encoder/motor", self._connected)

    def open(self) -> None:
        self._connected = True            # ingen egen hårdvara att öppna

    def set_speed(self, mm_s: float) -> None:
        pass                              # bara lead-noden driver motorn

    def position_mm(self) -> float:
        return self._pos

    def set_feed_position(self, mm: float) -> None:
        """Matas av lead-noden (nät-sync) — den gemensamma matningskoordinaten."""
        self._pos = float(mm)

    def close(self) -> None:
        self._connected = False
