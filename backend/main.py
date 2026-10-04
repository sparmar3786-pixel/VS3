"""FastAPI host for the live terminal engine."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from backend.config import get_settings
from backend.market_cache import is_market_open
from backend.pipeline.orchestrator import TerminalEngine

@dataclass
class AppState:
    engine: TerminalEngine = field(default_factory=TerminalEngine)
    clients: Set[WebSocket] = field(default_factory=set)
    task: asyncio.Task | None = None

state=AppState()
app=FastAPI(title="VS3 NSE Algo Terminal",version="2.0")

async def broadcast(channel:str,payload:Any)->None:
    dead=[]
    message={"channel":channel,"payload":payload}
    for ws in list(state.clients):
        try: await ws.send_json(message)
        except Exception: dead.append(ws)
    for ws in dead: state.clients.discard(ws)

async def engine_broadcast(channel:str,payload:Any)->None:
    await broadcast(channel,payload)

state.engine.broadcaster=engine_broadcast

@app.on_event("startup")
async def start_engine()->None:
    await state.engine.start()
    if state.task is None or state.task.done():
        state.task=asyncio.create_task(state.engine.run_forever(),name="terminal-engine")

@app.on_event("shutdown")
async def stop_engine()->None:
    if state.task:
        state.task.cancel()
        try: await state.task
        except BaseException: pass
        state.task=None
    await state.engine.stop()

@app.get("/health")
async def health()->dict:
    return {"ok":True,"source":getattr(state.engine._source,"name","none"),
            "running":state.engine._running,"market_open":is_market_open(),
            "cycle":state.engine._cycle}

@app.get("/api/config")
async def config()->dict:
    s=get_settings()
    return {"indices":s.index_list,"source":getattr(state.engine._source,"name","none"),
            "market_open":is_market_open(),"ai_enabled":s.ai_on,"mcp_enabled":s.mcp_on}

@app.get("/api/snapshot/{index}")
async def snapshot(index:str)->dict:
    snap=state.engine.latest_snapshot(index.upper())
    if snap is None:return {"index":index.upper(),"available":False}
    return {"available":True,"snapshot":snap.model_dump(mode="json"),
            "market_open":is_market_open()}

@app.get("/api/overview")
async def overview()->dict:
    return state.engine.state_frame()

@app.websocket("/ws")
async def websocket(ws:WebSocket)->None:
    await ws.accept()
    state.clients.add(ws)
    try:
        await ws.send_json({"channel":"state","payload":state.engine.state_frame()})
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect,Exception):
        state.clients.discard(ws)
