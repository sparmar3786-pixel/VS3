"""Groww Trading API adapter.

Read-only market-data adapter for VS3. Credentials are supplied per request or
through GROWW_ACCESS_TOKEN on the server; they are never embedded in Flutter.
"""
from __future__ import annotations
from typing import Any
import requests
BASE = "https://api.groww.in/v1"
class GrowwError(RuntimeError): pass
class GrowwClient:
    def __init__(self, access_token: str = ""):
        self.access_token=access_token.strip(); self.timeout=10
    @property
    def connected(self): return bool(self.access_token)
    def _get(self,path:str,params:dict[str,Any])->dict:
        if not self.access_token: raise GrowwError("Groww access token is not configured")
        r=requests.get(BASE+path,params=params,headers={"Accept":"application/json","Authorization":"Bearer "+self.access_token,"X-API-VERSION":"1.0"},timeout=self.timeout)
        r.raise_for_status(); d=r.json()
        if d.get("status")!="SUCCESS": raise GrowwError(str(d.get("error") or d)[:500])
        return d
    def quote(self,exchange,segment,trading_symbol): return self._get("/live-data/quote",{"exchange":exchange,"segment":segment,"trading_symbol":trading_symbol})
    def ltp(self,exchange_symbols:list[str],segment="CASH"): return self._get("/live-data/ltp",{"segment":segment,"exchange_symbols":",".join(exchange_symbols)})
    def option_chain(self,exchange,underlying,expiry): return self._get(f"/option-chain/exchange/{exchange}/underlying/{underlying}",{"expiry_date":expiry})
    def status(self): return {"connected":self.connected,"provider":"groww","read_only":True,"token_present":self.connected}
