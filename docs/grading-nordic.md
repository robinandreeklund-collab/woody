# Nordisk virkessortering — komplett analys (A/B/C/D) + hur vår skanner gör det

> Underlag för att bygga om graderingskoden. Mål: klassa virke enligt nordisk
> standard. **Viktigaste insikten först:** det finns **TVÅ helt olika
> sorteringssystem** i Norden, och de blandas ofta ihop:
>
> 1. **UTSEENDESORTERING (kvalitet/appearance)** → **A / B / C / D** (Nordic Timber,
>    "Blå boken") ≈ **EN 1611-1** (G-klasser). Baserat på kvist, vankant, sprickor,
>    skevhet, missfärgning. **Detta är vad "A B C D" betyder.**
> 2. **HÅLLFASTHETSSORTERING (strength)** → **T0–T3 / C14–C30** (INSTA 142 → EN 338).
>    Baserat på kvistandel, fibervinkel, densitet/årsringar, skevhet. **OBS: "C24" här
>    är INTE samma "C" som utseende-C.**
>
> Vår laser+färg+(tracheid)-skanner kan mata BÅDA systemen från samma scan.

---

## 1. System 1 — UTSEENDESORTERING (A/B/C/D)

### 1.1 Grader & nomenklatur
| Vår term | Nordic Timber (nuv.) | 1994 (bokstäver) | EN 1611-1 | Användning |
|---|---|---|---|---|
| **A** (A1–A4) | U/S (osorterat, "unsorted") | A1–A4 | G4-0 / G4-1 | Topp-snickeri, synlig panel, möbel |
| **B** | V (kvinta/"fifths") | B | G4-2 | Snickeri, en del synligt |
| **C** | VI ("sixths") | C | G4-3 | Bygg/utskott, mer defekter ok |
| **D** | VII ("sevenths") | D | G4-4 | Formvirke, emballage (nästan allt ok) |

- **A delas i A1–A4** (A1 bäst). I handeln säljs A ofta som "osorterat/US" = blandning A1–A4.
- **Bokstäverna A–D** kommer från 1994 års utgåva; nuvarande Nordic Timber använder U/S, V, VI, VII — men **A–D används fortfarande i handeln**. Vi mappar dem.
- **EN 1611-1** är den harmoniserade europeiska standarden: grader **G4-0…G4-4** (4-sidig sortering, "0" bäst) eller **G2-0…G2-4** (2-sidig, ovanligt i Sverige).

### 1.2 Graderingsprincip
- Bedöms på **alla 4 sidor** (för G4). **Sämsta enskilda defekten avgör graden** ("worst defect governs").
- Vissa produkter graderas på **bästa sidan** (t.ex. panel på visningssidan) eller **sämsta sidan** — måste definieras per produkt/kund.
- Görs på **torrt virke** (~18 % fuktkvot ±2 %). Skevhetsgränser förutsätter torkat virke.
- Gradering har **subjektivitet** → mål är att matcha en erfaren sorterares konsensus, inte en absolut sanning.

### 1.3 Defektkatalog (det som mäts) + hur gränserna fungerar
Varje grad har **gränser per defekt** (de exakta talen finns i Blå boken/EN 1611-1, se §6). Strukturen:

| Defekt (sv / en) | Hur den graderas | Vår sensor |
|---|---|---|
| **Kvist** (knot): frisk/torr/lös/barkringad/rötkvist/kantkvist | **Storlek** (mm el. % av sidans bredd), **typ**, **antal/grupp**, **läge** (sida/kant). Dominerande faktorn. | färg + tracheid + 3D |
| **Vankant** (wane) | Max bredd/djup som andel av mått + längd | **3D-laser (direkt)** |
| **Sprickor** (checks/splits): ytspricka, ändspricka, genomgående, ringspricka | Längd, djup, genomgående? | färg + 3D (öppen spricka = spår) |
| **Formfel/skevhet** (distortion): flatböj (bow), kantkrok (spring/crook), vridning (twist), skålning (cup) | **mm över referenslängd** (t.ex. /2 m) | **3D-laser (hela brädgeometrin)** |
| **Missfärgning**: blånad (blue stain), röta (fast/mjuk), mögel | Area, typ, allvarlighet | **färg-line-scan** |
| **Kådlåpor** (pitch/resin pockets), **tjurved/kådved** (compression/pitchwood) | Storlek/antal | färg + 3D + tracheid (tjurved) |
| **Barkdragg/lyror** (bark pockets/scars) | Storlek | färg + 3D |
| **Märg** (pith), **toppbrott** (top rupture), **insekt-/hanteringsskada** | Förekomst/storlek | färg + 3D |
| **Måttavvikelse** (dimension) | tjocklek/bredd/längd mot nominellt | **LR400 + 3D** |

