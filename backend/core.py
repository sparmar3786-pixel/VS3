from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GateResult:
    ok: bool
    flags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

class DataQualityGate:
    def __init__(self, max_age_seconds: float = 5):
        self.max_age_seconds = float(max_age_seconds)
    def check(self, age_seconds, has_oi=True, has_volume=True, duplicate=False):
        flags=[]; reasons=[]
        if age_seconds > self.max_age_seconds:
            flags.append("STALE"); reasons.append("stale")
        if not has_oi:
            flags.append("MISSING_OI"); reasons.append("OI unavailable")
        if not has_volume:
            flags.append("MISSING_VOLUME"); reasons.append("volume unavailable")
        if duplicate:
            flags.append("DUPLICATE"); reasons.append("duplicate tick")
        return GateResult(not flags, flags, reasons)

class RiskGate:
    def __init__(self, min_rr=1.8):
        self.min_rr=float(min_rr)
    def passes(self, rr):
        return rr is not None and float(rr) >= self.min_rr

@dataclass
class Decision:
    verdict: str
    plans: list[dict]
    suppressed_count: int = 0
    suppression_reasons: list[str] = field(default_factory=list)
    ai_wait_override: bool = False

class DecisionEngine:
    def __init__(self, min_plans=5, risk_gate=None):
        self.min_plans=int(min_plans)
        self.risk_gate=risk_gate or RiskGate()
    def build(self, plans, ai=None):
        candidates=[]
        suppressed=[]
        for p in plans or []:
            if not self.risk_gate.passes(p.get("rr")):
                suppressed.append("RR_GATE")
                continue
            candidates.append(p)
        wait_override=bool(getattr(ai, "wait_override", False))
        return Decision(
            verdict="WAIT" if wait_override else ("NO TRADE" if not candidates else "TRADE"),
            plans=candidates,
            suppressed_count=len(suppressed),
            suppression_reasons=suppressed,
            ai_wait_override=wait_override,
        )
