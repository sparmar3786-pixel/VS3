"""Import every part module so @register populates the pipeline registry."""
from __future__ import annotations
from backend.pipeline import (
    part01_data_input, part02_data_quality, part03_market_regime,
    part04_price_action, part05_indicators, part06_oi_engine,
    part07_premium_volume, part08_seller_pressure, part09_ce_engine,
    part10_pe_engine, part11_opposite_side_override, part12_strike_engine,
    part13_support_resistance, part14_greeks_engine, part15_vol_surface,
    part16_order_flow, part17_multi_leg, part18_expiry_engine,
    part19_liquidity_engine, part20_trap_engine, part21_cross_index,
    part22_time_engine, part23_quant_engine, part24_entry_engine,
    part25_risk_engine, part26_confidence_engine, part27_strategy_conflict,
    part28_signal_quality, part29_backtest_engine, part30_strategy_memory,
    part31_six_layer_ai, part32_final_decision,
)  # noqa: F401
