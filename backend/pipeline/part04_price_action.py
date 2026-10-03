"""Part 04 — Price Action."""
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

def _swings(prices:list[float],look:int=2):
    highs=[]; lows=[]
    for i in range(look,len(prices)-look):
        window=prices[i-look:i+look+1]
        if prices[i]==max(window): highs.append(prices[i])
        if prices[i]==min(window): lows.append(prices[i])
    return highs,lows

@register(4)
def run(ctx:PipelineContext)->PartResult:
    prices=list(ctx.price_history)
    out={"hh_hl":False,"lh_ll":False,"bos":False,"choch":False,"last_high":None,"last_low":None}
    if len(prices)>=10:
        highs,lows=_swings(prices)
        if len(highs)>=2 and len(lows)>=2:
            out["hh_hl"]=highs[-1]>highs[-2] and lows[-1]>lows[-2]
            out["lh_ll"]=highs[-1]<highs[-2] and lows[-1]<lows[-2]
        if highs: out["last_high"]=highs[-1]
        if lows: out["last_low"]=lows[-1]
        spot=prices[-1]
        if highs and spot>highs[-1]: out["bos"]=True
        if lows and spot<lows[-1]: out["choch"]=True
    ctx.put("price_action",out)
    return PartResult(part=4,name="Price Action",output=out)
