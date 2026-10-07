"""PDF-compatible /v1 API facade over the existing VS3 engine.

Read-only market analysis only. No order-placement endpoint is exposed.
"""
from __future__ import annotations
import asyncio
import csv
import io
import time
from typing import Any, Optional
from fastapi import APIRouter, Body, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
import hmac
from fastapi.responses import Response
from backend.config import get_settings
from backend.live_api import _from_snap, _jwt_exp
from backend.main import state
from backend.nse_mcp import NSEMCP, result_to_csv

_official_nse_mcp = NSEMCP()

def _require_api_token(x_app_key: str = Header(default="", alias="x-app-key"),
                       authorization: str = Header(default="")) -> None:
    s = get_settings()
    if str(s.api_token_required).strip().lower() not in {"1", "on", "true", "yes"}:
        return
    expected = str(s.api_token or "").strip() if hasattr(s, "api_token") else ""
    if not expected:
        raise HTTPException(503, "API_TOKEN is required on the server")
    supplied = x_app_key.strip()
    if not supplied and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "authentication required")

router = APIRouter(prefix="/v1", tags=["pdf-contract"], dependencies=[Depends(_require_api_token)])

MCP_TOOLS = [
    "get_indices", "get_market_status", "get_option_chain", "get_quote",
    "get_ltp", "get_oi_heatmap", "get_iv_surface", "get_greeks",
    "run_strategy_scan", "get_terminal_verdict",
]

def _source() -> Any:
    src = state.engine._source
    if src is None:
        raise HTTPException(503, "market source is not ready")
    return src

def _token_info(src: Any) -> dict:
    return {
        "connected": bool(getattr(src, "jwt", None)),
        "jwt_tail": (getattr(src, "jwt", "") or "")[-6:] or None,
        "expires_at": _jwt_exp(getattr(src, "jwt", None)),
        "has_refresh": bool(getattr(src, "refresh_token", None)),
        "has_feed": bool(getattr(src, "feed_token", None)),
        "flow": "loginByPassword(clientcode+PIN+TOTP) -> jwt/refresh/feed",
    }

@router.get("/angel/status")
async def angel_status() -> dict:
    try:
        return _token_info(_source())
    except HTTPException:
        return {"connected": False, "source": "none"}

@router.post("/angel/login")
async def angel_login(body: dict = Body(...)) -> dict:
    src = _source()
    s = get_settings()
    client_id = str(body.get("clientId") or body.get("client_id") or s.angel_client_id).strip()
    pin = str(body.get("pin") or s.angel_pin).strip()
    api_key = str(body.get("apiKey") or body.get("api_key") or s.angel_api_key).strip()
    totp = str(body.get("totp") or "").strip()
    if not (client_id and pin and api_key and totp):
        raise HTTPException(400, "need Angel One API key + client_id + PIN + TOTP")
    try:
        if hasattr(src, "api_key_override"):
            src.api_key_override = api_key
        if hasattr(src, "client_id_override"):
            src.client_id_override = client_id
        d = (await src._post_raw(
            "/rest/auth/angelbroking/user/v1/loginByPassword",
            {"clientcode": client_id, "password": pin, "totp": totp},
            authed=False,
        )).get("data") or {}
        if not d.get("jwtToken"):
            raise RuntimeError("Angel One returned no token")
        src.jwt, src.feed_token = d["jwtToken"], d.get("feedToken")
        src.refresh_token = d.get("refreshToken") or getattr(src, "refresh_token", None)
        src._connected = True
        state.engine._source = src
        return _token_info(src)
    except Exception as exc:
        raise HTTPException(401, f"Angel One login failed ({type(exc).__name__})")

@router.get("/angel/market")
async def angel_market(symbol: str = "NIFTY") -> dict:
    src = _source()
    key = symbol.upper().replace(" ", "")
    try:
        tick = await src.get_quote(key, token=key)
    except Exception as exc:
        raise HTTPException(502, f"Angel One quote failed ({type(exc).__name__})")
    if tick is None:
        return {"symbol": key, "connected": bool(getattr(src, "jwt", None)), "available": False}
    data = tick.model_dump(mode="json") if hasattr(tick, "model_dump") else dict(tick)
    return {"symbol": key, "connected": True, "available": True, **data}

def _rows(snap: Any, count: int) -> list[dict]:
    out = []
    for x in snap.strikes[:max(1, min(count, 200))]:
        out += [
            {"strike": x.strike, "type": "CE", "ltp": x.ce_ltp, "oi": x.ce_oi, "oiChg": x.ce_oi_change, "volume": x.ce_volume, "iv": x.ce_iv},
            {"strike": x.strike, "type": "PE", "ltp": x.pe_ltp, "oi": x.pe_oi, "oiChg": x.pe_oi_change, "volume": x.pe_volume, "iv": x.pe_iv},
        ]
    return out

