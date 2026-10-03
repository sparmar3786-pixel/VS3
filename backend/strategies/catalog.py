from dataclasses import dataclass

@dataclass(frozen=True)
class Strategy:
    id: int
    name: str
    section: str

_NAMES = """
Long Buildup|Short Buildup|Short Covering|Long Unwinding|Fresh OI Addition|OI Flush|OI Shift|OI Migration|OI Concentration|OI Concentration Shift|OI Concentration Break|OI Cluster Migration|Maximum OI Strike|Maximum Change-in-OI Strike|OI Wall Break|OI Wall Rebuild|OI Wall Removal|OI Accumulation|OI Distribution|OI Velocity|OI Acceleration|OI Normalization|OI Divergence|CE/PE OI Imbalance|CE/PE OI Spread|Cross-Strike OI Rotation|ATM OI Battle|ATM OI Migration|Premium Momentum|Premium Velocity|Premium Acceleration|Premium Explosion|Premium Collapse|Premium Reversal|Premium/OI Divergence|Price/OI Divergence|Price/Volume Divergence|Price Acceptance|Price Rejection|Rapid LTP Repricing|Price Stalling|Intrinsic/Extrinsic Value|Time-Value Compression|Moneyness Tracking|Volume Confirmation|Volume Spike|Volume Explosion|Volume/OI Ratio|Volume Acceleration|Volume Normalization|Volume Divergence|Volume + Price Confirmation|Volume + OI Confirmation|Multi-Strike Volume Expansion|CE Independent Engine|PE Independent Engine|CE/PE Pressure Index|CE/PE Premium Spread|CE/PE Volume Spread|CE/PE Chain Imbalance|Call-Writing Zone|Put-Writing Zone|Call-Unwinding Zone|Put-Unwinding Zone|CE Resistance Ladder|PE Support Ladder|CE→PE Rotation|PE→CE Rotation|Call Buyer Trap|Put Buyer Trap|Call Writer Trap|Put Writer Trap|Seller Pressure Detection|Probable Short-Covering Zone|Premium ↑ + OI ↓|Short-Covering + Volume|Multi-Strike Short Covering|Broad Short-Covering Wave|Short-Covering Confirmation|Short-Covering Failure|Short-Covering Exhaustion|Seller Absorption|Buyer Absorption|Seller Defence Zone|Seller Defence Failure|Position Exit Detection|Position Re-entry Detection|Position Flip Detection|Position Rotation|Position Exhaustion|ATM Strategy|ITM Strategy|OTM Strategy|ATM ±3 Strike Map|ATM ±5 Strike Map|Nearest OI Cluster|Nearest Volume Cluster|Highest Change-OI Cluster|Strike Pressure Gradient|Strike Momentum Ranking|Strike Liquidity Ranking|Strike Migration|Strike Flip|Strike Rejection|Strike Acceptance|Repeated Strike Defence|Strike Defence Failure|OI Wall Strategy|Option Chain Pressure Score|Chain-Wide Momentum Burst|OI Support|OI Resistance|Dynamic Support/Resistance|Support Breakdown|Resistance Breakout|Previous Day High|Previous Day Low|Day High Breakout|Day Low Breakdown|Previous Close Reaction|Weekly Level Reaction|OI Support/Resistance Rotation|EMA 8/13 Crossover|EMA 20/50 Trend|VWAP Reclaim|VWAP Breakdown|VWAP Reversal|Opening Range Breakout|Range Breakout|Range Breakdown|Range Rejection|Trend Continuation|Trend Reversal|Momentum Expansion|Momentum Exhaustion|Pullback Entry|Breakout + Retest|Breakdown + Retest|Failed Breakout|Failed Breakdown|Higher High + Higher Low|Lower High + Lower Low|Break of Structure|Market Structure Break|Change of Character|Structure Retest|Range Expansion|Range Contraction|Compression → Expansion|RSI Momentum|RSI Overbought|RSI Oversold|RSI Divergence|MACD Momentum|MACD Crossover|MACD Divergence|EMA + RSI|EMA + MACD|RSI + MACD + OI|ATR Expansion|ATR Contraction|Bollinger Squeeze|Bollinger Expansion|Bollinger Breakout|Volatility Compression|Volatility Expansion|Volatility Normalization|Delta Momentum|Delta-based Strike Selection|Gamma Expansion|Gamma Risk Zone|Gamma-Sensitive Strike Detection|Theta Decay|Theta Acceleration|Theta vs Momentum|Vega Expansion|IV Expansion|IV Crush|IV Confirmation|IV Skew|Call/Put IV Difference|IV Surface Shift|Realized vs Implied Volatility|IV + OI Confirmation|Expiry-Day Premium Decay|Expiry ATM Compression|Expiry Strike Pinning|Expiry Breakout|Expiry Breakdown|Expiry Short Covering|Expiry Long Unwinding|Expiry Gamma Expansion|Expiry Compression|Expiry Expansion|Days-to-Expiry Adjustment|Expiry Distance Adjustment|Weekly/Monthly Expiry Behaviour|Expiry Transition|Post-Expiry Reset|Expiry OI Migration|Last-Hour Momentum|Last-Hour Reversal|Liquidity Expansion|Liquidity Exhaustion|Liquidity Sweep|Liquidity Grab + Reversal|Liquidity Grab + Continuation|Liquidity Void|Liquidity Refill|Liquidity Concentration|Bid-Ask Spread Expansion|Bid-Ask Spread Compression|LTP vs Mid-Price Divergence|Tick Momentum|Tick Reversal|Consecutive Up/Down Moves|Absorption Detection|Aggressive Buying|Aggressive Selling|Bull Trap|Bear Trap|Buyer Trap|Seller Trap|False OI Signal|False Volume Signal|False Breakout Reversal|False Breakdown Reversal|Exhaustion → Reversal|Extreme OI → Reversal|Extreme Premium → Reversal|Momentum Reversal|Multi-Strike Reversal|Opposite-Side Reversal|Opposite-Side Override|Strong Bull Regime|Strong Bear Regime|Sideways/Range Regime|High-Volatility Regime|Low-Volatility Regime|Breakout Regime|Mean-Reversion Regime|Expiry Compression Regime|Expansion Regime|Regime Switching|Adaptive Momentum|Adaptive Mean Reversion|Z-Score Extreme|Rolling Z-Score|Mean Reversion|Momentum Factor|Relative Strength|Rolling Correlation|Beta Relationship|Volatility-Adjusted Momentum|Return Distribution|Statistical Outlier Detection|Anomaly Detection|Percentile Extreme Detection|Momentum Normalization|Volatility Normalization|NIFTY vs BANKNIFTY Divergence|BANKNIFTY vs FINNIFTY Divergence|NIFTY vs SENSEX Divergence|Index Relative Strength|Index Relative Momentum|Index Relative Volatility|Index Leadership Detection|Breadth Confirmation|Breadth vs Index Divergence|Sector Strength Confirmation|Sector Rotation|Market Leadership Shift|Risk-On/Risk-Off Detection|Index Divergence|Fibonacci Retracement|Fibonacci Extension|Swing Retracement|Pivot Points|CPR|CPR Breakout|CPR Rejection|Opening Range + Pivot|Previous Close Level|Weekly Reference Level|Early Entry|Confirmation Entry|Retest Entry|Late Entry Filter|Chasing Filter|Dynamic Stop Loss|Structure Stop Loss|Premium Stop Loss|ATR Stop Loss|Trailing Stop|Break-Even Shift|Partial Target|Target Extension|Risk/Reward Gate|Maximum-Loss Filter|Gap-Risk Filter|Wide-Spread Filter|Low-Liquidity Filter|Time Exit|OI-Wall Target|R:R Target|Strategy Conflict Engine|Multi-Confirmation Engine|Weak-Signal Suppression|Late-Signal Suppression|Signal Expiry Timer|Signal Cooldown|Duplicate-Signal Filter|Contradiction Detector|Repeated-Failure Suppression|Opposite-Side Strong-Signal Block|No-Trade Intelligence|Data-Quality Signal Gate|Timestamp Chronology|Data Freshness|Timestamp Synchronization|Missing Tick Detection|Abnormal Tick Detection|Data Gap Detection|Duplicate Tick Detection|API Latency Monitor|Feed Recovery Detection|Market-Status Validation|Exchange-Mismatch Protection|Invalid Strike Protection|Missing OI Protection|Missing Volume Protection|Stale Quote Block|Strategy-wise Backtest|Index-wise Backtest|CE-vs-PE Backtest|Expiry-vs-Non-expiry Backtest|Time-window Backtest|Strike-distance Backtest|Market-regime Backtest|Walk-Forward Testing|Out-of-Sample Testing|Monte-Carlo Trade Sequence Analysis|Parameter Sensitivity|Strategy Robustness Test|Slippage Sensitivity|Transaction-Cost Sensitivity|Forward Paper Validation|Live-vs-Backtest Drift Detection|Maximum Drawdown|Average R|Expectancy|Profit Factor|Consecutive Wins/Losses|Time-of-Day Performance|Multi-Model Agreement|Multi-Model Disagreement|AI Data-Quality Check|AI Stale-Data Detection|AI Contradiction Detection|AI Evidence Trace|AI Hallucination Guard|AI Final WAIT Override|Pattern Discovery|Candidate Strategy Discovery|Strategy Behaviour Memory|Strategy Failure-Pattern Analysis|Market-Regime Behaviour Memory|CALL Qualification|PUT Qualification|CALL vs PUT Conflict|Opposite-Side Override|Liquidity Gate|Risk/R:R Gate|Data-Quality Gate|Confidence/Confirmation Gate|Final WAIT|NO QUALIFYING TRADE
""".strip().split("|")

