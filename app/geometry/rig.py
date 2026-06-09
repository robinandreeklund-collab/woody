"""EN sanningskälla för riggens geometri.

Samma tal som i ritningen ``tools/draw_head_mech.py`` → ``head-mech.svg`` så att
GUI:t och konstruktionsritningen aldrig kan säga emot varandra. Allt i mm/grader.

Dubbel-oblik mäthuvud:
  • Två profilhuvuden (RÖD 650 vänster, GRÖN 520 höger), vart och ett med kamera
    + linjelaser på SAMMA sida, monterade på var sin sida om brädan och blickande
    oblikt in mot samma laserlinje.
  • Kamera-arm 25° från lod, laser-arm 50° från lod → trianguleringsvinkel θ=25°,
    huvudets obliquity (siktbisektris) = 37,5°.
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
    work_distance_mm: float = 760.0      # WD längs den oblika siktlinjen
    cam_arm_deg: float = 25.0            # kamera-arm, vinkel från lod
    laser_arm_deg: float = 50.0          # laser-arm, vinkel från lod
    surface_cam_wd_mm: float = 400.0     # ytkamera rakt ned i centrum

    # --- sensorer ---
    profile_px_long: int = 2448          # MV-CS050 lång axel (längs linjen)
    profile_px_short: int = 2048         # kort axel (höjd/triangulering)
    surface_px: int = 4096               # Huateng 4K radkamera
    point_lasers_x_mm: tuple = (60.0, 250.0, 440.0)   # LR400 V / C / H längs X
    # LR400-ankaret sitter UPPSTRÖMS (eget mätplan före lasertrianguleringen), så det
    # mäter varje rads absoluta tjocklek INNAN den når profil-FOV → ingen 655 nm-
    # interferens mot profilkamerorna och ingen modul-/skuggkrock. Feed-offset:
    lr_lead_mm: float = 45.0

    # --- fysiska kroppar (för montering & krock) ---
    # VIKTIGT: WD-datum = laserns FRÄMRE apertur (Powell-linsen = fläktens virtuella
    # origo). Det är den punkt som sitter på trianguleringsgeometrin. Modulkroppen
    # sticker ut BAKÅT längs laser-armen → mäts i framkant, inte bakkant.
    laser_len_mm: float = 99.0           # linjelaser-modulens längd (optisk axel)
    laser_dia_mm: float = 18.0           # modulens diameter (för krock/clearance)
    cam_body_len_mm: float = 42.0        # MV-CS050-kropp (datum = sensorplan)
    cam_lens_len_mm: float = 35.0        # MVL-MF1228M 12 mm-objektiv (sticker framåt)

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
        return self.work_distance_mm * math.cos(math.radians(self.laser_arm_deg)) # ~489

    @property
    def laser_offset_mm(self) -> float:
        return self.work_distance_mm * math.sin(math.radians(self.laser_arm_deg)) # ~582

    @property
    def baseline_mm(self) -> float:
        """Sidledsavstånd kamera↔laser (fysisk monteringsbaslinje)."""
        return 2.0 * self.work_distance_mm * math.sin(math.radians(self.tri_angle_deg / 2.0))

    # ---- laserns fysiska placering (datum = FRÄMRE apertur, kropp bakåt) ----
    def _pt(self, dist_mm: float, arm_deg: float) -> tuple:
        """(offset, höjd) för en punkt på en arm-linje, avstånd från brädpunkten."""
        a = math.radians(arm_deg)
        return (dist_mm * math.sin(a), dist_mm * math.cos(a))

    @property
    def laser_front_mm(self) -> tuple:
        """Laserns främre apertur = WD-datum (offset, höjd). Här ligger fläktens origo."""
        return self._pt(self.work_distance_mm, self.laser_arm_deg)

    @property
    def laser_back_mm(self) -> tuple:
        """Laserns bakkant/montage-ände, 99 mm bakåt längs armen (offset, höjd)."""
        return self._pt(self.work_distance_mm + self.laser_len_mm, self.laser_arm_deg)

    @property
    def laser_line_len_mm(self) -> float:
        """Laserlinjens längd på brädan vid WD (Powell 45° → överfyller 500 mm)."""
        return 2.0 * self.work_distance_mm * math.tan(math.radians(45.0 / 2.0))

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