**Gränsexempel (strukturen, ej exakta tal):** kviststorlek anges typiskt som **andel av sidans bredd** — A tillåter små, B större, C ännu större, D nästan obegränsat; vankant som andel + längd; skevhet i mm/2 m. Talen ligger i standarden.

---

## 2. System 2 — HÅLLFASTHETSSORTERING (T/C)

För **bärande/konstruktionsvirke**. Helt andra kriterier (styrka, inte utseende).

- **INSTA 142** (nordisk visuell): grader **T3 – T2 – T1 – T0** → motsvarar **C30 / C24 / C18 / C14** (EN 338, karakteristisk böjhållfasthet 30/24/18/14 N/mm²).
- Gäller furu, gran, lärk m.fl. **Maskinell sortering (MSR)** finns också (EN 14081) och ger fler/snävare klasser.
- **Avgörande faktorer:**
  - **Kvistandel (KAR — Knot Area Ratio):** kvistens projicerade area / tvärsnittsarean. Stora kvistar i kanten sänker styrkan mest.
  - **Fibervinkel / lutande fiber** (slope of grain) — stark hållfasthetsprediktor → **tracheideffekten** mäter detta.
  - **Densitet / årsringsbredd** — tätare = starkare. (Optiskt svårt; ofta röntgen i industrin, eller skattning.)
  - **Skevhet, sprickor, tjurved, toppbrott.**
- **OBS:** strength-**C24** ≠ appearance-**C**. Håll dem isär i kod och UI.
- För att **deklarera** bärande virke (CE/EN 14081) krävs certifierad sortering — relevant senare, inte för en prototyp.

---

## 3. Vad VÅR skanner kan mäta (genomförbarhet)

| Kriterium | Mätbart hos oss? | Hur |
|---|---|---|
| Vankant | ✅ direkt | 3D-laser-profil (kantens form) |
| Skevhet (bow/spring/twist/cup) | ✅ direkt | hela brädans 3D-geometri |
| Mått (tjocklek/bredd/längd, vinkel) | ✅ | LR400 (absolut) + 3D |
| Kvist — läge & storlek | ✅ | färgkontrast + 3D-relief + tracheid-virvel |
| Kvist — typ (frisk/torr/lös/röt) | 🟡 delvis | färg (mörk=torr) + ML-klassning |
| Sprickor | ✅ | färg (linje) + 3D (öppet spår) |
| Blånad / röta / mögel | ✅ | färg-line-scan (segmentering/ML) |
| Kådlåpor / bark / lyror | ✅ | färg + 3D |
| Fibervinkel (för styrka) | 🟡 | tracheid (röd laser) — PoC möjlig |
| Densitet / årsringar (för styrka) | 🔴 svårt | kräver röntgen för säker densitet; ringbredd ev. ur färg |

**Slutsats:** **utseendesortering A/B/C/D är väl täckt** av laser+färg(+tracheid). **Hållfasthet** kan vi göra delvis (KAR + fibervinkel via tracheid + skevhet), men säker densitet kräver röntgen → fokusera på **A/B/C/D först**.

---

## 4. Föreslagen kodarkitektur (gradering)

```
3D-fusion + färgbild + (tracheid)  →  [1] FEATURE-EXTRAKTION  →  defektlista
                                          ↓
                                   [2] REGEL-MOTOR (data-driven ruleset)
                                          ↓
                          grad (A/B/C/D) + STYRANDE defekt (spårbarhet)
```

### [1] Feature-extraktion (per bräda → per sida)
Bygg per-sida **feature-maps** + en **defektlista**, där varje defekt =
`{typ, sida, position(x,y), storlek, djup, allvarlighet, konfidens}`:
- **Kvistar:** detektera (färg/tracheid), mät diameter + andel av sidbredd, klassa typ (ML), läge (sida/kant/arris), gruppera kluster.
- **Vankant:** ur 3D-kantprofil → bredd/djup/längd per kant.
- **Sprickor:** färg-linje + 3D-spår → längd/djup, genomgående?
- **Skevhet:** ur 3D centrumlinje/yta → bow/spring/twist/cup i mm (+ normera /2 m).
- **Missfärgning:** färgsegmentering (ML el. tröskel) → area/typ/allvarlighet.
- **Mått:** tjocklek/bredd/längd/vinkel.

