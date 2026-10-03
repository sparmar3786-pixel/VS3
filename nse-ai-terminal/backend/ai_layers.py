"""The 6 AI layers.

L1 DataGuard      - tick validation, outlier / stale filtering, quality score
L2 RegimeDetector - TREND / RANGE / VOLATILE classification
L3 Ensemble       - regime-weighted vote of the active strategies
L4 OnlineML       - online logistic regression: P(next candle up)
L5 RiskGuard      - ATR sizing, exposure caps, daily-loss halt, kill switch
L6 Supervisor     - consensus gate + cooldown -> final trade decision
"""
import math
import time

import numpy as np

import config
from strategies import STRATEGIES, ema, rsi, atr


class DataGuard:
    def __init__(self):
        self.last = {}
        self.quality = {}

    def check(self, symbol, price, ts) -> bool:
        prev = self.last.get(symbol)
        ok = price > 0 and (prev is None or abs(price / prev[0] - 1) < 0.10)
        q = self.quality.get(symbol, 1.0)
        self.quality[symbol] = min(1.0, q + 0.01) if ok else max(0.0, q - 0.2)
        if ok:
            self.last[symbol] = (price, ts)
        return ok

    def score(self, symbol) -> float:
        q = self.quality.get(symbol, 1.0)
        last = self.last.get(symbol)
        if last and time.time() - last[1] > 15:
            q *= 0.5
        return round(q, 3)


class RegimeDetector:
    def detect(self, c):
        n = 20
        er = abs(c[-1] - c[-n]) / max(np.abs(np.diff(c[-n:])).sum(), 1e-9)
        r = np.diff(np.log(c))
        vr = r[-10:].std() / max(r[-60:].std(), 1e-9)
        if vr > 1.8:
            return "VOLATILE", float(er)
        return ("TREND" if er > 0.35 else "RANGE"), float(er)


REGIME_WEIGHTS = {
    "TREND": {"EMA Trend": .35, "Donchian Breakout": .30, "Momentum": .25,
              "RSI Reversion": .05, "VWAP Reversion": .05},
    "RANGE": {"RSI Reversion": .35, "VWAP Reversion": .35, "Momentum": .15,
              "EMA Trend": .10, "Donchian Breakout": .05},
    "VOLATILE": {"EMA Trend": .20, "Donchian Breakout": .20, "Momentum": .20,
                 "RSI Reversion": .20, "VWAP Reversion": .20},
}


class Ensemble:
    def __init__(self):
        self.enabled = {k: True for k in STRATEGIES}

    def vote(self, ohlcv, regime):
        votes = {k: round(fn(*ohlcv), 3) for k, fn in STRATEGIES.items()
                 if self.enabled[k]}
        w = REGIME_WEIGHTS[regime]
        tot = sum(w[k] for k in votes) or 1.0
        score = sum(votes[k] * w[k] for k in votes) / tot
        return float(score), votes


class OnlineML:
    N = 6

    def __init__(self, lr=0.05):
        self.w = {}
        self.lr = lr
        self.pending = {}

    @staticmethod
    def features(ohlcv, er):
        o, h, l, c, v = ohlcv
        a = max(atr(h, l, c), 1e-9)
        sd = np.diff(np.log(c[-31:])).std() or 1e-9
        return np.array([
            math.tanh((ema(c, 9)[-1] - ema(c, 21)[-1]) / a),
            (rsi(c) - 50) / 50,
            math.tanh(math.log(c[-1] / c[-6]) / (sd * 2.5)),
            math.tanh((c[-1] - c[-30:].mean()) / (c[-30:].std() or 1e-9) / 2),
            er,
            1.0,
        ])

    def predict(self, symbol, x):
        w = self.w.setdefault(symbol, np.zeros(self.N))
        z = float(w @ x)
        z = max(-60.0, min(60.0, z))
        return float(1 / (1 + math.exp(-z)))

    def learn(self, symbol, close):
        prev = self.pending.get(symbol)
        if prev:
            x, prev_close = prev
            y = 1.0 if close > prev_close else 0.0
            p = self.predict(symbol, x)
            self.w[symbol] = self.w.setdefault(symbol, np.zeros(self.N)) + self.lr * (y - p) * x

    def remember(self, symbol, x, close):
        self.pending[symbol] = (x, close)


class RiskGuard:
    def __init__(self):
        self.kill = False
        self.halted = False

    def evaluate_halt(self, equity, start_equity):
        if start_equity > 0 and (equity - start_equity) / start_equity < -config.MAX_DAILY_LOSS:
            self.halted = True

    def size(self, price, a, equity, regime, open_count):
        if self.kill or self.halted or open_count >= config.MAX_OPEN_POSITIONS:
            return 0, None
        stop_dist = 2 * a
        qty = int(equity * config.MAX_RISK_PER_TRADE / max(stop_dist, 1e-9))
        qty = min(qty, int(equity * config.MAX_POSITION_PCT / max(price, 1e-9)))
        if regime == "VOLATILE":
            qty //= 2
        return max(qty, 0), stop_dist


class Supervisor:
    def __init__(self):
        self.candles_since_trade = {}

    def tick_candle(self, symbol):
        self.candles_since_trade[symbol] = self.candles_since_trade.get(symbol, 99) + 1

    def decide(self, symbol, score, p_up, quality, holding):
        ml_edge = (p_up - 0.5) * 2
        combined = 0.7 * score + 0.3 * ml_edge
        confidence = round(min(1.0, abs(combined)) * quality, 3)
        cooldown_ok = self.candles_since_trade.get(symbol, 99) >= config.COOLDOWN_CANDLES
        action, why = "HOLD", "no consensus"
        if holding:
            side = 1 if holding > 0 else -1
            if combined * side < -0.10:
                action, why = "EXIT", "signal reversed"
        elif cooldown_ok and abs(combined) > 0.35 and quality > 0.6:
            agrees = abs(ml_edge) < 0.05 or (ml_edge > 0) == (score > 0)
            if agrees:
                action = "BUY" if combined > 0 else "SELL"
                why = f"ensemble {score:+.2f} / ML {p_up:.2f} agree"
            else:
                why = "ML disagrees with ensemble"
        return action, why, round(combined, 3), confidence

    def traded(self, symbol):
        self.candles_since_trade[symbol] = 0