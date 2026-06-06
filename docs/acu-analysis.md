# Luftburen ultraljud (ACU) i virkesriggen — analys & forskning

Hur skulle **Air-Coupled Ultrasound (ACU)** fungera i vår dubbel-oblika
laserskanner-rigg? Detta är en analys (ingen kodändring). Fokus: fysik, vad det
tillför, hur det skulle integreras mekaniskt, begränsningar, alternativ och en
rekommendation för prototypen.

> **Sammanfattning:** ACU är den enda av våra kandidater som ser **inuti** brädan
> utan kontakt — den kompletterar optiken (som bara ser ytan + geometri).
> Den kan i princip detektera **röta, inre kvist, håligheter, sprickor och
> delamineringar/limfogar** samt ge ett **densitets-/styvhetsindex**. Men den är
> tekniskt krävande: luft↔trä-gränssnittet ger enorm dämpning (~−100 till −130 dB
> systemdynamik krävs), den är känslig för ytråhet, luftdrag och temperatur, och
> **genomgångsmätning kräver åtkomst till BÅDA sidor** — vilket krockar med att
> brädan vilar på bandet. Rimligt som ett **separat, valfritt inre-inspektions-
> steg** (sändare över / mottagare i den öppna mätzonen under), men inte trivialt.
> För ren **styvhetsgradering** är akustisk resonans eller laser-tracheideffekt
> billigare; för **inre defektkartläggning** är röntgen/CT den industriella
> referensen. ACU sitter mitt emellan: beröringsfritt, billigare än CT, men lägre
> upplösning och SNR.

---

## 1. Vad ACU är och varför för virke
Ultraljud utan vätskekopplingsmedel — givarna sänder ljud genom **luft** in i
materialet. Mäter **gångtid (hastighet → styvhet/densitet)** och **dämpning
(amplitud → defekter/röta/håligheter)**. Optiken i vår rigg ser bara ytan; ACU
ser **strukturen under ytan**, vilket är just det som saknas för hållfasthets-
gradering (inre kvist, röta, sprickor).

## 2. Fysik & kärnutmaning
- **Impedansmissmatch:** akustisk impedans luft ≈ 400 Rayl, trä ≈ 1–3·10⁶ Rayl.
  Transmissionen vid ETT luft–trä-gränssnitt ≈ −35 till −40 dB (intensitet). Två
  gränssnitt (luft–trä–luft) ⇒ **−70 till −80 dB bara på gränssnitten**, plus
  dämpning inne i träet och givar↔luft-förluster → systemet behöver typiskt
  **−100 till −130 dB dynamik**. Det kräver högeffekt-sändare + känslig,
  lågbrus-mottagare + signalmedelvärdesbildning.
- **Hastighet:** luft ~343 m/s; trä längs fiber ~3500–5500 m/s, **tvärs fiber
  ~1000–2000 m/s**. Tvärs tjockleken (det vi mäter på en 20 mm bräda) är det
  tvärfiber → låg hastighet, hög dämpning.
- **Dämpning i trä** är hög och **anisotrop** (mycket högre tvärs fiber), ökar
  med frekvens och **fukthalt**. Därav låga frekvenser.
- **Frekvensval:** 50–250 kHz för trä (penetration vs upplösning). ~120–200 kHz
  vanligt. Våglängd i luft @150 kHz ≈ 2,3 mm; i trä tvärs fiber ≈ 10 mm →
  **lateral upplösning några mm–cm**, inte sub-mm som optiken.

## 3. Mätkonfigurationer
1. **Genomgång (through-transmission):** sändare ena sidan, mottagare andra.
   Standard, bäst SNR. **Kräver åtkomst till båda sidor.**
2. **Enkelsidig pitch-catch/reflektion:** givare på samma sida. Slipper
   undersidan men ekona från trä via luft är extremt svaga → svårt/opraktiskt
   för massivt virke.
3. **Guidade vågor (Lamb/plattvågor):** sänd in i kanten/ytan, mät utbredning —
   kan ge styvhet/defekter men komplext för sågat virke med varierande tvärsnitt.

## 4. Integration i VÅR rigg
- **Undersidan/bandet:** genomgång (alt. 1) kräver mottagare **under** brädan.
  Vår cross-feed har **transportband vid längd-ändarna** och en **öppen mätzon**
  i mitten → man **kan** placera mottagaren i den öppna zonen under brädan, och
  sändaren ovanför. Detta löser "undersidan saknar sensor" specifikt för ACU.
- **Beröringsfritt:** luftgap några mm–cm → perfekt för en bräda i rörelse (ingen
  kontakt, inget kopplingsmedel, inget slitage).
- **Placering:** eget **ACU-steg** längs matningen (likt LR400 uppströms), eller
  i linje med lasersnittet. Bör vara **mekaniskt frikopplat** från optiken
  (vibration/akustik stör inte kamerorna; lasrarna stör inte ACU).
- **Täckning vs takt:** en fast TX/RX-par mäter en **linje längs matningen** vid
  sin X-position medan brädan passerar. För att täcka hela 500 mm-längden behövs
  en **array av par längs X** (t.ex. 16–50 kanaler) → en **C-scan** byggs upp
  medan brädan matas (precis som radkameran bygger ytbilden). Många kanaler =
  kostnad/komplexitet. Alternativt några få par vid kritiska positioner.
- **Takt:** ACU kräver ofta **medelvärdesbildning** (lågt SNR) → effektiv
  mättakt per kanal kanske 100-tals–1000-tals Hz. Vid 50 mm/s matning ger det
  fin upplösning längs matningen; lateralt (längs X) sätts av array-tätheten.
