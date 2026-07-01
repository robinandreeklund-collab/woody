# Linjekamera-belysning — design & idrifttagning

Belysningen för **ytkameran** (HT-GELM44C-T2, färg, 4096 px, encoder-triggad linjekamera).
Den läser brädans **yta och färg** för utseendegradering (A/B/C/D: splint/kärna, blånad,
ton). Topografi/defektform kommer från laser-trianguleringen + höjdkartan — **inte** härifrån.
Därför är målet med belysningen **platt, jämn, färgtrogen** ljussättning på den avbildade
linjen, inte rakande relief-ljus.

> Detta dokument rör **ny belysningsdesign**, inte den låsta geometrin i `prototype-*.svg`.
> Hårdvaran (linjekamera, profilkameror, laser, encoder, LR400, fotocell) är oförändrad.

---

## 1. Lampor (val)

| Post | Värde |
|---|---|
| Modell | **HT-SL60030-W** (Huateng), vit bar light |
| Färgtemperatur | **6500 K** (vit) |
| Emitterande yta | 600 × 29 mm |
| Ytterhölje | 616 × 34 mm |
| Effekt (vit) | 35,5 W / list |
| Matning | 24 V DC (bekräfta) |
| Kontakt | SMR-03V-B (3-pol — sannolikt +/–/dim) |
| Antal | **2 st**, en på var sida, symmetriskt intiltade mot kameralinjen |

Beställ uttryckligen **-W** (vit). Serien finns även i R/B/G/IR850/IR940 — de är **inte** för
färgytan.

### Obekräftat från leverantör (måste in innan beställning)
- [ ] **CRI ≥ 90** (helst ≥ 95) — *den enda posten som kan stoppa valet.* 6500 K säger
  färgtemperatur, inte återgivningskvalitet. Krävs för ton + blånad. Be om samma LED-bin/batch
  för båda listorna.
- [ ] **Spridningsvinkel** — behövs för att räkna ljusbandets bredd på ytan.
- [ ] **Dimningsmetod** — analog eller PWM? Är det PWM: frekvensen (måste ligga **långt** över
  linjetakten, annars band i bilden).
- [ ] **Matningsspänning** — bekräfta 24 V DC.
- [ ] **Ljusflöde/irradians** för 600 mm vid arbetsavståndet (extra viktigt p.g.a.
  polarisationsförlust, se §4).

---

## 2. Geometri

- **Linjekameran avbildar en linje 40 mm offset** från laserplanet. Håller färgavläsningen
  skild från laserlinjerna (650/520 nm) och håller laserglöden ur färgbilden.
- **Lampor intiltade ~10°**, konvergens **aimad på 32 mm höjd** (mitt i tjocklekspannet
  15–50 mm). Aim på mitten gör bandvandringen symmetrisk.
- **Diffusor** på lamporna (mjukar glans + breddar bandet så ytan hålls belyst genom hela
  15–50 mm).

### 2.1 Vinkelfönster — undvik profilkamerornas FOV
Profilkamerorna (triangulering, 350 mm WD, ~10° konvergens, 121,55 mm isär, 15° tilt) upptar
ett vinkelband sett från konvergenspunkten. Lamporna **får inte** hamna i den konen.

```
  Tillåtet:   ≤ 10°   (lågt fönster — VALT)
  Förbjudet:  ~15–20° (rakt i profilkamerornas FOV)
  Tillåtet:   ≥ 25°   (högt fönster — nödutgång)
```

**Valt: det låga fönstret (~10°).** Motivering — linjekamerans jobb är *färg*, och färg vill ha
platt diffust ljus:

| | **≤10° (valt)** | ≥25° (nödutgång) |
|---|---|---|
| Bandvandring 15–50 mm | **±3,1 mm** (6,2 mm span) | ±8,2 mm (16,3 mm span) |
| Ljusstyrka | högre (kort kast, cos≈0,99) | lägre (längre kast + cosinus) |
| Färgåtergivning | platt, trogen | rakande → korn-skuggor kan misstolkas som ton/defekt |
| Rå yta | perfekt | ok |
| Hyvlat/blankt | risk för glansstrimma → löses med polarisation (§4) | god glansrejektion |

