import asyncio
import time
from datetime import datetime, timezone

from backend.models import Snapshot
from backend.pipeline.chain_cache import ChainCache


def make_snapshot(index="NIFTY"):
    return Snapshot(index=index, timestamp=datetime.now(timezone.utc), source="angel")


def test_concurrent_calls_single_flight():
    async def run():
        cache = ChainCache(ttl_sec=15, stale_sec=60, failure_backoff_sec=15)
        calls = 0

        async def fetch():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.02)
            return make_snapshot()

        results = await asyncio.gather(*[
            cache.get_chain("NIFTY", fetch,
                            disk_fallback=lambda _: None,
                            disk_age=lambda _: None)
            for _ in range(10)
        ])
        assert calls == 1
        assert all(r.state == "FRESH" for r in results)

    asyncio.run(run())


def test_failure_backoff_allows_only_one_retry_window():
    async def run():
        cache = ChainCache(ttl_sec=0, stale_sec=60, failure_backoff_sec=15)
        calls = 0

        async def fetch():
            nonlocal calls
            calls += 1
            raise RuntimeError("upstream down")

        for _ in range(4):
            result = await cache.get_chain(
                "NIFTY", fetch,
                disk_fallback=lambda _: None,
                disk_age=lambda _: None,
            )
            assert result.state == "DATA_GAP"
            assert result.trade_allowed is False

        assert calls == 1

    asyncio.run(run())


def test_age_boundaries():
    async def run():
        cache = ChainCache(ttl_sec=15, stale_sec=60)
        cache._memory["NIFTY"] = (make_snapshot(), time.monotonic() - 15.0, "angel")
        assert cache._memory_result("NIFTY") is not None

        cache._memory["NIFTY"] = (make_snapshot(), time.monotonic() - 15.01, "angel")
        assert cache._memory_result("NIFTY") is None
        assert cache._last_good_memory("NIFTY") is not None

        cache._memory["NIFTY"] = (make_snapshot(), time.monotonic() - 60.01, "angel")
        assert cache._last_good_memory("NIFTY") is None

    asyncio.run(run())


def test_all_paths_use_same_schema():
    async def run():
        cache = ChainCache()

        async def fail():
            raise RuntimeError("down")

        results = [
            await cache.get_chain(
                "NIFTY", lambda: asyncio.sleep(0, result=make_snapshot()),
                disk_fallback=lambda _: None,
                disk_age=lambda _: None,
            ),
            await cache.get_chain(
                "BANKNIFTY", fail,
                disk_fallback=lambda _: None,
                disk_age=lambda _: None,
            ),
        ]
        for result in results:
            assert hasattr(result, "data")
            assert hasattr(result, "age_sec")
            assert hasattr(result, "source")
            assert hasattr(result, "state")
            assert hasattr(result, "trade_allowed")

    asyncio.run(run())
