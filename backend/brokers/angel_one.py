"""Angel One SmartAPI adapter: REST session, instrument master and SmartStream V2."""

from __future__ import annotations

import asyncio
import json
import platform
import random
import socket
import struct
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

import pandas as pd
import pyotp
import requests
import websockets
from loguru import logger

from backend.brokers.base import AuthError, Capabilities, DataSource, DataSourceError, RateLimitError
from backend.config import get_settings
from backend.models import Snapshot, StrikeSnapshot, Tick

EXCHANGE_SEGMENT = {"NSE_CM": 1, "NSE_FO": 2, "BSE_CM": 3, "BSE_FO": 4}
SEGMENT_EXCHANGE = {"NSE": "NSE_CM", "NFO": "NSE_FO", "BSE": "BSE_CM", "BFO": "BSE_FO"}
INDEX_UNDERLYING = {"NIFTY":"NIFTY","BANKNIFTY":"BANKNIFTY","FINNIFTY":"FINNIFTY","MIDCPNIFTY":"MIDCPNIFTY","SENSEX":"SENSEX","BANKEX":"BANKEX"}
INSTRUMENT_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
AUTH_ERROR_CODES = {"AG8001","AB1010","AG8002","AB2001"}

class _AsyncRateLimiter:
    def __init__(self, rps: float) -> None:
        self.rps=max(0.1,rps); self._min_interval=1.0/self.rps; self._lock=asyncio.Lock(); self._last=0.0
    async def acquire(self) -> None:
        async with self._lock:
            wait=self._min_interval-(time.monotonic()-self._last)
            if wait>0: await asyncio.sleep(wait)
            self._last=time.monotonic()

