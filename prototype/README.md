# Virkesskanner — prototypbänk (GUI)

Webbaserat prototyp-GUI för **ett** dubbel-oblikt mäthuvud, brädor **1 m**
(cross-feed). Visar **alla sensorer live** enligt produktspecarna och kan köras
som **live-simulering** mot strömmande, slumpade brädor. Återanvänder repo-roten
(`src/board`, `src/hardware`, `src/laser`) för den simulerade hårdvaran. Tänkt
att köra på bänk-datorn (Jetson Orin Nano Super) och bli det riktiga bänk-GUI:t.

## Kör
```bash
pip install -r prototype/requirements.txt
streamlit run prototype/app.py
```
Öppnas på http://localhost:8501

## Lägen
- **Live-simulering:** riggen "kör" – matningen animeras och nya **slumpade 1 m-brädor**
  strömmar in en efter en (Start / Stopp / Nästa). Varje bräda har små mm-avvikelser
  i mått + **global skevhet** (vridning/bukt/kupa) ovanpå lokala defekter
  (sprickor, kvist, vankant, blånad, röta, hål). Loggar mätstatistik per bräda.
- **Manuell inspektion:** välj bräda, skevhet och driftparametrar; dra matningen.

## Sensorvyer (flikar)
- **Live-kameror:** bänk (2D ovanifrån) · **profilkamera RÖD 650 / GRÖN 520**
  (mono + bandpass — rå laserstripe förskjuten av höjden, med ocklusion/skugga) ·
  **ytkamera FÄRG** (RGB-linjekamera) · **ytkanal NIR** (blånad/röta mörka).
- **Profiler & 3D:** längsprofil (1 m) + **3 punktlaser** (absolut tjocklek) ·
  **tvärsnitt** (topp + sidor, röd/grön oblik) · höjdkarta + defekt-overlay · 3D-yta.
- **Datatakt & fart:** takt ↔ upplösning ↔ bandhastighet (pitch, profiler/s,
  mätpunkter/s, brädor/min, MB/s). Justera **takt** och **profiltakt** och se datan ändras live.
- **Hårdvara:** exakta modul-specar (lasrar, kameror, punktlaser).
- **BOM & systemkoppling:** komplett materiallista med ca-priser, kopplingsschema (allt
  till Jetson, buss · takt · datatakt), monteringsritning (ändvy) och tabell över **alla
  gränssnitt och uppdateringsfrekvenser** (prototyptakt vs buss-tak). Punktlasern visas
  både som absolut tjockleksankare och som tvärsnittssvep över 150 mm.

## Hårdvara (prototyp, per huvud)
- 1× NVIDIA Jetson Orin Nano Super (edge-compute + U-Net).
- 2× Hikrobot MV-CS050-10UM mono (USB3) + 8 mm lins + bandpass (650/520 nm).
- 1× iadiy LM9R650H100L60 (röd 650 nm, 100 mW) + 1× LM9G520H50L60T (grön 520 nm,
  50 mW) linjelaser, oblika. (Grön toppar på 50 mW i databladet.)
- 3× punktlaser-avståndssensor (V/C/H) för absolut tjocklek.
- Ytkamera (färg) + NIR-strobe för defektklassning.
- T-spårsram, encoder, transport för 1 m. Se BOM i chatten / docs.
