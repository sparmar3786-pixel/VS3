"""Central configuration for nse-ai-terminal.

All tunables live here and are sourced from environment variables / `.env`.
No magic numbers should be scattered across the codebase — import `get_settings()`.

Locked-principle notes:
    * `min_rr` is the single risk/R:R gate constant from the tested Run60/Run93 core.
      Do NOT change it silently; changing it is a *core* modification requiring the
      user's explicit approval.
    * `advanced_engine` toggles the ADVANCED OPTIONAL layer. The core locked engine
      (Run60 + Run93) always runs when data quality passes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings (pydantic v2)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------- data source ----------------
    data_source: str = "angel_one"
    data_fallback_order: str = "angel_one"

    # ---------------- Angel One SmartAPI ----------------
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_pin: str = ""
    angel_totp_secret: str = ""
    angel_refresh_token: str = ""
    angel_base_url: str = "https://apiconnect.angelbroking.com"
    angel_ws_url: str = "wss://smartapisocket.angelone.in/smart-stream"
    angel_publisher_login: str = "https://smartapi.angelone.in/publisher-login"

    # ---------------- engine ----------------
    advanced_engine: str = "on"
    min_trade_plans: int = 5
    min_rr: float = 1.8
    max_risk_per_trade: float = 0.01
    max_total_risk: float = 0.04

    # per-index lot sizes
    nifty_lot_size: int = 25
    banknifty_lot_size: int = 15
    finnifty_lot_size: int = 40
    midcpnifty_lot_size: int = 50
    sensex_lot_size: int = 10
    bankex_lot_size: int = 15

    # ---------------- live orders (keep off) ----------------

    # ---------------- data quality gate ----------------
    max_tick_age_sec: float = 5.0
    max_snapshot_age_sec: float = 10.0
    max_tick_jump_pct: float = 5.0
    rate_limit_rps: float = 8.0
    engine_cycle_sec: float = 3.0
    nse_mcp_poll_sec: float = 15.0
    market_cache_enabled: str = "on"
    after_market_ai_interval_sec: float = 300.0
    market_cache_dir: str = "data/market_cache"

    # ---------------- indices ----------------
    indices: str = "NIFTY,BANKNIFTY,FINNIFTY,MIDCPNIFTY,SENSEX,BANKEX"

    # ---------------- AI 6-layer ----------------
    ai_enabled: str = "on"
    ai_transport: str = "direct"           # puter | direct
    puter_auth_mode: str = "browser_token"  # browser_token | server_token
    puter_auth_token: str = ""
    puter_api_base: str = "https://api.puter.com"

    ai_model_l1: str = "gemini-2.5-flash-lite"
    ai_model_l2: str = "groq/openai/gpt-oss-20b"
    ai_model_l3: str = "cerebras/llama-3.3-70b"
    ai_model_l4: str = "deepseek/deepseek-chat"
    ai_model_l5: str = "cloudflare/@cf/zai-org/glm-4.7-flash"
    ai_model_l6: str = "ollama/llama3.2"
    ai_web_search: str = "on"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    google_api_key: str = ""
    xai_api_key: str = ""
    openai_base_url: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    cloudflare_ai_api_key: str = ""
    cloudflare_ai_base_url: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434/v1"

    # ---------------- MCP ----------------
    mcp_enabled: str = "on"
    mcp_config_path: str = "config/mcp_servers.json"
    nse_mcp_transport: str = "stdio"
    nse_mcp_sse_port: int = 8765

    # ---------------- durable cloud memory ----------------
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ---------------- server ----------------
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    db_path: str = "data/strategy_memory.sqlite"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    # ---------------------------- helpers ----------------------------
    @property
    def advanced_enabled(self) -> bool:
        return self.advanced_engine.strip().lower() in {"1", "on", "true", "yes"}

    @property
    def ai_on(self) -> bool:
        return self.ai_enabled.strip().lower() in {"1", "on", "true", "yes"}

    @property
    def mcp_on(self) -> bool:
        return self.mcp_enabled.strip().lower() in {"1", "on", "true", "yes"}

    @property
    def web_search_on(self) -> bool:
        return self.ai_web_search.strip().lower() in {"1", "on", "true", "yes"}

    @property
    @property
    def market_cache_on(self) -> bool:
        return self.market_cache_enabled.strip().lower() in {"1", "on", "true", "yes"}

    @property
    def fallback_order(self) -> List[str]:
        return [s.strip() for s in self.data_fallback_order.split(",") if s.strip()]

    @property
    def index_list(self) -> List[str]:
        return [s.strip().upper() for s in self.indices.split(",") if s.strip()]

    @property
    def cors_list(self) -> List[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    @property
    def ai_models(self) -> dict[str, str]:
        """Layer-id -> configured model id (may be blank to disable a layer)."""
        return {
            "L1": self.ai_model_l1,
            "L2": self.ai_model_l2,
            "L3": self.ai_model_l3,
            "L4": self.ai_model_l4,
            "L5": self.ai_model_l5,
            "L6": self.ai_model_l6,
        }

    def lot_size(self, index: str) -> int:
        """Return the configured lot size for `index` (case-insensitive)."""
        idx = index.upper().replace(" ", "")
        mapping = {
            "NIFTY": self.nifty_lot_size,
            "NIFTY50": self.nifty_lot_size,
            "BANKNIFTY": self.banknifty_lot_size,
            "FINNIFTY": self.finnifty_lot_size,
            "MIDCPNIFTY": self.midcpnifty_lot_size,
            "SENSEX": self.sensex_lot_size,
            "BANKEX": self.bankex_lot_size,
        }
        return mapping.get(idx, 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return Settings()
