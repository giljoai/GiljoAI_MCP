"""
Integration tests for Prompt Generation API (Handover 0073).

Tests:
- GET /api/prompts/orchestrator/{tool} - Orchestrator prompt generation
- GET /api/prompts/agent/{agent_id} - Agent prompt generation
- Multi-tenant isolation
- Authentication/authorization
- Error handling
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest.mark.asyncio
async def test_generate_orchestrator_prompt_claude_code(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test orchestrator prompt generation for Claude Code."""
    # Create test project
    project = Project(
        id="test-proj-123",
        tenant_key=test_user.tenant_key,
        name="Test Project",
        mission="Build a REST API",
        description="Test project description",
        status="active",
        meta_data={"path": "/home/user/projects/test-project"},
    )
    db_session.add(project)

    # Create test agents
    for i in range(3):
        agent = AgentExecution(
            job_id=f"agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="implementer",
            mission=f"Implement feature {i}",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # Generate prompt
    response = await client.get(f"/api/prompts/orchestrator/claude-code?project_id={project.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "prompt" in data
    assert "tool" in data
    assert "instructions" in data
    assert "project_name" in data
    assert "agent_count" in data

    # Validate content
    assert data["tool"] == "claude-code"
    assert data["project_name"] == "Test Project"
    assert data["agent_count"] == 3
    assert "claude-code orchestrate" in data["prompt"]
    assert f"--project-id={project.id}" in data["prompt"]
    assert '--mission="Build a REST API"' in data["prompt"]
    assert "--agents=3" in data["prompt"]
    assert "/home/user/projects/test-project" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_orchestrator_prompt_codex_gemini(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test orchestrator prompt generation for Codex/Gemini."""
    # Create test project
    project = Project(
        id="test-proj-456",
        tenant_key=test_user.tenant_key,
        name="API Project",
        mission="Create microservices",
        description="Microservices project",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # Generate prompt
    response = await client.get(f"/api/prompts/orchestrator/codex-gemini?project_id={project.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate Codex/Gemini format
    assert data["tool"] == "codex-gemini"
    assert "export PROJECT_ID=" in data["prompt"]
    assert "export MISSION=" in data["prompt"]
    assert "export AGENTS=" in data["prompt"]
    assert "codex orchestrate" in data["prompt"]
    assert "gemini orchestrate" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_orchestrator_prompt_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test orchestrator prompt generation with non-existent project."""
    response = await client.get(
        "/api/prompts/orchestrator/claude-code?project_id=nonexistent-123", headers=auth_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_orchestrator_prompt_unauthorized(client: AsyncClient):
    """Test orchestrator prompt generation without authentication."""
    response = await client.get("/api/prompts/orchestrator/claude-code?project_id=test-123")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_generate_agent_prompt(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test agent prompt generation."""
    # Create test project
    project = Project(
        id="test-proj-789",
        tenant_key=test_user.tenant_key,
        name="Backend Project",
        mission="Build backend services",
        description="Backend development",
        status="active",
        meta_data={"path": "/home/user/backend"},
    )
    db_session.add(project)

    # Create test agent
    agent = AgentExecution(
        job_id="agent-backend-001",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_display_name="backend-developer",
        agent_name="Backend API Agent",
        tool_type="claude-code",
        mission="Implement REST API endpoints with FastAPI and PostgreSQL database integration",
        status="preparing",
    )
    db_session.add(agent)
    await db_session.commit()

    # Generate prompt
    response = await client.get(f"/api/prompts/agent/{agent.job_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "prompt" in data
    assert "agent_id" in data
    assert "agent_name" in data
    assert "agent_display_name" in data
    assert "tool_type" in data
    assert "instructions" in data
    assert "mission_preview" in data

    # Validate content
    assert data["agent_id"] == "agent-backend-001"
    assert data["agent_name"] == "Backend API Agent"
    assert data["agent_display_name"] == "backend-developer"
    assert data["tool_type"] == "claude-code"
    assert "Implement REST API endpoints" in data["mission_preview"]

    # Validate prompt format
    prompt = data["prompt"]
    assert "# Agent: Backend API Agent" in prompt
    assert "# Type: backend-developer" in prompt
    assert "# Tool: claude-code" in prompt
    assert "export AGENT_ID=agent-backend-001" in prompt
    assert "export AGENT_TYPE=backend-developer" in prompt
    assert f"export PROJECT_ID={project.id}" in prompt
    assert "mkdir -p .missions" in prompt
    assert f"cat > .missions/{agent.job_id}.md" in prompt
    assert "claude-code-agent execute" in prompt


@pytest.mark.asyncio
async def test_generate_agent_prompt_agent_not_found(client: AsyncClient, auth_headers: dict):
    """Test agent prompt generation with non-existent agent."""
    response = await client.get("/api/prompts/agent/nonexistent-agent-999", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_multi_tenant_isolation_orchestrator(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in orchestrator prompt generation."""
    # Create project for user 1
    project = Project(
        id="tenant1-proj",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build app",
        description="Tenant 1 app",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # User 2 tries to access user 1's project
    response = await client.get(
        f"/api/prompts/orchestrator/claude-code?project_id={project.id}", headers=auth_headers_user_2
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_multi_tenant_isolation_agent(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in agent prompt generation."""
    # Create agent for user 1
    agent = AgentExecution(
        job_id="tenant1-agent",
        tenant_key=test_user.tenant_key,
        agent_display_name="developer",
        mission="Build feature",
        status="working",
    )
    db_session.add(agent)
    await db_session.commit()

    # User 2 tries to access user 1's agent
    response = await client.get(f"/api/prompts/agent/{agent.job_id}", headers=auth_headers_user_2)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_agent_prompt_universal_tool_type(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test agent prompt generation with universal tool type."""
    agent = AgentExecution(
        job_id="universal-agent-001",
        tenant_key=test_user.tenant_key,
        agent_display_name="tester",
        tool_type="universal",
        mission="Write comprehensive tests",
        status="working",
    )
    db_session.add(agent)
    await db_session.commit()

    response = await client.get(f"/api/prompts/agent/{agent.job_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tool_type"] == "universal"
    assert "universal-agent execute" in data["prompt"]


@pytest.mark.asyncio
async def test_agent_prompt_with_long_mission(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test agent prompt generation with long mission (preview truncation)."""
    long_mission = "A" * 500  # 500 characters
    agent = AgentExecution(
        job_id="long-mission-agent",
        tenant_key=test_user.tenant_key,
        agent_display_name="implementer",
        mission=long_mission,
        status="working",
    )
    db_session.add(agent)
    await db_session.commit()

    response = await client.get(f"/api/prompts/agent/{agent.job_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Mission preview should be truncated to 200 chars + "..."
    assert len(data["mission_preview"]) == 203
    assert data["mission_preview"].endswith("...")


