"""
Simplified tests for Execution Prompt API Endpoint (Handover 0109 - Agent 3).

Tests core functionality without complex fixture dependencies.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project, User


async def get_test_user(db_session):
    """Get test user created by auth_headers fixture."""
    stmt = select(User).where(User.username == "test_user")
    result = await db_session.execute(stmt)
    return result.scalars().first()


@pytest.mark.asyncio
async def test_generate_execution_prompt_multi_terminal_mode(
    api_client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test execution prompt generation in multi-terminal mode."""
    test_user = await get_test_user(db_session)

    # Create test project
    project = Project(
        id="test-proj-exec-mt",
        tenant_key=test_user.tenant_key,
        name="Multi-Terminal Test",
        mission="Test multi-terminal mode",
        description="Test project",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator
    orchestrator = MCPAgentJob(
        job_id="orch-mt-test",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate",
        status="working",
    )
    db_session.add(orchestrator)

    # Create 3 specialist agents
    for i in range(3):
        agent = MCPAgentJob(
            job_id=f"agent-mt-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="implementer",
            mission=f"Agent {i}",
            status="waiting",
        )
        db_session.add(agent)

    await db_session.commit()

    # Test endpoint
    response = await api_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode=false",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response
    assert data["success"] is True
    assert data["orchestrator_job_id"] == orchestrator.job_id
    assert data["project_id"] == project.id
    assert data["claude_code_mode"] is False
    assert data["agent_count"] == 3
    assert "MULTI-TERMINAL MODE" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_execution_prompt_claude_code_mode(
    api_client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test execution prompt generation in Claude Code mode."""
    test_user = await get_test_user(db_session)

    # Create test project
    project = Project(
        id="test-proj-exec-cc",
        tenant_key=test_user.tenant_key,
        name="Claude Code Test",
        mission="Test Claude Code mode",
        description="Test project",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator
    orchestrator = MCPAgentJob(
        job_id="orch-cc-test",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate",
        status="working",
    )
    db_session.add(orchestrator)

    await db_session.commit()

    # Test endpoint
    response = await api_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode=true",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response
    assert data["success"] is True
    assert data["claude_code_mode"] is True
    assert "CLAUDE CODE SUBAGENT MODE" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_execution_prompt_not_found(
    api_client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test 404 when orchestrator doesn't exist."""
    response = await api_client.get(
        "/api/v1/prompts/execution/non-existent-orch",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_execution_prompt_wrong_type(
    api_client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test error when job is not orchestrator type."""
    test_user = await get_test_user(db_session)

    project = Project(
        id="test-proj-exec-wt",
        tenant_key=test_user.tenant_key,
        name="Wrong Type Test",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)

    # Create implementer (not orchestrator)
    implementer = MCPAgentJob(
        job_id="impl-not-orch",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="implementer",  # Wrong type
        mission="Implement",
        status="working",
    )
    db_session.add(implementer)

    await db_session.commit()

    response = await api_client.get(
        f"/api/v1/prompts/execution/{implementer.job_id}",
        headers=auth_headers,
    )

    # Should get 404 because query filters by agent_type=orchestrator
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_execution_prompt_unauthenticated(
    api_client: AsyncClient
):
    """Test 401 when not authenticated."""
    response = await api_client.get("/api/v1/prompts/execution/some-orch")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
