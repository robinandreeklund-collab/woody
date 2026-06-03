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


@dataclass
class SegConfig:
    """Hyperparametrar för segmenteringsmodellen och dess träning.

    Standardvärdena är satta för att köra och verifieras på CPU mot den
    syntetiska generatorn på några minuter. För skarp träning mot Kodytek
    på GPU: höj n_train_boards/epochs/base_channels och peka loaders mot
    KodytekDataset (se src/dataset.py).
    """
    # Data (samma geometri som demobrädan i run_demo)
    n_classes: int = 7
    mm_per_px: float = 0.5
    board_length_mm: float = 1200.0
    board_width_mm: float = 125.0
    tile: int = 160                  # kvadratisk träningsruta (px); delbar med 2**depth
    n_train_boards: int = 12         # antal syntetiska brädor i träningsmängden
    n_val_boards: int = 3
    train_seed: int = 1000           # fröoffset så tränings-/valbrädor aldrig krockar
    val_seed: int = 9000
    p_defect_tile: float = 0.5       # andel rutor som centreras kring en defekt

    # Modell (kompakt U-Net)
    base_channels: int = 24
    depth: int = 3                   # antal ned-/uppsamplingssteg

    # Träning
    epochs: int = 8
    steps_per_epoch: int = 50
    batch_size: int = 8
    lr: float = 1e-3
    weight_decay: float = 1e-4
    dice_weight: float = 0.3         # total = CE + dice_weight * Dice
    use_class_weights: bool = True   # väg upp sällsynta defektklasser i CE
    augment: bool = True
    num_workers: int = 0

    # Körning / utdata
    device: str = "auto"             # "auto" | "cpu" | "cuda"
    out_dir: str = "outputs"
    ckpt_name: str = "seg_unet.pt"
    seed: int = 0

    def resolved_device(self) -> str:
        if self.device != "auto":
            return self.device
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"

    @classmethod
    def smoke(cls) -> "SegConfig":
        """Minimal konfig för snabb rökverifiering (sekunder–någon minut)."""
        return cls(tile=128, n_train_boards=4, n_val_boards=2,
                   base_channels=16, depth=3, epochs=2, steps_per_epoch=15,
                   batch_size=6)
