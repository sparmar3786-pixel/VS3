"""Master strategy registry and evidence-based evaluator.

Every catalog entry is a registered module. A module may be active, inactive, or
unavailable when its required market fields are not supplied. No unavailable
module is allowed to manufacture a trading signal.
"""
from __future__ import annotations
from typing import Any

_GROUPS = [
("OI / Position Strategies", """Long Buildup|Short Buildup|Short Covering|Long Unwinding|Fresh OI Addition|OI Flush|OI Shift|OI Migration|OI Concentration|OI Concentration Shift|OI Concentration Break|OI Cluster Migration|Maximum OI Strike|Maximum Change-in-OI Strike|OI Wall Break|OI Wall Rebuild|OI Wall Removal|OI Accumulation|OI Distribution|OI Velocity|OI Acceleration|OI Normalization|OI Divergence|CE/PE OI Imbalance|CE/PE OI Spread|Cross-Strike OI Rotation|ATM OI Battle|ATM OI Migration"""),
("Premium / Price Strategies", """Premium Momentum|Premium Velocity|Premium Acceleration|Premium Explosion|Premium Collapse|Premium Reversal|Premium/OI Divergence|Price/OI Divergence|Price/Volume Divergence|Price Acceptance|Price Rejection|Rapid LTP Repricing|Price Stalling|Intrinsic/Extrinsic Value|Time-Value Compression|Moneyness Tracking"""),
("Volume Strategies", """Volume Confirmation|Volume Spike|Volume Explosion|Volume/OI Ratio|Volume Acceleration|Volume Normalization|Volume Divergence|Volume + Price Confirmation|Volume + OI Confirmation|Multi-Strike Volume Expansion"""),
("CE/PE Strategies", """CE Independent Engine|PE Independent Engine|CE/PE Pressure Index|CE/PE Premium Spread|CE/PE Volume Spread|CE/PE Chain Imbalance|Call-Writing Zone|Put-Writing Zone|Call-Unwinding Zone|Put-Unwinding Zone|CE Resistance Ladder|PE Support Ladder|CE→PE Rotation|PE→CE Rotation|Call Buyer Trap|Put Buyer Trap|Call Writer Trap|Put Writer Trap"""),
("Short-Covering / Seller Strategies", """Seller Pressure Detection|Probable Short-Covering Zone|Premium ↑ + OI ↓|Short-Covering + Volume|Multi-Strike Short Covering|Broad Short-Covering Wave|Short-Covering Confirmation|Short-Covering Failure|Short-Covering Exhaustion|Seller Absorption|Buyer Absorption|Seller Defence Zone|Seller Defence Failure|Position Exit Detection|Position Re-entry Detection|Position Flip Detection|Position Rotation|Position Exhaustion"""),
("Strike / Option-Chain Strategies", """ATM Strategy|ITM Strategy|OTM Strategy|ATM ±3 Strike Map|ATM ±5 Strike Map|Nearest OI Cluster|Nearest Volume Cluster|Highest Change-OI Cluster|Strike Pressure Gradient|Strike Momentum Ranking|Strike Liquidity Ranking|Strike Migration|Strike Flip|Strike Rejection|Strike Acceptance|Repeated Strike Defence|Strike Defence Failure|OI Wall Strategy|Option Chain Pressure Score|Chain-Wide Momentum Burst"""),
("Support / Resistance", """OI Support|OI Resistance|Dynamic Support/Resistance|Support Breakdown|Resistance Breakout|Previous Day High|Previous Day Low|Day High Breakout|Day Low Breakdown|Previous Close Reaction|Weekly Level Reaction|OI Support/Resistance Rotation"""),
("Trend / Price Action", """EMA 8/13 Crossover|EMA 20/50 Trend|VWAP Reclaim|VWAP Breakdown|VWAP Reversal|Opening Range Breakout|Range Breakout|Range Breakdown|Range Rejection|Trend Continuation|Trend Reversal|Momentum Expansion|Momentum Exhaustion|Pullback Entry|Breakout + Retest|Breakdown + Retest|Failed Breakout|Failed Breakdown|Higher High + Higher Low|Lower High + Lower Low|Break of Structure|Market Structure Break|Change of Character|Structure Retest|Range Expansion|Range Contraction|Compression → Expansion"""),
("RSI / MACD / Volatility", """RSI Momentum|RSI Overbought|RSI Oversold|RSI Divergence|MACD Momentum|MACD Crossover|MACD Divergence|EMA + RSI|EMA + MACD|RSI + MACD + OI|ATR Expansion|ATR Contraction|Bollinger Squeeze|Bollinger Expansion|Bollinger Breakout|Volatility Compression|Volatility Expansion|Volatility Normalization"""),
("Greeks / IV", """Delta Momentum|Delta-based Strike Selection|Gamma Expansion|Gamma Risk Zone|Gamma-Sensitive Strike Detection|Theta Decay|Theta Acceleration|Theta vs Momentum|Vega Expansion|IV Expansion|IV Crush|IV Confirmation|IV Skew|Call/Put IV Difference|IV Surface Shift|Realized vs Implied Volatility|IV + OI Confirmation"""),
("Expiry Strategies", """Expiry-Day Premium Decay|Expiry ATM Compression|Expiry Strike Pinning|Expiry Breakout|Expiry Breakdown|Expiry Short Covering|Expiry Long Unwinding|Expiry Gamma Expansion|Expiry Compression|Expiry Expansion|Days-to-Expiry Adjustment|Expiry Distance Adjustment|Weekly/Monthly Expiry Behaviour|Expiry Transition|Post-Expiry Reset|Expiry OI Migration|Last-Hour Momentum|Last-Hour Reversal"""),
("Liquidity / Microstructure", """Liquidity Expansion|Liquidity Exhaustion|Liquidity Sweep|Liquidity Grab + Reversal|Liquidity Grab + Continuation|Liquidity Void|Liquidity Refill|Liquidity Concentration|Bid-Ask Spread Expansion|Bid-Ask Spread Compression|LTP vs Mid-Price Divergence|Tick Momentum|Tick Reversal|Consecutive Up/Down Moves|Absorption Detection|Aggressive Buying|Aggressive Selling"""),
("Trap / Reversal", """Bull Trap|Bear Trap|Buyer Trap|Seller Trap|False OI Signal|False Volume Signal|False Breakout Reversal|False Breakdown Reversal|Exhaustion → Reversal|Extreme OI → Reversal|Extreme Premium → Reversal|Momentum Reversal|Multi-Strike Reversal|Opposite-Side Reversal|Opposite-Side Override"""),
("Market Regime", """Strong Bull Regime|Strong Bear Regime|Sideways/Range Regime|High-Volatility Regime|Low-Volatility Regime|Breakout Regime|Mean-Reversion Regime|Expiry Compression Regime|Expansion Regime|Regime Switching|Adaptive Momentum|Adaptive Mean Reversion"""),
("Quant / Statistical", """Z-Score Extreme|Rolling Z-Score|Mean Reversion|Momentum Factor|Relative Strength|Rolling Correlation|Beta Relationship|Volatility-Adjusted Momentum|Return Distribution|Statistical Outlier Detection|Anomaly Detection|Percentile Extreme Detection|Momentum Normalization|Volatility Normalization"""),
("Cross-Index / Market Breadth", """NIFTY vs BANKNIFTY Divergence|BANKNIFTY vs FINNIFTY Divergence|NIFTY vs SENSEX Divergence|Index Relative Strength|Index Relative Momentum|Index Relative Volatility|Index Leadership Detection|Breadth Confirmation|Breadth vs Index Divergence|Sector Strength Confirmation|Sector Rotation|Market Leadership Shift|Risk-On/Risk-Off Detection|Index Divergence"""),
("Fibonacci / Classical Levels", """Fibonacci Retracement|Fibonacci Extension|Swing Retracement|Pivot Points|CPR|CPR Breakout|CPR Rejection|Opening Range + Pivot|Previous Close Level|Weekly Reference Level"""),
("Entry / Exit / Risk", """Early Entry|Confirmation Entry|Retest Entry|Late Entry Filter|Chasing Filter|Dynamic Stop Loss|Structure Stop Loss|Premium Stop Loss|ATR Stop Loss|Trailing Stop|Break-Even Shift|Partial Target|Target Extension|Risk/Reward Gate|Maximum-Loss Filter|Gap-Risk Filter|Wide-Spread Filter|Low-Liquidity Filter|Time Exit|OI-Wall Target|R:R Target"""),
("Signal Intelligence", """Strategy Conflict Engine|Multi-Confirmation Engine|Weak-Signal Suppression|Late-Signal Suppression|Signal Expiry Timer|Signal Cooldown|Duplicate-Signal Filter|Contradiction Detector|Repeated-Failure Suppression|Opposite-Side Strong-Signal Block|No-Trade Intelligence|Data-Quality Signal Gate"""),
("Data / Reliability", """Timestamp Chronology|Data Freshness|Timestamp Synchronization|Missing Tick Detection|Abnormal Tick Detection|Data Gap Detection|Duplicate Tick Detection|API Latency Monitor|Feed Recovery Detection|Market-Status Validation|Exchange-Mismatch Protection|Invalid Strike Protection|Missing OI Protection|Missing Volume Protection|Stale Quote Block"""),
("Backtest / Validation", """Strategy-wise Backtest|Index-wise Backtest|CE-vs-PE Backtest|Expiry-vs-Non-expiry Backtest|Time-window Backtest|Strike-distance Backtest|Market-regime Backtest|Walk-Forward Testing|Out-of-Sample Testing|Monte-Carlo Trade Sequence Analysis|Parameter Sensitivity|Strategy Robustness Test|Slippage Sensitivity|Transaction-Cost Sensitivity|Forward Paper Validation|Live-vs-Backtest Drift Detection|Maximum Drawdown|Average R|Expectancy|Profit Factor|Consecutive Wins/Losses|Time-of-Day Performance"""),
("AI / Strategy Discovery", """Multi-Model Agreement|Multi-Model Disagreement|AI Data-Quality Check|AI Stale-Data Detection|AI Contradiction Detection|AI Evidence Trace|AI Hallucination Guard|AI Final WAIT Override|Pattern Discovery|Candidate Strategy Discovery|Strategy Behaviour Memory|Strategy Failure-Pattern Analysis|Market-Regime Behaviour Memory"""),
("Final Decision Engine", """CALL Qualification|PUT Qualification|CALL vs PUT Conflict|Opposite-Side Override|Liquidity Gate|Risk/R:R Gate|Data-Quality Gate|Confidence/Confirmation Gate|Final WAIT|NO QUALIFYING TRADE"""),
]

