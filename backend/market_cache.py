"""Durable market snapshot cache for live recovery and after-market analysis."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from typing import Optional

from backend.models import Snapshot

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_OPEN = dtime(9, 15)
DEFAULT_CLOSE = dtime(15, 30)

def cache_dir() -> Path:
    p = Path(os.getenv("MARKET_CACHE_DIR", "data/market_cache"))
    p.mkdir(parents=True, exist_ok=True)
    return p

def is_market_open(now: Optional[datetime] = None) -> bool:
    now = now.astimezone(IST) if now else datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return DEFAULT_OPEN <= now.time() <= DEFAULT_CLOSE

def _path(index: str) -> Path:
    safe = "".join(c for c in index.upper() if c.isalnum() or c in "_-")
    return cache_dir() / f"{safe}.json"

def save_snapshot(snapshot: Snapshot, *, source: str = "live") -> None:
    payload = {
        "saved_at": time.time(),
        "saved_at_iso": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "snapshot": snapshot.model_dump(mode="json"),
    }
    tmp = _path(snapshot.index).with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(_path(snapshot.index))

def load_snapshot(index: str) -> Optional[Snapshot]:
    p = _path(index)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        return Snapshot.model_validate(payload["snapshot"])
    except Exception:
        return None

def cache_age_sec(index: str, now: Optional[float] = None) -> Optional[float]:
    p = _path(index)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        saved = float(payload.get("saved_at", p.stat().st_mtime))
        return max(0.0, (now or time.time()) - saved)
    except Exception:
        return None
