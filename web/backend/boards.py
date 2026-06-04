"""Datakontrakt: gör en bräda ur src.board till det format GUI:t konsumerar,
samt U-Net-segmentering ur src.infer. Ersätter prototypens js/textures.js.

Klasstaxonomi: modellen/board.py använder (clear, live_knot, dead_knot, crack,
blue_stain, wane, marrow). GUI:t/cutplan använder (Frisk, Kvist, Spricka, Blånad,
Vankant, Röta, Hål). MODEL_TO_GUI mappar mellan dem – PROVISORISK tills taxonomin
fastställts (marrow -> Röta; GUI:ts Hål används inte av modellen).
"""
from __future__ import annotations

import base64
import io
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from src.grading import grade_board, GradeInput

from src.board import make_board
from src.features import build_features
from src.config import SegConfig
from src.photometric import surface_normals, relief_map


def find_checkpoint(cfg: SegConfig):
    """Torch-fri checkpoint-koll (så backenden kan köras utan torch när ingen
    modell finns – t.ex. CPU-deploy på Render)."""
    p = Path(cfg.out_dir) / cfg.ckpt_name
    return p if p.exists() else None

# modellklass (0..6) -> GUI-klass (0..6). Taxonomin är nu enad (config.CLASSES =
# rastrerarens = GUI:ts), så mappningen är identitet.
MODEL_TO_GUI = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

# nedskalning av texturer (full 10800x250 -> hanterbart för webben)
TEX_LEN = 1400


