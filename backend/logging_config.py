"""Structured logging for nse-ai-terminal.

Uses ``loguru``. JSON-friendly, module-bound loggers, and a rotating file sink.
Call :func:`setup_logging` once at process start.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from backend.config import get_settings

_CONFIGURED = False

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[module]}</cyan> | <level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[module]} | {message}"
)


def setup_logging() -> None:
    """Configure loguru sinks exactly once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    logger.remove()
    logger.configure(extra={"module": "app"})

    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=_CONSOLE_FORMAT,
        colorize=True,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    log_dir = Path("data")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_dir / "terminal.log"),
        level=settings.log_level.upper(),
        format=_FILE_FORMAT,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    _CONFIGURED = True


def get_logger(module: str, **context: Any):
    """Return a logger bound to ``module`` (and optional static context)."""
    return logger.bind(module=module, **context)
