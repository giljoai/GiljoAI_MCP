"""
Tests for get_team_agents() - Team Discovery Tool (Handover 0360 Feature 2).

Purpose:
Agents need to discover teammates working on the same project to coordinate effectively.

Tool Signature:
    get_team_agents(job_id: str, tenant_key: str, include_inactive: bool = False) -> dict

Expected Response:
    {
        "success": true,
        "team": [
            {"agent_id": "ae-001", "job_id": "job-abc", "agent_display_name": "orchestrator", "status": "working"},
            {"agent_id": "ae-002", "job_id": "job-abc", "agent_display_name": "implementer", "status": "waiting"}
        ]
    }

Test Coverage:
1. Returns active agent executions for the job
2. Excludes inactive executions (complete, failed, cancelled, decommissioned) by default
3. Includes inactive executions when include_inactive=True
4. Respects tenant isolation
5. Returns empty list when no teammates found
6. Handles missing job_id gracefully
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
async def other_tenant_key():
    """Generate separate tenant key for isolation tests."""
    return f"tk_other_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_user(db_session, tenant_key):
    """Create test user."""
    user = User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username="test_user_0360",
        email="test_0360@giljoai.com",
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
        name="Test Product 0360",
        description="Test product for team discovery",
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
        name="Test Project 0360",
        description="Test project for team discovery",
        product_id=test_product.id,
        mission="Build authentication system",
        context_budget=150000,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_job(db_session, tenant_key, test_project):
    """Create test agent job."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        mission="Build OAuth2 authentication",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


# ========================================================================
# Tests for get_team_agents()
# ========================================================================


@pytest.mark.asyncio
async def test_get_team_agents_returns_active_teammates(
    db_session, tenant_key, test_job
):
    """Should return all active agent executions for the job."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents

    # Create multiple active executions for the same job
    execution1 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="working",
        agent_name="Orchestrator Instance 1",
    )
    execution2 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="waiting",
        agent_name="Orchestrator Instance 2",
    )
    execution3 = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",        status="blocked",
        agent_name="Backend Implementer",
    )

    db_session.add(execution1)
    db_session.add(execution2)
    db_session.add(execution3)
    await db_session.commit()

    # Call get_team_agents()
    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        include_inactive=False,
    )

    # Assertions
    assert result["success"] is True, f"Expected success, got error: {result.get('error')}"
    assert "team" in result, "Response should contain 'team' key"
    assert len(result["team"]) == 3, f"Expected 3 teammates, got {len(result['team'])}"

    # Verify team members contain required fields
    for member in result["team"]:
        assert "agent_id" in member, "Each team member should have agent_id"
        assert "job_id" in member, "Each team member should have job_id"
        assert "agent_display_name" in member, "Each team member should have agent_display_name"
        assert "status" in member, "Each team member should have status"
        assert member["job_id"] == test_job.job_id, "All members should belong to same job"

    # Verify specific team members
    agent_ids = {m["agent_id"] for m in result["team"]}
    assert execution1.agent_id in agent_ids, "Execution 1 should be in team"
    assert execution2.agent_id in agent_ids, "Execution 2 should be in team"
    assert execution3.agent_id in agent_ids, "Execution 3 should be in team"


@pytest.mark.asyncio
async def test_get_team_agents_excludes_inactive_by_default(
    db_session, tenant_key, test_job
):
    """Completed/decommissioned executions should be filtered by default."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents
    # Create mix of active and inactive executions
    active_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="working",
    )
    completed_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="complete",
        completed_at=datetime.now(timezone.utc),
    )
    decommissioned_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",        status="decommissioned",
        decommissioned_at=datetime.now(timezone.utc),
    )
    failed_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="tester",        status="failed",
        completed_at=datetime.now(timezone.utc),
    )

    db_session.add(active_execution)
    db_session.add(completed_execution)
    db_session.add(decommissioned_execution)
    db_session.add(failed_execution)
    await db_session.commit()

    # Call get_team_agents() without include_inactive
    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
    )

    # Assertions
    assert result["success"] is True
    assert len(result["team"]) == 1, "Should only return active execution"
    assert result["team"][0]["agent_id"] == active_execution.agent_id
    assert result["team"][0]["status"] == "working"

    # Verify inactive executions NOT in results
    returned_agent_ids = {m["agent_id"] for m in result["team"]}
    assert completed_execution.agent_id not in returned_agent_ids
    assert decommissioned_execution.agent_id not in returned_agent_ids
    assert failed_execution.agent_id not in returned_agent_ids


