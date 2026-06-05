"""Prototyp-GUI (Streamlit) — multisensor virkesskanner-bänk, ETT dubbel-oblikt
mäthuvud, brädor 1 m (cross-feed). Visar ALLA sensorer live enligt spec.

Två lägen:
  • Manuell inspektion — välj bräda, skevhet och takt; dra matningen.
  • Live-simulering — riggen "kör": brädan glider mjukt förbi huvudet (CSS-animerad
    bänk, standardtakt 60 brädor/min) och nya SLUMPADE 1 m-brädor (små mm-avvikelser
    + vridning/bukt/kupa + sprickor/kvist/vankant/röta) strömmar in en efter en.

Den mjuka rörelsen (bänken) körs i en lätt SVG som webbläsaren interpolerar mellan
serveruppdateringar (CSS-transition) → glider jämnt oavsett serverns tick-takt; de
tyngre sensorvyerna uppdateras i en egen, lugnare takt.

    pip install -r prototype/requirements.txt
    streamlit run prototype/app.py
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from proto_sim import (simulate, metrics, datarate, PL_FRACS, fig_profile_cams,
                       fig_surface_cams, fig_length_profile, fig_cross_section,
                       fig_heightmap, fig_surface3d, fig_throughput,
                       bom_rows, bom_total, interface_rows, fig_wiring, fig_assembly)
from src.hardware import Rig

st.set_page_config(page_title="Virkesskanner — prototyp", layout="wide", page_icon="🪵")

BENCH_TICK = 0.12        # s mellan bänk-uppdateringar (lätt SVG)
SENSOR_TICK = 0.7        # s mellan tunga sensor-uppdateringar
GLIDE_S = 0.75           # CSS-transition – ≥ värsta serverglappet → kontinuerlig glidning

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
  .live-dot { display:inline-block; width:9px; height:9px; border-radius:50%; background:#2f9e6e;
              margin-right:7px; animation:lp 1.2s infinite; }
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
@st.cache_data(show_spinner=False, max_entries=64)
def run(length, width, thick, seed, subtle, takt, rate, bow, cup, twist):
    return simulate(length_mm=length, width_mm=width, thickness_mm=thick, seed=seed,
                    subtle=subtle, boards_per_min=takt, profile_rate_hz=rate,
                    bow_mm=bow, cup_mm=cup, twist_mm=twist)


def stream_board(rng):
    """Slumpad 1 m-bräda: små mm-avvikelser i mått + global skevhet (twist/bukt/kupa)
    ovanpå lokala defekter (sprickor, kvist, vankant, röta, hål)."""
    return dict(width=int(round(np.clip(150 + rng.normal(0, 3), 140, 160))),
                thick=int(round(np.clip(45 + rng.normal(0, 2), 38, 52))),
                seed=int(rng.integers(0, 9999)), subtle=False,
                bow=float(abs(rng.normal(0, 1.4))),
                cup=float(abs(rng.normal(0, 0.9))),
                twist=float(rng.normal(0, 2.2)))


# ---------------- mjuk bänk (CSS-animerad SVG) ----------------
def bench_svg(feed, L, W, playing):
    """Lätt SVG ovanifrån: 1 m-brädan glider i sidled förbi den fasta laserlinjen.
    Brädans translateY animeras av CSS → mjuk glidning mellan serveruppdateringar."""
    Wp, Hp = 1060, 300
    x0, x1, Y0, bH = 70, 900, 150, 150
    bw = x1 - x0
    ty = feed * bH
    trans = f"transition:transform {GLIDE_S}s linear;" if playing else ""
    pls = "".join(
        f'<polygon points="{x0+f*bw-7},{Y0-15} {x0+f*bw+7},{Y0-15} {x0+f*bw},{Y0-2}" '
        f'fill="#a23ad6" stroke="#222" stroke-width="0.6"/>' for f in PL_FRACS)
    grp = f'style="transform:translateY({ty}px);{trans}"'
    return f"""
