# Webbgränssnitt – designdokument

Ett interaktivt 3D-gränssnitt som visar **hela inspektionsflödet live**: brädor
glider i sidled genom mätramen, skannas av line-scan + laser, och klassas av
segmenteringsnätet – allt synkat mot en simuleringsklocka.

Beslut (fastställda): **Python-backend (FastAPI)**, **live on-the-fly-generering
och inferens**, strömmat över **WebSocket**. Frontend i **React +
react-three-fiber**. Detta dokument är planen; ingen kod är skriven än.

---

## 1. Mål och avgränsning

**Mål.** Visa dataflödet som redan finns i `src/` som en snygg, begriplig
animation: bräda in → skanning (textur framkallas, laser läser höjd) → klassning
(defektoverlay tonas in), med live-mätare och reglage.

**Avgränsning (v1).** En mätram, en transportbana, nedskalade brädor (≈1200×250
px) för flyt. Verkliga 5,4 m @ 0,33 mm/px (16k px) är för tungt att texturmappa i
realtid – mätarna visar de skarpa siffrorna men 3D:n kör nedskalat. Ej i v1:
fotometrisk stereo, tracheid, ONNX-klientinferens (se §11).

---

## 2. Arkitekturöversikt

```
            WebSocket (/ws/stream)
  ┌─────────────────────────────────────────────┐
  │  FRONTEND (Vite + React + react-three-fiber) │
  │   - 3D-scen: bana, mätram, brädor, laser     │
  │   - simuleringsklocka (interpolerar lägen)   │
  │   - sidopanel: mätare, legend, laserprofil   │
  │   - reglage: hastighet, mm/px, encoder/tid   │
  └───────────────▲───────────────┬──────────────┘
        events     │               │  kommandon
                   │               ▼
  ┌────────────────┴──────────────────────────────┐
  │  BACKEND (FastAPI + uvicorn)                    │
  │   sim.py   brädkö + klocka + händelsegenerator  │
  │   reuse →  src.board / src.acquisition          │
  │            src.model / src.infer / src.config   │
  │   model laddas en gång (checkpoint)             │
  └────────────────────────────────────────────────┘
```

Backend äger sanningen (simuleringsklocka, brädsekvens, modellutfall). Frontend
renderar och interpolerar mellan händelser så animationen blir len även om
nätet skickar glest.

---

## 3. Backend (FastAPI)

### 3.1 Återanvändning av befintlig kod
Inga modelländringar. Backend importerar:
- `src.config.LineConfig` / `SegConfig` – geometri, härledda mått, hyperparametrar.
- `src.board.make_board` – genererar färg/facit/höjd.
- `src.acquisition` – encoder/tid-förvärv + `laser_profile`.
- `src.infer.load_model` / `predict_board` / `colorize` – inferens.

### 3.2 Filstruktur
```
web/backend/
  app.py            FastAPI-app, HTTP + WebSocket-rutter
  sim.py            Simulation: brädkö, klocka, händelseström
  encode.py         numpy-array -> PNG (base64) för texturer
  schemas.py        pydantic-modeller för meddelanden
  requirements.txt  fastapi, uvicorn[standard], pydantic, pillow
```
(torch/numpy/matplotlib kommer från repots rot-`requirements.txt`.)

### 3.3 HTTP-endpoints
| Metod | Väg | Svar |
|---|---|---|
| `GET` | `/api/health` | `{status, device, model_loaded}` |
| `GET` | `/api/config` | geometri + härledda mått (mätarna), klasslista + färger |
| `POST` | `/api/board` | engångsgenerering (debug): färg-PNG, höjd, defektsammanfattning |

