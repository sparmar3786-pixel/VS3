"""Canonical data models for nse-ai-terminal (pydantic v2).

This module defines the *single* shared vocabulary used by every layer:
brokers emit :class:`Tick` and :class:`Snapshot`; engines consume them and
emit :class:`StrategyResult`, :class:`TradePlan` and :class:`Decision`.

HONESTY NOTE
------------
`confidence` is a heuristic 0..1 score, NOT a probability and NOT a win rate.
A real win rate can only come from a validated historical backtest of a specific
setup on real data. Nothing here should be read as a performance promise.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================ enums ============================

class Side(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class OIClassification(str, Enum):
    """Run93 core 2x2 (premium x OI)."""
    LONG_BUILDUP = "LONG_BUILDUP"
    SHORT_BUILDUP = "SHORT_BUILDUP"
    SHORT_COVERING = "SHORT_COVERING"
    LONG_UNWINDING = "LONG_UNWINDING"
    NEUTRAL = "NEUTRAL"


class Regime(str, Enum):
    STRONG_BULL = "STRONG_BULL"
    STRONG_BEAR = "STRONG_BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"
    BREAKOUT = "BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"
    EXPIRY_COMPRESSION = "EXPIRY_COMPRESSION"
    EXPANSION = "EXPANSION"
    UNCERTAIN = "UNCERTAIN"


class Verdict(str, Enum):
    """Closed vocabulary for the final decision. Never add forced CALL/PUT."""
    CALL_BUY = "CALL BUY"
    PUT_BUY = "PUT BUY"
    WAIT = "WAIT"
    NO_QUALIFYING_TRADE = "NO QUALIFYING TRADE"


class DataQualityFlag(str, Enum):
    OK = "OK"
    STALE = "STALE"
    MISSING_OI = "MISSING_OI"
    MISSING_VOLUME = "MISSING_VOLUME"
    DUPLICATE = "DUPLICATE"
    ABNORMAL = "ABNORMAL"
    EXCHANGE_MISMATCH = "EXCHANGE_MISMATCH"
    INVALID_STRIKE = "INVALID_STRIKE"
    GAP = "GAP"
    LATENCY = "LATENCY"
    OUT_OF_ORDER = "OUT_OF_ORDER"


class OverrideAction(str, Enum):
    BLOCK = "BLOCK"
    EXIT = "EXIT"
    REVERSAL_WATCH = "REVERSAL_WATCH"
    NONE = "NONE"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================ market data ============================

class Tick(BaseModel):
    """A normalised market tick (canonical across all data sources)."""

    symbol: str
    exchange: str = "NSE"
    token: Optional[str] = None
    ltp: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str = "unknown"

    @property
    def mid(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2.0
        return None

    @property
    def spread(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None


class StrikeSnapshot(BaseModel):
    """One strike row of the option chain (CE + PE), canonical fields."""

    strike: float
    is_atm: bool = False

    ce_ltp: Optional[float] = None
    ce_oi: Optional[int] = None
    ce_oi_change: Optional[int] = None
    ce_volume: Optional[int] = None
    ce_iv: Optional[float] = None
    ce_delta: Optional[float] = None
    ce_gamma: Optional[float] = None
    ce_theta: Optional[float] = None
    ce_vega: Optional[float] = None
    ce_bid: Optional[float] = None
    ce_ask: Optional[float] = None
    ce_prev_ltp: Optional[float] = None

    pe_ltp: Optional[float] = None
    pe_oi: Optional[int] = None
    pe_oi_change: Optional[int] = None
    pe_volume: Optional[int] = None
    pe_iv: Optional[float] = None
    pe_delta: Optional[float] = None
    pe_gamma: Optional[float] = None
    pe_theta: Optional[float] = None
    pe_vega: Optional[float] = None
    pe_bid: Optional[float] = None
    pe_ask: Optional[float] = None
    pe_prev_ltp: Optional[float] = None

    def ce(self) -> Dict[str, Any]:
        return {
            "ltp": self.ce_ltp, "oi": self.ce_oi, "oi_change": self.ce_oi_change,
            "volume": self.ce_volume, "iv": self.ce_iv, "delta": self.ce_delta,
            "gamma": self.ce_gamma, "theta": self.ce_theta, "vega": self.ce_vega,
            "bid": self.ce_bid, "ask": self.ce_ask, "prev_ltp": self.ce_prev_ltp,
        }

    def pe(self) -> Dict[str, Any]:
        return {
            "ltp": self.pe_ltp, "oi": self.pe_oi, "oi_change": self.pe_oi_change,
            "volume": self.pe_volume, "iv": self.pe_iv, "delta": self.pe_delta,
            "gamma": self.pe_gamma, "theta": self.pe_theta, "vega": self.pe_vega,
            "bid": self.pe_bid, "ask": self.pe_ask, "prev_ltp": self.pe_prev_ltp,
        }


class Snapshot(BaseModel):
    """A full point-in-time option-chain snapshot for one index/expiry."""

    index: str
    expiry: str = ""
    spot: Optional[float] = None
    atm_strike: Optional[float] = None
    strikes: List[StrikeSnapshot] = Field(default_factory=list)
    prev_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    pdh: Optional[float] = None
    pdl: Optional[float] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str = "unknown"
    data_quality: Optional["DataQualityReport"] = None

    def by_strike(self) -> Dict[float, StrikeSnapshot]:
        return {s.strike: s for s in self.strikes}

    def atm(self) -> Optional[StrikeSnapshot]:
        if self.atm_strike is None:
            return None
        return self.by_strike().get(self.atm_strike)


class DataQualityReport(BaseModel):
    """Result of the data-quality gate (part 02)."""

    passed: bool = True
    flags: List[DataQualityFlag] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    age_sec: Optional[float] = None
    checked_at: datetime = Field(default_factory=_utcnow)

    def fail(self, flag: DataQualityFlag, reason: str) -> "DataQualityReport":
        self.passed = False
        self.flags.append(flag)
        self.reasons.append(reason)
        return self


# ============================ strategy layer ============================

class StrategyMeta(BaseModel):
    """Static metadata for a registered strategy module."""

    id: str
    number: int
    name: str
    family: str
    inputs: List[str] = Field(default_factory=list)
    math: str = ""
    required_data: List[str] = Field(default_factory=list)
    output: str = ""
    failure_conditions: List[str] = Field(default_factory=list)
    advanced: bool = False
    implemented: bool = True


class StrategyResult(BaseModel):
    """Runtime output of evaluating one strategy against a context."""

    strategy_id: str
    number: int
    name: str
    family: str
    fired: bool = False
    side: Optional[Side] = None
    score: float = 0.0
    confidence: float = 0.0
    evidence: Dict[str, Any] = Field(default_factory=dict)
    data_gap: bool = False
    reason: str = ""
    advanced: bool = False


# ============================ decision layer ============================

class TradePlan(BaseModel):
    """A complete, executable trade plan (paper by default)."""

    plan_id: str
    index: str
    side: Side
    strike: float
    option_type: str
    entry: float
    stop_loss: float
    targets: List[float] = Field(default_factory=list)
    trailing_sl_plan: str = ""
    time_exit: str = ""
    rr: float = 0.0
    position_size: int = 0
    confidence: float = 0.0
    strategy_ids: List[str] = Field(default_factory=list)
    regime: Optional[Regime] = None
    rationale: List[str] = Field(default_factory=list)
    suppressed: bool = False
    suppression_reason: str = ""


class Decision(BaseModel):
    """Final per-index decision produced by part 32."""

    index: str
    verdict: Verdict = Verdict.WAIT
    plans: List[TradePlan] = Field(default_factory=list)
    plans_qualifying: int = 0
    plans_suppressed: int = 0
    suppression_reasons: List[str] = Field(default_factory=list)
    data_quality: Optional[DataQualityReport] = None
    regime: Optional[Regime] = None
    override: OverrideAction = OverrideAction.NONE
    override_reason: str = ""
    ai_summary: Optional[Dict[str, Any]] = None
    notes: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)


Snapshot.model_rebuild()
