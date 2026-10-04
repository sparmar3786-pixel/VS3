"""Single-flight option-chain cache and stale/failure policy for VS3."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

from backend.brokers.base import AuthError
from backend.models import Snapshot


@dataclass
class ChainResult:
    data: Optional[Snapshot]
    age_sec: float
    source: str
    state: str
    trade_allowed: bool


class ChainCache:
    def __init__(self, *, ttl_sec: float = 15.0, stale_sec: float = 60.0,
                 failure_backoff_sec: float = 15.0) -> None:
        self.ttl_sec = ttl_sec
        self.stale_sec = stale_sec
        self.failure_backoff_sec = failure_backoff_sec
        self._locks: Dict[str, asyncio.Lock] = {}
        self._memory: Dict[str, tuple[Snapshot, float, str]] = {}
        self._negative_until: Dict[str, float] = {}

    def _lock(self, index: str) -> asyncio.Lock:
        key = index.upper()
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _memory_result(self, index: str, now: Optional[float] = None) -> Optional[ChainResult]:
        item = self._memory.get(index.upper())
        if not item:
            return None
        snapshot, fetched_mono, source = item
        age = max(0.0, (now or time.monotonic()) - fetched_mono)
        if age <= self.ttl_sec:
            return ChainResult(snapshot, age, source, "FRESH", True)
        return None

    def _last_good_memory(self, index: str, now: Optional[float] = None) -> Optional[ChainResult]:
        item = self._memory.get(index.upper())
        if not item:
            return None
        snapshot, fetched_mono, source = item
        age = max(0.0, (now or time.monotonic()) - fetched_mono)
        if age <= self.stale_sec:
            return ChainResult(snapshot, age, source, "DEGRADED", False)
        return None

    def put(self, snapshot: Snapshot, source: str) -> ChainResult:
        self._memory[snapshot.index.upper()] = (snapshot, time.monotonic(), source)
        return ChainResult(snapshot, 0.0, source, "FRESH", True)

    async def get_chain(
        self, index: str, fetch: Callable[[], Awaitable[Snapshot]], *,
        disk_fallback: Callable[[str], Optional[Snapshot]],
        disk_age: Callable[[str], Optional[float]],
        auth_refresh: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> ChainResult:
        key = index.upper()
        cached = self._memory_result(key)
        if cached:
            return cached

        async with self._lock(key):
            # Double-check after the per-index lock: concurrent callers share one fetch.
            cached = self._memory_result(key)
            if cached:
                return cached

            if time.monotonic() < self._negative_until.get(key, 0.0):
                memory = self._last_good_memory(key)
                if memory:
                    return memory
                snap = disk_fallback(key)
                age = disk_age(key)
                if snap is not None and age is not None and age <= self.stale_sec:
                    return ChainResult(snap, age, getattr(snap, "source", "disk"),
                                       "DEGRADED", False)
                return ChainResult(None, max(0.0, age or 0.0), "none", "DATA_GAP", False)

            try:
                snapshot = await fetch()
                if snapshot is None:
                    raise RuntimeError("empty option-chain snapshot")
                source = getattr(snapshot, "source", "angel") or "angel"
                return self.put(snapshot, source)
            except AuthError:
                if auth_refresh is not None:
                    try:
                        await auth_refresh()
                        snapshot = await fetch()
                        if snapshot is not None:
                            source = getattr(snapshot, "source", "angel") or "angel"
                            return self.put(snapshot, source)
                    except Exception:
                        pass
                self._negative_until[key] = time.monotonic() + self.failure_backoff_sec
            except Exception:
                self._negative_until[key] = time.monotonic() + self.failure_backoff_sec

            memory = self._last_good_memory(key)
            if memory:
                return memory
            snap = disk_fallback(key)
            age = disk_age(key)
            if snap is not None and age is not None and age <= self.stale_sec:
                return ChainResult(snap, age, getattr(snap, "source", "disk"),
                                   "DEGRADED", False)
            return ChainResult(None, max(0.0, age or 0.0), "none", "DATA_GAP", False)
