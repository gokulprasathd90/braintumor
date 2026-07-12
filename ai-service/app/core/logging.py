"""
logging.py — Structured logging configuration using Loguru.

Provides a single pre-configured `logger` instance used throughout
the AI service.  All log lines are emitted to:
  • stderr  (coloured, human-readable in development)
  • a rotating log file  (JSON in production, plain text in development)

Usage anywhere in the app:
    from app.core.logging import logger
    logger.info("Prediction complete", extra={"image_id": "abc-123"})
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def _configure_logger() -> None:
    """Remove Loguru defaults and add our sinks."""

    # Remove the default handler added by Loguru at import time
    logger.remove()

    is_dev = settings.ai_service_env == "development"

    # ── Console sink ──────────────────────────────────────────────────────────
    console_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=console_fmt,
        colorize=is_dev,
        backtrace=is_dev,
        diagnose=is_dev,
    )

    # ── File sink (rotating, 10 MB per file, keep 7 days) ─────────────────────
    log_file: Path = settings.log_dir / "ai_service_{time:YYYY-MM-DD}.log"

    file_fmt = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{line} | {message}"
    )

    logger.add(
        str(log_file),
        level=settings.log_level.upper(),
        format=file_fmt,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,          # thread-safe async write
        backtrace=True,
        diagnose=False,        # never write local variable values to disk
    )

    logger.info(
        f"Logger initialised | env={settings.ai_service_env} "
        f"level={settings.log_level} log_dir={settings.log_dir}"
    )


# Initialise once at import time
_configure_logger()

__all__ = ["logger"]
