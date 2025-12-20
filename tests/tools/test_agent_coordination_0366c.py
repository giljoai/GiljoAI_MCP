"""
Comprehensive failing tests for Phase C - Agent Identity Refactor (Handover 0366c).

Tests the NEW semantic contract for agent coordination tools:
- spawn_agent(job_id, ...) - Spawns NEW execution for EXISTING job
- get_agent_status(agent_id, ...) - Queries SPECIFIC executor status

Semantic Contract (Phase C):
- agent_id = executor UUID (the WHO - specific agent instance)
- job_id = work order UUID (the WHAT - persistent across succession)

Test Philosophy (TDD RED Phase):
- These tests WILL FAIL initially (correct for RED phase)
- Tests define expected behavior BEFORE implementation
- Tools currently use old parameter names (job_id ambiguously)
- Phase C implementation will make these tests pass

Dependencies:
- Phase A: AgentJob model exists (job-level persistence)
- Phase B: AgentExecution model exists (executor-level tracking)

Test Coverage:
1. spawn_agent() creates AgentExecution for AgentJob
2. spawn_agent() returns BOTH job_id and agent_id
3. get_agent_status() uses agent_id (not job_id)
4. Multi-tenant isolation for agent_id
5. Succession chain tracking via agent_id
6. Error handling for missing job_id/agent_id
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.auth import User


# ========================================================================
# Test Fixtures
# ========================================================================


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_user(db_session, tenant_key):
    """Create test user."""
    user = User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username="test_user_0366c",
        email="test_0366c@giljoai.com",
        password_hash="hashed_password",
        config_data={},
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session, tenant_key):
    """Create test product."""
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product 0366c",
        description="Test product for agent identity refactor",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, tenant_key, test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project 0366c",
        description="Test project for Phase C",
        product_id=test_product.id,
        mission="Implement OAuth2 authentication",
        context_budget=150000,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_agent_job(db_session, tenant_key, test_project):
    """
    Create test AgentJob (work order) - Phase A artifact.

    This is the WHAT (mission, scope, objectives).
    Multiple executions can reference this same job.
    """
    agent_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Build OAuth2 authentication with JWT tokens",
        job_type="implementer",
        status="active",
        job_metadata={"priority": "high"},
    )
    db_session.add(agent_job)
    await db_session.commit()
    await db_session.refresh(agent_job)
    return agent_job


@pytest_asyncio.fixture
async def test_agent_execution(db_session, tenant_key, test_agent_job):
    """
    Create test AgentExecution (executor instance) - Phase B artifact.

    This is the WHO (which agent instance is executing).
    References the parent AgentJob via foreign key.
    """
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_agent_job.job_id,
        tenant_key=tenant_key,
        agent_type="implementer",
        instance_number=1,
        status="working",
        agent_name="Backend Implementer #1",
        context_used=0,
        context_budget=50000,
        tool_type="claude-code",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


# ========================================================================
# Test 1: spawn_agent() - Creates AgentExecution for Existing Job
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_creates_execution_for_job(db_session, tenant_key, test_agent_job, test_project):
    """
    Test spawn_agent() creates NEW executor for EXISTING job.

    Expected behavior (NEW semantic contract):
    - Takes job_id (work order UUID) as input
    - Creates NEW AgentExecution (executor instance)
    - Links execution to job via foreign key
    - Returns BOTH job_id and agent_id
    - Increments instance_number (succession tracking)

    Will FAIL because:
    - spawn_agent() doesn't exist yet in agent_coordination.py
    - Old code uses ambiguous job_id for both concepts
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent

    # Call spawn_agent with job_id (work order)
    result = await spawn_agent(
        job_id=test_agent_job.job_id,  # NEW semantic: the WHAT (work order)
        agent_type="implementer",
        tenant_key=tenant_key,
    )

    # Verify success
    assert result.get("success") is True, f"spawn_agent failed: {result.get('error')}"

    # Verify BOTH IDs returned (Phase C requirement)
    assert "job_id" in result, "spawn_agent must return job_id (work order)"
    assert "agent_id" in result, "spawn_agent must return agent_id (executor)"

    # Verify job_id matches input (persistence)
    assert result["job_id"] == test_agent_job.job_id, "job_id should persist from input"

    # Verify agent_id is NEW (executor instance)
    agent_id = result["agent_id"]
    assert agent_id != test_agent_job.job_id, "agent_id should be NEW (not reusing job_id)"

    # Verify AgentExecution created in database
    from sqlalchemy import select

    execution_query = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id,
        AgentExecution.tenant_key == tenant_key,
    )
    execution_result = await db_session.execute(execution_query)
    execution = execution_result.scalar_one_or_none()

    assert execution is not None, "AgentExecution should be created in database"
    assert execution.job_id == test_agent_job.job_id, "Execution should reference parent job"
    assert execution.agent_type == "implementer", "Agent type should match input"
    assert execution.tenant_key == tenant_key, "Tenant isolation should be enforced"

    # Verify instance_number incremented (succession tracking)
    assert execution.instance_number >= 1, "Instance number should be sequential"


