"""DEMO data source — a clearly-labelled synthetic feed.

Purpose: let the whole terminal run end-to-end with **no credentials**. Every
tick/snapshot is tagged `source="demo"` and the UI shows a DEMO banner. This is
NOT real market data and must never be mistaken for it.

Prices are generated with a seeded random walk plus Black-Scholes greeks so the
deterministic engines have something coherent to chew on.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

from backend.brokers.base import Capabilities, DataSource
from backend.models import Snapshot, StrikeSnapshot, Tick
from backend.quant.option_math import bs_greeks, bs_price

_BASE_SPOT = {
    "NIFTY": 24000.0, "BANKNIFTY": 52000.0, "FINNIFTY": 23000.0,
    "MIDCPNIFTY": 12000.0, "SENSEX": 79000.0, "BANKEX": 56000.0,
}
_STEP = {
    "NIFTY": 50.0, "BANKNIFTY": 100.0, "FINNIFTY": 50.0,
    "MIDCPNIFTY": 25.0, "SENSEX": 100.0, "BANKEX": 100.0,
}


class DemoSource(DataSource):
    name = "demo"
    capabilities = Capabilities(
        streaming=True, greeks=True, option_chain=True, historical=True,
        oi=True, volume=True, bid_ask=True,
    )

    def __init__(self, rps: float = 50.0, seed: Optional[int] = None) -> None:
        super().__init__(rps=rps)
        self._rng = random.Random(seed)
        self._state: Dict[str, float] = {}
        self._oi_memory: Dict[tuple, int] = {}

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

    def _spot(self, index: str) -> float:
        index = index.upper()
        base = _BASE_SPOT.get(index, 20000.0)
        if index not in self._state:
            self._state[index] = base
        self._state[index] *= 1.0 + self._rng.gauss(0.0, 0.0006)
        return round(self._state[index], 2)

    async def get_ltp(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[float]:
        return self._spot(symbol) if symbol.upper() in _BASE_SPOT else None

    async def get_quote(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[Tick]:
        spot = self._spot(symbol)
        return Tick(symbol=symbol, exchange=exchange, token=token, ltp=spot,
                    open=spot, high=spot * 1.004, low=spot * 0.996, close=spot,
                    volume=self._rng.randint(1000, 9000), oi=self._rng.randint(10_000, 90_000),
                    bid=spot - 0.5, ask=spot + 0.5, source="demo")

    async def get_option_chain(self, index: str, expiry: Optional[str] = None) -> Snapshot:
        idx = index.upper()
        spot = self._spot(idx)
        step = _STEP.get(idx, 50.0)
        atm = round(spot / step) * step
        r, days = 0.065, 3.0
        T = max(days, 1.0) / 365.0

        strikes: List[StrikeSnapshot] = []
        for i in range(-10, 11):
            k = atm + i * step
            moneyness = (spot - k) / spot
            base_iv = 0.14 + 0.6 * abs(moneyness) + (0.02 if k < spot else 0.0)
            iv = max(0.05, base_iv + self._rng.gauss(0.0, 0.004))
            ce_px = bs_price(spot, k, T, r, iv, "CE")
            pe_px = bs_price(spot, k, T, r, iv, "PE")
            ce_g = bs_greeks(spot, k, T, r, iv, "CE")
            pe_g = bs_greeks(spot, k, T, r, iv, "PE")

            ce_oi = self._oi_bucket(idx, k, "CE", moneyness)
            pe_oi = self._oi_bucket(idx, k, "PE", -moneyness)
            strikes.append(StrikeSnapshot(
                strike=k, is_atm=(k == atm),
                ce_ltp=round(ce_px, 2), pe_ltp=round(pe_px, 2),
                ce_oi=ce_oi, pe_oi=pe_oi,
                ce_oi_change=self._rng.randint(-8000, 9000),
                pe_oi_change=self._rng.randint(-8000, 9000),
                ce_volume=self._rng.randint(500, 60000),
                pe_volume=self._rng.randint(500, 60000),
                ce_iv=round(iv, 4), pe_iv=round(iv * 1.02, 4),
                ce_delta=round(ce_g["delta"], 4), pe_delta=round(pe_g["delta"], 4),
                ce_gamma=round(ce_g["gamma"], 6), pe_gamma=round(pe_g["gamma"], 6),
                ce_theta=round(ce_g["theta"], 3), pe_theta=round(pe_g["theta"], 3),
                ce_vega=round(ce_g["vega"], 4), pe_vega=round(pe_g["vega"], 4),
                ce_bid=round(max(ce_px - 0.5, 0.05), 2), ce_ask=round(ce_px + 0.5, 2),
                pe_bid=round(max(pe_px - 0.5, 0.05), 2), pe_ask=round(pe_px + 0.5, 2),
                ce_prev_ltp=round(ce_px * (1 + self._rng.gauss(0, 0.01)), 2),
                pe_prev_ltp=round(pe_px * (1 + self._rng.gauss(0, 0.01)), 2),
            ))

        return Snapshot(
            index=idx, expiry=expiry or _default_expiry(idx), spot=spot, atm_strike=atm,
            strikes=strikes, prev_close=round(spot * 0.998, 2),
            day_high=round(spot * 1.004, 2), day_low=round(spot * 0.995, 2),
            pdh=round(spot * 1.006, 2), pdl=round(spot * 0.993, 2),
            source="demo", timestamp=datetime.now(timezone.utc),
        )

    def _oi_bucket(self, idx: str, strike: float, opt: str, moneyness: float) -> int:
        base = 20000 + int(60000 * math.exp(-((moneyness) ** 2) / 0.00008))
        val = max(1000, base + self._rng.randint(-4000, 4000))
        self._oi_memory[(idx, strike, opt)] = val
        return val

    def list_expiries(self, index: str) -> List[str]:
        return [_default_expiry(index)]

    async def get_historical(self, token: str, exchange: str, interval: str,
                             frm: datetime, to: datetime) -> pd.DataFrame:
        n = max(1, int((to - frm).total_seconds() // 300))
        price = _BASE_SPOT.get(token.upper(), 24000.0)
        rows = []
        for i in range(n):
            price *= 1.0 + self._rng.gauss(0, 0.0008)
            hi = price * (1 + abs(self._rng.gauss(0, 0.0005)))
            lo = price * (1 - abs(self._rng.gauss(0, 0.0005)))
            rows.append({"timestamp": frm + timedelta(minutes=5 * i),
                         "open": price, "high": hi, "low": lo, "close": price,
                         "volume": self._rng.randint(1000, 50000)})
        return pd.DataFrame(rows)


def _default_expiry(index: str) -> str:
    today = datetime.now(timezone.utc)
    days_ahead = (3 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).strftime("%d%b%Y").upper()
