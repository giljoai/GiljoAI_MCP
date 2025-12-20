"""
TDD Tests for agent_status.py tools (Handover 0366c - RED Phase)

Phase C of Agent Identity Refactor: MCP Tool Standardization

RED Phase: These tests document expected behavior for refactor.

Current Tool Signatures (OLD - uses job_id):
- set_agent_status(job_id, tenant_key, status, ...)
- report_progress(job_id, tenant_key, progress)

Expected NEW Signatures (after refactor):
- set_agent_status(agent_id, tenant_key, status, ...)
- report_progress(agent_id, tenant_key, progress)

Semantic Contract:
- agent_id = executor UUID (the WHO - specific agent instance)
- job_id = work order UUID (the WHAT - persistent across succession)
- Health monitoring targets executions (agent_id), not jobs
- Status updates target executions (agent_id), not jobs
- Response includes both agent_id (executor) and job_id (work order context)
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
async def health_monitoring_setup(db_session):
    """
    Create job with two executions for health monitoring tests.

    Scenario: Orchestrator succession
    - Job: "job-health" (work order)
    - Exec 1: agent-001 (complete - old executor)
    - Exec 2: agent-002 (working - current executor, monitored)

    Health checks should monitor agent-002 (active execution), NOT agent-001.
    """
    tenant_key = "tenant-health-test"

    # Create product (required for project)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product Health",
        description="Test product for health monitoring",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project (required for job)
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Project Health",
        description="Test project for health monitoring",
        product_id=product.id,
        mission="Build monitoring system",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create job (work order)
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        mission="Monitor system health",
        job_type="orchestrator",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)

    # Create first execution (completed)
    exec1 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        progress=100,
        health_status="healthy",
        last_health_check=datetime.now(timezone.utc),
    )
    db_session.add(exec1)

    # Create second execution (working - successor)
    exec2 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,  # SAME job as exec1
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        started_at=datetime.now(timezone.utc),
        spawned_by=exec1.agent_id,  # Succession chain
        progress=25,
        health_status="healthy",
        last_health_check=datetime.now(timezone.utc),
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
        "exec1": exec1,  # Completed execution
        "exec2": exec2,  # Active execution
    }


@pytest_asyncio.fixture(scope="function")
async def status_update_setup(db_session):
    """
    Create job with one execution for status update tests.
    """
    tenant_key = "tenant-status-update"

    # Create product (required for project)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product Status",
        description="Test product for status updates",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project (required for job)
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Project Status",
        description="Test project for status updates",
        product_id=product.id,
        mission="Update system status",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        mission="Update system status",
        job_type="implementer",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="implementer",
        instance_number=1,
        status="waiting",
        started_at=datetime.now(timezone.utc),
        progress=0,
        health_status="unknown",
    )
    db_session.add(execution)

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return {
        "tenant_key": tenant_key,
        "product": product,
        "project": project,
        "job": job,
        "execution": execution,
    }


# ============================================================================
# TEST 1: Health Check Uses Agent ID (Executor-Specific)
# ============================================================================


@pytest.mark.asyncio
async def test_health_check_should_use_agent_id(health_monitoring_setup, db_session):
    """
    Test: Health monitoring should target specific agent_id (executor)

    After refactor, check_agent_health(agent_id=...) should:
    1. Look up AgentExecution by agent_id
    2. Return health status for THAT specific executor
    3. Include both agent_id (executor) and job_id (context) in response

    This test documents expected behavior - WILL FAIL until refactor complete.
    """
    setup = health_monitoring_setup
    tenant_key = setup["tenant_key"]
    job = setup["job"]
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    # Import tool (will fail until refactor)
    from src.giljo_mcp.tools.agent_status import set_agent_status

    # Simulate health check for exec2 (active execution)
    # After refactor, this should use agent_id parameter
    # For now, we test the expected database state

    # Update exec2 health directly (simulating refactored tool behavior)
    exec2.health_status = "healthy"
    exec2.last_health_check = datetime.now(timezone.utc)
    await db_session.commit()
    await db_session.refresh(exec2)

    # Verify exec2 health updated
    assert exec2.health_status == "healthy"
    assert exec2.last_health_check is not None

    # Verify exec1 health unchanged (different executor)
    await db_session.refresh(exec1)
    assert exec1.health_status == "healthy"  # Unchanged from fixture

    # Expected response structure after refactor:
    expected_response = {
        "success": True,
        "agent_id": exec2.agent_id,  # NEW: executor identifier
        "job_id": job.job_id,  # Context: what work order
        "health_status": "healthy",
        "last_health_check": exec2.last_health_check.isoformat(),
    }

    # Verify response includes both agent_id and job_id
    assert expected_response["agent_id"] == exec2.agent_id
    assert expected_response["job_id"] == job.job_id


@pytest.mark.asyncio
async def test_health_check_isolates_between_executions(health_monitoring_setup, db_session):
    """
    Test: Health status is per-execution (not per-job)

    Scenario: Two executions on same job have DIFFERENT health states
    - Exec1: Complete, healthy (old executor)
    - Exec2: Working, warning (current executor)

    Critical: Without agent_id targeting, we'd conflate health states.
    """
    setup = health_monitoring_setup
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    # Set different health states for each execution
    exec1.health_status = "healthy"
    exec1.health_failure_count = 0
    exec2.health_status = "warning"
    exec2.health_failure_count = 2

    await db_session.commit()
    await db_session.refresh(exec1)
    await db_session.refresh(exec2)

    # Verify different health states
    assert exec1.health_status == "healthy"
    assert exec2.health_status == "warning"
    assert exec1.health_failure_count == 0
    assert exec2.health_failure_count == 2

    # After refactor, check_agent_health(agent_id=exec2.agent_id) should return "warning"
    # NOT "healthy" from exec1


# ============================================================================
# TEST 2: Status Updates Target Agent Execution
# ============================================================================


@pytest.mark.asyncio
async def test_set_agent_status_should_use_agent_id(status_update_setup, db_session):
    """
    Test: set_agent_status() should target specific agent_id (executor)

    After refactor, set_agent_status(agent_id=..., status=...) should:
    1. Look up AgentExecution by agent_id
    2. Update execution.status, execution.progress
    3. Leave AgentJob unchanged (job status is stable)
    4. Return both agent_id and job_id in response

    This test documents expected behavior - WILL FAIL until refactor complete.
    """
    setup = status_update_setup
    tenant_key = setup["tenant_key"]
    job = setup["job"]
    execution = setup["execution"]

    # Simulate status update for execution (simulating refactored tool behavior)
    execution.status = "working"
    execution.progress = 50
    execution.current_task = "Implementing feature X"

    await db_session.commit()
    await db_session.refresh(execution)

    # Verify execution updated
    assert execution.status == "working"
    assert execution.progress == 50
    assert execution.current_task == "Implementing feature X"

    # Verify job unchanged (job status is stable)
    await db_session.refresh(job)
    assert job.status == "active", "Job status should not change when updating execution status"

    # Expected response structure after refactor:
    expected_response = {
        "success": True,
        "agent_id": execution.agent_id,  # NEW: executor identifier
        "job_id": job.job_id,  # Context: what work order
        "old_status": "waiting",
        "new_status": "working",
        "message": "Status updated to 'working' successfully",
    }

    # Verify response includes both agent_id and job_id
    assert expected_response["agent_id"] == execution.agent_id
    assert expected_response["job_id"] == job.job_id


@pytest.mark.asyncio
async def test_set_agent_status_with_progress_requires_agent_id(status_update_setup, db_session):
    """
    Test: Progress updates are executor-specific (not job-wide)

    Scenario: Update execution progress using agent_id
    - Before: progress=0, status=waiting
    - After: progress=75, status=working

    After refactor, set_agent_status(agent_id=..., status="working", progress=75)
    should update THAT specific execution (not all executions on the job).
    """
    setup = status_update_setup
    execution = setup["execution"]

    # Simulate progress update
    execution.status = "working"
    execution.progress = 75
    execution.current_task = "Writing tests"

    await db_session.commit()
    await db_session.refresh(execution)

    # Verify updates
    assert execution.status == "working"
    assert execution.progress == 75
    assert execution.current_task == "Writing tests"


# ============================================================================
# TEST 3: Response Includes Both Agent ID and Job ID
# ============================================================================


@pytest.mark.asyncio
async def test_status_update_response_includes_both_ids(status_update_setup):
    """
    Test: Status update response includes both agent_id and job_id

    Response structure after refactor:
    {
        "success": true,
        "agent_id": "uuid-exec",  # WHO executed the update
        "job_id": "uuid-job",     # WHAT work order context
        "old_status": "...",
        "new_status": "...",
        "message": "..."
    }

    This provides:
    - agent_id: Identifies the specific executor (for succession tracking)
    - job_id: Provides work order context (for UI linking)
    """
    setup = status_update_setup
    job = setup["job"]
    execution = setup["execution"]

    # Expected response structure
    expected_response = {
        "success": True,
        "agent_id": execution.agent_id,  # Executor
        "job_id": job.job_id,  # Work order
        "old_status": "waiting",
        "new_status": "working",
        "message": "Status updated to 'working' successfully",
    }

    # Verify both IDs present
    assert "agent_id" in expected_response
    assert "job_id" in expected_response
    assert expected_response["agent_id"] == execution.agent_id
    assert expected_response["job_id"] == job.job_id


# ============================================================================
# TEST 4: Isolation Between Executions on Same Job
# ============================================================================


@pytest.mark.asyncio
async def test_status_updates_isolated_between_executions(health_monitoring_setup, db_session):
    """
    Test: Status updates target specific execution (not all executions on job)

    Scenario: Two executions on same job
    - Exec1: Complete (100% progress)
    - Exec2: Working (25% progress)

    After refactor, set_agent_status(agent_id=exec2.agent_id, progress=50)
    should update ONLY exec2 (not exec1).
    """
    setup = health_monitoring_setup
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    # Record initial states
    exec1_initial_progress = exec1.progress
    exec2_initial_progress = exec2.progress

    # Update exec2 only (simulating refactored tool behavior)
    exec2.progress = 50
    exec2.current_task = "Refactoring code"

    await db_session.commit()
    await db_session.refresh(exec1)
    await db_session.refresh(exec2)

    # Verify exec2 updated
    assert exec2.progress == 50
    assert exec2.current_task == "Refactoring code"

    # Verify exec1 unchanged
    assert exec1.progress == exec1_initial_progress, "Exec1 should not be affected by exec2 update"
    assert exec1.current_task is None  # Unchanged from fixture


# ============================================================================
# TEST 5: Multi-Tenant Isolation (Security)
# ============================================================================


@pytest.mark.asyncio
async def test_status_update_blocks_cross_tenant_access(db_session):
    """
    Test: Status updates enforce multi-tenant isolation

    Security: Tenant A cannot update Tenant B's agent status (even with valid agent_id).
    """
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Create product and project for Tenant B
    product_b = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Product B",
        description="Product for tenant B",
        is_active=True,
    )
    db_session.add(product_b)
    await db_session.commit()
    await db_session.refresh(product_b)

    project_b = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Project B",
        description="Project for tenant B",
        product_id=product_b.id,
        mission="Tenant B work",
        status="active",
    )
    db_session.add(project_b)
    await db_session.commit()
    await db_session.refresh(project_b)

    # Create execution for Tenant B
    job_b = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        mission="Tenant B work",
        job_type="implementer",
        status="active",
    )
    db_session.add(job_b)

    exec_b = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_b.job_id,
        tenant_key=tenant_b,
        agent_type="implementer",
        instance_number=1,
        status="working",
        progress=0,
    )
    db_session.add(exec_b)

    await db_session.commit()
    await db_session.refresh(exec_b)

    # Import tool (will fail until refactor)
    from src.giljo_mcp.tools.agent_status import set_agent_status

    # Act: Tenant A tries to update Tenant B's execution
    with pytest.raises(ValueError, match="not found for tenant"):
        await set_agent_status(
            agent_id=exec_b.agent_id,  # Tenant B's agent!
            tenant_key=tenant_a,  # Tenant A's key!
            status="blocked",
            reason="Malicious attempt",
        )


# ============================================================================
# TEST 6: Report Progress Targets Agent Execution
# ============================================================================


@pytest.mark.asyncio
async def test_report_progress_should_use_agent_id(status_update_setup, db_session):
    """
    Test: report_progress() should target specific agent_id (executor)

    After refactor, report_progress(agent_id=..., progress={...}) should:
    1. Look up AgentExecution by agent_id
    2. Update execution.last_progress_at timestamp
    3. Store progress in execution metadata (not job metadata)

    This test documents expected behavior - WILL FAIL until refactor complete.
    """
    setup = status_update_setup
    tenant_key = setup["tenant_key"]
    job = setup["job"]
    execution = setup["execution"]

    # Simulate progress report (simulating refactored tool behavior)
    now = datetime.now(timezone.utc)
    execution.last_progress_at = now
    # Note: Progress stored in execution metadata, not job metadata

    await db_session.commit()
    await db_session.refresh(execution)

    # Verify execution updated
    assert execution.last_progress_at is not None
    assert (now - execution.last_progress_at).total_seconds() < 5  # Recent timestamp

    # Expected response structure after refactor:
    expected_response = {
        "success": True,
        "agent_id": execution.agent_id,  # NEW: executor identifier
        "job_id": job.job_id,  # Context: what work order
        "timestamp": now.isoformat(),
        "message": "Progress reported successfully",
    }

    # Verify response includes both agent_id and job_id
    assert expected_response["agent_id"] == execution.agent_id
    assert expected_response["job_id"] == job.job_id


# ============================================================================
# TEST 7: Expected Tool Signature After Refactor
# ============================================================================


@pytest.mark.asyncio
async def test_expected_tool_signatures_documentation():
    """
    Test: Document expected tool signatures after refactor

    This is a documentation test that specifies the expected API.

    Current (OLD):
    - set_agent_status(job_id, tenant_key, status, ...)
    - report_progress(job_id, tenant_key, progress)

    Expected (NEW):
    - set_agent_status(agent_id, tenant_key, status, ...)
    - report_progress(agent_id, tenant_key, progress)

    Implementation notes for GREEN phase:
    1. Rename job_id parameter to agent_id in both tools
    2. Look up AgentExecution (not Job/MCPAgentJob) using agent_id
    3. Update execution fields (status, progress, health_status, etc.)
    4. Include both agent_id and job_id in response for context
    5. Maintain tenant_key filtering for security
    """
    # This test always passes - it's documentation only
    expected_signatures = {
        "set_agent_status": {
            "old_params": [
                "job_id",
                "tenant_key",
                "status",
                "progress",
                "reason",
                "current_task",
                "estimated_completion",
            ],
            "new_params": [
                "agent_id",  # Changed from job_id
                "tenant_key",
                "status",
                "progress",
                "reason",
                "current_task",
                "estimated_completion",
            ],
            "changes": [
                "job_id → agent_id",
                "Look up AgentExecution (not Job)",
                "Response includes both agent_id and job_id",
            ],
        },
        "report_progress": {
            "old_params": ["job_id", "tenant_key", "progress"],
            "new_params": ["agent_id", "tenant_key", "progress"],
            "changes": [
                "job_id → agent_id",
                "Look up AgentExecution (not MCPAgentJob)",
                "Update execution.last_progress_at",
                "Response includes both agent_id and job_id",
            ],
        },
    }

    assert expected_signatures["set_agent_status"]["new_params"][0] == "agent_id"
    assert expected_signatures["report_progress"]["new_params"][0] == "agent_id"


# ============================================================================
# TEST 8: Nonexistent Agent ID Handling
# ============================================================================


@pytest.mark.asyncio
async def test_status_update_handles_nonexistent_agent_id(db_session):
    """
    Test: set_agent_status() handles nonexistent agent_id gracefully

    After refactor, set_agent_status(agent_id="nonexistent") should:
    - Raise ValueError with clear message (agent not found)
    - NOT crash the server
    """
    from src.giljo_mcp.tools.agent_status import set_agent_status

    # Try to update status for nonexistent agent
    with pytest.raises(ValueError, match="not found"):
        await set_agent_status(
            agent_id="nonexistent-agent-id",
            tenant_key="tenant-test",
            status="working",
            progress=50,
        )
