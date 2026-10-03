"""Part 01 — Data Input."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(1)
def run(ctx: PipelineContext) -> PartResult:
    snap=ctx.snapshot
    frame=[]
    for s in snap.strikes:
        frame.append({
            "strike":s.strike,"is_atm":s.is_atm,
            "ce_ltp":s.ce_ltp,"ce_oi":s.ce_oi,"ce_oi_change":s.ce_oi_change,
            "ce_volume":s.ce_volume,"ce_iv":s.ce_iv,"ce_delta":s.ce_delta,
            "ce_bid":s.ce_bid,"ce_ask":s.ce_ask,"ce_prev_ltp":s.ce_prev_ltp,
            "pe_ltp":s.pe_ltp,"pe_oi":s.pe_oi,"pe_oi_change":s.pe_oi_change,
            "pe_volume":s.pe_volume,"pe_iv":s.pe_iv,"pe_delta":s.pe_delta,
            "pe_bid":s.pe_bid,"pe_ask":s.pe_ask,"pe_prev_ltp":s.pe_prev_ltp})
    ctx.put("frame",frame); ctx.put("spot",snap.spot); ctx.put("atm_strike",snap.atm_strike)
    ctx.put("expiry",snap.expiry); ctx.put("source",snap.source)
    if snap.timestamp: ctx.price_history.append(snap.spot or 0.0)
    ok=bool(frame) and snap.spot is not None
    res=PartResult(part=1,name="Data Input",ok=ok,data_gap=not ok)
    res.output={"strikes":len(frame),"spot":snap.spot,"atm":snap.atm_strike}
    if not ok: res.notes.append("empty chain or missing spot")
    return res
