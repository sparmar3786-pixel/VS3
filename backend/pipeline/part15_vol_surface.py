"""Part 15 — Volatility Surface Engine (ADVANCED)."""
from __future__ import annotations
import numpy as np
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(15)
def run(ctx:PipelineContext)->PartResult:
    if not ctx.advanced:return PartResult(part=15,name="Volatility Surface Engine",skipped=True,notes=["advanced engine disabled"])
    snap=ctx.snapshot; spot=snap.spot or 0.; pts=[(s.strike,s.ce_iv) for s in snap.strikes if s.ce_iv and spot]
    if len(pts)<5 or spot<=0:
        ctx.put("vol_surface",{"data_gap":True})
        return PartResult(part=15,name="Volatility Surface Engine",data_gap=True,notes=["insufficient IV points for a surface"])
    x=np.array([(k-spot)/spot for k,_ in pts]); y=np.array([iv for _,iv in pts])
    slope=float(np.polyfit(x,y,1)[0]); curv=float(np.polyfit(x,y,2)[0]); atm=float(np.interp(0,x,y))
    otm=float(np.mean(y[x>.01])) if (x>.01).any() else atm; prev=ctx.get("_prev_surface"); shift=atm-prev if prev is not None else 0.
    out={"iv_slope":slope,"iv_curvature":curv,"atm_iv":atm,"otm_vs_atm_iv":otm-atm,"smile":curv>0,"skew":slope,
         "surface_shift":shift,"term_structure":{"slope":None,"inverted":None,"note":"needs multiple expiries; DATA_GAP if only one"},
         "moneyness_iv_points":len(pts)}
    ctx.put("_prev_surface",atm); ctx.put("vol_surface",out)
    return PartResult(part=15,name="Volatility Surface Engine",output=out)
