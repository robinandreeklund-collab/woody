# CLAUDE.md — instruktioner för Claude Code

Du fortsätter att **integrera denna referensprototyp i den riktiga kodbasen**. Läs `README.md`
först (full spec) och `ARCHITECTURE.md` (föreslagen stack). Detta dokument säger vad du ska göra,
i vilken ordning, och var de verkliga modulerna kopplas in.

## Vad prototypen är
En komplett, fungerande HTML/CSS/JS + Three.js-referens för GUI:t. Den driver allt med **simulerad
data**. Look, layout, animationer, formler och kapalgoritm är slutgiltiga och ska bevaras troget.

## Vad som ska bytas ut mot riktigt
1. **`js/textures.js` (procedurell bräda) → riktig data.** Behåll det *utdataformat* prototypen
   förväntar sig (se "Datakontrakt"), men producera lagren från riktiga källor:
   - färg = RGB line-scan-bild
   - höjd = laserprofil/höjdkarta (mm)
   - tracheid/undersida/röntgen = respektive sensor
   - facit-kartan (`label`) används idag som "prediktion" — ersätt med riktig U-Net-inferens.
2. **Segmentering → riktig U-Net.** Använd befintliga `src/model.py` + `src/infer.py` (kaklad
   inferens). Antingen serverside (FastAPI) eller i webbläsaren via ONNX (onnxruntime-web).
3. **`js/cutplan.js` (DP) → porta till backend** (samma algoritm i Python) eller behåll i frontend.
   Algoritmen är korrekt; ändra inte beteendet, bara var den körs.

## Datakontrakt (det prototypen konsumerar)
`WoodGen.makeBoard(seed)` returnerar ett objekt; ersätt källan men behåll formen:
```
{
  W, H, RES,                       // bildmått (px) + mm/px
  color, label, height,            // <canvas/bild> lager (label = klass 0..6 som färg+alfa)
  tracheid, xray, underColor, underLabel,
  heightData,                      // Uint8ClampedArray (RGBA) av height, för profilberäkning
  stats: {
    counts[7], areas[7],           // per klass
    features: [{cls, u, fv, area}],// u=position längs längd 0..1, fv=position längs bredd 0..1
    crackLenMm, maxFiberDev, innerKnots, defectArea
  },
  id, plan                         // sätts av main.js (id) + cutplan (plan)
}
```
`CutPlan.plan(features, lengths)` → `{pieces:[{aU,bU,lenM,grade,value,color}], totalValue, yield, trimM, L, lengths}`.

## Föreslagen ordning
1. **Scaffold** `web/frontend` (Vite + React + react-three-fiber + drei + Zustand) och `web/backend`
   (FastAPI). Se `ARCHITECTURE.md`.
2. **Porta state** (`js/main.js` `state` + kö-logik) till en Zustand-store. Behåll formlerna i
   "takt↔upplösning" exakt.
3. **Porta UI** (`style.css` + `js/panel.js` + `js/readout.js`) till React-komponenter. Behåll
   design-tokens och canvas-ritningarna (profil, kap-stapel, readout-remsor) — de kan ligga kvar
   som `<canvas>` med samma ritkod.
4. **Porta 3D** (`js/scene.js`) till r3f: brädan = mesh med färgtextur + höjdkarta som displacement;
   flerkanals-fragment-shadern blir en `shaderMaterial`. Behåll `COL`-paletten och geometrimåtten.
5. **Backend-endpoints:** `GET /api/config`, `POST /api/board` (riktig make_board), `POST /api/segment`
   (U-Net), `POST /api/cutplan` (porterad DP). `WS /ws/stream` driver animationen (1 bräda/s) mot
   simklockan så GUI:t matchar prototypens tempo.
6. **Senare:** exportera U-Net → ONNX → onnxruntime-web för en helt statisk deploy utan Python.

## Bevara exakt (regression-risk)
- Skanningsriktning: bilden byggs upp **tvärs bredden (kortsidan)**, hela längden per skannlinje.
  Readout-remsan framkallas uppifrån ner; skannlinjen är horisontell.
- Formlerna `feedWorld/feedMps/alongRes/coarse/dataRate` (README).
- Kapalgoritmens parametrar (`SEV`, `FOOT`, `GRADE`, priser, längder).
- Design-tokens, typsnitt (IBM Plex Sans/Mono), gul mätram `#c2a43e`, accent `#e8542c`.
- Måtten: brädbredd 70–150 mm ställbar, kedjesträngar 77 mm, runda medbringare 50 mm Ø.

## Får ändras
- Var DP och inferens körs (frontend/backend).
- Textur-upplösning för prestanda (prototypen kör nedskalat 1400×176 i stället för 16k px).
- Rena refaktoreringar, så länge beteende och utseende består.

## Verifiering
- GUI:t ska se ut och bete sig som prototypen (jämför sida vid sida).
- Inga konsolfel. 60 fps på en bräda/s.
- Kapvärden varierar realistiskt per bräda (~130–310 kr) och optimeraren väljer bästa längdkombination.
- Sänkt takt → finare `alongRes` + skarpare bild; encoder→tid-trigg → synlig geometrisk distorsion.
