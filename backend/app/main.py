"""FastAPI app: API, WebSocket and the built frontend from one process (AGENTS.md §4).

Exactly one instance runs in production: state is in memory, and a second task would split staff
approvals from passenger phones.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import flowcore
from app.api.routes import build_router
from app.schemas import Health
from app.state import Runtime
from flowcore import aws
from flowcore.config import get_settings

STATIC = Path(__file__).parent / "static"
PAGES = Path(__file__).parent / "pages"


def create_app() -> FastAPI:
    # Settings and intervals are read here, not at import time (AGENTS.md §17.5.3).
    settings = get_settings()
    runtime = Runtime(
        scenario_id=Runtime.default_scenario(settings.env("FLOW_SCENARIO")),
        tick_seconds=float(settings.env("FLOW_TICK_SECONDS") or 1),
        clock_seconds=float(settings.env("FLOW_CLOCK_SECONDS") or 5),
        ping_seconds=float(settings.env("FLOW_PING_SECONDS") or 20),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        runtime.start()
        yield
        await runtime.stop()

    app = FastAPI(title="Cathay Flow", version=flowcore.__version__, lifespan=lifespan)
    app.state.runtime = runtime

    @app.get("/api/health", response_model=Health)
    async def health() -> Health:
        return Health(
            ok=True,
            version=flowcore.__version__,
            offline=settings.offline,
            bucket=aws.mask(settings.bucket) if settings.bucket else None,
            scenario=runtime.sim.meta["id"] if runtime.sim else None,
        )

    app.include_router(build_router(runtime))

    @app.websocket("/ws")
    async def ws(socket: WebSocket, role: str = "passenger", pid: str | None = None) -> None:
        await socket.accept()
        runtime.hub.add(socket, "staff" if role == "staff" else "passenger", pid)
        await runtime.publish_clock()
        try:
            while True:  # drain what the client sends; the server does not act on it
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            runtime.hub.remove(socket)

    @app.get("/ws-test", response_class=HTMLResponse, include_in_schema=False)
    async def ws_test() -> str:
        return (PAGES / "ws_test.html").read_text(encoding="utf-8")

    if (STATIC / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            file = STATIC / path
            return FileResponse(file if path and file.is_file() else STATIC / "index.html")
    else:
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def placeholder() -> str:
            return (PAGES / "placeholder.html").read_text(encoding="utf-8")

    return app


app = create_app()
