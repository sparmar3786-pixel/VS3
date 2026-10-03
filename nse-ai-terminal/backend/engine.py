import asyncio
import json
import time

import config
from ai_layers import DataGuard, RegimeDetector, Ensemble, OnlineML, RiskGuard, Supervisor
from broker import PaperBroker
from candles import CandleBuilder
from feed import make_feed, SimFeed
from strategies import atr

MIN_BARS = 70


class Engine:
    def __init__(self):
        self.symbols = config.SYMBOLS
        self.feed = make_feed(self.symbols)
        self.builders = {s: CandleBuilder(config.CANDLE_SECONDS) for s in self.symbols}
        self.prices: dict[str, float] = {}
        self.ref_px: dict[str, float] = {}
        self.last_tick_ts = 0.0
        self.broker = PaperBroker(config.CAPITAL)
        self.l1, self.l2 = DataGuard(), RegimeDetector()
        self.l3, self.l4 = Ensemble(), OnlineML()
        self.l5, self.l6 = RiskGuard(), Supervisor()
        self.signals: dict[str, dict] = {}
        self.clients: set = set()
        self.layer_stats = {i: {"processed": 0, "last_ms": 0.0} for i in range(1, 7)}

    async def broadcast(self, msg: dict):
        data = json.dumps(msg)
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def state(self):
        eq = self.broker.equity(self.prices)
        return {"type":"state","portfolio":{"equity":round(eq,2),"pnl":round(eq-self.broker.start_equity,2),
                "realized":round(self.broker.realized,2),"fees":round(self.broker.fees,2),
                "halted":self.l5.halted,"kill":self.l5.kill},
                "positions":[{"symbol":s,**p,"last":self.prices.get(s,p["avg"])} for s,p in self.broker.positions.items()],
                "orders":self.broker.orders[-30:][::-1],"signals":self.signals,
                "strategies":self.l3.enabled,"layers":self.layer_stats,"prices":self.prices}

    def snapshot(self):
        return {"type":"snapshot","symbols":self.symbols,
                "candles":{s:b.history() for s,b in self.builders.items()},
                **{k:v for k,v in self.state().items() if k!="type"}}

    def _timed(self, layer, t0):
        st=self.layer_stats[layer]; st["processed"]+=1
        st["last_ms"]=round((time.perf_counter()-t0)*1000,3)

    def run_pipeline(self, symbol):
        b=self.builders[symbol]
        if len(b.closed)<MIN_BARS:return
        ohlcv=b.arrays(); o,h,l,c,v=ohlcv; price=c[-1]
        t=time.perf_counter(); quality=self.l1.score(symbol); self._timed(1,t)
        t=time.perf_counter(); regime,er=self.l2.detect(c); self._timed(2,t)
        t=time.perf_counter(); score,votes=self.l3.vote(ohlcv,regime); self._timed(3,t)
        t=time.perf_counter(); self.l4.learn(symbol,price); x=self.l4.features(ohlcv,er); p_up=self.l4.predict(symbol,x)
        self.l4.remember(symbol,x,price); self._timed(4,t)
        t=time.perf_counter(); eq=self.broker.equity(self.prices); self.l5.evaluate_halt(eq,self.broker.start_equity)
        a=atr(h,l,c); qty,stop_dist=self.l5.size(price,a,eq,regime,len(self.broker.positions)); self._timed(5,t)
        t=time.perf_counter(); self.l6.tick_candle(symbol); pos=self.broker.positions.get(symbol); holding=pos["qty"] if pos else 0
        action,why,combined,conf=self.l6.decide(symbol,score,p_up,quality,holding)
        if action in ("BUY","SELL") and qty>0:
            stop=price-stop_dist if action=="BUY" else price+stop_dist
            self.broker.execute(symbol,action,qty,price,why,stop); self.l6.traded(symbol)
        elif action=="EXIT" and pos:
            side="SELL" if pos["qty"]>0 else "BUY"; self.broker.execute(symbol,side,abs(pos["qty"]),price,why); self.l6.traded(symbol)
        elif action in ("BUY","SELL"):
            action,why="BLOCKED","risk guard (limits/halt/kill)"
        self._timed(6,t)
        self.signals[symbol]={"regime":regime,"er":round(er,3),"votes":votes,"score":round(score,3),
                "p_up":round(p_up,3),"quality":quality,"combined":combined,"confidence":conf,
                "action":action,"why":why,"qty":qty}

    def check_stops(self,symbol,price):
        pos=self.broker.positions.get(symbol)
        if not pos or pos.get("stop") is None:return
        hit=(pos["qty"]>0 and price<=pos["stop"]) or (pos["qty"]<0 and price>=pos["stop"])
        if self.l5.kill or hit:
            side="SELL" if pos["qty"]>0 else "BUY"
            self.broker.execute(symbol,side,abs(pos["qty"]),price,"KILL SWITCH" if self.l5.kill else "stop-loss")

    def close_all(self):
        for s,p in list(self.broker.positions.items()):
            side="SELL" if p["qty"]>0 else "BUY"
            self.broker.execute(s,side,abs(p["qty"]),self.prices.get(s,p["avg"]),"KILL SWITCH")

    def warmup(self):
        if isinstance(self.feed,SimFeed):
            for s in self.symbols:
                for sym,p,v,ts in self.feed.history_ticks(s,150,config.CANDLE_SECONDS):
                    self.builders[sym].update(p,v,ts); self.prices[sym]=p; self.ref_px.setdefault(sym,p)

    async def run(self):
        self.warmup(); last_state=0.0
        async for sym,price,vol,ts in self.feed.stream():
            if sym not in self.builders or not self.l1.check(sym,price,ts):continue
            self.prices[sym]=price; self.ref_px.setdefault(sym,price); self.last_tick_ts=time.time()
            closed=self.builders[sym].update(price,vol,ts); self.check_stops(sym,price)
            if closed:self.run_pipeline(sym)
            cur=self.builders[sym].cur
            await self.broadcast({"type":"tick","symbol":sym,"candle":cur})
            if time.time()-last_state>0.5:last_state=time.time(); await self.broadcast(self.state())
            await asyncio.sleep(0)