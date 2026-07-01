# Laser-tracheideffekt i virkesriggen — analys & nyttjande

Hur fungerar **tracheideffekten** (laser-spridning för fibervinkel) och hur skulle
vi nyttja den i vår rigg? Analys/forskning — ingen kodändring.

> **Sammanfattning:** En fokuserad laserpunkt på barrträ ger en **elliptisk
> spridningsfläck** vars **långaxel pekar längs fiberriktningen** — för att veden
> "rör-leder" ljuset längs tracheiderna (de långa cellerna), strax under ytan. Genom
> att mäta ellipsens **vinkel** över hela brädan får vi en **fibervinkelkarta**, och
> där fibern **virvlar** sitter **kvistar** (även de som börjar under ytan). Fibervinkel
> är en av de **starkaste hållfasthetsprediktorerna** som finns — det här är guld för
> sortering. Det är beröringsfritt, snabbt (kamerabaserat, samma matning), billigt
> (ingen strålning, ingen CT), och **återanvänder vår laser+kamera-arkitektur**.
> Bäst med **röd/NIR**-laser (grön 520 är svag för effekten) och en **uppifrån-kamera**
> som ser den diffusa spridningshalon (inte bara den ljusa kärnan).

---

## 1. Fysiken
Barrvedens **tracheider** är långa, rörformiga celler (~2–4 mm långa, ~20–40 µm
diameter) orienterade längs fibern. När en laserpunkt träffar ytan kopplas ljus in
och **leds subytligt längs tracheiderna** (ljusledning/"light piping") innan det
sprids ut igen. Resultatet: en **elliptisk fläck** där:
- **långaxeln ∥ den lokala fiberriktningen** (i ytplanet) → **fibervinkel**,
- **excentricitet/utbredning** beror på dykvinkel (grain dive), våglängd och vedens
  egenskaper.
Eftersom ljuset dyker en bit ner ser effekten **även fiberstörningar strax under
ytan** — t.ex. en kvist som ännu inte brutit igenom.

## 2. Varför det är värdefullt
- **Fibervinkel = stark hållfasthetsprediktor.** Sned-/virvlande fiber sänker
  hållfastheten dramatiskt; det är detta (snarare än kvisten i sig) som styr
  brottet. Maskinell hållfasthetssortering kombinerar ofta fibervinkel (tracheid)
  med densitet (röntgen) för bästa MOE/MOR-prediktion.
- **Robust kvistdetektion:** runt en kvist **virvlar fibern** → ett tydligt
  vinkelmönster i kartan, oberoende av ytans färg (bättre än ren färg-kvist-
  detektion, och ser begynnande/under-ytan-kvist).
- **Beröringsfritt, snabbt, billigt** och utan strålning — passar en matad bräda.

## 3. Hur det mäts
- **Punkter > linje:** effekten mäts renast med en **fokuserad punkt** (eller en
  **rad av punkter**) där man kan passa en ellips kring varje fläck. En kontinuerlig
  laser**linje** ger överlappande spridning — man kan ändå läsa linjens **asymmetriska
  bloom** (tvärspridning vs fibervinkel), men dot-array ger renare data.
- **Ellipsanalys:** tröskla/segmentera fläcken, beräkna **andra moment (PCA)** →
  huvudaxelns vinkel = fibervinkel; axelförhållandet = ett mått på dyk/kvalitet.
- **Våglängd:** effekten är **starkare vid längre våglängd** (djupare ljusledning).
  **Röd 650 nm = användbar**, **NIR 780–1060 nm = bäst**. **Grön 520 nm är svag**
  (mer ytspridning, mindre piping) → vår gröna laser lämpar sig dåligt för detta.
- **Kamera:** behöver avbilda den **diffusa halon** (inte bara den mättade kärnan),
  helst **uppifrån (nära normal)** för att se ellipsformen rätt, med tillräcklig
  **dynamik** (HDR/exponering) så halon syns utan att kärnan dränker den.

## 4. Nyttjande i VÅR setup
Vår rigg har redan lasrar (röd 650 / grön 520) + profilkameror (oblika, bandpass)
+ ytkamera (uppifrån, färg). Tracheid passar in så här:

**Återanvändning / minsta tillägg (PoC):**
- Använd **röda 650-lasern** och avbilda spridningen. Profilkamerorna är dock
  **oblika + bandpass-snäva** (optimerade för att se stripens *centrum* för höjd) →
  mindre lämpliga för halo-analys. Bättre: låt en **uppifrån-kamera** (ytkameran,
  eller en dedikerad mono-kamera) se den röda spridningen i en separat exponering.
- Snabbaste demo: analysera **röda stripens tvärbloom/asymmetri** längs linjen →
  grov fibervinkel. Begränsat men visar principen med befintlig hårdvara.

**Riktig tracheid-station (rekommenderad uppbyggnad):**
- En **dot-laser-bar** (rad av fokuserade punkter, **röd eller NIR**) projicerad
  tvärs längden (X), avbildad av en **uppifrån-kamera** (NIR-känslig om NIR-laser).
- Detta knyter an till **NIR-kanalen** som redan fanns som tillval i BOM:en — en
  **NIR dot-laser + NIR-mono-kamera** blir då både röta/blånad- *och* tracheid-station.
- Medan brädan **matas (cross-feed)** sveper punktraden ytan → bygg en
  **fibervinkelkarta Φ(x,y)** över hela brädan (precis som ytbilden byggs rad-för-rad).
- Eget steg längs matningen, mekaniskt/optiskt frikopplat från profil-trianguleringen
  (annan exponering/våglängd), gärna nära men separerat från lasersnittet.