def _make_registry():
    out, i = [], 1
    for family, raw in _GROUPS:
        for name in raw.split("|"):
            out.append({"id": i, "name": name, "family": family})
            i += 1
    return out

STRATEGIES = _make_registry()
if len(STRATEGIES) != 377:
    raise RuntimeError(f"Master registry must contain 377 modules, got {len(STRATEGIES)}")

_ADVANCED = [
("Volatility Surface Engine", "IV Surface Slope|IV Surface Curvature|IV Surface Shift|IV Smile/Skew Change|ATM IV vs OTM IV Divergence|Term-Structure Slope|Term-Structure Inversion|Moneyness-IV Interaction"),
("Vega-Weighted Order Flow", "Vega-Weighted Net Demand|Vega Flow Acceleration|Vega Flow Reversal|Delta-vs-Vega Flow Separation|Directional-Flow vs Volatility-Flow Separation|Vega Flow Imbalance|Aggregate Vega Pressure"),
("Delta/Vega Information Decomposition", "Delta-Informed Flow|Vega-Informed Flow|Directional Information Score|Volatility Information Score|Combined Information Imbalance"),
("Cross-Option Flow Engine", "Same-Expiry Cross-Strike Flow|Same-Strike CE/PE Flow|Cross-Maturity Flow|Delta-Bucket Flow|Vega-Bucket Flow|Aggregate Option-Flow Pressure"),
("Multi-Leg Strategy Recognition", "Straddle Flow|Strangle Flow|Bull Spread Flow|Bear Spread Flow|Calendar Spread Flow|Butterfly|Iron Butterfly|Condor|Iron Condor|Ratio Spread|Collar|Covered Call|Covered Put|Strip|Strap|Jelly Roll"),
("Trade Classification Engine", "Buyer-Initiated vs Seller-Initiated Classification|Aggressor-Side Volume|Trade-Size Buckets|Large-Lot Flow|Small-Lot Flow|Trade-Flow Imbalance|Flow Persistence"),
]
ADVANCED_STRATEGIES = []
_j = 378
for _family, _raw in _ADVANCED:
    for _name in _raw.split("|"):
        ADVANCED_STRATEGIES.append({"id": _j, "name": _name, "family": _family, "tier": "advanced"})
        _j += 1
