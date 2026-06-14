"""RealScanner — verklig hårdvara via HAL-gränssnitten (enligt prototype-wiring.svg).

Fas 1 + Fas 2 KOMPLETT:
  * 2× profilkamera Hikrobot MV-CS050-10UM (GenICam/USB3, RÖD+GRÖN huvud)
  * Linjekamera HT-GELM44C-T2 (GenICam/GigE, encoder-triggad via band B)
  * 3× punktlaser LR400 (RS-485 Modbus, Waveshare USB→4CH ch1–3) — absolut
    tjocklek, ankrar trianguleringens offset/tilt (fusion.anchor)
  * RoboClaw 2x7A (USB packet serial) — båda banden, sluten slinga
  * GPIO fält-IO: laser-enable RÖD/GRÖN, vitt LED, anhåll-fotocell (gpio_io)

Bräd-livscykel i verkligt läge: fotocellen detekterar att en bräda laddats mot
anhållet (``arm_photocell``) → ``new_board()`` tänder lasrar+LED, kör den trådade
förvärvspipelinen (capture ∥ GPU-process) till en färdig, graderbar Board, och
släcker lasrarna. open() ansluter varje enhet utan att krascha om något saknas.
"""
from __future__ import annotations

from ..base import Scanner
from ...geometry import RIG
from . import camera_config, lr400_config
from .cameras import GenICamProfileCamera, GenICamSurfaceCamera
from .gpio_io import make_field_io
from .lr400_modbus import LR400ModbusLaser
from .roboclaw_conveyor import RoboClawConveyor