# ========================================================================
# Test 2: spawn_agent() - Returns Both job_id and agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_returns_both_ids(db_session, tenant_key, test_agent_job):
    """
    Test spawn_agent() returns BOTH job_id and agent_id in response.

    Expected behavior (NEW semantic contract):
    - Response includes job_id (the WHAT - work order)
    - Response includes agent_id (the WHO - executor)
    - Both are UUIDs but serve different purposes
    - Enables clear communication in logs/UI

    Will FAIL because:
    - spawn_agent() doesn't exist yet
    - Old code only returned job_id ambiguously
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent

    result = await spawn_agent(
        job_id=test_agent_job.job_id,
        agent_type="tester",
        tenant_key=tenant_key,
    )

    # Verify both IDs present
    assert "job_id" in result, "Response must include job_id (work order)"
    assert "agent_id" in result, "Response must include agent_id (executor)"

    # Verify they are different UUIDs
    assert result["job_id"] != result["agent_id"], "job_id and agent_id should be distinct"

    # Verify job_id is the work order
    assert result["job_id"] == test_agent_job.job_id, "job_id should match input (persistent)"

    # Verify agent_id is the executor
    assert len(result["agent_id"]) == 36, "agent_id should be valid UUID format"

    # Verify response clarity (for logging/debugging)
    if "message" in result:
        # Should mention BOTH concepts clearly
        message = result["message"].lower()
        assert "agent" in message or "executor" in message, "Message should clarify executor concept"


# ========================================================================
# Test 3: get_agent_status() - Uses agent_id (NOT job_id)
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_status_uses_agent_id(db_session, tenant_key, test_agent_execution):
    """
    Test get_agent_status() uses agent_id (executor UUID) to query status.

    Expected behavior (NEW semantic contract):
    - Takes agent_id (executor UUID) as input (NOT job_id)
    - Queries AgentExecution table by agent_id
    - Returns executor-specific status (status, progress, health)
    - Does NOT query AgentJob table

    Will FAIL because:
    - get_agent_status() currently uses job_id ambiguously
    - Need to change parameter from job_id → agent_id
    """
    from src.giljo_mcp.tools.agent_coordination import get_agent_status

    # Call with agent_id (executor UUID) - NEW semantic contract
    result = await get_agent_status(
        agent_id=test_agent_execution.agent_id,  # NEW semantic: the WHO (executor)
        tenant_key=tenant_key,
    )

    # Verify success
    assert result.get("success") is True or "error" not in result, f"get_agent_status failed: {result.get('error')}"

    # Verify agent_id returned (executor identity)
    assert "agent_id" in result, "Response must include agent_id (executor UUID)"
    assert result["agent_id"] == test_agent_execution.agent_id, "agent_id should match input"

    # Verify executor-specific fields returned
    assert "status" in result, "Response must include execution status"
    assert result["status"] == test_agent_execution.status, "Status should match AgentExecution record"

    assert "progress" in result, "Response must include execution progress"
    assert result["progress"] == test_agent_execution.progress, "Progress should match AgentExecution record"

    assert "health_status" in result, "Response must include health status"

    # Verify job_id also returned (for context)
    assert "job_id" in result, "Response should include job_id for reference"
    assert result["job_id"] == test_agent_execution.job_id, "job_id should reference parent job"


# ========================================================================
# Test 4: get_agent_status() - Multi-Tenant Isolation by agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_status_multi_tenant_isolation(db_session, test_agent_execution):
    """
    Test multi-tenant isolation using agent_id (executor UUID).

    Expected behavior (NEW semantic contract):
    - Agent from tenant1 NOT accessible with tenant2 key
    - No data leakage across tenants (executor-level isolation)
    - Error response doesn't leak executor details
    - Zero cross-tenant access

    Will FAIL because:
    - get_agent_status() might not exist with agent_id parameter yet
    """
    from src.giljo_mcp.tools.agent_coordination import get_agent_status

    # Create second tenant
    tenant2_key = f"tk_test_{uuid4().hex[:16]}"

    # Attempt cross-tenant access (WRONG tenant key)
    result = await get_agent_status(
        agent_id=test_agent_execution.agent_id,  # tenant1's executor
        tenant_key=tenant2_key,  # WRONG tenant key
    )

    # Verify access denied
    assert "error" in result or result.get("success") is False, "Cross-tenant access should be denied"

    # Verify no executor data leaked
    assert "status" not in result, "Status should not leak across tenants"
    assert "progress" not in result, "Progress should not leak across tenants"
    assert "health_status" not in result, "Health status should not leak across tenants"
    assert test_agent_execution.agent_name not in str(result), "Agent name should not leak"


# ========================================================================
# Test 5: spawn_agent() - Succession Chain Tracking
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_succession_chain(db_session, tenant_key, test_agent_job, test_agent_execution):
    """
    Test spawn_agent() tracks succession chain via spawned_by.

    Expected behavior (NEW semantic contract):
    - spawned_by field contains parent AGENT_ID (executor UUID)
    - NOT parent job_id (work order UUID)
    - Enables tracing executor lineage
    - Supports multi-level succession chains

    Will FAIL because:
    - spawn_agent() doesn't accept spawned_by_agent_id yet
    - Old code might use job_id for spawned_by (ambiguous)
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent

    # Spawn NEW executor with parent executor reference
    result = await spawn_agent(
        job_id=test_agent_job.job_id,  # Work order (persistent)
        agent_type="implementer",
        tenant_key=tenant_key,
        spawned_by_agent_id=test_agent_execution.agent_id,  # Parent EXECUTOR (not job)
    )

    # Verify success
    assert result.get("success") is True, f"spawn_agent failed: {result.get('error')}"

    # Verify NEW agent_id created
    new_agent_id = result["agent_id"]
    assert new_agent_id != test_agent_execution.agent_id, "Should create NEW executor"

    # Verify succession chain in database
    from sqlalchemy import select

    execution_query = select(AgentExecution).where(
        AgentExecution.agent_id == new_agent_id,
        AgentExecution.tenant_key == tenant_key,
    )
    execution_result = await db_session.execute(execution_query)
    new_execution = execution_result.scalar_one_or_none()

    assert new_execution is not None, "New execution should exist"
    assert new_execution.spawned_by == test_agent_execution.agent_id, (
        "spawned_by should contain parent AGENT_ID (executor), not job_id"
    )

    # Verify instance number incremented
    assert new_execution.instance_number > test_agent_execution.instance_number, (
        "Instance number should increment for succession"
    )


