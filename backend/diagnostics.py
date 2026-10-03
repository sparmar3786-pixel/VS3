"""Read-only production diagnostics for the live NSE terminal.

This module never creates market values or trading signals. It only reports the
health/freshness of data already supplied by the existing engine.
"""
from __future__ import annotations

import time
from typing import Any


def _age(ts: Any, now: float | None = None) -> float | None:
    if ts is None:
        return None
    try:
        value = float(ts)
    except (TypeError, ValueError):
        return None
    return max(0.0, (time.time() if now is None else now) - value)


def freshness(ts: Any, now: float | None = None) -> dict[str, Any]:
    age = _age(ts, now)
    if age is None:
        return {"state": "no-data", "age_sec": None}
    if age <= 30:
        state = "fresh"
    elif age <= 120:
        state = "stale"
    else:
        state = "expired"
    return {"state": state, "age_sec": round(age, 1)}


def strategy_health(evidence: Any, registry_count: int) -> dict[str, Any]:
    rows = evidence if isinstance(evidence, list) else []
    counts = {"active": 0, "inactive": 0, "unavailable": 0, "error": 0}
    for item in rows:
        state = item.get("state") if isinstance(item, dict) else None
        if state in counts:
            counts[state] += 1
        else:
            counts["error"] += 1
    accounted = sum(counts.values())
    return {
        "registered": int(registry_count),
        "evaluated": len(rows),
        "active": counts["active"],
        "inactive": counts["inactive"],
        "unavailable": counts["unavailable"],
        "error": counts["error"],
        "not_evaluated": max(0, int(registry_count) - accounted),
    }


def build_diagnostics(*, state: dict[str, Any], engine: Any,
                      registry_count: int, angel_connected: bool,
                      nse_mcp_connected: bool, ai_providers: Any) -> dict[str, Any]:
    last = engine.last if isinstance(getattr(engine, "last", None), dict) else {}
    evidence = getattr(engine, "strategy_evidence", [])
    last_update = state.get("last_update")
    provider_rows = ai_providers if isinstance(ai_providers, list) else []
    configured = sum(
        1 for p in provider_rows
        if isinstance(p, dict) and p.get("configured") is True
    )
    return {
        "ok": True,
        "server": {"state": "healthy"},
        "market": {
            "open": bool(state.get("market_open", False)),
            "last_signal_ts": last.get("ts"),
        },
        "feeds": {
            "angel": {
                "connected": bool(angel_connected),
                "freshness": freshness(last_update),
                "last_update": last_update,
                "error": state.get("error"),
            },
            "nse": {
                "configured": True,
                "connected": state.get("nse_error") is None,
                "error": state.get("nse_error"),
            },
            "nse_mcp": {
                "connected": bool(nse_mcp_connected),
                "error": state.get("nse_mcp_error"),
            },
        },
        "strategies": strategy_health(evidence, registry_count),
        "signal": {
            "action": last.get("action", "WAIT"),
            "ts": last.get("ts"),
            "reasons": list(last.get("reasons", []))[:20],
        },
        "ai": {
            "total": len(provider_rows),
            "configured": configured,
            "ready": configured > 0,
            "providers": provider_rows,
        },
        "errors": [
            x for x in [state.get("error"), state.get("nse_error"),
                        state.get("nse_mcp_error")]
            if x
        ],
    }


def build_audit(engine: Any, registry_count: int) -> dict[str, Any]:
    last = engine.last if isinstance(getattr(engine, "last", None), dict) else {}
    evidence = getattr(engine, "strategy_evidence", [])
    active = [
        {
            "id": x.get("id"),
            "family": x.get("family"),
            "name": x.get("name"),
            "state": x.get("state"),
            "reason": x.get("reason"),
        }
        for x in evidence
        if isinstance(x, dict) and x.get("state") == "active"
    ]
    unavailable = sum(
        1 for x in evidence
        if isinstance(x, dict) and x.get("state") == "unavailable"
    )
    return {
        "action": last.get("action", "WAIT"),
        "ts": last.get("ts"),
        "symbol": last.get("symbol"),
        "strike": last.get("strike"),
        "type": last.get("type"),
        "entry": last.get("entry"),
        "sl": last.get("sl"),
        "target": last.get("target"),
        "score": last.get("score"),
        "reasons": list(last.get("reasons", []))[:20],
        "strategy_registry_count": int(registry_count),
        "active_evidence": active[:120],
        "active_count": len(active),
        "unavailable_count": unavailable,
        "rule": "Evidence only. Missing data never becomes a signal.",
    }
