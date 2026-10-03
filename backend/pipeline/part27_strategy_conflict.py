"""Part 27 — Strategy Conflict Engine."""
from __future__ import annotations
from backend.models import Side
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
@register(27)
def run(ctx:PipelineContext)->PartResult:
    results=ctx.ensure_strategy_scan(); fired=[r for r in results if r.fired]
    call=[r for r in fired if r.side==Side.CALL]; put=[r for r in fired if r.side==Side.PUT]
    call_score=sum(r.score for r in call); put_score=sum(abs(r.score) for r in put); net=sum(r.score for r in fired)
    conflict=bool(call and put and abs(call_score-put_score)<1.0)
    out={"call_ids":[r.strategy_id for r in call],"put_ids":[r.strategy_id for r in put],"net_score":round(net,4),"conflict":conflict}
    ctx.put("conflict",out); return PartResult(part=27,name="Strategy Conflict Engine",output={"conflict":conflict,"net_score":round(net,4)})