25°-fönstret löser glans men skuggar ådringen så den ser ut som färgvariation → byter ett
problem mot ett annat. Därför **10° + polarisation**, inte 25°.

### 2.2 Bandvandring vs tilt (referens)
Sidledsvandring av ljusbandets mitt = `Δh · tan(vinkel)`, Δh = 35 mm (15→50), aim på mitten:

| Tilt | Bandvandring (span) | Avvikelse från mitten |
|---|---|---|
| **10°** | **6,2 mm** | **±3,1 mm** |
| 15° | 9,4 mm | ±4,7 mm |
| 20° | 12,5 mm | ±6,4 mm |
| 25° | 16,3 mm | ±8,2 mm |
| 30° | 20,2 mm | ±10,1 mm |

---

## 3. Två ytor: hyvlat OCH råsågat
Riggen ska klara **båda**. Råsågat/matt är förlåtande (ingen glans). Hyvlat/halvblankt är
det svåra fallet: linjekameran tittar ~rakt ner, så vid flack vinkel reflekteras glanslobens
**rakt tillbaka in i linsen** → utbränd strimma längs linjen. Designen löser det utan att
offra den flacka (färgtrogna) vinkeln — se polarisation nedan.

---

## 4. Korspolarisation (löser glans på hyvlat utan att röra vinkeln)
Standardtricket i maskinsyn för "platt ljus men blank yta":

- **Linjär polarisatorfilm på båda lamporna** + en **korsad analysator (90°) på linjekamerans
  lins.**
- Spegelreflexen (ytreflex) behåller polarisationen → blockeras av den korsade analysatorn.
  Den diffusa, färgbärande reflektionen kommer igenom.
- **Resultat:** glansen dödas oavsett vinkel → behåll 10° med minimal bandvandring + trogen färg.

Att känna till:
- **Ljusförlust ~50–65 %** → kräver ljusbudget kvar (ännu ett skäl att få lumen-siffran).
  Två 35,5 W dimbara listor bör ha marginal, men verifiera.
- Använd **färgneutrala (visuella) polarisatorer** så bilden inte tonas (vitbalansera ändå).
- **Linjär** polarisator, inte cirkulär, på båda sidor.

Faller polarisation bort (kostnad/ljus): kör 10° + kraftig diffusor och testa; gå till 25°
bara om glansen kvarstår, med vetskap om färg-/bandvandringspriset.

---

## 5. LR400-raden (uppströms, fast position)
3× LR400 monterade på **fast position uppströms**, före laser- och färglinjen
(~90 mm höjd, ~169 mm sidled enligt ritning). Tre roller samtidigt, utan krock:

1. **Absolut tjocklek** — ankrar trianguleringen (`fusion.anchor`). LR400:s egentliga jobb.
2. **Bräd-närvaro / framkant** — grind-signal. Eftersom den sitter uppströms fördröjs grinden
   med avståndet uttryckt i **encoder-counts**.
3. **Tjockleksprofil längs brädan** — encodern co-registrerar position, så LR400-läsningen
   per längdposition kan läggas rad-för-rad mot höjdkartan.

> **Kontroll:** bekräfta att LR400:s mätområde vid 90 mm montering täcker bandet (0 mm) upp
> till 50 mm bräda.

> **Notis (kant):** för den *skarpa* fram-/bakkanten är anhåll-fotocellen (GPIO pin 7, snabb
> hårdvaruflank) skarpare än LR400 (pollad över RS-485 Modbus). Bästa upplägget är hybrid:
> fotocell ger grind-timingen, LR400 ger tjocklek + lateral utbredning.

---

## 6. Trigger & flöde (varför encodern, inte beräknad tid)
Linjekameran behöver **två skilda triggers**:

