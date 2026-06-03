"""Konfiguration för den tvärmatade virkesinspektionen.

Alla värden speglar uppställningen vi resonerat fram:
  - brädan ligger tvärs över transportkedjorna (tvärmatning)
  - brädans LÄNGD spänner över mätzonen
  - brädans BREDD passerar genom zonen i sidled (= skanningsaxeln)
"""
from dataclasses import dataclass


@dataclass
class LineConfig:
    # Geometri
    board_length_m: float = 5.4      # tvärs banan, spänner över mätzonen
    board_width_m: float = 0.125     # passerar zonen i sidled (100-150 mm)
    thickness_mm: float = 22.0

    # Genomströmning / matning
    boards_per_min: int = 60
    board_spacing_m: float = 0.25    # centrum-till-centrum längs matningen

    # Optik / sensor
    target_mm_per_px: float = 0.33   # upplösning tvärs längden
    color_channels: int = 3
    bit_depth: int = 8

    @property
    def boards_per_sec(self) -> float:
        return self.boards_per_min / 60.0

    @property
    def sideways_speed_mps(self) -> float:
        """Sidledshastighet genom mätzonen."""
        return self.board_spacing_m * self.boards_per_sec

    @property
    def pixels_across_length(self) -> int:
        """Antal pixlar som krävs tvärs hela brädlängden."""
        return round(self.board_length_m * 1000 / self.target_mm_per_px)

    @property
    def line_rate_hz(self) -> float:
        """Radtakt för line-scan = hastighet / pixelstorlek."""
        return self.sideways_speed_mps * 1000.0 / self.target_mm_per_px

    @property
    def data_rate_mb_s(self) -> float:
        bytes_per_line = self.pixels_across_length * self.color_channels * (self.bit_depth / 8)
        return bytes_per_line * self.line_rate_hz / 1e6


# Defektklasser (matchar i stort sett den öppna Kodytek-datamängden)
CLASSES = {
    0: "clear_wood",
    1: "live_knot",
    2: "dead_knot",
    3: "crack",
    4: "blue_stain",
    5: "wane",
    6: "marrow",
}

CLASS_COLORS = {  # för etikettöverlägg (RGB 0-1)
    0: (0.00, 0.00, 0.00),
    1: (0.20, 0.80, 0.20),
    2: (0.85, 0.20, 0.20),
    3: (1.00, 0.55, 0.00),
    4: (0.20, 0.45, 0.95),
    5: (0.65, 0.45, 0.85),
    6: (0.95, 0.85, 0.10),
}
