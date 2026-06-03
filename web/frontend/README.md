# web/frontend — React + Vite + TypeScript

React/Vite/TS-port av referensprototypen (`claude_code_woody/`). Skalet och
state-hanteringen (Zustand, `src/store.ts`) är React; den beprövade
renderingsmotorn (Three.js-scen, panel- och readout-canvas, kapalgoritm) körs
oförändrad från prototypen under `src/engine/` så att look/feel bevaras exakt.

```
src/
  main.tsx        React-mount + laddar motorn i rätt ordning
  App.tsx         skalet (#stage/#view, #readout, #panel) – motsv. Virkesskanner.html
  store.ts        Zustand – porterad från main.js `state`
  styles.css      prototypens designsystem (oförändrat)
  engine/         prototypens moduler (verbatim) + sim.js (porterad main.js)
    config.js textures.js cutplan.js scene.js panel.js readout.js sim.js
```

Three.js laddas som global (`window.THREE`) via CDN i `index.html`, precis som
prototypen.

## Köra

```bash
npm install
npm run dev        # http://localhost:5173  (proxar /api + /ws -> :8000)
npm run build      # produktionsbygge -> dist/
```

## Datakälla

Just nu driver den klientside-generatorn (`engine/textures.js`, WoodGen) appen –
den fungerar helt fristående. Nästa integrationssteg: byt datakällan till
backendens `/api/board` + `/api/segment` (kräver att backenden levererar samtliga
lager motorn konsumerar: label/tracheid/röntgen/undersida, inte bara färg/relief/
höjd). Vite-proxyn mot `:8000` är redan på plats.
