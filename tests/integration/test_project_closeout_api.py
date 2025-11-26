"""
Integration tests for Project Closeout API (Handover 0073).

Tests:
- GET /api/projects/{project_id}/can-close - Check closeout readiness
- POST /api/projects/{project_id}/generate-closeout - Generate closeout prompt
- POST /api/projects/{project_id}/complete - Complete project
- Closeout workflow (can-close → generate → complete)
- Multi-tenant isolation
- WebSocket events
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project, User


@pytest.mark.asyncio
async def test_can_close_all_agents_complete(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test can-close when all agents are complete."""
    # Create project
    project = Project(
        id="closeout-proj-001",
        tenant_key=test_user.tenant_key,
        name="Closeout Project",
        mission="Build feature",
        description="Feature development",
        status="active",
    )
    db_session.add(project)

    # Create completed agents
    for i in range(3):
        agent = MCPAgentJob(
            job_id=f"complete-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission=f"Implement feature {i}",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response
    assert data["can_close"] is True
    assert data["all_agents_finished"] is True
    assert data["summary"] is not None
    assert "3 successful agents" in data["summary"]

    # Validate agent status breakdown
    assert data["agent_statuses"]["complete"] == 3
    assert data["agent_statuses"]["failed"] == 0
    assert data["agent_statuses"]["active"] == 0
    assert data["agent_statuses"]["blocked"] == 0


@pytest.mark.asyncio
async def test_can_close_some_agents_failed(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test can-close with mix of complete and failed agents."""
    project = Project(
        id="mixed-proj",
        tenant_key=test_user.tenant_key,
        name="Mixed Project",
        mission="Build app",
        description="App development",
        status="active",
    )
    db_session.add(project)

    # Create mix of agents
    for i in range(2):
        agent = MCPAgentJob(
            job_id=f"success-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission=f"Implement feature {i}",
            status="complete",
        )
        db_session.add(agent)

    for i in range(1):
        agent = MCPAgentJob(
            job_id=f"failed-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="tester",
            mission=f"Test feature {i}",
            status="failed",
            block_reason="Dependencies missing",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["can_close"] is True
    assert data["agent_statuses"]["complete"] == 2
    assert data["agent_statuses"]["failed"] == 1
    assert "2 successful agents" in data["summary"]
    assert "1 failed agents" in data["summary"]


@pytest.mark.asyncio
async def test_can_close_agents_still_working(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test can-close when agents are still active."""
    project = Project(
        id="active-proj",
        tenant_key=test_user.tenant_key,
        name="Active Project",
        mission="Build feature",
        description="Feature dev",
        status="active",
    )
    db_session.add(project)

    # Create active agents
    for i in range(2):
        agent = MCPAgentJob(
            job_id=f"working-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission="Implement",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["can_close"] is False
    assert data["all_agents_finished"] is False
    assert data["summary"] is None
    assert data["agent_statuses"]["active"] == 2


@pytest.mark.asyncio
async def test_can_close_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test can-close with non-existent project."""
    response = await client.get("/api/v1/projects/nonexistent-proj/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_closeout_prompt(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test closeout prompt generation."""
    # Create project with metadata
    project = Project(
        id="gen-closeout-proj",
        tenant_key=test_user.tenant_key,
        name="Generated Closeout",
        mission="Build REST API",
        description="API development",
        status="active",
        meta_data={"path": "/home/user/projects/api-project", "git_branch": "feature/api-endpoints"},
    )
    db_session.add(project)

    # Create completed agents
    for i in range(2):
        agent = MCPAgentJob(
            job_id=f"closeout-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="backend-dev",
            mission="Implement endpoints",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Generate closeout prompt
    response = await client.post(f"/api/v1/projects/{project.id}/generate-closeout", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "prompt" in data
    assert "checklist" in data
    assert "project_name" in data
    assert "agent_summary" in data

    # Validate prompt content
    prompt = data["prompt"]
    assert "#!/bin/bash" in prompt
    assert "Generated Closeout" in prompt
    assert "/home/user/projects/api-project" in prompt
    assert "git status" in prompt
    assert "git add ." in prompt
    assert 'git commit -m "Project complete: Generated Closeout' in prompt
    assert "git push origin feature/api-endpoints" in prompt
    assert "PROJECT_SUMMARY.md" in prompt
    assert "Build REST API" in prompt

    # Validate checklist
    assert len(data["checklist"]) >= 5
    assert any("Review" in item for item in data["checklist"])
    assert any("Commit" in item for item in data["checklist"])

    # Verify prompt stored in database
    await db_session.refresh(project)
    assert project.closeout_prompt == prompt


@pytest.mark.asyncio
async def test_complete_project_closeout(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test project completion with closeout."""
    # Create project
    project = Project(
        id="complete-proj",
        tenant_key=test_user.tenant_key,
        name="Complete Project",
        mission="Build feature",
        description="Feature dev",
        status="active",
    )
    db_session.add(project)

    # Create agents
    agent_count = 4
    for i in range(agent_count):
        agent = MCPAgentJob(
            job_id=f"final-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission="Develop",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Complete project
    response = await client.post(
        f"/api/v1/projects/{project.id}/complete", json={"confirm_closeout": True}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response
    assert data["success"] is True
    assert "completed_at" in data
    assert data["retired_agents"] == agent_count

    # Verify project status updated
    await db_session.refresh(project)
    assert project.status == "completed"
    assert project.completed_at is not None
    assert project.closeout_executed_at is not None


@pytest.mark.asyncio
async def test_complete_project_without_confirmation(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test project completion fails without confirmation."""
    project = Project(
        id="unconfirmed-proj",
        tenant_key=test_user.tenant_key,
        name="Unconfirmed",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # Try completing without confirmation
    response = await client.post(
        f"/api/v1/projects/{project.id}/complete", json={"confirm_closeout": False}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "confirm" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_closeout_workflow_end_to_end(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test complete closeout workflow: can-close → generate → complete."""
    # Setup project with completed agents
    project = Project(
        id="workflow-proj",
        tenant_key=test_user.tenant_key,
        name="Workflow Project",
        mission="Full stack app",
        description="Complete workflow test",
        status="active",
        meta_data={"path": "/workspace/app"},
    )
    db_session.add(project)

    for i in range(3):
        agent = MCPAgentJob(
            job_id=f"workflow-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission=f"Implement module {i}",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Step 1: Check can-close
    response1 = await client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)
    assert response1.status_code == status.HTTP_200_OK
    assert response1.json()["can_close"] is True

    # Step 2: Generate closeout prompt
    response2 = await client.post(f"/api/v1/projects/{project.id}/generate-closeout", headers=auth_headers)
    assert response2.status_code == status.HTTP_200_OK
    assert "prompt" in response2.json()

    # Step 3: Complete project
    response3 = await client.post(
        f"/api/v1/projects/{project.id}/complete", json={"confirm_closeout": True}, headers=auth_headers
    )
    assert response3.status_code == status.HTTP_200_OK
    assert response3.json()["success"] is True

    # Verify final state
    await db_session.refresh(project)
    assert project.status == "completed"
    assert project.orchestrator_summary is not None
    assert project.closeout_prompt is not None
    assert project.closeout_executed_at is not None


@pytest.mark.asyncio
async def test_closeout_multi_tenant_isolation_can_close(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in can-close endpoint."""
    project = Project(
        id="tenant-closeout-1",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # User 2 tries to check user 1's project
    response = await client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers_user_2)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_closeout_multi_tenant_isolation_generate(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in generate-closeout endpoint."""
    project = Project(
        id="tenant-closeout-2",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # User 2 tries to generate closeout for user 1's project
    response = await client.post(f"/api/v1/projects/{project.id}/generate-closeout", headers=auth_headers_user_2)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_closeout_multi_tenant_isolation_complete(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in complete endpoint."""
    project = Project(
        id="tenant-closeout-3",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # User 2 tries to complete user 1's project
    response = await client.post(
        f"/api/v1/projects/{project.id}/complete", json={"confirm_closeout": True}, headers=auth_headers_user_2
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_closeout_data_endpoint_success(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """GET /closeout returns checklist and prompt for the project."""
    project = Project(
        id="closeout-data-1",
        tenant_key=test_user.tenant_key,
        name="Closeout Data Project",
        mission="Complete the data pipeline",
        description="Data pipeline work",
        status="active",
    )
    db_session.add(project)

    # Mix of agent statuses
    db_session.add(
        MCPAgentJob(
            job_id="closeout-complete-1",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="developer",
            mission="Implement",
            status="complete",
        )
    )
    db_session.add(
        MCPAgentJob(
            job_id="closeout-working-1",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="analyst",
            mission="Analyze",
            status="working",
        )
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/closeout", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["project_id"] == project.id
    assert data["project_name"] == project.name
    assert "checklist" in data and len(data["checklist"]) >= 3
    assert "close_project_and_update_memory" in data["closeout_prompt"]
    assert data["agent_count"] == 2
    assert data["all_agents_complete"] is False


@pytest.mark.asyncio
async def test_get_closeout_data_endpoint_not_found(client: AsyncClient, auth_headers: dict):
    """Closeout data returns 404 for missing project."""
    response = await client.get("/api/v1/projects/does-not-exist/closeout", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_closeout_data_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers_user_2: dict,
):
    """Closeout data enforces tenant isolation."""
    project = Project(
        id="closeout-tenant-1",
        tenant_key=test_user.tenant_key,
        name="Tenant Protected Project",
        mission="Isolation mission",
        description="Isolation details",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/closeout", headers=auth_headers_user_2)

    assert response.status_code == status.HTTP_404_NOT_FOUND
