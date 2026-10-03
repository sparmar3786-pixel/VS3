"""Concrete deterministic evaluators for core strategy families 1-219."""
from __future__ import annotations
from backend.models import Regime, Side, StrategyResult
from backend.pipeline.context import PipelineContext
from backend.quant.option_math import clamp
from backend.strategies.framework import make_context_evaluator, make_evaluator

def _g(c,k,d=None): return c.get(k) or d or {}
def _oi(c): return _g(c,"oi")
def _ind(c): return _g(c,"indicators")
def _pv(c): return _g(c,"premium_volume")
def _pa(c): return _g(c,"price_action")
def _st(c): return _g(c,"strike_engine")
def _sp(c): return _g(c,"seller_pressure")
def _ce(c): return _g(c,"ce_engine")
def _pe(c): return _g(c,"pe_engine")
def _gr(c): return _g(c,"greeks")
def _lq(c): return _g(c,"liquidity")
def _tr(c): return _g(c,"trap")
def _of(c): return _g(c,"order_flow")
def _bias(c): return float(_oi(c).get("bias",0.0))
def _counts(c): return _oi(c).get("counts") or {}

def _oi_default(c): return clamp(_bias(c),-1,1),{"oi_bias":_bias(c)}
def _oi_build(c):
    x=_counts(c); lb=x.get("LONG_BUILDUP",0); sb=x.get("SHORT_BUILDUP",0)
    return clamp((lb-sb)/max(1,lb+sb),-1,1),{"long_buildup":lb,"short_buildup":sb}
def _oi_cover(c):
    x=_counts(c); sc=x.get("SHORT_COVERING",0); lu=x.get("LONG_UNWINDING",0)
    return clamp((sc-lu)/max(1,sc+lu),-1,1),{"short_covering":sc,"long_unwinding":lu}
F1={"buildup":_oi_build,"covering":_oi_cover,"unwinding":_oi_cover,"flush":_oi_cover,"wall":_oi_default,"cluster":_oi_default,"migration":_oi_default,"rotation":_oi_default,"maximum":_oi_default,"velocity":_oi_default,"acceleration":_oi_default,"concentration":_oi_default}
OI_EVAL=make_evaluator("OI / Position",F1,_oi_default)

def _prem(c): return clamp(float(_pv(c).get("bias",0)), -1,1),dict(_pv(c))
def _prem_div(c): return clamp(float(_pv(c).get("bias",0))-_bias(c),-1,1),{"premium_bias":_pv(c).get("bias"),"oi_bias":_bias(c)}
PREMIUM_EVAL=make_evaluator("Premium / Price",{"momentum":_prem,"velocity":_prem,"acceleration":_prem,"divergence":_prem_div,"reversal":_prem},_prem)

def _vol(c):
    s=float(_pv(c).get("ce_vol_share",.5)); return clamp((s-.5)*2,-1,1),{"ce_vol_share":s}
VOLUME_EVAL=make_evaluator("Volume",{"spike":_vol,"explosion":_vol,"confirmation":_vol,"expansion":_vol},_vol)

def _cepe(c): return clamp((float(_ce(c).get("score",0))+float(_pe(c).get("score",0)))/6,-1,1),{"ce":_ce(c).get("score"),"pe":_pe(c).get("score")}
CEPE_EVAL=make_evaluator("CE/PE",{"engine":_cepe,"imbalance":_cepe,"spread":_cepe,"rotation":_cepe,"trap":_cepe},_cepe)

def _seller(c): return clamp(float(_sp(c).get("seller_pressure",0)),-1,1),{"seller_pressure":_sp(c).get("seller_pressure")}
SELLER_EVAL=make_evaluator("Short-Covering / Seller",{"covering":_seller,"seller":_seller,"absorption":_seller,"exhaustion":_seller},_seller)

def _strike(c):
    st=_st(c); spot=c.get("spot"); atm=st.get("atm")
    if not spot or not atm:return None,{}
    return clamp((spot-atm)/max(1,st.get("step",50))*.5,-1,1),{"spot":spot,"atm":atm}
STRIKE_EVAL=make_evaluator("Strike / Option-Chain",{"atm":_strike,"itm":_strike,"otm":_strike,"cluster":_strike,"migration":_strike,"wall":_strike,"ranking":_strike},_strike)

SR_EVAL=make_context_evaluator("Support/Resistance")

def _ema(c):
    i=_ind(c); a,b=i.get("ema8"),i.get("ema13")
    if a is None or b is None:return None,{}
    return clamp((a-b)/max(1e-6,b)*200,-1,1),{"ema8":a,"ema13":b}