### [2] Regel-motor (regler som DATA, inte hårdkod)
- Gränserna per grad ligger i en **YAML/JSON-ruleset** (t.ex. `grading_rules_nordic.yaml`) → lätt att tona mot exakt standard-utgåva / kundregler utan att röra koden.
- För varje sida: hitta den **defekt som ger lägst grad**. Brädans grad = **sämsta sidan / sämsta defekten** (eller "bästa sidan" för panel — konfigurerbart per recept).
- Returnera **grad + den styrande defekten** (varför den blev nedklassad → spårbarhet, kalibrering, operatörsförtroende).
- **Dubbel utdata** möjlig: appearance-grad (A/B/C/D) OCH strength-klass (C-grad) från samma feature-set via två rulesets.

### Kalibrering mot referensbrädor
- Gradera en uppsättning **manuellt graderade referensbrädor**, tona trösklar/gränser tills systemet **matchar sorterar-konsensus**. Mät överensstämmelse (confusion matrix mot facit).

---

## 5. Implementationsplan (nästa steg i koden)
1. Definiera **defekt-datamodell** + per-sida feature-maps i pipelinen.
2. Skriv **regel-motorn** (läser `grading_rules_nordic.yaml`, "sämsta defekt avgör", konfigurerbar bästa/sämsta-sida).
3. Lägg ett **start-ruleset** för A/B/C/D (struktur enligt §1.3; exakta tal när standarden köpts).
4. Koppla in befintliga detektorer (vankant/skevhet/mått via 3D finns redan); lägg **kvist/spricka/missfärgnings-detektering** (regler först, ML sen).
5. **Kalibreringsläge:** kör referensbrädor → confusion matrix → tona gränser.
6. GUI: visa **grad + styrande defekt + var på brädan** (overlay).

## 6. Viktiga förbehåll
- **Exakta gränsvärden är upphovsrättsskyddade.** Köp **Nordic Timber ("Blå boken")** och/eller **SS-EN 1611-1** (från SIS) för de precisa talen — och för att få **deklarera** graden. Vi kan koda strukturen + typvärden nu; lägg in de exakta talen från standarden.
- **A–D (1994) ↔ U/S, V, VI, VII (nuv.) ↔ EN G4-0…4** — mappa, och bestäm vilken terminologi UI:t visar.
- **Bästa- vs sämsta-sida** beror på produkt (panel = visningssida) → gör det till en recept-inställning.
- **Fuktkvot ~18 %** antas; skevhet gäller torkat virke.
- **Strength-C ≠ appearance-C.** Håll isär. Bärande virke kräver certifiering (EN 14081) — senare.
- **Säker densitet kräver röntgen** → börja med utseende (A/B/C/D), lägg ev. tracheid-fibervinkel för en grov styrkeindikation.

## Källor
- [Swedish Wood — Wood grades](https://www.swedishwood.com/wood-facts/about-wood/wood-grades/)
- [Swedish Wood — Grading of sawn timber (PDF)](https://www.swedishwood.ae/siteassets/5-publikationer/pdfer/grading-of-sawn-timber.pdf)
- [Nordic softwood grading rules / "Blue book" (Fordaq)](https://www.fordaq.com/fordaq/html/quality_softwood_bluebook_En.htm)
- [SS-EN 1611-1 (SIS)](https://www.sis.se/en/produkter/wood-technology/wood-sawlogs-and-sawn-timber/ssen16111/)
- [INSTA 142 — Nordic visual strength grading (GlobalSpec)](https://standards.globalspec.com/std/1183594/ds-insta-142)
- [Visual grading of sawn timber (Sahateollisuuskirja)](https://sahateollisuuskirja.fi/en/laatulajittelu-ja-lujuuslajittelu/sahatavaran-visuaalinen-laadun-maarittely/)
- [Appearance Grading of Sawn Timber (DiVA, fulltext PDF)](http://www.diva-portal.org/smash/get/diva2:990037/FULLTEXT01.pdf)