# ========================================================================
# Test 6: spawn_agent() - Error Handling for Missing job_id
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_error_missing_job_id(db_session, tenant_key):
    """
    Test spawn_agent() error handling for missing job_id.

    Expected behavior:
    - Returns structured error response
    - Clear message about missing job_id (work order)
    - Professional error handling
    - No exceptions raised

    Will FAIL because:
    - spawn_agent() doesn't exist yet
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent

    # Call with empty job_id
    result = await spawn_agent(
        job_id="",  # Invalid
        agent_type="implementer",
        tenant_key=tenant_key,
    )

    # Verify error response
    assert "error" in result or result.get("success") is False, "Should return error for empty job_id"

    # Verify error message clarity
    error_msg = result.get("error", result.get("message", "")).lower()
    assert "job" in error_msg or "required" in error_msg, "Error should mention missing job_id"


# ========================================================================
# Test 7: spawn_agent() - Error Handling for Non-Existent job_id
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_error_nonexistent_job_id(db_session, tenant_key):
    """
    Test spawn_agent() error handling for non-existent job_id.

    Expected behavior:
    - Returns structured error response
    - Clear message about job not found
    - Suggests checking job_id (work order UUID)
    - Professional error handling

    Will FAIL because:
    - spawn_agent() doesn't exist yet
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent

    fake_job_id = str(uuid4())

    # Call with non-existent job_id
    result = await spawn_agent(
        job_id=fake_job_id,  # Doesn't exist
        agent_type="tester",
        tenant_key=tenant_key,
    )

    # Verify error response
    assert "error" in result or result.get("success") is False, "Should return error for non-existent job"

    # Verify error message clarity
    error_msg = result.get("error", result.get("message", "")).lower()
    assert "not found" in error_msg or "does not exist" in error_msg, "Error should indicate job not found"


# ========================================================================
# Test 8: get_agent_status() - Error Handling for Missing agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_status_error_missing_agent_id(db_session, tenant_key):
    """
    Test get_agent_status() error handling for missing agent_id.

    Expected behavior:
    - Returns structured error response
    - Clear message about missing agent_id (executor UUID)
    - Professional error handling
    - No exceptions raised

    Will FAIL because:
    - get_agent_status() uses job_id currently (wrong parameter)
    """
    from src.giljo_mcp.tools.agent_coordination import get_agent_status

    # Call with empty agent_id
    result = await get_agent_status(
        agent_id="",  # Invalid
        tenant_key=tenant_key,
    )

    # Verify error response
    assert "error" in result or result.get("success") is False, "Should return error for empty agent_id"

    # Verify error message clarity
    error_msg = result.get("error", result.get("message", "")).lower()
    assert "agent" in error_msg or "required" in error_msg, "Error should mention missing agent_id"


