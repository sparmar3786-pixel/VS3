"""Compatibility catalog for the VS3 master strategy contract.

The canonical strategy definitions live in :mod:`backend.strategy_registry`.
This module exposes the historical object-shaped CORE/ADVANCED interface used
by the contract tests and older consumers.
"""
from __future__ import annotations

from dataclasses import dataclass

from .strategy_registry import STRATEGIES, ADVANCED_STRATEGIES


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    family: str
    tier: str = "core"


CORE = [
    Strategy(
        id=f"S{item["id"]:03d}",
        name=item["name"],
        family=item["family"],
    )
    for item in STRATEGIES
]

# The public master contract defines 25 advanced modules (X378..X402).
# Keep the remaining experimental registry entries available through
# strategy_registry.ALL_STRATEGIES rather than changing this contract.
ADVANCED = [
    Strategy(
        id=f"X{item["id"]:03d}",
        name=item["name"],
        family=item["family"],
        tier="advanced",
    )
    for item in ADVANCED_STRATEGIES[:25]
]

if len(CORE) != 377:
    raise RuntimeError(f"CORE catalog must contain 377 modules, got {len(CORE)}")
if len(ADVANCED) != 25:
    raise RuntimeError(
        f"ADVANCED catalog must contain 25 modules, got {len(ADVANCED)}"
    )
