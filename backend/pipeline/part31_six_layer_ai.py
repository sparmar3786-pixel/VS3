"""Part 31 — 6-AI Validation (async). AI only validates deterministic output."""
from __future__ import annotations
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
@register(31)
async def run(ctx:PipelineContext)->PartResult:
    ai=ctx.get("_ai")
    if ai is None:
        ctx.put("ai",{"enabled":False,"reason":"ai client not attached"}); return PartResult(part=31,name="6-AI Validation",skipped=True,notes=["ai disabled"])
    try:
        verdict=await ai.validate(ctx); ctx.put("ai",verdict)
        return PartResult(part=31,name="6-AI Validation",output={"layers":len(verdict.get("layers",[])),"wait_override":verdict.get("wait_override",False),"guarded":verdict.get("guard_triggered",False)})
    except Exception as e:
        ctx.put("ai",{"enabled":True,"error":str(e),"degraded":True}); return PartResult(part=31,name="6-AI Validation",ok=False,notes=[f"ai layer error (non-fatal): {e}"])
