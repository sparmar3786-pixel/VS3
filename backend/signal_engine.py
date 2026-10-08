"""Deterministic market-structure signal engine.

The engine is deliberately independent from broker SDKs and UI code. Providers
must first normalize data into backend.models.Snapshot. AI is an explanation and
validation layer; it is never allowed to manufacture a trade when data gates fail.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _age(snapshot: Any) -> float:
    ts = getattr(snapshot, "timestamp", None)
    if ts is None:
        return 10**9
    if getattr(ts, "tzinfo", None) is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())


def _oi_walls(snapshot: Any) -> tuple[float | None, float | None]:
    spot = _num(getattr(snapshot, "spot", None))
    rows = list(getattr(snapshot, "strikes", []) or [])
    if spot is None or not rows:
        return None, None
    below = [r for r in rows if _num(getattr(r, "strike", None)) is not None and _num(r.strike) <= spot]
    above = [r for r in rows if _num(getattr(r, "strike", None)) is not None and _num(r.strike) >= spot]
    support = max(below, key=lambda r: _num(getattr(r, "pe_oi", 0)) or 0) if below else None
    resistance = max(above, key=lambda r: _num(getattr(r, "ce_oi", 0)) or 0) if above else None
    return (_num(getattr(support, "strike", None)), _num(getattr(resistance, "strike", None)))


def _pcr(snapshot: Any) -> float | None:
    ce = sum(_num(getattr(r, "ce_oi", 0)) or 0 for r in getattr(snapshot, "strikes", []) or [])
    pe = sum(_num(getattr(r, "pe_oi", 0)) or 0 for r in getattr(snapshot, "strikes", []) or [])
    return round(pe / ce, 3) if ce > 0 else None


def build_signal(snapshot: Any, source: str = "unknown", max_age_sec: float = 240.0,
                 min_rr: float = 1.8) -> dict:
    if snapshot is None:
        return {"verdict": "NO TRADE", "reason": "No verified market snapshot is available.",
                "data_quality": {"passed": False, "flags": ["MISSING_DATA"]}}

    age = _age(snapshot)
    rows = list(getattr(snapshot, "strikes", []) or [])
    spot = _num(getattr(snapshot, "spot", None))
    support, resistance = _oi_walls(snapshot)
    pcr = _pcr(snapshot)
    missing_oi = any(getattr(r, "ce_oi", None) is None or getattr(r, "pe_oi", None) is None for r in rows)
    missing_volume = any(getattr(r, "ce_volume", None) is None or getattr(r, "pe_volume", None) is None for r in rows)
    flags = []
    if age > max_age_sec:
        flags.append("STALE")
    if not rows or spot is None:
        flags.append("INCOMPLETE_CHAIN")
    if missing_oi:
        flags.append("MISSING_OI")
    if missing_volume:
        flags.append("MISSING_VOLUME")
    if flags:
        return {
            "verdict": "WAIT",
            "reason": "Data-quality gate blocked the signal; AI must not override it.",
            "data_quality": {"passed": False, "flags": flags, "age_sec": round(age, 2), "source": source},
            "support": support, "resistance": resistance, "pcr": pcr,
        }

    atm = _num(getattr(snapshot, "atm_strike", None)) or spot
    near = min(rows, key=lambda r: abs((_num(getattr(r, "strike", 0)) or 0) - atm))
    ce_oi_chg = _num(getattr(near, "ce_oi_change", 0)) or 0
    pe_oi_chg = _num(getattr(near, "pe_oi_change", 0)) or 0
    ce_ltp = _num(getattr(near, "ce_ltp", None))
    pe_ltp = _num(getattr(near, "pe_ltp", None))

    # Directional evidence: PCR + ATM OI migration + option premium availability.
    bull = (pcr is not None and pcr > 1.05) + (pe_oi_chg > ce_oi_chg)
    bear = (pcr is not None and pcr < 0.95) + (ce_oi_chg > pe_oi_chg)
    room_up = resistance is None or spot < resistance
    room_down = support is None or spot > support

    side = None
    if bull >= 2 and room_up and ce_ltp and ce_ltp > 0:
        side = "CALL BUY"
    elif bear >= 2 and room_down and pe_ltp and pe_ltp > 0:
        side = "PUT BUY"

    reasons = [
        f"PCR={pcr if pcr is not None else 'NA'}",
        f"ATM CE OI change={ce_oi_chg:g}, PE OI change={pe_oi_chg:g}",
        f"OI support={support if support is not None else 'NA'}",
        f"OI resistance={resistance if resistance is not None else 'NA'}",
    ]
    if side == "CALL BUY":
        reasons += ["Bullish evidence dominates.", "Nearest PE-OI wall acts as support.",
                    "CE trade is allowed only while price has room before the strongest CE-OI resistance."]
    elif side == "PUT BUY":
        reasons += ["Bearish evidence dominates.", "Nearest CE-OI wall acts as resistance.",
                    "PE trade is allowed only while price has room before the strongest PE-OI support."]
    else:
        return {
            "verdict": "WAIT",
            "reason": "Conflicting or insufficient directional evidence.",
            "data_quality": {"passed": True, "age_sec": round(age, 2), "source": source},
            "spot": spot, "atm": atm, "support": support, "resistance": resistance,
            "pcr": pcr, "reasons": reasons,
        }

    premium = ce_ltp if side == "CALL BUY" else pe_ltp
    # Premium risk is a fallback only. The structural wall is reported separately;
    # a production order engine would additionally use ATR/slippage before execution.
    stop = premium * 0.70
    target = premium + (premium - stop) * min_rr
    rr = (target - premium) / (premium - stop) if premium > stop else 0.0
    if rr < min_rr:
        return {"verdict": "WAIT", "reason": "Risk/reward gate failed.", "rr": round(rr, 2),
                "min_rr": min_rr, "data_quality": {"passed": True, "age_sec": round(age, 2)}}

    return {
        "verdict": side,
        "reason": "Deterministic Run60 + Run93 evidence qualified the directional side.",
        "index": getattr(snapshot, "index", ""),
        "spot": spot, "atm": atm, "support": support, "resistance": resistance, "pcr": pcr,
        "option_ltp": premium, "entry": premium, "stop_loss": round(stop, 2),
        "target": round(target, 2), "rr": round(rr, 2), "min_rr": min_rr,
        "risk_note": "R:R is a gate, not a guarantee. Structure/ATR/slippage should tighten the final paper plan.",
        "reasons": reasons,
        "data_quality": {"passed": True, "age_sec": round(age, 2), "source": source},
    }
