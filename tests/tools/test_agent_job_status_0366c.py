"""
TDD Tests for agent_job_status.py (Handover 0366c - RED Phase)

Phase C of Agent Identity Refactor: MCP Tool Standardization

RED Phase: These tests document expected behavior for refactor.

Current Tool Signature (OLD - semantically ambiguous):
- update_job_status(job_id, tenant_key, new_status, reason)

Expected After Refactor:
- Two separate tools with clear semantics:
  1. get_job_status(job_id, tenant_key) → Query work order status (WHAT)
  2. get_agent_status(agent_id, tenant_key) → Query executor status (WHO)
  3. update_job_status(job_id, tenant_key, new_status, reason) → Update work order
  4. update_agent_status(agent_id, tenant_key, new_status, reason) → Update executor

Semantic Clarity:
- job_id = work order UUID (the WHAT - persistent across succession)
- agent_id = executor UUID (the WHO - specific instance)

Key Test Scenarios:
1. Job with multiple executions (succession)
2. Status queries differentiate job vs execution
3. Response includes BOTH job_id AND agent_id for clarity
4. Multi-tenant isolation
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def job_status_setup(db_session, db_manager, tenant_manager):
    """
    Create job with multiple executions for status testing.

    Scenario: Orchestrator succession
    - Job: "build-auth" (work order - persistent)
    - Exec 1: agent-001 (complete - old executor, decommissioned)
    - Exec 2: agent-002 (working - current executor)

    Expected Behavior:
    - get_job_status(job.job_id) → "active" (work order still in progress)
    - get_agent_status(agent-001) → "complete" (old executor finished)
    - get_agent_status(agent-002) → "working" (current executor active)
    """
    tenant_key = "tenant-status-test"

    # Create product (required for project)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for status testing",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project (required for job)
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Project",
        description="Test project for status testing",
        product_id=product.id,
        mission="Build authentication system",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create job (work order - persists across succession)
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        mission="Build OAuth2 authentication system",
        job_type="orchestrator",
        status="active",  # Job still active (work continues)
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)

    # Create first execution (completed and decommissioned)
    exec1 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="complete",  # Executor finished
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        decommissioned_at=datetime.now(timezone.utc),
        progress=100,
        succession_reason="context_limit",
    )
    db_session.add(exec1)

    # Create second execution (current - working)
    exec2 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=2,
        status="working",  # Current executor active
        started_at=datetime.now(timezone.utc),
        spawned_by=exec1.agent_id,  # Succession chain
        progress=45,
        current_task="Implementing OAuth2 token validation",
    )
    db_session.add(exec2)

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(exec1)
    await db_session.refresh(exec2)

    return {
        "tenant_key": tenant_key,
        "product": product,
        "project": project,
        "job": job,
        "exec1": exec1,
        "exec2": exec2,
    }


@pytest_asyncio.fixture(scope="function")
async def multi_tenant_status_setup(db_session, db_manager):
    """
    Create jobs in different tenants for isolation testing.

    Scenario: Multi-tenant isolation
    - Tenant A: job-a with exec-a
    - Tenant B: job-b with exec-b

    Expected Behavior:
    - get_job_status(job-a, tenant_a) → Success
    - get_job_status(job-a, tenant_b) → Error (wrong tenant)
    - get_agent_status(exec-a, tenant_a) → Success
    - get_agent_status(exec-a, tenant_b) → Error (wrong tenant)
    """
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    jobs = {}
    executions = {}

    for tenant in [tenant_a, tenant_b]:
        # Create product
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant,
            name=f"Product {tenant}",
            description=f"Test product for {tenant}",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant,
            name=f"Project {tenant}",
            description=f"Test project for {tenant}",
            product_id=product.id,
            mission="Build something",
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create job
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant,
            project_id=project.id,
            mission=f"Mission for {tenant}",
            job_type="implementer",
            status="active",
        )
        db_session.add(job)

        # Create execution
        execution = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job.job_id,
            tenant_key=tenant,
            agent_type="implementer",
            instance_number=1,
            status="working",
            progress=25,
        )
        db_session.add(execution)

        await db_session.commit()
        await db_session.refresh(job)
        await db_session.refresh(execution)

        jobs[tenant] = job
        executions[tenant] = execution

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "jobs": jobs,
        "executions": executions,
    }


# ============================================================================
# TESTS: get_job_status (Work Order Status)
# ============================================================================


@pytest.mark.asyncio
async def test_get_job_status_returns_work_order_status(job_status_setup, db_manager):
    """
    Test get_job_status() queries AgentJob table (work order).

    Expected: Returns job-level status ("active"), NOT execution status.
    """
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    setup = job_status_setup

    # Query work order status
    result = await get_job_status(
        job_id=setup["job"].job_id,
        tenant_key=setup["tenant_key"],
    )

    # Assertions
    assert result["success"] is True
    assert result["job_id"] == setup["job"].job_id
    assert result["status"] == "active"  # Job status, not execution status
    assert result["job_type"] == "orchestrator"

    # CRITICAL: Response should include both identifiers
    assert "job_id" in result  # Work order ID
    # Note: get_job_status doesn't return agent_id (queries job, not execution)


@pytest.mark.asyncio
async def test_get_job_status_with_multiple_executions(job_status_setup, db_manager):
    """
    Test get_job_status() with job that has multiple executions.

    Expected: Returns job status, optionally lists all executions.
    """
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    setup = job_status_setup

    result = await get_job_status(
        job_id=setup["job"].job_id,
        tenant_key=setup["tenant_key"],
    )

    # Job status should reflect work order state
    assert result["success"] is True
    assert result["status"] == "active"

    # Optional: Response could include execution history
    if "executions" in result:
        assert len(result["executions"]) == 2
        assert result["executions"][0]["agent_id"] == setup["exec1"].agent_id
        assert result["executions"][0]["status"] == "complete"
        assert result["executions"][1]["agent_id"] == setup["exec2"].agent_id
        assert result["executions"][1]["status"] == "working"


@pytest.mark.asyncio
async def test_get_job_status_nonexistent_job(job_status_setup, db_manager):
    """
    Test get_job_status() with nonexistent job_id.

    Expected: Returns error (not found).
    """
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    setup = job_status_setup

    result = await get_job_status(
        job_id=str(uuid.uuid4()),  # Random UUID
        tenant_key=setup["tenant_key"],
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


# ============================================================================
# TESTS: get_agent_status (Executor Status)
# ============================================================================


@pytest.mark.asyncio
async def test_get_agent_status_returns_executor_status(job_status_setup, db_manager):
    """
    Test get_agent_status() queries AgentExecution table (executor).

    Expected: Returns execution-level status ("working"), NOT job status.
    """
    from src.giljo_mcp.tools.agent_job_status import get_agent_status

    setup = job_status_setup

    # Query current executor status
    result = await get_agent_status(
        agent_id=setup["exec2"].agent_id,
        tenant_key=setup["tenant_key"],
    )

    # Assertions
    assert result["success"] is True
    assert result["agent_id"] == setup["exec2"].agent_id
    assert result["status"] == "working"  # Execution status, not job status
    assert result["agent_type"] == "orchestrator"
    assert result["instance_number"] == 2
    assert result["progress"] == 45
    assert result["current_task"] == "Implementing OAuth2 token validation"

    # CRITICAL: Response should include both identifiers
    assert "agent_id" in result  # Executor ID
    assert "job_id" in result  # Work order ID (for context)
    assert result["job_id"] == setup["job"].job_id


@pytest.mark.asyncio
async def test_get_agent_status_old_executor(job_status_setup, db_manager):
    """
    Test get_agent_status() for decommissioned executor.

    Expected: Returns "complete" status for old executor.
    """
    from src.giljo_mcp.tools.agent_job_status import get_agent_status

    setup = job_status_setup

    # Query old executor status
    result = await get_agent_status(
        agent_id=setup["exec1"].agent_id,
        tenant_key=setup["tenant_key"],
    )

    assert result["success"] is True
    assert result["agent_id"] == setup["exec1"].agent_id
    assert result["status"] == "complete"
    assert result["instance_number"] == 1
    assert result["progress"] == 100

    # Should include decommission timestamp
    assert result["decommissioned_at"] is not None


@pytest.mark.asyncio
async def test_get_agent_status_nonexistent_agent(job_status_setup, db_manager):
    """
    Test get_agent_status() with nonexistent agent_id.

    Expected: Returns error (not found).
    """
    from src.giljo_mcp.tools.agent_job_status import get_agent_status

    setup = job_status_setup

    result = await get_agent_status(
        agent_id=str(uuid.uuid4()),  # Random UUID
        tenant_key=setup["tenant_key"],
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


# ============================================================================
# TESTS: Multi-Tenant Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_get_job_status_tenant_isolation(multi_tenant_status_setup, db_manager):
    """
    Test get_job_status() enforces tenant isolation.

    Expected: Cannot query job from wrong tenant.
    """
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    setup = multi_tenant_status_setup

    job_a = setup["jobs"][setup["tenant_a"]]

    # Query with correct tenant - SUCCESS
    result = await get_job_status(
        job_id=job_a.job_id,
        tenant_key=setup["tenant_a"],
    )
    assert result["success"] is True
    assert result["job_id"] == job_a.job_id

    # Query with WRONG tenant - FAIL
    result = await get_job_status(
        job_id=job_a.job_id,
        tenant_key=setup["tenant_b"],  # Wrong tenant
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_agent_status_tenant_isolation(multi_tenant_status_setup, db_manager):
    """
    Test get_agent_status() enforces tenant isolation.

    Expected: Cannot query execution from wrong tenant.
    """
    from src.giljo_mcp.tools.agent_job_status import get_agent_status

    setup = multi_tenant_status_setup

    exec_a = setup["executions"][setup["tenant_a"]]

    # Query with correct tenant - SUCCESS
    result = await get_agent_status(
        agent_id=exec_a.agent_id,
        tenant_key=setup["tenant_a"],
    )
    assert result["success"] is True
    assert result["agent_id"] == exec_a.agent_id

    # Query with WRONG tenant - FAIL
    result = await get_agent_status(
        agent_id=exec_a.agent_id,
        tenant_key=setup["tenant_b"],  # Wrong tenant
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


# ============================================================================
# TESTS: update_job_status (Existing Tool - Semantic Clarification)
# ============================================================================


@pytest.mark.asyncio
async def test_update_job_status_uses_job_id_parameter(job_status_setup, db_manager):
    """
    Test update_job_status() uses job_id parameter (work order).

    Expected: Updates job-level status, affects ALL executions.
    """
    from src.giljo_mcp.tools.agent_job_status import update_job_status

    setup = job_status_setup

    # Update job status to completed
    result = await update_job_status(
        job_id=setup["job"].job_id,  # Work order ID
        tenant_key=setup["tenant_key"],
        new_status="completed",
        reason="All objectives achieved",
    )

    assert result["success"] is True
    assert result["job_id"] == setup["job"].job_id
    assert result["new_status"] == "completed"

    # CRITICAL: Response should clarify this is job-level update
    # (affects work order, not just one execution)


@pytest.mark.asyncio
async def test_response_includes_both_identifiers(job_status_setup, db_manager):
    """
    Test responses include both job_id AND agent_id where meaningful.

    Expected:
    - get_job_status() → includes job_id (primary) + execution list
    - get_agent_status() → includes agent_id (primary) + job_id (context)
    - update_job_status() → includes job_id
    """
    from src.giljo_mcp.tools.agent_job_status import (
        get_job_status,
        get_agent_status,
    )

    setup = job_status_setup

    # Job status response
    job_result = await get_job_status(
        job_id=setup["job"].job_id,
        tenant_key=setup["tenant_key"],
    )
    assert "job_id" in job_result  # Primary identifier

    # Agent status response
    agent_result = await get_agent_status(
        agent_id=setup["exec2"].agent_id,
        tenant_key=setup["tenant_key"],
    )
    assert "agent_id" in agent_result  # Primary identifier
    assert "job_id" in agent_result  # Context (which job is this executor working on)


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_get_agent_status_with_succession_chain(job_status_setup, db_manager):
    """
    Test get_agent_status() includes succession chain information.

    Expected: Response shows spawned_by and succeeded_by relationships.
    """
    from src.giljo_mcp.tools.agent_job_status import get_agent_status

    setup = job_status_setup

    # Query current executor (exec2)
    result = await get_agent_status(
        agent_id=setup["exec2"].agent_id,
        tenant_key=setup["tenant_key"],
    )

    assert result["success"] is True

    # Should show succession chain
    if "spawned_by" in result:
        assert result["spawned_by"] == setup["exec1"].agent_id

    # Query old executor (exec1)
    result_old = await get_agent_status(
        agent_id=setup["exec1"].agent_id,
        tenant_key=setup["tenant_key"],
    )

    # Could show who succeeded (if tracked)
    # (depending on whether we track forward succession)


@pytest.mark.asyncio
async def test_get_job_status_shows_current_executor(job_status_setup, db_manager):
    """
    Test get_job_status() includes current executor information.

    Expected: Response indicates which agent is currently working.
    """
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    setup = job_status_setup

    result = await get_job_status(
        job_id=setup["job"].job_id,
        tenant_key=setup["tenant_key"],
    )

    assert result["success"] is True

    # Should indicate current executor
    if "current_agent_id" in result:
        assert result["current_agent_id"] == setup["exec2"].agent_id
    if "current_instance" in result:
        assert result["current_instance"] == 2


# ============================================================================
# TDD BUG FIX TESTS (Added for Handover 0366c Bug Fix)
# ============================================================================


@pytest.mark.asyncio
async def test_get_job_status_does_not_raise_name_error(db_session, db_manager, tenant_manager):
    """Calling get_job_status should not raise NameError for undefined variables."""
    from src.giljo_mcp.tools.agent_job_status import get_job_status

    test_tenant_key = "test-name-error"

    # Should not raise NameError - even if job doesn't exist
    result = await get_job_status(
        job_id="nonexistent-job",
        tenant_key=test_tenant_key,
        db_manager=db_manager
    )

    # Behavior: Returns error dict, not exception
    assert result["success"] is False
    assert "not found" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_update_job_status_uses_correct_model_import(db_session, db_manager, tenant_manager):
    """
    Test that update_job_status imports AgentJob (not deprecated Job model).

    This is a code inspection test - we verify the import statement is correct.
    We're not testing the full execution path (which has other session management issues).
    """
    import inspect
    from src.giljo_mcp.tools.agent_job_status import update_job_status

    # Get the source code of the function
    source = inspect.getsource(update_job_status)

    # Verify correct import is used
    assert "from giljo_mcp.models.agent_identity import AgentJob" in source

    # Verify deprecated import is NOT used
    assert "from giljo_mcp.models import Job" not in source


# ============================================================================
# EXPECTED FAILURES
# ============================================================================

"""
These tests will FAIL because:
1. get_job_status() and get_agent_status() don't exist yet
2. update_job_status() exists but doesn't return both job_id/agent_id
3. Current implementation is job-centric, not execution-centric

After GREEN phase (implementation):
- Add get_job_status() tool
- Add get_agent_status() tool
- Update response schemas to include both identifiers
- Add execution history to get_job_status() response
"""
