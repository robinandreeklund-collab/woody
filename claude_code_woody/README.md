# Woody — Virkesskanner (multisensor 3D-GUI + kapoptimering)

Referensprototyp av ett webb-GUI för en **line-scan virkesskanner i drift**. Visualiserar hela
kedjan: geometri/takt → bräda → skanning → U-Net-segmentering → **kapoptimering** (var brädan ska
sågas för max värde) → kapstation.

> **Detta är en design-/beteendereferens i HTML/CSS/JS + Three.js — inte produktionskod.**
> Uppgiften (se `CLAUDE.md`) är att integrera detta i den riktiga stacken och byta simulerad data
> mot riktig `make_board` + U-Net-inferens. Kapoptimeringen (`js/cutplan.js`) är en **riktig algoritm**
> som kan portas rakt av.

---

## Snabbstart (prototypen)
Ingen byggprocess. Servera mappen statiskt och öppna `Virkesskanner.html`:
```bash
cd claude_code_woody
python3 -m http.server 8000   # → http://localhost:8000/Virkesskanner.html
```
Kräver internet (Three.js r0.157 + IBM Plex via CDN).

---

## Maskinen (fysik & koordinater)
- **X = matningsled (sidled).** Brädor matas i **−X** genom mätramen vid X=0.
- **Z = brädans längd** (5,4 m). En bräda ligger TVÄRS över flera kedjor.
- **Y = upp.** Skala: `BOARD_LEN = 7 wu ≙ 5,4 m` ⇒ **1 wu ≈ 771 mm**.

| Element | Mått | Notering |
|---|---|---|
| Brädlängd | 5,4 m | längs Z |
| Brädbredd | **125 mm default, ställbar 70–150 mm** | längs X (matningsled); 3D via `group.scale.z` |
| Brädtjocklek | 22 mm nom. | höjdkarta ger relief/vankant |
| Kedjesträngar | **5 st, 77 mm breda** vid Z=−3/−1,5/0/1,5/3 wu | kontinuerliga, längs X |
| Medbringare | **runda 50 mm Ø** | en rad/bräda, en per kedjesträng, bakom brädan |
| Medbringaravstånd | default 250 mm, ställbart | = brädornas pitch |
| Mätram (portal) | **gul `#c2a43e`**, X=0, spänner hela längden | skannlinje + alla sensorer |
| Kapstation | stålportal X=−1,35 wu | klinga + 2 sidoknuffar (puttar i ±Z) |

**Viktigt om skanningsriktning:** brädan matas genom ramen i **bredd-led (kortsidan)**. Line-scan-
sensorn är en linje som täcker **hela längden (5,4 m)** på en gång; bilden byggs upp **rad för rad
tvärs bredden** medan brädan glider. Därför framkallas mätresultatremsan **uppifrån och ner**
(= tvärs bredden), inte längs längden.

---

## Layout (en enda vy)
`#app` = flex med två kolumner:

**Vänster (`#left`, flex:1, kolumn):**
1. **`#stage`** (≈40 % höjd) — kompakt **3D-kontextband** (Three.js). Visar maskinen i drift: mätram, kedjor, runda medbringare, brädor som matas, kapstation. HUD: titel uppe vänster, "Mätram aktiv · {takt} brädor/min" nere vänster.
2. **`#readout`** (resten, scrollbar) — **MÄTRESULTAT**, huvudfokus:
   - **Aktuell bräda** (stort kort): utrullad platt, framkallas tvärs bredden med vald kanal + ev. segmentering + sågplan-overlay (kaplinjer + kvalitetsfärg + "{längd} m · {kvalitet} / {kr}"-etiketter), plus en **tjockleksprofil längs hela längden**. Header: bräd-#, status (Skannar %/✓ Klassad), kaplista, kr.
   - **Historik** (4 mini-kort): senast klassade brädor utrullade, med defekter, kvalitet och värde.

