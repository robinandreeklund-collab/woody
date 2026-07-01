# Hållfasthetssortering av konstruktionsvirke (analys)

Hur virket ska klassas *exakt* enligt Träguiden/svensk praxis, och hur våra
sensorer mappar mot reglerna. Källa: Träguiden – Konstruktionsvirke
(virkestyper och kvalitet), SS 230120, SS-EN 14081-1, EN 338.

## Två skilda system (förväxla dem inte)

1. **Hållfasthetssortering (konstruktionsvirke)** → klasser **C14, C18, C24,
   C30, C35**. Styr bärförmågan. Sorteras antingen:
   - **visuellt** enligt **SS 230120** (sorteringsklasser **T0, T1, T2, T3**
     som ger **C14, C18, C24, C30**), eller
   - **maskinellt** enligt **SS-EN 14081-1** (kan nå **C35**; ger ofta fler
     kvistar tillåtna än visuellt).
   Karakteristiska värden enligt **EN 338**. "C24" = 24 N/mm² karakteristisk
   böjhållfasthet; minst 95 av 100 bitar ska klara värdet.

2. **Utseendesortering (handelssortering)** → **G4-0…G4-3** (eller A–D / nordiska
   "blå boken"). Styr utseendet. Annan sak än hållfasthet.

**Avgörande:** för konstruktionsvirke är det *hållfasthetssorteringen* som gäller.
Vår nuvarande A/B/C-värdemodell är en utseende-/grovmodell – den bör kompletteras
(eller ersättas) med C-klassning för konstruktionsvirke.

## Egenskaper och gränser (visuell sortering, SS 230120)

| Egenskap | C30 (T3) | C24 (T2) | C18 (T1) | C14 (T0) |
|---|---|---|---|---|
| **Enstaka kvist (andel av bredden)** | 1/6 | 1/4 | 2/5 | 1/2 |
| Kvist (andel av tjockleken) | 1/3 | 1/2 | 4/5 | full |
| **Planböj (flatböj)** mm/2 m | 10 | 10 | 20 | 20 |
| **Kantkrok (spring)** mm/2 m | 8 | 8 | 12 | 12 |
| **Skevhet (vridning)** | 2 mm per 25 mm bredd | ← | ← | ← |
| **Vankant** | ≤ 1/3 av sidan | ← | ← | ← |
| **Sprickor** (längd) | strängare | ≤ 0,5 m | mer | mest |
| **Fast röta** | endast i kvist | endast i kvist | begränsat | smala stråk/kant |
| **Lös röta** | endast i kvist | ← | ← | ← |
| **Blånad** | **obegränsad – påverkar ej hållfasthet** | ← | ← | ← |

Klassen sätts av den **strängaste** (begränsande) egenskapen.

## Hur våra sensorer mäter varje egenskap

| Regel | Sensor i vår rigg | Status |
|---|---|---|
| Kvistkvot (kvist/bredd, kvist/tjocklek) | U-Net-segmentering (kvist) + brädmått | mäts (kvistarea→diameter) |
| Planböj / kantkrok / skevhet | laser-array (höjdkarta + warp) | mäts (geometry/laser) |
| Vankant ≤ 1/3 | laserprofil (vankantbredd) | mäts |
| Spricklängd | U-Net (spricka) | mäts |
| Röta (i kvist eller ej) | U-Net (röta) + kvistmask | mäts (delvis) |
| Blånad (ignoreras för hållfasthet) | U-Net (blånad) | **exkluderas** i C-klassningen |
| Densitet/årsringsbredd (maskin) | – | ej i prototypen (kräver täthetsmätning/röntgen) |

## Implementation

`src/grading.py` implementerar de visuella reglerna ovan: tar uppmätta värden
(kvistkvot, böj/krok/skevhet per 2 m, vankantandel, spricklängd, röta) och
returnerar **T-klass → C-klass** plus den begränsande egenskapen. Blånad ingår
inte. Maskinklass C35 kräver täthets-/E-modulmätning (utanför prototypen).

### Per bit, inte per bräda
Sorteringen gäller den **färdiga biten**. Därför bör C-klassning köras per
kapbit i kapoptimeringen, och priset sättas per C-klass (C30 > C24 > C18 > C14 >
vrak) i stället för dagens A/B/C.

## Att fastställa mot standarden
- Exakta tabellvärden (kvist även i tjocklek, sprickgränser per klass, skevhet
  vs referenslängd) bör dubbelkollas mot SS 230120 i sin helhet.
- Deformationer mäts korrekt som värsta värde över en **2 m-mätsträcka** ur
  laserprofilen (vår syntetiska warp är helbräds-värden – approximeras nu).