## 5. Vad vi får ut — och hur det kombineras
- **Fibervinkelkarta Φ(x,y)** (lokala grain-angle, grader).
- **Kvistkarta** ur virvelmönster (gradient/curl i Φ) + ev. dyk-index.
- **Styvhetsindex** (fibervinkel-baserat), kombineras gärna med densitet senare.
- **Sensorfusion → gradering:** 3D-geometri (skevhet) + ytfärg (blånad/röta/spricka)
  + LR400 (absolut tjocklek) + **tracheid (fibervinkel/kvist/styvhet)** → ett
  betydligt starkare graderingsbeslut än med enbart optik. I appen skulle detta bli
  en ny "fibervinkel"-vy + en input till graderingsregelverket.

## 6. Begränsningar
- **Barrträ** (tracheider) fungerar bra; **lövträ** sämre (annan cellstruktur).
- **Ytråhet/sågdamm/fukt** sprider och sänker kontrasten → ren, torr yta bäst.
- **Dynamik/geometri:** kräver att kameran ser halon (HDR) och en någorlunda
  normal vy; brädans bukt ändrar avstånd/vinkel → kalibrera.
- **Kalibrering per träslag/yta** för absolut vinkel; relativ virvel runt kvist är
  robustare.
- Grön 520 olämplig; röd ok; NIR bäst (extra hårdvara).

## 7. Rekommendation / faser
1. **PoC med befintlig röd laser:** avbilda röd-spridningen uppifrån (ytkamera eller
   en enkel mono-kamera) och mät stripens tvär-bloom/asymmetri → visa att fibervinkel
   kan extraheras. Lågt risk, ingen ny laser.
2. **Dedikerad station:** **röd/NIR dot-laser-bar + uppifrån-kamera** → riktig
   fibervinkelkarta Φ(x,y) vid matning. Slå ihop med NIR-kanalen (röta/blånad).
3. **Fusion i graderingen:** lägg fibervinkel/kvist/styvhet som indata till
   regelverket; ny GUI-vy (vinkelkarta + virvel-overlay).
4. **Kombinera med densitet** (röntgen) om maskinell hållfasthetssortering ska nå
   högsta prediktion — tracheid (fibervinkel) + densitet är industristandard-paret.

## 8. Kan vi BÖRJA med linjelasern (röd 650)?

**Ja — men det avgörande är kameravyn/exponeringen, inte lasern.** Linjelasern
fungerar som start, med dessa caveats:

**Hur grain-angle läses ur en LINJE (inte punkter):**
Längs hela linjen sprids ljuset elliptiskt. Det vi mäter är den **tvärspridning
(bloom vinkelrätt mot linjen, i matningsled Y)** vid varje X:
- Fiber **∥ linjen (X)** → ljus leds längs X → linjen förblir **smal i Y**.
- Fiber **⟂ linjen (längs Y)** → ljus leds i Y → linjen **blöder ut i Y** (breddas).
- Fiber **i vinkel** → bloomen blir **asymmetrisk/lutad**.
→ ur tvärprofilens **bredd + asymmetri (skevhet)** per X får man fibervinkel-
komponenten. Medan brädan matas byggs en (grov) **fibervinkelkarta**.

**Vad som faktiskt krävs (och varför lasern är den enkla biten):**
- **Röd 650 ✓** (grön 520 olämplig). Bandpassfiltret @650 är till och med en fördel
  — kameran ser bara laserljuset, inte omgivningen.
- **Kameran är flaskhalsen:** tracheid-signalen är den **svaga diffusa halon** runt
  den ljusa kärnan. Våra **profilkameror är oblika + ROI-snäva + kort exponering**
  för att se stripens *centrum* (höjd) → de ser inte halon bra, och den oblika vyn
  förkortar tvär-bloomen. Man vill ha en **uppifrån-kamera** (nära normal) med
  **högre dynamik/HDR** så halon syns utan att kärnan mättar.
  - Billigast: en **enkel mono-kamera med 650-bandpass rakt ovanför** linjeregionen,
    eller använd **ytkameran i en röd-laser-exponering** (LED av, laser på) som en
    egen bildruta.
- **Kärnan mättar:** den starka trianguleringskärnan kan dränka halon → använd
  **separat exponering/HDR** eller en egen kamera så höjd och tracheid inte slåss.

**Begränsningar med LINJE jämfört med punkter:**
- Lägre **vinkelnoggrannhet** (linjen tappar den rena "längs-fibern"-ledningen; man
  får främst tvär-bloomen → grain-angle med tecken-tvetydighet nära ±parallellt).
- Överlappande spridning längs linjen → lägre kontrast.
- **Kvist-virveln syns ändå** även med grov absolut vinkel → kvistdetektion är en
  stor vinst direkt, även om exakt vinkel är ungefärlig.

**Slutsats:** börja gärna med **röda linjelasern + en uppifrån-kamera (eller
ytkameran i röd-exponering) med HDR** → grov fibervinkel + kvist-virvel som PoC,
utan ny laser. Uppgradera sedan till **röd/NIR dot-array** för produktions-noggrann
fibervinkel.

## 9. Industriella system & referenser
- Kommersiella skannrar som använder laser/tracheid för fibervinkel + kvist:
  **WoodEye**, **Microtec (Goldeneye/Finscan)**, **Limab** m.fl.
- Maskinell hållfasthetssortering: fibervinkel (tracheid) + densitet (röntgen) → MOE.
- Sökord: "tracheid effect grain angle scanning", "laser light diffusion wood fibre
  orientation", "dot laser grain angle lumber strength grading", "knot detection
  grain deviation tracheid".
