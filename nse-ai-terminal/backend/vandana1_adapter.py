"""Compatibility adapter for the production Vandana1 FastAPI server.

The copied Vandana1 modules intentionally remain isolated under backend/vandana1.
Only this adapter adds that directory to Python's import path, so their legacy
absolute imports resolve locally without colliding with VS3's old demo modules.
"""
from pathlib import Path
import sys

VANDANA_ROOT = Path(__file__).resolve().parent / "vandana1"
if str(VANDANA_ROOT) not in sys.path:
    sys.path.insert(0, str(VANDANA_ROOT))

from server import app as app  # noqa: E402,F401
