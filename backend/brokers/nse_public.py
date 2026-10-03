"""Optional public-NSE fallback adapter.

Reads NSE's public option-chain JSON as a throttled, non-streaming fallback.
Prefer licensed/reliable broker feeds for real-time use.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from backend.brokers.base import Capabilities, DataSource, DataSourceError
from backend.config import get_settings
from backend.models import Snapshot, StrikeSnapshot, Tick

_BASE="https://www.nseindia.com"
_INDEX_SYMBOL={"NIFTY":"NIFTY","BANKNIFTY":"BANKNIFTY","FINNIFTY":"FINNIFTY","MIDCPNIFTY":"MIDCPNIFTY"}
_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept":"application/json, text/plain, */*","Accept-Language":"en-US,en;q=0.9",
    "Referer":"https://www.nseindia.com/option-chain","Connection":"keep-alive",
}

class NSEPublicSource(DataSource):
    name="nse_public"
    capabilities=Capabilities(streaming=False,greeks=False,option_chain=True,historical=False,oi=True,volume=True,bid_ask=False)

    def __init__(self)->None:
        s=get_settings(); super().__init__(rps=min(s.rate_limit_rps,.5))
        self._session=requests.Session(); self._bootstrapped=False; self._last=0.

    async def connect(self)->None:
        await self._bootstrap(); self._connected=True

    async def close(self)->None:
        self._session.close(); self._connected=False

    async def _throttle(self)->None:
        wait=(1./self.rps)-(time.monotonic()-self._last)
        if wait>0: await asyncio.sleep(wait)
        self._last=time.monotonic()

    async def _bootstrap(self)->None:
        if self._bootstrapped:return
        await self._throttle()
        try:
            r=await asyncio.to_thread(self._session.get,_BASE,headers=_HEADERS,timeout=10)
            if r.status_code>=400: raise DataSourceError(f"NSE bootstrap http {r.status_code}")
            await self._throttle()
            r=await asyncio.to_thread(self._session.get,_BASE+"/option-chain",headers=_HEADERS,timeout=10)
            if r.status_code>=400: raise DataSourceError(f"NSE option-chain bootstrap http {r.status_code}")
        except DataSourceError: raise
        except Exception as e: raise DataSourceError(f"NSE bootstrap failed: {e}")
        self._bootstrapped=True

    async def _get_json(self,path:str)->dict:
        await self._bootstrap(); await self._throttle()
        try:
            resp=await asyncio.to_thread(self._session.get,_BASE+path,headers=_HEADERS,timeout=12)
            if resp.status_code!=200: raise DataSourceError(f"NSE {path} http {resp.status_code}")
            return resp.json()
        except DataSourceError:
            self._bootstrapped=False
            await self._bootstrap(); await self._throttle()
            resp=await asyncio.to_thread(self._session.get,_BASE+path,headers=_HEADERS,timeout=12)
            if resp.status_code!=200: raise DataSourceError(f"NSE {path} http {resp.status_code} after retry")
            return resp.json()

    async def get_ltp(self,symbol:str,token:str,exchange:str="NSE")->Optional[float]:
        return (await self.get_option_chain(symbol)).spot

    async def get_quote(self,symbol:str,token:str,exchange:str="NSE")->Optional[Tick]:
        snap=await self.get_option_chain(symbol)
        return Tick(symbol=symbol,exchange=exchange,token=token,ltp=snap.spot,source="nse_public") if snap.spot is not None else None

    async def get_option_chain(self,index:str,expiry:Optional[str]=None)->Snapshot:
        idx=index.upper(); sym=_INDEX_SYMBOL.get(idx)
        if not sym: raise DataSourceError(f"nse_public does not serve {idx} (BSE index)")
        data=await self._get_json(f"/api/option-chain-indices?symbol={sym}")
        records=data.get("records") or {}; rows=records.get("data") or []
        underlying=float(records.get("underlyingValue") or 0.)
        strikes:Dict[float,StrikeSnapshot]={}
        for row in rows:
            if expiry and row.get("expiryDate","")!=expiry: continue
            k=float(row.get("strikePrice",0)); s=strikes.setdefault(k,StrikeSnapshot(strike=k))
            ce=row.get("CE") or {}; pe=row.get("PE") or {}
            if ce:
                s.ce_ltp=_f(ce.get("lastPrice")); s.ce_oi=_i(ce.get("openInterest")); s.ce_oi_change=_i(ce.get("changeinOpenInterest")); s.ce_volume=_i(ce.get("totalTradedVolume")); s.ce_iv=_f(ce.get("impliedVolatility"))
            if pe:
                s.pe_ltp=_f(pe.get("lastPrice")); s.pe_oi=_i(pe.get("openInterest")); s.pe_oi_change=_i(pe.get("changeinOpenInterest")); s.pe_volume=_i(pe.get("totalTradedVolume")); s.pe_iv=_f(pe.get("impliedVolatility"))
        if not strikes: raise DataSourceError("NSE option chain returned no strikes")
        step=_detect_step(sorted(strikes)); atm=round(underlying/step)*step if underlying else None
        for s in strikes.values(): s.is_atm=atm is not None and abs(s.strike-atm)<.5
        return Snapshot(index=idx,expiry=expiry or "",spot=underlying or None,atm_strike=atm,strikes=sorted(strikes.values(),key=lambda x:x.strike),prev_close=_f(records.get("underlyingValue")),source="nse_public",timestamp=datetime.now(timezone.utc))

    def list_expiries(self,index:str)->List[str]:
        return []

def _detect_step(strikes:List[float])->float:
    diffs=[b-a for a,b in zip(strikes,strikes[1:]) if b-a>0]
    return min(diffs) if diffs else 50.

def _f(v)->Optional[float]:
    try:return float(v) if v not in (None,"") else None
    except (TypeError,ValueError):return None

def _i(v)->Optional[int]:
    try:return int(float(v)) if v not in (None,"") else None
    except (TypeError,ValueError):return None