class RealScanner(Scanner):
    def __init__(self, cfg=None):
        # Kamera-identitet + inställningar från data/cameras.json (serienr binder
        # RÖD≠GRÖN; ROI/exponering/divider per kamera). Saknad fil → säkra defaults.
        cams = camera_config.load()
        cr, cg, cs = cams["profile_red"], cams["profile_green"], cams["surface"]
        prof_f = getattr(cfg, "profile_features", None) if cfg else None
        surf_f = getattr(cfg, "surface_features", None) if cfg else None
        self.profile_red = GenICamProfileCamera(
            "red", serial=cr["serial"], roi_rows=cr["roi_rows"],
            exposure_us=cr["exposure_us"], roi_offset_y=cr["roi_offset_y"],
            frame_rate_hz=cr["frame_rate_hz"], features=prof_f)
        self.profile_green = GenICamProfileCamera(
            "green", serial=cg["serial"], roi_rows=cg["roi_rows"],
            exposure_us=cg["exposure_us"], roi_offset_y=cg["roi_offset_y"],
            frame_rate_hz=cg["frame_rate_hz"], features=prof_f)
        self.surface = GenICamSurfaceCamera(serial=cs["serial"], features=surf_f)
        self.surface.configure_encoder_line_trigger(
            divider=cs["divider"], multiplier=cs["multiplier"],
            direction=cs["direction"], line_rate_hz=cs["line_rate_hz"])
        # 3× LR400 över RS-485 Modbus (Waveshare 4CH ch1–3) — absolut tjocklek-ankare.
        # Per-kanal port/unit/register/D0 från data/lr400.json (delad buss-klient).
        lr = lr400_config.load()
        chans = ["ch1", "ch2", "ch3"]
        self.point_lasers = []
        for i, x in enumerate(RIG.point_lasers_x_mm):
            c = lr[chans[i]] if i < len(chans) else lr400_config.DEFAULTS["ch1"]
            self.point_lasers.append(LR400ModbusLaser(
                i, x, port=c["port"], unit=c["unit"], baud=c["baud"], d0_mm=c["d0_mm"],
                reg_addr=c["reg_addr"], reg_kind=c["reg_kind"], scale=c["scale"]))
        # Delad rigg: EN encoder + EN motordrivare. Bara lead-noden (has_conveyor)
        # bygger en egen RoboClaw; sensor-huvuden får matningspositionen från lead.
        from ...net import head_config
        self.is_lead = bool(head_config.load().get("has_conveyor", True))
        if self.is_lead:
            self.conveyor = RoboClawConveyor()
        else:
            from .shared_conveyor import SharedConveyorClient
            self.conveyor = SharedConveyorClient()
        self.laser_red, self.laser_green, self.led_white, self.photocell = make_field_io()
        self._board = None
        self._pipeline = None         # AcquisitionPipeline (lazy — värmer GPU)

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

    # ------------------------------------------------------------ bräd-livscykel
    def arm_photocell(self, callback) -> None:
        """Anropa ``callback`` när en bräda laddas mot anhållet (fotocell-flank)."""
        self.photocell.on_board_loaded(callback)

    def new_board(self) -> None:
        """Skanna en VERKLIG bräda: lasrar+LED på → förvärvspipeline → Board.

        Misslyckas hårdvara saknas → board() förblir None (bring-up-vänligt).
        """
        self._board = None
        try:
            if self._pipeline is None:
                from ...processing.acquisition import AcquisitionPipeline
                self._pipeline = AcquisitionPipeline(
                    self, lr_positions=list(RIG.point_lasers_x_mm))
            if not self.lasers_armed():
                print("[SÄKERHET] lasrar ej armade — kör arm_lasers(confirm=True) efter "
                      "interlock. Skannar utan laserprofil tills dess.")
            self.laser_red.set(True)
            self.laser_green.set(True)
            self.led_white.set(True)
            try:
                lr = (lambda y: [pl.read_mm(y) for pl in self.point_lasers]) \
                    if any(getattr(pl, "_connected", False) for pl in self.point_lasers) else None
                board, stats = self._pipeline.scan_board(lr_provider=lr)
                self._board = board
                print(f"[HAL] bräda skannad: {stats.rows} rader @ "
                      f"{stats.rows_per_s:.0f} rader/s, överlapp {stats.overlap:.2f}×")
            finally:
                self.laser_red.set(False)
                self.laser_green.set(False)
                self.led_white.set(False)
        except Exception as exc:
            print(f"[HAL] skanning misslyckades — {exc}")

    def board(self):
        return self._board

    # ------------------------------------------------------------ lasersäkerhet
    def arm_lasers(self, confirm: bool = False) -> bool:
        """Lås upp klass 3B-laser-enable EFTER människo-interlock (rum låst, dörr-
        interlock, skyddsglasögon HM326-C). GUI:t ska anropa detta från en EXPLICIT
        bekräftelse-kontroll. Utan arm vägrar new_board/begin_stream tända lasrarna."""
        a = bool(confirm)
        self.laser_red.arm(a)
        self.laser_green.arm(a)
        return a

    def disarm_lasers(self) -> None:
        """Släck + avarma båda lasrarna (säkert läge)."""
        self.laser_red.disarm()
        self.laser_green.disarm()

    def lasers_armed(self) -> bool:
        return bool(self.laser_red.is_armed and self.laser_green.is_armed)

    # ------------------------------------------------------------ löpande flöde
    def feed_position_mm(self) -> float:
        """RoboClaw-encoder (counts → mm) — radklockan för linjekameran."""
        try:
            return self.conveyor.position_mm()
        except Exception:
            return 0.0

    def board_present(self) -> bool:
        """Anhåll-fotocell (GPIO pin 7, aktiv låg). Utan GPIO/ej ansluten → False."""
        try:
            return bool(self.photocell.read())
        except Exception:
            return False

    def begin_stream(self, gap_mm: float = 25.0) -> None:
        """Löpande flöde: tänd lasrar + LED (släcks i end_stream).

        SÄKERHET: tänder klass 3B-lasrar — sker när operatören startar drift i
        real-läge (samma som new_board i pass-läge). Kräver att riggen är säkrad.
        """
        try:
            if not self.lasers_armed():
                print("[SÄKERHET] lasrar ej armade — arm_lasers(confirm=True) efter interlock.")
            self.laser_red.set(True)
            self.laser_green.set(True)
            self.led_white.set(True)
        except Exception as exc:
            print(f"[HAL] kunde inte tända ljus för flöde — {exc}")

    def end_stream(self) -> None:
        for d in (getattr(self, "laser_red", None), getattr(self, "laser_green", None),
                  getattr(self, "led_white", None)):
            try:
                if d is not None:
                    d.set(False)
            except Exception:
                pass

    def devices(self) -> list:
        return [self.profile_red, self.profile_green, self.surface,
                *self.point_lasers, self.conveyor,
                self.laser_red, self.laser_green, self.led_white, self.photocell]
