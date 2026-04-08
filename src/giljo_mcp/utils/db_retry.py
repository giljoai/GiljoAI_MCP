# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Shared deadlock retry utility for PostgreSQL concurrent operations.

Provides a reusable async retry mechanism for database operations that may
encounter PostgreSQL deadlocks (SQLSTATE 40P01) during concurrent access.

Used by MessageService for counter updates on both send and receive paths.
"""

import asyncio
import logging
import random
from collections.abc import Coroutine
from typing import Any, Callable

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.exceptions import RetryExhaustedError


logger = logging.getLogger(__name__)

# PostgreSQL deadlock SQLSTATE
PG_DEADLOCK_CODE = "40P01"

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 0.1  # seconds
DEFAULT_JITTER_MAX = 0.05  # seconds


def _is_deadlock(err: OperationalError) -> bool:
    """Check if an OperationalError is a PostgreSQL deadlock (SQLSTATE 40P01)."""
    return getattr(getattr(err, "orig", None), "pgcode", None) == PG_DEADLOCK_CODE


async def _attempt_operation(
    session: AsyncSession,
    operation: Callable[[], Coroutine[Any, Any, Any]],
) -> tuple[bool, Any]:
    """Execute operation once, handling deadlock detection.

    Returns:
        (success, result) tuple. On deadlock, rolls back and returns (False, error).
        On success, returns (True, result). Non-deadlock errors propagate immediately.
    """
    try:
        result = await operation()
    except OperationalError as db_err:
        if not _is_deadlock(db_err):
            raise
        await session.rollback()
        return False, db_err
    return True, result


async def with_deadlock_retry(
    session: AsyncSession,
    operation: Callable[[], Coroutine[Any, Any, Any]],
    *,
    operation_name: str = "db_operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    jitter_max: float = DEFAULT_JITTER_MAX,
    context: dict[str, Any] | None = None,
) -> Any:
    """
    Execute an async database operation with deadlock retry and exponential backoff.

    On PostgreSQL deadlock (SQLSTATE 40P01), rolls back the session and retries
    with exponential backoff plus jitter. Non-deadlock OperationalErrors propagate
    immediately without retry.

    Args:
        session: Active SQLAlchemy async session (rolled back on deadlock).
        operation: Async callable that performs the database work. Called with no
                   arguments; close over any state it needs.
        operation_name: Human-readable name for log messages.
        max_retries: Maximum number of attempts before raising RetryExhaustedError.
        base_delay: Base delay in seconds for exponential backoff.
        jitter_max: Maximum random jitter added to each delay.
        context: Optional dict included in RetryExhaustedError for diagnostics.

    Returns:
        Whatever ``operation`` returns on success.

    Raises:
        RetryExhaustedError: After ``max_retries`` consecutive deadlocks.
        OperationalError: For non-deadlock database errors (propagated immediately).
    """
    if max_retries < 1:
        raise ValueError(f"max_retries must be >= 1, got {max_retries}")
    if base_delay < 0:
        raise ValueError(f"base_delay must be >= 0, got {base_delay}")

    last_error: OperationalError | None = None

    for attempt in range(max_retries):
        success, result = await _attempt_operation(session, operation)

        if success:
            return result

        last_error = result

        if attempt < max_retries - 1:
            backoff = (base_delay * (2**attempt)) + random.uniform(0, jitter_max)
            logger.warning(
                "[DEADLOCK] %s deadlock on attempt %d/%d, retrying in %.3fs",
                operation_name,
                attempt + 1,
                max_retries,
                backoff,
            )
            await asyncio.sleep(backoff)

    logger.error(
        "[DEADLOCK] %s failed after %d retries",
        operation_name,
        max_retries,
        exc_info=last_error,
    )
    raise RetryExhaustedError(
        message=f"Deadlock retry exhausted after {max_retries} attempts",
        context={"operation": operation_name, **(context or {})},
    ) from last_error
