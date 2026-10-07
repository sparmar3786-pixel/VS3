"""Vandana2 application wrapper.

Keeps backend.main unchanged while adding the authenticated live terminal routes
and serving the standalone terminal UI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.responses import FileResponse

from backend.main import app
from backend.live_api import build_router, recorder
from backend.platform_router import build_router as build_platform_router
from backend.v1_compat import router as v1_router

ROOT = Path(__file__).resolve().parent.parent
_frontend = ROOT / "frontend"

app.include_router(build_router(lambda: getattr(__import__("backend.main", fromlist=["state"]), "state").engine), prefix="")
app.include_router(build_platform_router())
app.include_router(v1_router, prefix="")
# Explicit contract assertion at startup is intentionally avoided; the router owns the /v1 prefix.

_recorder_task: asyncio.Task | None = None


@app.on_event("startup")
async def _start_live_recorder() -> None:
    global _recorder_task
    from backend.main import state
    _recorder_task = asyncio.create_task(recorder(lambda: state.engine), name="live-setup-recorder")


@app.on_event("shutdown")
async def _stop_live_recorder() -> None:
    global _recorder_task
    if _recorder_task:
        _recorder_task.cancel()
        try:
            await _recorder_task
        except asyncio.CancelledError:
            pass
        _recorder_task = None


@app.get("/terminal.html", include_in_schema=False)
async def terminal_page() -> FileResponse:
    return FileResponse(_frontend / "terminal.html", media_type="text/html")


@app.get("/", include_in_schema=False)
async def root_page() -> FileResponse:
    return FileResponse(_frontend / "terminal.html", media_type="text/html")