<div style="background:#fff;border:1px solid #e3e1d9;border-radius:12px;padding:6px 10px 2px;">
<svg viewBox="0 0 {Wp} {Hp}" width="100%" style="display:block">
  <defs><clipPath id="scan"><rect x="0" y="{Y0}" width="{Wp}" height="{Hp-Y0}"/></clipPath></defs>
  <rect x="0" y="0" width="{Wp}" height="{Hp}" fill="#faf9f4"/>
  <text x="{x0}" y="22" fill="#23262b" font-size="14" font-weight="700"
        font-family="IBM Plex Sans,sans-serif">BÄNK — bräda matas i sidled förbi 1 m-laserlinjen</text>
  <g {grp}><rect x="{x0}" y="{Y0-bH}" width="{bw}" height="{bH}" rx="6"
        fill="#efe9d8" stroke="#b9a96f" stroke-width="2"/></g>
  <g clip-path="url(#scan)" {grp}><rect x="{x0}" y="{Y0-bH}" width="{bw}" height="{bH}" rx="6"
        fill="#2f6fb0" opacity="0.16"/></g>
  <rect x="{x0+bw*0.40}" y="{Y0-58}" width="{bw*0.20}" height="34" rx="5"
        fill="#23262b" opacity="0.9"/>
  <text x="{x0+bw*0.5}" y="{Y0-36}" fill="#fff" font-size="11" text-anchor="middle"
        font-family="IBM Plex Sans,sans-serif">mäthuvud</text>
  <line x1="{x0-6}" y1="{Y0-1.5}" x2="{x1+6}" y2="{Y0-1.5}" stroke="#e8542c" stroke-width="2.6"/>
  <line x1="{x0-6}" y1="{Y0+1.5}" x2="{x1+6}" y2="{Y0+1.5}" stroke="#2f9e6e" stroke-width="2.6"/>
  {pls}
  <text x="{x1+10}" y="{Y0+4}" fill="#23262b" font-size="11"
        font-family="IBM Plex Sans,sans-serif">laserlinje 1 m</text>
  <text x="{x1+10}" y="{Y0+18}" fill="#6a6e74" font-size="10"
        font-family="IBM Plex Sans,sans-serif">röd 650 + grön 520</text>
  <text x="{x0+bw*0.5}" y="{Hp-12}" fill="#b06" font-size="12" text-anchor="middle"
        font-family="IBM Plex Sans,sans-serif">↓ matning ({W:.0f} mm bredd) · {feed*100:.0f} %</text>
