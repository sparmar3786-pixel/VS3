"""Part 05 — Indicators."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import atr,bollinger,ema,macd,rsi,vwap

@register(5)
def run(ctx:PipelineContext)->PartResult:
    prices=list(ctx.price_history); vols=[1.0]*len(prices)
    highs=[p*1.002 for p in prices]; lows=[p*0.998 for p in prices]
    ind={"ema8":ema(prices,8),"ema13":ema(prices,13),"ema20":ema(prices,20),
         "ema50":ema(prices,50),"vwap":vwap(prices,vols),"rsi":rsi(prices,14),
         "macd":macd(prices),"atr":atr(highs,lows,prices,14),
         "boll":bollinger(prices,20,2.0)}
    spot=ctx.get("spot") or (prices[-1] if prices else None)
    ind["atr_pct"]=(ind["atr"]/spot*100.0) if ind["atr"] and spot else None
    ctx.put("indicators",ind); ctx.put("atr_pct",ind["atr_pct"])
    return PartResult(part=5,name="Indicators",output=ind)
