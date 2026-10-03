import numpy as np


class CandleBuilder:
    """Aggregates ticks into fixed-interval OHLCV candles."""

    def __init__(self, seconds: int, maxlen: int = 600):
        self.sec = seconds
        self.maxlen = maxlen
        self.closed: list[dict] = []
        self.cur: dict | None = None

    def update(self, price: float, vol: float, ts: float) -> bool:
        bucket = int(ts // self.sec * self.sec)
        just_closed = False
        if self.cur is None or bucket > self.cur["time"]:
            if self.cur is not None:
                self.closed.append(self.cur)
                if len(self.closed) > self.maxlen:
                    self.closed = self.closed[-self.maxlen:]
                just_closed = True
            self.cur = {"time": bucket, "open": price, "high": price,
                        "low": price, "close": price, "volume": vol}
        else:
            c = self.cur
            c["high"] = max(c["high"], price)
            c["low"] = min(c["low"], price)
            c["close"] = price
            c["volume"] += vol
        return just_closed

    def arrays(self):
        k = self.closed
        o = np.array([x["open"] for x in k], dtype=float)
        h = np.array([x["high"] for x in k], dtype=float)
        l = np.array([x["low"] for x in k], dtype=float)
        c = np.array([x["close"] for x in k], dtype=float)
        v = np.array([x["volume"] for x in k], dtype=float)
        return o, h, l, c, v

    def history(self) -> list[dict]:
        out = list(self.closed)
        if self.cur:
            out.append(dict(self.cur))
        return out