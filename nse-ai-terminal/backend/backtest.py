"""Backtest the exact same 6-layer pipeline on historical candles.

    python backtest.py                       # synthetic data, all symbols
    python backtest.py data/RELIANCE.csv ... # CSVs: time,open,high,low,close,volume
                                             # (time = unix seconds; symbol = file name)
Reports return, max drawdown, Sharpe (per-bar, annualisation not assumed),
win rate and trade count. Uses candle high/low for stop-loss fills.
Past performance does not predict future results.
"""
import csv
import math
import random
import sys
from pathlib import Path

import numpy as np

import config
from engine import Engine


def load_csv(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            out.append({"time": int(float(r["time"])), "open": float(r["open"]),
                        "high": float(r["high"]), "low": float(r["low"]),
                        "close": float(r["close"]), "volume": float(r.get("volume", 0) or 0)})
    return out


def synthetic(n=3000, start=1000.0, seed=None):
    rnd = random.Random(seed)
    px, vol, drift, t0 = start, 0.0004, 0.0, 1_700_000_000
    out = []
    for i in range(n):
        if rnd.random() < 0.01: vol = rnd.choice([0.0002, 0.0004, 0.0009])
        if rnd.random() < 0.01: drift = rnd.choice([-0.00003, 0.0, 0.00003])
        o = px
        pts = []
        for _ in range(4):
            px *= math.exp(drift + rnd.gauss(0, vol))
            pts.append(px)
        out.append({"time": t0 + i * config.CANDLE_SECONDS, "open": o,
                    "high": max(pts + [o]), "low": min(pts + [o]),
                    "close": pts[-1], "volume": rnd.randint(100, 5000)})
    return out


def run(series: dict[str, list[dict]]):
    e = Engine()
    e.symbols = list(series)
    e.builders = {s: type(next(iter(e.builders.values())))(config.CANDLE_SECONDS, maxlen=600)
                  for s in series}
    events = sorted(((c["time"], s, c) for s, cs in series.items() for c in cs),
                    key=lambda x: (x[0], x[1]))
    curve = []
    for _, s, c in events:
        pos = e.broker.positions.get(s)
        if pos and pos.get("stop") is not None:
            if pos["qty"] > 0 and c["low"] <= pos["stop"]:
                e.check_stops(s, pos["stop"])
            elif pos["qty"] < 0 and c["high"] >= pos["stop"]:
                e.check_stops(s, pos["stop"])
        e.prices[s] = c["close"]
        b = e.builders[s]
        b.closed.append(dict(c))
        b.closed = b.closed[-b.maxlen:]
        e.run_pipeline(s)
        curve.append(e.broker.equity(e.prices))
    e.close_all()
    return e, np.array(curve)


def metrics(e, curve):
    eq = curve
    peak = np.maximum.accumulate(eq)
    r = np.diff(eq) / eq[:-1]
    b = e.broker
    return {"return_pct": round(float(eq[-1] / b.start_equity - 1) * 100, 2),
            "max_drawdown_pct": round(float(((eq - peak) / peak).min()) * 100, 2),
            "sharpe": round(float(r.mean() / r.std() * math.sqrt(len(r))) if r.std() > 0 else 0.0, 2),
            "orders": b.n_orders, "closed_trades": b.n_closed,
            "win_rate_pct": round(b.n_wins / b.n_closed * 100, 1) if b.n_closed else 0.0,
            "fees": round(b.fees), "realized": round(b.realized),
            "note": "Synthetic data. Not a prediction of real performance."}


def report(e, curve):
    eq = curve
    ret = eq[-1] / e.broker.start_equity - 1
    peak = np.maximum.accumulate(eq)
    mdd = ((eq - peak) / peak).min()
    r = np.diff(eq) / eq[:-1]
    sharpe = r.mean() / r.std() * math.sqrt(len(r)) if r.std() > 0 else 0.0
    b = e.broker
    print(f"Return        : {ret*100:+.2f}%")
    print(f"Max drawdown  : {mdd*100:.2f}%")
    print(f"Sharpe (total): {sharpe:.2f}   (per-bar returns, not annualised)")
    print(f"Orders        : {b.n_orders}  closed trades: {b.n_closed}  win rate: "
          f"{(b.n_wins/b.n_closed*100 if b.n_closed else 0):.1f}%")
    print(f"Fees paid     : {e.broker.fees:,.0f}   Realized P&L: {e.broker.realized:,.0f}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        series = {Path(p).stem.upper(): load_csv(p) for p in sys.argv[1:]}
    else:
        series = {s: synthetic(3000, start=1000.0 + 500 * i, seed=i)
                  for i, s in enumerate(config.SYMBOLS)}
    engine, curve = run(series)
    report(engine, curve)