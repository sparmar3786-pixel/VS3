"""The object threaded through every pipeline part."""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional
from backend.config import Settings
from backend.models import Snapshot, StrategyResult, Tick
from backend.pipeline.base import PartResult

@dataclass
class PipelineContext:
    index: str
    snapshot: Snapshot
    settings: Settings
    ticks: Deque[Tick] = field(default_factory=lambda: deque(maxlen=500))
    price_history: Deque[float] = field(default_factory=lambda: deque(maxlen=400))
    oi_history: Deque[float] = field(default_factory=lambda: deque(maxlen=400))
    prev_snapshot: Optional[Snapshot] = None
    state: Dict[str, Any] = field(default_factory=dict)
    results: List[PartResult] = field(default_factory=list)
    strategy_results: List[StrategyResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def put(self, key: str, value: Any) -> None:
        self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def has(self, *keys: str) -> bool:
        return all(k in self.state for k in keys)

    def flag(self, note: str) -> None:
        self.notes.append(note)

    def ensure_strategy_scan(self) -> List[StrategyResult]:
        if not self.strategy_results:
            from backend.strategies.registry import evaluate_all
            self.strategy_results = evaluate_all(self)
        return self.strategy_results

    @property
    def advanced(self) -> bool:
        return self.settings.advanced_enabled

    @property
    def data_quality_ok(self) -> bool:
        dq = self.get("dq")
        return bool(dq is None or getattr(dq, "passed", True))
