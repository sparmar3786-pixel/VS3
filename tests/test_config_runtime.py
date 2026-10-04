from backend.config import Settings

def test_market_cache_toggle_is_a_boolean_property():
    assert Settings(market_cache_enabled="on").market_cache_on is True
    assert Settings(market_cache_enabled="off").market_cache_on is False
