"""Part 25 — Risk Engine (THE single risk / R:R gate).
Locked Run60/Run93 principle: exactly one final risk/R:R gate.
The gate constant min_rr lives in config and must not be changed silently.
TUNING: atr_sl_mult, premium_sl_pct, min_confidence, min_confirming.
"""
from __future__ import annotations
from typing import Optional
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
TUNING={"atr_sl_mult":1.0,"premium_sl_pct":0.12,"min_confidence":0.35,"min_confirming":2,"capital_inr":1_000_000.0}
def passes_risk_gate(rr:Optional[float],min_rr:float)->bool:return rr is not None and rr>=min_rr
def position_size(capital:float,risk_frac:float,entry:float,sl:float,lot:int)->int:
    risk_per_unit=abs(entry-sl)
    if risk_per_unit<=0 or lot<=0:return 0
    budget=capital*risk_frac; units=int(budget//risk_per_unit)
    return max(0,(units//lot)*lot)
@register(25)
def run(ctx:PipelineContext)->PartResult:
    ind=ctx.get("indicators") or {}; spot=ctx.get("spot"); atr_val=ind.get("atr") or (spot*0.005 if spot else None)
    out={"min_rr":ctx.settings.min_rr,"atr_sl_distance":round(atr_val*TUNING["atr_sl_mult"],2) if atr_val else None,"premium_sl_pct":TUNING["premium_sl_pct"],"min_confidence":TUNING["min_confidence"],"min_confirming":TUNING["min_confirming"],"capital_inr":TUNING["capital_inr"]}
    ctx.put("risk",out); return PartResult(part=25,name="Risk Engine",output=out)
