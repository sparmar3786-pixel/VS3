"""Part 11 — Opposite-Side Override."""
from __future__ import annotations
from backend.models import OverrideAction
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(11)
def run(ctx:PipelineContext)->PartResult:
    ce=ctx.get("ce_engine") or {}; pe=ctx.get("pe_engine") or {}
    cs=ce.get("score",0.0); ps=pe.get("score",0.0); net=cs+ps
    action=OverrideAction.NONE; reason=""
    if cs>2 and ps<-2: action=OverrideAction.BLOCK; reason="CE strongly bullish but PE strongly bearish -> conflict, block"
    elif cs<-2 and ps>2: action=OverrideAction.BLOCK; reason="CE strongly bearish but PE strongly bullish -> conflict, block"
    elif abs(net)<.5 and (abs(cs)>1.5 or abs(ps)>1.5): action=OverrideAction.REVERSAL_WATCH; reason="side engines net-neutral with strong opposing evidence"
    if action==OverrideAction.BLOCK and abs(net)>3: action=OverrideAction.EXIT; reason="strong one-sided evidence against prevailing position -> exit signal"
    out={"action":action.value,"reason":reason,"ce_score":cs,"pe_score":ps,"net":net}
    ctx.put("override",out)
    return PartResult(part=11,name="Opposite-Side Override",output=out)
