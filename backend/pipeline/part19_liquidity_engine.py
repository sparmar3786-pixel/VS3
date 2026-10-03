"""Part 19 — Liquidity Engine (spread, depth, liquidity score + filters). """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
@register(19)
def run(ctx: PipelineContext)->PartResult:
    snap=ctx.snapshot; atm=ctx.get("atm_strike"); spreads=[]
    for s in snap.strikes:
        for o in ("ce","pe"):
            b=getattr(s,f"{o}_bid"); a=getattr(s,f"{o}_ask")
            if b and a and a>=b: spreads.append(a-b)
    avg_spread=sum(spreads)/len(spreads) if spreads else None
    atm_row=next((s for s in snap.strikes if s.strike==atm),None)
    atm_spread=None if atm_row and atm_row.ce_bid and atm_row.ce_ask else None
    if atm_row and atm_row.ce_bid and atm_row.ce_ask: atm_spread=atm_row.ce_ask-atm_row.ce_bid
    total_vol=sum((s.ce_volume or 0)+(s.pe_volume or 0) for s in snap.strikes)
    score=1.0 if atm_spread is not None and atm_row and atm_row.ce_ltp else 0.0
    if score:
        ratio=atm_spread/max(atm_row.ce_ltp,0.05); score=max(0.0,1.0-ratio*5)
    out={"avg_spread":avg_spread,"atm_spread":atm_spread,"total_volume":total_vol,"liquidity_score":round(score,4),
         "wide_spread":bool(atm_spread is not None and atm_row and atm_row.ce_ltp and atm_spread>0.05*atm_row.ce_ltp),"low_liquidity":total_vol<1000}
    ctx.put("liquidity",out); return PartResult(part=19,name="Liquidity Engine",output=out)
