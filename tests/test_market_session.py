from datetime import datetime, time, timezone
from backend.market_cache import is_market_open

def test_market_session_weekday_open():
    dt=datetime(2026,10,5,10,0,tzinfo=timezone.utc).replace(hour=4,minute=30)
    # 10:00 IST = 04:30 UTC
    assert is_market_open(dt) is True

def test_market_session_weekend_closed():
    dt=datetime(2026,10,4,4,30,tzinfo=timezone.utc)
    assert is_market_open(dt) is False

def test_market_session_after_close():
    dt=datetime(2026,10,5,10,31,tzinfo=timezone.utc)
    # 16:01 IST
    assert is_market_open(dt) is False
