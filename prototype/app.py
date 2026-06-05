"""Prototyp-GUI (Streamlit) — virkesskanner-bänk med ETT dubbel-oblikt mäthuvud,
brädor upp till 1 m (cross-feed). Webbaserat, tänkt att köra på prototyp-datorn
(Jetson Orin Nano). Ljust tema via .streamlit/config.toml.

Två lägen:
  • Manuell inspektion — välj bräda och dra matningen själv (granska en bräda).
  • Live-simulering — riggen "kör": matningen animeras automatiskt och nya
    SLUMPADE brädor strömmar in en efter en, precis som tänkt hårdvara i drift.

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
from proto_sim import (simulate, fig_bench, fig_profile, fig_heightmap,
                       fig_surface3d, metrics)
from src.hardware import Rig

st.set_page_config(page_title="Virkesskanner — prototyp", layout="wide", page_icon="🪵")

STEP_FRAC = 0.08          # matning per live-tick (8 % av bredden)
TICK_S = 0.6              # sekunder mellan live-ticks
LEN_CHOICES = (400, 600, 800, 1000)
WID_CHOICES = (100, 125, 150, 175, 200)
THK_CHOICES = (22, 34, 45, 63, 75)

st.markdown("""
<style>
  .block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1480px; }
  header[data-testid="stHeader"] { background: transparent; height: 0; }
  #MainMenu, footer { visibility: hidden; }
  .ph-title { font: 700 30px 'IBM Plex Sans', system-ui, sans-serif; color:#23262b; margin:0; }
  .ph-sub   { color:#6a6e74; font-size:14px; margin:3px 0 0; }
  .ph-rule  { height:3px; background:linear-gradient(90deg,#e8542c,#2f9e6e,#2f6fb0,#a23ad6); border-radius:3px; margin:12px 0 18px; }
  .ph-sec   { font:700 12px 'IBM Plex Mono', monospace; letter-spacing:.08em; color:#6a6e74; margin:4px 0 2px; text-transform:uppercase; }
  [data-testid="stMetric"] { background:#fff; border:1px solid #e3e1d9; border-radius:12px;
                             padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,.04); }
  [data-testid="stMetricLabel"] p { color:#6a6e74 !important; font-size:12px; font-weight:600; }
  [data-testid="stMetricValue"] { color:#23262b !important; font-weight:700; }
  [data-testid="stSidebar"] { background:#ecebe4; border-right:1px solid #ddd9cf; }
  [data-testid="stSidebar"] h2 { font-size:14px; color:#23262b; letter-spacing:.03em; }
  div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-radius:12px; }
  .live-dot { display:inline-block; width:9px; height:9px; border-radius:50%;
              background:#2f9e6e; margin-right:7px; box-shadow:0 0 0 0 rgba(47,158,110,.6);
              animation:lp 1.2s infinite; }
  @keyframes lp { 0%{box-shadow:0 0 0 0 rgba(47,158,110,.6);} 70%{box-shadow:0 0 0 9px rgba(47,158,110,0);} 100%{box-shadow:0 0 0 0 rgba(47,158,110,0);} }
  .live-bar { background:#fff; border:1px solid #e3e1d9; border-radius:10px; padding:9px 14px;
              font:600 13px 'IBM Plex Sans',sans-serif; color:#23262b; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="ph-title">Multisensor virkesskanner — prototypbänk</div>'
            '<div class="ph-sub">1 dubbel-oblikt mäthuvud (röd 650 nm + grön 520 nm) · '
            '3 punktlasrar (absolut tjocklek) · cross-feed, brädor upp till 1 m · '
            'simulerad hårdvara</div><div class="ph-rule"></div>', unsafe_allow_html=True)


# ---------------- simulering (cachad) ----------------
@st.cache_data(show_spinner=False, max_entries=64)
def run(length, width, thick, seed, subtle):
    return simulate(length_mm=length, width_mm=width, thickness_mm=thick,
                    seed=seed, subtle=subtle)


def random_board(rng):
    return dict(length=int(rng.choice(LEN_CHOICES)), width=int(rng.choice(WID_CHOICES)),
                thick=int(rng.choice(THK_CHOICES)), seed=int(rng.integers(0, 9999)),
                subtle=bool(rng.random() < 0.25))


# ---------------- session-state ----------------
ss = st.session_state
ss.setdefault("mode", "Live-simulering")
ss.setdefault("running", False)
ss.setdefault("feed", 0.0)
ss.setdefault("rng_seed", 7)
ss.setdefault("board", None)          # aktuella slump-bräd-parametrar
ss.setdefault("count", 0)
ss.setdefault("log", [])              # senaste klarmätta brädor
if ss.board is None:
    ss.board = random_board(np.random.default_rng(ss.rng_seed))


# ---------------- inställningar ----------------
sb = st.sidebar
sb.header("LÄGE")
ss.mode = sb.radio("Driftläge", ["Live-simulering", "Manuell inspektion"],
                   index=0 if ss.mode == "Live-simulering" else 1, label_visibility="collapsed")

if ss.mode == "Manuell inspektion":
    sb.header("BRÄDA")
    length = sb.slider("Längd (mm)", 200, 1000, 1000, 50)
    width = sb.slider("Bredd (mm)", 75, 220, 150, 5)
    thick = sb.slider("Tjocklek (mm)", 18, 150, 45, 1)
    seed = sb.number_input("Bräd-id (seed)", 0, 9999, 3, 1)
    subtle = sb.checkbox("Subtila defekter (sensortest)", False)
    sb.header("DRIFT")
    feed = sb.slider("Matning / skannposition (%)", 0, 100, 60, 1) / 100.0
    sb.caption("Dra för att se brädan matas i sidled förbi huvudet.")
else:
    sb.header("DRIFT")
    cstart, cstop = sb.columns(2)
    if cstart.button("▶ Start", use_container_width=True, type="primary", disabled=ss.running):
        ss.running = True; st.rerun()
    if cstop.button("⏸ Stopp", use_container_width=True, disabled=not ss.running):
        ss.running = False; st.rerun()
    if sb.button("⏭ Nästa bräda", use_container_width=True):
        ss.board = random_board(np.random.default_rng(ss.rng_seed + ss.count + 1))
        ss.feed = 0.0; st.rerun()
    ss.rng_seed = sb.number_input("Slumpfrö (brädström)", 0, 9999, ss.rng_seed, 1)
    sb.caption(f"Brädor körda denna session: **{ss.count}**")
    sb.progress(min(ss.feed, 1.0), text=f"Matning {min(ss.feed,1.0)*100:.0f} %")


# ---------------- gemensam vy-rendering ----------------
def card(fig):
    with st.container(border=True):
        st.pyplot(fig, width="stretch")
    plt.close(fig)


def render_views(sim, feed_frac):
    m = metrics(sim)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Längd", f"{m['langd_mm']} mm")
    c2.metric("Bredd", f"{m['bredd_mm']} mm")
    c3.metric("Tjocklek (punktlaser)", f"{m['tjocklek_punktlaser_mm']} mm")
    c4.metric("Täckning", f"{m['tackning_pct']} %")
    top = max(m["defekter"], key=m["defekter"].get) if m["defekter"] else "—"
    c5.metric("Vanligaste defekt", top.replace("_", " ") if top != "—" else "—")

    st.write("")
    st.markdown('<div class="ph-sec">Sensorvyer</div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="medium")
    with a:
        card(fig_bench(sim, feed_frac))
        card(fig_heightmap(sim, feed_frac))
    with b:
        card(fig_profile(sim, feed_frac))
        card(fig_surface3d(sim, feed_frac))
    return m, top


def hardware_specs():
    """Exakta modul-specar för prototyphuvudet (lasrar + kameror), från Rig."""
    r = Rig(board_length_mm=1000.0, board_width_mm=150.0, board_thickness_mm=45.0)
    red, grn, cam = r.laser, r.laser_green, r.profile_cam
    rows = [
        {"Modul": "Linjelaser V (röd)", "Modell": red.name,
         "Spec": f"{red.wavelength_nm:.0f} nm · {red.power_mw:.0f} mW · {red.fan_angle_deg:.0f}° linje · Ø{red.diameter_mm:.0f} mm · {red.voltage_v:.0f} V"},
        {"Modul": "Linjelaser H (grön)", "Modell": grn.name,
         "Spec": f"{grn.wavelength_nm:.0f} nm · {grn.power_mw:.0f} mW · {grn.fan_angle_deg:.0f}° linje · Ø{grn.diameter_mm:.0f} mm · {grn.voltage_v:.0f} V"},
        {"Modul": "Profilkamera ×2", "Modell": cam.name,
         "Spec": f"mono {cam.width_px}×{cam.height_px} · {cam.pixel_um:.2f} µm · {cam.frame_rate_full_hz:.0f} fps · {cam.interface} · bandpass {cam.bandpass_nm:.0f} nm"},
        {"Modul": "Punktlaser ×3", "Modell": "ToF/triangulerings-avståndsmätare",
         "Spec": "V / C / H längs 1 m-linjen · absolut tjocklek · analog/I²C till Jetson ADC"},
    ]
    st.markdown('<div class="ph-sec">Hårdvara — prototyphuvud</div>', unsafe_allow_html=True)
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Lasrar: iadiy line-module-serien (röd 650 nm 100 mW, grön 520 nm 50 mW — "
               "grönt toppar på 50 mW). Olika våglängd + matchande bandpassfilter → ingen "
               "förväxling mellan modulerna. Beställ grön som fokuserbar custom-linje för skärpa.")


def fusion_note():
    st.markdown('<div class="ph-sec">Sensorfusion</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "**Linjelasrar (röd/grön, oblika)** ger hela tvärsnittets *form* — topp + 2 "
            "sidor/vankant — och fyller varandras skuggor.  \n"
            "**3 punktlasrar (V/C/H)** ger *absolut tjocklek* med hög noggrannhet (lila "
            "trianglar i längsprofilen).  \n"
            "**Fusion:** punktlasrarna **ankrar** linjeprofilen i absolut skala (rättar "
            "drift/offset); linjelasrarna fyller i hela profilen mellan punkterna → "
            "noggrann absolut 3D-profil av varje bräda.")


# ---------------- körning ----------------
if ss.mode == "Manuell inspektion":
    sim = run(length, width, thick, int(seed), subtle)
    render_views(sim, feed)
    fusion_note()
    hardware_specs()

else:
    interval = TICK_S if ss.running else None

    @st.fragment(run_every=interval)
    def live_panel():
        # avancera matningen; vid brädans slut -> logga + ny slumpbräda
        if ss.running:
            ss.feed += STEP_FRAC
            if ss.feed >= 1.0:
                bp = ss.board
                sim_done = run(bp["length"], bp["width"], bp["thick"], bp["seed"], bp["subtle"])
                m = metrics(sim_done)
                top = max(m["defekter"], key=m["defekter"].get) if m["defekter"] else "—"
                ss.count += 1
                ss.log.insert(0, {"#": ss.count, "Längd": f"{m['langd_mm']}",
                                  "Bredd": f"{m['bredd_mm']}", "Tjocklek": f"{m['tjocklek_punktlaser_mm']}",
                                  "Täckning %": f"{m['tackning_pct']}",
                                  "Defekt": top.replace("_", " ") if top != "—" else "—"})
                ss.log = ss.log[:8]
                ss.board = random_board(np.random.default_rng(ss.rng_seed + ss.count))
                ss.feed = 0.0

        status = ("RIGG KÖR — matar bräda" if ss.running else "PAUSAD")
        dot = '<span class="live-dot"></span>' if ss.running else ""
        bp = ss.board
        st.markdown(f'<div class="live-bar">{dot}{status} &nbsp;·&nbsp; aktuell bräda: '
                    f'{bp["length"]}×{bp["width"]} mm, {bp["thick"]} mm tjock '
                    f'(seed {bp["seed"]}) &nbsp;·&nbsp; matning {min(ss.feed,1.0)*100:.0f} %'
                    f'</div>', unsafe_allow_html=True)
        st.write("")

        sim = run(bp["length"], bp["width"], bp["thick"], bp["seed"], bp["subtle"])
        render_views(sim, min(ss.feed, 1.0))

    live_panel()
    fusion_note()

    if ss.log:
        st.markdown('<div class="ph-sec">Strömmade brädor (senaste)</div>', unsafe_allow_html=True)
        st.dataframe(ss.log, hide_index=True, width="stretch")

    hardware_specs()
