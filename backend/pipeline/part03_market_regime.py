"""Part 03 — Market Regime."""
from __future__ import annotations
from backend.models import Regime
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import ema, vwap

def classify_regime(prices,spot,atr_pct)->tuple[Regime,float]:
    if not prices or spot is None or len(prices)<5: return Regime.UNCERTAIN,0.0
    e20=ema(prices,20) or spot; e50=ema(prices,50) or spot
    vw=vwap(prices,[1.0]*len(prices)) or spot; slope=(e20-e50)/e50 if e50 else 0.0
    above=(spot-vw)/vw if vw else 0.0; vol=atr_pct or 0.0
    if vol>1.2:return Regime.HIGH_VOL,vol
    if vol<0.25:return Regime.LOW_VOL,vol
    if slope>0.0015 and above>0:return Regime.STRONG_BULL,slope
    if slope<-0.0015 and above<0:return Regime.STRONG_BEAR,slope
    if abs(slope)<0.0005:return Regime.SIDEWAYS,slope
    return (Regime.BREAKOUT if above>0.002 else Regime.MEAN_REVERSION),slope

@register(3)
def run(ctx:PipelineContext)->PartResult:
    prices=list(ctx.price_history); spot=ctx.get("spot")
    regime,score=classify_regime(prices,spot,ctx.get("atr_pct"))
    ctx.put("regime",regime.value); ctx.put("regime_score",score)
    return PartResult(part=3,name="Market Regime",output={"regime":regime.value,"score":round(score,6)})
