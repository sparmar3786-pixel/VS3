"""Read-only Groww market-data adapter.

Only market-data endpoints are exposed here. Authentication is an access token
supplied by the server configuration or request header; no token is persisted.
"""
from __future__ import annotations

from typing import Any, Dict
import requests

DEFAULT_BASE = "https://api.groww.in/v1"


class GrowwError(RuntimeError):
    pass


class GrowwClient:
    def __init__(self, access_token: str = "", base_url: str = DEFAULT_BASE):
        self.access_token = (access_token or "").strip()
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise GrowwError("Groww access token is not configured")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-API-VERSION": "1.0",
        }

    def _get(self, path: str, **params: Any) -> Dict[str, Any]:
        r = requests.get(self.base_url + path, headers=self._headers(), params=params, timeout=12)
        try:
            data = r.json()
        except Exception:
            data = {"status": "FAILURE", "error": {"message": r.text[:300]}}
        if r.status_code >= 400 or data.get("status") == "FAILURE":
            err = data.get("error") or {}
            raise GrowwError(f"HTTP {r.status_code}: {err.get('message', 'Groww request failed')}")
        return data

    def status(self) -> dict:
        return {
            "configured": bool(self.access_token),
            "provider": "groww",
            "base_url": self.base_url,
            "read_only": True,
            "token_persisted": False,
        }

    def quote(self, exchange: str, segment: str, trading_symbol: str) -> dict:
        return self._get("/live-data/quote", exchange=exchange, segment=segment,
                         trading_symbol=trading_symbol)

    def ltp(self, segment: str, exchange_symbols: str) -> dict:
        return self._get("/live-data/ltp", segment=segment, exchange_symbols=exchange_symbols)

    def option_chain(self, exchange: str, underlying: str, expiry_date: str) -> dict:
        return self._get(
            f"/option-chain/exchange/{exchange}/underlying/{underlying}",
            expiry_date=expiry_date,
        )
