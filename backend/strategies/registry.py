"""Strategy registry — single entry point for catalogue + optional advanced modules."""
from __future__ import annotations

from typing import List, Optional

from backend.models import StrategyMeta, StrategyResult
from backend.pipeline.context import PipelineContext
from backend.strategies.advanced_modules import ADVANCED_COUNT, build_advanced
from backend.strategies.base import Strategy
from backend.strategies.catalog import build_meta, module_names
from backend.strategies.implementations_advanced import FAMILY_EVALUATORS as ADV_EVALS
from backend.strategies.implementations_core import FAMILY_EVALUATORS as CORE_EVALS

_EVALS = {**CORE_EVALS, **ADV_EVALS}


def _fallback(meta: StrategyMeta, ctx: PipelineContext) -> StrategyResult:
    return StrategyResult(
        strategy_id=meta.id,
        number=meta.number,
        name=meta.name,
        family=meta.family,
        fired=False,
        data_gap=True,
        reason="no evaluator bound",
        advanced=meta.advanced,
    )


def _build() -> List[Strategy]:
    strategies: List[Strategy] = []
    for meta in build_meta():
        strategies.append(Strategy(meta, _EVALS.get(meta.family, _fallback)))
    strategies.extend(build_advanced())
    return strategies


_REGISTRY: Optional[List[Strategy]] = None


def registry() -> List[Strategy]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build()
    return _REGISTRY


def all_meta() -> List[StrategyMeta]:
    return [s.meta for s in registry()]


def get_meta(sid: str) -> Optional[StrategyMeta]:
    key = str(sid).strip().upper()
    raw = str(sid).strip()
    for s in registry():
        if s.meta.id.upper() == key or str(s.meta.number) == raw:
            return s.meta
    return None


def search_meta(q: str = "", family: str = "") -> List[StrategyMeta]:
    ql, fl = q.lower().strip(), family.lower().strip()
    out: List[StrategyMeta] = []
    for m in all_meta():
        if fl and fl not in m.family.lower():
            continue
        if ql and not (
            ql in m.name.lower()
            or ql in m.family.lower()
            or ql in m.id.lower()
        ):
            continue
        out.append(m)
    return out


def evaluate_all(ctx: PipelineContext) -> List[StrategyResult]:
    """Evaluate all applicable strategies; advanced modules require the gate."""
    out: List[StrategyResult] = []
    for s in registry():
        if s.meta.advanced and not ctx.advanced:
            continue
        out.append(s.evaluate(ctx))
    return out


def coverage_stats() -> dict:
    catalogue = module_names()
    metas = all_meta()
    return {
        "catalogue_modules": len(catalogue),
        "advanced_modules": ADVANCED_COUNT,
        "total_registered": len(metas),
        "families": len({m.family for m in metas}),
        "advanced_flagged": sum(1 for m in metas if m.advanced),
    }
