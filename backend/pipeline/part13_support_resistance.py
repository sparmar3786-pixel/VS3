"""Part 13 — Support / Resistance (CONTEXT ONLY)."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(13)
def run(ctx:PipelineContext)->PartResult:
    snap=ctx.snapshot; spot=snap.spot or 0.; hi=snap.day_high or snap.pdh or spot; lo=snap.day_low or snap.pdl or spot; c=snap.prev_close or spot
    pivot=(hi+lo+c)/3; r1=2*pivot-lo; s1=2*pivot-hi; r2=pivot+(hi-lo); s2=pivot-(hi-lo)
    tc=(hi+lo)/2; bc=(pivot+c)/2; rng=hi-lo
    fib={f"fib_{int(p*100)}":hi-rng*p for p in (.236,.382,.5,.618,.786)}
    st=ctx.get("strike_engine") or {}
    out={"context_only":True,"ce_resistance_oi":st.get("max_ce_oi_strike"),"pe_support_oi":st.get("max_pe_oi_strike"),
         "pdh":snap.pdh,"pdl":snap.pdl,"day_high":snap.day_high,"day_low":snap.day_low,"prev_close":snap.prev_close,
         "weekly_ref":{"week_high":snap.pdh,"week_low":snap.pdl},
         "pivots":{"pivot":round(pivot,2),"r1":round(r1,2),"s1":round(s1,2),"r2":round(r2,2),"s2":round(s2,2)},
         "cpr":{"top":round(tc,2),"bottom":round(bc,2)},
         "fibonacci":{k:round(v,2) for k,v in fib.items()}}
    ctx.put("sr",out)
    return PartResult(part=13,name="Support / Resistance (context only)",output={"context_only":True,"pivots":{"pivot":round(pivot,2)}})
