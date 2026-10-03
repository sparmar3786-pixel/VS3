"""MCP client and DataSource adapter with health checks and local fallback."""
from __future__ import annotations
import asyncio,json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any,Dict,List,Optional
from loguru import logger
from backend.brokers.base import Capabilities,DataSource,DataSourceError
from backend.config import get_settings
from backend.models import Snapshot,Tick

class MCPClient:
 def __init__(self,cfg:Dict[str,Any])->None:
  self.cfg=cfg;self.name=cfg.get("name","mcp");self.timeout=float(cfg.get("timeout_sec",20));self._stack=None;self._session=None
 async def connect(self):
  from mcp import ClientSession
  self._stack=AsyncExitStack()
  if self.cfg.get("transport","stdio")=="sse":
   from mcp.client.sse import sse_client
   read,write=await self._stack.enter_async_context(sse_client(self.cfg["url"]))
  else:
   from mcp import StdioServerParameters
   from mcp.client.stdio import stdio_client
   params=StdioServerParameters(command=self.cfg["command"],args=self.cfg.get("args",[]))
   read,write=await self._stack.enter_async_context(stdio_client(params))
  self._session=await self._stack.enter_async_context(ClientSession(read,write));await self._session.initialize()
 async def close(self):
  if self._stack is not None:await self._stack.aclose()
  self._stack=None;self._session=None
 async def health_check(self)->bool:
  try:await asyncio.wait_for(self._session.list_tools(),timeout=self.timeout);return True
  except Exception:return False
 async def call_tool(self,name:str,args:Dict[str,Any])->Optional[Any]:
  if self._session is None:return None
  try:r=await asyncio.wait_for(self._session.call_tool(name,args),timeout=self.timeout)
  except Exception as e:logger.warning("mcp {} tool {} failed: {}",self.name,name,e);return None
  for block in getattr(r,"content",[]) or []:
   text=getattr(block,"text",None)
   if text:
    try:return json.loads(text)
    except Exception:return {"text":text}
  return None

def load_config(path:Optional[str]=None)->Dict[str,Any]:
 p=Path(path or get_settings().mcp_config_path)
 if not p.exists():return {"servers":[],"fallback_order":[]}
 try:return json.loads(p.read_text())
 except Exception as e:logger.warning("bad mcp config {}: {}",p,e);return {"servers":[],"fallback_order":[]}

class MCPSource(DataSource):
 name="mcp";capabilities=Capabilities(streaming=False,greeks=True,option_chain=True,historical=False)
 def __init__(self)->None:super().__init__(rps=5.0);self._clients=[];self._active=None;self._fallback=None
 async def connect(self):
  cfg=load_config();order=cfg.get("fallback_order") or [s.get("name") for s in cfg.get("servers",[])]
  by_name={s.get("name"):s for s in cfg.get("servers",[]) if s.get("enabled",True)}
  for name in order:
   c=by_name.get(name)
   if not c:continue
   client=MCPClient(c)
   try:
    await client.connect()
    if await client.health_check():self._clients.append(client);self._active=client;logger.info("mcp: active server = {}",client.name);break
    await client.close()
   except Exception as e:logger.warning("mcp: could not connect {} ({})",name,e)
  if self._active is None:
   from backend.brokers.factory import build_source
   s=get_settings();local_name=s.data_source if s.data_source!="mcp" else "demo"
   try:self._fallback=build_source(local_name);await self._fallback.connect();logger.info("mcp: local fallback '{}'",local_name)
   except Exception as e:logger.error("mcp: local fallback failed ({})",e)
  self._connected=True
 async def close(self):
  for c in self._clients:await c.close()
  if self._fallback is not None:await self._fallback.close()
  self._connected=False
 async def _tool(self,name,args):
  if self._active is not None:return await self._active.call_tool(name,args)
  return None
 async def get_ltp(self,symbol,token,exchange="NSE"):
  out=await self._tool("get_ltp",{"index":symbol})
  if out is not None:return out if isinstance(out,(int,float)) else out.get("result")
  return await self._fallback.get_ltp(symbol,token,exchange) if self._fallback else None
 async def get_quote(self,symbol,token,exchange="NSE"):
  out=await self._tool("get_quote",{"index":symbol})
  if out:return Tick(symbol=symbol,exchange=exchange,token=token,ltp=float(out.get("ltp",0)),source="mcp")
  return await self._fallback.get_quote(symbol,token,exchange) if self._fallback else None
 async def get_option_chain(self,index,expiry=None):
  out=await self._tool("get_option_chain",{"index":index,"expiry":expiry})
  if out:
   try:return Snapshot.model_validate(out)
   except Exception as e:logger.warning("mcp chain parse failed: {}",e)
  if self._fallback:return await self._fallback.get_option_chain(index,expiry)
  raise DataSourceError("no MCP server and no fallback available")
 def list_expiries(self,index):return self._fallback.list_expiries(index) if self._fallback else []
 def resolve_token(self,index,strike,option_type,expiry):return self._fallback.resolve_token(index,strike,option_type,expiry) if self._fallback else None
