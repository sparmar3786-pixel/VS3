from __future__ import annotations
from dataclasses import dataclass,field
from .catalog import CORE,ADVANCED
from .config import get_settings
from .data_sources import SourceRouter
from .strategy_engine import StrategyEngine
@dataclass
class GateResult:
    ok:bool;flags:list[str]=field(default_factory=list);reasons:list[str]=field(default_factory=list)
class DataQualityGate:
    def __init__(self,max_age_seconds=5):self.max_age_seconds=max_age_seconds
    def check(self,age_seconds,has_oi=True,has_volume=True,duplicate=False):
        flags=[];reasons=[]
        if age_seconds>self.max_age_seconds:flags.append("STALE");reasons.append("stale")
        if not has_oi:flags.append("MISSING_OI");reasons.append("OI unavailable")
        if not has_volume:flags.append("MISSING_VOLUME");reasons.append("volume unavailable")
        if duplicate:flags.append("DUPLICATE");reasons.append("duplicate tick")
        return GateResult(not flags,flags,reasons)
class RiskGate:
    def __init__(self,min_rr=1.8):self.min_rr=float(min_rr)
    def passes(self,rr):return rr is not None and float(rr)>=self.min_rr
@dataclass
class AIValidation:
    wait_override:bool=False
    layers:list[dict]=field(default_factory=list)
@dataclass
class Decision:
    verdict:str;plans:list[dict];suppressed_count:int=0;suppression_reasons:list[str]=field(default_factory=list);ai_wait_override:bool=False
    def asdict(self):return {"verdict":self.verdict,"plans":self.plans,"plans_qualifying":len(self.plans),"plans_suppressed":self.suppressed_count,"suppressed_count":self.suppressed_count,"suppression_reasons":self.suppression_reasons,"ai_wait_override":self.ai_wait_override}
class DecisionEngine:
    def __init__(self,min_plans=5,risk_gate=None):self.min_plans=min_plans;self.risk_gate=risk_gate or RiskGate()
    def build(self,plans,ai=None):
        ai=ai or AIValidation();valid=[];sup=[]
        for p in plans:
            if not p.get("strategy_ids"):sup.append("missing exact strategy IDs");continue
            if not self.risk_gate.passes(p.get("rr")):sup.append("R:R below single gate");continue
            valid.append(p)
        if ai.wait_override:return Decision("WAIT",valid,len(sup),sup,True)
        if not valid:return Decision("NO QUALIFYING TRADE",[],len(sup),sup,False)
        sides={p.get("side") for p in valid}
        verdict="CALL BUY" if sides=={"CALL"} else "PUT BUY" if sides=={"PUT"} else "WAIT"
        return Decision(verdict,valid,len(sup),sup,False)
class StrategyRegistry:
    def __init__(self):self._all=CORE+ADVANCED
    def count_core(self):return len(CORE)
    def count_advanced(self):return len(ADVANCED)
    def all(self):return self._all
    def search(self,q=""):
        q=q.lower().strip();return [x for x in self._all if not q or q in x.id.lower() or q in x.name.lower() or q in x.family.lower()]
class TerminalEngine:
    INDICES=["NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY","SENSEX","BANKEX"]
    def __init__(self):
        self.registry=StrategyRegistry();self.risk=RiskGate(get_settings().min_rr);self.snapshots={};self.router=SourceRouter();self.strategies=StrategyEngine(get_settings().advanced_engine)
    def snapshot(self,index):
        if index not in self.INDICES:raise ValueError("unknown index")
        if index not in self.snapshots:
            seeds={"NIFTY":24689.75,"BANKNIFTY":52317.20,"FINNIFTY":23482.10,"MIDCPNIFTY":12345.60,"SENSEX":81742.0,"BANKEX":56210.75}
            spot=seeds[index];step=50 if index not in {"SENSEX","BANKEX"} else 100;atm=round(spot/step)*step;chain=[]
            for i in range(-12,13):
                strike=atm+i*step;chain.append({"strike":strike,"ce_ltp":round(max(.05,100-i*5),2),"ce_oi":58000+abs(i)*3200,"ce_chg_oi":round(-i*1.7,2),"ce_vol":12000+abs(i)*400,"pe_ltp":round(max(.05,100+i*5),2),"pe_oi":42000+abs(i)*3600,"pe_chg_oi":round(i*1.5,2),"pe_vol":10500+abs(i)*350})
            self.snapshots[index]={"index":index,"spot":spot,"atm_strike":atm,"chain":chain,"timestamp":0,"source":"DEMO","data_quality":"OK","regime":"UNCERTAIN","notes":["DEMO DATA — not live market data"]}
        return self.snapshots[index]
    def refresh(self,index):
        return self.snapshot(index)
    def decision(self,index,ai=None):
        snap=self.snapshot(index);results=self.strategies.evaluate(snap);plans=self.strategies.plans(snap,results,self.risk.min_rr)
        d=DecisionEngine(5,self.risk).build(plans,ai);out=d.asdict();out.update({"index":index,"data_quality":snap["data_quality"],"regime":snap["regime"],"source":snap["source"]});return out