def _png_b64(rgb: np.ndarray) -> str:
    """HxWx3 uint8 -> data-URL PNG (kräver Pillow)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _downscale_rgb(rgb: np.ndarray, target_len: int = TEX_LEN) -> np.ndarray:
    """Nedskala längs längdaxeln (axel 0) till target_len rader (nearest)."""
    H = rgb.shape[0]
    if H <= target_len:
        return rgb
    idx = np.linspace(0, H - 1, target_len).astype(int)
    return rgb[idx]


def _features_from_label(label: np.ndarray, mm_per_px: float):
    """Defektinstanser ur en klasskarta -> [{cls, u, fv, area}] i GUI-taxonomi.
    u = position längs längden (0..1), fv = position längs bredden (0..1)."""
    H, W = label.shape
    counts = [0] * 7
    areas = [0.0] * 7
    features = []
    px_area_mm2 = mm_per_px * mm_per_px
    for model_cls in range(1, 7):
        gui_cls = MODEL_TO_GUI[model_cls]
        mask = label == model_cls
        if not mask.any():
            continue
        lab, n = ndimage.label(mask)
        if n == 0:
            continue
        centroids = ndimage.center_of_mass(mask, lab, range(1, n + 1))
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        for (r, c), sz in zip(centroids, sizes):
            counts[gui_cls] += 1
            area = float(sz) * px_area_mm2
            areas[gui_cls] += area
            features.append({"cls": gui_cls, "u": r / H, "fv": c / W, "area": area})
    return counts, areas, features


def board_payload(board: dict, target_len: int = TEX_LEN) -> dict:
    """Bygger GUI:ts board-datakontrakt ur en make_board-bräda."""
    color = board["color"]
    label = board["label"]
    height = board["height"]
    mm = board["mm_per_px"]
    H, W = label.shape

    # reliefkanal (fotometrisk stereo) som gråskala
    relief = relief_map(surface_normals(height, mm))
    relief_rgb = (np.clip(relief / (np.percentile(relief, 99) + 1e-6), 0, 1)
                  * 255).astype(np.uint8)
    relief_rgb = np.repeat(relief_rgb[..., None], 3, axis=2)

    # höjd som gråskala (för profil + höjdkanal)
    h_norm = np.clip((height - height.min()) / (np.ptp(height) + 1e-6), 0, 1)
    height_rgb = np.repeat((h_norm * 255).astype(np.uint8)[..., None], 3, axis=2)

    counts, areas, features = _features_from_label(label, mm)
    return {
        "id": None,
        "lengthMm": H * mm, "widthMm": W * mm, "mmPerPx": mm,
        "texLen": min(target_len, H),
        "color_png": _png_b64(_downscale_rgb(color, target_len)),
        "relief_png": _png_b64(_downscale_rgb(relief_rgb, target_len)),
        "height_png": _png_b64(_downscale_rgb(height_rgb, target_len)),
        "stats": {
            "counts": counts, "areas": [round(a, 1) for a in areas],
            "features": features,
            "defectArea": round(sum(areas), 1),
        },
    }


def segment_board(board: dict, seg_cfg: SegConfig | None = None):
    """U-Net-segmentering -> GUI-klasskarta + per-klass-stats + mIoU.
    Faller tillbaka på facit om ingen checkpoint finns (dokumenterat)."""
    seg_cfg = seg_cfg or SegConfig()
    ckpt = find_checkpoint(seg_cfg)
    if ckpt is not None:
        from src.infer import load_model, predict_board   # lazy: torch krävs bara här
        model, mcfg = load_model(str(ckpt))
        pred = predict_board(model, board, mcfg)
        source = "unet"
    else:
        pred = board["label"]
        source = "facit"

    gt = board["label"]
    # mIoU mot facit (per modellklass som finns)
    ious = []
    for c in range(7):
        p, g = pred == c, gt == c
        union = (p | g).sum()
        if union:
            ious.append((p & g).sum() / union)
    miou = float(np.mean(ious)) if ious else 1.0

    counts, areas, features = _features_from_label(pred, board["mm_per_px"])
    return {
        "source": source, "miou": round(miou, 3),
        "stats": {"counts": counts, "areas": [round(a, 1) for a in areas],
                  "features": features},
    }


def make_board_for(seed: int, width_mm: float = 125.0, length_m: float = 5.4,
                   mm_per_px: float = 0.5, subtle: bool = False):
    return make_board(length_mm=length_m * 1000, width_mm=width_mm,
                      mm_per_px=mm_per_px, seed=seed, subtle_defects=subtle)


# ---- engine payload: hela kedjan (färg + segmentering + features + kapplan) ----
import glob
import random as _random

from . import cutplan as _cutplan

# GUI-klassfärger (config.js-taxonomi) för frontendens overlay
GUI_RGB = {1: (212, 149, 63), 2: (210, 83, 63), 3: (85, 119, 189),
           4: (160, 114, 196), 5: (111, 161, 92), 6: (207, 111, 158)}
ENGINE_LEN = 1400          # texturlängd som motorn väntar sig

# Kodytek levereras i ~154 mm-sektioner (line-scan, 0,060×0,150 mm/px). En hel
# bräda byggs genom att stapla N konsekutiva sektioner längs längden. En liten
# pool färdigsydda brädor cachas (snabbt efter uppvärmning på långsam disk).
STITCH_N = 35              # sektioner per bräda (~5,4 m, matchar nominell brädlängd)
STITCH_POOL = 8            # antal olika brädor som cyklas i GUI:t
STITCH_MM = 0.30           # isotrop visnings-mm/px (≈ riggens 0,305)
SEC_LEN_MM = 153.6         # en sektions längd (1024 px @ 6,67 px/mm)
SEC_WIDTH_MM = 168.0       # en sektions bredd (2800 px @ 16,66 px/mm)


def _img_orient(arr_lw):
    """(length,width[,3]) logiskt -> (width,length[,3]) bildorientering (längd vågrätt)."""
    if arr_lw.ndim == 3:
        return np.transpose(arr_lw, (1, 0, 2))
    return arr_lw.T


def _downscale_len(arr, target=ENGINE_LEN):
    w = arr.shape[1]
    if w <= target:
        return arr
    idx = np.linspace(0, w - 1, target).astype(int)
    return arr[:, idx]


def _features_img(label_img, mm_per_px):
    """Features ur klasskarta i bildorientering: u=kol/längd, fv=rad/bredd."""
    H, W = label_img.shape
    counts = [0] * 7
    areas = [0.0] * 7
    feats = []
    pa = mm_per_px * mm_per_px
    crack_px = 0
    for cid in range(1, 7):
        mask = label_img == cid
        if not mask.any():
            continue
        if cid == 2:
            crack_px += int(mask.sum())
        lab, n = ndimage.label(mask)
        if n == 0:
            continue
        cents = ndimage.center_of_mass(mask, lab, range(1, n + 1))
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        for (r, c), sz in zip(cents, sizes):
            counts[cid] += 1
            area = float(sz) * pa
            areas[cid] += area
            feats.append({"cls": cid, "u": c / W, "fv": r / H, "area": area})
    return counts, areas, feats, crack_px * mm_per_px


def measured_height(label_img, mm_per_px, seed):
    """Höjdkartan kamerorna mäter: slumpad 3D-deformation + fin defekt-relief,
    läst av laser-/kamera-arrayen (triangulering, ocklusion, fusion).
    label_img i bildorientering (bredd, längd). Returnerar (z_img i bildorient.,
    warp, layout)."""
    from src.geometry import random_warp, warp_height, warp_summary
    from src.laser import simulate_array
    from src.hardware import Rig

    lab_lw = np.ascontiguousarray(label_img.T)             # (längd, bredd)
    Hl, Wl = lab_lw.shape
    length_mm = Hl * mm_per_px
    width_mm = Wl * mm_per_px
    # nedsampla för en snabb höjdsim
    if Hl > 700:
        idx = np.linspace(0, Hl - 1, 700).astype(int)
        lab_lw = lab_lw[idx]
        Hl = 700
    sim_mmpx = length_mm / Hl

    fine = np.zeros((Hl, Wl), np.float64)
    fine[lab_lw == 1] += 1.0        # kvist – liten upphöjning
    fine[lab_lw == 2] -= 3.0        # spricka – grop
    fine[lab_lw == 4] -= 1.0        # vankant
    fine[lab_lw == 6] -= 2.0        # hål

    rng = np.random.default_rng(seed)
    p = random_warp(rng)
    rig = Rig(board_length_mm=length_mm, board_width_mm=width_mm)
    z = warp_height(Hl, Wl, width_mm, p) + fine
    res = simulate_array(z, sim_mmpx, rig, seed=seed)
    zf = res["z_fused"]                                    # (längd, bredd) uppmätt höjd
    z_img = np.ascontiguousarray(zf.T)                     # tillbaka till bildorient.

    # Rakhet: kantkrok ur silhuetten, planböj/skevhet ur laserhöjden, med
    # centerlinjer + värsta 2 m-fönster (för rakhetsvyn i panelen).
    st = _straightness(zf, p, length_mm, width_mm, sim_mmpx)

    layout = {"nLasers": rig.n_lasers, "nCams": rig.n_profile_cams,
              "nSurfaceCams": rig.n_surface_cams,
              "laserOverlapFrac": round(rig.overlap_mm / rig.seg_len_mm, 3),
              "surfaceOverlapFrac": 0.06,
              "segLenMm": round(rig.seg_len_mm), "overlapMm": rig.overlap_mm,
              "heightResMm": round(rig.height_resolution_mm, 2),
              "coverage": round(res["coverage"], 3), "warp": warp_summary(p),
              "bowMm2m": st["bowMm2m"], "springMm2m": st["springMm2m"],
              "twistMm2m": st["twistMm2m"], "straightness": st}
    # exakta sensorspecar + segmentutbredning (för "klicka upp varje sensor"-vyn)
    layout["segments"] = [[round(s), round(e)] for (s, e, _c) in rig.segments()]
    layout["sensors"] = {
        "surface": {
            "model": rig.surface_cam.name, "n": rig.n_surface_cams,
            "pxAcross": rig.surface_cam.px_across, "pixelUm": rig.surface_cam.pixel_um,
            "mmPerPx": round(rig.surface_mm_per_px, 3),
            "fovMm": round(rig.surface_fov_per_cam_mm),
            "wdMm": round(rig.surface_wd_mm), "lensMm": round(rig.surface_lens_mm),
            "lineRateKHz": round(rig.surface_color_line_rate_hz / 1e3, 1),
        },
        "profile": {
            "model": rig.profile_cam.name, "n": rig.n_lasers,
            "pxLat": rig.profile_cam.width_px, "pixelUm": rig.profile_cam.pixel_um,
            "mmPerPx": round(rig.lateral_res_mm, 3),
            "segLenMm": round(rig.seg_len_mm), "overlapMm": rig.overlap_mm,
            "heightResMm": round(rig.height_resolution_mm, 2),
            "wdMm": round(rig.profile_wd_mm), "triAngle": rig.tri_angle_deg,
            "frameFps": rig.profile_cam.frame_rate_full_hz,
            "profileRateHz": rig.profile_rate_hz, "laser": rig.laser.name,
        },
        "boardLenMm": round(length_mm), "boardWidthMm": round(width_mm),
    }
    return z_img, layout


def _worst_window(arr: np.ndarray, win: int):
    """Värsta sagitta (avvikelse från kordan) över ett glidande fönster.
    Returnerar (sagitta, startfrac, slutfrac)."""
    best, bi = 0.0, 0
    step = max(1, win // 4)
    for i in range(0, max(1, len(arr) - win), step):
        seg = arr[i:i + win]
        if len(seg) < 3:
            continue
        chord = np.linspace(seg[0], seg[-1], len(seg))
        s = float(np.max(np.abs(seg - chord)))
        if s > best:
            best, bi = s, i
    return best, bi / len(arr), min(1.0, (bi + win) / len(arr))


def _straightness(zf: np.ndarray, p, length_mm: float, width_mm: float,
                  mm_per_row: float, lat_res_mm: float = 0.45, n_out: int = 160):
    """Rakhetsmått + centerlinjer: kantkrok ur silhuettens kanter (lateral),
    planböj + skevhet ur laserhöjden, med värsta 2 m-fönster för var och en."""
    from src.geometry import lateral_offset
    H, W = zf.shape
    win = max(4, int(round(2000.0 / mm_per_row)))

    # kantkrok (lateral) ur silhuettens detekterade kanter
    c = lateral_offset(H, p).astype(np.float64)
    rng = np.random.default_rng(int(abs(p.spring_mm) * 1000) + 1)
    qL = np.round(((c - width_mm / 2) + rng.normal(0, lat_res_mm * 0.4, H)) / lat_res_mm) * lat_res_mm
    qR = np.round(((c + width_mm / 2) + rng.normal(0, lat_res_mm * 0.4, H)) / lat_res_mm) * lat_res_mm
    spring_c = (qL + qR) / 2.0
    # planböj (höjd, mittlinjen) + skevhet (kant-höjdskillnad)
    bow_c = zf[:, W // 2].astype(np.float64)
    edge = zf[:, min(3, W - 1)] - zf[:, max(0, W - 4)]

    s_sag, s_a, s_b = _worst_window(spring_c, win)
    b_sag, b_a, b_b = _worst_window(bow_c, win)
    t_sag, t_a, t_b = _worst_window(edge, win)

    def ds(a):
        idx = np.linspace(0, len(a) - 1, n_out).astype(int)
        v = a[idx] - float(a.mean())
        return [round(float(x), 2) for x in v]

    return {
        "bowMm2m": round(b_sag, 1), "springMm2m": round(s_sag, 1), "twistMm2m": round(t_sag, 1),
        "springCenterMm": ds(spring_c), "bowCenterMm": ds(bow_c),
        "win2mFrac": round(win / H, 3),
        "worstSpring": {"a": round(s_a, 3), "b": round(s_b, 3), "sag": round(s_sag, 1)},
        "worstBow": {"a": round(b_a, 3), "b": round(b_b, 3), "sag": round(b_sag, 1)},
    }


def _height_png_b64(z_img: np.ndarray) -> str:
    """Höjdavvikelse (mm) -> gråskala-PNG. Range ±12 mm så warp (böj/vrid) inte
    klipps; 0.5 = plant. (3D-vyn överdriver displacementet för synlighet.)"""
    g = np.clip(z_img / 24.0 + 0.5, 0.0, 1.0)
    rgb = np.repeat((g * 255).astype(np.uint8)[..., None], 3, axis=2)
    return _png_b64(rgb)


GUI_NAMES = {1: "Kvist", 2: "Spricka", 3: "Blånad", 4: "Vankant", 5: "Röta", 6: "Hål"}
NOMINAL_LENGTH_MM = 5400.0
LENGTH_TOL_MM = 10.0      # tolerans: |avvikelse| <= -> godkänd längd


def engine_payload(color_img, label_img, mm_per_px, source, miou, lengths, board_id):
    """Bygger frontendens datakontrakt. color_img/label_img i bildorientering."""
    counts, areas, feats, crack_mm = _features_img(label_img, mm_per_px)

    # Uppmätt längd ur laserprofilen (brädor diffar lite). Mätosäkerhet ~lateral
    # upplösning. label_img: axel 1 = längd.
    true_len = label_img.shape[1] * mm_per_px
    rng = np.random.default_rng(board_id)
    measured_len = round(true_len + rng.normal(0, 0.3), 1)   # ±0,3 mm mätbrus

    # defektpositioner i mm (u = position längs längden 0..1) -> "var ligger felet"
    defects = []
    for f in feats:
        f["posMm"] = round(f["u"] * measured_len)
        defects.append({"cls": f["cls"], "name": GUI_NAMES.get(f["cls"], "?"),
                        "posMm": f["posMm"], "areaMm2": round(f["area"])})
    defects.sort(key=lambda d: -d["areaMm2"])

    color_s = _downscale_len(np.ascontiguousarray(color_img))
    label_s = _downscale_len(np.ascontiguousarray(label_img.astype(np.uint8)))
    z_img, layout = measured_height(label_img, mm_per_px, board_id)
    width_mm = label_img.shape[0] * mm_per_px

    # Deformationer (mm/2 m) ur laserprofilen – board-nivå, gäller alla bitar.
    deform = {"bow_mm_2m": layout["bowMm2m"], "spring_mm_2m": layout["springMm2m"],
              "twist_mm": layout["twistMm2m"]}

    # Kapoptimering med HÅLLFASTHETSSORTERING per bit (C-klass driver värdet).
    plan = _cutplan.plan_by_strength(feats, lengths, deform, width_mm)

    # Hela brädans C-klass (för översikt). Blånad ingår ej.
    knot_areas = [f["area"] for f in feats if f["cls"] == 1]
    knot_ratio = (2 * math.sqrt(max(knot_areas) / math.pi) / width_mm) if knot_areas else 0.0
    crack_areas = [f["area"] for f in feats if f["cls"] == 2]
    crack_len_m = (max(crack_areas) / 5.0 / 1000.0) if crack_areas else 0.0
    wane_area = sum(f["area"] for f in feats if f["cls"] == 4)
    wane_frac = (wane_area / measured_len) / width_mm if measured_len else 0.0
    grade = grade_board(GradeInput(
        knot_w_ratio=knot_ratio, width_mm=width_mm, wane_frac=wane_frac,
        crack_len_m=crack_len_m, rot_present=any(f["cls"] == 5 for f in feats),
        rot_in_knot_only=False, **deform,
    ))

    return {
        "id": board_id, "source": source, "mmPerPx": mm_per_px,
        "lengthMm": measured_len, "nominalLengthMm": NOMINAL_LENGTH_MM,
        "lengthDevMm": round(measured_len - NOMINAL_LENGTH_MM, 1),
        "lengthTolMm": LENGTH_TOL_MM,
        "lengthOk": bool(abs(measured_len - NOMINAL_LENGTH_MM) <= LENGTH_TOL_MM),
        "strength": {"cclass": grade["cclass"], "limiting": grade["limiting"]},
        "straightness": layout.get("straightness"),
        "defects": defects[:6],
        "color_png": _png_b64(color_s),
        "label_png": _labelid_png_b64(label_s),
        "height_png": _height_png_b64(_downscale_len(z_img)),
        "laser": layout,
        "stats": {
            "counts": counts, "areas": [round(a, 1) for a in areas],
            "features": feats, "crackLenMm": round(crack_mm),
            "defectArea": round(sum(areas), 1), "miou": miou,
        },
        "cutplan": plan,
    }


def _labelid_png_b64(label_id: np.ndarray) -> str:
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(label_id, "L").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class BoardSource:
    """Levererar brädor till GUI:t. Använder rastrerad Kodytek + tränad modell om
    de finns, annars syntetisk make_board (så GUI:t fungerar direkt)."""

    def __init__(self, seg_cfg: SegConfig | None = None):
        import os
        from dataclasses import replace
        cfg = seg_cfg or SegConfig()
        # miljöstyrning från startskriptet
        cfg = replace(cfg,
                      data_root=os.environ.get("WOODY_KODYTEK_ROOT", cfg.data_root),
                      ckpt_name=os.environ.get("WOODY_CKPT", cfg.ckpt_name))
        self.cfg = cfg
        self.model = None
        self.mcfg = None
        ckpt = find_checkpoint(self.cfg)
        if ckpt is not None:
            from src.infer import load_model        # lazy: torch krävs bara med modell
            self.model, self.mcfg = load_model(str(ckpt))
        self.kodytek = sorted(glob.glob(str(self.cfg.data_root) + "/images/*")) \
            if self.cfg.data_root else []

    def next(self, seed: int, lengths) -> dict:
        if self.kodytek:
            return self._kodytek(seed, lengths)
        return self._synthetic(seed, lengths)

    def _synthetic(self, seed, lengths):
        # brädor diffar lite i längd (kapas över/under nominellt) -> lasern mäter
        length_m = 5.4 + np.random.default_rng(seed * 7 + 1).uniform(-0.06, 0.03)
        b = make_board_for(seed, length_m=length_m, mm_per_px=1.0)  # grövre = snabbare
        if self.model is not None:
            from src.infer import predict_board
            pred = predict_board(self.model, b, self.mcfg)
        else:
            pred = b["label"]
        color_img = _img_orient(b["color"])
        label_img = _img_orient(pred)
        src = "unet+syntetisk" if self.model is not None else "facit+syntetisk"
        return engine_payload(color_img, label_img, b["mm_per_px"], src, 0.987,
                              lengths, seed)

    @staticmethod
    def _orient_section(a):
        """Orienterar en sektion så att BREDDEN (längsta pixelaxeln, ~2800 px)
        ligger på axel 1 – tål blandade orienteringar i datan."""
        if a.ndim == 3:
            return np.ascontiguousarray(np.transpose(a, (1, 0, 2))) if a.shape[0] > a.shape[1] else a
        return np.ascontiguousarray(a.T) if a.shape[0] > a.shape[1] else a

    def _stitch_board(self, seed):
        """Bygger en hel brädyta av STITCH_N konsekutiva sektioner (cachas i en
        pool). Returnerar (color, mask, mm) i bildorientering (axel 1 = längd)."""
        from PIL import Image
        if not hasattr(self, "_board_cache"):
            self._board_cache = {}
        n = len(self.kodytek)
        if n == 0:
            return None
        g = seed % STITCH_POOL
        if g in self._board_cache:
            return self._board_cache[g]
        N = min(STITCH_N, n)
        start = (g * N) % max(1, n - N + 1)
        paths = self.kodytek[start:start + N]
        cw = max(8, round(SEC_WIDTH_MM / STITCH_MM))      # bredd-px
        rl = max(8, round(SEC_LEN_MM / STITCH_MM))        # längd-px per sektion
        masks_dir = Path(self.cfg.data_root) / "masks"
        cols, msks = [], []
        for p in paths:
            a = self._orient_section(np.asarray(Image.open(p).convert("RGB")))
            cols.append(np.asarray(Image.fromarray(a).resize((cw, rl), Image.BILINEAR)))
            mp = masks_dir / (Path(p).stem + ".png")
            if mp.exists():
                m = self._orient_section(np.asarray(Image.open(mp)))
                if m.ndim == 3:
                    m = m[..., 0]
                m = np.asarray(Image.fromarray(m.astype(np.uint8)).resize((cw, rl), Image.NEAREST))
            else:
                m = np.zeros((rl, cw), np.uint8)
            msks.append(m)
        color = np.ascontiguousarray(np.transpose(np.concatenate(cols, axis=0), (1, 0, 2)))
        mask = np.ascontiguousarray(np.concatenate(msks, axis=0).T)
        res = (color, mask, STITCH_MM)                    # axel0=bredd, axel1=längd
        self._board_cache[g] = res
        return res

    def _kodytek(self, seed, lengths):
        st = self._stitch_board(seed)
        if st is None:
            return self._synthetic(seed, lengths)         # data ej klar än -> syntetisk
        color, mask, mm = st
        if self.model is not None:
            from src.infer import predict_board
            board = {"color": color, "height": np.zeros(color.shape[:2], np.float32),
                     "fiber_angle": np.zeros(color.shape[:2], np.float32), "mm_per_px": mm}
            label_img = predict_board(self.model, board, self.mcfg)
            src = "unet+kodytek"
        else:
            label_img, src = mask, "facit+kodytek"
        return engine_payload(color, label_img, mm, src, 0.0, lengths, seed)

    # ---------- sann-upplösnings-utsnitt (för "klicka upp sensor"-zoomvyn) ----------
    def oriented_full(self, seed: int):
        """Återskapar brädan (samma seed) och ger full-upplösnings färg i
        bildorientering (axel 1 = längd) + mm/px. Liten cache."""
        if not hasattr(self, "_full_cache"):
            self._full_cache = {}
        if seed in self._full_cache:
            return self._full_cache[seed]
        if self.kodytek:
            st = self._stitch_board(seed)                 # samma hopsydda bräda som visas
            res = (st[0], st[2]) if st is not None else (np.zeros((4, 4, 3), np.uint8), STITCH_MM)
        else:
            length_m = 5.4 + np.random.default_rng(seed * 7 + 1).uniform(-0.06, 0.03)
            b = make_board_for(seed, length_m=length_m, mm_per_px=1.0)
            res = (_img_orient(b["color"]), b["mm_per_px"])
        self._full_cache[seed] = res
        if len(self._full_cache) > 6:
            self._full_cache.pop(next(iter(self._full_cache)))
        return res

    def crop_window(self, seed: int, u0: float, u1: float, v0: float, v1: float,
                    max_px: int = 2000) -> dict:
        """Klipper ut normaliserat fönster [u0,u1]×[v0,v1] (längd×bredd) ur den
        full-upplösta brädan och returnerar PNG + verklig mm/px (kapad till max_px)."""
        color, mm = self.oriented_full(seed)
        H, W = color.shape[:2]                       # H=bredd-rader, W=längd-kol
        c0, c1 = sorted((int(np.clip(u0, 0, 1) * W), int(np.clip(u1, 0, 1) * W)))
        r0, r1 = sorted((int(np.clip(v0, 0, 1) * H), int(np.clip(v1, 0, 1) * H)))
        c1, r1 = max(c1, c0 + 1), max(r1, r0 + 1)
        sub = np.ascontiguousarray(color[r0:r1, c0:c1])
        sh, sw = sub.shape[:2]
        scale = min(1.0, max_px / max(sh, sw))
        if scale < 1.0:
            from PIL import Image
            sub = np.asarray(Image.fromarray(sub).resize(
                (max(1, int(sw * scale)), max(1, int(sh * scale))), Image.LANCZOS))
        return {"png": _png_b64(sub), "wPx": int(sub.shape[1]), "hPx": int(sub.shape[0]),
                "mmPerPx": round(mm / max(scale, 1e-9), 4),
                "spanLenMm": round((c1 - c0) * mm), "spanWidthMm": round((r1 - r0) * mm)}
