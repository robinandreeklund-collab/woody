"""Prototyp-simulering — ETT dubbel-oblikt mäthuvud, bräda 1 m.

CROSS-FEED: laserlinjen löper LÄNGS brädans 1 m längd; brädan matas i SIDLED så
att de ~150 mm bredden passerar förbi huvudet. Vid varje matningsläge mäts en
höjdprofil längs hela 1 m-linjen; över matningen byggs hela höjdkartan upp.

Modulen modellerar HELA sensoruppsättningen och vad varje sensor ser – enligt
produktspecarna i src.hardware:

  • 2× profilkamera (mono + bandpass 650/520 nm) ser laserstripen förskjuten av
    höjden (triangulering) med ocklusion/skugga, fokusbredd och sensorbrus.
  • 1× ytkamera FÄRG (linjekamera) bygger upp brädans yttextur över matningen.
  • 1× ytkanal NIR (strobad) – lyfter fram blånad/röta.
  • 3× punktlaser (V/C/H) – absolut tjocklek (fusion-ankare).

Brädorna kan dessutom ha GLOBAL skevhet i mm – vridning (twist), kupa (cup) och
bukt (bow) – ovanpå de lokala defekterna (sprickor, kvist, vankant, röta, hål).

Bandhastighet + profiltakt styr profil-pitchen i matningsled → datamängd och
effektiv upplösning ändras med farten (visas live).
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src.board import make_board
from src.hardware import Rig
from src.laser import simulate_array
from src.config import CLASSES, CLASS_COLORS

INK, MUTED, PAPER = "#23262b", "#6a6e74", "#f7f6f1"
RED, GRN, BLUE, GOLD, PURP = "#e8542c", "#2f9e6e", "#2f6fb0", "#b9a96f", "#a23ad6"
BOARD_LEN = 1000.0                   # prototypbrädor är alltid 1 m
PL_FRACS = (0.1, 0.5, 0.9)           # 3 punktlaser: V / C / H längs 1 m-linjen
ROI_ROWS = 256                       # profilkamerans ROI-band (höjd) för triangulering


# --------------------------------------------------------------- global skevhet
def _apply_warp(height, bow_mm, cup_mm, twist_mm):
    """Lägger global skevhet (mm) ovanpå höjdfältet:
      bow   – bukt längs längden (båge),
      cup   – kupa tvärs bredden (kanter upp),
      twist – vridning (helikoid: motsatta hörn upp/ned).
    Speglar verkliga virkesdeformationer; små mm-avvikelser."""
    H, W = height.shape
    u = np.linspace(-1.0, 1.0, H)[:, None]
    v = np.linspace(-1.0, 1.0, W)[None, :]
    dz = (bow_mm * (u ** 2 - 1 / 3.0)
          + cup_mm * (v ** 2 - 1 / 3.0)
          + twist_mm * u * v)
    return height + dz


# ----------------------------------------------------------------- simulering
def simulate(length_mm=BOARD_LEN, width_mm=150.0, thickness_mm=45.0,
             mm_per_px=0.6, seed=3, subtle=False,
             boards_per_min=60.0, profile_rate_hz=490.0,
             bow_mm=0.0, cup_mm=0.0, twist_mm=0.0, passes=1):
    """Bräda (defekter + global skevhet) + dubbel-oblikt huvud + driftparametrar.

    Takten (brädor/min) styr bandhastigheten: vid cross-feed passerar brädans
    bredd förbi linjen på 60/takt sekunder → feed = bredd · takt / 60.
    passes>1: Jetson kör brädan fram/back N gånger → medelvärdar (brus ↓ ~√N) och
    mäter pass-till-pass-repeterbarhet (för kvalitet/kalibrering)."""
    L = float(min(length_mm, BOARD_LEN))
    b = make_board(length_mm=L, width_mm=width_mm, thickness_mm=thickness_mm,
                   mm_per_px=mm_per_px, seed=int(seed), subtle_defects=subtle)
    if bow_mm or cup_mm or twist_mm:
        b["height"] = np.clip(_apply_warp(b["height"], bow_mm, cup_mm, twist_mm), 0, None)
    feed_mps = width_mm / 1000.0 * boards_per_min / 60.0
    rig = Rig(board_length_mm=L, board_width_mm=width_mm, board_thickness_mm=thickness_mm,
              feed_mps=feed_mps, profile_rate_hz=profile_rate_hz)
    npass = max(1, int(passes))
    res = simulate_array(b["height"], mm_per_px, rig, seed=1)
    if npass > 1:                                  # multi-pass fram/back → medel + repeterbarhet
        Z = np.stack([res["z_fused"]] +
                     [simulate_array(b["height"], mm_per_px, rig, seed=1 + i)["z_fused"]
                      for i in range(1, npass)])
        res["z_fused"] = Z.mean(0)
        res["pass_std_mm"] = float(np.nanmean(np.std(Z, 0)))
    else:
        res["pass_std_mm"] = float("nan")
    res["passes"] = npass

    pitch_mm = feed_mps * 1000.0 / max(1.0, profile_rate_hz)
    Ww = b["height"].shape[1]
    n_profiles = int(np.clip(round(width_mm / max(1e-6, pitch_mm)), 2, Ww))
    return {"board": b, "rig": rig, "meas": res, "mm_per_px": mm_per_px,
            "L": L, "width": width_mm, "thickness": thickness_mm,
            "takt": boards_per_min, "feed_mps": feed_mps, "profile_rate_hz": profile_rate_hz,
            "pitch_mm": pitch_mm, "n_profiles": n_profiles, "passes": npass,
            "warp": {"bow_mm": bow_mm, "cup_mm": cup_mm, "twist_mm": twist_mm}}


def _ax(ax, title):
    ax.set_facecolor("#fff")
    for s in ax.spines.values():
        s.set_color(MUTED); s.set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_title(title, color=INK, fontsize=10.5, fontweight="bold", loc="left", pad=7)


def _fig(figsize):
    fig = plt.figure(figsize=figsize, dpi=120); fig.patch.set_facecolor("#ffffff")
    return fig


# ----------------------------------------------------- bänkvy (ovanifrån, cross-feed)
def fig_bench(sim, feed_frac, figsize=(7.4, 3.0)):
    L, Wd = sim["L"], sim["width"]
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, "BÄNK — bräda matas i SIDLED förbi 1 m-laserlinjen (ovanifrån)")
    sy = feed_frac * Wd
    ax.add_patch(plt.Rectangle((0, 0), L, Wd, fc="#efe9d8", ec=GOLD, lw=1.4))
    ax.add_patch(plt.Rectangle((0, 0), L, sy, fc=BLUE, ec="none", alpha=0.10))
    ax.plot([0, L], [sy, sy], color=INK, lw=2.0)
    ax.text(L + 8, sy, "laserlinje 1 m\n(röd+grön oblik)", color=INK, fontsize=7.5, va="center")
    for f in PL_FRACS:
        ax.plot(f * L, sy, marker="v", ms=10, color=PURP, mec="k", mew=0.5, zorder=5)
    ax.plot([], [], marker="v", color=PURP, ls="none", label="3 punktlaser (V/C/H)")
    ax.annotate("", xy=(L * 0.5, sy + 46), xytext=(L * 0.5, sy + 8),
                arrowprops=dict(arrowstyle="-|>", color="#b06", lw=2))
    ax.text(L * 0.5 + 10, sy + 28, "matning (bredd)", color="#b06", fontsize=8)
    ax.set_xlim(-20, L + 150); ax.set_ylim(-20, Wd + 20)
    ax.set_xlabel("längd (mm) — laserlinjens riktning"); ax.set_ylabel("bredd (mm) — matning")
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    fig.tight_layout(); return fig


# ----------------------------------------------- rå profilkamera (laserstripe, per spec)
def _stripe_image(sim, feed_frac, which):
    """Vad EN mono-profilkamera (med bandpass) faktiskt ser: laserstripen förskjuten
    av höjden (triangulering) med ocklusion, fokusbredd och sensorbrus.
    'which' = 'red' (vänster oblik, 650 nm) / 'green' (höger oblik, 520 nm)."""
    btrue = sim["board"]["height"]; rig = sim["rig"]
    Hlen, Ww = btrue.shape
    L, T = sim["L"], sim["thickness"]
    col = int(np.clip(feed_frac * (Ww - 1), 0, Ww - 1))
    W_img, H_img = 720, 420
    idx = np.linspace(0, Hlen - 1, W_img).astype(int)
    h = btrue[idx, col].astype(float)

    hmax = T * 1.18
    base, usable = H_img * 0.10, H_img * 0.80
    center = base + np.clip(h, 0, hmax) / hmax * usable

    dx = L / W_img
    g = np.gradient(h, dx)
    tan_lim = np.tan(np.radians(rig.tri_angle_deg))
    valid = np.abs(g) <= tan_lim
    sign = +1.0 if which == "red" else -1.0
    drop = g * sign < -0.6 * tan_lim
    shadow = max(2, int(round(3.0 / dx)))
    for s in range(1, shadow):
        if which == "red":
            valid[s:] &= ~drop[:-s]
        else:
            valid[:-s] &= ~drop[s:]

    rng = np.random.default_rng(col * 7 + (1 if which == "red" else 2))
    rows = np.arange(H_img)[:, None]
    sig = max(2.2, (rig.laser.line_width_mm / hmax * usable) + 2.0)
    inten = np.exp(-((rows - center[None, :]) ** 2) / (2 * sig ** 2)) * valid[None, :]
    inten = inten * (0.85 + 0.15 * rng.random((H_img, W_img)))
    inten += 0.018 * rng.random((H_img, W_img))
    inten = np.clip(inten, 0, 1)
    img = np.zeros((H_img, W_img, 3))
    ch = 0 if which == "red" else 1
    img[..., ch] = inten
    img[..., 1 if which == "red" else 0] += inten * (0.10 if which == "red" else 0.05)
    return np.clip(img, 0, 1), valid, hmax


def fig_profile_cams(sim, feed_frac, figsize=(7.4, 4.2)):
    L = sim["L"]
    fig = _fig(figsize)
    for i, (which, nm) in enumerate([("red", "650"), ("green", "520")]):
        ax = fig.add_subplot(2, 1, i + 1)
        img, valid, hmax = _stripe_image(sim, feed_frac, which)
        _ax(ax, f"PROFILKAMERA {'RÖD' if which=='red' else 'GRÖN'} {nm} nm — mono + bandpass (rå laserstripe)")
        ax.imshow(img, origin="lower", extent=[0, L, 0, hmax], aspect="auto", interpolation="nearest")
        ax.text(0.99, 0.05, f"täckning {100*valid.mean():.0f}%", transform=ax.transAxes,
                ha="right", color="#fff", fontsize=7.5, bbox=dict(fc="#0007", ec="none", pad=2))
        ax.set_ylabel("höjd (mm)")
        ax.set_xlabel("längd (mm) — 2448 px-axel") if i == 1 else ax.set_xticklabels([])
    fig.tight_layout(); return fig


# ------------------------------------------------- ytkameror (färg + NIR, linjekamera)
def fig_surface_cams(sim, feed_frac, figsize=(7.4, 4.2)):
    L, Wd = sim["L"], sim["width"]
    col = sim["board"]["color"]; nir = sim["board"]["nir"]
    Hlen, Ww = col.shape[:2]
    cut = int(np.clip(feed_frac * Ww, 1, Ww))
    fig = _fig(figsize)

    ax1 = fig.add_subplot(2, 1, 1)
    _ax(ax1, "YTKAMERA FÄRG — RGB-linjekamera (yttextur byggs i matningsled)")
    rgb = np.zeros((Hlen, Ww, 3), np.uint8); rgb[:, :cut] = col[:, :cut]
    ax1.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower", extent=[0, L, 0, Wd], aspect="auto")
    ax1.axhline(feed_frac * Wd, color="#fff", lw=1.0, alpha=0.7)
    ax1.set_ylabel("bredd (mm)"); ax1.set_xticklabels([])

    ax2 = fig.add_subplot(2, 1, 2)
    _ax(ax2, "YTKANAL NIR — strobad (blånad/röta framträder mörkt)")
    nn = np.full((Hlen, Ww), np.nan); nn[:, :cut] = nir[:, :cut]
    ax2.imshow(nn.T, origin="lower", extent=[0, L, 0, Wd], aspect="auto", cmap="inferno",
               vmin=float(np.nanmin(nir)), vmax=float(np.nanmax(nir)))
    ax2.axhline(feed_frac * Wd, color="#fff", lw=1.0, alpha=0.7)
    ax2.set_ylabel("bredd (mm)"); ax2.set_xlabel("längd (mm)")
    fig.tight_layout(); return fig


# ------------------------------------------------- live längsprofil + punktlaser
def fig_length_profile(sim, feed_frac, figsize=(7.4, 3.2)):
    z = sim["meas"]["z_fused"]; btrue = sim["board"]["height"]
    L, T = sim["L"], sim["thickness"]; Hpx, Wpx = z.shape
    col = int(np.clip(feed_frac * (Wpx - 1), 0, Wpx - 1))
    xs = np.linspace(0, L, Hpx); prof = z[:, col]
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, "LÄNGSPROFIL (1 m) — linjelaser + punktlaser-ankare")
    ax.fill_between(xs, 0, prof, color=RED, alpha=0.10)
    ax.plot(xs, prof, color=RED, lw=1.4, label="linjelaser (profil)")
    ax.axhline(T, color=MUTED, ls="--", lw=0.8)
    ax.text(L, T + 0.4, f"nominell {T:.0f} mm", color=MUTED, fontsize=7.5, ha="right")
    for f in PL_FRACS:
        li = int(f * (Hpx - 1)); xmm = f * L
        val = float(btrue[li, col] + np.random.default_rng(col + int(f * 100)).normal(0, 0.04))
        ax.plot(xmm, val, marker="v", ms=11, color=PURP, mec="k", mew=0.6, zorder=6)
        ax.annotate(f"{val:.1f}", (xmm, val), textcoords="offset points",
                    xytext=(0, 9), fontsize=7.5, color=PURP, ha="center", fontweight="bold")
    ax.plot([], [], marker="v", color=PURP, ls="none", label="punktlaser V/C/H (absolut, 3× längs 1 m)")
    ax.set_xlim(0, L); ax.set_ylim(0, T * 1.5)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("höjd (mm)")
    ax.legend(loc="lower center", fontsize=7.5, ncol=2, frameon=False)
    fig.tight_layout(); return fig


# ------------------------------------------------- tvärsnittsprofil (över bredden)
def fig_cross_section(sim, length_frac, figsize=(7.4, 3.2)):
    """Tvärsnitt (tvärs 150 mm bredd) vid en längdposition: topp-profil + två sidoväggar
    från de OBLIKA LINJELASRARNA (röd ser vänster sida, grön höger). Kupa/vridning syns.
    (Punktlasrarna mäter inte här – de ligger längs 1 m och ankrar LÄNGSprofilen.)"""
    z = sim["meas"]["z_fused"]; Hpx, Wpx = z.shape
    Wd, T = sim["width"], sim["thickness"]
    li = int(np.clip(length_frac * (Hpx - 1), 0, Hpx - 1))
    ys = np.linspace(0, Wd, Wpx); top = z[li, :]
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, f"TVÄRSNITT (tvärs 150 mm) vid längd {length_frac*sim['L']:.0f} mm — linjelasrar")
    ax.fill_between(ys, 0, top, color="#e2e8da", ec="none")
    ax.plot(ys, top, color=INK, lw=1.6, label="uppmätt topp-profil")
    ax.plot([ys[0], ys[0]], [0, top[0]], color=RED, lw=3, solid_capstyle="round",
            label="vänster sida (röd 650)")
    ax.plot([ys[-1], ys[-1]], [0, top[-1]], color=GRN, lw=3, solid_capstyle="round",
            label="höger sida (grön 520)")
    ax.axhline(T, color=MUTED, ls="--", lw=0.8)
    ax.text(Wd, T + 0.4, f"nominell {T:.0f} mm", color=MUTED, fontsize=7.5, ha="right")
    ax.set_xlim(-4, Wd + 4); ax.set_ylim(0, T * 1.4)
    ax.set_xlabel("bredd (mm) — matningsled"); ax.set_ylabel("höjd (mm)")
    ax.legend(loc="lower center", fontsize=7, ncol=3, frameon=False)
    fig.tight_layout(); return fig


# --------------------------------------------------- höjdkarta (upplösning ∝ fart)
def _resample_width(z, n):
    Hlen, Ww = z.shape
    if n >= Ww:
        return z
    blk = (np.arange(Ww) * n // Ww)
    out = np.empty_like(z)
    for k in range(n):
        m = blk == k
        if m.any():
            out[:, m] = z[:, m].mean(axis=1, keepdims=True)
    return out


def fig_heightmap(sim, feed_frac, figsize=(7.4, 3.2)):
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]
    L, Wd = sim["L"], sim["width"]; Hpx, Wpx = z.shape
    cut = int(np.clip(feed_frac * Wpx, 1, Wpx))
    zr = _resample_width(z, sim["n_profiles"])
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, f"HÖJDKARTA (matningsled) — pitch {sim['pitch_mm']:.2f} mm/profil + defekter")
    img = np.full_like(zr, np.nan); img[:, :cut] = zr[:, :cut]
    ax.imshow(img.T, aspect="auto", origin="lower", cmap="viridis",
              extent=[0, L, 0, Wd], vmin=np.nanmin(z), vmax=np.nanmax(z), interpolation="nearest")
    ov = np.zeros((*lbl.shape, 4))
    for cid, c in CLASS_COLORS.items():
        if cid:
            ov[lbl == cid] = (*c, 0.85)
    ov[:, cut:] = 0
    ax.imshow(np.transpose(ov, (1, 0, 2)), aspect="auto", origin="lower", extent=[0, L, 0, Wd])
    ax.axhline(feed_frac * Wd, color=INK, lw=1.2)
    for f in PL_FRACS:
        ax.plot(f * L, feed_frac * Wd, marker="v", ms=7, color=PURP, mec="k", mew=0.4)
    ax.set_xlabel("längd (mm)"); ax.set_ylabel("bredd (mm) — matning")
    fig.tight_layout(); return fig


# -------------------------------------------------------------------- enkel 3D
def fig_surface3d(sim, feed_frac=1.0, figsize=(7.4, 3.4), stride=16):
    z = sim["meas"]["z_fused"]; L, Wd = sim["L"], sim["width"]; Hpx, Wpx = z.shape
    cut = int(np.clip(feed_frac * Wpx, 2, Wpx))
    zc = z[::stride, :cut:max(1, cut // 54 or 1)]
    xx = np.linspace(0, L, zc.shape[0]); yy = np.linspace(0, feed_frac * Wd, zc.shape[1])
    X, Y = np.meshgrid(xx, yy, indexing="ij")
    fig = _fig(figsize)
    ax = fig.add_subplot(111, projection="3d"); ax.set_facecolor(PAPER)
    ax.plot_surface(X, Y, zc, cmap="viridis", linewidth=0, antialiased=True,
                    rcount=zc.shape[0], ccount=zc.shape[1])
    ax.set_title("3D — uppmätt brädyta (skevhet + defekter)", color=INK, fontsize=10.5,
                 fontweight="bold", loc="left")
    ax.set_xlabel("längd (mm)", fontsize=8); ax.set_ylabel("bredd (mm)", fontsize=8)
    ax.set_zlabel("höjd (mm)", fontsize=8); ax.tick_params(colors=MUTED, labelsize=7)
    ax.view_init(elev=42, azim=-62)
    try: ax.set_box_aspect((3, 0.6, 0.4))
    except Exception: pass
    fig.tight_layout(); return fig


# ---------------------------------------------------- datatakt / fart-tradeoff
def datarate(sim):
    rig = sim["rig"]; rate = sim["profile_rate_hz"]
    px_len = rig.profile_cam.width_px
    pts_per_s = rate * px_len * 2
    mbps = rate * px_len * ROI_ROWS * 2 / 1e6
    return {"pitch_mm": sim["pitch_mm"], "n_profiles": sim["n_profiles"],
            "profiles_per_s": rate, "points_per_s": pts_per_s,
            "mb_per_s": mbps, "boards_per_min": sim["takt"], "feed_mps": sim["feed_mps"]}


def fig_throughput(sim, figsize=(7.4, 3.2)):
    rate = sim["profile_rate_hz"]; Wd = sim["width"]
    takt = np.linspace(10.0, 180.0, 90)
    feed = Wd / 1000.0 * takt / 60.0
    pitch = feed * 1000.0 / rate
    d = datarate(sim)
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, "TAKT — upplösning i matningsled ↓ vs bandhastighet ↑ (vald takt markerad)")
    ax.plot(takt, pitch, color=BLUE, lw=1.8)
    ax.axvline(sim["takt"], color=MUTED, ls="--", lw=0.8)
    ax.plot(sim["takt"], d["pitch_mm"], "o", color=BLUE, ms=8, zorder=6)
    ax.annotate(f"{d['pitch_mm']:.2f} mm/profil", (sim["takt"], d["pitch_mm"]),
                textcoords="offset points", xytext=(8, 6), color=BLUE, fontsize=8, fontweight="bold")
    ax.set_xlabel("takt (brädor/min)"); ax.set_ylabel("pitch (mm/profil)", color=BLUE)
    ax.tick_params(axis="y", colors=BLUE)
    ax2 = ax.twinx(); ax2.plot(takt, feed, color=GRN, lw=1.8)
    ax2.plot(sim["takt"], d["feed_mps"], "s", color=GRN, ms=8, zorder=6)
    ax2.set_ylabel("bandhastighet (m/s)", color=GRN); ax2.tick_params(axis="y", colors=GRN)
    for s in ax2.spines.values(): s.set_color(MUTED)
    fig.tight_layout(); return fig


# ============================================================ BOM & systemintegration
# Priser SEK exkl. moms/frakt (Jetson, CS050, MindVision verifierade; övriga ca).
# Fas: 1 = vänster modul (röd) – minimal "funkar-det?"-test, handmatning på alu-ram;
#      2 = höger modul (grön) + 2 transportband + encoder/mäthjul – repeterbar dubbel-oblik;
#      3 = full sensorsvit (ytkamera/NIR + punktlaser).
BOM = [
    # --- FAS 1: komplett röd-profilerare på rullband + Jetson-styrning ---
    ("Edge-compute", "NVIDIA Jetson Orin Nano Super Dev Kit", 1, "U-Net + styrning (4×USB3, GbE, 40-pin)", "—", "—", 3695, 1),
    ("Profilkamera RÖD", "Hikrobot MV-CS050-10UM (mono)", 1, "3D-triangulering (röd-huvud)", "USB3", "~490 prof/s (ROI)", 3382, 1),
    ("Objektiv C-mount", "HIKROBOT MVL-MF0828M-8MP (8 mm, 8MP, 2/3″)", 1, "profiloptik (500 mm FOV @ WD 474 mm)", "—", "—", 500, 1),
    ("Bandpassfilter 650", "650 nm", 1, "isolerar röd laser", "—", "—", 350, 1),
    ("Linjelaser röd", "iadiy LM9R650H100L60", 1, "linjelaser 650 nm 100 mW (oblik 30°)", "5 V + GPIO-en", "CW", 300, 1),
    ("Ramstativ (alu)", "vänt stativ + tvärbalk (T-spår)", 1, "håller röd-huvudet över rullbandet", "—", "—", 900, 1),
    ("Rullband ×2", "rostfri 24 V, 50 mm/s, 600 mm (TUNGFUII-typ)", 2, "matning (cross-feed), Jetson-styrt fram/back", "24 V DC", "50 mm/s", 900, 1),
    ("Motordrivare", "DC H-brygga (fram/back + PWM)", 1, "Jetson styr riktning+fart → multi-pass", "GPIO×2 + PWM", "—", 250, 1),
    ("Encoder + mäthjul", "Inkrementell encoder + mäthjul mot brädan", 1, "position (immun mot slir) + kameratrigger", "GPIO A/B + trig→kam", "~0,1 mm/puls", 900, 1),
    ("Ingångslaser", "fotcell/genombrott (brädstart)", 1, "registrerar brädans läge vid ingång (rullband)", "GPIO", "kant-trig", 250, 1),
    ("Anslag / mathåll", "fast anslag i bakkant (laddläge)", 1, "lägg brädan mot → känd start, kvadrerar", "—", "—", 150, 1),
    ("Sidoanslag / styrskena", "fast anslag längs ENA sidan", 1, "brädans ena kant rider mot → datum + anti-skev", "—", "—", 200, 1),
    ("Diverse", "Kablar, 24 V/5 V-nätaggregat, fästen", 1, "—", "—", "—", 1500, 1),
    # --- FAS 2: grön-modul (dubbel-oblik) + punktlaser + line-scan-yta ---
    ("Profilkamera GRÖN", "Hikrobot MV-CS050-10UM (mono)", 1, "3D höger + occlusion-fyllning", "USB3", "~490 prof/s (ROI)", 3382, 2),
    ("Objektiv C-mount", "HIKROBOT MVL-MF0828M-8MP (8 mm, 8MP, 2/3″)", 1, "profiloptik (500 mm FOV @ WD 474 mm)", "—", "—", 500, 2),
    ("Bandpassfilter 520", "520 nm", 1, "isolerar grön laser", "—", "—", 350, 2),
    ("Linjelaser grön", "iadiy LM9G520H50L60T", 1, "linjelaser 520 nm 50 mW (oblik 30°)", "5 V + GPIO-en", "CW", 350, 2),
    ("Punktlaser ×3 (rek.)", "Panasonic HG-C1400 (mätavstånd 400 mm)", 3, "absolut tjocklek — ankrar längsprofilen", "analog→ADC", "1,5 kHz", 1900, 2),
    ("ADC", "MCP3008 (SPI, 200 kSPS, 8 kanaler)", 1, "läser 3 analoga punktlaser (Jetson saknar ADC)", "SPI", "—", 60, 2),
    ("Ytkamera (line-scan)", "MindVision MV-XGLC83BM-T4-90", 1, "yta färg+NIR (4-TDI)", "10GBase-T (NBASE-T→1GbE)", "1,2 kHz proto / 110 kHz max", 6902, 2),
    ("Objektiv M72 (ytkamera)", "Vision Datum VT-LEN72-5545MP150 (55 mm, M72, ≤66,7 mm)", 1, "8K-yta över 500 mm @ WD ~535 mm", "—", "—", 16000, 2),
    ("NIR-belysning", "850 nm linjeljus (strobad)", 1, "ytkanal NIR", "ytkamera-strobe", "= radtakt", 900, 2),
    ("Färgbelysning", "RGB linjeljus (strobad R/G/B)", 1, "färg via sekventiell strobe", "ytkamera 3 strobe-ut", "radtakt/3", 1500, 2),
    ("LED-driver", "konstantström / strobe-driver", 1, "driver för strobe-ljus", "ytkamera-strobe-ut", "—", 300, 2),
]


def bom_rows():
    return [{"Fas": f, "Komponent": k, "Modell": m, "Antal": q, "Roll": r, "Gränssnitt": i,
             "Uppdateringstakt": u, "Ca pris (st)": f"{p:,}".replace(",", " ")}
            for (k, m, q, r, i, u, p, f) in BOM]


def bom_total(max_fas=3):
    return sum(q * p for (_, _, q, _, _, _, p, f) in BOM if f <= max_fas)


def interface_rows(sim):
    """Alla gränssnitt + uppdaterings-/datatakter, prototyptakt vs buss-tak."""
    rig = sim["rig"]; rate = sim["profile_rate_hz"]; v = sim["feed_mps"]
    pcam_mbs = rig.profile_cam.width_px * ROI_ROWS * rate / 1e6
    s_mmpp = rig.surface_mm_per_px
    s_line = v * 1000.0 / s_mmpp
    s_mbs = rig.surface_cam.px_across * s_line / 1e6
    s_max_mbs = rig.surface_cam.px_across * rig.surface_cam.line_rate_hz / 1e6
    pl_rate = 1500.0
    return [
        {"Enhet": "Profilkamera RÖD", "Buss": "USB3 (5 Gbit/s)", "Takt (proto)": f"{rate:.0f} prof/s",
         "Datatakt": f"{pcam_mbs:.0f} MB/s", "Buss-tak": "~500 MB/s", "Marginal": f"{500/pcam_mbs:.1f}×"},
        {"Enhet": "Profilkamera GRÖN", "Buss": "USB3 (5 Gbit/s)", "Takt (proto)": f"{rate:.0f} prof/s",
         "Datatakt": f"{pcam_mbs:.0f} MB/s", "Buss-tak": "~500 MB/s", "Marginal": f"{500/pcam_mbs:.1f}×"},
        {"Enhet": "Ytkamera (line-scan)", "Buss": "10GBase-T→1/2.5/5G", "Takt (proto)": f"{s_line:.0f} rad/s",
         "Datatakt": f"{s_mbs:.0f} MB/s", "Buss-tak": "118 MB/s (1GbE)", "Marginal": f"{118/max(s_mbs,1e-3):.0f}× (direkt till Jetson)"},
        {"Enhet": "Ytkamera (MAX)", "Buss": "10GBase-T (10G)", "Takt (proto)": f"{rig.surface_cam.line_rate_hz/1e3:.0f} krad/s",
         "Datatakt": f"{s_max_mbs:.0f} MB/s", "Buss-tak": "1250 MB/s (10GigE)", "Marginal": f"{1250/s_max_mbs:.1f}× (kräver 10G-värd)"},
        {"Enhet": "3× Punktlaser → ADC", "Buss": "analog→SPI", "Takt (proto)": f"{pl_rate:.0f} Hz",
         "Datatakt": "<0,1 MB/s", "Buss-tak": "SPI 200 kSPS", "Marginal": "3 abs-ankare längs 1 m (V/C/H) → skala/drift"},
        {"Enhet": "RGB/NIR-strobe", "Buss": "ytkamera strobe-ut", "Takt (proto)": f"{s_line:.0f} Hz (sync)",
         "Datatakt": "—", "Buss-tak": "3 strobe-kanaler", "Marginal": "färg = radtakt/4 (R/G/B+NIR)"},
        {"Enhet": "Ingångslaser (brädstart)", "Buss": "GPIO", "Takt (proto)": "kant-trig",
         "Datatakt": "—", "Buss-tak": "—", "Marginal": "nollställer position på rullbandet"},
        {"Enhet": "Motordrivare (fram/back)", "Buss": "GPIO/PWM", "Takt (proto)": "—",
         "Datatakt": "—", "Buss-tak": "—", "Marginal": "Jetson: load→fram→mät→back→upprepa"},
        {"Enhet": "Encoder + mäthjul", "Buss": "RS422→ytkamera", "Takt (proto)": "pulser",
         "Datatakt": "—", "Buss-tak": "—", "Marginal": "låser radtakt + position (immun mot slir)"},
    ]


def _node(ax, x, y, w, h, title, sub, fc):
    ax.add_patch(mpatches.FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.006,rounding_size=0.02", fc=fc, ec=INK, lw=1.1))
    ax.text(x, y + 0.013, title, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
    ax.text(x, y - 0.026, sub, ha="center", va="center", fontsize=6.6, color="#444")


def fig_wiring(sim, figsize=(7.4, 4.3)):
    ir = {r["Enhet"]: r for r in interface_rows(sim)}
    fig = _fig(figsize); ax = fig.add_subplot(111); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    _ax(ax, "SYSTEMKOPPLING — allt till Jetson (buss · takt · datatakt)")
    _node(ax, 0.5, 0.5, 0.22, 0.17, "Jetson Orin Nano", "U-Net + fusion", "#dfe9f5")
    USB, NET, AD, GP = BLUE, PURP, GOLD, GRN
    nodes = [
        (0.16, 0.83, "Profilkamera RÖD", "CS050 · 650 nm", "#fde9e3", USB,
         f"USB3 · {ir['Profilkamera RÖD']['Datatakt']}"),
        (0.16, 0.50, "Profilkamera GRÖN", "CS050 · 520 nm", "#e3f3ea", USB,
         f"USB3 · {ir['Profilkamera GRÖN']['Datatakt']}"),
        (0.16, 0.17, "Ytkamera line-scan", "MindVision · NBASE-T", "#efe6f7", NET,
         f"10GBase-T→1GbE · {ir['Ytkamera (line-scan)']['Datatakt']}"),
        (0.84, 0.83, "3× Punktlaser → MCP3008", "HG-C1400 · 400 mm WD", "#fbf3df", AD,
         f"SPI · {ir['3× Punktlaser → ADC']['Takt (proto)']}"),
        (0.84, 0.50, "RGB/NIR-strobe", "drivs av ytkamerans 3 strobe-ut", "#e9f5ec", GP,
         f"3 strobe-kanaler · {ir['RGB/NIR-strobe']['Takt (proto)']}"),
        (0.84, 0.17, "Encoder (RS422)", "→ ytkamera (TDI) + profil-trig", "#e9f5ec", GP, "RS422 · låser radtakt"),
    ]
    for (x, y, t, s, fc, col, lbl) in nodes:
        _node(ax, x, y, 0.235, 0.135, t, s, fc)
        jx = 0.39 if x < 0.5 else 0.61
        ax.annotate("", xy=(jx, 0.5 + (y - 0.5) * 0.35), xytext=(x + (0.12 if x < 0.5 else -0.12), y),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.7))
        mx = (jx + x) / 2
        ax.text(mx, y + 0.05, lbl, ha="center", fontsize=6.2, color=col,
                bbox=dict(fc="#fff", ec="none", pad=0.4))
    ax.text(0.5, 0.30, "Linjelasrar röd+grön: CW, 3 V PSU (ingen datalänk)",
            ha="center", fontsize=6.8, color=MUTED, style="italic")
    fig.tight_layout(); return fig


def fig_assembly(sim, figsize=(7.4, 4.0)):
    Wd, T = sim["width"], sim["thickness"]
    fig = _fig(figsize); ax = fig.add_subplot(111)
    _ax(ax, "MÄTHUVUD — montering (ändvy, schematisk, ej skala)")
    ax.add_patch(plt.Rectangle((-150, -9), 300, 9, fc="#cfcabb", ec=MUTED))      # transportband
    ax.add_patch(plt.Rectangle((-Wd / 2, 0), Wd, T, fc="#efe9d8", ec=GOLD, lw=1.4))  # bräda
    ax.text(0, T / 2, f"bräda {Wd:.0f}×{T:.0f} mm", ha="center", fontsize=7, color="#6a5a2a")
    # överliggande ytkamera + RGB/NIR-strobe
    ax.add_patch(mpatches.FancyBboxPatch((-22, 128), 44, 18, boxstyle="round,pad=1,rounding_size=3",
                 fc="#efe6f7", ec=INK, lw=1.1))
    ax.text(0, 137, "Ytkamera line-scan\n+ RGB/NIR-strobe", ha="center", va="center", fontsize=6.6, color=INK)
    for sx in (-Wd / 2, Wd / 2):
        ax.plot([0, sx], [128, T], color=PURP, lw=0.8, ls=(0, (3, 2)))
    # oblika moduler
    ax.add_patch(mpatches.FancyBboxPatch((-150, 92), 40, 20, boxstyle="round,pad=1,rounding_size=3",
                 fc="#fde9e3", ec=INK, lw=1.1)); ax.text(-130, 102, "Modul V\nröd 650", ha="center", va="center", fontsize=6.6)
    ax.add_patch(mpatches.FancyBboxPatch((110, 92), 40, 20, boxstyle="round,pad=1,rounding_size=3",
                 fc="#e3f3ea", ec=INK, lw=1.1)); ax.text(130, 102, "Modul H\ngrön 520", ha="center", va="center", fontsize=6.6)
    ax.annotate("", xy=(-Wd / 2 + 6, T), xytext=(-126, 92), arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.8))
    ax.annotate("", xy=(Wd / 2 - 6, T), xytext=(126, 92), arrowprops=dict(arrowstyle="-|>", color=GRN, lw=1.8))
    _oa = f"{sim['rig'].oblique_angle_deg:.0f}°"
    ax.text(-92, 70, _oa, color=RED, fontsize=8); ax.text(74, 70, _oa, color=GRN, fontsize=8)
    # punktlaser: 3× spridda LÄNGS 1 m (in i bilden) → i ändvyn ett centrerat nedåt-skott
    ax.plot([0, 0], [118, T], color=PURP, lw=1.2, ls=(0, (1, 1)))
    ax.plot(0, 120, marker="v", ms=9, color=PURP, mec="k", mew=0.4)
    ax.text(0, 114, "3× punktlaser (V/C/H) längs 1 m (in i bilden) → ankrar LÄNGSprofilen",
            ha="center", fontsize=6.3, color=PURP)
    ax.text(-148, 122, f"standoff ≈ {sim['rig'].module_standoff_mm:.0f} mm", fontsize=6.3, color=MUTED)
    ax.add_patch(plt.Rectangle((132, -9), 18, 12, fc="#bdb8aa", ec=MUTED))
    ax.text(141, -3, "enc", ha="center", fontsize=5.8, color=INK)
    ax.set_xlim(-165, 165); ax.set_ylim(-15, 155); ax.set_aspect("auto")
    ax.set_xlabel("bredd (mm)"); ax.set_ylabel("höjd över band (mm)")
    fig.tight_layout(); return fig


# --------------------------------------------------------------------- metrics
def metrics(sim):
    z = sim["meas"]["z_fused"]; lbl = sim["board"]["label"]; btrue = sim["board"]["height"]
    Hpx, Wpx = z.shape
    pls = [float(np.median(btrue[int(f * (Hpx - 1)), :])) for f in PL_FRACS]
    counts = {CLASSES[c]: int((lbl == c).sum()) for c in range(1, 7) if (lbl == c).any()}
    d = datarate(sim); w = sim["warp"]
    ps = sim["meas"].get("pass_std_mm", float("nan")); npass = sim.get("passes", 1)
    rep1 = round(ps * 1000, 1) if ps == ps else None                 # µm, 1 pass
    repN = round(ps / np.sqrt(npass) * 1000, 1) if ps == ps else None  # µm efter medel
    return {
        "tjocklek_punktlaser_mm": round(float(np.mean(pls)), 1),
        "tackning_pct": round(sim["meas"]["coverage"] * 100, 1),
        "langd_mm": round(sim["L"]), "bredd_mm": round(sim["width"]),
        "defekter": counts,
        "pitch_mm": round(d["pitch_mm"], 3), "boards_per_min": round(d["boards_per_min"], 1),
        "mb_per_s": round(d["mb_per_s"], 1), "profiles_per_s": round(d["profiles_per_s"]),
        "twist_mm": round(w["twist_mm"], 1), "bow_mm": round(w["bow_mm"], 1),
        "cup_mm": round(w["cup_mm"], 1),
        "passes": npass, "repeat_1pass_um": rep1, "repeat_avg_um": repN,
    }


if __name__ == "__main__":
    s = simulate(1000, 150, 45, seed=3, boards_per_min=60, bow_mm=1.5, cup_mm=0.8, twist_mm=2.2)
    print("metrics:", metrics(s))
    print("bom_total:", bom_total(), "SEK")
    figs = [("bench", fig_bench(s, 0.55)), ("profcams", fig_profile_cams(s, 0.55)),
            ("surfcams", fig_surface_cams(s, 0.55)), ("length", fig_length_profile(s, 0.55)),
            ("cross", fig_cross_section(s, 0.5)), ("heightmap", fig_heightmap(s, 0.55)),
            ("surface3d", fig_surface3d(s, 1.0)), ("throughput", fig_throughput(s)),
            ("wiring", fig_wiring(s)), ("assembly", fig_assembly(s))]
    for name, f in figs:
        f.savefig(f"/tmp/proto_{name}.png", facecolor="#fff", bbox_inches="tight")
    print(f"renderade {len(figs)} figurer")
