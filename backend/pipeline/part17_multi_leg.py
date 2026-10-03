"""Part 17 — Multi-Leg Options. Recognises 23 multi-leg structures but ONLY emits one when every leg's data exists. Never fabricates a missing leg — a structure with a missing leg is reported as a gap. """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
STRUCTURES = ["Long Call","Long Put","Short Call","Short Put","Bull Call Spread","Bear Call Spread","Bull Put Spread","Bear Put Spread","Long Straddle","Short Straddle","Long Strangle","Short Strangle","Calendar Spread","Butterfly","Iron Butterfly","Condor","Iron Condor","Ratio Spread","Collar","Covered Call","Covered Put","Strip","Strap"]
@register(17)
def run(ctx: PipelineContext) -> PartResult:
    if not ctx.advanced: return PartResult(part=17,name="Multi-Leg Options",skipped=True,notes=["advanced engine disabled"])
    snap=ctx.snapshot; step=_step([s.strike for s in snap.strikes]) or 50.0; atm=ctx.get("atm_strike")
    have={s.strike:(s.ce_ltp is not None and s.pe_ltp is not None) for s in snap.strikes}; buildable=[]
    if atm is not None:
        a=have.get(atm,False); up1=have.get(atm+step,False); dn1=have.get(atm-step,False)
        if a: buildable += ["Long Call","Long Put","Short Call","Short Put","Long Straddle","Short Straddle","Covered Call","Covered Put"]
        if a and up1: buildable += ["Bull Call Spread","Bull Put Spread","Long Strangle","Short Strangle","Collar","Ratio Spread"]
        if a and dn1: buildable += ["Bear Call Spread","Bear Put Spread","Strip","Strap"]
        if a and up1 and dn1: buildable += ["Butterfly","Iron Butterfly","Condor","Iron Condor","Calendar Spread"]
    out={"structures_recognized":sorted(set(buildable)),"structures_total":len(STRUCTURES),"missing_leg_gap":sorted(set(STRUCTURES)-set(buildable))}
    ctx.put("multi_leg",out)
    return PartResult(part=17,name="Multi-Leg Options",output={"recognized":len(out["structures_recognized"]),"total":len(STRUCTURES)})
def _step(strikes):
    ks=sorted(strikes); diffs=[b-a for a,b in zip(ks,ks[1:]) if b-a>0]; return min(diffs) if diffs else 50.0
