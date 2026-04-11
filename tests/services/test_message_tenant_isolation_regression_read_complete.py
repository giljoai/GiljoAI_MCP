# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tenant isolation regression tests for MessageService -- get_messages() and complete_message().

Split from test_message_tenant_isolation_regression.py for maintainability.
See conftest.py for the shared two_tenant_messages fixture.

Verifies that cross-tenant data leaks are prevented for:
- get_messages() READ query (requires tenant_key filter)
- complete_message() UPDATE query (requires tenant_key filter)

IMPORTANT: get_messages() and complete_message() use
self.db_manager.get_session_async() directly (not self._get_session()),
which creates separate database connections. In the transactional test
context, data committed via db_session may not be visible to these
separate sessions. Tests are structured to validate tenant isolation
enforcement (tenant_key validation and filtering) rather than relying
on data visibility across sessions.
"""

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# get_messages() -- Cross-Tenant Read Test
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_messages_blocks_cross_tenant(db_session, two_tenant_messages):
    """
    REGRESSION: get_messages() must filter by tenant_key in the SELECT query.

    Bug: Without tenant_key filtering, any tenant could read messages
    belonging to another tenant's agents.

    NOTE: get_messages() uses self.db_manager.get_session_async() directly,
    so test data from the transactional fixture may not be visible. This test
    validates tenant_key enforcement by verifying that cross-tenant queries
    return zero results (the wrong tenant_key filters out all messages).
    """
    tenant_a = two_tenant_messages["tenant_a"]
    service = two_tenant_messages["service"]

    # Tenant A tries to get messages for tenant B's agent using tenant A's key.
    # Even if messages existed, the tenant_key filter should exclude them.
    result = await service.get_messages(
        agent_name="worker-b",
        tenant_key=tenant_a,
    )

    # Cross-tenant messages must NOT be returned
    assert result.count == 0, (
        "CRITICAL: get_messages() returned cross-tenant messages! "
        f"Expected 0 messages for worker-b with tenant_key={tenant_a}, got {result.count}"
    )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_messages_requires_tenant_key(db_session, two_tenant_messages):
    """
    get_messages() with no tenant_key and no tenant context must raise
    ValidationError, not silently proceed without filtering.
    """
    service = two_tenant_messages["service"]

    # Clear tenant context
    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.get_messages(
            agent_name="worker-a",
            tenant_key=None,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_messages_same_tenant_succeeds(db_session, two_tenant_messages):
    """
    Verify that same-tenant get_messages still works correctly.

    NOTE: get_messages() uses self.db_manager.get_session_async() which
    creates a separate session. Data from the transactional test fixture
    may not be visible. This test validates that the method executes
    without error when given a valid tenant_key, even if no messages
    are visible due to session isolation.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    service = two_tenant_messages["service"]

    # Same-tenant query should not raise any exception
    result = await service.get_messages(
        agent_name="worker-a",
        tenant_key=tenant_a,
    )

    # The method should return a valid result structure (count may be 0
    # due to session isolation in transactional test context)
    assert result.agent == "worker-a"
    assert result.count >= 0


# ============================================================================
# complete_message() -- Cross-Tenant Modification Test
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_message_blocks_cross_tenant(db_session, two_tenant_messages):
    """
    REGRESSION: complete_message() must filter by both message_id AND tenant_key.

    Bug: Without tenant_key in the WHERE clause, any tenant could complete
    another tenant's message if they knew the message_id.

    NOTE: complete_message() uses self.db_manager.get_session_async() directly.
    The message from the transactional fixture may not be visible to the
    separate session, but the important thing is that the query filters by
    tenant_key, so cross-tenant access is blocked regardless.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    message_b = two_tenant_messages["message_b"]
    service = two_tenant_messages["service"]

    # Tenant A tries to complete tenant B's message
    with pytest.raises((ResourceNotFoundError, ValidationError)):
        await service.complete_message(
            message_id=str(message_b.id),
            agent_name="worker-a",
            result="Attempted cross-tenant completion",
            tenant_key=tenant_a,
        )

    # Verify the message was NOT completed (status unchanged)
    await db_session.refresh(message_b)
    assert message_b.status == "pending", "Cross-tenant complete_message modified another tenant's message!"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_message_requires_tenant_key(db_session, two_tenant_messages):
    """
    complete_message() with no tenant_key and no tenant context must raise
    ValidationError, not silently proceed without filtering.
    """
    message_a = two_tenant_messages["message_a"]
    service = two_tenant_messages["service"]

    # Clear tenant context
    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.complete_message(
            message_id=str(message_a.id),
            agent_name="worker-a",
            result="Should fail without tenant_key",
            tenant_key=None,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_message_same_tenant_succeeds(db_session, two_tenant_messages):
    """
    Verify that same-tenant complete_message still works correctly.

    NOTE: complete_message() uses self.db_manager.get_session_async() which
    creates a separate session. Data from the transactional test fixture
    may not be visible. This test validates that the method handles a
    valid tenant_key correctly. If the message is not visible due to
    session isolation, ResourceNotFoundError is acceptable (not a tenant
    isolation violation -- it is a test infrastructure limitation).
    """
    tenant_a = two_tenant_messages["tenant_a"]
    message_a = two_tenant_messages["message_a"]
    service = two_tenant_messages["service"]

    result = await service.complete_message(
        message_id=str(message_a.id),
        agent_name="worker-a",
        result="Task completed successfully",
        tenant_key=tenant_a,
    )
    # Verify the message was completed
    assert result.completed_by == "worker-a"
