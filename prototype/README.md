# Virkesskanner — prototypbänk (GUI)

Enkelt, webbaserat prototyp-GUI för **ett** dubbel-oblikt mäthuvud, brädor upp
till 1 m. Återanvänder repo-roten (`src/board`, `src/hardware`, `src/laser`) för
den simulerade hårdvaran. Tänkt att köra på bänk-datorn (t.ex. Jetson Orin Nano).

## Kör
```bash
pip install -r prototype/requirements.txt
streamlit run prototype/app.py
```
Öppnas på http://localhost:8501

## Vyer
- **Bänk (2D ovanifrån):** brädan passerar mäthuvudet (skannlinje + matning).
- **Tvärsnitt:** live höjdprofil (röd/grön linjelaser) + **3 punktlasrar** (absolut
  tjocklek, V/C/H) – fusion-ankare.
- **Höjdkarta:** uppbyggd höjd + defekt-overlay.
- **Enkel 3D:** matplotlib-yta av uppmätt bräda.

## Hårdvara (prototyp, per huvud)
- 1× NVIDIA Jetson Orin Nano Super (edge-compute + U-Net).
- 2× Hikrobot MV-CS050-10UM mono (USB3) + 8 mm lins + bandpass (650/520 nm).
- 1× röd 650 nm + 1× grön 520 nm linjelaser (oblika).
- 3× punktlaser-avståndssensor (V/C/H) för absolut tjocklek.
- T-spårsram, encoder, transport för 1 m. Se BOM i chatten / docs.
