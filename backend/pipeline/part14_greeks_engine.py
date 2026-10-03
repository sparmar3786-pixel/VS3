"""Part 14 — Greeks Engine. Missing greeks are reported as DATA_GAP, never guessed."""
from __future__ import annotations
import statistics
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import realized_vol, returns_from_prices

@register(14)
def run(ctx:PipelineContext)->PartResult:
    atm=ctx.get("atm_strike"); snap=ctx.snapshot
    ce_ivs=[s.ce_iv for s in snap.strikes if s.ce_iv]; pe_ivs=[s.pe_iv for s in snap.strikes if s.pe_iv]
    row=next((s for s in snap.strikes if s.strike==atm),None)
    ac=statistics.mean(ce_ivs) if ce_ivs else None; ap=statistics.mean(pe_ivs) if pe_ivs else None
    skew=ap-ac if ac is not None and ap is not None else None
    rv=realized_vol(returns_from_prices(list(ctx.price_history)),20)
    have=row is not None and row.ce_delta is not None
    out={"atm":atm,"atm_ce_delta":getattr(row,"ce_delta",None) if row else None,
         "atm_pe_delta":getattr(row,"pe_delta",None) if row else None,
         "atm_ce_gamma":getattr(row,"ce_gamma",None) if row else None,
         "atm_theta":getattr(row,"ce_theta",None) if row else None,
         "avg_ce_iv":ac,"avg_pe_iv":ap,"iv_skew_pe_minus_ce":skew,"realized_vol_ann":rv,
         "iv_minus_rv":ac-rv if ac is not None and rv is not None else None,
         "gamma_expansion":bool(row and row.ce_gamma and row.ce_gamma>.0008)}
    ctx.put("greeks",out)
    res=PartResult(part=14,name="Greeks Engine",output=out,data_gap=not have)
    if not have: res.notes.append("no greeks on ATM row")
    return res
