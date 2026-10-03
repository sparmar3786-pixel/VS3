"""Data-source factory and graceful fallback orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pandas as pd
from loguru import logger

from backend.brokers.base import Capabilities, DataSource, DataSourceError
from backend.config import get_settings
from backend.models import Snapshot, Tick

def build_source(name: str) -> DataSource:
    key=name.strip().lower()
    if key in {"angel_one","angel","smartapi"}:
        from backend.brokers.angel_one import AngelOneClient
        return AngelOneClient()
    if key in {"nse_public","nse","public"}:
        from backend.brokers.nse_public import NSEPublicSource
        return NSEPublicSource()
    if key in {"mcp","nse_mcp"}:
        from backend.mcp.mcp_client import MCPSource
        return MCPSource()
    if key in {"demo","mock","synthetic"}:
        from backend.brokers.demo import DemoSource
        return DemoSource()
    raise DataSourceError(f"unknown data source: {name!r}")

class FallbackSource(DataSource):
    name="fallback"

    def __init__(self,sources:List[DataSource])->None:
        super().__init__(rps=1.0); self.sources=sources
        self.capabilities=Capabilities(
            streaming=any(x.capabilities.streaming for x in sources),
            greeks=any(x.capabilities.greeks for x in sources),
            option_chain=any(x.capabilities.option_chain for x in sources),
            historical=any(x.capabilities.historical for x in sources),
            oi=any(x.capabilities.oi for x in sources),
            volume=any(x.capabilities.volume for x in sources),
            bid_ask=any(x.capabilities.bid_ask for x in sources),
            depth=any(x.capabilities.depth for x in sources),
            trade_level=any(x.capabilities.trade_level for x in sources))
        self._active:Optional[DataSource]=None

    async def connect(self)->None:
        for s in self.sources:
            try:
                await s.connect(); self._active=s
                logger.info("fallback: active source = {}",s.name); break
            except Exception as e: logger.warning("fallback: {} unavailable ({})",s.name,e)
        else: raise DataSourceError("no data source could connect")
        self._connected=True

    async def close(self)->None:
        for s in self.sources:
            try: await s.close()
            except Exception: pass
        self._connected=False

    async def _try(self,method:str,*args,**kwargs):
        errors=[]
        ordered=([self._active] if self._active else [])+[s for s in self.sources if s is not self._active]
        for s in ordered:
            if not getattr(s,"connected",False):
                try: await s.connect()
                except Exception as e: errors.append(f"{s.name}:connect:{e}"); continue
            fn=getattr(s,method,None)
            if fn is None: continue
            try:
                result=await fn(*args,**kwargs)
                if result is not None:
                    self._active=s; return result
            except Exception as e: errors.append(f"{s.name}:{method}:{e}")
        if errors: logger.warning("fallback {} failed everywhere: {}",method,errors[:3])
        return None

    async def get_ltp(self,symbol:str,token:str,exchange:str="NSE")->Optional[float]:
        return await self._try("get_ltp",symbol,token,exchange)

    async def get_quote(self,symbol:str,token:str,exchange:str="NSE")->Optional[Tick]:
        return await self._try("get_quote",symbol,token,exchange)

    async def get_option_chain(self,index:str,expiry:Optional[str]=None)->Snapshot:
        snap=await self._try("get_option_chain",index,expiry)
        if snap is None: raise DataSourceError(f"no source could supply option chain for {index}")
        return snap

    async def get_historical(self,token:str,exchange:str,interval:str,frm:datetime,to:datetime)->pd.DataFrame:
        for s in self.sources:
            try:
                df=await s.get_historical(token,exchange,interval,frm,to)
                if df is not None and not df.empty:return df
            except Exception: continue
        return pd.DataFrame(columns=["timestamp","open","high","low","close","volume"])

    async def subscribe(self,tokens,on_tick)->None:
        ordered=([self._active] if self._active else [])+self.sources
        seen=set()
        for s in ordered:
            if s and id(s) not in seen and s.capabilities.streaming:
                seen.add(id(s))
                try:
                    await s.subscribe(tokens,on_tick); self._active=s; return
                except Exception as e: logger.warning("fallback subscribe {} failed: {}",s.name,e)

    def list_expiries(self,index:str)->List[str]:
        for s in self.sources:
            try:
                exps=s.list_expiries(index)
                if exps:return exps
            except Exception: continue
        return []

    def resolve_token(self,index:str,strike:float,option_type:str,expiry:str)->Optional[str]:
        for s in self.sources:
            try:
                tok=s.resolve_token(index,strike,option_type,expiry)
                if tok:return tok
            except Exception: continue
        return None

def get_data_source()->DataSource:
    s=get_settings(); order=s.fallback_order or [s.data_source]
    if s.data_source not in order: order=[s.data_source]+order
    sources=[]
    for name in order:
        try: sources.append(build_source(name))
        except DataSourceError as e: logger.warning("factory: skipping {} ({})",name,e)
    if not sources: raise DataSourceError("no live data source configured")
    return sources[0] if len(sources)==1 else FallbackSource(sources)
