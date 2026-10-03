"""Part 18 — Expiry Engine (days-to-expiry, weekly/monthly behaviour). """
from __future__ import annotations
from datetime import datetime, timezone
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
_MONTHS={m:i+1 for i,m in enumerate(["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"])}
def days_to_expiry(expiry: str)->int|None:
    if not expiry:return None
    for fmt in ("%d%b%Y","%d-%b-%Y","%d%b%y"):
        try:return max(0,(datetime.strptime(expiry.upper(),fmt).replace(tzinfo=timezone.utc)-datetime.now(timezone.utc)).days)
        except ValueError:continue
    return None
@register(18)
def run(ctx: PipelineContext)->PartResult:
    expiry=ctx.get("expiry") or ctx.snapshot.expiry; dte=days_to_expiry(expiry)
    out={"expiry":expiry,"days_to_expiry":dte,"is_expiry_day":dte==0,"expiry_week":dte is not None and dte<=3,"gamma_risk_zone":dte is not None and dte<=1}
    ctx.put("expiry",out); return PartResult(part=18,name="Expiry Engine",output=out)
