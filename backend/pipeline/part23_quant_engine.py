"""Part 23 — Quant Engine (z-score, rolling z, percentiles, mean-reversion, momentum factor, relative strength, correlation, beta, vol-adjusted momentum, return distribution, outlier/anomaly, normalised momentum/volatility/OI). """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import percentile_rank, realized_vol, returns_from_prices, rolling_correlation, rolling_zscore, zscore
@register(23)
def run(ctx: PipelineContext)->PartResult:
    prices=list(ctx.price_history); rets=returns_from_prices(prices); spot=ctx.get("spot"); oi=ctx.get("oi") or {}; out={"data_gap":False}
    if len(prices)<5:
        out["data_gap"]=True; ctx.put("quant",out); return PartResult(part=23,name="Quant Engine",data_gap=True)
    rz=rolling_zscore(prices,20); pct=percentile_rank(prices[-1],prices); mom=(prices[-1]/prices[max(0,len(prices)-20)]-1) if len(prices)>20 else (prices[-1]/prices[0]-1); vol=realized_vol(rets,20) or 0.0
    out.update({"zscore":zscore(prices[-1],prices),"rolling_z":rz,"percentile":pct,"momentum_factor":mom,"vol_adjusted_momentum":(mom/vol) if vol else None,"mean_reversion_signal":bool(rz is not None and abs(rz)>2),"outlier":bool(pct is not None and (pct>97 or pct<3)),"anomaly":bool(rz is not None and abs(rz)>3),"return_mean":float(rets.mean()) if len(rets) else 0.0,"return_std":float(rets.std()) if len(rets) else 0.0,"norm_momentum":_norm(mom,0.01),"norm_volatility":_norm(vol,0.3),"norm_oi_bias":_norm(oi.get("bias",0.0),0.5),"rolling_correlation":rolling_correlation(prices,prices,20)})
    ctx.put("quant",out); return PartResult(part=23,name="Quant Engine",output={k:(round(v,5) if isinstance(v,float) else v) for k,v in out.items()})
def _norm(x:float,scale:float)->float:
    if not scale:return 0.0
    return max(-1.0,min(1.0,x/scale))
