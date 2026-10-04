from datetime import datetime, timedelta, timezone

from backend.market_cache import cache_age_sec, save_snapshot
from backend.models import Snapshot


def test_disk_age_uses_fetch_timestamp_not_file_mtime(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKET_CACHE_DIR", str(tmp_path))
    fetched = datetime.now(timezone.utc) - timedelta(seconds=30)
    snap = Snapshot(index="NIFTY", timestamp=fetched, source="angel")
    save_snapshot(snap, source="angel")

    age = cache_age_sec("NIFTY")
    assert age is not None
    assert 29.0 <= age <= 31.0