**Höger (`#panel`, 372 px, scrollbar, vit):** instrumentpanel — se nedan.

Responsivt < 900 px: panelen läggs under.

### Panelsektioner
1. **Header** — logotyp "◧", titel, status (LIVE/PAUS).
2. **Genomflöde** — rad/s (758) · MB/s (37.2) · brädor/min.
3. **Huvudvy** — 5 kanaler: Färg · Relief · Tracheid · Segmentering · Höjd (styr både 3D-shadern och readout-remsorna).
4. **Laser-höjdprofil** — tvärsnittsgraf + Tjocklek/Vankant (mm).
5. **Sidosensorer** — Undersida + Röntgen (PiP, PÅ/AV) + "{n} inre kvist(ar)".
6. **Defekter** — 6 klasser (chip · namn · antal · area) + mIoU (≈0,987).
7. **Sågoptimering** — kap-stapel + kr/bräda · utbyte % · bitar + 3 nummerfält (kaplängder) + "Sågplan PÅ/AV" + kvalitetslegend.
8. **Reglage** — Triggning (Encoder/Tid-jitter) + varning; sliders Takt / Bräddbredd / Medbringaravstånd; res-ruta (längsupplösning + skärpa); knappar Segmentering, Paus/Spela, Steg.

---

## Sensorkanaler
Sätts av `uChannel` i brädans fragment-shader (`js/scene.js`); samma val driver readout-remsorna.

| # | Kanal | Visar |
|---|---|---|
| 0 | Färg | RGB-trätextur + relief-skuggning |
| 1 | Relief (fotometrisk stereo) | normal/relief ur höjdkarta; roterande LED-ljus; sprickor poppar |
| 2 | Tracheid | fiberriktningsfält färgat efter avvikelse (grön→röd) = hållfasthet |
| 3 | Segmentering | U-Net-overlay (klassfärger) |
| 4 | Höjd | laserprofil som färgkarta (blå→röd) |

PiP (2D): Undersida (via kedjespringor) + Röntgen (inre kvistar).
Shader-extra: segmenterings-overlay, **sågplan-overlay**, glödande skannlinje, **upplösnings-
kvantisering** (`mix(200,22,uCoarse)` rader → hög takt = grov/undersamplad bild).

---

## Kapoptimering (`js/cutplan.js`) — RIKTIG algoritm (porta till backend)
DP som väljer var brädan kapas i tillåtna längder för max värde. Alla bitar säljbara; snitten
placeras för att maximera A/B-utbytet.

- **In:** `features = [{cls, u, fv, area}]`, `u` = position längs längden 0..1.
- **Param:** `L=5,4 m`, `CM=540`; `lengths=[3.0,2.7,2.4] m` (UI-fält).
- `SEV` (klass→svårighet): kvist1=1, blånad3=1, vankant4=2, spricka2=3, röta5=3, hål6=3.
- `FOOT` (klass→cm utbredning): {1:9,2:32,3:38,4:75,5:42,6:7}.
- `GRADE=[A,B,C,C]` (index=värsta svårighet); pris kr/m **A=58, B=40, C=24**; färg A`#4aa86a` B`#d6a23e` C`#cf6b46`.
- **DP:** `best[i]` = max värde första *i* cm; övergång trimma 1 cm (spill) eller lägg bit `lc` som slutar i *i*: `best[i]=max(best[i], best[i-lc]+PRICE[grade]·lc/100)`. Backtracka → bitar `{aU,bU,lenM,grade,value,color}`. Returnerar `{pieces,totalValue,yield,trimM,L,lengths}`.

---

