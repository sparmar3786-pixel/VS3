"""VS3 production FastAPI entrypoint.

Vandana1 is the single source of truth for Angel One, NSE MCP, strategy and
AI orchestration. The former standalone demo Engine is no longer started here.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vandana1_adapter import app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / "frontend"
MOBILE = ROOT / "app" / "www"

@app.get("/api/health")
def api_health():
    # Backward-compatible route for the existing VS3 web UI.
    from server import health
    return health()

@app.get("/api/state")
def api_state():
    from server import terminal_snapshot
    return terminal_snapshot()

@app.get("/")
def index():
    return FileResponse(DESKTOP / "index.html")

if MOBILE.exists():
    app.mount("/app", StaticFiles(directory=MOBILE, html=True), name="app")
if DESKTOP.exists():
    app.mount("/static", StaticFiles(directory=DESKTOP), name="static")
