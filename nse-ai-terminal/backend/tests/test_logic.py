import math
import os
import sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import options
import views
from engine import Engine

def test_put_call_parity():
    spot,k,t,iv,r=24700.0,24700.0,4/365,0.14,0.065
    c=options.bs(spot,k,t,iv,True,r)["price"];p=options.bs(spot,k,t,iv,False,r)["price"]
    assert abs((c-p)-(spot-k*math.exp(-r*t)))<1e-6

def test_chain_shape():
    ch=options.build_chain("NIFTY50",24690.0)
    assert len(ch["rows"])==17 and sum(r["atm"] for r in ch["rows"])==1
    assert ch["support"] in [r["strike"] for r in ch["rows"]]

def _engine_with_signal(combined,p_up,regime="TREND"):
    e=Engine();e.warmup()
    e.signals["NIFTY50"]={"regime":regime,"er":.5,"votes":{},"score":combined,"p_up":p_up,"quality":1.0,
                          "combined":combined,"confidence":.7,"action":"HOLD","why":"","qty":1}
    return e

def test_recommendations():
    assert views.layers(_engine_with_signal(.6,.8))["recommendation"]=="CALL BUY"
    assert views.layers(_engine_with_signal(-.6,.2))["recommendation"]=="PUT BUY"
    assert views.layers(_engine_with_signal(.6,.8,"VOLATILE"))["recommendation"]=="NO TRADE"
    assert views.layers(_engine_with_signal(.1,.5))["recommendation"]=="WAIT"

def test_plans_have_positive_risk():
    p=views.plans(_engine_with_signal(.6,.8))
    assert p["plans"] and all(x["sl"]<x["entry"]<x["t1"]<x["t2"] for x in p["plans"])