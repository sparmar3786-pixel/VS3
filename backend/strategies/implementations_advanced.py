"""Concrete evaluators for ADVANCED families (numbers 247-377).

Families 15-23 are intentionally deterministic. Context-only families never
qualify a trade; gate families validate already-produced pipeline state.
"""

from __future__ import annotations

from typing import Dict, Tuple

from backend.models import Verdict
from backend.quant.option_math import clamp
from backend.strategies.framework import (
    make_context_evaluator,
    make_evaluator,
    make_gate_evaluator,
)


def _q(c):
    return c.get("quant") or {}


def _cx(c):
    return c.get("cross_index_res") or {}


def _risk(c):
    return c.get("risk") or {}


def _entry(c):
    return c.get("entry") or {}


def _dq(c):
    return c.get("dq")


def _bt(c):
    return c.get("backtest") or {}


def _ai(c):
    return c.get("ai") or {}


def _dec(c):
    return c.get("decision")


def _conf(c):
    return c.get("conflict") or {}


def _sq(c):
    return c.get("signal_quality") or {}


def _liq(c):
    return c.get("liquidity") or {}


# ------------------------------------------------------------------
# family 15: Quant / Statistical


def _m_quant_default(c):
    z = _q(c).get("zscore")
    return (None if z is None else clamp(-z / 3, -1, 1)), _q(c)


def _m_rolling_z(c):
    z = _q(c).get("rolling_z")
    return (None if z is None else clamp(-z / 3, -1, 1)), _q(c)


def _m_mean_rev(c):
    return (0.3 if _q(c).get("mean_reversion_signal") else 0.0), _q(c)


def _m_momentum(c):
    m = _q(c).get("momentum_factor")
    return (None if m is None else clamp(m * 10, -1, 1)), {"momentum": m}


def _m_vol_adj(c):
    m = _q(c).get("vol_adjusted_momentum")
    return (None if m is None else clamp(m, -1, 1)), {"vol_adj_mom": m}


def _m_corr(c):
    r = _q(c).get("rolling_correlation")
    return (None if r is None else clamp(r, -1, 1)), {"corr": r}


def _m_outlier(c):
    return (-0.4 if _q(c).get("outlier") else 0.0), _q(c)


def _m_anomaly(c):
    return (-0.4 if _q(c).get("anomaly") else 0.0), _q(c)


def _m_pct(c):
    p = _q(c).get("percentile")
    return (None if p is None else clamp((50 - p) / 50, -1, 1)), {"percentile": p}


def _m_normalization(c):
    return clamp(_q(c).get("norm_momentum", 0.0), -1, 1), _q(c)


F15 = {
    "z-score": _m_rolling_z,
    "rolling z": _m_rolling_z,
    "mean reversion": _m_mean_rev,
    "momentum factor": _m_momentum,
    "relative strength": _m_momentum,
    "correlation": _m_corr,
    "beta": _m_corr,
    "volatility-adjusted": _m_vol_adj,
    "return distribution": _m_quant_default,
    "outlier": _m_outlier,
    "anomaly": _m_anomaly,
    "percentile": _m_pct,
    "extreme": _m_pct,
    "normalization": _m_normalization,
}
QUANT_EVAL = make_evaluator("Quant/Statistical", F15, _m_quant_default)


# ------------------------------------------------------------------
# family 16: Cross-Index / Breadth


def _m_cross_default(c):
    cx = _cx(c)
    if cx.get("data_gap"):
        return None, cx
    return clamp(cx.get("relative_strength", 0.0), -1, 1), cx


def _m_cross_div(c):
    cx = _cx(c)
    if cx.get("data_gap"):
        return None, cx
    return (0.4 if cx.get("divergence") else 0.0), cx


def _m_cross_lead(c):
    cx = _cx(c)
    if cx.get("data_gap"):
        return None, cx
    return (0.3 if cx.get("leadership") == c.index else 0.0), cx


F16 = {
    "divergence": _m_cross_div,
    "relative": _m_cross_default,
    "leadership": _m_cross_lead,
    "breadth": _m_cross_default,
    "rotation": _m_cross_div,
    "risk-on": _m_cross_default,
    "strength": _m_cross_default,
    "shift": _m_cross_lead,
}
CROSS_EVAL = make_evaluator("Cross-Index/Breadth", F16, _m_cross_default)


# ------------------------------------------------------------------
# family 17: Fibonacci / Classical (context only)

FIB_EVAL = make_context_evaluator("Fibonacci/Classical")


# ------------------------------------------------------------------
# family 18: Entry / Exit / Risk (gate style)


def _risk_gate_fn(c) -> Tuple[bool, dict, float]:
    s = c.settings
    decis = _dec(c)
    if decis is not None:
        best_rr = max((p.rr for p in decis.plans), default=0.0)
        ok = best_rr >= s.min_rr
        return ok, {"best_rr": best_rr, "min_rr": s.min_rr}, (0.4 if ok else -0.4)
    return False, {"min_rr": s.min_rr}, 0.0