SECTIONS = (
    "OI / Position Strategies","Premium / Price Strategies","Volume Strategies","CE/PE Strategies",
    "Short-Covering / Seller Strategies","Strike / Option-Chain Strategies","Support / Resistance",
    "Trend / Price Action","RSI / MACD / Volatility","Greeks / IV","Expiry Strategies",
    "Liquidity / Microstructure","Trap / Reversal","Market Regime","Quant / Statistical",
    "Cross-Index / Market Breadth","Fibonacci / Classical Levels","Entry / Exit / Risk",
    "Signal Intelligence","Data / Reliability","Backtest / Validation","AI / Strategy Discovery",
    "Final Decision Engine"
)

assert len(_NAMES) == 377, len(_NAMES)

STRATEGY_REGISTRY = {}
_STARTS = (1,29,45,55,73,91,111,123,150,168,185,203,220,235,247,261,275,285,306,318,333,355,368)
for i, name in enumerate(_NAMES, 1):
    section_idx = 0
    for j, start in enumerate(_STARTS):
        if i >= start:
            section_idx = j
    STRATEGY_REGISTRY[i] = Strategy(i, name, SECTIONS[section_idx] if section_idx < len(SECTIONS) else "Unknown")

def strategy_search(query: str = "") -> list[Strategy]:
    q = query.strip().lower()
    return [s for s in STRATEGY_REGISTRY.values() if not q or q in s.name.lower() or q in s.section.lower()]

