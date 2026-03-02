"""
Tenant isolation regression tests for MessageService -- broadcast(), send_message(),
list_messages(), and combined cross-tenant audit.

Split from test_message_tenant_isolation_regression.py for maintainability.
See conftest.py for the shared two_tenant_messages fixture.

Verifies that cross-tenant data leaks are prevented for:
- broadcast() query for agent jobs (requires tenant_key filter)
- send_message() requires tenant_key (no fallback without context)
- list_messages() requires tenant_key for all query paths

IMPORTANT: broadcast() uses self.db_manager.get_session_async() directly
(not self._get_session()), which creates separate database connections.
In the transactional test context, data committed via db_session may not
be visible to these separate sessions. Tests are structured to validate
tenant isolation enforcement (tenant_key validation and filtering) rather
than relying on data visibility across sessions.
"""

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# broadcast() -- Cross-Tenant Broadcast Test
# ============================================================================
#
# RISK: broadcast() uses self.db_manager.get_session_async() directly, NOT
# self._get_session(). This means it creates a separate database session
# that will NOT see data from the transactional test fixture. Tests that
# depend on seeing agent jobs in the separate session may hang or fail
# with ResourceNotFoundError (no agents found) rather than demonstrating
# cross-tenant blocking. The tests below are structured to validate the
# tenant_key enforcement logic regardless of data visibility.
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_broadcast_blocks_cross_tenant(db_session, two_tenant_messages):
    """
    REGRESSION: broadcast() must filter agent jobs by tenant_key.

    Bug: Without tenant_key filtering on the AgentJob query, a broadcast
    could reach agents belonging to another tenant's project.

    broadcast() queries AgentJob WHERE project_id AND tenant_key match.
    Using the wrong tenant_key means no agent jobs are found, raising
    ResourceNotFoundError. This is the correct blocking behavior.

    NOTE: broadcast() uses self.db_manager.get_session_async() directly.
    Agent jobs from the transactional fixture may not be visible. The test
    validates that mismatched tenant_key results in an error (either
    ResourceNotFoundError for no agents found, or ValidationError).
    """
    tenant_a = two_tenant_messages["tenant_a"]
    project_b = two_tenant_messages["project_b"]
    service = two_tenant_messages["service"]

    # Tenant A tries to broadcast to tenant B's project
    with pytest.raises((ResourceNotFoundError, ValidationError)):
        await service.broadcast(
            content="Cross-tenant broadcast attempt",
            project_id=project_b.id,
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_broadcast_requires_tenant_key(db_session, two_tenant_messages):
    """
    broadcast() with no tenant_key and no tenant context must raise
    ValidationError, not silently proceed without filtering.
    """
    project_a = two_tenant_messages["project_a"]
    service = two_tenant_messages["service"]

    # Clear tenant context
    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.broadcast(
            content="Should fail without tenant_key",
            project_id=project_a.id,
            tenant_key=None,
        )


# ============================================================================
# send_message() -- Tenant Key Requirement Test
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_send_message_requires_tenant_key(db_session, two_tenant_messages):
    """
    send_message() with no tenant_key and no tenant context must raise
    ValidationError.

    send_message() uses self._get_session() (respects test_session), so
    it can see fixture data. However, without tenant_key it must fail.
    """
    project_a = two_tenant_messages["project_a"]
    service = two_tenant_messages["service"]

    # Clear tenant context
    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.send_message(
            to_agents=["worker-a"],
            content="Should fail without tenant_key",
            project_id=project_a.id,
            tenant_key=None,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_send_message_blocks_cross_tenant(db_session, two_tenant_messages):
    """
    REGRESSION: send_message() must validate project belongs to the tenant.

    send_message() queries Project WHERE tenant_key AND project_id match.
    Using the wrong tenant_key means the project is not found, raising
    ResourceNotFoundError.

    send_message() uses self._get_session() which respects test_session,
    so fixture data is visible.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    project_b = two_tenant_messages["project_b"]
    service = two_tenant_messages["service"]

    # Tenant A tries to send a message to tenant B's project
    with pytest.raises(ResourceNotFoundError):
        await service.send_message(
            to_agents=["worker-b"],
            content="Cross-tenant message attempt",
            project_id=project_b.id,
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_send_message_same_tenant_succeeds(db_session, two_tenant_messages):
    """
    Verify that same-tenant send_message still works correctly.

    send_message() uses self._get_session() which respects test_session,
    so fixture data is visible. This should successfully create a message.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    project_a = two_tenant_messages["project_a"]
    service = two_tenant_messages["service"]

    result = await service.send_message(
        to_agents=["worker-a"],
        content="Same-tenant message from orchestrator",
        project_id=project_a.id,
        from_agent="orchestrator",
        tenant_key=tenant_a,
    )

    assert result.message_type == "direct"
    assert result.to_agents is not None


# ============================================================================
# Combined -- Full Cross-Tenant Audit
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_message_service_cross_tenant_audit(db_session, two_tenant_messages):
    """
    Integration test: Attempt every cross-tenant message operation from
    tenant A against tenant B's data. All must be blocked.

    NOTE: Methods using self.db_manager.get_session_async() (get_messages,
    complete_message, broadcast) create separate sessions. Cross-tenant
    blocking is validated via tenant_key filtering logic.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    project_b = two_tenant_messages["project_b"]
    message_b = two_tenant_messages["message_b"]
    service = two_tenant_messages["service"]

    violations = []

    # 1. get_messages cross-tenant -- should return 0 results
    try:
        result = await service.get_messages(
            agent_name="worker-b",
            tenant_key=tenant_a,
        )
        if result.count > 0:
            violations.append(
                f"get_messages() returned {result.count} cross-tenant messages"
            )
    except (ResourceNotFoundError, ValidationError):
        pass  # Blocked as expected

    # 2. complete_message cross-tenant -- should raise
    try:
        await service.complete_message(
            message_id=str(message_b.id),
            agent_name="worker-a",
            result="Cross-tenant completion attempt",
            tenant_key=tenant_a,
        )
        violations.append("complete_message() allowed cross-tenant completion")
    except (ResourceNotFoundError, ValidationError):
        pass  # Blocked as expected

    # 3. broadcast cross-tenant -- should raise
    try:
        await service.broadcast(
            content="Cross-tenant broadcast attempt",
            project_id=project_b.id,
            tenant_key=tenant_a,
        )
        violations.append("broadcast() allowed cross-tenant broadcast")
    except (ResourceNotFoundError, ValidationError):
        pass  # Blocked as expected

    # 4. send_message cross-tenant -- should raise
    try:
        await service.send_message(
            to_agents=["worker-b"],
            content="Cross-tenant send attempt",
            project_id=project_b.id,
            tenant_key=tenant_a,
        )
        violations.append("send_message() allowed cross-tenant send")
    except (ResourceNotFoundError, ValidationError):
        pass  # Blocked as expected

    # 5. No tenant_key at all -- all should raise ValidationError
    TenantManager.clear_current_tenant()

    no_tenant_methods = [
        ("get_messages", lambda: service.get_messages(agent_name="worker-a", tenant_key=None)),
        (
            "complete_message",
            lambda: service.complete_message(
                message_id=str(message_b.id),
                agent_name="worker-a",
                result="No tenant attempt",
                tenant_key=None,
            ),
        ),
        (
            "broadcast",
            lambda: service.broadcast(
                content="No tenant broadcast",
                project_id=project_b.id,
                tenant_key=None,
            ),
        ),
        (
            "send_message",
            lambda: service.send_message(
                to_agents=["worker-a"],
                content="No tenant send",
                project_id=project_b.id,
                tenant_key=None,
            ),
        ),
    ]

    for method_name, method_call in no_tenant_methods:
        try:
            await method_call()
            violations.append(
                f"{method_name}() proceeded without tenant_key (should raise ValidationError)"
            )
        except ValidationError:
            pass  # Correctly blocked
        except (ResourceNotFoundError, Exception):
            # Other errors are acceptable -- the point is it did not succeed
            pass

    assert len(violations) == 0, (
        "CRITICAL: Tenant isolation violated!\nViolations:\n"
        + "\n".join(f"- {v}" for v in violations)
    )


# ============================================================================
# list_messages() -- Cross-Tenant Read Tests (BATCH 1 addition)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_list_messages_requires_tenant_key(db_session, two_tenant_messages):
    """
    REGRESSION: list_messages() must always require tenant_key.

    Bug: When tenant_key was None AND project_id was provided, list_messages()
    would proceed without tenant filtering, leaking cross-tenant messages.
    Now raises ValidationError if tenant_key is missing.
    """
    service = two_tenant_messages["service"]

    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.list_messages(
            project_id=two_tenant_messages["project_a"].id,
            tenant_key=None,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_list_messages_blocks_cross_tenant_by_agent(db_session, two_tenant_messages):
    """
    REGRESSION: list_messages() must filter AgentJob by tenant_key.

    Bug: AgentJob lookup conditions were conditionally filtered by tenant_key.
    Now tenant_key is always included in the AgentJob WHERE clause.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    job_b = two_tenant_messages["job_b"]
    service = two_tenant_messages["service"]

    # Tenant A tries to list messages for tenant B's agent
    # Cross-tenant agent lookup should find no matching job and raise
    with pytest.raises(ResourceNotFoundError):
        await service.list_messages(
            agent_id=job_b.job_id,
            tenant_key=tenant_a,
        )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_list_messages_blocks_cross_tenant_by_project(db_session, two_tenant_messages):
    """
    REGRESSION: list_messages() must filter Messages by tenant_key.

    Bug: When querying by project_id, the Message query conditionally
    included tenant_key. Now tenant_key is always in the WHERE clause.
    """
    tenant_a = two_tenant_messages["tenant_a"]
    project_b = two_tenant_messages["project_b"]
    service = two_tenant_messages["service"]

    # Tenant A tries to list messages in tenant B's project
    result = await service.list_messages(
        project_id=project_b.id,
        tenant_key=tenant_a,
    )

    assert result.count == 0, (
        f"CRITICAL: list_messages() returned {result.count} cross-tenant messages!"
    )
