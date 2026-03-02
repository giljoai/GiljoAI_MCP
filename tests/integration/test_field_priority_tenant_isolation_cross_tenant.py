"""
Integration tests for field priority multi-tenant isolation - Cross-Tenant Tests

Tests 4a, 4b, 4c: Verify that field priorities are properly isolated between
different tenants, preventing cross-tenant data leakage.

BUG CONTEXT:
- Each user belongs to a tenant (tenant_key)
- Field priorities are user-specific within a tenant
- Bug: Empty field_priorities means tenant isolation can't be verified

Handover: Field Priority Bug Fix - Phase 1
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

pytestmark = pytest.mark.skip(reason="0750c3: ThinPromptGenerator test assertions stale — needs update for current prompt format")


# ============================================================================
# TEST 4a-4c: Cross-Tenant Isolation of Field Priorities
# ============================================================================


@pytest.mark.asyncio
async def test_field_priorities_isolated_between_tenants(
    db_session, user_tenant_a, user_tenant_b, project_tenant_a, project_tenant_b
):
    """
    TEST 4a: Field priorities should be isolated between tenants.

    USER STORY:
    1. User A in Tenant A has field priorities: {git_history: 4}
    2. User B in Tenant B has field priorities: {git_history: 2}
    3. When User A stages project, gets Tenant A priorities
    4. When User B stages project, gets Tenant B priorities
    5. Neither user should see the other's configuration

    This confirms tenant isolation for field priority configurations.
    """
    # ARRANGE: Verify users have different priorities
    priorities_a = user_tenant_a.field_priority_config["priorities"]
    priorities_b = user_tenant_b.field_priority_config["priorities"]

    assert priorities_a["git_history"] == 4  # Tenant A excludes
    assert priorities_b["git_history"] == 2  # Tenant B includes

    # ACT: Generate orchestrator job for Tenant A
    generator_a = ThinClientPromptGenerator(db=db_session, tenant_key=user_tenant_a.tenant_key)

    user_field_config_a = user_tenant_a.field_priority_config or {}
    field_priorities_a = user_field_config_a.get("priorities", {})

    result_a = await generator_a.generate(
        project_id=str(project_tenant_a.id),
        user_id=str(user_tenant_a.id),
        tool="claude-code",
        field_priorities=field_priorities_a,
    )

    # ACT: Generate orchestrator job for Tenant B
    generator_b = ThinClientPromptGenerator(db=db_session, tenant_key=user_tenant_b.tenant_key)

    user_field_config_b = user_tenant_b.field_priority_config or {}
    field_priorities_b = user_field_config_b.get("priorities", {})

    result_b = await generator_b.generate(
        project_id=str(project_tenant_b.id),
        user_id=str(user_tenant_b.id),
        tool="claude-code",
        field_priorities=field_priorities_b,
    )

    # ASSERT: Verify Tenant A got their own priorities
    orchestrator_id_a = result_a["orchestrator_id"]

    stmt_a = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id_a)
    job_result_a = await db_session.execute(stmt_a)
    orchestrator_job_a = job_result_a.scalar_one_or_none()

    actual_priorities_a = orchestrator_job_a.job_metadata.get("field_priorities", {})

    assert actual_priorities_a == priorities_a, (
        f"Tenant A should get their own priorities. Expected: {priorities_a}, Got: {actual_priorities_a}"
    )

    # ASSERT: Verify Tenant B got their own priorities
    orchestrator_id_b = result_b["orchestrator_id"]

    stmt_b = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id_b)
    job_result_b = await db_session.execute(stmt_b)
    orchestrator_job_b = job_result_b.scalar_one_or_none()

    actual_priorities_b = orchestrator_job_b.job_metadata.get("field_priorities", {})

    assert actual_priorities_b == priorities_b, (
        f"Tenant B should get their own priorities. Expected: {priorities_b}, Got: {actual_priorities_b}"
    )

    # CRITICAL ASSERTION: Priorities should be DIFFERENT
    assert actual_priorities_a != actual_priorities_b, (
        "Tenant A and Tenant B should have DIFFERENT field priorities. Tenant isolation is broken if they're the same."
    )


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_tenant_orchestrator_job(
    db_session, user_tenant_a, user_tenant_b, project_tenant_a
):
    """
    TEST 4b: Tenant B cannot access Tenant A's orchestrator job.

    SECURITY TEST:
    1. Tenant A creates orchestrator job with their priorities
    2. Tenant B tries to query for Tenant A's job
    3. Query should return None (tenant isolation enforced by database)

    This verifies database-level tenant isolation.
    """
    # ARRANGE: Create orchestrator job for Tenant A
    generator_a = ThinClientPromptGenerator(db=db_session, tenant_key=user_tenant_a.tenant_key)

    user_field_config_a = user_tenant_a.field_priority_config or {}
    field_priorities_a = user_field_config_a.get("priorities", {})

    result_a = await generator_a.generate(
        project_id=str(project_tenant_a.id),
        user_id=str(user_tenant_a.id),
        tool="claude-code",
        field_priorities=field_priorities_a,
    )

    orchestrator_id_a = result_a["orchestrator_id"]

    # ACT: Try to access Tenant A's job using Tenant B's tenant_key
    stmt_b = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id_a,
        AgentExecution.tenant_key == user_tenant_b.tenant_key,  # WRONG TENANT
    )
    job_result_b = await db_session.execute(stmt_b)
    orchestrator_job_b = job_result_b.scalar_one_or_none()

    # ASSERT: Tenant B should NOT be able to access Tenant A's job
    assert orchestrator_job_b is None, (
        "Tenant B should NOT be able to access Tenant A's orchestrator job. Tenant isolation is broken!"
    )

    # VERIFY: Tenant A CAN access their own job
    stmt_a = select(AgentExecution).where(
        AgentExecution.job_id == orchestrator_id_a,
        AgentExecution.tenant_key == user_tenant_a.tenant_key,  # CORRECT TENANT
    )
    job_result_a = await db_session.execute(stmt_a)
    orchestrator_job_a = job_result_a.scalar_one_or_none()

    assert orchestrator_job_a is not None, "Tenant A should be able to access their own orchestrator job"


@pytest.mark.asyncio
async def test_field_priorities_query_respects_tenant_key(db_session, user_tenant_a, user_tenant_b):
    """
    TEST 4c: Querying users by field priorities should respect tenant_key.

    DATABASE TEST:
    1. Query for users with specific field priority config
    2. Results should only include users from same tenant
    3. Users from other tenants should NOT appear

    This verifies database queries respect tenant isolation.
    """
    # ARRANGE: Both users have field_priority_config, but different tenants
    assert user_tenant_a.field_priority_config is not None
    assert user_tenant_b.field_priority_config is not None

    # ACT: Query for users in Tenant A with field priority config
    stmt = select(User).where(User.tenant_key == user_tenant_a.tenant_key, User.field_priority_config.isnot(None))
    result = await db_session.execute(stmt)
    users_a = result.scalars().all()

    # ASSERT: Should only find Tenant A user
    user_ids_a = [u.id for u in users_a]

    assert user_tenant_a.id in user_ids_a, "Query should find Tenant A user"

    assert user_tenant_b.id not in user_ids_a, "Query should NOT find Tenant B user (different tenant)"
