"""Riggens hårdvara + självkonsistent optik/placering för den fysikaliska simmen.

Varje fält är märkt [datablad] (produktspec) eller [designval] (vår optik/
montering). Geometrin är härledd så den hänger ihop: lins ↔ arbetsavstånd ↔ FOV
↔ trianguleringsvinkel ↔ höjdupplösning ↔ baslinje. Cross-feed (alt A): brädan
matas i sidled förbi 6 stationära laser+kamera-moduler längs längden; varje
laserlinje löper LÄNGS sitt längdsegment.

Valda produkter:
  LineLaser   – iadiy LM9R650H100L60 (650 nm, 100 mW, 60° linje). CW-modul –
                ingen egen bildtakt; profiltakten sätts av profilkameran.
  SurfaceCam  – MindVision MV-XGLC83BM-T4-90 (10GigE mono 8K linjekamera, 7 µm,
                4-line TDI, 109,89 kHz @ 8-bit / 87,7 kHz @ 12-bit). Färg fås via
                strobad sekventiell belysning (RGB + NIR).
  ProfileCam  – Hikrobot MV-CS050-10UC (USB3, 5 MP global shutter, IMX264,
                60 fps @ 2448×2048).
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
    line_width_mm: float = 0.25           # [designval] strippens bredd vid fokus

    def working_distance_for(self, line_len_mm: float) -> float:
        """Arbetsavstånd som ger en linje av önskad längd (2·WD·tan(fan/2))."""
        return line_len_mm / (2.0 * math.tan(math.radians(self.fan_angle_deg / 2)))


@dataclass
class SurfaceCam:
    """MindVision MV-XGLC83BM-T4-90 (verifierat datablad). Mono 4-line TDI; färg
    fås via kamerans 3 strobade ljuskälle-utgångar (sekventiell RGB-belysning)."""
    name: str = "MindVision MV-XGLC83BM-T4-90"  # [datablad]
    px_across: int = 8192                 # [datablad] 8K
    tdi_stages: int = 4                   # [datablad] 4-line TDI
    pixel_um: float = 7.0                 # [datablad] 7×7 µm (sensor 57,344 mm)
    mono: bool = True                     # [datablad] (färg via strobade ljus)
    color_strobe_lights: int = 4          # [designval] 3 utgångar (R/G/B) + NIR
    nir_channel: bool = True              # [designval] NIR-strobe -> blånad/röta
    line_rate_hz: float = 109_890.0       # [datablad] mono 8-bit (87,7 kHz @ 12-bit)
    bit_depth: int = 8                    # [datablad] (10/12-bit möjligt)
    interface: str = "10GBase-T (10GigE)" # [datablad]
    mount: str = "M72, fläns 12 mm"       # [datablad]
    power_w: float = 10.0                 # [datablad] <10 W

    @property
    def sensor_w_mm(self) -> float:
        return self.px_across * self.pixel_um / 1000.0   # 57.344 mm


@dataclass
class ProfileCam:
    name: str = "Hikrobot MV-CS050-10UC"
    width_px: int = 2448                  # [datablad] (lång axel = längs segmentet)
    height_px: int = 2048                 # [datablad] (kort axel = höjd/triangulering)
    pixel_um: float = 3.45                # [datablad] Sony IMX264
    global_shutter: bool = True           # [datablad]
    frame_rate_full_hz: float = 60.0      # [datablad] 60 fps @ 2448×2048 (USB3; GigE-varianten -10GC ≈ 35,6 fps)
    interface: str = "USB3"               # [datablad] UC = USB3

    @property
    def sensor_w_mm(self) -> float:
        return self.width_px * self.pixel_um / 1000.0

    @property
    def sensor_h_mm(self) -> float:
        return self.height_px * self.pixel_um / 1000.0


@dataclass
class Rig:
    laser: LineLaser = None
    surface_cam: SurfaceCam = None
    profile_cam: ProfileCam = None
    board_length_mm: float = 5400.0       # [designval]
    board_width_mm: float = 150.0         # [designval]
    board_thickness_mm: float = 22.0      # [designval]

    # --- ytkanal ---
    surface_target_mm_per_px: float = 0.33  # [designval] önskad ytupplösning
    surface_wd_mm: float = 0.0              # [designval] 0 => auto: ytkameran på SAMMA nivå som linjelasern

    # --- profil/triangulering: optik som hänger ihop ---
    profile_lens_mm: float = 8.0          # [designval] objektiv (8 mm -> ~1,1 m FOV/modul)
    profile_wd_mm: float = 1040.0         # [designval] arbetsavstånd profilkamera
    tri_angle_deg: float = 30.0           # [designval] trianguleringsvinkel (Scheimpflug)
    depth_range_mm: float = 50.0          # [designval] mätrange i höjd (±25 mm)
    overlap_mm: float = 150.0             # [designval] överlapp mellan segment

    # --- drift ---
    profile_rate_hz: float = 500.0        # [designval] profiler/s via ROI-band (~250 av 2048 rader: 60 fps·2048/250 ≈ 490 fps, ryms i databladet)
    feed_mps: float = 0.25                # [designval] matningshastighet

    def __post_init__(self):
        self.laser = self.laser or LineLaser()
        self.surface_cam = self.surface_cam or SurfaceCam()
        self.profile_cam = self.profile_cam or ProfileCam()
        # ytkameran monteras på samma nivå som linjelasern (förskjuten i matningsled)
        if not self.surface_wd_mm:
            self.surface_wd_mm = round(self.laser_working_distance_mm)

    # ---------- ytkanal (färg-linjekameror tilade över längden) ----------
    @property
    def n_surface_cams(self) -> int:
        per_cam_mm = self.surface_cam.px_across * self.surface_target_mm_per_px
        return max(1, math.ceil(self.board_length_mm / per_cam_mm))

    @property
    def surface_mm_per_px(self) -> float:
        return self.board_length_mm / (self.n_surface_cams * self.surface_cam.px_across)

    @property
    def surface_fov_per_cam_mm(self) -> float:
        return self.board_length_mm / self.n_surface_cams

    @property
    def surface_lens_mm(self) -> float:
        """M72-objektiv för önskad FOV: f = sensor·WD/FOV."""
        return self.surface_cam.sensor_w_mm * self.surface_wd_mm / self.surface_fov_per_cam_mm

    @property
    def surface_line_rate_at_feed(self) -> float:
        return self.feed_mps * 1000.0 / self.surface_mm_per_px

    @property
    def surface_color_line_rate_hz(self) -> float:
        """Effektiv färg-radtakt via 3 strobade ljus (3 mono-pass/rad)."""
        return self.surface_cam.line_rate_hz / self.surface_cam.color_strobe_lights

    @property
    def surface_gbit_s(self) -> float:
        """Bandbredd vid max radtakt (mono 8-bit) – ryms i 10GigE?"""
        return self.surface_cam.px_across * self.surface_cam.bit_depth * \
            self.surface_cam.line_rate_hz / 1e9

    # ---------- profil/triangulering (härledd optik) ----------
    @property
    def seg_len_mm(self) -> float:
        """Längdsegment/modul = profilkamerans FOV (sensor·WD/lins)."""
        return self.profile_cam.sensor_w_mm * self.profile_wd_mm / self.profile_lens_mm

    @property
    def lateral_res_mm(self) -> float:
        """Upplösning längs längden = FOV / px."""
        return self.seg_len_mm / self.profile_cam.width_px

    @property
    def height_resolution_mm(self) -> float:
        """Höjdupplösning ur trianguleringen: lateral_res / tan(θ)."""
        return self.lateral_res_mm / math.tan(math.radians(self.tri_angle_deg))

    @property
    def baseline_mm(self) -> float:
        """Sidledsavstånd laser↔kamera (WD·tan θ) – fysisk monteringsbaslinje."""
        return self.profile_wd_mm * math.tan(math.radians(self.tri_angle_deg))

    @property
    def laser_working_distance_mm(self) -> float:
        """Laserns WD vald så linjelängden ≈ segmentlängden."""
        return self.laser.working_distance_for(self.seg_len_mm)

    @property
    def n_lasers(self) -> int:
        step = max(1e-6, self.seg_len_mm - self.overlap_mm)
        return max(1, math.ceil((self.board_length_mm - self.overlap_mm) / step))

    @property
    def n_profile_cams(self) -> int:
        return self.n_lasers

    def segments(self):
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
        return self.lateral_res_mm

    # ---------- mätpunkter (cross-feed, beror på hastigheten) ----------
    def feed_for_takt(self, boards_per_min: float, pitch_mm: float = 250.0) -> float:
        return pitch_mm / 1000.0 * boards_per_min / 60.0

    def measurement_points(self, feed_mps: float | None = None) -> dict:
        v = feed_mps if feed_mps is not None else self.feed_mps
        prof_pitch_mm = v * 1000.0 / self.profile_rate_hz
        width_profiles = self.board_width_mm / prof_pitch_mm
        per_laser_pts = self.profile_cam.width_px * width_profiles
        length_pts = self.n_profile_cams * self.profile_cam.width_px
        surf_px_across = self.n_surface_cams * self.surface_cam.px_across
        surf_rows = self.board_width_mm / self.surface_mm_per_px
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

    def placement(self) -> dict:
        """Optimerad, självkonsistent placering (för montering/beställning)."""
        return {
            "feed": "cross-feed (brädan i sidled förbi stationära moduler)",
            "n_modules": self.n_lasers,
            "seg_len_mm": round(self.seg_len_mm),
            "overlap_mm": self.overlap_mm,
            "profile_lens_mm": self.profile_lens_mm,
            "profile_wd_mm": self.profile_wd_mm,
            "laser_wd_mm": round(self.laser_working_distance_mm),
            "tri_angle_deg": self.tri_angle_deg,
            "baseline_laser_cam_mm": round(self.baseline_mm),
            "lateral_res_mm": round(self.lateral_res_mm, 3),
            "height_res_mm": round(self.height_resolution_mm, 3),
            "depth_range_mm": self.depth_range_mm,
            "surface_cams": self.n_surface_cams,
            "surface_lens_mm": round(self.surface_lens_mm),
            "surface_wd_mm": self.surface_wd_mm,
            "surface_mm_per_px": round(self.surface_mm_per_px, 3),
        }

    def summary(self) -> dict:
        return {
            "surface_cam": self.surface_cam.name,
            "n_surface_cams": self.n_surface_cams,
            "surface_mm_per_px": round(self.surface_mm_per_px, 3),
            "surface_lens_mm (M72)": round(self.surface_lens_mm),
            "surface_wd_mm": self.surface_wd_mm,
            "surface_color_line_rate_kHz (strobe RGB)": round(self.surface_color_line_rate_hz / 1e3, 1),
            "surface_gbit_s@max": round(self.surface_gbit_s, 1),
            "laser": self.laser.name,
            "laser_wd_mm": round(self.laser_working_distance_mm),
            "profile_cam": self.profile_cam.name,
            "profile_lens_mm": self.profile_lens_mm,
            "profile_wd_mm": self.profile_wd_mm,
            "seg_len_mm": round(self.seg_len_mm),
            "overlap_mm": self.overlap_mm,
            "n_lasers": self.n_lasers,
            "n_profile_cams": self.n_profile_cams,
            "tri_angle_deg": self.tri_angle_deg,
            "baseline_mm": round(self.baseline_mm),
            "lateral_res_mm": round(self.lateral_res_mm, 3),
            "height_resolution_mm": round(self.height_resolution_mm, 3),
            "depth_range_mm": self.depth_range_mm,
        }
