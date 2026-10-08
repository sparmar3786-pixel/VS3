"""PDF-compatible /v1 API facade over the existing VS3 engine.

Read-only market analysis only. No order-placement endpoint is exposed.
"""
from __future__ import annotations
import asyncio
import csv
import io
import time
from typing import Any, Optional
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
import hmac
from fastapi.responses import Response
from backend.config import get_settings
from backend.live_api import _from_snap, _jwt_exp
from backend.main import state
from backend.nse_mcp import NSEMCP, result_to_csv
from backend.signal_engine import build_signal

_official_nse_mcp = NSEMCP()

def _require_api_token(request: Request,
                       x_app_key: str = Header(default="", alias="x-app-key"),
                       x_token: str = Header(default="", alias="x-token"),
                       authorization: str = Header(default="")) -> None:
    s = get_settings()
    # Safe read-only diagnostics are public so the APK can distinguish
    # "backend is reachable" from "backend token is invalid".
    if request.method == "GET" and request.url.path in {"/v1/angel/status", "/v1/nse/mcp/tools"}:
        return
    if str(s.api_token_required).strip().lower() not in {"1", "on", "true", "yes"}:
        return
    expected = str(s.api_token or "").strip() if hasattr(s, "api_token") else ""
    if not expected:
        raise HTTPException(503, "API_TOKEN is required on the server")
    supplied = x_app_key.strip() or x_token.strip()
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