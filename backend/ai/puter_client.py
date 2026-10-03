"""Best-effort server-side Puter transport; browser zero-key mode remains separate."""
from __future__ import annotations
from typing import Any,Dict,List,Optional
import httpx
from loguru import logger
from backend.config import Settings
_DRIVER_ENDPOINT="/drivers/call"
_CHAT_INTERFACE="puter-chat-completion"

class PuterClient:
    def __init__(self,settings:Settings)->None:
        self.s=settings; self.token=settings.puter_auth_token; self.base=settings.puter_api_base.rstrip("/")
    def available(self)->bool:return bool(self.token)
    def _headers(self)->Dict[str,str]:return {"Authorization":f"Bearer {self.token}","Content-Type":"application/json"}
    async def list_models(self)->List[Dict[str,Any]]:
        if not self.available():return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r=await c.post(self.base+_DRIVER_ENDPOINT,headers=self._headers(),json={"interface":_CHAT_INTERFACE,"method":"models","args":{}})
                r.raise_for_status(); d=r.json(); return d.get("result") or d.get("models") or []
        except Exception as e: logger.warning("puter listModels failed: {}",e); return []
    async def list_model_providers(self)->List[str]:
        if not self.available():return []
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r=await c.post(self.base+_DRIVER_ENDPOINT,headers=self._headers(),json={"interface":_CHAT_INTERFACE,"method":"providers","args":{}})
                r.raise_for_status(); d=r.json(); return list(d.get("result") or d.get("providers") or [])
        except Exception as e: logger.warning("puter listModelProviders failed: {}",e); return []
    async def chat(self,messages:List[Dict[str,str]],*,model:str,tools:Optional[List[dict]]=None,temperature:float=0.1,max_tokens:int=1200)->Optional[Dict[str,Any]]:
        if not self.available():return None
        args={"messages":messages,"model":model,"temperature":temperature,"max_tokens":max_tokens}
        if tools:args["tools"]=tools
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r=await c.post(self.base+_DRIVER_ENDPOINT,headers=self._headers(),json={"interface":_CHAT_INTERFACE,"method":"complete","args":args})
                r.raise_for_status(); d=r.json(); result=d.get("result")
                if isinstance(result,dict):result=result.get("message",{}).get("content","")
                return {"provider":"puter","model":model,"content":str(result)}
        except Exception as e: logger.warning("puter chat failed ({}): {}",model,e); return None
    async def resolve_model(self,preferred:str)->Optional[str]:
        models=await self.list_models()
        if not models:return preferred
        ids={str(m.get("id") or m.get("name") or m) for m in models}
        if preferred in ids:return preferred
        for i in ids:
            if preferred.split("-")[0] in i:return i
        return None
