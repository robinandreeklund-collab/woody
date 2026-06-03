"""Riktiga hårdvaruspecar för riggen, som driver den fysikaliska sensor-simmen.

Varje fält är märkt [datablad] (från produkten) eller [designval] (vårt val av
optik/montering – beror inte på produkten utan på hur vi bygger riggen).

Valda produkter (passar jobbet bäst):
  LineLaser   – iadiy LM9R650H100L60: 650 nm, 100 mW, 60° linje. Billig
                prototyplaser; array tvärs bredden längs hela längden.
  SurfaceCam  – Hikrobot 8K-linjekamera (10GigE, 109 kHz), FÄRG-variant av den
                länkade MV-XGLC83BM (mono duger ej för färgdefekter som blånad).
                Två kameror tilas -> 0,33 mm/px över 5,4 m.
  ProfileCam  – Hikrobot MV-CS050-10: 5 MP global shutter (2448×2048, 3,45 µm).
                Ser laserstrippen i vinkel; global shutter krävs i rörelse.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LineLaser:
    name: str = "iadiy LM9R650H100L60"
    wavelength_nm: float = 650.0          # [datablad]
    power_mw: float = 100.0               # [datablad]
    fan_angle_deg: float = 60.0           # [datablad] "L60"
    diameter_mm: float = 9.0              # [datablad] "LM9"
    voltage_v: float = 3.0                # [datablad]
    working_distance_mm: float = 1000.0   # [designval] ~1 m -> ren, tunn linje
    line_width_mm: float = 0.25           # [designval] strippens bredd vid fokus

    @property
    def line_length_mm(self) -> float:
        """Belyst linjelängd vid working_distance (2·WD·tan(fan/2)) [härlett]."""
        return 2.0 * self.working_distance_mm * math.tan(math.radians(self.fan_angle_deg / 2))


@dataclass
class SurfaceCam:
    """Färg-linjekamera för ytan (8K-familjen, färgvariant av MV-XGLC83BM)."""
    name: str = "Hikrobot 8K färg-linjekamera (10GigE)"
    px_across: int = 8192                 # [datablad] 8K
    tdi_stages: int = 4                   # [datablad] 8192×4
    line_rate_hz: float = 109_000.0       # [datablad] max radtakt
    pixel_um: float = 5.0                 # [datablad] (8K-familjen ~5 µm)
    channels: int = 3                     # [designval] färg (RGB)
    bit_depth: int = 8                    # [datablad] per kanal
    interface: str = "10GigE"             # [datablad]


@dataclass
class ProfileCam:
    """Area-kamera som ser laserstrippen (triangulering)."""
    name: str = "Hikrobot MV-CS050-10"
    width_px: int = 2448                  # [datablad]
    height_px: int = 2048                 # [datablad] (Sony IMX264, 5 MP)
    pixel_um: float = 3.45                # [datablad]
    global_shutter: bool = True           # [datablad]
    interface: str = "GigE/USB3"          # [datablad] (GC/GM = GigE, UC/UM = USB3)
    frame_rate_hz: float = 35.0           # [datablad] full bild (snabbare med ROI)


@dataclass
class Rig:
    """Hela mätuppställningen (laser- och kamera-array) + härledda mått.

    Lasrar + profilkameror sitter i array längs LÄNGDEN, var och en täcker ett
    segment med överlapp (fusion). Brädan matas in med kortsidan; varje laser-
    stripe går TVÄRS de ~150 mm bredden. Ytan täcks av tilade färg-linjekameror.
    """
    laser: LineLaser = None
    surface_cam: SurfaceCam = None
    profile_cam: ProfileCam = None
    board_length_mm: float = 5400.0       # [designval] brädlängd
    board_width_mm: float = 150.0         # [designval] brädbredd
    surface_target_mm_per_px: float = 0.33  # [designval] önskad ytupplösning
    tri_angle_deg: float = 30.0           # [designval] vinkel laser–kamera
    overlap_mm: float = 150.0             # [designval] överlapp mellan segment
    profile_len_fov_mm: float = 1100.0    # [designval] profilkamerans FOV längs längden
    profile_rate_hz: float = 500.0        # [designval] profiler/s (area-kamera m. ROI)
    feed_mps: float = 0.25                # [designval] matningshastighet

    def __post_init__(self):
        self.laser = self.laser or LineLaser()
        self.surface_cam = self.surface_cam or SurfaceCam()
        self.profile_cam = self.profile_cam or ProfileCam()

    # --- ytkanal (färg-linjekameror tilade över längden) ---
    @property
    def n_surface_cams(self) -> int:
        """Antal färg-linjekameror för att nå önskad upplösning över längden."""
        per_cam_mm = self.surface_cam.px_across * self.surface_target_mm_per_px
        return max(1, math.ceil(self.board_length_mm / per_cam_mm))

    @property
    def surface_mm_per_px(self) -> float:
        return self.board_length_mm / (self.n_surface_cams * self.surface_cam.px_across)

    @property
    def surface_line_rate_at_feed(self) -> float:
        return self.feed_mps * 1000.0 / self.surface_mm_per_px

    @property
    def surface_gbit_s_per_cam(self) -> float:
        """Dataflöde/kamera vid drift (vår matning), färg [härlett]."""
        bits = self.surface_cam.px_across * self.surface_cam.bit_depth * self.surface_cam.channels
        return bits * self.surface_line_rate_at_feed / 1e9

    @property
    def surface_max_color_line_rate_hz(self) -> float:
        """Max färg-radtakt som ryms i 10GigE (~10 Gbit/s) [härlett]."""
        bits = self.surface_cam.px_across * self.surface_cam.bit_depth * self.surface_cam.channels
        return 10e9 / bits

    # --- laser-/kamera-array (triangulering, tvärs bredden, längs längden) ---
    @property
    def seg_len_mm(self) -> float:
        return self.profile_len_fov_mm

    @property
    def n_lasers(self) -> int:
        step = max(1e-6, self.seg_len_mm - self.overlap_mm)
        return max(1, math.ceil((self.board_length_mm - self.overlap_mm) / step))

    @property
    def n_profile_cams(self) -> int:
        return self.n_lasers                  # en profilkamera per lasersegment

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
        """Höjdupplösning: objektpixel / tan(θ). Grov (~mm) med den billiga
        prototyplasern + 5 MP-kamera över ett ~1 m-segment; dedikerad
        profilsensor ger finare. Range begränsas av DOF (lins/Scheimpflug)."""
        return self.profile_mm_per_px_len / math.tan(math.radians(self.tri_angle_deg))

    # --- mätpunkter (cross-feed: brädan rör sig i sidled, sensorer längs längden) ---
    # En profil/pixelrad per exponering; tätheten i matningsled = hastighet/takt.
    def feed_for_takt(self, boards_per_min: float, pitch_mm: float = 250.0) -> float:
        """Matningshastighet (m/s) för en given takt och brädpitch."""
        return pitch_mm / 1000.0 * boards_per_min / 60.0

    def measurement_points(self, feed_mps: float | None = None) -> dict:
        """Mätpunkter per bräda vid given matning (cross-feed: brädan matas i
        sidled förbi de stationära modulerna; varje laserlinje löper LÄNGS sitt
        längdsegment). Tätheten tvärs matningen (bredden) beror på hastigheten."""
        v = feed_mps if feed_mps is not None else self.feed_mps
        prof_pitch_mm = v * 1000.0 / self.profile_rate_hz   # profilavstånd i matningsled
        width_profiles = self.board_width_mm / prof_pitch_mm  # profiler medan bredden passerar
        # PER LASER/MODUL: punkter längs sitt segment (kamerans px) × profiler
        per_laser_pts = self.profile_cam.width_px * width_profiles
        # höjd/laser totalt: alla moduler
        length_pts = self.n_profile_cams * self.profile_cam.width_px
        # yta/färg: px tvärs längden × pixelrader medan bredden passerar
        surf_px_across = self.n_surface_cams * self.surface_cam.px_across
        surf_rows = self.board_width_mm / self.surface_mm_per_px   # kvadratiska px
        return {
            "feed_mps": round(v, 3),
            "laser_width_pitch_mm": round(prof_pitch_mm, 3),
            "laser_width_profiles": round(width_profiles),
            "per_laser_length_pts": self.profile_cam.width_px,
            "per_laser_points_per_board": round(per_laser_pts),
            "laser_length_pts_total": length_pts,
            "laser_points_per_board": round(length_pts * width_profiles),
            "surface_px_across": surf_px_across,
            "surface_rows": round(surf_rows),
            "surface_px_per_board": round(surf_px_across * surf_rows),
        }

    def summary(self) -> dict:
        return {
            # yta
            "surface_cam": self.surface_cam.name,
            "n_surface_cams": self.n_surface_cams,
            "surface_mm_per_px": round(self.surface_mm_per_px, 3),
            "surface_line_rate_hz@feed": round(self.surface_line_rate_at_feed),
            "surface_gbit_s_per_cam@feed": round(self.surface_gbit_s_per_cam, 3),
            "surface_max_color_line_rate_kHz@10GigE": round(self.surface_max_color_line_rate_hz / 1e3),
            # laser/höjd
            "laser": self.laser.name,
            "fan_deg": self.laser.fan_angle_deg,
            "working_distance_mm": self.laser.working_distance_mm,
            "laser_line_capability_mm": round(self.laser.line_length_mm),
            "laser_covers_width_mm": self.board_width_mm,
            "profile_cam": self.profile_cam.name,
            "seg_len_mm (kamera-FOV/längd)": round(self.seg_len_mm),
            "overlap_mm": self.overlap_mm,
            "n_lasers": self.n_lasers,
            "n_profile_cams": self.n_profile_cams,
            "tri_angle_deg": self.tri_angle_deg,
            "height_resolution_mm": round(self.height_resolution_mm, 4),
        }
