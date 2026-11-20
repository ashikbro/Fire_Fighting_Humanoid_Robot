"""FireOps Cloud application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .config import settings
from .db import init_db
from .deps import CurrentUser, require
from .notifier import start_worker
from .realtime import hub
from .routers import auth, fleet, ops
from .security import decode_token
from .simulator import seed_demo, simulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    hub.bind_loop(asyncio.get_running_loop())
    start_worker()
    if settings.enable_simulator:
        simulator.start()
    yield
    simulator.stop()


app = FastAPI(title="FireOps Cloud", version=__version__, lifespan=lifespan,
              description="Fleet command center for fire-fighting robots: telemetry, fire-risk analytics, "
                          "incident response, robot commands and predictive maintenance.")
app.include_router(auth.router)
app.include_router(auth.team)
app.include_router(fleet.router)
app.include_router(fleet.device)
app.include_router(ops.router)


class IgniteIn(BaseModel):
    x: float | None = None
    y: float | None = None
    intensity: float = Field(default=0.5, gt=0, le=1)


@app.post("/api/demo/seed", tags=["demo"])
def demo_seed(user: CurrentUser = Depends(require("admin"))):
    return seed_demo(user.org_id, user.id)


@app.post("/api/demo/ignite", tags=["demo"])
def demo_ignite(body: IgniteIn, user: CurrentUser = Depends(require("operator"))):
    """Start a simulated fire (demo mode only) to exercise the response workflow."""
    f = simulator.ignite(user.org_id, body.x, body.y, body.intensity)
    return {"x": round(f.x, 1), "y": round(f.y, 1), "intensity": f.intensity}


@app.get("/api/demo/world", tags=["demo"])
def demo_world(user: CurrentUser = Depends(require("viewer"))):
    w = simulator.worlds.get(user.org_id)
    return {"fires": [{"x": f.x, "y": f.y, "intensity": f.intensity} for f in w.fires] if w else []}


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "version": __version__}


@app.websocket("/ws")
async def websocket(ws: WebSocket, token: str = Query(...)):
    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        await ws.close(code=4401)
        return
    org_id = int(claims["org"])
    await hub.connect(org_id, ws)
    try:
        while True:
            await ws.receive_text()  # keepalive pings from the client
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(org_id, ws)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")

