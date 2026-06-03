# ARCHITECTURE.md — föreslagen riktig stack

Prototypen är ett statiskt HTML/JS-GUI. För integration i den riktiga produkten föreslås:

```
web/
  frontend/                 Vite + React + TypeScript
    src/
      store.ts              Zustand — porterat från js/main.js `state` + kö-logik
      scene/                react-three-fiber + @react-three/drei
        Scene.tsx           porterat från js/scene.js (mätram, kedjor, medbringare, kapstation)
        BoardMaterial.tsx   flerkanals-shadern (uChannel/uOverlay/uCutOverlay/uDistort/uCoarse)
      panel/                porterat från js/panel.js (canvas-graf + kap-stapel behålls som <canvas>)
      readout/              porterat från js/readout.js (utrullade brädor, tvärs bredden)
      lib/derive.ts         takt↔upplösning-formlerna (oförändrade)
    index.html, vite.config.ts
  backend/                  FastAPI
    main.py                 endpoints + WS, återanvänder ../../src
    cutplan.py              DP porterad från js/cutplan.js
```

## Backend (FastAPI)
Återanvänd befintliga moduler i repo-roten:
- `src/board.py` — riktig `make_board` (eller läs riktiga sensorbilder).
- `src/acquisition.py` — line-scan-uppbyggnad, encoder/tids-trigg, laserprofil.
- `src/model.py`, `src/infer.py` — U-Net + kaklad inferens. Ladda checkpoint en gång vid start.

Endpoints:
| Metod | Path | Gör |
|---|---|---|
| GET | `/api/config` | LineConfig, defektklasser, defaultvärden |
| POST | `/api/board` | generera/hämta bräda → datakontraktet (se CLAUDE.md) |
| POST | `/api/segment` | kör U-Net → klasskarta + per-klass-stats + mIoU |
| POST | `/api/cutplan` | kör DP (cutplan.py) → pieces/totalValue/yield |
| WS | `/ws/stream` | driver animationen: bräda in → skannprogress → klassad → sågplan, 1 bräda/s |

## Frontend
- **3D:** brädan som mesh; färgtextur + höjdkarta (displacement). Flerkanals-fragment-shadern blir
  en r3f `shaderMaterial` (samma GLSL som i `js/scene.js`). Behåll `COL` och geometrin.
- **Panel & Readout:** behåll canvas-ritkoden (profil, kap-stapel, utrullade remsor) — flytta in i
  React-komponenter som ritar i en `useRef`-canvas. Design-tokens från `style.css` → CSS-variabler/Tailwind.
- **Store (Zustand):** håller hela `state`; WS-meddelanden uppdaterar den; UI och scen läser den.

## Statisk deploy (senare, utan Python)
Exportera U-Net → ONNX, kör i webbläsaren via **onnxruntime-web**. Då kan hela demon (inkl.
inferens + DP) köras klientside och hostas statiskt. Kör texturer nedskalat (t.ex. 1400×176) för
flyt, precis som prototypen — full 16k px behövs inte för visualisering.
