# API (all JSON, paper mode)

| Method | Path | Returns |
|---|---|---|
| GET | /api/health | status, mode, stale flag, last tick age |
| POST | /api/login | demo session (no credentials accepted) |
| GET | /api/overview | indices, stocks, layer summary, portfolio |
| GET | /api/chain?symbol=NIFTY50 | spot, ATM, PCR, support/resistance, rows |
| GET | /api/layers?symbol= | 6 layer verdicts + recommendation |
| GET | /api/plans?symbol= | entry/SL/T1/T2/RR plans |
| GET | /api/strategies | strategies, weights per regime, enabled flags |
| POST | /api/strategy/{name}?enabled=true | toggle a strategy |
| GET | /api/risk | limits + live risk state |
| POST | /api/kill, /api/resume | kill switch |
| GET | /api/notifications | recent orders / halts |
| GET | /api/candles/{symbol} | OHLCV candles |
| GET | /api/backtest?symbol=&bars= | synthetic backtest metrics |
| GET | /api/state | portfolio, positions, orders, signals |
| WS | /ws | live ticks + state for desktop terminal |