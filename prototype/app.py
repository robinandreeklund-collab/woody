"""Prototyp-GUI (Streamlit) för virkesskanner-bänken — ETT dubbel-oblikt mäthuvud,
brädor upp till 1 m. Enkelt, webbaserat, tänkt att köra på prototyp-datorn
(t.ex. Jetson Orin Nano). Visar simulerad hårdvara + hur brädan passerar huvudet
(2D bänkvy), live-tvärsnitt med punktlaser-ankare, höjdkarta och en enkel 3D.

    pip install -r prototype/requirements.txt
    streamlit run prototype/app.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from proto_sim import (simulate, fig_bench, fig_profile, fig_heightmap,
                       fig_surface3d, metrics)

st.set_page_config(page_title="Virkesskanner — prototyp", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
  .block-container { padding-top: 1.4rem; max-width: 1500px; }
  h1, h2, h3 { font-family: 'IBM Plex Sans', system-ui, sans-serif; }
  .stMetric { background:#fff; border:1px solid #e3e1d9; border-radius:10px; padding:10px 12px; }
  [data-testid="stSidebar"] { background:#ecebe4; }
</style>
""", unsafe_allow_html=True)

st.title("Multisensor virkesskanner — prototypbänk")
st.caption("1 dubbel-oblikt mäthuvud (röd 650 nm + grön 520 nm) · 3 punktlasrar · "
           "brädor upp till 1 m · simulerad hårdvara")

# ---------------- inställningar ----------------
sb = st.sidebar
sb.header("Bräda")
length = sb.slider("Längd (mm)", 200, 1000, 1000, 50)
width = sb.slider("Bredd (mm)", 75, 220, 150, 5)
thick = sb.slider("Tjocklek (mm)", 18, 150, 45, 1)
seed = sb.number_input("Bräd-id (seed)", 0, 9999, 3, 1)
subtle = sb.checkbox("Subtila defekter (sensortest)", False)
sb.header("Drift")
feed = sb.slider("Matning / skannposition (%)", 0, 100, 60, 1) / 100.0
sb.caption("Dra för att se brädan passera huvudet.")

@st.cache_data(show_spinner="Simulerar hårdvara …")
def run(length, width, thick, seed, subtle):
    return simulate(length_mm=length, width_mm=width, thickness_mm=thick,
                    seed=seed, subtle=subtle)

sim = run(length, width, thick, int(seed), subtle)
m = metrics(sim)

# ---------------- nyckeltal ----------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Längd", f"{m['langd_mm']} mm")
c2.metric("Bredd", f"{m['bredd_mm']} mm")
c3.metric("Tjocklek (punktlaser)", f"{m['tjocklek_punktlaser_mm']} mm")
c4.metric("Täckning", f"{m['tackning_pct']} %")
top = max(m["defekter"], key=m["defekter"].get) if m["defekter"] else "—"
c5.metric("Vanligaste defekt", top)

st.divider()
# ---------------- vyer ----------------
left, right = st.columns(2)
with left:
    st.pyplot(fig_bench(sim, feed), use_container_width=True)
    st.pyplot(fig_heightmap(sim, feed), use_container_width=True)
with right:
    st.pyplot(fig_profile(sim, feed), use_container_width=True)
    st.pyplot(fig_surface3d(sim, feed), use_container_width=True)

with st.expander("Om sensorfusion (linjelaser + 3 punktlasrar)"):
    st.markdown(
        "- **Linjelasrar (röd/grön, oblika):** ger hela tvärsnittets *form* — topp + "
        "2 sidor/vankant — och fyller varandras skuggor.\n"
        "- **3 punktlasrar (V/C/H):** ger *absolut tjocklek* med hög noggrannhet i tre "
        "punkter (lila trianglar i tvärsnittet).\n"
        "- **Fusion:** punktlasrarna **ankrar** linjeprofilen i absolut skala (rättar drift/"
        "offset), linjelasrarna fyller i hela profilen mellan punkterna. Tillsammans → "
        "noggrann absolut 3D-profil av varje bräda.")