### 3.4 WebSocket `/ws/stream`
Driver hela animationen. **Klient → server (kommandon):**
```jsonc
{ "type": "set_params",
  "speed_mps": 0.25, "mm_per_px": 0.5,
  "trigger": "encoder" | "time", "running": true }
{ "type": "reset" }
```
**Server → klient (händelser, alla med `sim_t` i sekunder):**
```jsonc
// var 0,5 s: synk + mätare
{ "type": "tick", "sim_t": 12.34,
  "stats": { "line_rate_hz": 758, "data_rate_mb_s": 37.2,
             "boards_per_min": 60, "scanned_total": 12 } }

// en bräda föds vid banans ingång (lookahead ~3 brädor)
{ "type": "board_spawn", "id": 42, "t_enter": 13.0,
  "length_mm": 1200, "width_mm": 125, "thickness_mm": 22,
  "mm_per_px": 0.5,
  "color_png": "data:image/png;base64,...",   // nedskalad färgtextur
  "height_png": "data:image/png;base64,..." } // 16-bit-höjd -> displacement

// klassningen klar (skickas så fort inferensen är gjord, före utgång)
{ "type": "board_segmented", "id": 42,
  "overlay_png": "data:image/png;base64,...",
  "defects": [ { "cls": 1, "name": "live_knot", "area_mm2": 380, "count": 2,
                 "bbox_px": [r0,c0,r1,c1] } ],
  "metrics": { "miou": 0.987, "defect_area_frac": 0.06 } }

// laserprofil för det som just skannas (inset i panelen)
{ "type": "laser_profile", "id": 42,
  "thickness_mm": 22.0, "wane_max_mm": 6.5,
  "wane_mm": [/* nedsamplad vektor */] }
```

### 3.5 Simuleringsmotor (`sim.py`)
- **Klocka.** Monoton `sim_t` (drivs av en async-loop). En bräda föds var
  `board_spacing_m / speed_mps` sekund (vid 0,25 m/s, 0,25 m delning → 1/s).
- **Lookahead-kö.** Håll ~3 brädor i förväg: en bakgrundsuppgift kör
  `make_board(seed=id)` + `predict_board` och cachar resultatet, så `board_spawn`
  och `board_segmented` kan skickas utan att blockera klockan.
- **Trigger-läge.** `encoder` → skicka färgtexturen rak. `time` → kör
  `acquisition.acquire_timetrigger` med jitter och skicka den distorderade
  texturen, så distorsionen syns i 3D.
- **Determinism.** `id` = frö → reproducerbart; "reset" nollställer klocka och kö.

### 3.6 Prestanda
- Texturer nedskalas serverside (PIL) till ≤1200×250 och PNG-komprimeras →
  ~20–60 kB/bräda, oproblematiskt över WS.
- Inferens < 1 s CPU per bräda; lookahead-kön döljer latensen.
- En global asyncio-lås runt modellen (torch är inte trådsäker per default).

---

## 4. Frontend (React + react-three-fiber)

### 4.1 Stack
Vite + TypeScript, **react-three-fiber** (deklarativ Three.js) + **@react-three/drei**
(OrbitControls, Environment, Html-etiketter), **Zustand** (state), **Tailwind**
(panel-UI). WS-klient i `net/socket.ts`.

### 4.2 Filstruktur
```
web/frontend/
  index.html  package.json  vite.config.ts  tailwind.config.js
  src/
    main.tsx  App.tsx
    state/store.ts             // zustand: boards, klocka, params, stats
    net/socket.ts              // WS: parsar händelser -> store
    three/Scene.tsx            // <Canvas>, ljus, kamera, OrbitControls
    three/Conveyor.tsx         // bana + transportkedjor
    three/MeasurementFrame.tsx // gantry med kamera- och laserhus
    three/ScanLine.tsx         // glödande skannlinje (emissivt plan)
    three/LaserPlane.tsx       // laserblad + trianguleringshint
    three/Board.tsx            // texturerad slab: framkallning + overlay
    ui/MetricsPanel.tsx        // rad/s, MB/s, brädor/min, scanned_total
    ui/Legend.tsx              // klassfärger
    ui/Controls.tsx            // hastighet, mm/px, encoder/tid, play/pause
    ui/LaserProfileInset.tsx   // live tjocklek/vankant (figur 3 fast levande)
```

### 4.3 Scengraf
```
<Canvas>
  <Lights/> <Environment/>
  <Conveyor/>                      // statisk bana + kedjeanimation
  <MeasurementFrame position=x_frame>
     <ScanLine/> <LaserPlane/>
  </MeasurementFrame>
  {boards.map(b => <Board key=b.id .../>)}   // drivs av klockan
  <OrbitControls/>
</Canvas>
```

