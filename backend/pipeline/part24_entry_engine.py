"""Part 24 — Entry Engine (entry price/type, chase filter). """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
@register(24)
def run(ctx: PipelineContext)->PartResult:
    snap=ctx.snapshot; atm=ctx.get("atm_strike"); oi=ctx.get("oi") or {}; bias=oi.get("bias",0.0); side="CE" if bias>=0 else "PE"; row=next((s for s in snap.strikes if s.strike==atm),None)
    if row is None:
        ctx.put("entry",{"data_gap":True}); return PartResult(part=24,name="Entry Engine",data_gap=True)
    entry=getattr(row,f"{side.lower()}_ltp"); ask=getattr(row,f"{side.lower()}_ask")
    out={"side":side,"strike":row.strike,"entry":entry,"ask":ask,"entry_type":"confirmation" if abs(bias)>0.3 else "early","chase":bool(entry and ask and ask>entry*1.01)}
    ctx.put("entry",out); return PartResult(part=24,name="Entry Engine",output=out)
