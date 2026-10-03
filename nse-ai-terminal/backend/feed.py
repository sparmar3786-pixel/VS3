import asyncio
import json
import math
import random
import time
from typing import AsyncIterator

import config

BASE_PRICES={"NIFTY50":24690.0,"BANKNIFTY":52317.0,"FINNIFTY":23482.0,"MIDCPNIFTY":12345.0,"SENSEX":81742.0,
             "RELIANCE":2950.0,"TCS":4100.0,"HDFCBANK":1750.0,"INFY":1850.0}
PRICE_KEYS=("last_price","ltp","price","lastPrice","last_traded_price")

class SimFeed:
    def __init__(self,symbols):
        self.symbols=symbols; self.px={s:BASE_PRICES.get(s,1000.0) for s in symbols}
        self.vol={s:0.0004 for s in symbols}; self.drift={s:0.0 for s in symbols}
    def _step(self,s):
        if random.random()<0.01:self.vol[s]=random.choice([0.0002,0.0004,0.0009])
        if random.random()<0.01:self.drift[s]=random.choice([-0.00008,0.0,0.00008])
        r=self.drift[s]+random.gauss(0,self.vol[s]); self.px[s]=max(1.0,self.px[s]*math.exp(r))
        return round(self.px[s],2),random.randint(10,500)
    def history_ticks(self,symbol,n_candles,sec):
        now=time.time(); start=now-n_candles*sec; out=[]
        for i in range(n_candles*4):
            ts=start+i*sec/4; p,v=self._step(symbol); out.append((symbol,p,v,ts))
        return out
    async def stream(self):
        while True:
            for s in self.symbols:
                p,v=self._step(s); yield(s,p,v,time.time())
            await asyncio.sleep(0.25)

def find_price(obj):
    if isinstance(obj,dict):
        for k in PRICE_KEYS:
            if k in obj:
                try:return float(obj[k]),float(obj.get("volume",0) or 0)
                except (TypeError,ValueError):pass
        for v in obj.values():
            r=find_price(v)
            if r:return r
    elif isinstance(obj,list):
        for v in obj:
            r=find_price(v)
            if r:return r
    return None

class MCPFeed:
    def __init__(self,symbols):self.symbols=symbols
    @staticmethod
    def _parse(result):
        for part in result.content:
            text=getattr(part,"text",None)
            if not text:continue
            try:d=json.loads(text)
            except Exception:continue
            r=find_price(d)
            if r:return r
        return None
    async def _session_stream(self):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        headers={"Authorization":f"Bearer {config.MCP_AUTH_TOKEN}"} if config.MCP_AUTH_TOKEN else None
        async with streamablehttp_client(config.MCP_SERVER_URL,headers=headers) as (r,w,_):
            async with ClientSession(r,w) as session:
                await session.initialize()
                while True:
                    t0=time.time()
                    for s in self.symbols:
                        inst=config.MCP_INSTRUMENT_FMT.format(symbol=s)
                        try:
                            res=await asyncio.wait_for(session.call_tool(config.MCP_QUOTE_TOOL,{config.MCP_SYMBOL_ARG:inst}),10)
                        except asyncio.TimeoutError:
                            print(f"[mcp] {s}: timeout"); continue
                        parsed=self._parse(res)
                        if parsed:yield(s,parsed[0],parsed[1],time.time())
                    await asyncio.sleep(max(0.0,config.MCP_POLL_SECONDS-(time.time()-t0)))
    async def stream(self):
        delay=1.0
        while True:
            try:
                async for tick in self._session_stream():
                    delay=1.0; yield tick
            except asyncio.CancelledError:raise
            except Exception as e:print(f"[mcp] connection lost: {e!r}; retry in {delay:.0f}s")
            await asyncio.sleep(delay+random.random()); delay=min(delay*2,30.0)

def make_feed(symbols):
    if config.FEED_MODE=="mcp" and config.MCP_SERVER_URL:return MCPFeed(symbols)
    return SimFeed(symbols)