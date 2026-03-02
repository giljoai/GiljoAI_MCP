"""
Setup compatibility endpoint module.

Provides `check_first_run` for tests and tooling that still import
`api.endpoints.setup`. The implementation uses the current unified
setup state mechanism (SetupStateManager) instead of legacy logic.

This module is intentionally small and stable so it can be maintained
independently of the broader setup/installer flows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import inspect

from fastapi import APIRouter, HTTPException, Request

from src.giljo_mcp.setup.state_manager import SetupStateManager


logger = logging.getLogger(__name__)

router = APIRouter()


async def check_first_run(request: Request) -> Dict[str, Any]:
    """
    Determine whether this instance is in a first-run state.

    This mirrors the expectations of `tests/unit/test_first_run_detection.py`:
    - It is a coroutine accepting a FastAPI `Request`.
    - It returns a simple dict with a `first_run` boolean.
    - It uses a database session pulled from `request.app.state.api_state.db_manager`
      when available, but falls back to SetupStateManager for robustness.
    """
    # Prefer DB-based detection when a db_manager is wired on api_state.
    try:
        api_state = getattr(request.app.state, "api_state", None)
        db_manager = getattr(api_state, "db_manager", None)
        if db_manager is not None:
            # Handover 1011 Phase 3: Migrated to ConfigurationRepository
            from sqlalchemy.ext.asyncio import AsyncSession

            from src.giljo_mcp.repositories import ConfigurationRepository

            async def _has_admin_user() -> bool:
                """Return True if at least one admin user exists."""
                session_ctx = db_manager.get_session_async()
                repo = ConfigurationRepository(db_manager)

                # Support both async context managers and async generators
                if hasattr(session_ctx, "__aenter__"):
                    async with session_ctx as session:  # type: AsyncSession
                        return await repo.check_admin_user_exists(session)
                elif inspect.isasyncgen(session_ctx):
                    async for session in session_ctx:  # type: AsyncSession
                        return await repo.check_admin_user_exists(session)
                    return False
                else:
                    logger.warning("db_manager.get_session_async returned unsupported type in check_first_run")
                    return False

            admin_exists = await _has_admin_user()
            return {"first_run": not admin_exists}

            # ORIGINAL QUERY (for rollback):
            # from sqlalchemy import select
            # from src.giljo_mcp.models import User
            # result = await session.execute(select(User).where(User.role == "admin").limit(1))
            # return result.scalar_one_or_none() is not None

    except Exception as e:  # pragma: no cover - defensive logging
        logger.warning("DB-based first-run detection failed in check_first_run: %s", e)
        # Safe default on DB error: treat as not first run to avoid blocking login
        return {"first_run": False}

    # Fallback to SetupStateManager (same logic as startup.py) when no db_manager is available
    try:
        state_manager = SetupStateManager.get_instance(tenant_key="default")
        state = state_manager.get_state()
        is_first_run = not state.get("completed", False)
        return {"first_run": is_first_run}
    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        logger.error("SetupStateManager-based first-run detection failed: %s", e)
        # Conservative fallback for production: treat as NOT first run to avoid blocking login.
        return {"first_run": False}


@router.get("/first-run")
async def first_run_status(request: Request) -> Dict[str, Any]:
    """
    HTTP wrapper around `check_first_run` for API usage.

    Exposes a minimal endpoint so that `/api/setup/first-run` can be called
    if needed, without reintroducing the complex legacy setup wizard flows.
    """
    try:
        return await check_first_run(request)
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Failed to determine first-run status: %s", e)
        raise HTTPException(status_code=500, detail="Failed to determine first-run status") from e
