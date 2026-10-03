"""Part 08 — Seller Pressure Engine."""
from __future__ import annotations
from backend.models import OIClassification
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

@register(8)
def run(ctx:PipelineContext)->PartResult:
    oi=ctx.get("oi") or {}; per=oi.get("per_strike") or []
    seller_pressure=0.0; covering_zone=[]
    for row in per:
        if row["ce"]==OIClassification.SHORT_BUILDUP.value:seller_pressure-=1.0
        if row["pe"]==OIClassification.SHORT_BUILDUP.value:seller_pressure+=1.0
        if row["ce"]==OIClassification.SHORT_COVERING.value or row["pe"]==OIClassification.SHORT_COVERING.value:
            covering_zone.append(row["strike"])
    n=max(1,len(per))
    out={"seller_pressure":round(seller_pressure/n,4),"probable_covering_strikes":sorted(set(covering_zone)),
         "note":"probable zone inferred from observable OI/premium; not a hidden-level claim"}
    ctx.put("seller_pressure",out)
    return PartResult(part=8,name="Seller Pressure Engine",output=out)
