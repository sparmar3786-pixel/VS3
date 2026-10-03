"""AI hallucination guard and closed structured-output contract."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

VERDICT_VOCABULARY: Set[str] = {"CALL BUY", "PUT BUY", "WAIT", "NO QUALIFYING TRADE"}
FORBIDDEN_FIELDS = {"strike","entry","stop_loss","sl","target","targets","take_profit","tp","position_size","quantity"}

LAYER_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type":"object",
    "properties":{
        "layer":{"type":"string"},"agrees":{"type":"boolean"},"confidence":{"type":"number"},
        "concerns":{"type":"array","items":{"type":"string"}},
        "flagged_strikes":{"type":"array","items":{"type":"number"}},
        "verdict_recommendation":{"type":["string","null"]},"notes":{"type":"string"},
    },
    "required":["layer","agrees","concerns"],
}

@dataclass
class GuardResult:
    ok: bool
    issues: List[str] = field(default_factory=list)
    sanitized: Dict[str, Any] = field(default_factory=dict)

class HallucinationGuard:
    def __init__(self, allowed_strikes: Optional[Set[float]] = None) -> None:
        self.allowed_strikes={round(s,2) for s in (allowed_strikes or set())}

    def check(self, raw: Any) -> GuardResult:
        issues: List[str]=[]
        if not isinstance(raw,dict):
            return GuardResult(False,["output is not a JSON object"],{})
        invented=[k for k in raw if k.lower() in FORBIDDEN_FIELDS]
        if invented: issues.append(f"guard: stripped invented trade fields {invented}")
        flagged=[]
        for s in raw.get("flagged_strikes",[]) or []:
            try: sv=round(float(s),2)
            except (TypeError,ValueError): continue
            if self.allowed_strikes and sv not in self.allowed_strikes:
                issues.append(f"guard: dropped non-existent strike {sv}"); continue
            flagged.append(sv)
        verdict=raw.get("verdict_recommendation")
        if isinstance(verdict,str):
            vv=verdict.strip().upper()
            if vv not in VERDICT_VOCABULARY:
                issues.append(f"guard: nulled out-of-vocabulary verdict {verdict!r}"); verdict=None
            else: verdict=vv
        else: verdict=None
        try: conf=max(0.0,min(1.0,float(raw.get("confidence")))) if raw.get("confidence") is not None else 0.5
        except (TypeError,ValueError): conf=0.5
        sanitized={"layer":str(raw.get("layer","unknown")),"agrees":bool(raw.get("agrees",False)),
                   "confidence":conf,"concerns":[str(c) for c in (raw.get("concerns",[]) or [])][:10],
                   "flagged_strikes":flagged,"verdict_recommendation":verdict,"notes":str(raw.get("notes",""))[:800]}
        return GuardResult(len(issues)==0,issues,sanitized)

def decides_wait_override(layer_outputs: List[Dict[str,Any]], min_wait_layers:int=3)->bool:
    if not layer_outputs:return False
    l6=next((o for o in layer_outputs if str(o.get("layer","")).startswith("L6")),None)
    if l6 and l6.get("verdict_recommendation")=="WAIT":return True
    return sum(1 for o in layer_outputs if o.get("verdict_recommendation")=="WAIT")>=min_wait_layers
