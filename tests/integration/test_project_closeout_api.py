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

from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


def _completion_payload(confirm_closeout: bool = True) -> dict:
    return {
        "summary": "Completed project closeout with key outcomes recorded for 360 memory.",
        "key_outcomes": ["All agents completed work", "Closeout checklist executed"],
        "decisions_made": ["Chose standard closeout workflow"],
        "confirm_closeout": confirm_closeout,
    }


@pytest.mark.asyncio
async def test_can_close_all_agents_complete(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
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
        agent = AgentExecution(
            job_id=f"complete-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission=f"Implement feature {i}",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await async_client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response
    assert data["can_close"] is True
    assert data["all_agents_finished"] is True
    assert data["summary"] is not None
    assert "3 successful agents" in data["summary"]

    # Validate agent status breakdown
    assert data["agent_statuses"]["complete"] == 3
    assert data["agent_statuses"]["blocked"] == 0
    assert data["agent_statuses"]["active"] == 0
    assert data["agent_statuses"]["blocked"] == 0


@pytest.mark.asyncio
async def test_can_close_some_agents_failed(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
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
        agent = AgentExecution(
            job_id=f"success-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission=f"Implement feature {i}",
            status="complete",
        )
        db_session.add(agent)

    for i in range(1):
        agent = AgentExecution(
            job_id=f"failed-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="tester",
            mission=f"Test feature {i}",
            status="blocked",
            block_reason="Dependencies missing",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await async_client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["can_close"] is True
    assert data["agent_statuses"]["complete"] == 2
    assert data["agent_statuses"]["blocked"] == 1
    assert "2 successful agents" in data["summary"]
    assert "1 blocked agents" in data["summary"]


@pytest.mark.asyncio
async def test_can_close_agents_still_working(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
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
        agent = AgentExecution(
            job_id=f"working-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission="Implement",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # Check can-close
    response = await async_client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["can_close"] is False
    assert data["all_agents_finished"] is False
    assert data["summary"] is None
    assert data["agent_statuses"]["active"] == 2


@pytest.mark.asyncio
async def test_can_close_project_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test can-close with non-existent project."""
    response = await async_client.get("/api/v1/projects/nonexistent-proj/can-close", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_closeout_prompt(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
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
        agent = AgentExecution(
            job_id=f"closeout-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="backend-dev",
            mission="Implement endpoints",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Generate closeout prompt
    response = await async_client.post(f"/api/v1/projects/{project.id}/generate-closeout", headers=auth_headers)

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
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, test_product, auth_headers: dict
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
        product_id=test_product.id,
    )
    db_session.add(project)

    # Create agents
    agent_count = 4
    for i in range(agent_count):
        agent = AgentExecution(
            job_id=f"final-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission="Develop",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Complete project
    response = await async_client.post(
        f"/api/v1/projects/{project.id}/complete", json=_completion_payload(), headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response
    assert data["success"] is True
    assert "completed_at" in data
    assert data["memory_updated"] is True
    assert data["sequence_number"] == 1
    assert data["git_commits_count"] == 0

    # Verify project status updated
    await db_session.refresh(project)
    assert project.status == "completed"
    assert project.completed_at is not None
    assert project.closeout_executed_at is not None


@pytest.mark.asyncio
async def test_complete_project_without_confirmation(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
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
    response = await async_client.post(
        f"/api/v1/projects/{project.id}/complete",
        json=_completion_payload(confirm_closeout=False),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "confirm" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_closeout_workflow_end_to_end(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, test_product, auth_headers: dict
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
        product_id=test_product.id,
    )
    db_session.add(project)

    for i in range(3):
        agent = AgentExecution(
            job_id=f"workflow-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission=f"Implement module {i}",
            status="complete",
        )
        db_session.add(agent)

    await db_session.commit()

    # Step 1: Check can-close
    response1 = await async_client.get(f"/api/v1/projects/{project.id}/can-close", headers=auth_headers)
    assert response1.status_code == status.HTTP_200_OK
    assert response1.json()["can_close"] is True

    # Step 2: Generate closeout prompt
    response2 = await async_client.post(f"/api/v1/projects/{project.id}/generate-closeout", headers=auth_headers)
    assert response2.status_code == status.HTTP_200_OK
    assert "prompt" in response2.json()

    # Step 3: Complete project
    response3 = await async_client.post(
        f"/api/v1/projects/{project.id}/complete", json=_completion_payload(), headers=auth_headers
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
    authed_client_user_2: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
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
    response = await authed_client_user_2.get(f"/api/v1/projects/{project.id}/can-close")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_closeout_multi_tenant_isolation_generate(
    authed_client_user_2: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
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
    response = await authed_client_user_2.post(f"/api/v1/projects/{project.id}/generate-closeout")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_closeout_multi_tenant_isolation_complete(
    authed_client_user_2: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    test_product,
):
    """Test multi-tenant isolation in complete endpoint."""
    project = Project(
        id="tenant-closeout-3",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build",
        description="Test",
        status="active",
        product_id=test_product.id,
    )
    db_session.add(project)
    await db_session.commit()

    # User 2 tries to complete user 1's project
    response = await authed_client_user_2.post(
        f"/api/v1/projects/{project.id}/complete",
        json=_completion_payload(),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_closeout_data_endpoint_success(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """GET /closeout returns basic project metadata for closeout."""
    project = Project(
        id="closeout-data-1",
        tenant_key=test_user.tenant_key,
        name="Closeout Data Project",
        mission="Complete the data pipeline",
        description="Data pipeline work",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    # Mix of agent statuses
    job1 = AgentJob(
        job_id="closeout-complete-job-1",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        job_type="developer",
        mission="Implement",
    )
    db_session.add(job1)
    db_session.add(
        AgentExecution(
            job_id=job1.job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="developer",
            status="complete",
        )
    )

    job2 = AgentJob(
        job_id="closeout-working-job-1",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        job_type="analyst",
        mission="Analyze",
    )
    db_session.add(job2)
    db_session.add(
        AgentExecution(
            job_id=job2.job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="analyst",
            status="working",
        )
    )
    await db_session.commit()

    response = await async_client.get(f"/api/v1/projects/{project.id}/closeout", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["project_id"] == project.id
    assert data["project_name"] == project.name
    assert data["agent_count"] == 2
    assert data["completed_agents"] == 1
    assert data["blocked_agents"] == 0
    assert data["all_agents_complete"] is False
    assert data["has_blocked_agents"] is False


@pytest.mark.asyncio
async def test_get_closeout_data_endpoint_not_found(async_client: AsyncClient, auth_headers: dict):
    """Closeout data returns 404 for missing project."""
    response = await async_client.get("/api/v1/projects/does-not-exist/closeout", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_closeout_data_tenant_isolation(
    authed_client_user_2: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
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

    response = await authed_client_user_2.get(f"/api/v1/projects/{project.id}/closeout")

    assert response.status_code == status.HTTP_404_NOT_FOUND
