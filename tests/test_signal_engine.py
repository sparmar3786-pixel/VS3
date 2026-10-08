from datetime import datetime, timedelta, timezone

from backend.models import Snapshot, StrikeSnapshot
from backend.signal_engine import build_signal


def test_signal_blocks_stale_snapshot():
    s = Snapshot(
        index="NIFTY",
        spot=25000,
        atm_strike=25000,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
        source="nse_mcp",
        strikes=[StrikeSnapshot(strike=25000, ce_oi=100, pe_oi=120, ce_volume=10, pe_volume=10)],
    )
    out = build_signal(s, source="nse_mcp", max_age_sec=240)
    assert out["verdict"] == "WAIT"
    assert "STALE" in out["data_quality"]["flags"]


def test_signal_exposes_support_resistance_and_rr():
    s = Snapshot(
        index="NIFTY",
        spot=25000,
        atm_strike=25000,
        source="angel_one",
        strikes=[
            StrikeSnapshot(strike=24900, ce_oi=50, pe_oi=1000, ce_oi_change=10, pe_oi_change=500,
                           ce_ltp=140, pe_ltp=100, ce_volume=100, pe_volume=100),
            StrikeSnapshot(strike=25000, ce_oi=100, pe_oi=500, ce_oi_change=10, pe_oi_change=300,
                           ce_ltp=120, pe_ltp=110, ce_volume=100, pe_volume=100),
            StrikeSnapshot(strike=25100, ce_oi=1200, pe_oi=50, ce_oi_change=-50, pe_oi_change=10,
                           ce_ltp=80, pe_ltp=130, ce_volume=100, pe_volume=100),
        ],
    )
    out = build_signal(s, source="angel_one", max_age_sec=240, min_rr=1.8)
    assert out["support"] == 24900
    assert out["resistance"] == 25100
    assert out["rr"] >= 1.8
