# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared tenant-scoped session context managers for service classes.

BE-8000d (waste-fix 8000 series, item d / dup-1): the injected-test-session
``_get_session`` asynccontextmanager block was copy-pasted across ~30 service
files and had drifted into several subtly different behaviours. These three
helpers capture the three *distinct* behaviour contracts that were actually in
use; each service delegates to the one matching its prior behaviour EXACTLY, so
this is a pure de-duplication with no behaviour change.

The three contracts differ only in how tenant context is applied:

- ``optional_tenant_session`` -- apply ``tenant_session_context`` on an injected
  test session *only when a key is present* (bare-yield otherwise); a fresh
  session gets the key via the manager's own ``tenant_key`` argument.
- ``tenant_scoped_session`` -- *always* apply ``tenant_session_context`` on an
  injected test session; a fresh session gets the key via the manager argument.
- ``tenant_context_session`` -- apply ``tenant_session_context`` on *both*
  paths (the fresh session is obtained WITHOUT a key, then wrapped), which also
  pushes/pops ``TenantManager`` current-tenant state around the yield.

Genuine one-offs are intentionally NOT routed here because their semantics
differ: the auth family (auth_service / mission_orchestration_service /
notification_service / sequence_chain_context) sets ``session.info["tenant_key"]``
directly without ``tenant_session_context``; job_completion_service double-applies
the key on its fallback path; tenant_configuration_service and tool_accessor
yield a tenant-agnostic session (bare yield, no key).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from giljo_mcp.database import tenant_session_context


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from giljo_mcp.database import DatabaseManager


@asynccontextmanager
async def optional_tenant_session(
    db_manager: DatabaseManager,
    tenant_key: str | None,
    test_session: AsyncSession | None,
) -> AsyncIterator[AsyncSession]:
    """Yield a session, applying tenant context on the test session only when a key is present.

    Injected test session -> wrap in ``tenant_session_context`` iff ``tenant_key``
    is truthy, else yield it untouched. No injected session -> a fresh session
    from the manager, which applies ``tenant_key`` itself.
    """
    if test_session is not None:
        if tenant_key:
            with tenant_session_context(test_session, tenant_key):
                yield test_session
        else:
            yield test_session
    else:
        async with db_manager.get_session_async(tenant_key=tenant_key) as session:
            yield session


@asynccontextmanager
async def tenant_scoped_session(
    db_manager: DatabaseManager,
    tenant_key: str | None,
    test_session: AsyncSession | None,
) -> AsyncIterator[AsyncSession]:
    """Yield a session, always applying tenant context on the injected test session.

    Injected test session -> always wrap in ``tenant_session_context``. No
    injected session -> a fresh session from the manager, which applies
    ``tenant_key`` itself.
    """
    if test_session is not None:
        with tenant_session_context(test_session, tenant_key):
            yield test_session
    else:
        async with db_manager.get_session_async(tenant_key=tenant_key) as session:
            yield session


@asynccontextmanager
async def tenant_context_session(
    db_manager: DatabaseManager,
    tenant_key: str | None,
    test_session: AsyncSession | None,
) -> AsyncIterator[AsyncSession]:
    """Yield a session, applying ``tenant_session_context`` on both paths.

    Injected test session -> wrap in ``tenant_session_context``. No injected
    session -> a fresh session obtained WITHOUT a key, then wrapped in
    ``tenant_session_context`` (which also pushes/pops ``TenantManager``
    current-tenant state around the yield).
    """
    if test_session is not None:
        with tenant_session_context(test_session, tenant_key):
            yield test_session
    else:
        async with db_manager.get_session_async() as session:
            with tenant_session_context(session, tenant_key):
                yield session
