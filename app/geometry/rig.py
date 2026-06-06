"""EN sanningskälla för riggens geometri.

Samma tal som i ritningen ``tools/draw_head_mech.py`` → ``head-mech.svg`` så att
GUI:t och konstruktionsritningen aldrig kan säga emot varandra. Allt i mm/grader.

Dubbel-oblik mäthuvud:
  • Två profilhuvuden (RÖD 650 vänster, GRÖN 520 höger), vart och ett med kamera
    + linjelaser på SAMMA sida, monterade på var sin sida om brädan och blickande
    oblikt in mot samma laserlinje.
  • Kamera-arm 20° från lod, laser-arm 40° från lod → trianguleringsvinkel θ=30°,
    huvudets obliquity (siktbisektris) = 30°.
  • Ytkameran (4K färg-radkamera) hänger i CENTRUM, rakt ned, på 400 mm.
  • Punktlasrarna (LR400) sitter uppströms och ankrar absolut tjocklek.

Cross-feed: laserlinjen löper LÄNGS brädans längd (X, 500 mm); brädan matas i
BREDD (Y, 75 mm). Tjocklek = Z.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RigGeometry:
    # --- bräda (prototyp) ---
    board_len_mm: float = 500.0          # X — längs laserlinjen
    board_width_mm: float = 75.0         # Y — matningsled
    board_thick_mm: float = 20.0         # Z — nominell tjocklek

    # --- optik / armar (= head-mech.svg) ---
    work_distance_mm: float = 710.0      # WD längs den oblika siktlinjen
    cam_arm_deg: float = 20.0            # kamera-arm, vinkel från lod
    laser_arm_deg: float = 40.0          # laser-arm, vinkel från lod
    surface_cam_wd_mm: float = 400.0     # ytkamera rakt ned i centrum

    # --- sensorer ---
    profile_px_long: int = 2448          # MV-CS050 lång axel (längs linjen)
    profile_px_short: int = 2048         # kort axel (höjd/triangulering)
    surface_px: int = 4096               # Huateng 4K radkamera
    point_lasers_x_mm: tuple = (60.0, 250.0, 440.0)   # LR400 V / C / H längs X

    @property
    def tri_angle_deg(self) -> float:
        """Trianguleringsvinkel θ = laser-arm − kamera-arm."""
        return self.laser_arm_deg - self.cam_arm_deg

    @property
    def oblique_deg(self) -> float:
        """Huvudets obliquity = siktbisektrisen mellan armarna."""
        return (self.cam_arm_deg + self.laser_arm_deg) / 2.0

    # ---- härledda monteringspunkter (mm, relativt brädmitt i tvärsnittet) ----
    @property
    def cam_height_mm(self) -> float:
        return self.work_distance_mm * math.cos(math.radians(self.cam_arm_deg))   # ~667

    @property
    def cam_offset_mm(self) -> float:
        return self.work_distance_mm * math.sin(math.radians(self.cam_arm_deg))   # ~243

    @property
    def laser_height_mm(self) -> float:
        return self.work_distance_mm * math.cos(math.radians(self.laser_arm_deg)) # ~544

    @property
    def laser_offset_mm(self) -> float:
        return self.work_distance_mm * math.sin(math.radians(self.laser_arm_deg)) # ~456

    @property
    def baseline_mm(self) -> float:
        """Sidledsavstånd kamera↔laser (fysisk monteringsbaslinje)."""
        return 2.0 * self.work_distance_mm * math.sin(math.radians(self.tri_angle_deg / 2.0))

    # ---- upplösningar (mm/px) ----
    @property
    def surface_mm_per_px(self) -> float:
        return self.board_len_mm / self.surface_px            # ~0,122

    @property
    def profile_lat_mm_per_px(self) -> float:
        return self.board_len_mm / self.profile_px_long       # ~0,204

    @property
    def board_aspect(self) -> float:
        """Längd/bredd — för att rita ytan i RÄTT proportion (≈6,67:1)."""
        return self.board_len_mm / self.board_width_mm

    def summary(self) -> dict:
        return {
            "board_mm": (self.board_len_mm, self.board_width_mm, self.board_thick_mm),
            "WD_mm": self.work_distance_mm,
            "cam_arm_deg": self.cam_arm_deg,
            "laser_arm_deg": self.laser_arm_deg,
            "theta_deg": self.tri_angle_deg,
            "oblique_deg": self.oblique_deg,
            "cam_height_mm": round(self.cam_height_mm),
            "cam_offset_mm": round(self.cam_offset_mm),
            "laser_height_mm": round(self.laser_height_mm),
            "laser_offset_mm": round(self.laser_offset_mm),
            "baseline_mm": round(self.baseline_mm),
            "surface_cam_wd_mm": self.surface_cam_wd_mm,
            "surface_mm_per_px": round(self.surface_mm_per_px, 4),
            "profile_lat_mm_per_px": round(self.profile_lat_mm_per_px, 4),
        }


# global instans — importera denna överallt
RIG = RigGeometry()
