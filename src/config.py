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


# Defektklasser – ENAD taxonomi (samma i rastrerare, syntetik, backend och GUI)
CLASSES = {
    0: "clear_wood",
    1: "knot",         # Kvist (levande + död)
    2: "crack",        # Spricka
    3: "blue_stain",   # Blånad
    4: "wane",         # Vankant
    5: "rot",          # Röta
    6: "hole",         # Hål (urslagen/saknad kvist)
}

CLASS_COLORS = {  # för etikettöverlägg (RGB 0-1) – matchar GUI:ts färger
    0: (0.00, 0.00, 0.00),
    1: (0.831, 0.584, 0.247),
    2: (0.824, 0.325, 0.247),
    3: (0.333, 0.467, 0.741),
    4: (0.627, 0.447, 0.769),
    5: (0.435, 0.631, 0.361),
    6: (0.812, 0.435, 0.620),
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
    dataset: str = "synthetic"       # "synthetic" | "kodytek" | "combined"
    data_root: str = ""              # rastrerad Kodytek-root (images/ + masks/)
    val_frac: float = 0.15           # tränings-/valdelning för kodytek
    extra_channels: tuple = ("nir",)  # utöver RGB: NIR-strobe (blånad/röta syns
    #                                   bäst där). Lägg till "relief"/"grain_dev"
    #                                   för sprickor/kvist – se run_ablation.py.
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

    # Kodytek-resampling (a) + kombinerad träning (b). Kodytek-bilderna är
    # ~168×154 mm SEKTIONER (line-scan 0,060×0,150 mm/px), inte hela brädor.
    target_mm_per_px: float = 0.0    # >0: resampla Kodytek-rutor till denna mm/px (matcha riggen)
    kodytek_len_mm: float = 168.0    # sektionens LÄNGSTA axel (2800 px @ 16,66 px/mm)
    kodytek_width_mm: float = 154.0  # sektionens KORTASTE axel (1024 px @ 6,67 px/mm)
    synth_frac: float = 0.5          # andel syntetiska rutor i "combined"

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

    @classmethod
    def gpu_kodytek(cls, data_root: str) -> "SegConfig":
        """Skarp träning mot rastrerad Kodytek på GPU (t.ex. RTX 5090).
        device='auto' plockar upp GPU:n. Justera fritt."""
        return cls(dataset="kodytek", data_root=data_root,
                   tile=320, base_channels=48, depth=4,
                   epochs=40, steps_per_epoch=200, batch_size=16,
                   num_workers=8, extra_channels=(), device="auto",
                   ckpt_name="seg_kodytek.pt")

    @classmethod
    def gpu_kodytek_scaled(cls, data_root: str) -> "SegConfig":
        """(a) Kodytek resamplad till riggens 0,33 mm/px så pixelskalan matchar
        de sensorer vi tänker använda (RGB). Annars som gpu_kodytek."""
        return cls(dataset="kodytek", data_root=data_root,
                   tile=320, base_channels=48, depth=4,
                   epochs=40, steps_per_epoch=200, batch_size=16,
                   num_workers=8, extra_channels=(), device="auto",
                   target_mm_per_px=0.33, dice_weight=0.6,
                   ckpt_name="seg_kodytek_033.pt")

    @classmethod
    def gpu_combined(cls, data_root: str) -> "SegConfig":
        """(b) Kombinerad träning: syntetisk rigg-data (NIR + riggens 0,33 mm/px)
        BLANDAT med riktiga Kodytek-rutor (resamplade till samma mm/px). Modellen
        ser både verklig appearance och sensorernas upplösning/NIR (4 kanaler)."""
        return cls(dataset="combined", data_root=data_root,
                   tile=320, base_channels=48, depth=4,
                   epochs=40, steps_per_epoch=200, batch_size=16,
                   num_workers=4, extra_channels=("nir",), device="auto",
                   target_mm_per_px=0.33, mm_per_px=0.33,
                   board_length_mm=1600.0, board_width_mm=150.0,
                   n_train_boards=16, n_val_boards=4, synth_frac=0.5,
                   dice_weight=0.6, ckpt_name="seg_combined.pt")


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
SEVERE_DEFECTS = (2, 5, 6)      # spricka, röta, hål
MODERATE_DEFECTS = (1, 3)       # kvist, blånad
WANE_DEFECT = 4                 # vankant


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
