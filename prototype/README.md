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
  gränssnitt och uppdateringsfrekvenser** (prototyptakt vs buss-tak). De 3 punktlasrarna
  sitter **längs 1 m** (V/C/H) och ger absoluta Z-ankare som låser längsprofilen; tvärsnittet
  tvärs 150 mm kommer från de oblika linjelasrarna.

## Hårdvara (prototyp, per huvud) — fasad uppbyggnad
Se fliken **BOM & systemkoppling** för komplett lista med priser och faser.

- **Fas 1 (vänster, minimal — 500 mm-brädor):** Jetson Orin Nano Super · 1× MV-CS050-10UM
  mono (USB3) + C-mount 8 mm + bandpass 650 nm · 1× iadiy LM9R650H100L60 (röd 650 nm). Enkel
  **alu-ram**, brädan **puttas för hand** för att verifiera trianguleringen (kamera free-run,
  **ingen encoder**). 500 mm ger kortare laserlinje + finare upplösning (~0,20 mm/px).
- **Fas 2 (höger + automatiserad matning):** +1× MV-CS050-10UM + bandpass 520 nm +
  iadiy LM9G520H50L60T (grön) → full dubbel-oblik · **2× mini-transportör (24 V, 50 mm/s)** en
  vänster/en höger med öppet mätfält + **PWM-regulator** + **inkrementell encoder med mäthjul**
  (RS422, ~0,1 mm/puls) → repeterbar, positionslåst matning (~20 brädor/min).
- **Fas 3 (full svit):** MindVision MV-XGLC83BM-T4-90 (line-scan, NBASE-T) + M72-optik ·
  850 nm NIR + RGB strobad belysning · 3× Panasonic HG-C1100 punktlaser (längs 1 m,
  ankrar längsprofilen) + MCP3008 ADC.

CS050 har C-mount och **kräver objektiv** (ingår, 1 per kamera). MindVision faller tillbaka
till 1 GbE (NBASE-T) → ingen switch behövs.
