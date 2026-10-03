"""Shared machinery for turning a catalogue entry into a runnable evaluator."""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple
from backend.models import Side, StrategyMeta, StrategyResult
from backend.quant.option_math import clamp
if TYPE_CHECKING:
    from backend.pipeline.context import PipelineContext
ScoreResult = Tuple[Optional[float], Dict]
MetricFn = Callable[["PipelineContext"], ScoreResult]
GateFn = Callable[["PipelineContext"], Tuple[bool, Dict, Optional[float]]]
THRESHOLD = 0.08
def _pick(name: str, metrics: Dict[str, MetricFn], default: MetricFn) -> MetricFn:
    lname=name.lower()
    for kw,m in metrics.items():
        if kw in lname: return m
    return default
def make_evaluator(family: str, metrics: Dict[str, MetricFn], default: MetricFn):
    def _ev(meta: StrategyMeta, ctx: "PipelineContext") -> StrategyResult:
        try: score,evidence=_pick(meta.name,metrics,default)(ctx)
        except Exception as e:
            return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=False,data_gap=True,reason=f"metric error: {e}",advanced=meta.advanced)
        if score is None:
            return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=False,data_gap=True,reason="required data missing",evidence=evidence or {},advanced=meta.advanced)
        fired=abs(score)>THRESHOLD
        return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=fired,side=(Side.CALL if score>0 else Side.PUT),score=round(score,4),confidence=round(clamp(abs(score)),4),evidence=evidence or {},reason=("fired" if fired else "below threshold"),advanced=meta.advanced)
    return _ev
def make_context_evaluator(family: str):
    def _ev(meta: StrategyMeta,ctx:"PipelineContext")->StrategyResult:
        ev=dict(ctx.get("sr") or {}); ev["context_only"]=True
        return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=False,side=None,score=0.0,confidence=0.0,evidence=ev,reason="context only — never overrides the signal engine",advanced=meta.advanced)
    return _ev
def make_gate_evaluator(family: str, fn: GateFn):
    def _ev(meta: StrategyMeta,ctx:"PipelineContext")->StrategyResult:
        try: ok,evidence,score=fn(ctx)
        except Exception as e:
            return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=False,data_gap=True,reason=f"gate error: {e}",advanced=meta.advanced)
        s=score or 0.0
        return StrategyResult(strategy_id=meta.id,number=meta.number,name=meta.name,family=family,fired=bool(ok),side=(Side.CALL if s>0 else Side.PUT if s<0 else None),score=round(s,4),confidence=round(clamp(abs(s)),4),evidence=evidence or {},reason=("satisfied" if ok else "not satisfied"),advanced=meta.advanced)
    return _ev
