"""Small NSE public-data adapter used by the live terminal.

NSE may reject cloud/datacenter IPs. The caller handles MCP-first fallback.
This module deliberately exposes only read-only market-data operations.
"""

from __future__ import annotations

from typing import Any

import requests

BASE = "https://www.nseindia.com"
HEADERS = {
    "accept": "application/json,text/plain,*/*",
    "accept-language": "en-IN,en;q=0.9",
    "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "referer": "https://www.nseindia.com/",
}

IDX = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}
CHAIN_IDX = set(IDX)
_INDEX_NAMES = {
    "NIFTY": "NIFTY 50",
    "BANKNIFTY": "NIFTY BANK",
    "FINNIFTY": "NIFTY FINANCIAL SERVICES",
    "MIDCPNIFTY": "NIFTY MID SELECT",
    "NIFTYNXT50": "NIFTY NEXT 50",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(BASE, timeout=12)
    return s


def _get(path: str, **params: Any) -> dict:
    s = _session()
    r = s.get(BASE + path, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def market_status() -> dict:
    d = _get("/api/marketStatus")
    return {"marketState": d.get("marketState", []), "marketcap": d.get("marketcap", {})}


def constituents(index: str) -> dict:
    key = index.upper().replace(" ", "")
    name = _INDEX_NAMES.get(key, index.upper())
    d = _get("/api/equity-stockIndices", index=name)
    rows = d.get("data") or []
    stocks = []
    for x in rows:
        stocks.append({
            "symbol": x.get("symbol"),
            "ltp": x.get("lastPrice"),
            "pct": x.get("pChange"),
            "vol": x.get("totalTradedVolume"),
        })
    return {"index": key, "count": len(stocks), "stocks": stocks, "source": "nse_public"}


def fno_symbols() -> dict:
    # The public equity index feed is more stable than NSE's changing F&O
    # discovery endpoints. Keep this read-only list intentionally conservative.
    d = _get("/api/equity-stockIndices", index="NIFTY 500")
    symbols = [x.get("symbol") for x in (d.get("data") or []) if x.get("symbol")]
    return {"symbols": symbols, "source": "nse_public"}


def _leg(row: dict, prefix: str) -> dict:
    return {
        "ltp": row.get(f"{prefix}LastTradedPrice"),
        "oi": row.get(f"{prefix}OpenInterest"),
        "oiChg": row.get(f"{prefix}ChangeinOpenInterest"),
        "vol": row.get(f"{prefix}TotalTradedVolume"),
        "iv": row.get(f"{prefix}ImpliedVolatility"),
    }


def chain(symbol: str, expiry: str | None = None) -> dict:
    key = symbol.upper().replace(" ", "")
    index_symbol = _INDEX_NAMES.get(key, symbol.upper())
    endpoint = "/api/option-chain-indices" if key in CHAIN_IDX else "/api/option-chain-equities"
    d = _get(endpoint, symbol=index_symbol)
    records = d.get("records") or {}
    all_exp = records.get("expiryDates") or []
    selected = expiry or (all_exp[0] if all_exp else None)
    rows = []
    for row in records.get("data") or []:
        if selected and row.get("expiryDate") != selected:
            continue
        strike = row.get("strikePrice")
        if strike is None:
            continue
        rows.append({
            "strike": strike,
            "ce": _leg(row, "CE-"),
            "pe": _leg(row, "PE-"),
        })
    ce = sum((x["ce"].get("oi") or 0) for x in rows)
    pe = sum((x["pe"].get("oi") or 0) for x in rows)
    return {
        "spot": records.get("underlyingValue"),
        "expiry": selected,
        "expiries": all_exp,
        "pcr": round(pe / ce, 2) if ce else None,
        "strikes": rows,
        "source": "nse_public",
    }
