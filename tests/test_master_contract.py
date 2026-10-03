from backend.catalog import CORE, ADVANCED
from backend.core import DataQualityGate, RiskGate, DecisionEngine
from backend.oi import classify_oi

def test_strategy_catalog_is_exact():
    assert len(CORE) == 377
    assert len(ADVANCED) == 25
    assert CORE[0].id == "S001"
    assert CORE[-1].id == "S377"
    assert ADVANCED[0].id == "X378"
    assert ADVANCED[-1].id == "X402"

def test_oi_2x2():
    assert classify_oi(1.0, 2.0) == "LONG_BUILDUP"
    assert classify_oi(-1.0, 2.0) == "SHORT_BUILDUP"
    assert classify_oi(1.0, -2.0) == "SHORT_COVERING"
    assert classify_oi(-1.0, -2.0) == "LONG_UNWINDING"

def test_data_quality_blocks_missing_required_data():
    r=DataQualityGate(max_age_seconds=5).check(6,has_oi=True,has_volume=True)
    assert not r.ok and "STALE" in r.flags

def test_single_rr_gate():
    gate=RiskGate(1.8)
    assert gate.passes(1.8)
    assert not gate.passes(1.79)

def test_decision_never_pads_to_five():
    plans=[{"side":"CALL","rr":2.0,"strategy_ids":["S001"]}]
    d=DecisionEngine(5, RiskGate(1.8)).build(plans)
    assert len(d.plans)==1
    assert d.plans[0]["strategy_ids"]==["S001"]

def test_wait_override_wins():
    plans=[{"side":"CALL","rr":2.0,"strategy_ids":["S001"]}]
    d=DecisionEngine(5, RiskGate(1.8)).build(plans, type("A",(),{"wait_override":True})())
    assert d.verdict=="WAIT"
