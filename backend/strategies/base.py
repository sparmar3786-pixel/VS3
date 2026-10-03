"""Strategy abstraction: metadata + a bound evaluator."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable
from backend.models import StrategyMeta, StrategyResult

if TYPE_CHECKING:
    from backend.pipeline.context import PipelineContext

Evaluator = Callable[[StrategyMeta, "PipelineContext"], StrategyResult]

@dataclass
class Strategy:
    """A registered strategy module = static metadata + a runnable evaluator."""
    meta: StrategyMeta
    evaluator: Evaluator

    def evaluate(self, ctx: "PipelineContext") -> StrategyResult:
        try:
            return self.evaluator(self.meta, ctx)
        except Exception as e:
            return StrategyResult(
                strategy_id=self.meta.id,
                number=self.meta.number,
                name=self.meta.name,
                family=self.meta.family,
                fired=False,
                data_gap=True,
                reason=f"evaluator error: {e}",
                advanced=self.meta.advanced,
            )
