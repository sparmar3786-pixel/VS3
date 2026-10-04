"""Live-connect routes (mounted by backend/app.py; main.py is untouched).

* Angel One token flow  : clientcode + PIN + TOTP -> jwt / refresh / feed token
* NSE public            : index constituents, F&O symbols, option chains (index + stocks)
* Angel One             : SENSEX / BANKEX option chain, candles up to N years (chunked)
* Net switch            : stays ONLINE unless "net off" is explicitly ticked
* AI daily memory       : per-day JSONL + downloadable file (for saving on the phone)
* Setups                : latest decisions per index + per-day history

Every route needs the header  X-API-Key: <TERMINAL_API_KEY>  (fails closed if unset).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend import nse_http
from backend.config import get_settings
from backend.logging_config import get_logger
from backend.strategies.catalog import strategy_search

log = get_logger("live")
IST = timezone(timedelta(hours=5, minutes=30))
DATA = Path(os.getenv("DATA_DIR", "data"))
BSE_IDX = {"SENSEX", "BANKEX"}
# Angel getCandleData max days per request
LIM = {"ONE_MINUTE": 30, "THREE_MINUTE": 60, "FIVE_MINUTE": 100, "TEN_MINUTE": 100,
       "FIFTEEN_MINUTE": 200, "THIRTY_MINUTE": 200, "ONE_HOUR": 400, "ONE_DAY": 2000}

_net = {"offline": False}


def _today() -> str:
    return datetime.now(IST).date().isoformat()


def _safe_day(d: str) -> str:
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return d
    except Exception:
        raise HTTPException(400, "day must be YYYY-MM-DD")


def _read_jsonl(p: Path) -> List[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def _append_jsonl(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


try:
    _net["offline"] = bool(json.loads((DATA / "net.json").read_text()).get("offline"))
except Exception:
    pass


def guard(x_api_key: str = Header(default="")) -> None:
    key = os.getenv("TERMINAL_API_KEY", "")
    if not key:
        raise HTTPException(503, "TERMINAL_API_KEY is not set on the server")
    if not hmac.compare_digest(x_api_key, key):
        raise HTTPException(401, "bad API key")


def online() -> None:
    if _net["offline"]:
        raise HTTPException(503, "offline mode is ON (net off ticked)")


def _jwt_exp(tok: Optional[str]) -> Optional[str]:
    try:
        p = tok.split(".")[1]
        p += "=" * (-len(p) % 4)
        return datetime.fromtimestamp(json.loads(base64.urlsafe_b64decode(p))["exp"], timezone.utc).isoformat()
    except Exception:
        return None


# ---------------------------- NSE via MCP (first) or direct (fallback) ----------------------------
def _mcp_servers() -> List[dict]:
    try:
        cfg = json.loads(Path(get_settings().mcp_config_path).read_text())
    except Exception:
        return []
    by = {x.get("name"): x for x in cfg.get("servers", []) if isinstance(x, dict)}
    out = []
    for n in cfg.get("live_order") or ["nse-live"]:
        x = by.get(n)
        if not x or not x.get("enabled", True) or x.get("transport") != "sse":
            continue
        url = os.path.expandvars(str(x.get("url", "")))
        if url and "${" not in url:
            out.append({**x, "url": url})
    return out


async def mcp_call(tool: str, args: dict) -> Optional[dict]:
    """One short-lived SSE session per call (robust; results are cached by `via`)."""
    tok = os.getenv("NSE_MCP_TOKEN", "")
    hd = {"Authorization": "Bearer " + tok} if tok else None
    for x in _mcp_servers():
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            async with sse_client(x["url"], headers=hd) as (rd, wr):
                async with ClientSession(rd, wr) as sess:
                    await sess.initialize()
                    res = await asyncio.wait_for(sess.call_tool(tool, args), float(x.get("timeout_sec", 20)))
            if getattr(res, "isError", False):
                continue
            for b in res.content or []:
                if getattr(b, "text", None):
                    return json.loads(b.text)
        except Exception as e:
            log.warning("mcp {} {} failed: {}", x.get("name"), tool, type(e).__name__)
    return None


_via_cache: Dict[str, tuple] = {}


async def via(tool: str, args: dict, direct: Callable[..., dict], ttl: float) -> dict:
    key = tool + json.dumps(args, sort_keys=True)
    hit = _via_cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    out, err = None, None
    for mode in [m.strip() for m in os.getenv("NSE_VIA", "mcp,direct").split(",")]:
        if mode == "mcp":
            d = await mcp_call(tool, args)
            if d is not None:
                out = {**d, "via": "mcp"}
        elif mode == "direct":
            try:
                out = {**await asyncio.to_thread(direct, **args), "via": "direct"}
            except Exception as e:
                err = e
        if out:
            break
    if out is None:
        raise HTTPException(502, "no NSE data: MCP server unreachable/unset and direct NSE failed"
                                 f" ({type(err).__name__ if err else 'skipped'}). NSE blocks cloud IPs; "
                                 "run the NSE MCP server on an allowed IP (see docs/RAILWAY.md).")
    _via_cache[key] = (time.time(), out)
    return out


def _from_snap(s: Any, expiries: List[str]) -> dict:
    def leg(x: Any, p: str) -> dict:
        return {"ltp": getattr(x, p + "_ltp", None), "oi": getattr(x, p + "_oi", None),
                "oiChg": getattr(x, p + "_oi_change", None), "vol": getattr(x, p + "_volume", None),
                "iv": getattr(x, p + "_iv", None)}
    st = [{"strike": x.strike, "ce": leg(x, "ce"), "pe": leg(x, "pe")} for x in s.strikes]
    ce = sum(v["ce"]["oi"] or 0 for v in st)
    pe = sum(v["pe"]["oi"] or 0 for v in st)
    return {"spot": s.spot, "expiry": s.expiry, "expiries": expiries, "pcr": round(pe / ce, 2) if ce else None,
            "strikes": st, "source": s.source, "asOf": s.timestamp.isoformat()}


def _strip(o: Any) -> Any:
    drop = {"timestamp", "ts", "time", "generated_at", "updated_at"}
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in drop}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


class LoginIn(BaseModel):
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    pin: Optional[str] = None
    totp: Optional[str] = None


class NetIn(BaseModel):
    offline: bool


class AskIn(BaseModel):
    question: str
    context: str = ""


class MemIn(BaseModel):
    layer: str
    model: str = ""
    question: str = ""
    analysis: str
    verdict: str = ""


def build_router(get_engine: Callable[[], Any]) -> APIRouter:
    r = APIRouter(prefix="/api/live", dependencies=[Depends(guard)])
    own: Dict[str, Any] = {"c": None}

    def angel() -> Any:
        eng = get_engine()
        src = getattr(eng, "_source", None) if eng else None
        if getattr(src, "name", "") == "angel_one":
            return src
        if own["c"] is None:
            from backend.brokers.angel_one import AngelOneClient
            own["c"] = AngelOneClient()
        return own["c"]

    def token_info(c: Any) -> dict:
        return {"connected": bool(c.jwt), "jwt_tail": (c.jwt or "")[-6:] or None, "expires_at": _jwt_exp(c.jwt),
                "has_refresh": bool(c.refresh_token), "has_feed": bool(c.feed_token),
                "flow": "loginByPassword(clientcode+PIN+TOTP) -> jwt/refresh/feed"}

    # ---- Angel One token flow ----
    @r.get("/angel/token")
    async def angel_token() -> dict:
        return token_info(angel())

    @r.post("/angel/login")
    async def angel_login(b: LoginIn) -> dict:
        online()
        s, c = get_settings(), angel()
        cid, pin = b.client_id or s.angel_client_id, b.pin or s.angel_pin
        api_key = (b.api_key or s.angel_api_key or "").strip()
        totp = b.totp or (c.generate_totp() if s.angel_totp_secret else "")
        if not (api_key and cid and pin and totp):
            raise HTTPException(400, "need Angel One API key + client_id + PIN + TOTP")
        if hasattr(c, "api_key_override"):
            c.api_key_override = api_key
        if hasattr(c, "client_id_override"):
            c.client_id_override = cid
        try:
            d = (await c._post_raw("/rest/auth/angelbroking/user/v1/loginByPassword",
                                   {"clientcode": cid, "password": pin, "totp": totp}, authed=False)).get("data") or {}
        except Exception as e:
            log.warning("angel login failed: {}", type(e).__name__)
            raise HTTPException(401, "Angel One login failed (check client id / PIN / TOTP)")
        if not d.get("jwtToken"):
            raise HTTPException(401, "Angel One returned no token")
        c.jwt, c.feed_token = d["jwtToken"], d.get("feedToken")
        c.refresh_token = d.get("refreshToken") or c.refresh_token
        c._connected = True
        eng = get_engine()
        if eng is not None:
            eng._source = c
            eng._running = True
            if s.ai_on and eng._ai is None:
                from backend.ai.six_layer_ai import build_ai_client
                eng._ai = build_ai_client(s)
        return token_info(c)

    @r.post("/angel/refresh")
    async def angel_refresh() -> dict:
        online()
        c = angel()
        try:
            await c._refresh()
        except Exception:
            raise HTTPException(401, "token refresh failed; login again")
        return token_info(c)

    # ---- net switch ----
    @r.get("/net")
    async def net_get() -> dict:
        return dict(_net)

    @r.post("/net")
    async def net_set(b: NetIn) -> dict:
        _net["offline"] = b.offline
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / "net.json").write_text(json.dumps(_net))
        return dict(_net)

    @r.get("/nse/ping")
    async def nse_ping() -> dict:
        online()
        return await via("nse_market_status", {}, nse_http.market_status, 10)

    # ---- indices / chains ----
    @r.get("/index/{name}/constituents")
    async def constituents(name: str) -> dict:
        key = name.upper().replace(" ", "")
        if key in BSE_IDX:
            p = Path("config/bse_constituents.json")
            lst = json.loads(p.read_text()).get(key, []) if p.exists() else []
            return {"index": key, "source": "config/bse_constituents.json", "count": len(lst),
                    "stocks": [{"symbol": s} for s in lst]}
        online()
        return await via("nse_constituents", {"index": name}, nse_http.constituents, 20)

    @r.get("/fno-symbols")
    async def fno_symbols() -> dict:
        online()
        return await via("nse_fno_symbols", {}, nse_http.fno_symbols, 3600)

    @r.get("/option-chain/{symbol}")
    async def chain(symbol: str, expiry: Optional[str] = None) -> dict:
        online()
        key = symbol.upper().replace(" ", "")
        if key in BSE_IDX:
            c = angel()
            if not c.jwt:
                raise HTTPException(409, "login to Angel One first: POST /api/live/angel/login")
            try:
                snap = await c.get_option_chain(key, expiry)
            except Exception as e:
                raise HTTPException(502, f"Angel One chain failed ({type(e).__name__})")
            return _from_snap(snap, c.list_expiries(key))
        return await via("nse_option_chain", {"symbol": symbol.upper(), "expiry": expiry}, nse_http.chain, 15)

    @r.get("/candles/{symbol}")
    async def candles(symbol: str, interval: str = "ONE_DAY", years: float = 5, exchange: str = "NSE") -> dict:
        online()
        c, key = angel(), symbol.upper().replace(" ", "")
        if not c.jwt:
            raise HTTPException(409, "login to Angel One first: POST /api/live/angel/login")
        if interval not in LIM:
            raise HTTPException(400, f"interval must be one of {list(LIM)}")
        if key in nse_http.IDX or key in nse_http.CHAIN_IDX or key in BSE_IDX:
            token = await c.get_index_token(key)
            exchange = "BSE" if key in BSE_IDX else "NSE"
        else:
            hits = await c.search_scrip(exchange, symbol.upper())
            pick = next((h for h in hits if str(h.get("tradingsymbol", "")).upper() == f"{key}-EQ"), hits[0] if hits else None)
            token = pick.get("symboltoken") if pick else None
        if not token:
            raise HTTPException(404, f"token not found for {symbol}")
        end, start = datetime.now(IST), datetime.now(IST) - timedelta(days=int(365 * min(max(years, 0.1), 10)))
        step, frames, chunks = timedelta(days=LIM[interval]), [], 0
        while end > start and chunks < 80:
            frm = max(start, end - step)
            df = await c.get_historical(token, exchange, interval, frm, end)
            if not df.empty:
                frames.append(df)
            end, chunks = frm - timedelta(minutes=1), chunks + 1
        if not frames:
            return {"symbol": key, "interval": interval, "candles": [], "truncated": False}
        df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
        return {"symbol": key, "interval": interval, "count": len(df), "truncated": end > start,
                "candles": df.values.tolist()}

    # ---- setups ----
    @r.get("/setups")
    async def setups(day: Optional[str] = None) -> dict:
        if day:
            return {"day": day, "entries": _read_jsonl(DATA / "setups" / f"{_safe_day(day)}.jsonl")}
        eng, live = get_engine(), []
        for i in get_settings().index_list:
            d = eng.latest_decision(i) if eng else None
            if d:
                live.append({"index": i, "decision": d.model_dump(mode="json")})
        return {"live": live, "today": _read_jsonl(DATA / "setups" / f"{_today()}.jsonl")}

    # ---- strategy registry ----
    @r.get("/strategies")
    async def strategies(q: str = "") -> dict:
        rows = strategy_search(q)[:377]
        return {"count": len(rows), "strategies": [
            {"id": f"S{x.id:03d}", "number": x.id, "name": x.name, "family": x.section}
            for x in rows
        ]}

    # ---- AI layers + daily memory ----
    @r.get("/ai/layers")
    async def ai_layers() -> dict:
        from backend.ai.six_layer_ai import LAYERS
        s = get_settings()
        return {"enabled": s.ai_on, "layers": [
            {"id": l["id"], "name": l["name"], "role": l["role"], "model": getattr(s, l["env"], ""),
             "on": bool(getattr(s, l["env"], ""))} for l in LAYERS]}

    @r.post("/ai/ask")
    async def ai_ask(b: AskIn) -> dict:
        online()
        from backend.ai.six_layer_ai import LAYERS, SixLayerAI
        s = get_settings()
        ai = SixLayerAI(s)
        if not ai.available():
            raise HTTPException(503, "no AI transport configured (provider keys / Puter token)")
        system = ("You are one layer of a 6-layer research board for an NSE index-options terminal. Answer the "
                  "question in plain language from your role. Never invent strikes, entries, stop-losses or targets; "
                  "confidence is not a win rate; say clearly when data is missing. Research only, not financial advice.")

        async def one(l: dict) -> dict:
            base = {"id": l["id"], "name": l["name"], "role": l["role"], "model": None}
            try:
                model = await ai._model_for(l)
                if not model:
                    return {**base, "answer": None, "error": "layer disabled (no model set)"}
                msgs = [{"role": "system", "content": system},
                        {"role": "user", "content": "Role: " + l["role"] + "\nContext: " + b.context[:6000]
                         + "\nQuestion: " + b.question[:2000]}]
                tools = [{"type": "web_search"}] if l["web"] and s.web_search_on else None
                res = None
                if ai.transport in ("puter", "auto") and ai.puter.available():
                    res = await ai.puter.chat(msgs, model=model, tools=tools)
                if res is None and ai.transport in ("direct", "auto") and ai.provider.available():
                    res = await ai.provider.chat(model, msgs, tools=tools)
                return {**base, "model": model, "answer": (res or {}).get("content")}
            except Exception as e:
                return {**base, "answer": None, "error": type(e).__name__}

        layers = await asyncio.gather(*[one(l) for l in LAYERS])
        for x in layers:
            if x.get("answer"):
                _append_jsonl(DATA / "ai_memory" / f"{_today()}.jsonl",
                              {"ts": datetime.now(IST).isoformat(timespec="seconds"), "layer": x["id"],
                               "model": x.get("model") or "", "question": b.question, "analysis": x["answer"], "verdict": ""})
        return {"day": _today(), "layers": layers}

    @r.post("/ai/memory")
    async def mem_add(b: MemIn) -> dict:
        _append_jsonl(DATA / "ai_memory" / f"{_today()}.jsonl",
                      {"ts": datetime.now(IST).isoformat(timespec="seconds"), **b.model_dump()})
        return {"saved": True, "day": _today()}

    @r.get("/ai/days")
    async def mem_days() -> dict:
        p = DATA / "ai_memory"
        return {"days": sorted(f.stem for f in p.glob("*.jsonl")) if p.exists() else []}

    @r.get("/ai/memory")
    async def mem_get(day: Optional[str] = None) -> dict:
        d = _safe_day(day or _today())
        return {"day": d, "entries": _read_jsonl(DATA / "ai_memory" / f"{d}.jsonl")}

    @r.get("/ai/memory/export")
    async def mem_export(day: Optional[str] = None) -> Response:
        d = _safe_day(day or _today())
        body = json.dumps(_read_jsonl(DATA / "ai_memory" / f"{d}.jsonl"), ensure_ascii=False, indent=1)
        return Response(body, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="ai-memory-{d}.json"'})

    @r.get("/mcp/status")
    async def mcp_status() -> dict:
        try:
            names = [x.get("name") for x in json.loads(Path(get_settings().mcp_config_path).read_text()).get("servers", [])]
        except Exception:
            names = []
        usable = [x["name"] for x in _mcp_servers()]
        reach = (await mcp_call("nse_market_status", {})) is not None if usable and not _net["offline"] else None
        return {"enabled": get_settings().mcp_on, "servers": names, "live_usable": usable, "reachable": reach,
                "via_order": os.getenv("NSE_VIA", "mcp,direct"), "offline": _net["offline"]}

    return r


async def recorder(get_engine: Callable[[], Any]) -> None:
    """Every 15 s, append a changed decision per index to data/setups/<day>.jsonl."""
    last: Dict[str, str] = {}
    while True:
        try:
            await asyncio.sleep(15)
            eng = get_engine()
            if not eng:
                continue
            for i in get_settings().index_list:
                d = eng.latest_decision(i)
                if not d:
                    continue
                dump = d.model_dump(mode="json")
                h = hashlib.sha1(json.dumps(_strip(dump), sort_keys=True, default=str).encode()).hexdigest()
                if last.get(i) != h:
                    last[i] = h
                    _append_jsonl(DATA / "setups" / f"{_today()}.jsonl",
                                  {"ts": datetime.now(IST).isoformat(timespec="seconds"), "index": i, "decision": dump})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("recorder: {}", e)