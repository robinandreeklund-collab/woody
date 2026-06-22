"""3× punktlaser LR400 över RS-485 (Modbus RTU) via Waveshare USB→4CH.

Enligt prototype-wiring.svg (Fas 2): ch1–3 = 3× LR400, ch4 = reserv. Varje LR400
läses som ett Modbus-register (avstånd → mm via skala). Tjocklek = ``d0_mm −
uppmätt avstånd`` (d0 sätts vid nollning mot tomt band, kalibrering ``lr400.zero_d0``).
Punktlasrarna ger ABSOLUT tjocklek och ankrar trianguleringens globala offset/tilt
(fusion.anchor). pymodbus importeras lazy så appen startar utan biblioteket.

Buss-topologi: flera lasrar på SAMMA port (delad RS-485-buss, olika slav-adresser)
DELAR en Modbus-klient — annars kolliderar de om porten. Per-kanal port/unit/register
kommer från ``data/lr400.json`` (se lr400_config.py).
"""
from __future__ import annotations

from ..base import DeviceInfo, PointLaserIF
from ...geometry import RIG

# Delad klient per serieport (flera lasrar på samma RS-485-buss → en klient).
import threading

_CLIENTS: dict = {}            # port -> {"client": c, "refs": int}
_CLIENTS_LOCK = threading.Lock()


def _get_client(port: str, baud: int):
    with _CLIENTS_LOCK:
        entry = _CLIENTS.get(port)
        if entry is None:
            from pymodbus.client import ModbusSerialClient    # lazy
            client = ModbusSerialClient(port=port, baudrate=baud, parity="N",
                                        stopbits=1, bytesize=8, timeout=0.1)
            if not client.connect():
                raise RuntimeError(f"kunde inte öppna {port}")
            entry = {"client": client, "refs": 0}
            _CLIENTS[port] = entry
        entry["refs"] += 1
        return entry["client"]


def _release_client(port: str) -> None:
    with _CLIENTS_LOCK:
        entry = _CLIENTS.get(port)
        if not entry:
            return
        entry["refs"] -= 1
        if entry["refs"] <= 0:
            try:
                entry["client"].close()
            finally:
                _CLIENTS.pop(port, None)


class LR400ModbusLaser(PointLaserIF):
    _NAMES = ["V", "C", "H"]

    def __init__(self, idx: int, x_mm: float, port: str = "/dev/ttyUSB0",
                 unit: int = 1, baud: int = 9600, d0_mm: float = 100.0,
                 reg_addr: int = 0, reg_kind: str = "holding", scale: float = 0.01,
                 client=None):
        self._idx, self._x = idx, x_mm
        self._port, self._unit, self._baud = port, unit, baud
        self._d0 = d0_mm                    # nollreferens (kalibreras mot tomt band)
        self._reg_addr, self._reg_kind, self._scale = reg_addr, reg_kind, scale
        self._client = client              # injicerbar för test; annars delad pool
        self._owns_pool = client is None
        self._connected = client is not None

    def info(self) -> DeviceInfo:
        nm = self._NAMES[self._idx] if 0 <= self._idx < len(self._NAMES) else str(self._idx)
        return DeviceInfo(f"Punktlaser LR-{nm}", "LR400", f"RS-485 ch{self._idx + 1}",
                          self._connected)

    def open(self) -> None:
        if self._connected:                # idempotent: dubbel-open läcker annars pool-refs
            return
        if self._owns_pool:
            self._client = _get_client(self._port, self._baud)
        self._connected = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------ avläsning
    def _read_register(self):
        """Läs råregistret → avstånd i mm, eller None om ogiltigt/utanför mätområde."""
        if not self._connected or self._client is None:
            return None
        try:
            if self._reg_kind == "input":
                rr = self._client.read_input_registers(address=self._reg_addr, count=1, device_id=self._unit)
            else:
                rr = self._client.read_holding_registers(address=self._reg_addr, count=1, device_id=self._unit)
            if rr is None or rr.isError() or not getattr(rr, "registers", None):
                return None
            return rr.registers[0] * self._scale
        except Exception:
            return None

    def read_distance_mm(self):
        """Råa absolutavståndet (mm), eller None om sensorn inte ser något mål."""
        return self._read_register()

    def read_distance_avg(self, n: int = 50):
        """Medelavstånd + brus (RMS) över n giltiga avläsningar. (mean, rms, n_ok)."""
        vals = [d for d in (self._read_register() for _ in range(max(1, n))) if d is not None]
        if not vals:
            return (None, None, 0)
        import statistics
        mean = sum(vals) / len(vals)
        rms = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        return (mean, rms, len(vals))

    def read_mm(self, y_mm: float = 0.0) -> float:
        """Absolut tjocklek = d0 − uppmätt avstånd. Faller tillbaka på nominell
        tjocklek om sensorn inte svarar (pipeline ska aldrig krascha)."""
        dist = self._read_register()
        if dist is None:
            return RIG.board_thick_mm
        return self._d0 - dist

    def set_d0(self, d0_mm: float) -> None:
        """Sätt nollreferensen (kalibrering zero_d0)."""
        self._d0 = float(d0_mm)

    @property
    def d0_mm(self) -> float:
        return self._d0

    def close(self) -> None:
        if self._owns_pool and self._connected:
            _release_client(self._port)
        self._client = None
        self._connected = False
