"""Part 20 — Trap Engine (bull/bear/buyer/seller traps, false signals, exhaustion). """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
@register(20)
def run(ctx: PipelineContext)->PartResult:
    pa=ctx.get("price_action") or {}; oi=ctx.get("oi") or {}; pv=ctx.get("premium_volume") or {}; bias=oi.get("bias",0.0); prem_bias=pv.get("bias",0.0)
    traps={"bull_trap":bool(pa.get("bos") and bias<0),"bear_trap":bool(pa.get("choch") and bias>0),"false_oi_signal":bool(abs(bias)>0.3 and abs(prem_bias)<0.05),"false_volume_signal":bool(pv.get("ce_vol_share",0.5)>0.9 and abs(prem_bias)<0.02),"exhaustion_reversal":bool(abs(bias)>0.5 and abs(prem_bias)<0.05)}
    out={"traps":traps,"any_trap":any(traps.values())}; ctx.put("trap",out); return PartResult(part=20,name="Trap Engine",output=out)