# ========================================================================
# Test 9: get_agent_status() - Error Handling for Non-Existent agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_status_error_nonexistent_agent_id(db_session, tenant_key):
    """
    Test get_agent_status() error handling for non-existent agent_id.

    Expected behavior:
    - Returns structured error response
    - Clear message about executor not found
    - Suggests checking agent_id (executor UUID)
    - Professional error handling

    Will FAIL because:
    - get_agent_status() uses job_id currently (wrong parameter)
    """
    from src.giljo_mcp.tools.agent_coordination import get_agent_status

    fake_agent_id = str(uuid4())

    # Call with non-existent agent_id
    result = await get_agent_status(
        agent_id=fake_agent_id,  # Doesn't exist
        tenant_key=tenant_key,
    )

    # Verify error response
    assert "error" in result or result.get("success") is False, "Should return error for non-existent agent"

    # Verify error message clarity
    error_msg = result.get("error", result.get("message", "")).lower()
    assert "not found" in error_msg or "does not exist" in error_msg, "Error should indicate agent not found"


# ========================================================================
# Test 10: Integration - Full Succession Flow
# ========================================================================


@pytest.mark.asyncio
async def test_full_succession_flow(db_session, tenant_key, test_project):
    """
    Test complete succession workflow using NEW semantic contract.

    Workflow:
    1. Create AgentJob (work order) - job_id
    2. Spawn Execution 1 (executor) - agent_id_1
    3. Get status for agent_id_1
    4. Spawn Execution 2 (successor) - agent_id_2, same job_id
    5. Get status for agent_id_2
    6. Verify both executions reference same job

    Will FAIL because:
    - spawn_agent() and get_agent_status() don't exist with NEW signatures yet
    """
    from src.giljo_mcp.tools.agent_coordination import spawn_agent, get_agent_status

    # Step 1: Create AgentJob (work order)
    agent_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Implement rate limiting middleware",
        job_type="implementer",
        status="active",
        job_metadata={},
    )
    db_session.add(agent_job)
    await db_session.commit()
    await db_session.refresh(agent_job)

    # Step 2: Spawn Execution 1 (first executor)
    exec1_result = await spawn_agent(
        job_id=agent_job.job_id,  # Work order (persistent)
        agent_type="implementer",
        tenant_key=tenant_key,
    )

    assert exec1_result.get("success") is True
    agent_id_1 = exec1_result["agent_id"]

    # Step 3: Get status for agent_id_1
    status1_result = await get_agent_status(
        agent_id=agent_id_1,  # Executor UUID
        tenant_key=tenant_key,
    )

    assert status1_result.get("success") is True or "error" not in status1_result
    assert status1_result["agent_id"] == agent_id_1
    assert status1_result["job_id"] == agent_job.job_id

    # Step 4: Spawn Execution 2 (successor - SAME job)
    exec2_result = await spawn_agent(
        job_id=agent_job.job_id,  # SAME work order (persistence)
        agent_type="implementer",
        tenant_key=tenant_key,
        spawned_by_agent_id=agent_id_1,  # Parent executor
    )

    assert exec2_result.get("success") is True
    agent_id_2 = exec2_result["agent_id"]

    # Verify different executors, same job
    assert agent_id_2 != agent_id_1, "Should create NEW executor"
    assert exec2_result["job_id"] == agent_job.job_id, "Should reference SAME job"

    # Step 5: Get status for agent_id_2
    status2_result = await get_agent_status(
        agent_id=agent_id_2,  # Successor executor UUID
        tenant_key=tenant_key,
    )

    assert status2_result.get("success") is True or "error" not in status2_result
    assert status2_result["agent_id"] == agent_id_2
    assert status2_result["job_id"] == agent_job.job_id

    # Step 6: Verify both executions reference same job
    from sqlalchemy import select

    executions_query = select(AgentExecution).where(
        AgentExecution.job_id == agent_job.job_id,
        AgentExecution.tenant_key == tenant_key,
    ).order_by(AgentExecution.instance_number)

    executions_result = await db_session.execute(executions_query)
    executions = executions_result.scalars().all()

    assert len(executions) == 2, "Should have 2 executions for same job"
    assert executions[0].agent_id == agent_id_1, "First execution should be agent_id_1"
    assert executions[1].agent_id == agent_id_2, "Second execution should be agent_id_2"
    assert executions[1].spawned_by == agent_id_1, "Second execution should track parent agent_id"
    assert executions[1].instance_number > executions[0].instance_number, "Instance numbers should increment"
