"""GPIO-IO på Jetsons 40-pin header — laser-enable, LED-enable, anhåll-fotocell.

Pin-tilldelning enligt prototype-pinout.svg (BOARD-numrering, J12):
  pin  7  ANHÅLL-FOTOCELL in (NPN → pull-up, aktiv LÅG när bräda laddats)
  pin 16  LINJELASER RÖD enable  (→ D4184/AO3400-MOSFET, 5 V-laser)
  pin 18  LINJELASER GRÖN enable (→ AOD4184 opto-MOSFET, 24 V-laser)
  pin 13  VITT LED A enable      (→ MOSFET, 24 V-list)
  pin 15  VITT LED B enable      (→ MOSFET, 24 V-list)

Jetson.GPIO importeras lazy så appen startar på dev-maskiner utan biblioteket.
SÄKERHET: lasrarna är klass 3B — enable får bara sättas när interlock/rutiner
är uppfyllda (rum låst, glasögon). close() släcker ALLTID utgångarna.
"""
from __future__ import annotations

from ..base import Device, DeviceInfo

# BOARD-pin → roll (sanningskälla = prototype-pinout.svg / tools/draw_pinout.py)
PIN_PHOTOCELL = 7
PIN_LASER_RED = 16
PIN_LASER_GREEN = 18
PIN_LED_A = 13
PIN_LED_B = 15

_GPIO = None


def _gpio():
    """Delad Jetson.GPIO-modul i BOARD-läge (lazy)."""
    global _GPIO
    if _GPIO is None:
        import Jetson.GPIO as GPIO          # lazy
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        _GPIO = GPIO
    return _GPIO


class GpioEnable(Device):
    """Aktiv-HÖG enable-utgång (laser/LED via MOSFET-modul).

    ``requires_arm=True`` (lasrar, klass 3B): ``set(True)`` VÄGRAR tända tills
    ``arm(confirm=True)`` anropats — representerar människo-interlock (rum låst,
    dörrinterlock, skyddsglasögon HM326-C). Det gör säkerhetsregeln kodlåst: ingen
    rutin kan tända lasern av misstag. LED (``requires_arm=False``) tänds direkt.
    """

    def __init__(self, name: str, model: str, pins: list[int], requires_arm: bool = False):
        self._name, self._model, self._pins = name, model, list(pins)
        self._requires_arm = requires_arm
        self._connected = False
        self._on = False
        self._armed = False

    def info(self) -> DeviceInfo:
        pins = "+".join(str(p) for p in self._pins)
        return DeviceInfo(self._name, self._model, f"GPIO ut · pin {pins}", self._connected)

    def open(self) -> None:
        g = _gpio()
        for p in self._pins:
            g.setup(p, g.OUT, initial=g.LOW)
        self._connected = True
        self._on = False
        self._armed = False

    def arm(self, confirm: bool = False) -> bool:
        """Lås upp tändning EFTER människo-interlock. ``confirm`` måste vara True."""
        self._armed = bool(confirm)
        return self._armed

    def disarm(self) -> None:
        self.set(False)
        self._armed = False

    def set(self, on: bool) -> bool:
        """Tänd/släck. Returnerar False om tändning vägrades (ej armad laser)."""
        if not self._connected:
            return False
        if on and self._requires_arm and not self._armed:
            print(f"[SÄKERHET] {self._name}: tändning VÄGRAD — arm(confirm=True) "
                  f"krävs (interlock, glasögon) innan klass-3B-laser tänds.")
            return False
        g = _gpio()
        for p in self._pins:
            g.output(p, g.HIGH if on else g.LOW)
        self._on = bool(on)
        return True

    @property
    def is_on(self) -> bool:
        return self._on

    @property
    def is_armed(self) -> bool:
        return self._armed

    @property
    def requires_arm(self) -> bool:
        return self._requires_arm

    def close(self) -> None:
        if self._connected:
            try:
                self.set(False)               # släck ALLTID vid stängning (lasersäkerhet)
            finally:
                self._armed = False
                self._connected = False


class PhotocellInput(Device):
    """Anhåll-fotocell (GTRIC LSZ-S30N1, NPN NO): bräda laddad → aktiv LÅG.

    ``read()`` = momentanstatus; ``on_board_loaded(cb)`` = flank-callback
    (falling edge) som startar skanning + nollar position.
    """

    def __init__(self, pin: int = PIN_PHOTOCELL):
        self._pin = pin
        self._connected = False
        self._cb = None

    def info(self) -> DeviceInfo:
        return DeviceInfo("Fotocell · anslag", "GTRIC LSZ-S30N1 · NPN",
                          f"GPIO in · pin {self._pin}", self._connected)

    def open(self) -> None:
        g = _gpio()
        g.setup(self._pin, g.IN)              # NPN open collector → extern/intern pull-up
        self._connected = True

    def read(self) -> bool:
        """True = bräda detekterad (NPN drar LÅG)."""
        if not self._connected:
            return False
        g = _gpio()
        return g.input(self._pin) == g.LOW

    def collect_load_events(self, n: int = 10, timeout_s: float = 30.0,
                            poll_dt: float = 0.002):
        """Polla efter ``n`` laddnings-flanker (HÖG→LÅG) → tidsstämplar (monotont).
        För trigg-kalibrering: operatören laddar brädan mot anhållet n gånger.
        Returnerar listan tidsstämplar (s); avbryter vid timeout."""
        import time
        if not self._connected:
            return []
        g = _gpio()
        stamps, prev = [], (g.input(self._pin) == g.LOW)
        t0 = time.monotonic()
        while len(stamps) < n and (time.monotonic() - t0) < timeout_s:
            cur = (g.input(self._pin) == g.LOW)
            if cur and not prev:                      # fallande flank = bräda laddad
                stamps.append(time.monotonic())
            prev = cur
            time.sleep(poll_dt)
        return stamps

    def on_board_loaded(self, callback) -> None:
        """Registrera flank-callback: anropas när en bräda laddas mot anhållet."""
        if not self._connected:
            return
        g = _gpio()
        self._cb = callback
        g.add_event_detect(self._pin, g.FALLING, bouncetime=50,
                           callback=lambda ch: callback())

    def close(self) -> None:
        if self._connected and self._cb is not None:
            try:
                _gpio().remove_event_detect(self._pin)
            except Exception:
                pass
        self._connected = False
        self._cb = None


def make_field_io():
    """Standarduppsättningen fält-IO enligt pinout: (laser_röd, laser_grön, led, fotocell).
    Lasrarna kräver arm(confirm=True) före tändning (klass 3B); LED gör inte det."""
    return (GpioEnable("Linjelaser RÖD enable", "650 nm · D4184-MOSFET", [PIN_LASER_RED],
                       requires_arm=True),
            GpioEnable("Linjelaser GRÖN enable", "520 nm · AOD4184 opto", [PIN_LASER_GREEN],
                       requires_arm=True),
            GpioEnable("Vitt LED-ljus", "24 V list ×2 · MOSFET", [PIN_LED_A, PIN_LED_B]),
            PhotocellInput())