def module_names() -> list[str]:
    return list(_NAMES)

_FAMILY_BY_RANGE = (
    (1, 28, "OI / Position"),
    (29, 44, "Premium / Price"),
    (45, 54, "Volume"),
    (55, 72, "CE/PE"),
    (73, 90, "Short-Covering / Seller"),
    (91, 110, "Strike / Option-Chain"),
    (111, 122, "Support/Resistance"),
    (123, 149, "Trend/Price Action"),
    (150, 167, "RSI/MACD/Volatility"),
    (168, 184, "Greeks/IV"),
    (185, 202, "Expiry"),
    (203, 219, "Liquidity/Microstructure"),
    (220, 234, "Trap/Reversal"),
    (235, 246, "Market Regime"),
    (247, 260, "Quant/Statistical"),
    (261, 274, "Cross-Index/Breadth"),
    (275, 284, "Fibonacci/Classical"),
    (285, 305, "Entry/Exit/Risk"),
    (306, 317, "Signal Intelligence"),
    (318, 332, "Data/Reliability"),
    (333, 354, "Backtest/Validation"),
    (355, 367, "AI/Strategy Discovery"),
    (368, 377, "Final Decision Engine"),
)

def _family(number: int) -> str:
    for lo, hi, family in _FAMILY_BY_RANGE:
        if lo <= number <= hi:
            return family
    return "Final Decision Engine"

def build_meta():
    from backend.models import StrategyMeta
    return [
        StrategyMeta(id=f"S{number:03d}", number=number, name=name, family=_family(number),
                     inputs=[], math="", required_data=[], output="signal",
                     failure_conditions=[], advanced=False, implemented=True)
        for number, name in enumerate(_NAMES, 1)
    ]