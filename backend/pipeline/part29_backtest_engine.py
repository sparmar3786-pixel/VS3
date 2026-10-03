"""Part 29 — Backtest Engine. Lightweight in-cycle memory hook; never fabricates absent history."""
from __future__ import annotations
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
@register(29)
def run(ctx:PipelineContext)->PartResult:
    memory=ctx.get("_memory"); summary={"available":False}
    if memory is not None:
        try:summary=memory.strategy_summary(ctx.index);summary["available"]=True
        except Exception as e:summary={"available":False,"error":str(e)}
    ctx.put("backtest",summary); return PartResult(part=29,name="Backtest Engine",output={"available":summary.get("available",False)})