@router.get("/angel/option-chain")
async def angel_option_chain(symbol: str = "NIFTY", count: int = 40, expiry: Optional[str] = None) -> dict:
    src = _source()
    key = symbol.upper().replace(" ", "")
    try:
        snap = await src.get_option_chain(key, expiry)
    except Exception as exc:
        raise HTTPException(502, f"option chain failed ({type(exc).__name__})")
    if snap is None:
        raise HTTPException(502, "option chain unavailable")
    expiries = src.list_expiries(key) if hasattr(src, "list_expiries") else []
    return {"symbol": key, "connected": bool(getattr(src, "jwt", None)),
            **_from_snap(snap, expiries), "rows": _rows(snap, count)}

@router.get("/nse/mcp/tools")
async def mcp_tools() -> dict:
    try:
        tools = await asyncio.to_thread(_official_nse_mcp.tools)
        return {"enabled": True, "connected": True, "endpoint": _official_nse_mcp.url,
                "count": len(tools),
                "tools": [{"name": t.get("name"), "description": t.get("description")} for t in tools]}
    except Exception as exc:
        return {"enabled": get_settings().mcp_on, "connected": False, "endpoint": _official_nse_mcp.url,
                "count": 0, "tools": [], "error": str(exc)[:500]}

@router.get("/nse/mcp/context")
async def mcp_context(symbol: str = "NIFTY") -> dict:
    key = symbol.upper().replace(" ", "")
    try:
        data = await asyncio.to_thread(_official_nse_mcp.context, key)
        data["symbol"] = key
        data["source"] = "official_nse_streamable_http"
        data["fetched_at"] = time.time()
        return data
    except Exception as exc:
        snap = state.engine._mcp_snapshots.get(key)
        updated = state.engine._mcp_updated.get(key)
        if snap is not None:
            data = _from_snap(snap, [])
            if updated is not None:
                data["age_sec"] = max(0.0, time.time() - updated)
            return {"symbol": key, "connected": True, "source": "nse_mcp_cache", "data": data}
        return {"symbol": key, "connected": False, "pending": True, "source": "official_nse_streamable_http",
                "error": str(exc)[:500]}

@router.get("/nse/option-chain.csv")
async def nse_option_chain_csv(symbol: str = "NIFTY", expiry: Optional[str] = None) -> Response:
    key = symbol.upper().replace(" ", "")
    try:
        _tool, result = await asyncio.to_thread(_official_nse_mcp.option_chain, key, expiry)
        return Response(result_to_csv(result), media_type="text/csv",
                        headers={"X-NSE-MCP-Tool": str(_tool)})
    except Exception as exc:
        snap = state.engine._mcp_snapshots.get(key) or state.engine.latest_snapshot(key)
        if snap is None:
            raise HTTPException(503, "NSE MCP option chain unavailable: " + str(exc)[:300])
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["symbol","expiry","spot","strike","type","ltp","oi","oi_change","volume","iv","source"])
        for row in _rows(snap, 200):
            w.writerow([key,snap.expiry,snap.spot,row["strike"],row["type"],row["ltp"],row["oi"],
                        row["oiChg"],row["volume"],row["iv"],snap.source])
        return Response(buf.getvalue(), media_type="text/csv")

@router.get("/ai/context")
async def ai_context(index: str = "NIFTY") -> dict:
    key = index.upper().replace(" ", "")
    ctx = state.engine.latest_context(key)
    snap = state.engine.latest_snapshot(key)
    mcp = state.engine._mcp_snapshots.get(key)
    try:
        mcp = await asyncio.to_thread(_official_nse_mcp.context, key)
    except Exception:
        pass
    return {
        "index": key,
        "market_open": bool(ctx and ctx.get("market_open")),
        "snapshot": snap.model_dump(mode="json") if snap else None,
        "nse_mcp": _from_snap(mcp, []) if mcp else {"connected": False, "pending": True},
        "engine_context": (ctx.results[-1] if ctx and ctx.results and isinstance(ctx.results[-1], dict) else {}),
        "ai_enabled": get_settings().ai_on,
        "read_only": True,
    }

@router.get("/terminal")
async def terminal() -> dict:
    return state.engine.state_frame()

@router.websocket("/ws")
async def ws_v1(ws: WebSocket) -> None:
    s = get_settings()
    expected = str(getattr(s, "api_token", "") or "").strip()
    supplied = ws.headers.get("x-app-key", "").strip()
    auth = ws.headers.get("authorization", "")
    if not supplied and auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
    if str(s.api_token_required).strip().lower() in {"1", "on", "true", "yes"}:
        if not expected:
            await ws.close(code=1011)
            return
        if not supplied or not hmac.compare_digest(supplied, expected):
            await ws.close(code=1008)
            return
    await ws.accept()
    state.clients.add(ws)
    try:
        await ws.send_json({"channel":"state","payload":state.engine.state_frame()})
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        state.clients.discard(ws)
