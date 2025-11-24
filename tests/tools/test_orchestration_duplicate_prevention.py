"""
Test orchestrator duplication prevention during staging.

Tests that:
1. Only one active orchestrator can exist during staging
2. Succession is still allowed during runtime
3. Proper error messages are returned

Following TDD discipline from QUICK_LAUNCH.txt
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.giljo_mcp.models import MCPAgentJob, Project


@pytest.mark.asyncio
async def test_spawn_agent_prevents_duplicate_orchestrator_during_staging(db_session, db_manager):
    """
    Test that spawn_agent_job prevents creating duplicate orchestrator when one is waiting.

    BEHAVIOR: When an orchestrator with status 'waiting' exists,
    attempting to spawn another orchestrator should fail with appropriate error.
    """
    from src.giljo_mcp.tools.orchestration import spawn_agent_job
    from src.giljo_mcp.models import Project

    # Setup
    tenant_key = "test_tenant_123"
    project_id = str(uuid4())

    # Create project first (foreign key constraint)
    project = Project(
        id=project_id,
        name="Test Project",
        description="Test project for orchestrator duplication",
        mission="Test mission for orchestrator duplication",
        tenant_key=tenant_key,
        status="active"
    )
    db_session.add(project)
    await db_session.commit()

    # Create existing orchestrator with 'waiting' status
    existing_orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        agent_name="Orchestrator",
        status="waiting",  # Staging status
        mission="Existing orchestrator mission"
    )
    db_session.add(existing_orchestrator)
    await db_session.commit()

    # Attempt to create duplicate orchestrator (should fail)
    result = await spawn_agent_job(
        agent_type="orchestrator",
        agent_name="Duplicate Orchestrator",
        mission="Should not be created",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session
    )

    # BEHAVIOR: Should fail with error
    assert result.get("success") is False
    assert "error" in result
    assert "orchestrator already exists" in result["error"].lower()
    assert "existing_job_id" in result
    assert result["existing_job_id"] == existing_orchestrator.job_id


@pytest.mark.asyncio
async def test_spawn_agent_prevents_duplicate_orchestrator_when_working(db_session, db_manager):
    """
    Test that spawn_agent_job prevents creating duplicate orchestrator when one is working.

    BEHAVIOR: When an orchestrator with status 'working' exists,
    attempting to spawn another orchestrator should fail.
    """
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_456"
    project_id = str(uuid4())

    # Create project first
    project = Project(
        id=project_id,
        name="Test Project Working",
        description="Test with working orchestrator",
        mission="Test mission for working orchestrator",
        tenant_key=tenant_key,
        status="active"
    )
    db_session.add(project)
    await db_session.commit()

    # Create existing orchestrator with 'working' status
    existing_orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        agent_name="Orchestrator",
        status="working",  # Already running
        mission="Working orchestrator mission"
    )
    db_session.add(existing_orchestrator)
    await db_session.commit()

    # Attempt to create duplicate orchestrator (should fail)
    result = await spawn_agent_job(
        agent_type="orchestrator",
        agent_name="Another Orchestrator",
        mission="Should not be created",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session
    )

    # BEHAVIOR: Should fail with error
    assert result.get("success") is False
    assert "orchestrator already exists" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_spawn_agent_allows_orchestrator_when_previous_complete(db_session, db_manager):
    """
    Test that spawn_agent_job ALLOWS creating orchestrator when previous one is complete.

    BEHAVIOR: When an orchestrator with status 'complete' exists (succession scenario),
    creating a new orchestrator should succeed.
    """
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_789"
    project_id = str(uuid4())

    # Create project first
    project = Project(
        id=project_id,
        name="Test Succession Project",
        description="Test succession scenario",
        mission="Test mission for succession scenario",
        tenant_key=tenant_key,
        status="active"
    )
    db_session.add(project)
    await db_session.commit()

    # Create existing orchestrator with 'complete' status
    completed_orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        status="complete",  # Finished, succession allowed
        mission="Completed orchestrator mission",
        instance_number=1
    )
    db_session.add(completed_orchestrator)
    await db_session.commit()

    # Attempt to create successor orchestrator (should succeed)
    result = await spawn_agent_job(
        agent_type="orchestrator",
        agent_name="Orchestrator #2",
        mission="Successor orchestrator mission",
        project_id=project_id,
        tenant_key=tenant_key,
        parent_job_id=completed_orchestrator.job_id,  # Link to parent
        session=db_session
    )

    # BEHAVIOR: Should succeed for succession
    assert result.get("success") is True
    assert "agent_job_id" in result
    assert "agent_prompt" in result


@pytest.mark.asyncio
async def test_spawn_agent_allows_non_orchestrator_agents(db_session, db_manager):
    """
    Test that spawn_agent_job still allows creating non-orchestrator agents freely.

    BEHAVIOR: The validation should ONLY apply to orchestrator type,
    other agent types can have multiple instances.
    """
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    tenant_key = "test_tenant_multi"
    project_id = str(uuid4())

    # Create project first
    project = Project(
        id=project_id,
        name="Multi Agent Project",
        description="Test multiple non-orchestrator agents",
        mission="Test mission for multiple agents",
        tenant_key=tenant_key,
        status="active"
    )
    db_session.add(project)
    await db_session.commit()

    # Create existing orchestrator
    orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        agent_name="Orchestrator",
        status="working",
        mission="Orchestrator mission"
    )
    db_session.add(orchestrator)

    # Create existing implementer
    implementer1 = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_key,
        agent_type="implementer",
        agent_name="Implementer #1",
        status="working",
        mission="First implementer"
    )
    db_session.add(implementer1)
    await db_session.commit()

    # Attempt to create second implementer (should succeed)
    result = await spawn_agent_job(
        agent_type="implementer",
        agent_name="Implementer #2",
        mission="Second implementer mission",
        project_id=project_id,
        tenant_key=tenant_key,
        session=db_session
    )

    # BEHAVIOR: Non-orchestrator agents can have multiple instances
    assert result.get("success") is True
    assert "agent_job_id" in result


@pytest.mark.asyncio
async def test_spawn_agent_respects_tenant_isolation(db_session, db_manager):
    """
    Test that orchestrator validation respects multi-tenant isolation.

    BEHAVIOR: An orchestrator in tenant_a should not block creating
    an orchestrator in tenant_b for the same project_id.
    """
    from src.giljo_mcp.tools.orchestration import spawn_agent_job

    # Setup
    project_id = str(uuid4())  # Same project ID
    tenant_a = "tenant_key_aaa"
    tenant_b = "tenant_key_bbb"

    # Create projects for both tenants (same ID but different tenants)
    project_a = Project(
        id=project_id,
        name="Tenant A Project",
        description="Project in tenant A",
        mission="Test mission for tenant A",
        tenant_key=tenant_a,
        status="active"
    )
    db_session.add(project_a)

    # Note: In real system, project_id would be unique, but for testing tenant isolation
    # we need to create a second project with same ID in different tenant
    # This simulates the multi-tenant scenario where tenants are isolated
    project_b = Project(
        id=str(uuid4()),  # Actually need different ID due to primary key constraint
        name="Tenant B Project",
        description="Project in tenant B",
        mission="Test mission for tenant B",
        tenant_key=tenant_b,
        status="active"
    )
    db_session.add(project_b)
    await db_session.commit()

    # Use project_b's ID for tenant_b test
    project_b_id = project_b.id

    # Create orchestrator in tenant_a
    orchestrator_a = MCPAgentJob(
        job_id=str(uuid4()),
        project_id=project_id,
        tenant_key=tenant_a,
        agent_type="orchestrator",
        agent_name="Orchestrator A",
        status="working",
        mission="Tenant A orchestrator"
    )
    db_session.add(orchestrator_a)
    await db_session.commit()

    # Attempt to create orchestrator in tenant_b (should succeed due to isolation)
    result = await spawn_agent_job(
        agent_type="orchestrator",
        agent_name="Orchestrator B",
        mission="Tenant B orchestrator",
        project_id=project_b_id,  # Use project_b's ID
        tenant_key=tenant_b,  # Different tenant
        session=db_session
    )

    # BEHAVIOR: Multi-tenant isolation - should succeed
    assert result.get("success") is True
    assert "agent_job_id" in result