- **Standoff/fokus:** fokuserade givare (kupade/linsade) ~20–50 mm fokus ger bäst
  lateral upplösning; planar ger robusthet mot höjdvariation (vår bräda buktar).

## 5. Vad ACU TILLFÖR (utöver befintliga sensorer)
| Egenskap | Optik (vår rigg) | ACU |
|---|---|---|
| Yt-geometri / skevhet | ✓ (sub-mm) | – |
| Yt-defekter (kvist, vankant, spricka, blånad) | ✓ | (indirekt) |
| **Inre röta / nedbrytning** | ✗ | ✓ (hastighet↓, dämpning↑) |
| **Inre kvist / håligheter / sprickor** | ✗ | ✓ (några mm–cm) |
| **Densitet / styvhet (MOE-index)** | ✗ | ✓ (gångtid) |
| **Limfog/delaminering (limträ/plywood)** | ✗ | ✓ (stark indikator) |
| Lateral upplösning | sub-mm | mm–cm |
| Takt | hög | måttlig |

ACU ger alltså **inre kvalitet + ett styvhetsindex** — kärnvärden för
hållfasthetssortering som optiken inte kan ge.

## 6. Hårdvara (research)
- **Givare:** piezokomposit 1-3, **CMUT**, eller **ferroelektret/EMFi**-film med
  matchningslager. Leverantörer/system historiskt: The Ultran Group, NCA/SecondWave,
  Sonotec, QMI, Airmar/airborne-piezo, samt forskningssystem.
- **Frekvens:** 100–250 kHz för sågat virke (lägre för tjockare/fuktigare).
- **Elektronik:** högeffekt-**pulser** (100–800 V tonburst), lågbrus-**förförstärkare**,
  bandpass + medelvärde, gating för gångtid/amplitud.
- **Forskningsläge:** ACU på trä/träbaserade skivor är väl studerat (delaminering i
  plywood/limträ, röta/nedbrytning, densitetskartor). Mogen princip, men
  industriell drift på snabb såglinje är ovanligare än optik/röntgen.

## 7. Begränsningar & risker
- **SNR/dynamik:** −100…−130 dB → kräver dyr, känslig kedja + skärmning.
- **Ytråhet & bukt:** sågad/skrovlig yta sprider ljudet; brädans bukt ändrar
  luftgap/infallsvinkel → amplitudvariation som måste kalibreras bort.
- **Fukt & densitet:** varierar kraftigt i virke → påverkar hastighet/dämpning;
  måste kompenseras (annars falska "defekter"). Fuktgradient = störkälla.
- **Luftdrag & temperatur:** ljudhastigheten i luft varierar med temp/flöde →
  driftande gångtid; kräver referens/kompensation (jfr nollplans-resonemanget).
- **Takt vs täckning:** full C-scan kräver array (många kanaler) → kostnad.
- **Upplösning:** mm–cm, inte sub-mm; lokaliserar men finbestämmer inte små defekter.

## 8. Alternativ (jämförelse för inre/styvhet)
- **Röntgen / CT:** industriell referens för inre kvist/röta/densitet (t.ex.
  CT-loggскannrar). Bäst upplösning/densitet, men dyrt + **strålsäkerhet**.
- **Mikrovåg / THz:** fukt/densitet/fiberriktning, beröringsfritt; begränsad
  defektupplösning.
- **NIR / hyperspektral:** yt-/nära-ytkemi (röta, fukt, extraktivämnen) — kompletterar.
- **Akustisk resonans (longitudinell vibration, MTG/Viscan-typ):** billig, robust
  **styvhets-/MOE-gradering** av hela brädan — men ger inte defekt-LOKALISERING.
- **Laser-tracheideffekt:** vår laser kan (med rätt analys) mäta **fibervinkel**
  ur stripens spridning/elongation → stark hållfasthetsindikator, **återanvänder
  befintlig hårdvara**.

## 9. Rekommendation för prototypen
1. **Inte i grundprototypen.** Optik + LR400 ger geometri, yt-defekter och absolut
   tjocklek — bygg klart och verifiera den kedjan först.
2. **Billigaste inre-tillägget först:** prova **laser-tracheideffekt** (fibervinkel)
   på befintlig hårdvara + ev. **akustisk resonans** för ett styvhetsindex.
3. **ACU som proof-of-concept-steg** om inre defektkartläggning verkligen behövs:
   börja med **ETT fokuserat TX/RX-par i genomgång** (sändare över, mottagare i den
   öppna mätzonen under) vid ~150 kHz för att detektera **grov röta/håligheter** vid
   en X-position medan brädan matas. Utvärdera SNR på riktigt virke innan en array.
4. **Skala till array/C-scan** bara om PoC visar tillräckligt SNR och defekt-kontrast.
5. **Om budget finns och inre krav är höga:** jämför mot **röntgen** (bättre
   upplösning) innan stor ACU-investering.

## 10. Referenser / vidare läsning
- Översikter om luftburen ultraljud för NDT (impedansanpassning, CMUT/piezokomposit).
- Studier: ACU genomgång på plywood/limträ för delaminering; ultraljudshastighet/
  dämpning vs röta och densitet i sågat virke; anisotropisk ljudutbredning i trä.
- Industriell jämförelse: CT-loggскannrar (inre kvist/densitet), resonans-baserad
  styvhetsgradering (MTG/Viscan), tracheideffekt-skanning (fibervinkel).
- (Sök på: "air-coupled ultrasound wood NDT", "CMUT air-coupled", "ultrasonic
  velocity decay detection timber", "acoustic resonance strength grading lumber".)
