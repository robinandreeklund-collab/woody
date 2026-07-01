# Dashboard → nästa nivå: analys & förslag

Hur vi tar kontrollsystemets GUI från "live-översikt" till en komplett
**3D-inspektions- och analysplattform**. Status: ✅ = byggt, ▶ = föreslaget.

## 0. Vad vi redan har (datагrund)
Vi mäter och lagrar per bräda: full **höjdkarta Z(x,y)** (dubbel-oblik triangulering,
röd+grön, LR400-ankrad absolut tjocklek), **färgyta (RGB)**, **defektregioner** och
**skevhet**. Det räcker för allt nedan — det är en visualiserings-/analysfråga, inte
en mätfråga.

## 1. Profiler ✅ + ▶
- ✅ **Längsprofil Z(x)** längs 500 mm (bukt/krok).
- ✅ **Tvärprofil Z(y)** tvärs 75 mm — topp + båda kanterna (vankant/kupa). *(det du saknade)*
- ▶ **Kantprofiler (vankant):** tjocklek vid vänster/höger kant *längs* längden →
  vankant-längd och -djup per kant (det röda/gröna huvudet ser var sin kant bäst).
- ▶ **Per-huvud-profiler:** visa röd vs grön separat + den fusionerade → man ser
  hur de fyller varandras ocklusion.
- ▶ **Slice-verktyg:** dra ett snitt var som helst i 3D → profil uppdateras live.

## 2. 3D-rekonstruktion ✅ → ▶ (ny nivå)
- ✅ Software-3D (Canvas): roterbar yta ur höjdkartan, färglägen **Höjd/Avvikelse/
  Skuggad**, referensplan, auto-snurr, zoom. Skevheten förstoras så vridning syns.
- ▶ **Qt Quick 3D på Jetson (GPU):** lyser, texturerad, mjuk 60 fps orbit. Ger:
  - **Foto-textur:** mappa färgytan på meshen → "digital tvilling" av brädan.
  - **Solid extrudering:** rita brädan som en *kropp* (tjocklek), inte bara ett ark.
  - **Defekt-pins i 3D:** klickbara markörer (kvist/vankant/spricka) på rätt plats.
  - **Mät-pick:** klicka två punkter → avstånd/höjdskillnad; hovra → Z-värde.
  - **Avvikelse-heatmap** mot ideal/bästa-plan + **vridningspilar** vid hörnen.
  - **Export:** STL/PLY (mesh) + skärmbild till PDF-rapport.
- ▶ **Jämför två brädor** sida-vid-sida eller överlagrade (före/efter tork, t.ex.).

## 3. Skevhet & gradering ✅ + ▶
- ✅ Uppmätt **bow / cup / twist / crook** (mm) ur höjdkartan, med staplar.
- ▶ **Regelverk per standard** (t.ex. SS-EN 1611-1 / hållfasthetssortering): trösklar
  per klass → automatiskt utfall + *varför* (vilken parameter fällde brädan).
- ▶ **Dimensions-/volymrapport:** faktisk tjocklek/bredd/längd-statistik, min/medel/max,
  volym, och **kapförslag** (var man kapar bort värsta defekten → bästa utbyte).

## 4. Trender & produktion ▶
- ▶ **Trendgrafer** över skiftet: klassfördelning, genomflöde, skevhet-histogram,
  defekttyper över tid (driver process-/torkbeslut).
- ▶ **Larm/SPC:** glidande medel + gränser → flagga när något driver (t.ex. ökande bow).
- ▶ **Sökbar historik:** filtrera loggen (klass/defekt/datum), öppna en gammal bräda i 3D.

## 5. Interaktion & rapport ▶
- ▶ **Frys & granska:** pausa på en bräda, snurra/zooma, mät, kommentera.
- ▶ **Replay:** spela upp en skanning rad-för-rad.
- ▶ **PDF-rapport per bräda:** 3D-bild, profiler, skevhet, defekter, klass → arkiv/kund.
- ▶ **Pekskärms-läge:** större träffytor, svep mellan vyer (bänkpanel).

## 6. Teknik
- 3D nu: Canvas (funkar överallt, verifierbart). På bänken: **Qt Quick 3D** (RHI/GPU)
  för textur/ljus/mjukhet — Jetson har GPU:n.
- Mät-pick & defekt-pins: ray-pick i Quick3D eller skärm→mesh-projektion.
- Allt drivs av samma `mesh3d`/höjdkarta + färgyta vi redan exponerar.

## Föreslagen ordning
1. ✅ Tvärprofil + 3D-grund (klart).
2. ▶ Kant-/vankantprofiler + per-huvud-profiler.
3. ▶ Qt Quick 3D med foto-textur + solid + defekt-pins + mät-pick.
4. ▶ Graderingsregelverk + dimensions-/kaprapport.
5. ▶ Trender/SPC + sökbar historik + PDF-rapport.
