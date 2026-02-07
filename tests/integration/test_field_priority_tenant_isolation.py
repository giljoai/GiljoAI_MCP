"""
Integration tests for field priority multi-tenant isolation - TDD Phase 1 (RED)

This test suite verifies that field priorities respect tenant isolation,
ensuring users in different tenants cannot access each other's configurations.

BUG CONTEXT:
- Each user belongs to a tenant (tenant_key)
- Field priorities are user-specific within a tenant
- Bug: Empty field_priorities means tenant isolation can't be verified

These tests will initially FAIL to confirm proper tenant isolation.

Handover: Field Priority Bug Fix - Phase 1
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


# Use existing fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def tenant_a_key():
    """Tenant A isolation key"""
    return f"tenant_a_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def tenant_b_key():
    """Tenant B isolation key (different from tenant A)"""
    return f"tenant_b_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_tenant_a(db_session, tenant_a_key):
    """Create user in Tenant A with specific field priorities"""
    user = User(
        id=str(uuid4()),
        username=f"user_a_{uuid4().hex[:6]}",
        email=f"user_a_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_a_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4,  # Tenant A excludes git_history
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_tenant_b(db_session, tenant_b_key):
    """Create user in Tenant B with DIFFERENT field priorities"""
    user = User(
        id=str(uuid4()),
        username=f"user_b_{uuid4().hex[:6]}",
        email=f"user_b_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_b_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 4,  # Tenant B excludes vision_documents
                "agent_templates": 2,
                "project_description": 1,
                "memory_360": 4,  # Tenant B excludes memory_360
                "git_history": 2,  # Tenant B INCLUDES git_history (different from A)
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def product_tenant_a(db_session, tenant_a_key):
    """Create product in Tenant A"""
    product = Product(
        id=str(uuid4()),
        name=f"Product A {uuid4().hex[:8]}",
        description="Product for Tenant A.",
        tenant_key=tenant_a_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def product_tenant_b(db_session, tenant_b_key):
    """Create product in Tenant B"""
    product = Product(
        id=str(uuid4()),
        name=f"Product B {uuid4().hex[:8]}",
        description="Product for Tenant B.",
        tenant_key=tenant_b_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def project_tenant_a(db_session, product_tenant_a, tenant_a_key):
    """Create project in Tenant A"""
    project = Project(
        id=str(uuid4()),
        name=f"Project A {uuid4().hex[:8]}",
        description="Project for Tenant A.",
        product_id=str(product_tenant_a.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Mission for Tenant A.",
        context_budget=180000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def project_tenant_b(db_session, product_tenant_b, tenant_b_key):
    """Create project in Tenant B"""
    project = Project(
        id=str(uuid4()),
        name=f"Project B {uuid4().hex[:8]}",
        description="Project for Tenant B.",
        product_id=str(product_tenant_b.id),
        tenant_key=tenant_b_key,
        status="planning",
        mission="Mission for Tenant B.",
        context_budget=180000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# TEST 4: Multi-Tenant Isolation of Field Priorities
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
        product_id=str(product.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Alice's mission.",
        context_budget=180000,
    )

    project_bob = Project(
        id=str(uuid4()),
        name=f"Bob's Project {uuid4().hex[:8]}",
        product_id=str(product.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Bob's mission.",
        context_budget=180000,
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
