"""Riktiga hårdvaruspecar för riggen, som driver den fysikaliska sensor-simmen.

Värdena är från faktiska produkter (prototypval). Härledda mått (linjelängd,
höjdupplösning, antal lasermoduler för full täckning, dataflöde) räknas ur dem så
simuleringen speglar verkligheten.

Produkter:
  LineLaser   – iadiy LM9R650H100L60 (650 nm, 100 mW, 60° linjevinkel). Billig
                prototyplaser.
  LineScanCam – Hikrobot MV-XGLC83BM TDI line-scan 8192×4, 10GigE, 109 kHz
                (yt-/färgkanal över brädans längd).
  AreaCam     – Hikrobot MV-CS050-10 5 MP global shutter (2448×2048), som
                trianguleringskamera som ser laserstrippen i vinkel.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LineLaser:
    name: str = "iadiy LM9R650H100L60"
    wavelength_nm: float = 650.0
    power_mw: float = 100.0
    fan_angle_deg: float = 60.0          # "L60" (60° ger ren, tunn linje på håll)
    working_distance_mm: float = 1000.0  # ~1 m håll -> 60° ≈ 1,2 m linjelängd
    line_width_mm: float = 0.25          # strippens bredd vid fokus
    voltage_v: float = 3.0

    @property
    def line_length_mm(self) -> float:
        """Belyst linjelängd vid working_distance (2·WD·tan(fan/2))."""
        return 2.0 * self.working_distance_mm * math.tan(math.radians(self.fan_angle_deg / 2))


@dataclass
class LineScanCam:
    name: str = "Hikrobot MV-XGLC83BM (TDI)"
    px_across: int = 8192                # px tvärs längden
    tdi_stages: int = 4
    line_rate_hz: float = 109_000.0      # max radtakt
    pixel_um: float = 7.0
    interface: str = "10GigE"
    bit_depth: int = 8


@dataclass
class AreaCam:
    name: str = "Hikrobot MV-CS050-10"
    width_px: int = 2448
    height_px: int = 2048
    pixel_um: float = 3.45
    global_shutter: bool = True
    interface: str = "GigE"


@dataclass
class Rig:
    """Hela mätuppställningen (laser- och kamera-array) + härledda mått.

    Lasrar och profilkameror sitter i array längs brädans LÄNGD, var och en
    täcker ett segment med överlapp; segmenten fusioneras. Beräkningarna är
    konsekventa ur produktspecarna (antaganden anges)."""
    laser: LineLaser = None
    surface_cam: LineScanCam = None
    profile_cam: AreaCam = None
    board_length_mm: float = 5400.0
    board_width_mm: float = 150.0
    tri_angle_deg: float = 30.0          # vinkel laser–kamera (triangulering)
    overlap_mm: float = 150.0            # överlapp mellan grann-segment
    profile_height_range_mm: float = 50.0  # antaget mätrange (DOF) per profilkamera
    feed_mps: float = 0.25

    def __post_init__(self):
        self.laser = self.laser or LineLaser()
        self.surface_cam = self.surface_cam or LineScanCam()
        self.profile_cam = self.profile_cam or AreaCam()

    # --- ytkanal (line-scan över längden) ---
    @property
    def surface_mm_per_px(self) -> float:
        return self.board_length_mm / self.surface_cam.px_across

    @property
    def max_feed_for_square_px(self) -> float:
        """Matningshastighet (m/s) som ger kvadratiska pixlar vid max radtakt."""
        return self.surface_mm_per_px / 1000.0 * self.surface_cam.line_rate_hz

    @property
    def surface_gbit_s(self) -> float:
        """Dataflöde vid max radtakt (10GigE ≈ 10 Gbit/s budget)."""
        return self.surface_cam.px_across * self.surface_cam.bit_depth * \
            self.surface_cam.line_rate_hz / 1e9

    # --- laser-/kamera-array (triangulering) ---
    @property
    def seg_len_mm(self) -> float:
        return self.laser.line_length_mm

    @property
    def n_lasers(self) -> int:
        """Antal moduler för full längd med överlapp (step = seg − överlapp)."""
        step = max(1e-6, self.seg_len_mm - self.overlap_mm)
        return max(1, math.ceil((self.board_length_mm - self.overlap_mm) / step))

    @property
    def n_profile_cams(self) -> int:
        return self.n_lasers                 # en profilkamera per lasersegment

    def segments(self):
        """[(start_mm, end_mm, center_mm)] per laser/kamera längs längden."""
        step = self.seg_len_mm - self.overlap_mm
        segs = []
        for i in range(self.n_lasers):
            s = i * step
            e = min(s + self.seg_len_mm, self.board_length_mm)
            s = max(0.0, e - self.seg_len_mm)
            segs.append((s, e, (s + e) / 2))
        return segs

    @property
    def profile_mm_per_px_len(self) -> float:
        """Upplösning längs längden per profilkamera (lång axel över segmentet)."""
        return self.seg_len_mm / self.profile_cam.width_px

    @property
    def height_resolution_mm(self) -> float:
        """Höjdupplösning ur samma lins: objektpixel / tan(θ). Med den billiga
        prototyplasern + 5 MP-kamera över ett 1,2 m-segment blir den grov
        (~mm) – en dedikerad profilsensor ger finare. Range är DOF-begränsat
        (profile_height_range_mm, antaget)."""
        return self.profile_mm_per_px_len / math.tan(math.radians(self.tri_angle_deg))

    def summary(self) -> dict:
        return {
            "laser": self.laser.name,
            "fan_deg": self.laser.fan_angle_deg,
            "working_distance_mm": self.laser.working_distance_mm,
            "seg_len_mm": round(self.seg_len_mm, 0),
            "overlap_mm": self.overlap_mm,
            "n_lasers": self.n_lasers,
            "n_profile_cams": self.n_profile_cams,
            "surface_cam": self.surface_cam.name,
            "surface_mm_per_px": round(self.surface_mm_per_px, 3),
            "surface_gbit_s@109kHz": round(self.surface_gbit_s, 2),
            "max_feed_mps@109kHz": round(self.max_feed_for_square_px, 2),
            "profile_cam": self.profile_cam.name,
            "profile_mm_per_px_len": round(self.profile_mm_per_px_len, 3),
            "tri_angle_deg": self.tri_angle_deg,
            "height_resolution_mm": round(self.height_resolution_mm, 4),
            "height_range_mm": self.profile_height_range_mm,
        }
