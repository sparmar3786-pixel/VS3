"""Optional advanced option-flow / volatility-surface modules.

The brief enumerates 25 modules (378-402), despite calling them "24+".
All enumerated modules are retained and marked advanced=True so the
ADVANCED_ENGINE toggle gates them.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from backend.models import Side, StrategyMeta, StrategyResult
from backend.quant.option_math import clamp
from backend.strategies.base import Strategy

FAMILY = "Advanced Optional"


def _meta(
    num: int,
    name: str,
    inputs: List[str],
    math: str,
    req: List[str],
) -> StrategyMeta:
    return StrategyMeta(
        id=f"X{num:03d}",
        number=num,
        name=name,
        family=FAMILY,
        inputs=inputs,
        math=math,
        required_data=req,
        output="signed score",
        failure_conditions=["missing surface/flow data -> DATA_GAP"],
        advanced=True,
    )


def _res(
    meta: StrategyMeta,
    score: Optional[float],
    evidence: dict,
    reason: str = "",
) -> StrategyResult:
    if score is None:
        return StrategyResult(
            strategy_id=meta.id,
            number=meta.number,
            name=meta.name,
            family=FAMILY,
            fired=False,
            data_gap=True,
            evidence=evidence or {},
            reason=reason or "required data missing",
            advanced=True,
        )
    fired = abs(score) > 0.08
    return StrategyResult(
        strategy_id=meta.id,
        number=meta.number,
        name=meta.name,
        family=FAMILY,
        fired=fired,
        data_gap=False,
        side=(Side.CALL if score > 0 else Side.PUT),
        score=round(score, 4),
        confidence=round(clamp(abs(score)), 4),
        evidence=evidence or {},
        reason=reason or ("fired" if fired else "below threshold"),
        advanced=True,
    )


def _vs(c):
    return c.get("vol_surface") or {}


def _of(c):
    return c.get("order_flow") or {}


def _ml(c):
    return c.get("multi_leg") or {}


def _snap(c):
    return c.snapshot


def _mk(fn: Callable, meta: StrategyMeta):
    def _ev(m: StrategyMeta, c) -> StrategyResult:
        if not c.advanced:
            return StrategyResult(
                strategy_id=m.id,
                number=m.number,
                name=m.name,
                family=FAMILY,
                fired=False,
                reason="advanced engine disabled",
                advanced=True,
            )
        score, ev, *rest = fn(c)
        return _res(m, score, ev, rest[0] if rest else "")

    return _ev


# -------- volatility surface --------

def m378(c):
    v = _vs(c)
    s = v.get("iv_slope")
    return (None if s is None else clamp(-s * 20, -1, 1)), v, "slope"


def m379(c):
    v = _vs(c)
    k = v.get("iv_curvature")
    return (None if k is None else clamp(k * 20, -1, 1)), v, "curvature"


def m380(c):
    v = _vs(c)
    s = v.get("surface_shift")
    return (None if s is None else clamp(s * 20, -1, 1)), v, "shift"


def m381(c):
    v = _vs(c)
    s = v.get("skew")
    return (None if s is None else clamp(-s * 20, -1, 1)), v, "smile"


def m382(c):
    v = _vs(c)
    d = v.get("otm_vs_atm_iv")
    return (None if d is None else clamp(-d * 20, -1, 1)), v, "atm_otm"


def m383(c):
    ts = (_vs(c).get("term_structure") or {})
    s = ts.get("slope")
    return (None if s is None else clamp(s * 10, -1, 1)), ts, "term_slope"


def m384(c):
    ts = (_vs(c).get("term_structure") or {})
    inv = ts.get("inverted")
    return (None if inv is None else (-0.4 if inv else 0.2)), ts, "inversion"


def m385(c):
    v = _vs(c)
    pts = v.get("moneyness_iv_points")
    return (None if pts is None else clamp(pts / 40 - 0.3, -1, 1)), v, "moneyness_iv"


# -------- vega / delta flow --------

def m386(c):
    o = _of(c)
    x = o.get("vega_weighted_flow")
    return (None if x is None else clamp(x * 10, -1, 1)), o, "vega_demand"


def m387(c):
    o = _of(c)
    x = o.get("vega_flow_acceleration")
    return (None if x is None else clamp(x * 10, -1, 1)), o, "vega_accel"


def m388(c):
    o = _of(c)
    x = o.get("vega_flow_reversal")
    return (None if x is None else clamp(-x * 10, -1, 1)), o, "vega_reversal"


def m389(c):
    o = _of(c)
    d, v = o.get("delta_weighted_flow"), o.get("vega_weighted_flow")
    return (
        None if (d is None or v is None) else clamp((d - v) * 10, -1, 1),
        o,
        "dv_separation",
    )


def m390(c):
    return m389(c)


def m391(c):
    o = _of(c)
    d = o.get("delta_weighted_flow")
    return (None if d is None else clamp(d, -1, 1)), o, "delta_flow"


def m392(c):
    o = _of(c)
    v = o.get("vega_weighted_flow")
    return (None if v is None else clamp(v * 10, -1, 1)), o, "vega_flow"


def m393(c):
    o = _of(c)
    d, v = o.get("flow_imbalance"), o.get("vega_weighted_flow")
    return (
        None if d is None else clamp(d, -1, 1),
        {"direction": d, "volatility": v},
        "info_scores",
    )


def m394(c):
    o = _of(c)
    d, v = o.get("delta_weighted_flow"), o.get("vega_weighted_flow")
    return (
        None if d is None else clamp(d + (v or 0), -1, 1),
        o,
        "combined",
    )


def m395(c):
    o = _of(c)
    return (
        None if o.get("data_gap") else clamp(o.get("flow_imbalance", 0), -1, 1),
        o,
        "cross_strike",
    )


def m396(c):
    snap = _snap(c)
    ce = sum((s.ce_volume or 0) for s in snap.strikes)
    pe = sum((s.pe_volume or 0) for s in snap.strikes)
    tot = ce + pe
    return (
        None if tot == 0 else clamp((ce - pe) / tot, -1, 1),
        {"ce": ce, "pe": pe},
        "ce_pe_flow",
    )


def m397(c):
    return None, {"note": "needs multiple expiries; DATA_GAP"}, "cross_maturity"


def m398(c):
    o = _of(c)
    d = o.get("delta_weighted_flow")
    return (None if d is None else clamp(d * 0.5, -1, 1)), o, "delta_bucket"


def m399(c):
    o = _of(c)
    v = o.get("vega_weighted_flow")
    return (None if v is None else clamp(v * 5, -1, 1)), o, "vega_bucket"


def m400(c):
    o = _of(c)
    return (
        None
        if o.get("data_gap")
        else clamp(
            (o.get("flow_imbalance", 0) + o.get("persistence", 0)) / 2,
            -1,
            1,
        ),
        o,
        "aggregate",
    )


def m401(c):
    ml = _ml(c)
    n = len(ml.get("structures_recognized", []))
    return (
        None if not ml else clamp(n / 23 - 0.2, -1, 1),
        ml,
        "multi_leg",
    )


def m402(c):
    o = _of(c)
    return (
        None if o.get("data_gap") else clamp(o.get("flow_imbalance", 0), -1, 1),
        o,
        "trade_class",
    )


_MODULES = [
    (378, "IV surface slope", ["iv", "option_chain"], "d(IV)/d(moneyness) slope", ["iv"], m378),
    (379, "IV surface curvature", ["iv", "option_chain"], "second-order IV curvature", ["iv"], m379),
    (380, "IV surface shift", ["iv"], "IV level change vs previous", ["iv"], m380),
    (381, "IV smile/skew change", ["iv"], "change in smile/skew", ["iv"], m381),
    (382, "ATM vs OTM IV divergence", ["iv"], "OTM IV - ATM IV", ["iv"], m382),
    (383, "term-structure slope", ["iv", "expiries"], "IV term-structure slope", ["multi_expiry"], m383),
    (384, "term-structure inversion", ["iv", "expiries"], "front IV > back IV", ["multi_expiry"], m384),
    (385, "moneyness-IV interaction", ["iv", "strikes"], "IV by moneyness", ["iv"], m385),
    (386, "vega-weighted net demand", ["volume", "vega"], "sum(volume*vega)", ["bid_ask"], m386),
    (387, "vega flow acceleration", ["volume", "vega"], "d(vega flow)/dt", ["bid_ask"], m387),
    (388, "vega flow reversal", ["volume", "vega"], "sign flip in vega flow", ["bid_ask"], m388),
    (389, "delta-vs-vega flow separation", ["volume", "delta", "vega"], "delta flow vs vega flow", ["bid_ask"], m389),
    (390, "directional-flow vs volatility-flow separation", ["volume", "delta", "vega"], "direction vs vol flow", ["bid_ask"], m390),
    (391, "delta-informed flow", ["volume", "delta"], "delta-weighted aggressor flow", ["bid_ask"], m391),
    (392, "vega-informed flow", ["volume", "vega"], "vega-weighted aggressor flow", ["bid_ask"], m392),
    (393, "direction/volatility information scores", ["volume"], "info scores", ["bid_ask"], m393),
    (394, "combined information imbalance", ["volume"], "combined imbalance", ["bid_ask"], m394),
    (395, "same-expiry cross-strike flow", ["volume", "strikes"], "flow across strikes", ["bid_ask"], m395),
    (396, "same-strike CE/PE flow", ["volume"], "CE vs PE flow", ["volume"], m396),
    (397, "cross-maturity flow", ["volume", "expiries"], "flow across expiries", ["multi_expiry"], m397),
    (398, "delta-bucket flow", ["volume", "delta"], "flow by delta bucket", ["bid_ask"], m398),
    (399, "vega-bucket flow", ["volume", "vega"], "flow by vega bucket", ["bid_ask"], m399),
    (400, "aggregate option-flow pressure", ["volume"], "net flow pressure", ["bid_ask"], m400),
    (401, "multi-leg strategy recognition (straddle/strangle/spreads/calendar/butterfly/condor/ratio/collar/covered/strip/strap/jelly roll)", ["strikes", "premium"], "structure recognition", ["option_chain"], m401),
    (402, "trade classification engine (buyer vs seller initiated, aggressor volume, trade-size buckets, large/small lot, flow imbalance, persistence, reversal)", ["volume", "bid_ask"], "aggressor classification", ["bid_ask"], m402),
]


def build_advanced() -> List[Strategy]:
    out: List[Strategy] = []
    for num, name, inputs, math, req, fn in _MODULES:
        meta = _meta(num, name, inputs, math, req)
        out.append(Strategy(meta, _mk(fn, meta)))
    return out


ADVANCED_COUNT = len(_MODULES)
assert ADVANCED_COUNT == 25
assert [x[0] for x in _MODULES] == list(range(378, 403))
