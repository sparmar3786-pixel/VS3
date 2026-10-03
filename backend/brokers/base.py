"""Abstract data-source interface shared by all brokers/adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional

import pandas as pd

from backend.models import Snapshot, Tick


class DataSourceError(RuntimeError):
    """Raised for any broker/transport failure."""


class AuthError(DataSourceError):
    """Raised when the session/token is invalid or expired."""


class RateLimitError(DataSourceError):
    """Raised when the upstream rate limit is hit."""


TickCallback = Callable[[Tick], None]
AsyncTickCallback = Callable[[Tick], Awaitable[None]]


@dataclass
class Capabilities:
    """Declares what a data source can actually provide (drives graceful degradation)."""

    streaming: bool = False
    greeks: bool = False
    option_chain: bool = True
    historical: bool = False
    oi: bool = True
    volume: bool = True
    bid_ask: bool = False
    depth: bool = False
    trade_level: bool = False


class DataSource(ABC):
    """A pluggable market-data source.

    Implementations: Angel One SmartAPI, NSE public fallback, MCP bridge, demo.
    """

    name: str = "abstract"
    capabilities: Capabilities = Capabilities()

    def __init__(self, *, rps: float = 5.0) -> None:
        self.rps = rps
        self._connected = False
        self._last_call = 0.0

    @abstractmethod
    async def connect(self) -> None:
        """Establish session / authenticate. Idempotent."""

    @abstractmethod
    async def close(self) -> None:
        """Tear down sockets / sessions."""

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def get_ltp(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[float]:
        ...

    @abstractmethod
    async def get_quote(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[Tick]:
        ...

    async def get_market_data(self, mode: str, tokens: List[Dict[str, str]]) -> List[Tick]:
        """Batch quote. Default implementation loops :meth:`get_quote`."""
        out: List[Tick] = []
        for t in tokens:
            tick = await self.get_quote(
                t.get("symbol", ""), t.get("token", ""), t.get("exchange", "NSE")
            )
            if tick is not None:
                out.append(tick)
        return out

    @abstractmethod
    async def get_option_chain(self, index: str, expiry: Optional[str] = None) -> Snapshot:
        ...

    async def get_historical(
        self, token: str, exchange: str, interval: str, frm: datetime, to: datetime,
    ) -> pd.DataFrame:
        """Return OHLCV candles. Sources without history return an empty frame."""
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    async def subscribe(self, tokens: List[Dict[str, str]], on_tick: AsyncTickCallback) -> None:
        """Start streaming ticks for ``tokens``. No-op for non-streaming sources."""
        return None

    async def unsubscribe(self, tokens: List[Dict[str, str]]) -> None:
        return None

    def list_expiries(self, index: str) -> List[str]:
        return []

    def resolve_token(self, index: str, strike: float, option_type: str, expiry: str) -> Optional[str]:
        """Map an option contract to a source-specific token. None if unknown."""
        return None