def _entry_gate_fn(c) -> Tuple[bool, dict, float]:
    e = _entry(c)
    if e.get("data_gap"):
        return False, e, 0.0
    ok = e.get("entry") is not None and not e.get("chase")
    return ok, e, (0.3 if ok else -0.3)


def _filter_gate_fn(c) -> Tuple[bool, dict, float]:
    lq = _liq(c)
    entry = _entry(c)
    risky = bool(
        lq.get("low_liquidity")
        or lq.get("wide_spread")
        or entry.get("chase")
    )
    return (
        not risky,
        {
            "low_liquidity": lq.get("low_liquidity"),
            "wide_spread": lq.get("wide_spread"),
            "chase": entry.get("chase"),
        },
        (0.2 if not risky else -0.3),
    )


def _sl_target_gate_fn(c) -> Tuple[bool, dict, float]:
    r = _risk(c)
    ok = r.get("min_rr") is not None
    return ok, r, (0.1 if ok else 0.0)


def _entry_risk_gate(meta, c):
    name = meta.name.lower()
    if any(
        k in name
        for k in (
            "filter",
            "late entry",
            "chasing",
            "wide-spread",
            "low-liquidity",
            "gap-risk",
            "maximum-loss",
        )
    ):
        fn = _filter_gate_fn
    elif any(k in name for k in ("entry", "retest")):
        fn = _entry_gate_fn
    elif any(
        k in name
        for k in ("stop loss", "trailing", "break-even", "target", "exit")
    ):
        fn = _sl_target_gate_fn
    else:
        fn = _risk_gate_fn
    return make_gate_evaluator("Entry/Exit/Risk", fn)(meta, c)


# ------------------------------------------------------------------
# family 19: Signal Intelligence


def _signal_conflict_fn(c) -> Tuple[bool, dict, float]:
    cf = _conf(c)
    ok = not cf.get("conflict")
    return ok, cf, (0.2 if ok else -0.4)


def _signal_quality_fn(c) -> Tuple[bool, dict, float]:
    sq = _sq(c)
    ok = sq.get("kept_count", 0) >= 1
    return ok, sq, (0.2 if ok else -0.3)


def _signal_gate(meta, c):
    name = meta.name.lower()
    if "conflict" in name or "contradiction" in name or "block" in name:
        fn = _signal_conflict_fn
    else:
        fn = _signal_quality_fn
    return make_gate_evaluator("Signal Intelligence", fn)(meta, c)


# ------------------------------------------------------------------
# family 20: Data / Reliability


def _data_gate_fn(c) -> Tuple[bool, dict, float]:
    dq = _dq(c)
    ok = bool(dq is None or getattr(dq, "passed", True))
    ev = {
        "passed": ok,
        "flags": [f.value for f in (getattr(dq, "flags", []) or [])],
    }
    return ok, ev, (0.2 if ok else -0.6)


def _data_gate(meta, c):
    return make_gate_evaluator("Data/Reliability", _data_gate_fn)(meta, c)


# ------------------------------------------------------------------
# family 21: Backtest / Validation


def _bt_gate_fn(c) -> Tuple[bool, dict, float]:
    bt = _bt(c)
    ok = bool(bt.get("available"))
    return ok, bt, (0.15 if ok else 0.0)


def _bt_gate(meta, c):
    return make_gate_evaluator("Backtest/Validation", _bt_gate_fn)(meta, c)


# ------------------------------------------------------------------
# family 22: AI / Strategy Discovery


def _ai_gate_fn(c) -> Tuple[bool, dict, float]:
    ai = _ai(c)
    ok = bool(ai.get("enabled") and not ai.get("wait_override"))
    return (
        ok,
        {
            "enabled": ai.get("enabled"),
            "wait_override": ai.get("wait_override"),
            "agreement": ai.get("agreement"),
        },
        (0.2 if ok else 0.0),
    )


def _ai_gate(meta, c):
    return make_gate_evaluator("AI/Strategy Discovery", _ai_gate_fn)(meta, c)


# ------------------------------------------------------------------
# family 23: Final Decision Engine


def _final_gate_fn(c) -> Tuple[bool, dict, float]:
    d = _dec(c)
    if d is None:
        return False, {}, 0.0
    v = d.verdict
    ok = v in (Verdict.CALL_BUY, Verdict.PUT_BUY)
    return ok, {"verdict": v.value, "plans": d.plans_qualifying}, (0.3 if ok else 0.0)


def _final_gate(meta, c):
    return make_gate_evaluator("Final Decision Engine", _final_gate_fn)(meta, c)


FAMILY_EVALUATORS: Dict[str, object] = {
    "Quant/Statistical": QUANT_EVAL,
    "Cross-Index/Breadth": CROSS_EVAL,
    "Fibonacci/Classical": FIB_EVAL,
    "Entry/Exit/Risk": _entry_risk_gate,
    "Signal Intelligence": _signal_gate,
    "Data/Reliability": _data_gate,
    "Backtest/Validation": _bt_gate,
    "AI/Strategy Discovery": _ai_gate,
    "Final Decision Engine": _final_gate,
}
