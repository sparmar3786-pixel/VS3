"""Pipeline plumbing: PartResult, the part registry and the 32-part name map.

Every part module defines a single run(ctx) function decorated with @register(n)
so the orchestrator can execute the pipeline in strict numeric order.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict

if TYPE_CHECKING:
    from backend.pipeline.context import PipelineContext

PART_NAMES: Dict[int, str] = {
    1: "Data Input", 2: "Data Quality Engine", 3: "Market Regime",
    4: "Price Action", 5: "Indicators", 6: "Option OI Engine",
    7: "Premium + Volume Engine", 8: "Seller Pressure Engine",
    9: "CE Engine", 10: "PE Engine", 11: "Opposite-Side Override",
    12: "Strike Engine", 13: "Support / Resistance (context only)",
    14: "Greeks Engine", 15: "Volatility Surface Engine", 16: "Order Flow Engine",
    17: "Multi-Leg Options", 18: "Expiry Engine", 19: "Liquidity Engine",
    20: "Trap Engine", 21: "Cross-Index Engine", 22: "Time Engine",
    23: "Quant Engine", 24: "Entry Engine", 25: "Risk Engine",
    26: "Confidence Engine", 27: "Strategy Conflict Engine",
    28: "Signal Quality Filter", 29: "Backtest Engine", 30: "Strategy Memory",
    31: "6-AI Validation", 32: "Final Decision",
}
ADVANCED_PARTS = {15, 16, 17, 21}

@dataclass
class PartResult:
    part: int
    name: str
    ok: bool = True
    data_gap: bool = False
    skipped: bool = False
    output: Dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

PartFn = Callable[["PipelineContext"], PartResult]
REGISTRY: Dict[int, PartFn] = {}

def register(part: int):
    def deco(fn: PartFn) -> PartFn:
        REGISTRY[part] = fn
        fn._part = part  # type: ignore[attr-defined]
        return fn
    return deco

def get_part(part: int) -> PartFn | None:
    return REGISTRY.get(part)
