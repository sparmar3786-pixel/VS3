import os

SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "NIFTY50,BANKNIFTY,FINNIFTY,MIDCPNIFTY,SENSEX,RELIANCE,TCS,HDFCBANK,INFY").split(",")]
FEED_MODE = os.getenv("FEED_MODE", "sim")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
MCP_QUOTE_TOOL = os.getenv("MCP_QUOTE_TOOL", "get_quote")
MCP_SYMBOL_ARG = os.getenv("MCP_SYMBOL_ARG", "symbol")
MCP_POLL_SECONDS = float(os.getenv("MCP_POLL_SECONDS", "1.0"))
MCP_INSTRUMENT_FMT = os.getenv("MCP_INSTRUMENT_FMT", "{symbol}")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

CANDLE_SECONDS = int(os.getenv("CANDLE_SECONDS", "5"))
CAPITAL = float(os.getenv("CAPITAL", "1000000"))
MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", "0.005"))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.20"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "4"))
FEE_RATE = 0.0003
COOLDOWN_CANDLES = 3