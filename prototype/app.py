"""Prototyp-GUI (Streamlit) — multisensor virkesskanner-bänk, ETT dubbel-oblikt
mäthuvud, brädor 1 m (cross-feed). Visar ALLA sensorer live enligt spec.

Två lägen:
  • Manuell inspektion — välj bräda, skevhet och driftparametrar; dra matningen.
  • Live-simulering — riggen "kör": matningen animeras och nya SLUMPADE 1 m-brädor
    (små mm-avvikelser + vridning/bukt/kupa + sprickor/kvist/vankant/röta) strömmar
    in en efter en, som tänkt hårdvara i drift.

Sensorvyer (exakt enligt src.hardware-specar):
  profilkamera RÖD 650 / GRÖN 520 (mono+bandpass, rå laserstripe), ytkamera FÄRG,
  ytkanal NIR, 3 punktlaser, längsprofil, tvärsnitt, höjdkarta, 3D, datatakt.

    pip install -r prototype/requirements.txt
    streamlit run prototype/app.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from proto_sim import (simulate, metrics, datarate, fig_bench, fig_profile_cams,
                       fig_surface_cams, fig_length_profile, fig_cross_section,
                       fig_heightmap, fig_surface3d, fig_throughput)
from src.hardware import Rig

st.set_page_config(page_title="Virkesskanner — prototyp", layout="wide", page_icon="🪵")

STEP_REF = 0.10          # referenssteg/tick vid 0,25 m/s (skalas med farten)
TICK_S = 0.55            # sekunder mellan live-ticks

st.markdown("""
<style>
  .block-container { padding-top: 1.0rem; padding-bottom: 2rem; max-width: 1520px; }
  header[data-testid="stHeader"] { background: transparent; height: 0; }
  #MainMenu, footer { visibility: hidden; }
  .ph-title { font: 700 30px 'IBM Plex Sans', system-ui, sans-serif; color:#23262b; margin:0; }
  .ph-sub   { color:#6a6e74; font-size:14px; margin:3px 0 0; }
  .ph-rule  { height:3px; background:linear-gradient(90deg,#e8542c,#2f9e6e,#2f6fb0,#a23ad6); border-radius:3px; margin:12px 0 16px; }
  .ph-sec   { font:700 12px 'IBM Plex Mono', monospace; letter-spacing:.08em; color:#6a6e74; margin:6px 0 2px; text-transform:uppercase; }
  [data-testid="stMetric"] { background:#fff; border:1px solid #e3e1d9; border-radius:12px;
                             padding:10px 14px; box-shadow:0 1px 3px rgba(0,0,0,.04); }
  [data-testid="stMetricLabel"] p { color:#6a6e74 !important; font-size:11px; font-weight:600; }
  [data-testid="stMetricValue"] { color:#23262b !important; font-weight:700; font-size:22px; }
  [data-testid="stSidebar"] { background:#ecebe4; border-right:1px solid #ddd9cf; }
  [data-testid="stSidebar"] h2 { font-size:14px; color:#23262b; letter-spacing:.03em; }
  div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-radius:12px; }
  button[data-baseweb="tab"] { font-weight:600; }
  .live-dot { display:inline-block; width:9px; height:9px; border-radius:50%;
              background:#2f9e6e; margin-right:7px;
              animation:lp 1.2s infinite; }
  @keyframes lp { 0%{box-shadow:0 0 0 0 rgba(47,158,110,.6);} 70%{box-shadow:0 0 0 9px rgba(47,158,110,0);} 100%{box-shadow:0 0 0 0 rgba(47,158,110,0);} }
  .live-bar { background:#fff; border:1px solid #e3e1d9; border-radius:10px; padding:9px 14px;
              font:600 13px 'IBM Plex Sans',sans-serif; color:#23262b; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="ph-title">Multisensor virkesskanner — prototypbänk</div>'
            '<div class="ph-sub">1 dubbel-oblikt mäthuvud (röd 650 nm + grön 520 nm) · '
            'ytkamera färg + NIR · 3 punktlasrar · cross-feed, brädor 1 m · '
            'simulerad hårdvara, live</div><div class="ph-rule"></div>', unsafe_allow_html=True)


# ---------------- simulering (cachad) ----------------
@st.cache_data(show_spinner=False, max_entries=48)
def run(length, width, thick, seed, subtle, feed_mps, rate, bow, cup, twist):
    return simulate(length_mm=length, width_mm=width, thickness_mm=thick, seed=seed,
                    subtle=subtle, feed_mps=feed_mps, profile_rate_hz=rate,
                    bow_mm=bow, cup_mm=cup, twist_mm=twist)


def stream_board(rng):
    """Slumpad 1 m-bräda: små mm-avvikelser i mått + global skevhet (twist/bukt/kupa)
    ovanpå lokala defekter (sprickor, kvist, vankant, röta, hål)."""
    return dict(length=1000,
                width=int(round(np.clip(150 + rng.normal(0, 3), 140, 160))),
                thick=int(round(np.clip(45 + rng.normal(0, 2), 38, 52))),
                seed=int(rng.integers(0, 9999)), subtle=False,
                bow=float(abs(rng.normal(0, 1.4))),
                cup=float(abs(rng.normal(0, 0.9))),
                twist=float(rng.normal(0, 2.2)))


# ---------------- session-state ----------------
ss = st.session_state
ss.setdefault("mode", "Live-simulering")
ss.setdefault("running", False)
ss.setdefault("feed", 0.0)
ss.setdefault("rng_seed", 7)
ss.setdefault("board", None)
ss.setdefault("count", 0)
ss.setdefault("log", [])
if ss.board is None:
    ss.board = stream_board(np.random.default_rng(ss.rng_seed))


# ---------------- inställningar ----------------
sb = st.sidebar
sb.header("LÄGE")
ss.mode = sb.radio("Driftläge", ["Live-simulering", "Manuell inspektion"],
                   index=0 if ss.mode == "Live-simulering" else 1, label_visibility="collapsed")

sb.header("TRANSPORTBAND")
feed_mps = sb.slider("Bandhastighet (m/s)", 0.05, 1.0, 0.25, 0.05)
rate = sb.slider("Profiltakt (profiler/s)", 100, 1200, 490, 10)
sb.caption(f"Matnings-pitch ≈ **{feed_mps*1000/rate:.2f} mm/profil** "
           "(fart ÷ profiltakt → upplösning i matningsled).")
xpos = sb.slider("Tvärsnitt vid längd (%)", 0, 100, 50, 1) / 100.0

if ss.mode == "Manuell inspektion":
    sb.header("BRÄDA")
    width = sb.slider("Bredd (mm)", 140, 160, 150, 1)
    thick = sb.slider("Tjocklek (mm)", 38, 52, 45, 1)
    seed = sb.number_input("Bräd-id (seed)", 0, 9999, 3, 1)
    subtle = sb.checkbox("Subtila defekter (sensortest)", False)
    sb.header("SKEVHET (mm)")
    bow = sb.slider("Bukt / bow", 0.0, 5.0, 1.5, 0.1)
    cup = sb.slider("Kupa / cup", 0.0, 4.0, 0.8, 0.1)
    twist = sb.slider("Vridning / twist", -5.0, 5.0, 2.0, 0.1)
    sb.header("DRIFT")
    feed = sb.slider("Matning / skannposition (%)", 0, 100, 60, 1) / 100.0
    sb.caption("Dra för att se 1 m-brädan matas i sidled förbi huvudet.")
else:
    sb.header("DRIFT")
    cstart, cstop = sb.columns(2)
    if cstart.button("▶ Start", use_container_width=True, type="primary", disabled=ss.running):
        ss.running = True; st.rerun()
    if cstop.button("⏸ Stopp", use_container_width=True, disabled=not ss.running):
        ss.running = False; st.rerun()
    if sb.button("⏭ Nästa bräda", use_container_width=True):
        ss.board = stream_board(np.random.default_rng(ss.rng_seed + ss.count + 1))
        ss.feed = 0.0; st.rerun()
    ss.rng_seed = sb.number_input("Slumpfrö (brädström)", 0, 9999, ss.rng_seed, 1)
    sb.caption(f"Brädor körda denna session: **{ss.count}**")
    sb.progress(min(ss.feed, 1.0), text=f"Matning {min(ss.feed,1.0)*100:.0f} %")


# ---------------- vy-rendering ----------------
def card(fig):
    with st.container(border=True):
        st.pyplot(fig, width="stretch")
    plt.close(fig)


def kpi_row(sim):
    m = metrics(sim)
    cols = st.columns(7)
    cols[0].metric("Längd", f"{m['langd_mm']} mm")
    cols[1].metric("Bredd", f"{m['bredd_mm']} mm")
    cols[2].metric("Tjocklek (punktl.)", f"{m['tjocklek_punktlaser_mm']} mm")
    cols[3].metric("Vridning", f"{m['twist_mm']} mm")
    cols[4].metric("Bukt/kupa", f"{m['bow_mm']}/{m['cup_mm']} mm")
    cols[5].metric("Kapacitet", f"{m['boards_per_min']}/min")
    cols[6].metric("Dataflöde", f"{m['mb_per_s']} MB/s")
    return m


def render_all(sim, feed_frac, xpos):
    t1, t2, t3, t4 = st.tabs(["📷 Live-kameror", "📐 Profiler & 3D",
                              "⚙️ Datatakt & fart", "🔩 Hårdvara"])
    with t1:
        card(fig_bench(sim, feed_frac))
        a, b = st.columns(2, gap="medium")
        with a:
            card(fig_profile_cams(sim, feed_frac))
        with b:
            card(fig_surface_cams(sim, feed_frac))
    with t2:
        a, b = st.columns(2, gap="medium")
        with a:
            card(fig_length_profile(sim, feed_frac))
            card(fig_heightmap(sim, feed_frac))
        with b:
            card(fig_cross_section(sim, xpos))
            card(fig_surface3d(sim, feed_frac))
    with t3:
        card(fig_throughput(sim))
        d = datarate(sim)
        g = st.columns(4)
        g[0].metric("Matnings-pitch", f"{d['pitch_mm']:.2f} mm")
        g[1].metric("Profiler/s", f"{d['profiles_per_s']:.0f}")
        g[2].metric("Mätpunkter/s", f"{d['points_per_s']/1e6:.1f} M")
        g[3].metric("Profiler/bräda", f"{d['n_profiles']}")
        st.caption("Högre bandhastighet → färre profiler per bräda (grövre upplösning i "
                   "matningsled) men högre kapacitet. Höj profiltakten för att behålla "
                   "upplösningen vid hög fart (begränsas av kamerans ROI-radtakt).")
    with t4:
        hardware_specs()


def hardware_specs():
    r = Rig(board_length_mm=1000.0, board_width_mm=150.0, board_thickness_mm=45.0)
    red, grn, cam = r.laser, r.laser_green, r.profile_cam
    rows = [
        {"Sensor": "Linjelaser V (röd)", "Modell": red.name,
         "Spec": f"{red.wavelength_nm:.0f} nm · {red.power_mw:.0f} mW · {red.fan_angle_deg:.0f}° · Ø{red.diameter_mm:.0f} mm · {red.voltage_v:.0f} V"},
        {"Sensor": "Linjelaser H (grön)", "Modell": grn.name,
         "Spec": f"{grn.wavelength_nm:.0f} nm · {grn.power_mw:.0f} mW · {grn.fan_angle_deg:.0f}° · Ø{grn.diameter_mm:.0f} mm · {grn.voltage_v:.0f} V"},
        {"Sensor": "Profilkamera ×2", "Modell": cam.name,
         "Spec": f"mono {cam.width_px}×{cam.height_px} · {cam.pixel_um:.2f} µm · {cam.frame_rate_full_hz:.0f} fps · {cam.interface} · bandpass 650/520 nm"},
        {"Sensor": "Ytkamera färg", "Modell": r.surface_cam.name,
         "Spec": f"linjekamera {r.surface_cam.px_across}px · {r.surface_cam.pixel_um:.0f} µm · {r.surface_cam.interface}"},
        {"Sensor": "Ytkanal NIR", "Modell": "strobad NIR-belysning",
         "Spec": "~850 nm strobe via ytkameran → blånad/röta mörka"},
        {"Sensor": "Punktlaser ×3", "Modell": "avståndsmätare V/C/H",
         "Spec": "absolut tjocklek · analog/I²C → Jetson ADC · fusion-ankare"},
    ]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Lasrar: iadiy line-module-serien (röd 650 nm 100 mW, grön 520 nm 50 mW — "
               "grönt toppar på 50 mW). Olika våglängd + matchande bandpassfilter → ingen "
               "förväxling. Beställ grön som fokuserbar custom-linje för skärpa.")


# ---------------- körning ----------------
if ss.mode == "Manuell inspektion":
    sim = run(1000, width, thick, int(seed), subtle, feed_mps, rate, bow, cup, twist)
    kpi_row(sim)
    render_all(sim, feed, xpos)

else:
    interval = TICK_S if ss.running else None
    step = STEP_REF * (feed_mps / 0.25)          # animationssteg skalar med farten

    @st.fragment(run_every=interval)
    def live_panel():
        if ss.running:
            ss.feed += step
            if ss.feed >= 1.0:
                bp = ss.board
                done = run(bp["length"], bp["width"], bp["thick"], bp["seed"], bp["subtle"],
                           feed_mps, rate, bp["bow"], bp["cup"], bp["twist"])
                m = metrics(done)
                top = max(m["defekter"], key=m["defekter"].get) if m["defekter"] else "—"
                ss.count += 1
                ss.log.insert(0, {"#": ss.count, "Bredd": m["bredd_mm"], "Tjocklek": m["tjocklek_punktlaser_mm"],
                                  "Vrid": m["twist_mm"], "Bukt": m["bow_mm"], "Kupa": m["cup_mm"],
                                  "Täckning %": m["tackning_pct"],
                                  "Defekt": top.replace("_", " ") if top != "—" else "—"})
                ss.log = ss.log[:8]
                ss.board = stream_board(np.random.default_rng(ss.rng_seed + ss.count))
                ss.feed = 0.0

        bp = ss.board
        status = "RIGG KÖR — matar bräda" if ss.running else "PAUSAD"
        dot = '<span class="live-dot"></span>' if ss.running else ""
        st.markdown(f'<div class="live-bar">{dot}{status} &nbsp;·&nbsp; aktuell 1 m-bräda: '
                    f'{bp["width"]}×{bp["thick"]} mm · vrid {bp["twist"]:+.1f} / bukt {bp["bow"]:.1f} '
                    f'/ kupa {bp["cup"]:.1f} mm (seed {bp["seed"]}) &nbsp;·&nbsp; '
                    f'matning {min(ss.feed,1.0)*100:.0f} %</div>', unsafe_allow_html=True)
        st.write("")
        sim = run(bp["length"], bp["width"], bp["thick"], bp["seed"], bp["subtle"],
                  feed_mps, rate, bp["bow"], bp["cup"], bp["twist"])
        kpi_row(sim)
        render_all(sim, min(ss.feed, 1.0), xpos)

    live_panel()

    if ss.log:
        st.markdown('<div class="ph-sec">Strömmade 1 m-brädor (senaste)</div>', unsafe_allow_html=True)
        st.dataframe(ss.log, hide_index=True, width="stretch")
