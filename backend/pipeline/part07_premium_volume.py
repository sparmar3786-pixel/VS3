"""Part 07 — Premium + Volume Engine."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import safe_pct_change

def _step(ctx)->float:
    ks=sorted(s.strike for s in ctx.snapshot.strikes)
    diffs=[b-a for a,b in zip(ks,ks[1:]) if b-a>0]
    return min(diffs) if diffs else 50.0

@register(7)
def run(ctx:PipelineContext)->PartResult:
    atm=ctx.get("atm_strike"); ce_mom=pe_mom=None; ce_vol=pe_vol=total_vol=0
    for st in ctx.snapshot.strikes:
        if atm is not None and abs(st.strike-atm)<=2*_step(ctx):
            ce_mom=safe_pct_change(st.ce_ltp,st.ce_prev_ltp)
            pe_mom=safe_pct_change(st.pe_ltp,st.pe_prev_ltp)
            ce_vol+=st.ce_volume or 0; pe_vol+=st.pe_volume or 0
        total_vol+=(st.ce_volume or 0)+(st.pe_volume or 0)
    bias=(ce_mom-pe_mom)/100.0 if ce_mom is not None and pe_mom is not None else 0.0
    confirm=ce_vol/total_vol if total_vol else 0.5
    out={"ce_mom_pct":ce_mom,"pe_mom_pct":pe_mom,"bias":round(bias,4),"ce_vol_share":round(confirm,4),"total_volume":total_vol}
    ctx.put("premium_volume",out)
    return PartResult(part=7,name="Premium + Volume Engine",output=out)
