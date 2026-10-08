def classify_oi(premium_change: float, oi_change: float) -> str:
    """Classify option positioning from premium and open-interest direction."""
    p = float(premium_change)
    o = float(oi_change)
    if p > 0 and o > 0:
        return "LONG_BUILDUP"
    if p < 0 and o > 0:
        return "SHORT_BUILDUP"
    if p > 0 and o < 0:
        return "SHORT_COVERING"
    if p < 0 and o < 0:
        return "LONG_UNWINDING"
    return "NEUTRAL"
