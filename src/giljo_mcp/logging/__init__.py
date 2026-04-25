# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Structured Logging with Error Codes

Production-grade structured logging using structlog as a processing
pipeline on top of stdlib logging.getLogger():
- JSON output for production (machine-parseable)
- Console output for development (human-readable)
- Error code support for quick diagnosis
- File logging with daily rotation (logs/giljo_mcp.log)

Usage:
    import logging
    from giljo_mcp.logging import ErrorCode

    logger = logging.getLogger(__name__)
    logger.info("Processing request for user_id=%s", user_id)

Environment Variables:
    ENVIRONMENT: Set to "production" for JSON output, anything else for console
    LOG_LEVEL: debug, info, warning, error, critical (default: info)
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler as _BaseRotatingFileHandler
from pathlib import Path
from typing import Optional

import structlog

from .error_codes import ErrorCode, get_error_description


class _SafeRotatingFileHandler(_BaseRotatingFileHandler):
    """RotatingFileHandler that survives Windows file-lock errors.

    On Windows, os.rename() fails with PermissionError (WinError 32) when
    another process (uvicorn worker, log tail) holds the file open. Instead
    of crashing the request, we skip the rotation attempt — the next emit
    will retry when the lock may have cleared.
    """

    def doRollover(self):  # noqa: N802 -- must match parent class name
        try:  # noqa: SIM105 -- suppress is less clear for override pattern
            super().doRollover()
        except PermissionError:
            pass


# Re-export for convenience
__all__ = ["ErrorCode", "configure_logging", "get_error_description"]


# Module-level configuration state
class _LoggingState:
    """Configuration state holder to avoid global statement."""

    configured = False


def _setup_file_handler(level: int) -> None:
    """Add a RotatingFileHandler to the root logger.

    Writes human-readable log lines to logs/giljo_mcp.log with size-based
    rotation (10MB per file, 5 backups = 60MB max). Uses size-based rotation
    instead of time-based to avoid Windows file-locking issues (WinError 32)
    where TimedRotatingFileHandler cannot rename open files.
    """
    # Determine project root (3 levels up from this file: src/giljo_mcp/logging/)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "giljo_mcp.log"

    handler = _SafeRotatingFileHandler(
        filename=str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)


def configure_logging(
    environment: Optional[str] = None,
    log_level: str = "INFO",
    force_json: bool = False,
) -> None:
    """
    Configure structlog processing pipeline for the application.

    Structlog acts as a log processor/formatter on top of stdlib logging.
    Individual modules should use ``logging.getLogger(__name__)`` to obtain
    their loggers.

    Args:
        environment: "production" for JSON, anything else for console (default: from ENVIRONMENT env var)
        log_level: Logging level (default: INFO)
        force_json: Force JSON output regardless of environment
    """
    if _LoggingState.configured:
        return

    # Determine environment
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # Determine log level
    level_str = os.getenv("LOG_LEVEL", log_level).upper()
    level = getattr(logging, level_str, logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Add file handler for persistent logging (daily rotation)
    _setup_file_handler(level)

    # Shared processors for all configurations
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    # Production: JSON output
    if environment == "production" or force_json:
        processors = [*shared_processors, structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    # Development: Console output with colors
    else:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _LoggingState.configured = True


# Initialize logging configuration on import (lazy initialization)
def _init_logging() -> None:
    """Initialize logging configuration on module import"""
    if not _LoggingState.configured:
        configure_logging()


# Auto-configure on import for seamless backward compatibility
_init_logging()
