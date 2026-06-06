"""LR400 punktlaser över RS-485 (Modbus RTU) via Waveshare USB→4CH.

Varje LR400 läses som ett holding-register (avstånd i 0,01 mm). Tjocklek =
referensavstånd − uppmätt avstånd (sätts vid nollning, se kalibrering). SDK:t
(pymodbus) importeras lazy så att appen startar utan biblioteket installerat.
"""
from __future__ import annotations

from ..base import DeviceInfo, PointLaserIF
from ...geometry import RIG


class LR400ModbusLaser(PointLaserIF):
    def __init__(self, idx: int, x_mm: float, port: str = "/dev/ttyUSB0",
                 unit: int = 1, baud: int = 9600, ref_mm: float = 100.0):
        self._idx, self._x = idx, x_mm
        self._port, self._unit, self._baud = port, unit, baud
        self._ref = ref_mm          # referensavstånd vid nominell tjocklek (kalibreras)
        self._client = None
        self._connected = False

    def info(self) -> DeviceInfo:
        return DeviceInfo(f"Punktlaser LR-{['V', 'C', 'H'][self._idx]}",
                          "LR400", f"RS-485 ch{self._idx + 1}", self._connected)

    def open(self) -> None:
        from pymodbus.client import ModbusSerialClient    # lazy
        self._client = ModbusSerialClient(port=self._port, baudrate=self._baud,
                                          parity="N", stopbits=1, bytesize=8, timeout=0.1)
        self._connected = self._client.connect()
        if not self._connected:
            raise RuntimeError(f"LR400 ch{self._idx + 1}: kunde inte öppna {self._port}")

    def read_mm(self, y_mm: float = 0.0) -> float:
        if not self._connected:
            return RIG.board_thick_mm
        rr = self._client.read_holding_registers(address=0, count=1, slave=self._unit)
        if rr.isError():
            return RIG.board_thick_mm
        dist_mm = rr.registers[0] / 100.0               # 0,01 mm-enheter
        return self._ref - dist_mm                       # → tjocklek

    def zero(self, current_thickness_mm: float) -> None:
        """Nollning: sätt referensen så att aktuell mätning = känd tjocklek."""
        if self._connected:
            rr = self._client.read_holding_registers(address=0, count=1, slave=self._unit)
            if not rr.isError():
                self._ref = rr.registers[0] / 100.0 + current_thickness_mm

    def close(self) -> None:
        if self._client:
            self._client.close()
        self._connected = False
