import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import views
from engine import Engine

engine=Engine()
ROOT=Path(__file__).resolve().parent.parent
DESKTOP=ROOT/"frontend"
MOBILE=ROOT/"app"/"www"

@asynccontextmanager
async def lifespan(app:FastAPI):
    task=asyncio.create_task(engine.run())
    yield
    task.cancel()

app=FastAPI(title="NSE-AI-TERMINAL",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

@app.get("/api/health")
async def api_health():return views.health(engine)
@app.post("/api/login")
async def api_login():return {"mode":"PAPER","live_orders":False,"token":"demo"}
@app.get("/api/overview")
async def api_overview():return views.overview(engine)
@app.get("/api/chain")
async def api_chain(symbol:str="NIFTY50"):return views.chain(engine,symbol.upper())
@app.get("/api/layers")
async def api_layers(symbol:str="NIFTY50"):return views.layers(engine,symbol.upper())
@app.get("/api/plans")
async def api_plans(symbol:str="NIFTY50"):return views.plans(engine,symbol.upper())
@app.get("/api/strategies")
async def api_strategies():return views.strategies(engine)
@app.get("/api/risk")
async def api_risk():return views.risk(engine)
@app.get("/api/notifications")
async def api_notifications():return views.notifications(engine)
@app.get("/api/backtest")
async def api_backtest(symbol:str="NIFTY50",bars:int=500):return await views.backtest(symbol.upper(),bars)
@app.get("/api/state")
async def api_state():return engine.state()
@app.get("/api/candles/{symbol}")
async def api_candles(symbol:str):return views.candles(engine,symbol)
@app.post("/api/strategy/{name}")
async def toggle_strategy(name:str,enabled:bool):
    if name in engine.l3.enabled:engine.l3.enabled[name]=enabled
    return engine.l3.enabled
@app.post("/api/kill")
async def kill():engine.l5.kill=True;engine.close_all();return {"kill":True}
@app.post("/api/resume")
async def resume():engine.l5.kill=False;engine.l5.halted=False;return {"kill":False}
@app.websocket("/ws")
async def ws(websocket:WebSocket):
    await websocket.accept();engine.clients.add(websocket)
    try:
        await websocket.send_text(json.dumps(engine.snapshot()))
        while True:await websocket.receive_text()
    except WebSocketDisconnect:pass
    finally:engine.clients.discard(websocket)
@app.get("/")
async def index():return FileResponse(DESKTOP/"index.html")
if MOBILE.exists():app.mount("/app",StaticFiles(directory=MOBILE,html=True),name="app")
app.mount("/static",StaticFiles(directory=DESKTOP),name="static")