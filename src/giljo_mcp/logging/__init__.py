"""
Structured Logging with Error Codes

Production-grade structured logging using structlog with:
- JSON output for production (machine-parseable)
- Console output for development (human-readable)
- Backward compatibility with standard Python logging
- Error code support for quick diagnosis

Usage:
    from giljo_mcp.logging import get_logger, ErrorCode

    logger = get_logger(__name__)

    # Structured logging with context
    logger.info(
        "user_authenticated",
        user_id=user.id,
        ip_address=request.client.host,
        tenant_key=user.tenant_key
    )

    # Error logging with error code
    logger.error(
        "authentication_failed",
        error_code=ErrorCode.AUTH_INVALID_CREDENTIALS.value,
        user_id=user_id,
        reason="invalid_password"
    )

    # Backward compatible (no code changes needed)
    logger.info("Processing request...")  # Still works!

Environment Variables:
    ENVIRONMENT: Set to "production" for JSON output, anything else for console
    LOG_LEVEL: debug, info, warning, error, critical (default: info)
"""

import logging
import os
import sys
from typing import Optional

import structlog
from structlog.types import FilteringBoundLogger

from .error_codes import ErrorCode, get_error_description


# Re-export for convenience
__all__ = ["ErrorCode", "configure_logging", "get_colored_logger", "get_error_description", "get_logger"]


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
    Configure structlog for the application.

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

    # Configure standard logging (for backward compatibility)
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
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    # Development: Console output with colors
    else:
        processors = shared_processors + [
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


def get_logger(name: Optional[str] = None) -> FilteringBoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__), optional

    Returns:
        Structlog logger with error code support

    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id="123", ip="192.168.1.1")
        logger.error(
            "auth_failed",
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS.value,
            user_id="123"
        )
    """
    # Ensure logging is configured
    if not _LoggingState.configured:
        configure_logging()

    # Get structlog logger
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


def get_colored_logger(name: Optional[str] = None) -> FilteringBoundLogger:
    """
    Get a colored console logger (alias for backward compatibility).

    This is an alias for get_logger() to maintain compatibility with
    existing code that uses get_colored_logger().

    Args:
        name: Logger name (typically __name__), optional

    Returns:
        Structlog logger instance
    """
    return get_logger(name)


# Initialize logging configuration on import (lazy initialization)
# This ensures backward compatibility - existing code just works
def _init_logging() -> None:
    """Initialize logging configuration on module import"""
    if not _LoggingState.configured:
        configure_logging()


# Auto-configure on import for seamless backward compatibility
_init_logging()
