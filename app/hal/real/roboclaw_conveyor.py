"""Transportör via **RoboClaw 2x7A** (dubbelkanal) över USB packet serial.

Wrappar BasicMicros **officiella** Python-bibliotek (``pip install basicmicro``,
https://github.com/basicmicro/basicmicro_python) i stället för ett handrullat
protokoll — biblioteket sköter CRC16, retries och hela packet-serial-formatet.
Importeras lazy så appen startar utan det installerat.

RoboClaw driver BÅDA banden synkat med sluten slinga (quadrature-encoder per motor):
  * ``set_speed(mm/s)``  → SpeedM1M2 (counts/s, sluten slinga) eller DutyM1M2 (jog).
  * ``position_mm()``    ← ReadEncM1 × 1/counts_per_mm.
  * ``move_mm(d, v)``    → SpeedAccelDistanceM1M2 (kör exakt sträcka, auto-stopp).
  * ``read_speed_mm_s`` / ``encoder_counts`` / ``health`` ← för auto-kalibrering + selftest.

``counts_per_mm`` kalibreras mot riktiga band (Fas C/D, kalibrering ``conveyor.countsmm``).
"""
from __future__ import annotations

from ..base import ConveyorIF, DeviceInfo


class RoboClawConveyor(ConveyorIF):
    def __init__(self, port: str = "/dev/ttyACM0", address: int = 0x80,
                 baud: int = 38400, counts_per_mm: float = 100.0,
                 max_duty: int = 16000, closed_loop: bool = True,
                 controller=None):
        self._port = port
        self._addr = address & 0xFF
        self._baud = baud
        self._counts_per_mm = counts_per_mm     # encoder counts → mm (kalibreras)
        self._max_duty = max_duty               # tak för jog (öppen slinga)
        self._closed_loop = closed_loop
        self._mc = controller                   # injicerbar för test; annars Basicmicro
        self._connected = False
        self._zero_counts = 0

    def info(self) -> DeviceInfo:
        return DeviceInfo("Transportör (2 band)", "RoboClaw 2x7A", f"USB {self._port}", self._connected)

    # ------------------------------------------------------------------ comms
    def open(self) -> None:
        if self._mc is None:
            from basicmicro import Basicmicro            # lazy (pip install basicmicro)
            self._mc = Basicmicro(self._port, self._baud)
        if not self._mc.Open():
            raise RuntimeError(f"RoboClaw på {self._port} kunde inte öppnas")
        if not self.firmware():
            raise RuntimeError(f"RoboClaw på {self._port} svarade inte (version tom)")
        self._connected = True
        self._zero_counts = self._enc_m1()

    def firmware(self) -> str:
        try:
            ok, ver = self._mc.ReadVersion(self._addr)
            return ver.strip() if ok and ver else ""
        except Exception:
            return ""

    def _enc_m1(self) -> int:
        ok, count, _ = self._mc.ReadEncM1(self._addr)
        return count if ok else self._zero_counts

    def _enc_m2(self) -> int:
        ok, count, _ = self._mc.ReadEncM2(self._addr)
        return count if ok else 0

    # ------------------------------------------------------------ ConveyorIF
    def set_speed(self, mm_s: float) -> None:
        if not self._connected:
            return
        if self._closed_loop:
            cps = int(mm_s * self._counts_per_mm)          # counts/s, samma båda band
            self._mc.SpeedM1M2(self._addr, cps, cps)
        else:
            duty = int(max(-self._max_duty, min(self._max_duty,
                       mm_s / 50.0 * self._max_duty)))      # grov jog-skala
            self._mc.DutyM1M2(self._addr, duty, duty)

    def position_mm(self) -> float:
        return (self._enc_m1() - self._zero_counts) / self._counts_per_mm

    def zero(self) -> None:
        """Nollställ positionsreferens vid aktuell encoderräkning."""
        self._zero_counts = self._enc_m1()

    # --------------------------------------------- utökat API (kalib + selftest)
    def encoder_counts(self) -> tuple[int, int]:
        """Råa encoder-counts (M1, M2) — för bandsynk-jämförelse."""
        return (self._enc_m1(), self._enc_m2())

    def read_speed_mm_s(self) -> tuple[float, float]:
        """Momentan hastighet per band (mm/s) ur ReadSpeedM1/M2 (counts/s)."""
        try:
            ok1, s1, _ = self._mc.ReadSpeedM1(self._addr)
            ok2, s2, _ = self._mc.ReadSpeedM2(self._addr)
            return ((s1 if ok1 else 0) / self._counts_per_mm,
                    (s2 if ok2 else 0) / self._counts_per_mm)
        except Exception:
            return (0.0, 0.0)

    def move_mm(self, distance_mm: float, speed_mm_s: float = 30.0) -> None:
        """Kör båda banden en EXAKT sträcka (sluten slinga, auto-stopp). Bounded —
        används av auto-kalibrering (operatörsinitierad). Blockerar ej; poll position."""
        if not self._connected:
            return
        cpm = self._counts_per_mm
        dist = int(abs(distance_mm) * cpm)
        spd = int(max(1.0, abs(speed_mm_s)) * cpm) * (1 if distance_mm >= 0 else -1)
        accel = abs(spd) * 2                                # nå hastighet på ~0,5 s
        # SpeedAccelDistanceM1M2(addr, accel, speed1, dist1, speed2, dist2, buffer=0)
        self._mc.SpeedAccelDistanceM1M2(self._addr, accel, spd, dist, spd, dist, 0)

    def main_battery_v(self) -> float:
        try:
            ok, v = self._mc.ReadMainBatteryVoltage(self._addr)
            return v / 10.0 if ok else 0.0                  # 0,1 V-enheter
        except Exception:
            return 0.0

    def temperature_c(self) -> float:
        try:
            ok, t = self._mc.ReadTemp(self._addr)
            return t / 10.0 if ok else 0.0                  # 0,1 °C-enheter
        except Exception:
            return 0.0

    def error_status(self) -> int:
        try:
            ok, err = self._mc.ReadError(self._addr)
            return int(err) if ok else -1
        except Exception:
            return -1

    def health(self) -> dict:
        """Hälsobild för selftest/GUI: firmware, batteri, temp, encoders, fel."""
        m1, m2 = self.encoder_counts()
        return {"firmware": self.firmware(), "battery_v": self.main_battery_v(),
                "temp_c": self.temperature_c(), "enc_m1": m1, "enc_m2": m2,
                "error": self.error_status()}

    def close(self) -> None:
        if self._mc is not None and self._connected:
            try:
                self.set_speed(0.0)
            finally:
                try:
                    self._mc.close()
                except Exception:
                    pass
        self._connected = False
