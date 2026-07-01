# web/ – integration av virkesskanner-GUI:t

Integrerar referensprototypen i `claude_code_woody/` (komplett HTML/JS + Three.js,
se dess `README.md`/`CLAUDE.md`/`ARCHITECTURE.md`) med den riktiga Python-kodbasen
i repo-roten `src/`. Vald väg: **full React + react-three-fiber-frontend** mot en
**FastAPI-backend** som återanvänder `src/`.

## Status

- **Backend (`web/backend/`) – klar och verifierad.**
  - `GET /api/config` – konstanter, defektklasser, kap-priser/-längder.
  - `POST /api/board` – `src.board.make_board` → GUI:ts datakontrakt (färg/relief/
    höjd som PNG + defektfeatures).
  - `POST /api/segment` – U-Net via `src.infer` (faller tillbaka på facit utan
    checkpoint) → klasstats + mIoU.
  - `POST /api/cutplan` – `cutplan.py`, en **trogen port av js/cutplan.js**
    (verifierad identisk mot JS-originalet via node).
  - `WS /ws/stream` – driver animationen, en bräda/s (board → segment → cutplan).
- **Frontend (`web/frontend/`) – React + Vite + TypeScript.**
  Skal + state (Zustand) i React; prototypens beprövade motor (Three.js-scen,
  panel/readout-canvas, kapalgoritm) körs oförändrad under `src/engine/` så
  look/feel bevaras exakt.
- **End-to-end klart.** `engine/source.js` hämtar brädor från `/api/next` och
  patchar in **riktig färg + modellens segmentering + features + kapplan** i
  motorns brädor. Höjdlagret är den **fysikaliskt uppmätta höjdkartan** (slumpad
  3D-deformation läst av laser-/kamera-arrayen, `src/hardware|geometry|laser.py`),
  så brädan deformeras till den geometri kamerorna faktiskt mäter, med Kodytek-
  texturen ovanpå. Backenden servar frontenden på `/`. Fallback till lokal
  generator om backenden är onåbar. Rundor om 120 brädor + laser-array visas i HUD:en.

## Ett kommando (lokalt)

```bash
./start.sh                      # miljö + bygg + GUI på http://localhost:8000 (syntetisk data)
./start.sh --with-kodytek       # ladda ner + rastrera Kodytek, kör på riktig data
./start.sh --with-kodytek --train   # + träna modellen lokalt (GPU via device=auto)
```

## Köra backenden

```bash
pip install -r requirements.txt -r web/backend/requirements.txt
uvicorn web.backend.app:app --reload --port 8000   # från repo-roten
```

## Att lösa: klasstaxonomi

Prototypen använder klasserna (Frisk/Kvist/Spricka/Blånad/Vankant/**Röta**/**Hål**)
medan den tränade modellen använder (clear/live_knot/dead_knot/crack/blue_stain/
wane/**marrow**). `web/backend/boards.py:MODEL_TO_GUI` mappar provisoriskt
(live+dead knot→Kvist, marrow→Röta, GUI:ts Hål oanvänd). Bör fastställas – antingen
förena på en taxonomi eller behålla mappningen.