- **Rad-trigger (per rad):** encoder B (hårdvara, `E6B2-CWZ1X` → 26C32 → kamerans Line0).
  En puls per fast vägsteg → en rad → konstant mm/rad, immun mot hastighetsvariation. Detta
  **måste** vara encodern — inte en timer som räknar `hastighet × tid`, eftersom sluten slinga
  håller *medel*hastighet men inte momentan position (PID-ripple, last, accel/decel ackumuleras
  till bilddistorsion). Du har redan den faktiska förflyttningen i encodern — använd den direkt.
- **Grind (bräda in/ut):** närvarogivare (fotocell + LR400) öppnar/stänger "detta är en bräda".

Detta klarar **löpande flöde med godtyckligt mellanrum** mellan brädor: encodern klockar
rader hela tiden, grinden segmenterar strömmen per bräda. Mellanrummet är bara bandsträcka med
stängd grind. Beräknad timing skulle däremot havera vid manuell, varierande laddning.

**Gränser:** minsta gap (höjden måste hinna nollas mellan brädor), en bräda i bredd (annars
krävs lateral segmentering per LR400-kanal/kolumn), inom FOV i sidled, hastighet inom keep-up
(`tools/profile_acquisition.py`).

> **Mjukvara:** löpande flöde är **implementerat** och valbart i GUI:t (driftläge
> *Pass* | *Löpande*). `processing/segmentation.py` (`BoardGate`) är grind-/segmenterings­
> tillståndsmaskinen (TOM → ARMERAD → BRÄDA, klockad av encoder-counts, gated av
> fotocell+LR400); `acquisition.scan_stream` kör den encoder-klockat och yieldar en
> graderad bräda per bräda. Samma väg kör mot sim (virtuellt band) och real (RoboClaw-
> encoder + fotocell via `feed_position_mm`/`board_present` i `real_backends.py`).
> Avgränsning kvar: grinden är 1D (en bräda i bredd) — två brädor sida vid sida kräver
> lateral segmentering per LR400-kanal/kolumn.

---

## 7. Kalibrering (knyt in i GUI:t)
- **Vitbalans** mot vit referens under de skarpa lamporna (efter att polarisatorerna sitter).
- **Yt-profil** (rå / hyvlad): sätt ljusnivå (dimmer) + exponering + vitbalans per yttyp —
  råsågat är mörkt/matt, hyvlat ljust/blankt.
- Verifiera ljusbandets täckning + glans på **provbrädor vid både 15 och 50 mm tjocklek**.

---

## 8. Idrifttagning — checklista
- [ ] CRI ≥ 90 bekräftat skriftligt från leverantör
- [ ] Spridningsvinkel + lumen för 600 mm vid arbetsavstånd inhämtat
- [ ] Dimning analog, eller PWM-frekvens ≫ linjetakt
- [ ] 2× HT-SL60030-W monterade ~10°, konvergens aimad på 32 mm
- [ ] Diffusor monterad
- [ ] Korspolarisation: film på lampor + korsad analysator på lins (90°)
- [ ] Glanstest på **hyvlad** provbräda — ingen strimma vid 15 och 50 mm
- [ ] Bandtäckning verifierad vid 15 och 50 mm
- [ ] LR400-rad: mätområde täcker 0–50 mm från 90 mm montering
- [ ] Encoder-radtrigger + fotocell-grind verifierade (löpande flöde om aktuellt)
- [ ] Vitbalans + yt-profiler (rå/hyvlad) kalibrerade i GUI:t

---

## Referenser
- `docs/jetson-prep-plan.md` — huvudplan, enhetskarta, faser
- `docs/alignment-calibration.md`, `docs/zero-reference.md` — geometri/nollkalibrering
- `docs/grading-nordic.md` — A/B/C/D-gradering
- `prototype-wiring.svg`, `prototype-pinout.svg` — låst hårdvara (sanningskälla)