def _vwap(c):
    i=_ind(c); s=c.get("spot"); v=i.get("vwap")
    if not s or not v:return None,{}
    return clamp((s-v)/v*100,-1,1),{"spot":s,"vwap":v}
TREND_EVAL=make_evaluator("Trend/Price Action",{"ema":_ema,"vwap":_vwap,"trend":_ema,"structure":_ema,"breakout":_ema,"breakdown":_ema},_ema)

def _rsi(c):
    r=_ind(c).get("rsi")
    if r is None:return None,{}
    return clamp((50-r)/50,-1,1),{"rsi":r}
def _macd(c):
    m=_ind(c).get("macd")
    if not m:return None,{}
    return clamp(float(m.get("hist",0))/max(1e-6,abs(float(m.get("macd",1)))),-1,1),m
OSC_EVAL=make_evaluator("RSI/MACD/Volatility",{"rsi":_rsi,"macd":_macd,"crossover":_macd,"divergence":_macd},_rsi)

def _delta(c):
    d=_gr(c).get("atm_ce_delta")
    if d is None:return None,_gr(c)
    return clamp((d-.5)*2,-1,1),{"atm_ce_delta":d}
def _iv(c):
    d=_gr(c).get("iv_minus_rv")
    if d is None:return None,_gr(c)
    return clamp(-d*2,-1,1),{"iv_minus_rv":d}
GREEKS_EVAL=make_evaluator("Greeks/IV",{"delta":_delta,"iv":_iv,"crush":_iv,"realized":_iv},_delta)

def _expiry(c):
    e=c.get("expiry") or {}; d=e.get("days_to_expiry")
    if d is None:return None,e
    return clamp((3-d)/3*.3,-1,1),{"dte":d}
EXPIRY_EVAL=make_evaluator("Expiry",{"pin":lambda c:(.3 if (c.get("expiry") or {}).get("is_expiry_day") else 0), "expiry-day":lambda c:(.3 if (c.get("expiry") or {}).get("is_expiry_day") else 0),"days-to-expiry":_expiry,"compression":_expiry},_expiry)

def _liq(c):
    s=_lq(c).get("liquidity_score")
    if s is None:return None,_lq(c)
    return clamp(float(s)-.5,-1,1),_lq(c)
LIQUIDITY_EVAL=make_evaluator("Liquidity/Microstructure",{"liquidity":_liq,"spread":_liq,"tick":_liq,"aggressive":_liq},_liq)

def _trap(c):
    t=_tr(c).get("traps",{})
    return (-.5 if t.get("bull_trap") else .5 if t.get("bear_trap") else 0),t
TRAP_EVAL=make_evaluator("Trap/Reversal",{"bull":_trap,"bear":_trap,"trap":_trap,"reversal":_trap,"false":_trap},_trap)

def regime_evaluator(meta,ctx):
    name=meta.name.lower(); cur=ctx.get("regime")
    mapping={"strong bull":Regime.STRONG_BULL.value,"strong bear":Regime.STRONG_BEAR.value,"sideways":Regime.SIDEWAYS.value,"high-volatility":Regime.HIGH_VOL.value,"low-volatility":Regime.LOW_VOL.value,"breakout":Regime.BREAKOUT.value,"mean-reversion":Regime.MEAN_REVERSION.value,"compression":Regime.EXPIRY_COMPRESSION.value,"expansion":Regime.EXPANSION.value}
    target=next((v for k,v in mapping.items() if k in name),None)
    fired=bool(target and cur==target)
    return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family="Market Regime",fired=fired,side=None,score=.4 if fired else 0,confidence=.4 if fired else 0,evidence={"regime":cur,"target":target},reason="regime match" if fired else "regime not matched",advanced=meta.advanced)
REGIME_EVAL=regime_evaluator

EVALUATORS={"OI / Position":OI_EVAL,"Premium / Price":PREMIUM_EVAL,"Volume":VOLUME_EVAL,"CE/PE":CEPE_EVAL,"Short-Covering / Seller":SELLER_EVAL,"Strike / Option-Chain":STRIKE_EVAL,"Support/Resistance":SR_EVAL,"Trend/Price Action":TREND_EVAL,"RSI/MACD/Volatility":OSC_EVAL,"Greeks/IV":GREEKS_EVAL,"Expiry":EXPIRY_EVAL,"Liquidity/Microstructure":LIQUIDITY_EVAL,"Trap/Reversal":TRAP_EVAL,"Market Regime":REGIME_EVAL}


# Backward-compatible name expected by the registry.
FAMILY_EVALUATORS = EVALUATORS