class AngelOneClient(DataSource):
    name="angel_one"
    capabilities=Capabilities(streaming=True,greeks=True,option_chain=True,historical=True,oi=True,volume=True,bid_ask=True,depth=True,trade_level=False)
    _index_spot_cache: Dict[str,float]={}

    def __init__(self, *, price_scale: float=100.0, api_key: Optional[str]=None) -> None:
        s=get_settings(); super().__init__(rps=s.rate_limit_rps); self.s=s; self.price_scale=price_scale
        self.api_key_override=api_key.strip() if api_key else None
        self.client_id_override=None
        self._limiter=_AsyncRateLimiter(s.rate_limit_rps); self.jwt=None; self.refresh_token=s.angel_refresh_token or None
        self.feed_token=None; self._session=requests.Session(); self._instruments=None; self._all_instruments=None; self._token_index={}; self._index_tokens={}; self._ws=None

    def generate_totp(self)->str:
        if not self.s.angel_totp_secret: raise AuthError("ANGEL_TOTP_SECRET is not set")
        return pyotp.TOTP(self.s.angel_totp_secret).now()

    def _base_headers(self)->Dict[str,str]:
        try: local_ip=socket.gethostbyname(socket.gethostname())
        except Exception: local_ip="127.0.0.1"
        h={"Content-Type":"application/json","Accept":"application/json","X-UserType":"USER","X-SourceID":"WEB","X-ClientLocalIP":local_ip,"X-ClientPublicIP":local_ip,"X-MACAddress":"00:00:00:00:00:00","X-PrivateKey":(self.api_key_override or self.s.angel_api_key)}
        if self.jwt: h["Authorization"]=f"Bearer {self.jwt}"
        return h

    async def connect(self)->None:
        if not self.s.angel_api_key or not self.s.angel_client_id: raise AuthError("ANGEL_API_KEY / ANGEL_CLIENT_ID not configured")
        await self._login(); self._connected=True

    async def _login(self)->None:
        if not (self.s.angel_client_id and self.s.angel_pin and self.s.angel_totp_secret): raise AuthError("Angel One client id / PIN / TOTP secret incomplete")
        data=await self._post_raw("/rest/auth/angelbroking/user/v1/loginByPassword",{"clientcode":self.s.angel_client_id,"password":self.s.angel_pin,"totp":self.generate_totp()},authed=False)
        d=data.get("data") or {}; self.jwt=d.get("jwtToken"); self.refresh_token=d.get("refreshToken") or self.refresh_token; self.feed_token=d.get("feedToken")
        if not self.jwt: raise AuthError(f"login did not return jwtToken: {data}")
        logger.info("angel_one: login ok for {}",self.s.angel_client_id)

    async def _refresh(self)->None:
        if not self.refresh_token: await self._login(); return
        try:
            data=await self._post_raw("/rest/auth/angelbroking/jwt/v1/generateTokens",{"refreshToken":self.refresh_token},authed=False)
            d=data.get("data") or {}; self.jwt=d.get("jwtToken") or self.jwt; self.refresh_token=d.get("refreshToken") or self.refresh_token; self.feed_token=d.get("feedToken") or self.feed_token
        except DataSourceError:
            await self._login()

    async def _ensure_session(self)->None:
        if not self.jwt: await self._login()

    async def _request(self,method:str,path:str,body:Optional[dict]=None,*,retries:int=4,authed:bool=True)->dict:
        await self._limiter.acquire()
        if authed: await self._ensure_session()
        url=self.s.angel_base_url+path; delay=.5; last_err=None
        for _ in range(retries):
            try:
                resp=await asyncio.to_thread(self._session.request,method,url,headers=self._base_headers(),json=body,timeout=15)
                if resp.status_code==429: raise RateLimitError("rate limited")
                if resp.status_code in (401,403): raise AuthError(f"auth error ({resp.status_code})")
                payload=resp.json(); code=str(payload.get("errorCode") or "")
                if code in AUTH_ERROR_CODES: raise AuthError(f"{code}: {payload.get('message')}")
                if not payload.get("status",True):
                    if "token" in str(payload.get("message","")).lower(): raise AuthError(str(payload.get("message")))
                    raise DataSourceError(str(payload.get("message") or payload))
                return payload
            except (AuthError,RateLimitError) as e:
                last_err=e
                if isinstance(e,AuthError): await self._refresh()
            except Exception as e: last_err=e
            await asyncio.sleep(delay); delay=min(delay*2,8)
        raise DataSourceError(f"{path} failed after {retries} attempts: {last_err}")

    async def _post_raw(self,path:str,body:dict,*,authed:bool)->dict:
        await self._limiter.acquire(); resp=await asyncio.to_thread(self._session.post,self.s.angel_base_url+path,headers=self._base_headers(),json=body,timeout=15)
        if resp.status_code>=400: raise DataSourceError(f"{path} http {resp.status_code}: {resp.text[:200]}")
        payload=resp.json()
        if not payload.get("status",True): raise AuthError(f"{path}: {payload.get('message') or payload}")
        return payload

    async def get_ltp(self,symbol:str,token:str,exchange:str="NSE")->Optional[float]:
        d=(await self._request("POST","/rest/secure/angelbroking/order/v1/getLTP",{"exchange":exchange,"symboltoken":token,"tradingSymbol":symbol})).get("data") or {}
        return float(d["ltp"]) if d.get("ltp") is not None else None

    async def get_quote(self,symbol:str,token:str,exchange:str="NSE")->Optional[Tick]:
        if token.upper()==symbol.upper():
            resolved=await self.get_index_token(symbol)
            if resolved:
                token=resolved
                exchange="BSE" if symbol.upper().replace(" ","") in {"SENSEX","BANKEX"} else "NSE"
        ticks=await self.get_market_data("FULL",[{"exchange":exchange,"token":token,"symbol":symbol}])
        return ticks[0] if ticks else None

    async def get_market_data(self,mode:str,tokens:List[Dict[str,str]])->List[Tick]:
        by:Dict[str,List[str]]={}
        for t in tokens: by.setdefault(t.get("exchange","NSE"),[]).append(t["token"])
        data=(await self._request("POST","/rest/secure/angelbroking/market/v1/quote",{"mode":mode.upper(),"exchangeTokens":by})).get("data") or {}
        return [self._row_to_tick(r) for r in data.get("fetched",[])]

    async def get_option_greek(self,name:str,expiry:str)->List[Dict[str,Any]]:
        p=await self._request("POST","/rest/secure/angelbroking/marketData/v1/optionGreek",{"name":INDEX_UNDERLYING.get(name.upper(),name.upper()),"expirydate":expiry})
        return list(p.get("data") or [])

    async def get_historical(self,token:str,exchange:str,interval:str,frm:datetime,to:datetime)->pd.DataFrame:
        body={"exchange":exchange,"symboltoken":token,"interval":interval,"fromdate":frm.strftime("%Y-%m-%d %H:%M"),"todate":to.strftime("%Y-%m-%d %H:%M")}
        rows=(await self._request("POST","/rest/secure/angelbroking/historical/v1/getCandleData",body)).get("data") or []
        return pd.DataFrame(rows,columns=["timestamp","open","high","low","close","volume"])

    async def search_scrip(self,exchange:str,query:str)->List[Dict[str,Any]]:
        p=await self._request("POST","/rest/secure/angelbroking/order/v1/searchScrip",{"exchange":exchange,"searchscrip":query}); return list(p.get("data") or [])

    async def load_instruments(self,force:bool=False)->None:
        if self._instruments is not None and not force: return
        def dl()->pd.DataFrame:
            r=requests.get(INSTRUMENT_MASTER_URL,timeout=60); r.raise_for_status(); return pd.DataFrame(r.json())
        df=await asyncio.to_thread(dl)
        self._all_instruments=df
        self._instruments=df[df["exch_seg"].isin(["NFO","BFO"])] if "exch_seg" in df else df; idx={}
        index_tokens={}
        for _,row in df.iterrows():
            try:
                name=str(row.get("name","")).upper(); exp=str(row.get("expiry","")).upper(); sym=str(row.get("symbol","")).upper(); token=str(row.get("token","")); strike=float(row.get("strike",0))/100; opt="CE" if sym.endswith("CE") else ("PE" if sym.endswith("PE") else "")
                if opt: idx[(name,exp,strike,opt)]=token
            except Exception: continue
        self._token_index=idx
        if self._all_instruments is not None:
            for _,row in self._all_instruments.iterrows():
                try:
                    seg=str(row.get("exch_seg","")).upper()
                    name=str(row.get("name","")).upper().replace(" ","")
                    symbol=str(row.get("symbol","")).upper().replace(" ","")
                    token=str(row.get("token",""))
                    if seg in {"NSE","BSE"} and name in {x.replace(" ","") for x in INDEX_UNDERLYING.values()}:
                        index_tokens[name]=(token,seg)
                    elif seg in {"NSE","BSE"} and symbol in {"NIFTY50","NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY","SENSEX","BANKEX"}:
                        index_tokens[symbol]=(token,seg)
                except Exception: continue
        self._index_tokens=index_tokens

    async def get_index_token(self,index:str)->Optional[str]:
        await self.load_instruments()
        item=self._index_tokens.get(index.upper().replace(" ",""))
        return item[0] if item else None

    def resolve_token(self,index:str,strike:float,option_type:str,expiry:str)->Optional[str]:
        return self._token_index.get((INDEX_UNDERLYING.get(index.upper(),index.upper()),expiry.upper(),float(strike),option_type.upper()))

    async def get_option_chain(self,index:str,expiry:Optional[str]=None)->Snapshot:
        await self.load_instruments(); idx=index.upper()
        if not expiry:
            ex=self.list_expiries(idx)
            if not ex: raise DataSourceError(f"no expiry found for {idx}")
            expiry=ex[0]
        spot=await self._index_spot(idx); step=50.; atm=round(spot/step)*step
        sm={}
        tokens=[]
        for i in range(-12,13):
            k=atm+i*step; sm[k]=StrikeSnapshot(strike=k,is_atm=(k==atm))
            for opt in ("CE","PE"):
                tok=self.resolve_token(idx,k,opt,expiry)
                if tok: tokens.append({"exchange":"NFO","token":tok,"symbol":f"{idx}{expiry}{opt}"})
        if tokens:
            for t in await self.get_market_data("FULL",tokens): self._apply_tick_to_strike(sm,t)
        try:
            for g in await self.get_option_greek(idx,expiry):
                row=sm.get(float(g.get("strikePrice",0))); opt=str(g.get("optionType","")).lower()
                if row: 
                    for n in ("iv","delta","gamma","theta","vega"): setattr(row,f"{opt}_{n}",_f(g.get("impliedVolatility" if n=="iv" else n)))
        except DataSourceError as e: logger.warning("angel_one: greek feed unavailable ({})",e)
        return Snapshot(index=idx,expiry=expiry,spot=spot,atm_strike=atm,strikes=sorted(sm.values(),key=lambda s:s.strike),source="angel_one",timestamp=datetime.now(timezone.utc))

    async def _index_spot(self,index:str)->float:
        key=index.upper()
        cached=self._index_spot_cache.get(key,0.0)
        if cached: return cached
        token=await self.get_index_token(key)
        if token:
            try:
                exchange="BSE" if key.replace(" ","") in {"SENSEX","BANKEX"} else "NSE"
                ticks=await self.get_market_data("FULL",[{"exchange":exchange,"token":token,"symbol":key}])
                if ticks and ticks[0].ltp:
                    self._index_spot_cache[key]=ticks[0].ltp
                    return ticks[0].ltp
            except Exception as e:
                logger.warning("angel_one: index spot unavailable for {} ({})",key,e)
        return 0.0

    def list_expiries(self,index:str)->List[str]:
        if self._instruments is None or "name" not in self._instruments: return []
        name=INDEX_UNDERLYING.get(index.upper(),index.upper()); sub=self._instruments[self._instruments["name"].astype(str).str.upper()==name]
        return sorted({str(e).upper() for e in sub.get("expiry",pd.Series(dtype=str)).dropna()})[:3]

    def _apply_tick_to_strike(self,strikes:Dict[float,StrikeSnapshot],tick:Tick)->None:
        sym=tick.symbol.upper(); opt="CE" if sym.endswith("CE") else ("PE" if sym.endswith("PE") else None)
        if not opt:return
        digits="".join(ch for ch in sym[-12:] if ch.isdigit())
        if not digits:return
        strike=float(digits)/100. if len(digits)>5 else float(digits)
        row=next((v for k,v in strikes.items() if abs(k-strike)<.5),None)
        if row:
            setattr(row,f"{opt.lower()}_ltp",tick.ltp); setattr(row,f"{opt.lower()}_oi",tick.oi); setattr(row,f"{opt.lower()}_volume",tick.volume); setattr(row,f"{opt.lower()}_bid",tick.bid); setattr(row,f"{opt.lower()}_ask",tick.ask)

    def _row_to_tick(self,row:Dict[str,Any])->Tick:
        return Tick(symbol=str(row.get("tradingSymbol") or row.get("symbol") or ""),exchange=str(row.get("exchange") or "NSE"),token=str(row.get("symbolToken") or row.get("token") or ""),ltp=_f(row.get("ltp")) or 0.,open=_f(row.get("open")),high=_f(row.get("high")),low=_f(row.get("low")),close=_f(row.get("close")),volume=_i(row.get("volume")),oi=_i(row.get("opnInterest")),bid=_f(row.get("bidPrice") or row.get("bestBidPrice")),ask=_f(row.get("offerPrice") or row.get("bestAskPrice")),bid_qty=_i(row.get("bidQty")),ask_qty=_i(row.get("offerQty")),source="angel_one")

    async def subscribe(self,tokens:List[Dict[str,str]],on_tick)->None:
        if self._ws is None: self._ws=AngelOneWebSocket(self,on_tick,price_scale=self.price_scale); await self._ws.start()
        await self._ws.subscribe(tokens)

    async def unsubscribe(self,tokens:List[Dict[str,str]])->None:
        if self._ws: await self._ws.unsubscribe(tokens)

    async def close(self)->None:
        if self._ws: await self._ws.stop(); self._ws=None
        self._connected=False

