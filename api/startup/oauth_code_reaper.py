# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""OAuth expired-code reaper (BE-8000i).

Extracted into its own module rather than inlined in ``background_tasks.py``,
which was already at the 800-line CI guardrail (same rationale as
``tenant_guard.py``'s split from ``database.py``, BE-6063c).

``OAuthService.cleanup_expired_codes`` existed and was correct but had ZERO
production callers -- ``exchange_code_for_token`` only flips ``used=True`` on
a code (never deletes it), and ``generate_authorization_code`` inserts a new
row per ``/authorize`` call, so ``oauth_authorization_codes`` grew unbounded.
Runs daily -- this table churns far slower than MCP sessions (6h cadence).
"""

import asyncio
import logging

from api.app_state import APIState
from api.startup.metrics_flushers import log_task_death


logger = logging.getLogger(__name__)


async def cleanup_expired_oauth_codes_task(state: APIState):
    """Background task: purge expired/used OAuth authorization codes."""
    from giljo_mcp.services.oauth_service import OAuthService

    while True:
        await asyncio.sleep(86400)  # 24 hours
        if not state.db_manager:
            continue
        try:
            async with state.db_manager.get_session_async() as session:
                service = OAuthService(db_session=session)
                removed = await service.cleanup_expired_codes()
            if removed:
                logger.info("OAuth code cleanup: %d expired/used code(s) removed", removed)
            else:
                logger.debug("OAuth code cleanup: nothing to remove")
        except asyncio.CancelledError:
            raise
        # BE-9053: catch-log-continue at the loop boundary (SaaS reaper pattern).
        # The old narrow tuple let one unexpected exception kill the loop
        # permanently and silently.
        except Exception as e:
            logger.error("Error during OAuth code cleanup: %s", e, exc_info=True)


def start_oauth_code_cleanup_task(state: APIState) -> None:
    """Register the reaper as an asyncio task (mirrors every sibling reaper's
    start-up try/except in ``background_tasks.py::init_background_tasks()``)."""
    try:
        logger.info("Starting OAuth authorization code cleanup task...")
        task = asyncio.create_task(cleanup_expired_oauth_codes_task(state), name="oauth-code-cleanup")
        task.add_done_callback(log_task_death)
        state.oauth_code_cleanup_task = task
        logger.info("OAuth authorization code cleanup task started (runs daily)")
    except Exception as e:  # Broad catch: background task startup, non-fatal
        logger.error(f"Failed to start OAuth authorization code cleanup task: {e}", exc_info=True)
