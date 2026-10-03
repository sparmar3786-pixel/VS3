"""Part 28 — Signal Quality Filter. Suppresses weak, duplicate and contradictory signals with reasons."""
from __future__ import annotations
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
@register(28)
def run(ctx:PipelineContext)->PartResult:
    results=ctx.ensure_strategy_scan(); kept=[]; suppressed=[]; seen=set(); conflict=ctx.get("conflict") or {}
    for r in results:
        if not r.fired:continue
        if r.strategy_id in seen:suppressed.append((r.strategy_id,"duplicate"));continue
        seen.add(r.strategy_id)
        if r.confidence<0.2:suppressed.append((r.strategy_id,"weak"));continue
        if conflict.get("conflict") and r.side is not None and abs(r.score)<0.5:suppressed.append((r.strategy_id,"contradiction"));continue
        kept.append(r.strategy_id)
    out={"kept":kept,"suppressed":suppressed,"kept_count":len(kept),"suppressed_count":len(suppressed)}
    ctx.put("signal_quality",out); return PartResult(part=28,name="Signal Quality Filter",output={"kept":len(kept),"suppressed":len(suppressed)})
