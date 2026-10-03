"""Part 10 — PE Engine."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(10)
def run(ctx:PipelineContext)->PartResult:
    oi=ctx.get("oi") or {}; per={p["strike"]:p for p in oi.get("per_strike") or []}
    atm=ctx.get("atm_strike"); bull=bear=0
    for st in ctx.snapshot.strikes:
        row=per.get(st.strike,{})
        if row.get("pe")=="SHORT_BUILDUP": bull+=1
        if row.get("pe")=="LONG_BUILDUP": bear+=1
    out={"pe_bullish_count":bull,"pe_bearish_count":bear,"atm_pe_class":per.get(atm,{}).get("pe"),"score":round((bull-bear)*.5,3)}
    ctx.put("pe_engine",out)
    return PartResult(part=10,name="PE Engine",output=out)