ALL_STRATEGIES = STRATEGIES + ADVANCED_STRATEGIES
if len(ADVANCED_STRATEGIES) != 49 or len(ALL_STRATEGIES) != 426:
    raise RuntimeError("Advanced registry must contain 47 modules; total must be 424")

def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def _leg_state(leg):
    if not isinstance(leg, dict): return None
    ltp = _num(leg.get("ltp"))
    prev = _num(leg.get("prev_ltp"))
    oi = _num(leg.get("oi"))
    poi = _num(leg.get("prev_oi"))
    vol = _num(leg.get("vol"))
    return ltp, prev, oi, poi, vol

def _class(leg):
    s = _leg_state(leg)
    if not s or s[0] is None or s[1] is None or s[2] is None or s[3] is None: return None
    dp, doi = s[0]-s[1], s[2]-s[3]
    if dp > 0 and doi > 0: return "LONG_BUILDUP"
    if dp > 0 and doi < 0: return "SHORT_COVERING"
    if dp < 0 and doi > 0: return "SHORT_BUILDUP"
    if dp < 0 and doi < 0: return "LONG_UNWINDING"
    return "NEUTRAL"

def evaluate_strategies(market: dict[str, Any]) -> list[dict[str, Any]]:
    rows = market.get("rows") or []
    spot = _num(market.get("spot"))
    evidence = []
    classes = []
    for r in rows:
        for side in ("ce", "pe"):
            c = _class(r.get(side))
            if c:
                classes.append((side.upper(), float(r.get("strike", 0)), c))
    available = bool(rows)
    counts = {k: sum(1 for _,_,c in classes if c == k) for k in ("LONG_BUILDUP","SHORT_BUILDUP","SHORT_COVERING","LONG_UNWINDING")}
    def state(name):
        if not available: return "unavailable", []
        if name == "Long Buildup" and counts["LONG_BUILDUP"]: return "active", ["premium↑ + OI↑"]
        if name == "Short Buildup" and counts["SHORT_BUILDUP"]: return "active", ["premium↓ + OI↑"]
        if name == "Short Covering" and counts["SHORT_COVERING"]: return "active", ["premium↑ + OI↓"]
        if name == "Long Unwinding" and counts["LONG_UNWINDING"]: return "active", ["premium↓ + OI↓"]
        if name == "Fresh OI Addition" and any((_leg_state(r.get(s)) or (None,)*5)[3] is not None and (_leg_state(r.get(s)) or (None,)*5)[2] > (_leg_state(r.get(s)) or (None,)*5)[3] for r in rows for s in ("ce","pe")):
            return "active", ["OI increased from prior snapshot"]
        if name in {"CALL Qualification","PUT Qualification"}:
            wanted = "CE" if name.startswith("CALL") else "PE"
            hits = [(s,k,c) for s,k,c in classes if s == wanted and c in {"LONG_BUILDUP","SHORT_COVERING"}]
            return ("active", [f"{len(hits)} qualifying {wanted} observations"]) if hits else ("inactive", [])
        if name == "Data-Quality Signal Gate":
            return ("active", ["input chain present"]) if available else ("unavailable", ["option-chain missing"])
        if name in {"NO QUALIFYING TRADE","Final WAIT"}:
            return "inactive", []
        if not available:
            return "unavailable", ["option-chain missing"]
        return "inactive", []
    for s in ALL_STRATEGIES:
        st, ev = state(s["name"])
        evidence.append({"id":s["id"],"name":s["name"],"family":s["family"],"state":st,"evidence":ev})
    return evidence
