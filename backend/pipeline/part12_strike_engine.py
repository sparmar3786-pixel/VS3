"""Part 12 — Strike Engine."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

def _step(strikes):
    ks=sorted(strikes); d=[b-a for a,b in zip(ks,ks[1:]) if b-a>0]
    return min(d) if d else 50.0

@register(12)
def run(ctx:PipelineContext)->PartResult:
    snap=ctx.snapshot; spot=snap.spot or ctx.get("spot"); atm=ctx.get("atm_strike")
    step=_step([s.strike for s in snap.strikes])
    if atm is None and spot is not None: atm=round(spot/step)*step
    band=lambda n:[atm+i*step for i in range(-n,n+1)] if atm is not None else []
    ce_oi={s.strike:s.ce_oi or 0 for s in snap.strikes}; pe_oi={s.strike:s.pe_oi or 0 for s in snap.strikes}
    ce_coi={s.strike:s.ce_oi_change or 0 for s in snap.strikes}; pe_coi={s.strike:s.pe_oi_change or 0 for s in snap.strikes}
    max_ce=max(ce_oi,key=ce_oi.get) if ce_oi else None; max_pe=max(pe_oi,key=pe_oi.get) if pe_oi else None
    out={"atm":atm,"step":step,"atm_pm_3":band(3),"atm_pm_5":band(5),
         "max_ce_oi_strike":max_ce,"max_pe_oi_strike":max_pe,
         "max_ce_change_oi":max(ce_coi,key=ce_coi.get) if ce_coi else None,
         "max_pe_change_oi":max(pe_coi,key=pe_coi.get) if pe_coi else None,
         "moneyness":"ATM" if spot and atm and abs(spot-atm)<=step/2 else ("ITM" if spot and atm and spot>atm else "OTM")}
    ctx.put("strike_engine",out)
    return PartResult(part=12,name="Strike Engine",output={k:v for k,v in out.items() if k not in ("atm_pm_3","atm_pm_5")})
