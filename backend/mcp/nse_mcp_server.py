"""NSE MCP server using the official MCP SDK.

Exposes read-only NSE market/engine tools. Order placement is not exposed.
"""
from __future__ import annotations
import argparse
from typing import Any,Dict,List,Optional
from backend.config import get_settings
from backend.logging_config import get_logger,setup_logging
log=get_logger("mcp.server")
try:
 from mcp.server.fastmcp import FastMCP
except Exception as e:
 FastMCP=None;_IMPORT_ERROR=e
else:_IMPORT_ERROR=None
_settings=get_settings();_source=None;_engine=None

async def _get_source():
 global _source
 if _source is None:
  from backend.brokers.factory import get_data_source
  _source=get_data_source();await _source.connect()
 return _source
async def _get_engine():
 global _engine
 if _engine is None:
  from backend.pipeline.orchestrator import TerminalEngine
  _engine=TerminalEngine();await _engine.start()
 return _engine

def _build():
 if FastMCP is None:raise RuntimeError(f"the 'mcp' package is required: {_IMPORT_ERROR}")
 mcp=FastMCP("nse-mcp")
 @mcp.tool()
 async def get_indices()->List[str]:return _settings.index_list
 @mcp.tool()
 async def get_market_status()->Dict[str,Any]:
  from backend.pipeline.part22_time_engine import run as time_part
  from backend.pipeline.context import PipelineContext
  src=await _get_source();snap=await src.get_option_chain(_settings.index_list[0])
  res=time_part(PipelineContext(index=_settings.index_list[0],snapshot=snap,settings=_settings))
  return {"status":res.output,"source":getattr(src,"name","?")}
 @mcp.tool()
 async def get_option_chain(index:str,expiry:Optional[str]=None)->Dict[str,Any]:
  s=await (await _get_source()).get_option_chain(index,expiry);return s.model_dump(mode="json")
 @mcp.tool()
 async def get_quote(index:str)->Dict[str,Any]:
  t=await (await _get_source()).get_quote(index,token=index);return t.model_dump(mode="json") if t else {}
 @mcp.tool()
 async def get_ltp(index:str)->Optional[float]:return await (await _get_source()).get_ltp(index,token=index)
 @mcp.tool()
 async def get_oi_heatmap(index:str,expiry:Optional[str]=None)->List[Dict[str,Any]]:
  s=await (await _get_source()).get_option_chain(index,expiry)
  return [{"strike":x.strike,"ce_oi":x.ce_oi,"pe_oi":x.pe_oi,"ce_oi_change":x.ce_oi_change,"pe_oi_change":x.pe_oi_change} for x in s.strikes]
 @mcp.tool()
 async def get_iv_surface(index:str,expiry:Optional[str]=None)->Dict[str,Any]:
  s=await (await _get_source()).get_option_chain(index,expiry)
  return {"spot":s.spot,"points":[{"strike":x.strike,"ce_iv":x.ce_iv,"pe_iv":x.pe_iv} for x in s.strikes]}
 @mcp.tool()
 async def get_greeks(index:str,expiry:Optional[str]=None)->List[Dict[str,Any]]:
  s=await (await _get_source()).get_option_chain(index,expiry)
  return [{"strike":x.strike,"ce_delta":x.ce_delta,"pe_delta":x.pe_delta,"ce_gamma":x.ce_gamma,"pe_gamma":x.pe_gamma,"ce_theta":x.ce_theta,"pe_theta":x.pe_theta,"ce_vega":x.ce_vega,"pe_vega":x.pe_vega} for x in s.strikes]
 @mcp.tool()
 async def run_strategy_scan(index:str)->Dict[str,Any]:return await (await _get_engine()).run_strategy_scan(index)
 @mcp.tool()
 async def get_terminal_verdict(index:str)->Dict[str,Any]:
  d=await (await _get_engine()).run_strategy_scan(index)
  return {"index":index,"verdict":d.get("verdict"),"plans":d.get("plans_qualifying"),"suppressed":d.get("plans_suppressed")}
 @mcp.tool()
 async def place_live_order(index:str,strike:float,option_type:str,side:str,quantity:int,confirm:str)->Dict[str,Any]:
  if not _settings.live_orders_on:return {"accepted":False,"reason":"live orders disabled (ENABLE_LIVE_ORDERS=0)"}
  expected=f"{index}-{option_type}-{strike}-{side}"
  if _settings.human_confirm_required and confirm!=expected:return {"accepted":False,"reason":f"human confirmation required; echo confirm={expected!r}"}
  res=await (await _get_engine()).place_live_order({"index":index,"strike":strike,"option_type":option_type,"side":side,"quantity":quantity})
  return {"mode":"LIVE",**res}
 return mcp

def main():
 setup_logging();p=argparse.ArgumentParser(description="NSE MCP server")
 p.add_argument("--transport",choices=["stdio","sse"],default=_settings.nse_mcp_transport);p.add_argument("--port",type=int,default=_settings.nse_mcp_sse_port)
 a=p.parse_args();mcp=_build();log.info("nse-mcp starting (transport={})",a.transport)
 if a.transport=="sse":
  import uvicorn
  from starlette.responses import PlainTextResponse
  app=mcp.sse_app()
  async def health(_request): return PlainTextResponse("ok")
  app.add_route("/health", health, methods=["GET"])
  uvicorn.run(app,host="0.0.0.0",port=a.port)
 else:mcp.run(transport="stdio")
if __name__=="__main__":main()
