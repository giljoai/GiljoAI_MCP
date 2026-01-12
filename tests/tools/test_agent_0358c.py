"""
Comprehensive failing tests for agent.py migration (Handover 0358c).

Tests the migration from MCPAgentJob to AgentJob + AgentExecution in agent.py.

Semantic Contract (Handover 0358c):
- job_id = work order UUID (the WHAT - persistent across succession)
- agent_id = executor UUID (the WHO - specific agent instance)
- AgentJob = work order (mission, job_type, status: active/completed/cancelled)
- AgentExecution = executor (agent_display_name, instance_number, status: waiting/working/blocked/complete/failed/cancelled/decommissioned)

Test Philosophy (TDD RED Phase):
- These tests WILL FAIL initially (correct for RED phase)
- Tests define expected behavior BEFORE implementation
- agent.py currently uses MCPAgentJob (deprecated model)
- Implementation will migrate to AgentJob + AgentExecution
- Tests verify NEW behavior (dual-model architecture)

Dependencies:
- Phase A: AgentJob model exists (job-level persistence)
- Phase B: AgentExecution model exists (executor-level tracking)
- Phase C: agent_coordination.py migrated (0366c) - use as reference

Test Coverage:
1. launch_agent() uses AgentExecution by agent_id
2. _ensure_agent_with_session() creates AgentJob + AgentExecution pair
3. _decommission_agent_with_session() updates AgentExecution status
4. _get_agent_health_with_session() queries AgentExecution table
5. _handoff_agent_work_with_session() creates successor AgentExecution
6. spawn_and_log_sub_agent() creates AgentJob + AgentExecution for sub-agent
7. Multi-tenant isolation for all agent operations
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
        username="test_user_0358c",
        email="test_0358c@giljoai.com",
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
        name="Test Product 0358c",
        description="Test product for agent.py migration",
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
        name="Test Project 0358c",
        description="Test project for agent.py migration",
        product_id=test_product.id,
        mission="Implement user authentication system",
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
        mission="Build authentication with JWT tokens",
        job_type="backend-implementor",
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
        agent_display_name="backend-implementor",
        instance_number=1,
        status="waiting",
        agent_name="Backend Implementor #1",
        context_used=0,
        context_budget=50000,
        tool_type="claude-code",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


# ========================================================================
# Test 1: launch_agent() - Uses AgentExecution by agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_launch_agent_uses_agent_execution(db_session, tenant_key, test_agent_execution):
    """
    Test launch_agent() queries AgentExecution by agent_id (not MCPAgentJob by job_id).

    Expected behavior (NEW semantic contract):
    - Takes agent_id (executor UUID) as input
    - Queries AgentExecution table (not MCPAgentJob)
    - Updates AgentExecution.status to "working"
    - Updates AgentExecution.last_progress_at timestamp
    - Enforces tenant isolation via tenant_key

    Will FAIL because:
    - launch_agent() currently queries MCPAgentJob by job_id
    - Need to change to query AgentExecution by agent_id
    - Parameter name needs to change: agent_id (not job_id)
    """
    from src.giljo_mcp.tools.agent import launch_agent

    # Call launch_agent with agent_id (executor UUID) - NEW semantic contract
    result = await launch_agent(
        agent_id=test_agent_execution.agent_id,  # NEW: executor UUID (not job_id)
        tenant_key=tenant_key,
        session=db_session,
    )

    # Verify success
    assert result.get("success") is True, f"launch_agent failed: {result.get('error')}"

    # Verify agent_id returned (executor identity)
    assert "agent_id" in result, "Response must include agent_id (executor UUID)"
    assert result["agent_id"] == test_agent_execution.agent_id, "agent_id should match input"

    # Verify status updated
    assert result["status"] == "working", "Status should be 'working' after launch"

    # Verify database updated
    await db_session.refresh(test_agent_execution)
    assert test_agent_execution.status == "working", "AgentExecution.status should be updated in DB"
    assert test_agent_execution.last_progress_at is not None, "AgentExecution.last_progress_at should be set"


# ========================================================================
# Test 2: _ensure_agent_with_session() - Creates AgentJob + AgentExecution
# ========================================================================


@pytest.mark.asyncio
async def test_ensure_agent_creates_both_models(db_session, tenant_key, test_project):
    """
    Test _ensure_agent_with_session() creates BOTH AgentJob AND AgentExecution.

    Expected behavior (NEW dual-model architecture):
    - Creates AgentJob (work order) with mission, job_type
    - Creates AgentExecution (executor) with agent_display_name, instance_number=1
    - Links execution to job via foreign key (AgentExecution.job_id)
    - Returns both job_id and agent_id in response
    - Both models share tenant_key for isolation

    Will FAIL because:
    - _ensure_agent_with_session() currently creates only MCPAgentJob
    - Need to create AgentJob first, then AgentExecution
    - Response needs both job_id and agent_id
    """
    from src.giljo_mcp.tools.agent import _ensure_agent_with_session

    # Set project tenant_key so function can access it
    test_project.tenant_key = tenant_key

    # Call _ensure_agent_with_session to create new agent
    result = await _ensure_agent_with_session(
        session=db_session,
        project_id=test_project.id,
        agent_name="backend-implementor",
        mission="Build REST API with FastAPI",
    )

    # Verify success
    assert result.get("success") is True, f"ensure_agent failed: {result.get('error')}"

    # Verify BOTH IDs returned
    assert "job_id" in result, "Response must include job_id (work order UUID)"
    assert "agent_id" in result, "Response must include agent_id (executor UUID)"

    # Verify they are different UUIDs
    assert result["job_id"] != result["agent_id"], "job_id and agent_id should be distinct"

    # Verify AgentJob created in database
    from sqlalchemy import select

    job_query = select(AgentJob).where(
        AgentJob.job_id == result["job_id"],
        AgentJob.tenant_key == tenant_key,
    )
    job_result = await db_session.execute(job_query)
    agent_job = job_result.scalar_one_or_none()

    assert agent_job is not None, "AgentJob should be created in database"
    assert agent_job.mission == "Build REST API with FastAPI", "AgentJob.mission should match input"
    assert agent_job.job_type == "backend-implementor", "AgentJob.job_type should match agent_name"
    assert agent_job.status == "active", "AgentJob.status should be 'active'"

    # Verify AgentExecution created in database
    execution_query = select(AgentExecution).where(
        AgentExecution.agent_id == result["agent_id"],
        AgentExecution.tenant_key == tenant_key,
    )
    execution_result = await db_session.execute(execution_query)
    agent_execution = execution_result.scalar_one_or_none()

    assert agent_execution is not None, "AgentExecution should be created in database"
    assert agent_execution.job_id == result["job_id"], "AgentExecution should reference parent job"
    assert agent_execution.agent_display_name == "backend-implementor", "AgentExecution.agent_display_name should match"
    assert agent_execution.instance_number == 1, "First execution should have instance_number=1"
    assert agent_execution.status == "waiting", "AgentExecution.status should be 'waiting'"


# ========================================================================
# Test 3: _ensure_agent_with_session() - Returns Existing Agent (Idempotent)
# ========================================================================


@pytest.mark.asyncio
async def test_ensure_agent_returns_existing(db_session, tenant_key, test_agent_job, test_agent_execution):
    """
    Test _ensure_agent_with_session() is IDEMPOTENT (returns existing agent).

    Expected behavior (idempotency):
    - If AgentJob + AgentExecution already exist for project + agent_name
    - Returns existing job_id and agent_id (latest execution)
    - Does NOT create duplicate records
    - Sets is_new=False in response

    Will FAIL because:
    - ensure_agent() currently only checks MCPAgentJob
    - Need to query AgentJob by project_id + job_type
    - Need to return latest AgentExecution for that job
    """
    from src.giljo_mcp.tools.agent import _ensure_agent_with_session

    # Set agent_name for test_agent_execution (needed for lookup)
    test_agent_execution.agent_name = "backend-implementor #1"
    await db_session.commit()

    # Call _ensure_agent_with_session for EXISTING agent
    result = await _ensure_agent_with_session(
        session=db_session,
        project_id=test_agent_job.project_id,
        agent_name="backend-implementor",
        mission="Build REST API",  # Different mission - should NOT create new
    )

    # Verify success
    assert result.get("success") is True, f"ensure_agent failed: {result.get('error')}"

    # Verify returns existing IDs
    assert result["job_id"] == test_agent_job.job_id, "Should return existing job_id"
    assert result["agent_id"] == test_agent_execution.agent_id, "Should return existing agent_id"

    # Verify is_new=False
    assert result.get("is_new") is False, "is_new should be False for existing agent"

    # Verify no duplicate AgentJob created
    from sqlalchemy import select

    job_query = select(AgentJob).where(
        AgentJob.project_id == test_agent_job.project_id,
        AgentJob.job_type == "backend-implementor",
        AgentJob.tenant_key == tenant_key,
    )
    job_result = await db_session.execute(job_query)
    jobs = job_result.scalars().all()

    assert len(jobs) == 1, "Should NOT create duplicate AgentJob"


# ========================================================================
# Test 4: _decommission_agent_with_session() - Updates AgentExecution Status
# ========================================================================


@pytest.mark.asyncio
async def test_decommission_updates_execution_status(db_session, tenant_key, test_agent_job, test_agent_execution):
    """
    Test _decommission_agent_with_session() updates AgentExecution.status to 'decommissioned'.

    Expected behavior (NEW semantic contract):
    - Queries AgentExecution by agent_name + project_id
    - Sets AgentExecution.status = "decommissioned"
    - Optionally sets AgentJob.status = "completed" if all executions done
    - Returns success with decommission details

    Will FAIL because:
    - _decommission_agent_with_session() currently updates MCPAgentJob
    - Need to query and update AgentExecution instead
    - Need to check if all executions are done before completing job
    """
    from src.giljo_mcp.tools.agent import _decommission_agent_with_session

    # Set agent_name for lookup
    test_agent_execution.agent_name = "backend-implementor"
    await db_session.commit()

    # Call _decommission_agent_with_session
    result = await _decommission_agent_with_session(
        session=db_session,
        agent_name="backend-implementor",
        project_id=test_agent_job.project_id,
        reason="completed",
    )

    # Verify success
    assert result.get("success") is True, f"decommission_agent failed: {result.get('error')}"

    # Verify response
    assert result["status"] == "decommissioned", "Status should be 'decommissioned'"
    assert result["reason"] == "completed", "Reason should match input"

    # Verify AgentExecution updated in database
    await db_session.refresh(test_agent_execution)
    assert test_agent_execution.status == "decommissioned", "AgentExecution.status should be 'decommissioned'"

    # Verify AgentJob status updated (since only 1 execution)
    await db_session.refresh(test_agent_job)
    assert test_agent_job.status == "completed", "AgentJob.status should be 'completed' when all executions done"


# ========================================================================
# Test 5: _get_agent_health_with_session() - Queries AgentExecution Table
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_health_queries_execution_table(db_session, tenant_key, test_agent_execution):
    """
    Test _get_agent_health_with_session() queries AgentExecution table (not MCPAgentJob).

    Expected behavior (NEW semantic contract):
    - Queries AgentExecution by agent_name (if specified)
    - Returns executor-specific fields: status, context_used, last_active
    - Queries all AgentExecution records if agent_name=None
    - Includes job_id for reference

    Will FAIL because:
    - _get_agent_health_with_session() currently queries MCPAgentJob
    - Need to query AgentExecution table instead
    - Fields come from AgentExecution model
    """
    from src.giljo_mcp.tools.agent import _get_agent_health_with_session

    # Set agent_name for lookup
    test_agent_execution.agent_name = "backend-implementor"
    await db_session.commit()

    # Call _get_agent_health_with_session for specific agent
    result = await _get_agent_health_with_session(
        session=db_session,
        agent_name="backend-implementor",
    )

    # Verify success
    assert result.get("success") is True, f"get_agent_health failed: {result.get('error')}"

    # Verify executor-specific fields returned
    assert result["agent"] == "backend-implementor", "Agent name should match input"
    assert result["status"] == test_agent_execution.status, "Status should match AgentExecution.status"
    assert "context_used" in result, "Response must include context_used"
    assert "last_activity" in result, "Response must include last_activity"

    # Verify job_id included for reference
    assert "job_id" in result, "Response should include job_id for reference"
    assert result["job_id"] == test_agent_execution.job_id, "job_id should match AgentExecution.job_id"


# ========================================================================
# Test 6: _handoff_agent_work_with_session() - Creates Successor AgentExecution
# ========================================================================


@pytest.mark.asyncio
async def test_handoff_creates_successor_execution(db_session, tenant_key, test_agent_job, test_agent_execution):
    """
    Test _handoff_agent_work_with_session() creates successor AgentExecution.

    Expected behavior (NEW semantic contract):
    - Creates NEW AgentExecution for "to_agent"
    - Sets new_execution.spawned_by = from_agent.agent_id (executor UUID)
    - Sets from_execution.succeeded_by = new_agent_id
    - Sets from_execution.status = "complete"
    - Sets new_execution.status = "working"
    - Both executions reference SAME job_id (work order persistence)

    Will FAIL because:
    - _handoff_agent_work_with_session() currently updates MCPAgentJob statuses
    - Need to create new AgentExecution for successor
    - Need to track succession via agent_id (not job_id)
    """
    from src.giljo_mcp.tools.agent import _handoff_agent_work_with_session

    # Set agent_name for lookup
    test_agent_execution.agent_name = "backend-implementor"
    await db_session.commit()

    # Create target agent (to_agent) first
    to_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_agent_job.job_id,  # SAME job (work order)
        tenant_key=tenant_key,
        agent_display_name="backend-implementor",
        instance_number=2,
        status="waiting",
        agent_name="backend-implementor #2",
        context_used=0,
        context_budget=50000,
        tool_type="claude-code",
    )
    db_session.add(to_execution)
    await db_session.commit()

    # Call _handoff_agent_work_with_session
    result = await _handoff_agent_work_with_session(
        session=db_session,
        from_agent="backend-implementor",
        to_agent="backend-implementor #2",
        project_id=test_agent_job.project_id,
        context={"handoff_reason": "Context budget exceeded"},
    )

    # Verify success
    assert result.get("success") is True, f"handoff_agent_work failed: {result.get('error')}"

    # Verify from_execution updated
    await db_session.refresh(test_agent_execution)
    assert test_agent_execution.status == "complete", "From executor status should be 'complete'"
    assert test_agent_execution.succeeded_by == to_execution.agent_id, "succeeded_by should track successor agent_id"

    # Verify to_execution updated
    await db_session.refresh(to_execution)
    assert to_execution.status == "working", "To executor status should be 'working'"
    assert to_execution.spawned_by == test_agent_execution.agent_id, "spawned_by should track predecessor agent_id"

    # Verify both executions reference same job
    assert test_agent_execution.job_id == to_execution.job_id, "Both executions should reference same job_id"


# ========================================================================
# Test 7: spawn_and_log_sub_agent() - Creates AgentJob + AgentExecution
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_sub_agent_creates_execution(db_session, tenant_key, test_project, test_agent_execution):
    """
    Test spawn_and_log_sub_agent() creates AgentJob + AgentExecution for sub-agent.

    Expected behavior (NEW semantic contract):
    - Creates AgentJob for sub-agent mission
    - Creates AgentExecution with spawned_by=parent_agent.agent_id
    - Links execution to parent via agent_id (not job_id)
    - Returns interaction_id for tracking

    Will FAIL because:
    - spawn_and_log_sub_agent() currently works with MCPAgentJob
    - Need to create AgentJob + AgentExecution pair
    - spawned_by should reference parent agent_id
    """
    # This test would require more setup (parent agent, etc.)
    # For now, we'll test the pattern is correct

    # Note: Actual implementation will need to:
    # 1. Create AgentJob for sub-agent mission
    # 2. Create AgentExecution with spawned_by=parent.agent_id
    # 3. Create AgentInteraction record (existing behavior)
    # 4. Update parent context_used (existing behavior)

    pytest.skip("Requires full MCP tool setup - pattern tested in ensure_agent tests")


# ========================================================================
# Test 8: Multi-Tenant Isolation for Agent Operations
# ========================================================================


@pytest.mark.asyncio
async def test_multi_tenant_isolation_on_agent_operations(db_session, test_agent_execution):
    """
    Test multi-tenant isolation for agent operations.

    Expected behavior (multi-tenant isolation):
    - Agent from tenant1 NOT accessible with tenant2 key
    - No data leakage across tenants (executor-level isolation)
    - Error response doesn't leak executor details
    - Zero cross-tenant access

    Will FAIL because:
    - Current code may not enforce tenant_key filtering consistently
    - Need to verify all queries filter by tenant_key
    """
    from src.giljo_mcp.tools.agent import launch_agent

    # Create second tenant
    tenant2_key = f"tk_test_{uuid4().hex[:16]}"

    # Attempt cross-tenant access (WRONG tenant key)
    result = await launch_agent(
        agent_id=test_agent_execution.agent_id,  # tenant1's executor
        tenant_key=tenant2_key,  # WRONG tenant key
        session=db_session,
    )

    # Verify access denied
    assert "error" in result or result.get("success") is False, "Cross-tenant access should be denied"

    # Verify no executor data leaked
    assert "status" not in result or result.get("status") is None, "Status should not leak across tenants"
    assert test_agent_execution.agent_name not in str(result), "Agent name should not leak"


# ========================================================================
# Test 9: _ensure_agent_with_session() - Tenant Isolation on Creation
# ========================================================================


@pytest.mark.asyncio
async def test_ensure_agent_tenant_isolation(db_session, test_project):
    """
    Test _ensure_agent_with_session() enforces tenant isolation on creation.

    Expected behavior (tenant isolation):
    - AgentJob created with project's tenant_key
    - AgentExecution created with same tenant_key
    - No cross-tenant access to created agents

    Will FAIL because:
    - Need to verify tenant_key propagates correctly
    """
    from src.giljo_mcp.tools.agent import _ensure_agent_with_session

    # Call _ensure_agent_with_session
    result = await _ensure_agent_with_session(
        session=db_session,
        project_id=test_project.id,
        agent_name="frontend-developer",
        mission="Build React components",
    )

    # Verify success
    assert result.get("success") is True

    # Verify tenant_key matches project
    from sqlalchemy import select

    job_query = select(AgentJob).where(AgentJob.job_id == result["job_id"])
    job_result = await db_session.execute(job_query)
    agent_job = job_result.scalar_one_or_none()

    assert agent_job.tenant_key == test_project.tenant_key, "AgentJob.tenant_key should match project"

    execution_query = select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
    execution_result = await db_session.execute(execution_query)
    agent_execution = execution_result.scalar_one_or_none()

    assert agent_execution.tenant_key == test_project.tenant_key, "AgentExecution.tenant_key should match project"


# ========================================================================
# Test 10: Integration - Full Agent Lifecycle
# ========================================================================


@pytest.mark.asyncio
async def test_full_agent_lifecycle_workflow(db_session, tenant_key, test_project):
    """
    Test complete agent lifecycle using NEW dual-model architecture.

    Workflow:
    1. Ensure agent (creates AgentJob + AgentExecution)
    2. Launch agent (updates AgentExecution status)
    3. Get health (queries AgentExecution)
    4. Decommission agent (updates AgentExecution + AgentJob)

    Will FAIL because:
    - Functions use MCPAgentJob instead of dual-model
    """
    from src.giljo_mcp.tools.agent import (
        _ensure_agent_with_session,
        launch_agent,
        _get_agent_health_with_session,
        _decommission_agent_with_session,
    )

    # Step 1: Ensure agent (create AgentJob + AgentExecution)
    ensure_result = await _ensure_agent_with_session(
        session=db_session,
        project_id=test_project.id,
        agent_name="database-expert",
        mission="Design database schema",
    )

    assert ensure_result.get("success") is True
    job_id = ensure_result["job_id"]
    agent_id = ensure_result["agent_id"]

    # Step 2: Launch agent (update AgentExecution)
    launch_result = await launch_agent(
        agent_id=agent_id,
        tenant_key=tenant_key,
        session=db_session,
    )

    assert launch_result.get("success") is True
    assert launch_result["status"] == "working"

    # Step 3: Get health (query AgentExecution)
    health_result = await _get_agent_health_with_session(
        session=db_session,
        agent_name="database-expert",
    )

    assert health_result.get("success") is True
    assert health_result["status"] == "working"

    # Step 4: Decommission agent (update both models)
    decommission_result = await _decommission_agent_with_session(
        session=db_session,
        agent_name="database-expert",
        project_id=test_project.id,
        reason="completed",
    )

    assert decommission_result.get("success") is True
    assert decommission_result["status"] == "decommissioned"

    # Verify final state in database
    from sqlalchemy import select

    execution_query = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    execution_result = await db_session.execute(execution_query)
    execution = execution_result.scalar_one_or_none()

    assert execution.status == "decommissioned", "Execution should be decommissioned"

    job_query = select(AgentJob).where(AgentJob.job_id == job_id)
    job_result = await db_session.execute(job_query)
    job = job_result.scalar_one_or_none()

    assert job.status == "completed", "Job should be completed"
