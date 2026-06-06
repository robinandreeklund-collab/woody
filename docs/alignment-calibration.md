# Vinklar: kalibrering vs exakt mekanik — analys

Behöver linjelaserns/kamerans **exakta vinklar** kalibreras, eller räcker ett fäste med
fasta vinklar + höjdjustering? Och är en **mikroservo med feedback** för automatisk
vinkel-/träffpunkts-kalibrering en bra idé?

> **Kort svar:** Mekaniskt exakta vinklar behövs **inte**. Triangulering **kalibreras
> optiskt** — en pixel→mm-modell fångar de *verkliga* vinklarna, WD:t och lins­distorsionen.
> Bygg ett **styvt fast-vinkel-fäste** (nominella grader, ±~1° räcker) + **lås det**, och
> kalibrera. Tillåt bara **fin-DOF för uppriktning** (laserfokus + höjd/translation så
> stripen hamnar i kamerans ROI), inte en justerbar vinkel. **Servo på vinkeln avråds** —
> den lägger till spel/drift, precis det triangulering inte tål.

---

## 1. Varför exakta vinklar inte behövs
Triangulering ger 3D ur en **kalibreringsmodell**, inte ur mekaniska tal. Du ställer en
känd referens (stegnormal/kalibreringskloss med kända höjder, ev. plan i flera Z-lägen),
och löser ut sambandet **kamerapixel → (X, Z) i mm**. Den modellen **absorberar**:
- den faktiska kamera-/laservinkeln (vad fästet nu blev),
- arbetsavståndet, perspektiv, lins­distorsion, liten skevhet.

Alltså: **bygg ungefär rätt, kalibrera exakt.** Ritningens 20°/40° är design­mål så att
(a) linjen hamnar i FOV och (b) θ ger önskad Z-upplösning — inte toleranser du måste
träffa på bågminuten.

## 2. Hur känslig är vinkeln?
- **Absolut noggrannhet:** ointressant — kalibreringen fångar den verkliga vinkeln.
- **Z-upplösning ∝ 1/sin θ.** Vid θ=20° ändrar ±1° `sin θ` med ~3 % → någon ynka procent
  i upplösning. Försumbart.
- **Fienden är DRIFT efter kalibrering.** Om vinkeln *rör sig* (temperatur, vibration,
  glapp) efter att du kalibrerat → systematiskt fel. Därför: **styvhet + låsning** är allt
  som räknas, inte justerbarhet.

## 3. Vad bör vara justerbart (och sen låsas)
- **Laserfokus:** vrid linsen → skarp, smal linje vid WD (avgörande för subpixel).
- **Höjd/translation:** liten förflyttning så stripen hamnar mitt i kamerans **ROI-band**
  (höjd-/triangulerings­axeln). Det är "träffpunkten" du vill rikta — i bild, inte i grader.
- **Kamerafokus** (+ ev. liten tip/tilt för FOV), sen **lås allt**.
- **Vinkeln:** sätts av fästet/vinkeladaptern och rörs inte.

## 4. Skärpa över hela linjen (Scheimpflug)
Kameran tittar **oblikt** på laserplanet → skärpedjupet räcker inte alltid över hela
linjen. Proffs lutar **sensorn** (Scheimpflug) så fokusplanet sammanfaller med laser­planet.
Med 12 mm-objektiv vid WD 710 och liten bländare kan DoF räcka, men det här är en
**lins-/mont­eringsfråga** — inte vinkel­kalibrering. Värt att verifiera vid bygget.

## 5. Servo med feedback — analys
**För en fast prototyp: avråds.** En motoriserad led på vinkeln:
- inför **glapp/backlash + servo-drift** (temp/last) → mätbrus och nollans-drift,
- löser ett problem du inte har (du *kalibrerar* vinkeln, behöver inte *köra* till den),
- adderar kostnad, fel­källor och ett nytt kalibreringsberoende.
Du skulle alltså bygga in just den instabilitet triangulering kräver att slippa.

**När en motoriserad axel KAN motiveras:**
- **Autofokus** av laser/lins (linjär, inte vinkel) — kan vara värt.
- **Recept-/produktbyte** (helt andra dimensioner) → kör till förinställt läge och
  **kalibrera om per preset**. Då är det en grov omställning, inte kontinuerlig finjustering.
- **Forsknings-/multikonfig-rigg** där man ofta varierar geometrin.

**Bättre väg till "automatisk kalibrering":** automatisera **mjukvaru­kalibreringen**,
inte mekaniken. Lägg en kalibreringskloss i mätzonen → en rutin detekterar den och
räknar fram pixel→mm-modellen automatiskt (knapptryck). Ingen rörlig led behövs.

## 6. Rekommendation (vår prototyp)
1. **Styvt fast-vinkel-fäste** vid 20°/40° (vinkeladaptern), tolerans ±~0,5–1°, ordentligt låst.
2. Fin-DOF: **laserfokus + höjd/translation** för stripe-i-ROI, **kamerafokus**, sen lås.
3. **Engångs-kalibrering** med stegnormal → pixel→mm-modell (per kamera). Spara i config.
4. **Daglig drift hanteras inte mekaniskt** utan av **band-baslinje + LR400-ankare**
   (se docs/zero-reference.md). Kalibrera om bara efter en smäll eller periodiskt.
5. **Hoppa servon på vinkeln.** Vill du automatisera: automatisera kalibrerings­rutinen.

## 7. Koppling till programmet
- Kalibrering-fliken: "Kamera-intrinsics" + "Trianguleringsplan" = denna engångs­kalibrering
  (pixel→mm). Modellen lagras och används av `processing/triangulate.py` (idag en linjär
  `gain` — byts mot den kalibrerade modellen).
- Lägg ev. en **kalibrerings­wizard** (lägg i kloss → tryck → modell beräknas + sparas).
- Telemetri: visa "senast kalibrerad" + en drift­indikator (om band-/ankar­avvikelsen växer
  → dags för ny kalibrering).
