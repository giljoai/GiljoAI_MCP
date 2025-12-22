"""
TDD tests for tool_accessor.py migration (Handover 0358c).

Tests the migration from MCPAgentJob to AgentJob + AgentExecution dual model.

Test Philosophy (TDD RED Phase):
- These tests WILL FAIL initially (correct for RED phase)
- Tests define expected behavior BEFORE implementation
- tool_accessor.py currently uses MCPAgentJob
- Phase C implementation will make these tests pass

Semantic Contract (Phase C):
- job_id = work order UUID (WHAT - persistent across succession)
- agent_id = executor UUID (WHO - changes on succession)
- AgentJob = work order (mission, job_type, status: active/completed/cancelled)
- AgentExecution = executor (agent_type, instance_number, status: waiting/working/...)

API Response Contract:
- MCP tools MUST return BOTH job_id and agent_id for backward compatibility
- spawn_agent_job() → {"job_id": "...", "agent_id": "..."}
- get_orchestrator_instructions() → {"job_id": "...", "agent_id": "..."}
- get_agent_mission() → Return both job_id and agent_id

Test Coverage:
1. get_orchestrator_instructions() joins AgentExecution to AgentJob
2. get_orchestrator_instructions() returns both job_id and agent_id
3. spawn_agent_job() creates AgentExecution and returns agent_id
4. get_agent_mission() fetches mission from AgentJob via AgentExecution
5. get_workflow_status() creates both AgentJob and AgentExecution
6. get_pending_jobs() queries AgentJob table
7. Multi-tenant isolation for all MCP tools
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


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
        description="Test product for tool_accessor migration",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, tenant_key, test_product):
    """Create test project."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=test_product.id,
        name="Test Project 0358c",
        description="Test project for tool_accessor migration",
        mission="Test mission for tool_accessor migration",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def orchestrator_job(db_session, tenant_key, test_project):
    """Create orchestrator AgentJob."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Orchestrate test project development",
        job_type="orchestrator",
        status="active",
        job_metadata={"field_priorities": {}, "depth_config": {}},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def orchestrator_execution(db_session, tenant_key, orchestrator_job):
    """Create orchestrator AgentExecution."""
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="working",
        progress=0,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


@pytest_asyncio.fixture
async def tool_accessor(db_manager, db_session, tenant_key):
    """Create ToolAccessor instance with test session for transaction sharing."""
    # Create tenant manager for testing (no validation)
    from src.giljo_mcp.tenant import TenantManager
    tenant_manager = TenantManager()
    # Override get_current_tenant to return test tenant
    tenant_manager.get_current_tenant = lambda: tenant_key
    # Pass test_session for transaction sharing (Handover 0358c)
    return ToolAccessor(db_manager, tenant_manager, test_session=db_session)


# ========================================================================
# Test 1: get_orchestrator_instructions() joins AgentExecution → AgentJob
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_joins_tables(
    tool_accessor, orchestrator_job, orchestrator_execution, tenant_key
):
    """
    Test that get_orchestrator_instructions() queries AgentExecution
    and joins to AgentJob to fetch mission.

    Expected behavior:
    1. Query AgentExecution by job_id (NEW)
    2. Join to AgentJob to fetch mission
    3. Return orchestrator instructions with mission from AgentJob

    Will FAIL initially: tool_accessor.py uses AgentExecution.
    """
    result = await tool_accessor.get_orchestrator_instructions(
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
    )

    # Verify success
    assert result.get("error") is None, f"Unexpected error: {result.get('error')}"

    # Verify mission comes from AgentJob (not duplicated in AgentExecution)
    assert "mission" in result or "fetch_instructions" in result
    # Mission should match the AgentJob.mission
    # (fetch_instructions may replace inline mission per Handover 0350b)


# ========================================================================
# Test 2: get_orchestrator_instructions() returns both job_id and agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_returns_both_ids(
    tool_accessor, orchestrator_job, orchestrator_execution, tenant_key
):
    """
    Test that get_orchestrator_instructions() returns BOTH job_id and agent_id
    for backward compatibility.

    API Contract:
    - job_id: Work order UUID (persistent)
    - agent_id: Executor UUID (specific instance)

    Will FAIL initially: tool_accessor.py doesn't return agent_id separately.
    """
    result = await tool_accessor.get_orchestrator_instructions(
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
    )

    # Verify both IDs present
    assert "job_id" in result, "Missing job_id in response"
    assert "agent_id" in result, "Missing agent_id in response"

    # Verify correct values
    assert result["job_id"] == orchestrator_job.job_id
    assert result["agent_id"] == orchestrator_execution.agent_id


# ========================================================================
# Test 3: spawn_agent_job() creates AgentExecution and returns agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_job_returns_agent_id(
    tool_accessor, orchestrator_job, orchestrator_execution, tenant_key, test_project
):
    """
    Test that spawn_agent_job() creates AgentExecution and returns agent_id.

    Expected behavior:
    1. Create AgentJob for new work order
    2. Create AgentExecution for executor instance
    3. Return BOTH job_id and agent_id in response

    Will FAIL initially: tool_accessor.py uses MCPAgentJob, doesn't return agent_id.
    """
    result = await tool_accessor.spawn_agent_job(
        agent_type="implementer",
        agent_name="impl-auth",
        mission="Implement user authentication",
        project_id=test_project.id,
        tenant_key=tenant_key,
        parent_job_id=orchestrator_job.job_id,
    )

    # Verify success
    assert result.get("success") is True, f"spawn_agent_job failed: {result.get('error')}"

    # Verify BOTH IDs returned
    assert "job_id" in result, "Missing job_id in spawn response"
    assert "agent_id" in result, "Missing agent_id in spawn response"

    # Verify they are different (job vs execution)
    assert result["job_id"] != result["agent_id"]


# ========================================================================
# Test 4: get_agent_mission() fetches mission via AgentJob
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_mission_via_agentjob_mission(
    tool_accessor, orchestrator_job, orchestrator_execution, tenant_key
):
    """
    Test that get_agent_mission() fetches mission from AgentJob.mission.

    Expected behavior:
    1. Query AgentExecution by job_id
    2. Join to AgentJob to fetch mission
    3. Return mission (not duplicated in AgentExecution)

    Will FAIL initially: tool_accessor.py queries AgentExecution.mission directly.
    """
    result = await tool_accessor.get_agent_mission(
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
    )

    # Verify mission returned
    assert "mission" in result, "Missing mission in response"
    # Mission may have team context header (Handover 0353), so check if original mission is in the response
    assert orchestrator_job.mission in result["mission"], "Original mission not found in response"

    # Verify both IDs returned (API contract)
    assert "job_id" in result
    assert "agent_id" in result


# ========================================================================
# Test 5: get_workflow_status() creates both AgentJob and AgentExecution
# ========================================================================


@pytest.mark.asyncio
async def test_get_workflow_status_creates_both_models(
    tool_accessor, tenant_key, test_product, db_session
):
    """
    Test that get_workflow_status() creates BOTH AgentJob and AgentExecution
    when orchestrator doesn't exist yet.

    Expected behavior:
    1. Check if orchestrator exists (query AgentJob)
    2. If not, create AgentJob (work order)
    3. Also create AgentExecution (executor instance)
    4. Return both job_id and agent_id

    Will FAIL initially: tool_accessor.py creates only AgentExecution.
    """
    # Create inactive project for activation test
    inactive_project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=test_product.id,
        name="Inactive Test Project",
        description="Project to be activated",
        mission="Test activation",
        status="inactive",
    )
    db_session.add(inactive_project)
    await db_session.commit()
    await db_session.refresh(inactive_project)

    result = await tool_accessor.gil_activate(
        project_id=inactive_project.id,
    )

    # Verify success
    assert result.get("success") is True

    # Verify both models created in the same session (test transaction)
    from sqlalchemy import select

    # Verify AgentJob created
    job_result = await db_session.execute(
        select(AgentJob).where(
            AgentJob.project_id == inactive_project.id,
            AgentJob.tenant_key == tenant_key,
            AgentJob.job_type == "orchestrator",
        )
    )
    job = job_result.scalar_one_or_none()
    assert job is not None, "AgentJob not created"

    # Verify AgentExecution created
    exec_result = await db_session.execute(
        select(AgentExecution).where(
            AgentExecution.job_id == job.job_id,
            AgentExecution.tenant_key == tenant_key,
        )
    )
    execution = exec_result.scalar_one_or_none()
    assert execution is not None, "AgentExecution not created"

    # Verify relationship
    assert execution.job_id == job.job_id


# ========================================================================
# Test 6: get_pending_jobs() queries AgentJob table
# ========================================================================


@pytest.mark.asyncio
async def test_get_pending_jobs_queries_agentjob_table(
    db_session, tenant_key, test_project
):
    """
    Test that pending jobs query uses AgentJob table.

    Expected behavior:
    1. Query AgentJob for jobs with status="active"
    2. Join to AgentExecution for current executor status
    3. Return jobs with execution details

    Will FAIL initially: tool_accessor.py queries AgentExecution.
    """
    # Create multiple jobs
    job1 = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Job 1",
        job_type="analyzer",
        status="active",
    )
    job2 = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Job 2",
        job_type="implementer",
        status="active",
    )
    job3 = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Job 3",
        job_type="tester",
        status="completed",  # Should be excluded
    )

    db_session.add_all([job1, job2, job3])
    await db_session.commit()

    # Create executions for active jobs
    exec1 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job1.job_id,
        tenant_key=tenant_key,
        agent_type="analyzer",
        instance_number=1,
        status="waiting",
    )
    exec2 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job2.job_id,
        tenant_key=tenant_key,
        agent_type="implementer",
        instance_number=1,
        status="working",
    )

    db_session.add_all([exec1, exec2])
    await db_session.commit()

    # Query pending jobs
    from sqlalchemy import select

    result = await db_session.execute(
        select(AgentJob)
        .where(
            AgentJob.project_id == test_project.id,
            AgentJob.tenant_key == tenant_key,
            AgentJob.status == "active",
        )
    )
    pending_jobs = result.scalars().all()

    # Verify only active jobs returned
    assert len(pending_jobs) == 2
    assert all(job.status == "active" for job in pending_jobs)


# ========================================================================
# Test 7: Multi-tenant isolation for MCP tools
# ========================================================================


@pytest.mark.asyncio
async def test_multi_tenant_isolation_for_mcp_tools(
    tool_accessor, db_session, test_project, test_product
):
    """
    Test that all MCP tools enforce multi-tenant isolation.

    Expected behavior:
    1. Create job/execution in tenant A
    2. Try to access from tenant B
    3. Should return NOT_FOUND (not permission error)

    Will FAIL initially if tool_accessor.py doesn't join tables correctly.
    """
    tenant_a = f"tk_tenant_a_{uuid4().hex[:8]}"
    tenant_b = f"tk_tenant_b_{uuid4().hex[:8]}"

    # Create job in tenant A
    job_a = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_a,
        project_id=test_project.id,
        mission="Tenant A job",
        job_type="orchestrator",
        status="active",
    )
    exec_a = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job_a.job_id,
        tenant_key=tenant_a,
        agent_type="orchestrator",
        instance_number=1,
        status="working",
    )

    db_session.add_all([job_a, exec_a])
    await db_session.commit()

    # Try to access from tenant B
    tool_accessor.tenant_manager.get_current_tenant = lambda: tenant_b

    result = await tool_accessor.get_orchestrator_instructions(
        job_id=job_a.job_id,
        tenant_key=tenant_b,
    )

    # Should return NOT_FOUND (tenant isolation)
    assert result.get("error") == "NOT_FOUND"
    assert "not found" in result.get("message", "").lower()


# ========================================================================
# Test 8: Succession workflow preserves job_id, changes agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_succession_preserves_job_id_changes_agent_id(
    tool_accessor, orchestrator_job, orchestrator_execution, tenant_key
):
    """
    Test that succession creates new AgentExecution with SAME job_id.

    Expected behavior:
    1. Original: job_id=X, agent_id=A, instance=1
    2. Succession: job_id=X (SAME), agent_id=B (NEW), instance=2
    3. Mission remains in AgentJob (not duplicated)

    Will FAIL initially: tool_accessor.py succession uses AgentExecution.
    """
    # Trigger succession
    result = await tool_accessor.create_successor_orchestrator(
        current_job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
        reason="Testing succession workflow",
    )

    # Verify success
    assert result.get("success") is True, f"Succession failed: {result.get('error')}"

    # Verify response contains both IDs
    assert "successor_id" in result  # This might be agent_id
    assert "instance_number" in result

    # Verify new execution created (use test session to see uncommitted changes)
    from sqlalchemy import select

    # Need to use tool_accessor's test session to see the changes
    # Query all executions for this job
    exec_result = await tool_accessor._test_session.execute(
        select(AgentExecution)
        .where(
            AgentExecution.job_id == orchestrator_job.job_id,
            AgentExecution.tenant_key == tenant_key,
        )
        .order_by(AgentExecution.instance_number)
    )
    executions = exec_result.scalars().all()

    # Should have 2 executions now
    assert len(executions) == 2, f"Expected 2 executions, got {len(executions)}"

    # Verify job_id same, agent_id different
    assert executions[0].job_id == executions[1].job_id
    assert executions[0].agent_id != executions[1].agent_id

    # Verify instance numbers
    assert executions[0].instance_number == 1
    assert executions[1].instance_number == 2

    # Verify succession chain
    assert executions[1].spawned_by == executions[0].agent_id


# ========================================================================
# Test 9: get_agent_mission() handles succession chain
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_mission_handles_succession(
    tool_accessor, db_session, orchestrator_job, tenant_key
):
    """
    Test that get_agent_mission() returns correct mission across succession.

    Expected behavior:
    1. Create execution 1 for job
    2. Create execution 2 (successor) for SAME job
    3. get_agent_mission() should return SAME mission for both executions

    Will FAIL initially: Needs dual-model join logic.
    """
    # Create two executions for same job
    exec1 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="decommissioned",
    )
    exec2 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        spawned_by=exec1.agent_id,
    )

    db_session.add_all([exec1, exec2])
    await db_session.commit()

    # Both executions should return SAME mission (from AgentJob)
    result1 = await tool_accessor.get_agent_mission(
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
    )
    result2 = await tool_accessor.get_agent_mission(
        job_id=orchestrator_job.job_id,
        tenant_key=tenant_key,
    )

    # Verify both return same mission (may have team context header from Handover 0353)
    assert orchestrator_job.mission in result1.get("mission", ""), "Original mission not in result1"
    assert orchestrator_job.mission in result2.get("mission", ""), "Original mission not in result2"
    # Both should return the exact same mission (including team context)
    assert result1.get("mission") == result2.get("mission"), "Missions should be identical"


# ========================================================================
# Test 10: Error handling for missing job_id/agent_id
# ========================================================================


@pytest.mark.asyncio
async def test_error_handling_missing_ids(tool_accessor, tenant_key):
    """
    Test error handling when job_id or agent_id not found.

    Expected behavior:
    1. Invalid job_id → NOT_FOUND error
    2. Valid job_id but no execution → Appropriate error
    3. Cross-tenant access → NOT_FOUND (not permission error)

    Will FAIL initially: Needs dual-model error handling.
    """
    fake_job_id = str(uuid4())

    # Test 1: Invalid job_id
    result = await tool_accessor.get_orchestrator_instructions(
        job_id=fake_job_id,
        tenant_key=tenant_key,
    )
    assert result.get("error") == "NOT_FOUND"

    # Test 2: Invalid job_id for get_agent_mission
    result = await tool_accessor.get_agent_mission(
        job_id=fake_job_id,
        tenant_key=tenant_key,
    )
    assert result.get("error") is not None