## Härledda mått & takt↔upplösning (exakta formler — `js/main.js`)
`SENSOR_RATE=758` Hz, `PX_LEN=16364`, `WU_MM=5400/7`.
```
feedWorld (wu/s) = pitch · takt/60
feedMps   (m/s)  = feedWorld · WU_MM/1000
alongRes  (mm/px)= feedMps · 1000 / SENSOR_RATE
coarse    (0..1) = clamp((alongRes − 0.15)/0.7)        // → shader-kvantisering
dataRate  (MB/s) = SENSOR_RATE · PX_LEN · 3 / 1e6      // ≈ 37.2
```
Sänk takten → långsammare band → finare längsupplösning → skarpare bild. (Hela poängen med "takta ner".)

---

## State (porta till en store)
`state` i `js/main.js`:
```
channel 0..4 · overlay 0/1 · distort 0/1 · trigger 0/1
takt (brädor/min) · pitch (wu) · widthWu (wu)
lengths [m,m,m] · cutOverlay 0/1
time · playing · showUnder · showXray · dispScale
```
Kö: `boards=[{data,x}]` (N=11). Aktiv bräda = min |x| → driver panel + readout. `history` = 4 senast
klassade. `developFrac(x)` = utvecklad andel 0..1.

---

## Design-tokens

### CSS (`style.css`)
`--bg #f1f0ea` · `--panel #fff` · `--panel-2 #fbfaf7` · `--ink #25282c` / `--ink-2 #6a6e74` /
`--ink-3 #9a9ea4` · `--line #e4e2db` / `--line-2 #eceae3` · **`--laser #e8542c`** (accent) ·
`--blue #3f86c4` · `--green #2f9e6e` · radius 7–10px · **IBM Plex Sans** (UI) + **IBM Plex Mono** (siffror).

### 3D-palett (`js/scene.js` `COL`)
bg `0xf1f0ea` · floor `0xe7e5df` · grid `0xcfccc4` · metal `0xc3c6ca` · metalDark `0x33373d` ·
housing `0x2b3036` · **frame `0xc2a43e`** · medbringare `0x2c2f34` · laser `0xe8542c` ·
tracheid `0x33c98c` · blue `0x3f86c4` · led `0xfff4e0` · blank bräda `0xd9cdb2`.

### Defektklasser (`js/config.js`)
0 Frisk (ingen overlay) · 1 Kvist `#d4953f` · 2 Spricka `#d2533f` · 3 Blånad `#5577bd` ·
4 Vankant `#a072c4` · 5 Röta `#6fa15c` · 6 Hål `#cf6f9e`.

### Kvalitet (kap)
A `#4aa86a` (58 kr/m) · B `#d6a23e` (40) · C `#cf6b46` (24) · Spill `#8a8f96`.

---

## Filer
| Fil | Innehåll | Status |
|---|---|---|
| `Virkesskanner.html` | Skal: HUD, 3D-band, readout-mount, panel-mount; laddar moduler i ordning | referens |
| `style.css` | Hela UI/designsystemet | referens |
| `js/config.js` | `LineConfig`: defektklasser, basgeometri, härledda mått | referens |
| `js/textures.js` | **Procedurell bräda** (färg/facit/höjd/tracheid/undersida/röntgen) + statistik | **ERSÄTT med riktig data** |
| `js/cutplan.js` | **Kapoptimering (DP)** | **PORTA till backend** |
| `js/scene.js` | Three.js: scen, mätram, kedjor, medbringare, kapstation, brädans flerkanals-shader | referens |
| `js/panel.js` | Instrumentpanel (mätare, kanaler, profil, PiP, sågoptimering, reglage) | referens |
| `js/readout.js` | **Mätresultat-flöde**: aktuell bräda utrullad (tvärs bredden) + historik | referens |
| `js/main.js` | Simulering: kö, recykling, aktiv bräda, takt↔upplösning, kopplar scen↔panel↔readout | referens |

**Laddningsordning:** `three.min.js` → `config` → `textures` → `cutplan` → `scene` → `panel` → `readout` → `main`.

Se `CLAUDE.md` för konkreta integrationssteg och `ARCHITECTURE.md` för föreslagen stack.
