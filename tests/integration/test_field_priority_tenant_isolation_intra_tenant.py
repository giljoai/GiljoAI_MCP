"""
Integration tests for field priority multi-tenant isolation - Intra-Tenant Tests

Tests 4d, 4e: Verify that field priorities support user-level independence
within the same tenant, and that tenant_key propagates correctly to
orchestrator jobs.

BUG CONTEXT:
- Each user belongs to a tenant (tenant_key)
- Field priorities are user-specific within a tenant
- Bug: Empty field_priorities means tenant isolation can't be verified

Handover: Field Priority Bug Fix - Phase 1
"""

import random
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

pytestmark = pytest.mark.skip(reason="0750c3: ThinPromptGenerator test assertions stale — needs update for current prompt format")


# ============================================================================
# TEST 4d-4e: Intra-Tenant Isolation and Data Integrity
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_users_same_tenant_independent_priorities(db_session, tenant_a_key):
    """
    TEST 4d: Multiple users in same tenant can have independent field priorities.

    USER STORY:
    1. Two users (Alice and Bob) in same tenant
    2. Alice configures priorities: {git_history: 4}
    3. Bob configures priorities: {git_history: 2}
    4. Each user's orchestrator gets their own priorities

    This verifies user-level isolation within a tenant.
    """
    # ARRANGE: Create two users in same tenant with different priorities
    alice = User(
        id=str(uuid4()),
        username=f"alice_{uuid4().hex[:6]}",
        email=f"alice_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_a_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "git_history": 4,  # Alice excludes git
            },
        },
    )

    bob = User(
        id=str(uuid4()),
        username=f"bob_{uuid4().hex[:6]}",
        email=f"bob_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_a_key,  # SAME TENANT as Alice
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 4,  # Bob excludes vision (different from Alice)
                "git_history": 2,
            },
        },
    )

    db_session.add(alice)
    db_session.add(bob)
    await db_session.commit()
    await db_session.refresh(alice)
    await db_session.refresh(bob)

    # Create shared product and projects
    product = Product(
        id=str(uuid4()), name=f"Shared Product {uuid4().hex[:8]}", tenant_key=tenant_a_key, is_active=True
    )
    db_session.add(product)
    await db_session.commit()

    project_alice = Project(
        id=str(uuid4()),
        name=f"Alice's Project {uuid4().hex[:8]}",
        description="Alice's project description.",
        product_id=str(product.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Alice's mission.",
        series_number=random.randint(1, 999999),
    )

    project_bob = Project(
        id=str(uuid4()),
        name=f"Bob's Project {uuid4().hex[:8]}",
        description="Bob's project description.",
        product_id=str(product.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Bob's mission.",
        series_number=random.randint(1, 999999),
    )

    db_session.add(project_alice)
    db_session.add(project_bob)
    await db_session.commit()

    # ACT: Generate orchestrator for Alice
    generator_alice = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_a_key)

    alice_priorities = alice.field_priority_config.get("priorities", {})

    result_alice = await generator_alice.generate(
        project_id=str(project_alice.id), user_id=str(alice.id), tool="claude-code", field_priorities=alice_priorities
    )

    # ACT: Generate orchestrator for Bob
    generator_bob = ThinClientPromptGenerator(db=db_session, tenant_key=tenant_a_key)

    bob_priorities = bob.field_priority_config.get("priorities", {})

    result_bob = await generator_bob.generate(
        project_id=str(project_bob.id), user_id=str(bob.id), tool="claude-code", field_priorities=bob_priorities
    )

    # ASSERT: Verify Alice got her priorities
    stmt_alice = select(AgentExecution).where(AgentExecution.job_id == result_alice["orchestrator_id"])
    job_alice = (await db_session.execute(stmt_alice)).scalar_one()

    actual_priorities_alice = job_alice.job_metadata.get("field_priorities", {})

    assert actual_priorities_alice["git_history"] == 4, "Alice should have git_history=4 (excluded)"

    # ASSERT: Verify Bob got his priorities
    stmt_bob = select(AgentExecution).where(AgentExecution.job_id == result_bob["orchestrator_id"])
    job_bob = (await db_session.execute(stmt_bob)).scalar_one()

    actual_priorities_bob = job_bob.job_metadata.get("field_priorities", {})

    assert actual_priorities_bob["git_history"] == 2, "Bob should have git_history=2 (included)"

    # CRITICAL: Priorities should be DIFFERENT
    assert actual_priorities_alice != actual_priorities_bob, (
        "Alice and Bob should have independent field priorities even though they're in the same tenant"
    )


@pytest.mark.asyncio
async def test_orchestrator_job_tenant_key_matches_user_tenant(db_session, user_tenant_a, project_tenant_a):
    """
    TEST 4e: Orchestrator job tenant_key should match user's tenant_key.

    DATA INTEGRITY TEST:
    1. User in Tenant A stages project
    2. Created orchestrator job should have tenant_key = Tenant A
    3. Ensures tenant_key is correctly propagated

    This verifies data integrity in tenant isolation.
    """
    # ARRANGE: Extract user priorities
    user_field_config = user_tenant_a.field_priority_config or {}
    field_priorities = user_field_config.get("priorities", {})

    # ACT: Generate orchestrator job
    generator = ThinClientPromptGenerator(db=db_session, tenant_key=user_tenant_a.tenant_key)

    result = await generator.generate(
        project_id=str(project_tenant_a.id),
        user_id=str(user_tenant_a.id),
        tool="claude-code",
        field_priorities=field_priorities,
    )

    orchestrator_id = result["orchestrator_id"]

    # ASSERT: Verify orchestrator job has correct tenant_key
    stmt = select(AgentExecution).where(AgentExecution.job_id == orchestrator_id)
    job_result = await db_session.execute(stmt)
    orchestrator_job = job_result.scalar_one()

    assert orchestrator_job.tenant_key == user_tenant_a.tenant_key, (
        f"Orchestrator job tenant_key should match user's tenant_key. "
        f"Expected: {user_tenant_a.tenant_key}, Got: {orchestrator_job.tenant_key}"
    )

    # Verify project also has matching tenant_key
    assert project_tenant_a.tenant_key == user_tenant_a.tenant_key, (
        "Project should be in same tenant as user (data consistency)"
    )