SMART_STREAM_URL="wss://smartapisocket.angelone.in/smart-stream"
MODE_LTP,MODE_QUOTE,MODE_SNAPQUOTE=1,2,3
_FRAME_MIN={MODE_LTP:51,MODE_QUOTE:123,MODE_SNAPQUOTE:379}

class AngelOneWebSocket:
    def __init__(self,client:AngelOneClient,on_tick:Callable[[Tick],Awaitable[None]],*,price_scale:float=100.,max_backoff:float=30.,mode:int=MODE_SNAPQUOTE,heartbeat_s:float=10.)->None:
        self.client=client; self.on_tick=on_tick; self.price_scale=price_scale; self.max_backoff=max_backoff; self.mode=mode; self.heartbeat_s=heartbeat_s
        self._subs={}; self._ws=None; self._task=None; self._stop=asyncio.Event(); self._send_lock=asyncio.Lock(); self._last_msg=0.; self.frames_ok=0; self.frames_dropped=0
    async def start(self):
        if self._task and not self._task.done(): return
        self._stop.clear(); self._task=asyncio.create_task(self._run(),name="angel_one_ws")
    async def stop(self):
        self._stop.set()
        if self._ws:
            try: await self._ws.close()
            except Exception: pass
        if self._task:
            self._task.cancel()
            try: await self._task
            except BaseException: pass
        self._task=None; self._ws=None
    @staticmethod
    def _exchange_type(exchange:str)->int:
        return EXCHANGE_SEGMENT.get(SEGMENT_EXCHANGE.get(exchange.upper(),exchange.upper()),1)
    def _token_list(self,tokens):
        grouped={}
        for t in tokens: grouped.setdefault(self._exchange_type(t.get("exchange","NSE")),[]).append(str(t["token"]))
        return [{"exchangeType":k,"tokens":v} for k,v in grouped.items()]
    async def subscribe(self,tokens):
        for t in tokens:self._subs[(self._exchange_type(t.get("exchange","NSE")),str(t["token"]))]=dict(t)
        if self._ws: await self._send_action(1,tokens)
    async def unsubscribe(self,tokens):
        for t in tokens:self._subs.pop((self._exchange_type(t.get("exchange","NSE")),str(t["token"])),None)
        if self._ws: await self._send_action(0,tokens)
    async def _send_action(self,action,tokens):
        if not tokens or not self._ws:return
        msg={"correlationID":uuid.uuid4().hex[:10],"action":action,"params":{"mode":self.mode,"tokenList":self._token_list(tokens)}}
        try:
            async with self._send_lock: await self._ws.send(json.dumps(msg))
        except Exception as e: logger.warning("angel_one ws: send failed ({})",e)
    def _ws_headers(self):
        return {"Authorization":self.client.jwt or "","x-api-key":(self.client.api_key_override or self.client.s.angel_api_key),"x-client-code":(self.client.client_id_override or self.client.s.angel_client_id),"x-feed-token":self.client.feed_token or ""}
    async def _connect(self):
        h=self._ws_headers()
        try:return await websockets.connect(SMART_STREAM_URL,additional_headers=h,ping_interval=None,max_size=2**22)
        except TypeError:return await websockets.connect(SMART_STREAM_URL,extra_headers=h,ping_interval=None,max_size=2**22)
    async def _run(self):
        backoff=1.
        while not self._stop.is_set():
            try:
                await self.client._ensure_session()
                if not self.client.feed_token: await self.client._refresh()
                self._ws=await self._connect(); backoff=1.; self._last_msg=time.monotonic()
                if self._subs: await self._send_action(1,list(self._subs.values()))
                hb=asyncio.create_task(self._heartbeat())
                try: await self._recv_loop()
                finally: hb.cancel()
            except asyncio.CancelledError: raise
            except AuthError:
                try: await self.client._login()
                except Exception: pass
            except Exception as e:
                if "401" in str(e) or "403" in str(e):
                    try: await self.client._refresh()
                    except Exception: pass
            finally:
                if self._ws:
                    try: await self._ws.close()
                    except Exception: pass
                    self._ws=None
            if self._stop.is_set(): break
            delay=min(backoff,self.max_backoff)*(0.8+0.4*random.random())
            try: await asyncio.wait_for(self._stop.wait(),timeout=delay)
            except asyncio.TimeoutError: pass
            backoff=min(backoff*2,self.max_backoff)
    async def _heartbeat(self):
        while True:
            await asyncio.sleep(self.heartbeat_s)
            if self._ws is None:return
            if time.monotonic()-self._last_msg>self.heartbeat_s*3:
                await self._ws.close(); return
            try:
                async with self._send_lock: await self._ws.send("ping")
            except Exception:return
    async def _recv_loop(self):
        async for raw in self._ws:
            self._last_msg=time.monotonic()
            if isinstance(raw,str):
                if raw.strip().lower()=="pong":continue
                try:
                    obj=json.loads(raw)
                    if isinstance(obj,dict) and obj.get("errorCode") and str(obj["errorCode"]) in AUTH_ERROR_CODES: raise AuthError(str(obj))
                except json.JSONDecodeError: pass
                continue
            tick=self._parse_binary(raw)
            if tick is None:self.frames_dropped+=1; continue
            self.frames_ok+=1; self._cache_index_spot(tick)
            try: await self.on_tick(tick)
            except Exception as e: logger.error("angel_one ws: on_tick handler error ({})",e)
    def _cache_index_spot(self,tick):
        meta=self._subs.get((self._exchange_type(tick.exchange),tick.token))
        if meta and meta.get("index") and tick.ltp: AngelOneClient._index_spot_cache[meta["index"].upper()]=tick.ltp
    def _parse_binary(self,data:bytes)->Optional[Tick]:
        try:
            if not isinstance(data,(bytes,bytearray)) or len(data)<_FRAME_MIN[MODE_LTP]:return None
            mode=data[0]; need=_FRAME_MIN.get(mode)
            if need is None or len(data)<need:return None
            ex_type=data[1]; token=data[2:27].split(b"\x00",1)[0].decode("utf-8","ignore"); sc=self.price_scale
            def q(off):return struct.unpack_from("<q",data,off)[0]
            def price(off):return q(off)/sc
            exchange=next((k for k,v in SEGMENT_EXCHANGE.items() if EXCHANGE_SEGMENT.get(v)==ex_type),"NSE")
            meta=self._subs.get((ex_type,token),{}); ltp=price(43)
            if ltp<=0:return None
            kw={"symbol":meta.get("symbol",token),"exchange":exchange,"token":token,"ltp":ltp,"source":"angel_one"}
            if mode>=MODE_QUOTE: kw.update(volume=q(67),open=price(91),high=price(99),low=price(107),close=price(115))
            if mode==MODE_SNAPQUOTE:
                kw["oi"]=q(131); bid=ask=None; bq=aq=None
                for i in range(10):
                    off=147+i*20; flag=struct.unpack_from("<h",data,off)[0]; qty=q(off+2); px=q(off+10)/sc
                    if px<=0:continue
                    if flag==1 and bid is None:bid,bq=px,qty
                    elif flag==0 and ask is None:ask,aq=px,qty
                kw.update(bid=bid,ask=ask,bid_qty=bq,ask_qty=aq)
            return Tick(**kw)
        except Exception as e:
            logger.debug("angel_one ws: dropped bad frame ({})",e); return None

def _f(v:Any)->Optional[float]:
    if v is None or v=="":return None
    try:return float(v)
    except (TypeError,ValueError):return None

def _i(v:Any)->Optional[int]:
    f=_f(v); return int(f) if f is not None else None