</svg></div>"""


# ---------------- session-state ----------------
ss = st.session_state
ss.setdefault("mode", "Live-simulering")
ss.setdefault("running", False)
ss.setdefault("feed", 0.0)
ss.setdefault("t_last", 0.0)
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

sb.header("BRÄDA")
length = sb.selectbox("Brädlängd (mm)", [500, 1000], index=0,
                      help="500 mm = Fas 1 (kortare laserlinje, finare upplösning). 1000 mm = full bräda.")

sb.header("TRANSPORTBAND")
takt = sb.slider("Takt (brädor/min)", 10, 180, 20, 5)
rate = sb.slider("Profiltakt (profiler/s)", 100, 1200, 490, 10)
_feed = 150 / 1000 * takt / 60
sb.caption(f"Bandhastighet ≈ **{_feed*1000:.0f} mm/s** ({_feed:.2f} m/s) · matnings-pitch ≈ "
           f"**{_feed*1000/rate:.2f} mm/profil**. 20/min ≈ 50 mm/s (matchar mini-transportören).")
xpos = sb.slider("Tvärsnitt vid längd (%)", 0, 100, 50, 1) / 100.0

if ss.mode == "Manuell inspektion":
    sb.header("MÅTT (manuell)")
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
else:
    sb.header("DRIFT")
    cstart, cstop = sb.columns(2)
    if cstart.button("▶ Start", use_container_width=True, type="primary", disabled=ss.running):
        ss.running = True; ss.t_last = time.time(); st.rerun()
    if cstop.button("⏸ Stopp", use_container_width=True, disabled=not ss.running):
        ss.running = False; st.rerun()
    if sb.button("⏭ Nästa bräda", use_container_width=True):
        ss.board = stream_board(np.random.default_rng(ss.rng_seed + ss.count + 1))
        ss.feed = 0.0; st.rerun()
    ss.rng_seed = sb.number_input("Slumpfrö (brädström)", 0, 9999, ss.rng_seed, 1)
    sb.caption(f"Brädor körda denna session: **{ss.count}**")


# ---------------- vy-rendering ----------------
def card(fig):
    with st.container(border=True):
        st.pyplot(fig, width="stretch")
    plt.close(fig)


def kpi_row(sim):
    m = metrics(sim)
    c = st.columns(7)
    c[0].metric("Takt", f"{sim['takt']:.0f}/min")
    c[1].metric("Bredd", f"{m['bredd_mm']} mm")
    c[2].metric("Tjocklek (punktl.)", f"{m['tjocklek_punktlaser_mm']} mm")
    c[3].metric("Vridning", f"{m['twist_mm']} mm")
    c[4].metric("Bukt/kupa", f"{m['bow_mm']}/{m['cup_mm']} mm")
    c[5].metric("Matnings-pitch", f"{m['pitch_mm']:.2f} mm")
    c[6].metric("Dataflöde", f"{m['mb_per_s']} MB/s")


def render_sensors(sim, feed_frac, xpos, playing):
    t1, t2, t3, t4, t5 = st.tabs(["📷 Live-kameror", "📐 Profiler & 3D",
                                  "⚙️ Datatakt & fart", "🔩 Hårdvara",
                                  "🧾 BOM & systemkoppling"])
    with t1:
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
            if playing:
                with st.container(border=True):
                    st.info("3D-ytan ritas när bandet står stilla (⏸ Stopp) — "
                            "hålls lätt under körning för mjuk animering.")
            else:
                card(fig_surface3d(sim, feed_frac))
    with t3:
        card(fig_throughput(sim))
        d = datarate(sim)
        g = st.columns(4)
        g[0].metric("Matnings-pitch", f"{d['pitch_mm']:.2f} mm")
        g[1].metric("Profiler/s", f"{d['profiles_per_s']:.0f}")
        g[2].metric("Mätpunkter/s", f"{d['points_per_s']/1e6:.1f} M")
        g[3].metric("Profiler/bräda", f"{d['n_profiles']}")
        st.caption("Högre takt → snabbare band → färre profiler per bräda (grövre "
                   "matningsupplösning). Höj profiltakten för att behålla upplösningen "
                   "vid hög takt (begränsas av kamerans ROI-radtakt).")
    with t4:
        hardware_specs()
    with t5:
        bom_panel(sim)


def bom_panel(sim):
    st.markdown('<div class="ph-sec">Materiallista — fasad uppbyggnad (ett mäthuvud)</div>',
                unsafe_allow_html=True)
    st.dataframe(bom_rows(), hide_index=True, width="stretch")
    f1, f12, full = bom_total(1), bom_total(2), bom_total(3)
    c = st.columns(3)
    c[0].metric("Fas 1 — vänster (röd)", f"{f1:,} kr".replace(",", " "), help="1 kamera + röd laser + Jetson + alu-ram — putta för hand")
    c[1].metric("Fas 1+2 — dubbel-oblik", f"{f12:,} kr".replace(",", " "), delta=f"+{f12-f1:,} kr".replace(",", " "))
    c[2].metric("Full svit (Fas 1–3)", f"{full:,} kr".replace(",", " "), delta=f"+{full-f12:,} kr".replace(",", " "))
    f1s = f"{f1:,}".replace(",", " ")
    st.caption(f"**Fas 1 (~{f1s} kr):** bara *vänster* modul (röd 650 + 1 kamera) på en enkel "
               "alu-ram – putta brädan för hand och verifiera att trianguleringen ger en höjdprofil "
               "(kameran free-run, ingen encoder behövs än). **Fas 2:** komplettera *höger* modul "
               "(grön 520 + kamera nr 2) → full dubbel-oblik med occlusion-fyllning. **Fas 3:** "
               "ytkamera + NIR/RGB + 3 punktlaser + encoder. — CS050 har C-mount och **kräver "
               "objektiv** (ligger i listan, 1 per kamera). MindVision är NBASE-T → ingen switch "
               "behövs. Budget-punktlaser: VL53L1X ToF (~70 kr, ±5 mm) för konceptet.")

    st.markdown('<div class="ph-sec">Så kopplas allt ihop</div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="medium")
    with a:
        card(fig_wiring(sim))
    with b:
        card(fig_assembly(sim))

    st.markdown('<div class="ph-sec">Alla gränssnitt & uppdateringsfrekvenser</div>',
                unsafe_allow_html=True)
    st.dataframe(interface_rows(sim), hide_index=True, width="stretch")
    st.caption("**Profilkameror:** var sin USB3-controller (~307 MB/s/st ryms i ~500 MB/s). "
               "**Ytkamera:** NBASE-T → vid prototyptakt behövs bara ~10 MB/s, **rinner rakt in i "
               "Jetsons 1 GbE** (118 MB/s); full 10GigE krävs först vid max radtakt (110 kHz). "
               "**Encoder (RS422)** går till *ytkameran* som sköter TDI-radsynk själv och driver "
               "**R/G/B-strobe via sina 3 inbyggda strobe-utgångar** (färg = radtakt/4 med NIR); samma "
               "encoder triggar profilkamerorna. **Punktlaser:** 3× spridda **längs 1 m** (V/C/H), "
               "läses analogt via MCP3008 (SPI) → ger **absoluta Z-ankare längs LÄNGSprofilen** som "
               "låser linjelaserns skala/drift (tvärsnittet tvärs 150 mm kommer från de oblika "
               "linjelasrarna).")


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
    sim = run(length, width, thick, int(seed), subtle, takt, rate, bow, cup, twist)
    st.markdown(bench_svg(feed, length, width, False), unsafe_allow_html=True)
    st.write("")
    kpi_row(sim)
    render_sensors(sim, feed, xpos, False)

else:
    bp = ss.board

    # --- lätt bänk-loop: tidsbaserad matning + mjuk SVG-glidning ---
    @st.fragment(run_every=BENCH_TICK if ss.running else None)
    def bench_loop():
        if ss.running:
            now = time.time()
            dt = min(0.5, now - ss.t_last) if ss.t_last else BENCH_TICK
            ss.t_last = now
            period = 60.0 / max(1.0, takt)          # sek för en bräda att passera
            ss.feed += dt / period
            if ss.feed >= 1.0:
                done = run(length, bp["width"], bp["thick"], bp["seed"], bp["subtle"],
                           takt, rate, bp["bow"], bp["cup"], bp["twist"])
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
        cur = ss.board
        status = "RIGG KÖR — matar bräda" if ss.running else "PAUSAD"
        dot = '<span class="live-dot"></span>' if ss.running else ""
        st.markdown(f'<div class="live-bar">{dot}{status} &nbsp;·&nbsp; aktuell bräda: '
                    f'{length}×{cur["width"]}×{cur["thick"]} mm · vrid {cur["twist"]:+.1f} / bukt {cur["bow"]:.1f} '
                    f'/ kupa {cur["cup"]:.1f} mm (seed {cur["seed"]}) &nbsp;·&nbsp; takt {takt}/min</div>',
                    unsafe_allow_html=True)
        st.markdown(bench_svg(min(ss.feed, 1.0), length, cur["width"], ss.running),
                    unsafe_allow_html=True)

    # --- tyngre sensor-loop: egen, lugnare takt så bänken hålls mjuk ---
    @st.fragment(run_every=SENSOR_TICK if ss.running else None)
    def sensor_loop():
        cur = ss.board
        sim = run(length, cur["width"], cur["thick"], cur["seed"], cur["subtle"],
                  takt, rate, cur["bow"], cur["cup"], cur["twist"])
        kpi_row(sim)
        render_sensors(sim, min(ss.feed, 1.0), xpos, ss.running)

    bench_loop()
    st.write("")
    sensor_loop()

    if ss.log:
        st.markdown('<div class="ph-sec">Strömmade brädor (senaste)</div>', unsafe_allow_html=True)
        st.dataframe(ss.log, hide_index=True, width="stretch")