### 4.4 Brädans livscykel (kärnan i animationen)
Varje bräda är en slab-`mesh` (längd×bredd×tjocklek i rätt proportioner). Position
i matningsled interpoleras lokalt:
```
x(t) = x_start + speed_px_per_s * (clock.sim_t - t_enter)
```
- **Oskannad** (framför mätramen): blank/neutral yta.
- **Skannas** (passerar `x_frame`): en `reveal`-uniform (0→1) styrd av hur långt
  brädan korsat linjen klipper fram färgtexturen vänster→höger (custom shader
  eller animerad `clippingPlane`). Höjdkartan ger `displacementMap` → vankant och
  sprickor blir fysisk relief.
- **Klassad** (efter mätramen): `overlay_png` tonas in ovanpå färgen (mix-uniform
  0→1); `<Html>`-etiketter pop:ar vid defekternas bbox ("kvist", "spricka"…).
- **Utgång:** despawnas när den lämnat scenen; store släpper den.

### 4.5 Synk mot backend
`tick` sätter `clock.sim_t` (med liten utjämning mot lokal `requestAnimationFrame`
för len rörelse mellan tickar). Eftersom `board_spawn.t_enter` ligger i framtiden
placeras brädan korrekt redan innan den ska in. Glesa nät-events → len 60 fps lokalt.

### 4.6 Reglage → kommandon
`Controls` skickar `set_params` (hastighet, mm/px, encoder/tid, play/pause). Att
slå om till **tids-trigg** byter texturkällan till den distorderade bilden →
distorsionen syns direkt på brädan i 3D. Hastighet/mm/px uppdaterar mätarna
(`/api/config`-mått räknas om serverside).

---

## 5. Datakontrakt (sammanfattning)
Typade i `schemas.py` (pydantic) och en spegel i `frontend/src/net/types.ts`.
Texturer som data-URL-PNG. Klassfärger hämtas ur `config.CLASS_COLORS` så 3D och
legend alltid matchar facit. En enda källa för klasser → ingen drift.

---

## 6. Repo-struktur (tillägg)
```
web/
  DESIGN.md           (detta dokument)
  README.md           snabbstart (dev-kommandon)
  backend/  ...        (se §3.2)
  frontend/ ...        (se §4.2)
```
`src/` är oförändrad och delas av både CLI-pipelinen och webb-backenden.

---

## 7. Dev-setup (planerad)
```bash
# Backend
pip install -r requirements.txt -r web/backend/requirements.txt
uvicorn web.backend.app:app --reload --port 8000

# Frontend
cd web/frontend && npm install && npm run dev   # Vite på :5173, proxy -> :8000
```
Modellen tränas av `run_pipeline.py` (checkpoint i `outputs/`); backend laddar
den vid start, eller tränar en smoke-modell om ingen finns.

---

## 8. Milstolpar

| Fas | Innehåll | Klart när |
|---|---|---|
| **0** | Skelett: `web/backend/app.py` (health, config), `frontend` Vite-app, WS-handslag | mätarna visar `/api/config`-siffror live |
| **1** | Statisk 3D-bräda: texturerad slab + höjdrelief + overlay-toggle | en bräda renderas med facit/prediktion-toggle |
| **2** | Animation: spawn → rörelse → skannlinje-framkallning → overlay-intoning, sidopanel | brädor flyter genom mätramen och klassas (förgenererad seed-sekvens) |
| **3** | Live: `sim.py` lookahead-kö, on-the-fly `make_board`+`predict_board`, encoder/tid-toggle, laserprofil-inset | allt drivs live från backend, reglagen påverkar |
| **4** | Polish: ljus/material, kedjeanimation, "åk med"-kamera, etiketter, deploy | demobar, snygg |

Varje fas committas och pushas separat till branchen.

## 9. Risker & beslut
- **Texturstorlek vs flyt** → nedskala serverside; mätarna behåller skarpa tal.
- **Torch-trådsäkerhet** → asyncio-lås runt inferensen.
- **Reveal-effekten** → custom shader-material; fallback är animerat clipping-plan.
- **WS-backtryck** → lookahead-kö med tak; droppa `tick` före tunga events.

## 10. Framtida (utanför v1)
- **ONNX-klientinferens** (`onnxruntime-web`) → statisk deploy utan server.
- **Fotometrisk stereo / tracheid** som extra kanaler i `board.py` → fler
  defektsignaturer för både modell och visualisering.
- **Flera mätramar / undersida** för att spegla en hel såglinje.
