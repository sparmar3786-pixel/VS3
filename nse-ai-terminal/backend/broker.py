import time

import config


class PaperBroker:
    """Paper execution only. No real orders are ever sent."""

    def __init__(self, capital: float):
        self.start_equity = capital
        self.cash = capital
        self.positions: dict[str, dict] = {}
        self.orders: list[dict] = []
        self.realized = 0.0
        self.fees = 0.0
        self.n_orders = 0
        self.n_closed = 0
        self.n_wins = 0

    def equity(self, prices: dict) -> float:
        return self.cash + sum(p["qty"] * prices.get(s, p["avg"])
                               for s, p in self.positions.items())

    def execute(self, symbol, side, qty, price, reason, stop=None):
        if qty <= 0:
            return None
        delta = qty if side == "BUY" else -qty
        fee = abs(delta) * price * config.FEE_RATE
        self.cash -= delta * price + fee
        self.fees += fee
        pos = self.positions.get(symbol)
        pnl = 0.0
        if pos is None:
            self.positions[symbol] = {"qty": delta, "avg": price, "stop": stop}
        else:
            old = pos["qty"]
            if (old > 0) == (delta > 0):
                new = old + delta
                pos["avg"] = (pos["avg"] * abs(old) + price * abs(delta)) / abs(new)
                pos["qty"] = new
            else:
                closed = min(abs(old), abs(delta))
                pnl = closed * (price - pos["avg"]) * (1 if old > 0 else -1)
                self.realized += pnl
                pos["qty"] = old + delta
                if pos["qty"] == 0:
                    del self.positions[symbol]
        self.n_orders += 1
        if pnl != 0.0:
            self.n_closed += 1
            self.n_wins += 1 if pnl - fee > 0 else 0
        order = {"time": int(time.time()), "symbol": symbol, "side": side,
                 "qty": qty, "price": price, "pnl": round(pnl - fee, 2),
                 "reason": reason}
        self.orders.append(order)
        self.orders = self.orders[-200:]
        return order