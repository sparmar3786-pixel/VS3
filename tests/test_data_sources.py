from types import SimpleNamespace
from backend.groww_client import GrowwClient
from backend.signal_engine import build_signal

def test_groww_requires_token():
    assert GrowwClient('').status()['connected'] is False

def test_signal_has_risk_gate():
    rows=[SimpleNamespace(strike=x,ce_ltp=100,pe_ltp=100,ce_oi=1000 if x>=24800 else 300,pe_oi=1000 if x<=24600 else 300,ce_oi_change=100 if x==24700 else 0,pe_oi_change=100 if x==24700 else 0) for x in (24500,24600,24700,24800,24900)]
    s=SimpleNamespace(spot=24700,timestamp=None,strikes=rows,source='test')
    d=build_signal(s,source='test',min_rr=1.8)
    assert d['decision'] in {'CALL BUY','PUT BUY','WAIT','NO TRADE'}
    assert d['risk_reward'] is None or d['risk_reward'] >= 1.8
