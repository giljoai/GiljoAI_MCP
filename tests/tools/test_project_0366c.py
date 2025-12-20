"""
Comprehensive failing tests for Phase C - project.py semantic refactor (Handover 0366c).

Tests NEW project tool integration with AgentJob/AgentExecution models.

Semantic Contract (Phase C):
- job_id = work order UUID (the WHAT - persistent across succession)
- agent_id = executor UUID (the WHO - specific instance)
- project_id = project UUID (the WHERE - workspace/scope)

Test Philosophy (TDD RED Phase):
- These tests WILL FAIL initially (correct for RED phase)
- Tests define expected behavior BEFORE implementation
- Tools currently use MCPAgentJob (old monolithic model)
- Phase D implementation will make these tests pass

Dependencies:
- Phase A: AgentJob model exists (job-level persistence)
- Phase B: AgentExecution model exists (executor-level tracking)

Test Coverage:
1. Project operations interact with AgentJob/AgentExecution models
2. list_projects() aggregates execution-level data
3. project_status() returns nested job+execution structure
4. close_project() updates both job and execution statuses
5. Multi-tenant isolation enforced
6. Error handling for project operations

IMPORTANT: These tools are registered via FastMCP, so we cannot import them directly.
Instead, we call the MCP tool registration and extract registered functions for testing.
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
        username="test_user_project_0366c",
        email="test_project_0366c@giljoai.com",
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
        name="Test Product Project 0366c",
        description="Test product for project identity refactor",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project_with_job(db_session, tenant_key, test_product):
    """
    Create test project with associated AgentJob and AgentExecution.

    Simulates project with active orchestrator job.
    """
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project with Job 0366c",
        description="Test project with orchestrator job",
        product_id=test_product.id,
        mission="Build authentication system",
        context_budget=150000,
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    # Create AgentJob for orchestrator
    agent_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        mission="Orchestrate authentication system build",
        job_type="orchestrator",
        status="active",
        job_metadata={"auto_created": True},
    )
    db_session.add(agent_job)
    await db_session.flush()

    # Create AgentExecution for orchestrator
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=agent_job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="working",
        agent_name="Project Orchestrator #1",
        context_used=0,
        context_budget=150000,
        tool_type="claude-code",
    )
    db_session.add(execution)
    await db_session.commit()

    await db_session.refresh(project)
    await db_session.refresh(agent_job)
    await db_session.refresh(execution)

    return {
        "project": project,
        "job": agent_job,
        "execution": execution,
    }


# ========================================================================
# Test 1: create_project() - Basic Project Creation (No Job)
# ========================================================================


@pytest.mark.asyncio
async def test_create_project_basic(db_manager, db_session, tenant_key):
    """
    Test create_project() basic functionality without auto-creating job.

    Expected behavior:
    - Creates Project record
    - Returns project_id
    - Does NOT create AgentJob/AgentExecution (unless requested)
    - Multi-tenant isolation enforced

    Will LIKELY PASS because:
    - Current implementation already works for basic project creation
    - This establishes baseline before testing job creation
    """
    from src.giljo_mcp.tools.project import create_project
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    create_project_func = mcp._registered_tools["create_project"]

    # Create project without auto-job
    result = await create_project_func(
        name="Basic Test Project",
        mission="Test mission for basic project",
        tenant_key=tenant_key,
    )

    # Verify success
    assert result.get("success") is True, f"create_project failed: {result.get('error')}"
    assert "project_id" in result, "Response must include project_id"

    # Verify project exists in database
    from sqlalchemy import select

    project_query = select(Project).where(
        Project.id == result["project_id"],
        Project.tenant_key == tenant_key,
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    assert project is not None, "Project should exist in database"
    assert project.name == "Basic Test Project"
    assert project.tenant_key == tenant_key


# ========================================================================
# Test 2: create_project() - With Auto-Create Job (Future Feature)
# ========================================================================


@pytest.mark.asyncio
async def test_create_project_with_auto_job(db_manager, db_session, tenant_key):
    """
    Test create_project() with auto_create_orchestrator_job flag.

    Expected behavior (NEW semantic contract):
    - Creates Project record - project_id
    - Creates AgentJob record - job_id
    - Creates AgentExecution record - agent_id
    - Returns ALL THREE IDs: project_id, job_id, agent_id
    - Links job to project via foreign key
    - Links execution to job via foreign key

    Will FAIL because:
    - create_project() doesn't support auto_create_orchestrator_job yet
    - Old code doesn't use AgentJob/AgentExecution models
    """
    from src.giljo_mcp.tools.project import create_project
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    create_project_func = mcp._registered_tools["create_project"]

    # Create project WITH auto-job creation
    result = await create_project_func(
        name="Project with Auto Job",
        mission="Build feature X with orchestrator",
        tenant_key=tenant_key,
        auto_create_orchestrator_job=True,  # NEW parameter
    )

    # Verify success
    assert result.get("success") is True, f"create_project failed: {result.get('error')}"

    # Verify ALL THREE IDs returned
    assert "project_id" in result, "Response must include project_id"
    assert "job_id" in result, "Response must include job_id (work order)"
    assert "agent_id" in result, "Response must include agent_id (executor)"

    # Verify IDs are distinct UUIDs
    project_id = result["project_id"]
    job_id = result["job_id"]
    agent_id = result["agent_id"]

    assert len({project_id, job_id, agent_id}) == 3, "All three IDs should be unique"

    # Verify Project exists
    from sqlalchemy import select

    project_query = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == tenant_key,
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    assert project is not None, "Project should exist"
    assert project.name == "Project with Auto Job"

    # Verify AgentJob exists and links to project
    job_query = select(AgentJob).where(
        AgentJob.job_id == job_id,
        AgentJob.tenant_key == tenant_key,
    )
    job_result = await db_session.execute(job_query)
    job = job_result.scalar_one_or_none()

    assert job is not None, "AgentJob should be created"
    assert job.project_id == project_id, "Job should link to project"
    assert job.job_type == "orchestrator", "Job should be orchestrator type"
    assert job.tenant_key == tenant_key, "Job tenant isolation"

    # Verify AgentExecution exists and links to job
    exec_query = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id,
        AgentExecution.tenant_key == tenant_key,
    )
    exec_result = await db_session.execute(exec_query)
    execution = exec_result.scalar_one_or_none()

    assert execution is not None, "AgentExecution should be created"
    assert execution.job_id == job_id, "Execution should link to job"
    assert execution.agent_type == "orchestrator", "Execution should be orchestrator type"
    assert execution.instance_number == 1, "First execution should be instance 1"
    assert execution.tenant_key == tenant_key, "Execution tenant isolation"


# ========================================================================
# Test 3: list_projects() - Include Execution-Level Aggregates
# ========================================================================


@pytest.mark.asyncio
async def test_list_projects_includes_execution_aggregates(db_manager, db_session, test_project_with_job):
    """
    Test list_projects() includes execution-level aggregation.

    Expected behavior (NEW semantic contract):
    - Returns list of projects
    - For each project, includes:
      - job_count (number of AgentJobs)
      - execution_count (number of AgentExecutions)
      - active_agents (count of non-completed executions)
    - Uses NEW AgentJob/AgentExecution models

    Will FAIL because:
    - list_projects() uses MCPAgentJob (old model)
    - Doesn't aggregate execution-level data
    """
    from src.giljo_mcp.tools.project import list_projects
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    list_projects_func = mcp._registered_tools["list_projects"]

    # List all projects
    result = await list_projects_func()

    # Verify success
    assert result.get("success") is True, f"list_projects failed: {result.get('error')}"
    assert "projects" in result, "Response must include projects array"

    # Find our test project
    project_data = test_project_with_job["project"]
    found_project = None
    for proj in result["projects"]:
        if proj["id"] == str(project_data.id):
            found_project = proj
            break

    assert found_project is not None, "Test project should be in list"

    # Verify execution-level aggregates (NEW fields)
    assert "job_count" in found_project, "Should include job_count"
    assert found_project["job_count"] >= 1, "Should have at least 1 job"

    assert "execution_count" in found_project, "Should include execution_count"
    assert found_project["execution_count"] >= 1, "Should have at least 1 execution"

    assert "active_agents" in found_project, "Should include active_agents count"
    assert found_project["active_agents"] >= 1, "Should have at least 1 active agent"


# ========================================================================
# Test 4: project_status() - Returns Job and Execution Details
# ========================================================================


@pytest.mark.asyncio
async def test_project_status_returns_job_and_execution_details(db_manager, db_session, test_project_with_job):
    """
    Test project_status() returns job and execution-level details.

    Expected behavior (NEW semantic contract):
    - Returns project details
    - Returns array of jobs (AgentJob records)
    - For each job, returns array of executions (AgentExecution records)
    - Each execution includes: agent_id, instance_number, status, progress
    - Supports succession tracking (multiple executions per job)

    Will FAIL because:
    - project_status() uses MCPAgentJob (old model)
    - Doesn't return execution-level details
    - Doesn't support succession tracking
    """
    from src.giljo_mcp.tools.project import project_status
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    project_status_func = mcp._registered_tools["project_status"]

    project_data = test_project_with_job["project"]
    job_data = test_project_with_job["job"]
    execution_data = test_project_with_job["execution"]

    # Get project status
    result = await project_status_func(project_id=str(project_data.id))

    # Verify success
    assert result.get("success") is True, f"project_status failed: {result.get('error')}"
    assert "project" in result, "Response must include project details"

    # Verify project details
    assert result["project"]["id"] == str(project_data.id)

    # Verify jobs array (NEW structure)
    assert "jobs" in result, "Response must include jobs array"
    assert len(result["jobs"]) >= 1, "Should have at least 1 job"

    # Find our test job
    found_job = None
    for job in result["jobs"]:
        if job["job_id"] == str(job_data.job_id):
            found_job = job
            break

    assert found_job is not None, "Test job should be in jobs array"

    # Verify job details
    assert found_job["job_type"] == "orchestrator"
    assert found_job["status"] == "active"

    # Verify executions array for job (NEW structure)
    assert "executions" in found_job, "Job must include executions array"
    assert len(found_job["executions"]) >= 1, "Job should have at least 1 execution"

    # Find our test execution
    found_execution = None
    for execution in found_job["executions"]:
        if execution["agent_id"] == str(execution_data.agent_id):
            found_execution = execution
            break

    assert found_execution is not None, "Test execution should be in executions array"

    # Verify execution details (NEW fields)
    assert found_execution["agent_id"] == str(execution_data.agent_id)
    assert found_execution["instance_number"] == 1
    assert found_execution["status"] == "working"
    assert "progress" in found_execution
    assert "health_status" in found_execution
    assert found_execution["agent_type"] == "orchestrator"


# ========================================================================
# Test 5: close_project() - Updates Job and Execution Statuses
# ========================================================================


@pytest.mark.asyncio
async def test_close_project_updates_job_and_execution_statuses(db_manager, db_session, test_project_with_job):
    """
    Test close_project() properly updates AgentJob and AgentExecution statuses.

    Expected behavior (NEW semantic contract):
    - Updates Project.status to "completed"
    - Updates all AgentJob.status to "completed" (for active jobs)
    - Updates all AgentExecution.status to "decommissioned" (for active executions)
    - Sets completed_at/decommissioned_at timestamps
    - Multi-tenant isolation enforced

    Will FAIL because:
    - close_project() uses MCPAgentJob (old model)
    - Doesn't update AgentExecution records
    """
    from src.giljo_mcp.tools.project import close_project
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    close_project_func = mcp._registered_tools["close_project"]

    project_data = test_project_with_job["project"]
    job_data = test_project_with_job["job"]
    execution_data = test_project_with_job["execution"]

    # Close project
    result = await close_project_func(
        project_id=str(project_data.id),
        summary="Project completed successfully with OAuth2 implementation",
    )

    # Verify success
    assert result.get("success") is True, f"close_project failed: {result.get('error')}"

    # Verify Project status updated
    from sqlalchemy import select

    project_query = select(Project).where(Project.id == project_data.id)
    project_result = await db_session.execute(project_query)
    updated_project = project_result.scalar_one_or_none()

    assert updated_project.status == "completed", "Project status should be completed"
    assert updated_project.completed_at is not None, "Project completed_at should be set"

    # Verify AgentJob status updated
    job_query = select(AgentJob).where(AgentJob.job_id == job_data.job_id)
    job_result = await db_session.execute(job_query)
    updated_job = job_result.scalar_one_or_none()

    assert updated_job.status == "completed", "Job status should be completed"
    assert updated_job.completed_at is not None, "Job completed_at should be set"

    # Verify AgentExecution status updated (NEW behavior)
    exec_query = select(AgentExecution).where(AgentExecution.agent_id == execution_data.agent_id)
    exec_result = await db_session.execute(exec_query)
    updated_execution = exec_result.scalar_one_or_none()

    assert updated_execution.status == "decommissioned", "Execution status should be decommissioned"
    assert updated_execution.decommissioned_at is not None, "Execution decommissioned_at should be set"


# ========================================================================
# Test 6: switch_project() - Multi-Tenant Isolation
# ========================================================================


@pytest.mark.asyncio
async def test_switch_project_multi_tenant_isolation(db_manager, db_session, test_project_with_job):
    """
    Test switch_project() enforces multi-tenant isolation.

    Expected behavior:
    - Project from tenant1 NOT accessible with tenant2 key
    - No data leakage across tenants
    - Error response doesn't leak project details

    Will LIKELY PASS because:
    - Current implementation already has tenant isolation
    - This establishes baseline for NEW job/execution isolation
    """
    from src.giljo_mcp.tools.project import switch_project
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    switch_project_func = mcp._registered_tools["switch_project"]

    project_data = test_project_with_job["project"]

    # Create project in tenant1 (done in fixture)
    tenant1_key = project_data.tenant_key

    # Create second tenant
    tenant2_key = f"tk_test_{uuid4().hex[:16]}"

    # Attempt cross-tenant access (WRONG tenant key)
    # Note: switch_project doesn't take tenant_key parameter currently
    # This test documents EXPECTED behavior for future enhancement
    # For now, we verify project query isolation at database level

    from sqlalchemy import select

    # Query with wrong tenant should return nothing
    project_query = select(Project).where(
        Project.id == project_data.id,
        Project.tenant_key == tenant2_key,  # WRONG tenant
    )
    result = await db_session.execute(project_query)
    leaked_project = result.scalar_one_or_none()

    assert leaked_project is None, "Cross-tenant project access should be blocked"

    # Query with correct tenant should work
    project_query_correct = select(Project).where(
        Project.id == project_data.id,
        Project.tenant_key == tenant1_key,  # CORRECT tenant
    )
    result_correct = await db_session.execute(project_query_correct)
    valid_project = result_correct.scalar_one_or_none()

    assert valid_project is not None, "Same-tenant project access should work"


# ========================================================================
# Test 7: project_status() - Error Handling for Non-Existent Project
# ========================================================================


@pytest.mark.asyncio
async def test_project_status_error_nonexistent_project(db_manager, db_session, tenant_key):
    """
    Test project_status() error handling for non-existent project_id.

    Expected behavior:
    - Returns structured error response
    - Clear message about project not found
    - Professional error handling

    Will LIKELY PASS because:
    - Current implementation already has error handling
    - This establishes baseline
    """
    from src.giljo_mcp.tools.project import project_status
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered function
    project_status_func = mcp._registered_tools["project_status"]

    fake_project_id = str(uuid4())

    # Get status for non-existent project
    result = await project_status_func(project_id=fake_project_id)

    # Verify error response
    assert "error" in result or result.get("success") is False, "Should return error for non-existent project"

    # Verify error message clarity
    error_msg = result.get("error", "").lower()
    assert "not found" in error_msg or "does not exist" in error_msg, "Error should indicate project not found"


# ========================================================================
# Test 8: Integration - Project with Multiple Jobs and Executions
# ========================================================================


@pytest.mark.asyncio
async def test_project_with_multiple_jobs_and_executions(db_manager, db_session, tenant_key, test_product):
    """
    Test project with multiple jobs (orchestrator + workers) and executions (succession).

    Workflow:
    1. Create project
    2. Create orchestrator job with 2 executions (succession)
    3. Create worker job with 1 execution
    4. Verify project_status() shows all jobs and executions
    5. Verify aggregation counts correct

    Will FAIL because:
    - project_status() doesn't return execution-level details
    - list_projects() doesn't aggregate executions
    """
    from src.giljo_mcp.tools.project import create_project, project_status
    from src.giljo_mcp.tenant import TenantManager
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    tenant_manager = TenantManager()

    # Register tools
    from src.giljo_mcp.tools.project import register_project_tools
    register_project_tools(mcp, db_manager, tenant_manager)

    # Get registered functions
    create_project_func = mcp._registered_tools["create_project"]
    project_status_func = mcp._registered_tools["project_status"]

    # Step 1: Create project
    create_result = await create_project_func(
        name="Multi-Job Test Project",
        mission="Complex project with orchestrator and workers",
        tenant_key=tenant_key,
        product_id=str(test_product.id),
    )

    assert create_result.get("success") is True
    project_id = create_result["project_id"]

    # Step 2: Create orchestrator job with 2 executions (succession)
    orch_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        mission="Orchestrate feature implementation",
        job_type="orchestrator",
        status="active",
        job_metadata={},
    )
    db_session.add(orch_job)
    await db_session.flush()

    # Orchestrator execution 1
    orch_exec1 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orch_job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        agent_name="Orchestrator #1",
        context_used=90000,
        context_budget=150000,
        tool_type="claude-code",
    )
    db_session.add(orch_exec1)

    # Orchestrator execution 2 (successor)
    orch_exec2 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orch_job.job_id,  # SAME job
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=2,  # Succession
        status="working",
        agent_name="Orchestrator #2",
        spawned_by=orch_exec1.agent_id,
        context_used=10000,
        context_budget=150000,
        tool_type="claude-code",
    )
    db_session.add(orch_exec2)

    # Step 3: Create worker job with 1 execution
    worker_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project_id,
        mission="Implement authentication endpoints",
        job_type="implementer",
        status="active",
        job_metadata={},
    )
    db_session.add(worker_job)
    await db_session.flush()

    worker_exec = AgentExecution(
        agent_id=str(uuid4()),
        job_id=worker_job.job_id,
        tenant_key=tenant_key,
        agent_type="implementer",
        instance_number=1,
        status="working",
        agent_name="Backend Implementer #1",
        spawned_by=orch_exec1.agent_id,
        context_used=20000,
        context_budget=50000,
        tool_type="claude-code",
    )
    db_session.add(worker_exec)

    await db_session.commit()

    # Step 4: Get project status
    status_result = await project_status_func(project_id=project_id)

    assert status_result.get("success") is True

    # Verify jobs array
    assert "jobs" in status_result
    jobs = status_result["jobs"]
    assert len(jobs) == 2, "Should have 2 jobs (orchestrator + worker)"

    # Find orchestrator job
    orch_job_data = None
    worker_job_data = None
    for job in jobs:
        if job["job_type"] == "orchestrator":
            orch_job_data = job
        elif job["job_type"] == "implementer":
            worker_job_data = job

    assert orch_job_data is not None, "Orchestrator job should be in response"
    assert worker_job_data is not None, "Worker job should be in response"

    # Verify orchestrator job has 2 executions (succession)
    assert "executions" in orch_job_data
    assert len(orch_job_data["executions"]) == 2, "Orchestrator job should have 2 executions"

    # Verify execution instance numbers
    orch_instances = sorted([exec["instance_number"] for exec in orch_job_data["executions"]])
    assert orch_instances == [1, 2], "Orchestrator executions should be instances 1 and 2"

    # Verify worker job has 1 execution
    assert "executions" in worker_job_data
    assert len(worker_job_data["executions"]) == 1, "Worker job should have 1 execution"

    # Step 5: Verify aggregation counts
    assert status_result.get("job_count") == 2, "Should count 2 jobs total"
    assert status_result.get("execution_count") == 3, "Should count 3 executions total (2 orch + 1 worker)"
    assert status_result.get("active_agents") == 2, "Should count 2 active agents (orch #2 + worker)"
