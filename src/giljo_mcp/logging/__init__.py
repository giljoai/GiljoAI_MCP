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
from typing import Optional

import structlog

from .error_codes import ErrorCode, get_error_description


# Re-export for convenience
__all__ = ["ErrorCode", "configure_logging", "get_error_description"]


# Module-level configuration state
class _LoggingState:
    """Configuration state holder to avoid global statement."""

    configured = False


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
