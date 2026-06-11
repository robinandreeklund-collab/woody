"""Transportör via **RoboClaw 2x7A** (dubbelkanal) över USB packet serial.

Ersätter den utgångna Jrk G2-lösningen (se docs/jetson-prep-plan.md §4). RoboClaw
driver BÅDA banden synkat med sluten slinga (quadrature-encoder på varje motor):
  * ``set_speed(mm/s)``  → Drive M1/M2 With Signed Speed (cmd 37, counts/s) — closed loop.
  * ``position_mm()``    ← Read Encoder M1 (cmd 16) × 1/counts_per_mm.
  * ``firmware()``       ← Read Firmware Version (cmd 21) — används av självtestet.

Packet serial: varje paket = [adress, kommando, data...] följt av CRC16 (CCITT,
poly 0x1021) över alla föregående byte. Skrivkommandon kvitteras med 0xFF.
Läskommandon returnerar data + CRC16. pyserial importeras lazy så appen startar
utan biblioteket. Kalibrera ``counts_per_mm`` mot riktiga band (Fas C/D).
"""
from __future__ import annotations

import struct

from ..base import ConveyorIF, DeviceInfo

# RoboClaw packet-serial kommandon (BasicMicro)
_CMD_READ_ENC_M1 = 16
_CMD_READ_FIRMWARE = 21
_CMD_DRIVE_DUTY_M1M2 = 34       # öppen slinga (-32767..32767) — jog/bring-up
_CMD_DRIVE_SPEED_M1M2 = 37      # sluten slinga (signed counts/s)


def _crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc & 0xFFFF


class RoboClawConveyor(ConveyorIF):
    def __init__(self, port: str = "/dev/ttyACM0", address: int = 0x80,
                 baud: int = 38400, counts_per_mm: float = 100.0,
                 max_duty: int = 16000, closed_loop: bool = True):
        self._port = port
        self._addr = address & 0xFF
        self._baud = baud
        self._counts_per_mm = counts_per_mm     # encoder counts → mm (kalibreras)
        self._max_duty = max_duty               # tak för jog (öppen slinga)
        self._closed_loop = closed_loop
        self._ser = None
        self._connected = False
        self._zero_counts = 0

    def info(self) -> DeviceInfo:
        return DeviceInfo("Transportör (2 band)", "RoboClaw 2x7A", f"USB {self._port}", self._connected)

    # ------------------------------------------------------------------ comms
    def open(self) -> None:
        import serial                            # lazy
        self._ser = serial.Serial(self._port, baudrate=self._baud, timeout=0.2)
        # verifiera kommunikation genom att läsa firmware
        fw = self.firmware()
        if not fw:
            raise RuntimeError(f"RoboClaw på {self._port} svarade inte (firmware-läsning tom)")
        self._connected = True
        self._zero_counts = self._read_enc_m1()

    def _write_cmd(self, cmd: int, payload: bytes = b"") -> bool:
        """Skicka skrivkommando + CRC16, läs 0xFF-kvittens."""
        pkt = bytes([self._addr, cmd]) + payload
        pkt += struct.pack(">H", _crc16(pkt))
        self._ser.write(pkt)
        ack = self._ser.read(1)
        return ack == b"\xff"

    def _read_cmd(self, cmd: int, nbytes: int) -> bytes | None:
        """Skicka läskommando, läs nbytes data + 2 CRC-byte, validera CRC."""
        req = bytes([self._addr, cmd])
        self._ser.write(req)
        resp = self._ser.read(nbytes + 2)
        if len(resp) != nbytes + 2:
            return None
        data, crc_rx = resp[:nbytes], struct.unpack(">H", resp[nbytes:])[0]
        if _crc16(req + data) != crc_rx:
            return None
        return data

    def firmware(self) -> str:
        if self._ser is None:
            return ""
        # version är en nollterminerad sträng (upp till 48 byte) + 2 CRC
        self._ser.write(bytes([self._addr, _CMD_READ_FIRMWARE]))
        raw = self._ser.read(48)
        if not raw:
            return ""
        return raw.split(b"\x00", 1)[0].decode("ascii", "ignore").strip()

    def _read_enc_m1(self) -> int:
        data = self._read_cmd(_CMD_READ_ENC_M1, 5)   # 4 byte count + 1 statusbyte
        if not data:
            return self._zero_counts
        return struct.unpack(">i", data[:4])[0]

    # ------------------------------------------------------------ ConveyorIF
    def set_speed(self, mm_s: float) -> None:
        if not self._connected:
            return
        if self._closed_loop:
            cps = int(mm_s * self._counts_per_mm)     # counts/sek, samma på båda band
            self._write_cmd(_CMD_DRIVE_SPEED_M1M2, struct.pack(">ii", cps, cps))
        else:
            duty = int(max(-self._max_duty, min(self._max_duty,
                       mm_s / 50.0 * self._max_duty)))  # grov jog-skala
            self._write_cmd(_CMD_DRIVE_DUTY_M1M2, struct.pack(">hh", duty, duty))

    def position_mm(self) -> float:
        return (self._read_enc_m1() - self._zero_counts) / self._counts_per_mm

    def zero(self) -> None:
        """Nollställ positionsreferens vid aktuell encoderräkning."""
        self._zero_counts = self._read_enc_m1()

    def close(self) -> None:
        if self._ser:
            try:
                self.set_speed(0.0)
            finally:
                self._ser.close()
        self._connected = False
