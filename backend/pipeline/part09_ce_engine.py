"""Part 09 — CE Engine."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(9)
def run(ctx: PipelineContext)->PartResult:
    oi=ctx.get("oi") or {}; per={p["strike"]:p for p in oi.get("per_strike") or []}
    atm=ctx.get("atm_strike"); up=dn=0
    for st in ctx.snapshot.strikes:
        row=per.get(st.strike,{})
        if row.get("ce")=="LONG_BUILDUP": up+=1
        if row.get("ce")=="SHORT_BUILDUP": dn+=1
    out={"ce_bullish_count":up,"ce_bearish_count":dn,"atm_ce_class":per.get(atm,{}).get("ce"),"score":round((up-dn)*.5,3)}
    ctx.put("ce_engine",out)
    return PartResult(part=9,name="CE Engine",output=out)
