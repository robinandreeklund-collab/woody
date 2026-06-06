"""Transportör via Pololu Jrk G2 (USB seriell kommando-gränssnitt).

Jrk G2 styrs med dess binära kommandon (Set Target 0xC0..). Hastighet (mm/s) →
mål via en kalibrerad skala. Feedback/position läses ur 'Scaled Feedback'.
pyserial importeras lazy.
"""
from __future__ import annotations

import struct

from ..base import ConveyorIF, DeviceInfo


class JrkConveyor(ConveyorIF):
    def __init__(self, port: str = "/dev/ttyACM0", counts_per_mm: float = 20.0,
                 target_per_mm_s: float = 40.0):
        self._port = port
        self._counts_per_mm = counts_per_mm        # encoder → mm (kalibreras)
        self._target_per_mm_s = target_per_mm_s    # mm/s → Jrk-mål (kalibreras)
        self._ser = None
        self._connected = False
        self._zero_counts = 0

    def info(self) -> DeviceInfo:
        return DeviceInfo("Transportör", "Pololu Jrk G2", "USB", self._connected)

    def open(self) -> None:
        import serial                                # lazy
        self._ser = serial.Serial(self._port, baudrate=9600, timeout=0.1)
        self._connected = True
        self._zero_counts = self._read_feedback()

    def set_speed(self, mm_s: float) -> None:
        if not self._connected:
            return
        target = int(max(0, min(4095, 2048 + mm_s * self._target_per_mm_s)))
        # Jrk G2 "Set Target": 0xC0 + low 5 bits, high 7 bits
        self._ser.write(bytes([0xC0 + (target & 0x1F), (target >> 5) & 0x7F]))

    def _read_feedback(self) -> int:
        if not self._connected:
            return 0
        # "Get Variables": kommando 0xE5, offset 'Scaled Feedback' (2 byte)
        self._ser.write(bytes([0xE5, 0x02, 0x02]))
        data = self._ser.read(2)
        return struct.unpack("<H", data)[0] if len(data) == 2 else 0

    def position_mm(self) -> float:
        return (self._read_feedback() - self._zero_counts) / self._counts_per_mm

    def close(self) -> None:
        if self._ser:
            self.set_speed(0.0)
            self._ser.close()
        self._connected = False
