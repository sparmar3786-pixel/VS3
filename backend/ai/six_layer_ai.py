"""Six-layer AI validation; AI audits deterministic output only."""
from __future__ import annotations
import asyncio,json,re
from typing import Any,Dict,List,Optional
from backend.ai.guard import LAYER_OUTPUT_SCHEMA,HallucinationGuard,decides_wait_override
from backend.ai.provider_client import ProviderClient
from backend.ai.puter_client import PuterClient
from backend.config import Settings

WEB_SEARCH_TOOL={"type":"web_search"}
LAYERS=[
 {"id":"L1","name":"Gemini Flash-Lite","role":"fast candidate analysis","env":"ai_model_l1","web":False},
 {"id":"L2","name":"Groq GPT-OSS","role":"fast data verification","env":"ai_model_l2","web":False},
 {"id":"L3","name":"Cerebras Llama","role":"independent validation","env":"ai_model_l3","web":False},
 {"id":"L4","name":"DeepSeek","role":"quantitative / OI audit","env":"ai_model_l4","web":False},
 {"id":"L5","name":"Cloudflare GLM","role":"market structure analysis","env":"ai_model_l5","web":False},
 {"id":"L6","name":"Ollama Local","role":"final local risk audit","env":"ai_model_l6","web":False},
]
_SYSTEM=("You are a market-data VALIDATION layer inside an options terminal. "
"You may ONLY verify, cross-check and flag the deterministic engine output. "
"You must NEVER invent a strike, entry price, stop-loss or target. "
"Confidence is not a win rate. Reply with a SINGLE JSON object matching this schema: "+json.dumps(LAYER_OUTPUT_SCHEMA))

def _extract_json(text:str)->Optional[dict]:
 if not text:return None
 text=re.sub(r"^\`\`\`(?:json)?|\`\`\`$","",text.strip(),flags=re.MULTILINE).strip()
 try:return json.loads(text)
 except Exception:
  m=re.search(r"\{.*\}",text,re.DOTALL)
  if m:
   try:return json.loads(m.group(0))
   except Exception:return None
 return None

class SixLayerAI:
 def __init__(self,settings:Settings)->None:
  self.s=settings; self.puter=PuterClient(settings); self.provider=ProviderClient(settings)
  self.transport=settings.ai_transport.strip().lower(); self._resolved={}
 def available(self)->bool:
  if self.transport=="puter":return self.puter.available()
  if self.transport=="direct":return self.provider.available()
  return self.puter.available() or self.provider.available()
 async def _model_for(self,layer):
  configured=getattr(self.s,layer["env"],"")
  if not configured:return None
  if self.transport=="puter" and self.puter.available():
   resolved=await self.puter.resolve_model(configured); self._resolved[layer["id"]]=resolved; return resolved
  return configured
 def _digest(self,ctx)->Dict[str,Any]:
  oi=ctx.get("oi") or {}; ce=ctx.get("ce_engine") or {}; pe=ctx.get("pe_engine") or {}
  ind=ctx.get("indicators") or {}; gr=ctx.get("greeks") or {}
  net=oi.get("bias",0.0)+ce.get("score",0.0)*.5+pe.get("score",0.0)*.5
  snap=ctx.snapshot; top=sorted(snap.strikes,key=lambda s:(s.ce_oi or 0)+(s.pe_oi or 0),reverse=True)[:5]
  return {"index":ctx.index,"spot":snap.spot,"atm":ctx.get("atm_strike"),"expiry":snap.expiry,"regime":ctx.get("regime"),
          "oi_bias":round(oi.get("bias",0.0),4),"ce_score":ce.get("score"),"pe_score":pe.get("score"),
          "engine_direction":"CALL" if net>=0 else "PUT","confidence":ctx.get("confidence"),
          "indicators":{k:ind.get(k) for k in ("ema8","ema13","rsi","atr_pct","vwap")},
          "greeks":{k:gr.get(k) for k in ("atm_ce_delta","atm_ce_iv","avg_ce_iv","iv_skew_pe_minus_ce")},
          "data_quality_passed":bool(getattr(ctx.get("dq"),"passed",True)),
          "top_oi_strikes":[{"strike":s.strike,"ce_oi":s.ce_oi,"pe_oi":s.pe_oi} for s in top],
          "probable_covering":(ctx.get("seller_pressure") or {}).get("probable_covering_strikes",[]),
          "allowed_strikes":[s.strike for s in snap.strikes]}
 async def _call_layer(self,layer,digest):
  model=await self._model_for(layer)
  if not model:return None
  user=("Layer "+layer["id"]+" role: "+layer["role"]+". Validate the following engine output and return JSON only:\n"+
        json.dumps(digest,default=str))
  messages=[{"role":"system","content":_SYSTEM},{"role":"user","content":user}]
  tools=[WEB_SEARCH_TOOL] if layer["web"] and self.s.web_search_on else None
  result=None
  if self.transport in ("puter","auto") and self.puter.available():result=await self.puter.chat(messages,model=model,tools=tools)
  if result is None and self.transport in ("direct","auto") and self.provider.available():result=await self.provider.chat(model,messages,tools=tools)
  if result is None:return None
  parsed=_extract_json(result.get("content",""))
  if parsed is None:return None
  parsed["layer"]=layer["id"]; parsed.setdefault("model",model); return parsed
 async def validate(self,ctx)->Dict[str,Any]:
  if not self.available():return {"enabled":True,"degraded":True,"reason":"no AI transport configured","layers":[],"wait_override":False}
  digest=self._digest(ctx)
  guard=HallucinationGuard({round(float(s),2) for s in digest.get("allowed_strikes",[])})
  raw_layers=await asyncio.gather(*[self._call_layer(l,digest) for l in LAYERS])
  checked=[]; guard_triggered=False
  for raw in raw_layers:
   if raw is None:continue
   gr=guard.check(raw); guard_triggered=guard_triggered or not gr.ok
   gr.sanitized["model"]=raw.get("model"); checked.append(gr.sanitized)
  if not checked:return {"enabled":True,"degraded":True,"reason":"no layer returned valid JSON","layers":[],"wait_override":False,"guard_triggered":guard_triggered}
  agreement=round(sum(1 for o in checked if o.get("agrees"))/len(checked),3)
  return {"enabled":True,"degraded":False,"layers":checked,"agreement":agreement,
          "wait_override":decides_wait_override(checked),"guard_triggered":guard_triggered,
          "note":"AI is validation-only; confidence is not a win rate"}
def build_ai_client(settings:Settings)->Optional[SixLayerAI]:
 return SixLayerAI(settings) if settings.ai_on else None
