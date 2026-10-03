"""Part 26 — Confidence Engine. Confidence is a heuristic score, NOT a probability or win rate."""
from __future__ import annotations
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
@register(26)
def run(ctx:PipelineContext)->PartResult:
    dq=ctx.get("dq"); oi=ctx.get("oi") or {}; trap=ctx.get("trap") or {}; regime=ctx.get("regime")
    base=0.3 if (dq is None or getattr(dq,"passed",True)) else 0.0
    base+=min(0.35,abs(oi.get("bias",0.0))); results=ctx.ensure_strategy_scan(); fired=[r for r in results if r.fired]; confirming=len(fired)
    base+=min(0.2,confirming*0.02)
    if regime not in (None,"UNCERTAIN"):base+=0.05
    if trap.get("any_trap"):base-=0.15
    confidence=max(0.0,min(1.0,base)); ctx.put("confidence",round(confidence,4))
    return PartResult(part=26,name="Confidence Engine",output={"confidence":round(confidence,4),"confirming":confirming,"note":"heuristic score, not a probability/win rate"})
