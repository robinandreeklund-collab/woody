"""Konfiguration för den tvärmatade virkesinspektionen.

Alla värden speglar uppställningen vi resonerat fram:
  - brädan ligger tvärs över transportkedjorna (tvärmatning)
  - brädans LÄNGD spänner över mätzonen
  - brädans BREDD passerar genom zonen i sidled (= skanningsaxeln)
"""
from dataclasses import dataclass, field


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
    extra_channels: tuple = ()       # extra ingångar utöver RGB, t.ex.
    #                                  ("relief", "grain_dev"). Bäst på subtil/
    #                                  färgtvetydig data – se run_ablation.py.
    mm_per_px: float = 0.5
    board_length_mm: float = 1200.0
    board_width_mm: float = 125.0
    tile: int = 160                  # kvadratisk träningsruta (px); delbar med 2**depth
    subtle_defects: bool = False     # True: defekter osynliga i färg (sensortest)
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

    @property
    def in_channels(self) -> int:
        return 3 + len(self.extra_channels)

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


@dataclass
class SensorRig:
    """Parametrar för de kompletterande sensorkanalerna (utöver färg+laser).

    Fotometrisk stereo: riktade LED för relief/sprickor.
    Tracheid:           laserspridning -> fiberriktning/hållfasthet.
    Undersida:          kamera underifrån genom springorna mellan kedjorna.
    """
    # Fotometrisk stereo
    ps_n_lights: int = 4              # antal riktade LED runt brädan
    ps_elevation_deg: float = 30.0    # ljusets höjd över ytan
    ps_start_deg: float = 0.0

    # Tracheid-effekt
    tracheid_clear_aspect: float = 2.6  # spotens längd/bredd i ren ved (kvist -> ~1)

    # Undersida via kedjespringor
    n_chains: int = 6                 # antal transportkedjor under brädan
    chain_width_mm: float = 25.0      # bredd per kedja (ockluderar undersidan)
    underside_seed_offset: int = 4096  # eget frö -> undersidan har egna defekter


# Defektkategorier för kvalitetsklassning (klass-id enligt CLASSES)
SEVERE_DEFECTS = (2, 3, 6)      # död kvist, spricka, märg
MODERATE_DEFECTS = (1, 4)       # levande kvist, blånad
WANE_DEFECT = 5                 # vankant


@dataclass
class CutConfig:
    """Kap- och värdemodell. Efter klassningen avgör en DP-optimering var varje
    bräda kapas i tillåtna längder för att maximera totalvärdet. Alla siffror
    är tänkta att justeras mot en verklig prislista."""
    # Tillåtna kaplängder (m). Bör vara multiplar av step_mm.
    allowed_lengths_m: tuple = (3.0, 2.7, 2.4)
    step_mm: float = 30.0             # upplösning för kapositioner i DP:n
    kerf_mm: float = 4.0              # sågsnittets bredd (spill per kap)

    # Pris (SEK) per meter och kvalitetsklass
    grade_prices_per_m: dict = field(default_factory=lambda: {
        "A": 120.0, "B": 80.0, "C": 45.0, "reject": 8.0})

    # Klassningsregler (andel av bitens yta per defektkategori)
    reject_severe_frac: float = 0.05  # > så mycket allvarlig defekt -> vrak
    w_severe: float = 3.0             # vikter i defektpoängen
    w_moderate: float = 1.0
    w_wane: float = 0.5
    a_max_score: float = 0.004        # poäng <= -> klass A
    b_max_score: float = 0.030        #            -> klass B
    c_max_score: float = 0.120        #            -> klass C, annars vrak
