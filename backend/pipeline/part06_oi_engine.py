"""Part 06 — Option OI Engine (Run93 CORE, LOCKED)."""
from __future__ import annotations
from typing import Optional
from backend.models import OIClassification
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

_BIAS={"CE":{OIClassification.LONG_BUILDUP:1,OIClassification.SHORT_COVERING:1,OIClassification.SHORT_BUILDUP:-1,OIClassification.LONG_UNWINDING:-1},
       "PE":{OIClassification.LONG_BUILDUP:-1,OIClassification.SHORT_COVERING:-1,OIClassification.SHORT_BUILDUP:1,OIClassification.LONG_UNWINDING:1}}

def classify_oi(premium_change:Optional[float],oi_change:Optional[float],eps:float=1e-9)->OIClassification:
    if premium_change is None or oi_change is None:return OIClassification.NEUTRAL
    if premium_change>eps and oi_change>eps:return OIClassification.LONG_BUILDUP
    if premium_change<-eps and oi_change>eps:return OIClassification.SHORT_BUILDUP
    if premium_change>eps and oi_change<-eps:return OIClassification.SHORT_COVERING
    if premium_change<-eps and oi_change<-eps:return OIClassification.LONG_UNWINDING
    return OIClassification.NEUTRAL

def _prem_change(cur,prev): return None if cur is None or prev is None else cur-prev

@register(6)
def run(ctx:PipelineContext)->PartResult:
    prev_map={s.strike:s for s in ctx.prev_snapshot.strikes} if ctx.prev_snapshot else {}
    per=[]; agg=weight_sum=0.0; counts={c.value:0 for c in OIClassification}
    for st in ctx.snapshot.strikes:
        prev=prev_map.get(st.strike)
        ce_prev=(prev.ce_ltp if prev else None) or st.ce_prev_ltp
        pe_prev=(prev.pe_ltp if prev else None) or st.pe_prev_ltp
        ce=classify_oi(_prem_change(st.ce_ltp,ce_prev),st.ce_oi_change)
        pe=classify_oi(_prem_change(st.pe_ltp,pe_prev),st.pe_oi_change)
        counts[ce.value]+=1; counts[pe.value]+=1
        w=float((st.ce_oi or 0)+(st.pe_oi or 0) or 1)
        agg+=(_BIAS["CE"][ce]+_BIAS["PE"][pe])*w; weight_sum+=2*w
        per.append({"strike":st.strike,"ce":ce.value,"pe":pe.value,"ce_oi_change":st.ce_oi_change,"pe_oi_change":st.pe_oi_change})
    bias=agg/weight_sum if weight_sum else 0.0
    out={"per_strike":per,"bias":round(bias,4),"counts":counts}
    ctx.put("oi",out)
    return PartResult(part=6,name="Option OI Engine",output={"bias":round(bias,4),"counts":counts})
