"""Pure functions that turn engine state into JSON."""
import asyncio
import time
import config
from options import build_chain
from strategies import STRATEGIES
from ai_layers import REGIME_WEIGHTS

INDEX_SYMBOLS=["NIFTY50","BANKNIFTY","FINNIFTY","MIDCPNIFTY","SENSEX"]
DESCRIPTIONS={"EMA Trend":"EMA9 vs EMA21 gap, normalised by ATR. Follows trends.",
"RSI Reversion":"Fades RSI extremes (<35 / >65). Works in ranges.",
"Donchian Breakout":"Breakout of the 20-candle high/low channel.",
"VWAP Reversion":"Mean reversion to 30-candle VWAP, z-scored.",
"Momentum":"10-candle return scaled by recent volatility."}

def health(e):
    age=time.time()-e.last_tick_ts if e.last_tick_ts else None
    return {"status":"ok","mode":"PAPER","feed":config.FEED_MODE,"symbols":e.symbols,
            "last_tick_age_s":None if age is None else round(age,1),"stale":age is None or age>15,
            "kill":e.l5.kill,"halted":e.l5.halted}

def overview(e):
    idx=[]
    for s in INDEX_SYMBOLS:
        if s in e.prices:
            ref=e.ref_px.get(s,e.prices[s]);idx.append({"symbol":s,"last":round(e.prices[s],2),
            "chg_pct":round((e.prices[s]/ref-1)*100,2)})
    stocks=[]
    for s in e.symbols:
        if s not in INDEX_SYMBOLS and s in e.prices:
            ref=e.ref_px.get(s,e.prices[s]);stocks.append({"symbol":s,"last":round(e.prices[s],2),
            "chg_pct":round((e.prices[s]/ref-1)*100,2)})
    return {"indices":idx,"stocks":stocks,"layers":layers(e),"portfolio":e.state()["portfolio"]}

def layers(e,symbol="NIFTY50"):
    s=e.signals.get(symbol)
    if not s:return {"ready":False,"symbol":symbol,"recommendation":"WAIT","confidence":0,"layers":[],"note":"Collecting candles…"}
    direction=1 if s["combined"]>0 else -1 if s["combined"]<0 else 0
    checks=[("L1 Data Guard",s["quality"]>.6,f"quality {s['quality']}"),
            ("L2 Regime Detector",s["regime"]!="VOLATILE",s["regime"]),
            ("L3 Strategy Ensemble",abs(s["score"])>.2,f"score {s['score']:+.2f}"),
            ("L4 Online ML",direction!=0 and (s["p_up"]-.5)*direction>.02,f"P(up) {s['p_up']}"),
            ("L5 Risk Guard",not(e.l5.kill or e.l5.halted),"halted" if(e.l5.kill or e.l5.halted) else "within limits"),
            ("L6 Supervisor",abs(s["combined"])>.35,f"combined {s['combined']:+.2f}")]
    out=[{"name":n,"agrees":bool(ok),"detail":d} for n,ok,d in checks]
    if all(c["agrees"] for c in out):rec="CALL BUY" if direction>0 else "PUT BUY"
    elif not checks[0][1] or not checks[1][1] or not checks[4][1]:rec="NO TRADE"
    else:rec="WAIT"
    return {"ready":True,"symbol":symbol,"recommendation":rec,"confidence":s["confidence"],
            "layers":out,"agree_count":sum(c["agrees"] for c in out),"regime":s["regime"],
            "er":s["er"],"votes":s["votes"],"p_up":s["p_up"],"combined":s["combined"]}

def chain(e,symbol="NIFTY50"):
    spot=e.prices.get(symbol)
    if spot is None:return {"error":f"no price for {symbol}"}
    return build_chain(symbol,spot)

def plans(e,symbol="NIFTY50"):
    L=layers(e,symbol);rec=L["recommendation"]
    if rec not in ("CALL BUY","PUT BUY"):
        return {"recommendation":rec,"plans":[],"note":"No trade plan: layers do not all agree." if rec=="WAIT" else "Trading blocked (data/regime/risk)."}
    ch=chain(e,symbol);side="ce" if rec=="CALL BUY" else "pe";rows=ch["rows"];i0=next(i for i,r in enumerate(rows) if r["atm"])
    pick=[rows[i0+k] for k in ((0,1,2) if side=="ce" else (0,-1,-2))];out=[]
    for r in pick:
        entry=r[side]["ltp"]
        if entry<=0:continue
        sl,t1,t2=round(entry*.8,2),round(entry*1.2,2),round(entry*1.4,2)
        out.append({"side":"CALL" if side=="ce" else "PUT","strike":r["strike"],"entry":entry,"sl":sl,"t1":t1,"t2":t2,
                    "rr":round((t2-entry)/(entry-sl),1),"lot":ch["lot"],"delta":r[side]["delta"]})
    return {"recommendation":rec,"symbol":symbol,"plans":out,"note":"Demo rule: SL -20%, T1 +20%, T2 +40%. Educational only, not advice."}

def strategies(e):
    regime=(e.signals.get("NIFTY50") or {}).get("regime","RANGE");w=REGIME_WEIGHTS[regime]
    return {"regime":regime,"items":[{"name":k,"enabled":e.l3.enabled[k],"weight":w[k],"desc":DESCRIPTIONS.get(k,"")} for k in STRATEGIES]}

def risk(e):
    p=e.state()["portfolio"]
    return {"limits":{"max_risk_per_trade_pct":config.MAX_RISK_PER_TRADE*100,"max_daily_loss_pct":config.MAX_DAILY_LOSS*100,
        "max_position_pct":config.MAX_POSITION_PCT*100,"max_open_positions":config.MAX_OPEN_POSITIONS,"sl_type":"ATR x2"},
        "state":{"halted":p["halted"],"kill":p["kill"],"equity":p["equity"],"pnl":p["pnl"],"open_positions":len(e.broker.positions)}}

def notifications(e):
    items=[{"time":o["time"],"level":"info","title":f"{o['side']} {o['symbol']}","body":f"{o['qty']} @ {o['price']} · {o['reason']}"} for o in e.broker.orders[-30:][::-1]]
    if e.l5.halted:items.insert(0,{"time":int(time.time()),"level":"high","title":"Trading halted","body":"Daily loss limit reached."})
    if e.l5.kill:items.insert(0,{"time":int(time.time()),"level":"high","title":"Kill switch ON","body":"All positions closed, new trades blocked."})
    return {"items":items}

def candles(e,symbol):
    b=e.builders.get(symbol.upper());return b.history() if b else []

async def backtest(symbol="NIFTY50",bars=500):
    import backtest as bt
    bars=max(150,min(int(bars),1200))
    def job():
        eng,curve=bt.run({symbol:bt.synthetic(bars,start=1000.0,seed=int(time.time())%1000)})
        return bt.metrics(eng,curve)
    return await asyncio.to_thread(job)