@pytest.mark.asyncio
async def test_get_team_agents_includes_inactive_when_requested(
    db_session, tenant_key, test_job
):
    """include_inactive=True should return all executions."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents
    # Create mix of active and inactive executions
    active_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="working",
    )
    completed_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="complete",
        completed_at=datetime.now(timezone.utc),
    )
    decommissioned_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="implementer",        status="decommissioned",
        decommissioned_at=datetime.now(timezone.utc),
    )

    db_session.add(active_execution)
    db_session.add(completed_execution)
    db_session.add(decommissioned_execution)
    await db_session.commit()

    # Call get_team_agents() with include_inactive=True
    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        include_inactive=True,
    )

    # Assertions
    assert result["success"] is True
    assert len(result["team"]) == 3, "Should return all executions including inactive"

    # Verify all executions present
    returned_agent_ids = {m["agent_id"] for m in result["team"]}
    assert active_execution.agent_id in returned_agent_ids
    assert completed_execution.agent_id in returned_agent_ids
    assert decommissioned_execution.agent_id in returned_agent_ids

    # Verify status fields preserved
    statuses = {m["agent_id"]: m["status"] for m in result["team"]}
    assert statuses[active_execution.agent_id] == "working"
    assert statuses[completed_execution.agent_id] == "complete"
    assert statuses[decommissioned_execution.agent_id] == "decommissioned"


@pytest.mark.asyncio
async def test_get_team_agents_tenant_isolation(
    db_session, tenant_key, other_tenant_key, test_job
):
    """Should only return agents from same tenant."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents
    # Create execution in correct tenant
    same_tenant_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="working",
    )

    # Create job and execution in different tenant
    other_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=other_tenant_key,
        project_id=test_job.project_id,  # Same project, different tenant
        mission="Different tenant mission",
        job_type="orchestrator",
        status="active",
    )
    other_tenant_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=other_job.job_id,
        tenant_key=other_tenant_key,
        agent_display_name="orchestrator",        status="working",
    )

    db_session.add(same_tenant_execution)
    db_session.add(other_job)
    db_session.add(other_tenant_execution)
    await db_session.commit()

    # Call get_team_agents() with original tenant_key
    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
    )

    # Assertions
    assert result["success"] is True
    assert len(result["team"]) == 1, "Should only return same-tenant execution"
    assert result["team"][0]["agent_id"] == same_tenant_execution.agent_id
    assert result["team"][0]["tenant_key"] == tenant_key

    # Verify other tenant execution NOT in results
    returned_agent_ids = {m["agent_id"] for m in result["team"]}
    assert other_tenant_execution.agent_id not in returned_agent_ids


@pytest.mark.asyncio
async def test_get_team_agents_empty_team(
    db_session, tenant_key, test_job
):
    """Should return empty team list when no executions exist."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents

    # Don't create any executions
    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
    )

    # Assertions
    assert result["success"] is True
    assert "team" in result
    assert len(result["team"]) == 0, "Should return empty team list"


@pytest.mark.asyncio
async def test_get_team_agents_missing_job_id(
    tenant_key
):
    """Should handle missing job_id gracefully."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents

    # Call with non-existent job_id
    result = await get_team_agents(
        job_id="non-existent-job-id",
        tenant_key=tenant_key,
    )

    # Assertions - should return empty team, not error
    assert result["success"] is True
    assert "team" in result
    assert len(result["team"]) == 0, "Should return empty team for missing job"


@pytest.mark.asyncio
async def test_get_team_agents_returns_all_required_fields(
    db_session, tenant_key, test_job
):
    """Should return all required fields for each team member."""
    from src.giljo_mcp.tools.agent_coordination import get_team_agents
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",        status="working",
        agent_name="Test Orchestrator",
        progress=50,
        current_task="Analyzing codebase",
    )
    db_session.add(execution)
    await db_session.commit()

    result = await get_team_agents(
        job_id=test_job.job_id,
        tenant_key=tenant_key,
    )

    # Assertions
    assert result["success"] is True
    assert len(result["team"]) == 1

    member = result["team"][0]
    # Required fields
    assert member["agent_id"] == execution.agent_id
    assert member["job_id"] == test_job.job_id
    assert member["agent_display_name"] == "orchestrator"
    assert member["status"] == "working"

    # Optional but useful fields
    assert "agent_name" in member or member.get("agent_name") == "Test Orchestrator"
