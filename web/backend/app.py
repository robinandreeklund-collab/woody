"""FastAPI-backend för virkesskanner-GUI:t.

Återanvänder repo-roten src/ (board, infer, features) och porterad cutplan.
Exponerar config/board/segment/cutplan + en WS-ström som driver animationen.

Kör:  uvicorn web.backend.app:app --reload --port 8000
"""
from __future__ import annotations

import asyncio

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import cutplan as cutplan_mod
from .boards import board_payload, segment_board, make_board_for, BoardSource

# Lazy singleton-datakälla (laddar modell + ev. Kodytek en gång)
_SOURCE = None
def get_source() -> BoardSource:
    global _SOURCE
    if _SOURCE is None:
        _SOURCE = BoardSource()
    return _SOURCE

app = FastAPI(title="Woody virkesskanner-API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

# Konstanter (samma som prototypens main.js/config.js)
SENSOR_RATE = 758          # Hz, fast radtakt
PX_LEN = 16364             # px tvärs längden (5,4 m @ 0,33 mm)
WU_MM = 5400 / 7           # 1 världsenhet i mm

# GUI-defektklasser (config.js-taxonomi, klass 0 = frisk)
GUI_CLASSES = [
    {"id": 0, "namn": "Frisk", "hex": "#00000000"},
    {"id": 1, "namn": "Kvist", "hex": "#d4953f"},
    {"id": 2, "namn": "Spricka", "hex": "#d2533f"},
    {"id": 3, "namn": "Blånad", "hex": "#5577bd"},
    {"id": 4, "namn": "Vankant", "hex": "#a072c4"},
    {"id": 5, "namn": "Röta", "hex": "#6fa15c"},
    {"id": 6, "namn": "Hål", "hex": "#cf6f9e"},
]


@app.get("/api/health")
def health():
    from .boards import find_checkpoint
    from src.config import SegConfig
    return {"status": "ok", "model_loaded": find_checkpoint(SegConfig()) is not None}


@app.get("/api/config")
def config():
    return {
        "sensorRate": SENSOR_RATE, "pxLen": PX_LEN, "wuMm": WU_MM,
        "dataRate": round(SENSOR_RATE * PX_LEN * 3 / 1e6, 1),
        "classes": GUI_CLASSES,
        "cut": {"prices": cutplan_mod.PRICE, "colors": cutplan_mod.COLOR,
                "defaultLengths": [3.0, 2.7, 2.4]},
        "base": {"lengthM": 5.4, "widthMm": 125, "thickMm": 22,
                 "boardsPerMin": 60, "feedMps": 0.25, "mmPerPx": 0.33},
    }


class BoardReq(BaseModel):
    seed: int = 7
    widthMm: float = 125.0
    lengthM: float = 5.4
    mmPerPx: float = 0.5
    subtle: bool = False


@app.post("/api/board")
def board(req: BoardReq):
    b = make_board_for(req.seed, req.widthMm, req.lengthM, req.mmPerPx, req.subtle)
    payload = board_payload(b)
    payload["id"] = req.seed
    return payload


@app.post("/api/segment")
def segment(req: BoardReq):
    b = make_board_for(req.seed, req.widthMm, req.lengthM, req.mmPerPx, req.subtle)
    return segment_board(b)


class CutReq(BaseModel):
    features: list
    lengths: list[float] = [3.0, 2.7, 2.4]


@app.post("/api/cutplan")
def cut(req: CutReq):
    return cutplan_mod.plan(req.features, req.lengths)


class NextReq(BaseModel):
    seed: int = 0
    lengths: list[float] = [3.0, 2.7, 2.4]


@app.post("/api/next")
def next_board(req: NextReq):
    """Nästa bräda till GUI:t: färg + modellens segmentering + features + kapplan.
    Kodytek + tränad modell om de finns, annars syntetiskt (fungerar direkt)."""
    return get_source().next(req.seed, req.lengths)


class CropReq(BaseModel):
    seed: int
    u0: float = 0.0
    u1: float = 1.0
    v0: float = 0.0
    v1: float = 1.0
    maxPx: int = 2000


@app.post("/api/crop")
def crop(req: CropReq):
    """Sann-upplösnings-utsnitt av en bräda (regenereras från seed) för zoomvyn."""
    return get_source().crop_window(req.seed, req.u0, req.u1, req.v0, req.v1, req.maxPx)


ROUND = 120  # brädor per simuleringsrunda


@app.get("/api/round")
def round_info():
    src = get_source()
    return {"perRound": ROUND,
            "source": "kodytek" if src.kodytek else "syntetisk",
            "model": src.model is not None}


@app.websocket("/ws/stream")
async def stream(ws: WebSocket):
    """Driver animationen: en bräda i taget (board -> segment -> cutplan),
    med intervall enligt takt. Tunga beräkningar i trådpool så loopen ej blockas."""
    await ws.accept()
    loop = asyncio.get_event_loop()
    params = {"takt": 60, "seed": 100, "lengths": [3.0, 2.7, 2.4],
              "widthMm": 125.0, "mmPerPx": 0.5}

    async def recv():
        try:
            while True:
                msg = await ws.receive_json()
                params.update(msg)
        except WebSocketDisconnect:
            pass

    recv_task = asyncio.create_task(recv())
    try:
        while True:
            seed = params["seed"]
            params["seed"] += 1

            def work():
                b = make_board_for(seed, params["widthMm"], 5.4, params["mmPerPx"])
                payload = board_payload(b)
                payload["id"] = seed
                seg = segment_board(b)
                pln = cutplan_mod.plan(seg["stats"]["features"], params["lengths"])
                return payload, seg, pln

            payload, seg, pln = await loop.run_in_executor(None, work)
            await ws.send_json({"type": "board", "board": payload,
                                "segment": seg, "cutplan": pln})
            interval = 60.0 / max(1, params["takt"])  # sekunder per bräda
            await asyncio.sleep(interval)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        recv_task.cancel()


# Servera den byggda frontenden på "/" (efter API/WS så de matchas först).
_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="ui")
