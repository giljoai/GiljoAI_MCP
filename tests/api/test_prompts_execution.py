"""
Integration tests for Execution Prompt API Endpoint (Handover 0109 - Agent 3).

Tests:
- GET /api/v1/prompts/execution/{orchestrator_job_id} - Execution prompt generation
- Claude Code mode vs Multi-Terminal mode
- Multi-tenant isolation
- Authentication/authorization
- Error handling (404, 403, validation)
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project, User


@pytest.mark.asyncio
async def test_generate_execution_prompt_multi_terminal_mode(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test execution prompt generation in multi-terminal mode (claude_code_mode=false)."""
    # Create test project
    project = Project(
        id="test-proj-exec-1",
        tenant_key=test_user.tenant_key,
        name="Test Execution Project",
        mission="Build a REST API",
        description="Test project description",
        status="active",
        meta_data={"path": "/home/user/projects/test-project"},
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = MCPAgentJob(
        job_id="orch-exec-1",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate project execution",
        status="working",
        tool_type="claude-code",
    )
    db_session.add(orchestrator)

    # Create 3 specialist agent jobs
    agent_types = ["implementer", "tester", "reviewer"]
    for i, agent_type in enumerate(agent_types):
        agent = MCPAgentJob(
            job_id=f"agent-exec-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type=agent_type,
            agent_name=f"{agent_type.title()} #1",
            mission=f"Perform {agent_type} tasks",
            status="waiting",
            tool_type="claude-code",
        )
        db_session.add(agent)

    await db_session.commit()

    # Generate execution prompt (multi-terminal mode)
    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode=false",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert data["success"] is True
    assert data["orchestrator_job_id"] == orchestrator.job_id
    assert data["project_id"] == project.id
    assert data["project_name"] == project.name
    assert data["claude_code_mode"] is False
    assert data["agent_count"] == 3
    assert "prompt" in data
    assert isinstance(data["estimated_tokens"], int)
    assert data["estimated_tokens"] > 0

    # Validate prompt content
    prompt = data["prompt"]
    assert "PROJECT EXECUTION PHASE - MULTI-TERMINAL MODE" in prompt
    assert project.name in prompt
    assert "3 specialist agents" in prompt or "3 agents" in prompt
    assert "Terminal 1:" in prompt  # Multi-terminal instructions
    assert orchestrator.job_id in prompt  # Orchestrator ID reference


@pytest.mark.asyncio
async def test_generate_execution_prompt_claude_code_mode(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test execution prompt generation in Claude Code subagent mode (claude_code_mode=true)."""
    # Create test project
    project = Project(
        id="test-proj-exec-2",
        tenant_key=test_user.tenant_key,
        name="Claude Code Project",
        mission="Implement user authentication",
        description="Test project description",
        status="active",
        meta_data={"path": "/home/user/projects/auth-project"},
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = MCPAgentJob(
        job_id="orch-exec-2",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate authentication implementation",
        status="working",
        tool_type="claude-code",
    )
    db_session.add(orchestrator)

    # Create 5 specialist agent jobs
    agent_types = ["architect", "implementer", "tester", "reviewer", "documenter"]
    for i, agent_type in enumerate(agent_types):
        agent = MCPAgentJob(
            job_id=f"agent-cc-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type=agent_type,
            agent_name=f"{agent_type.title()} #1",
            mission=f"Perform {agent_type} tasks",
            status="waiting",
            tool_type="claude-code",
        )
        db_session.add(agent)

    await db_session.commit()

    # Generate execution prompt (Claude Code mode)
    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode=true",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert data["success"] is True
    assert data["orchestrator_job_id"] == orchestrator.job_id
    assert data["project_id"] == project.id
    assert data["project_name"] == project.name
    assert data["claude_code_mode"] is True
    assert data["agent_count"] == 5
    assert "prompt" in data
    assert isinstance(data["estimated_tokens"], int)

    # Validate prompt content
    prompt = data["prompt"]
    assert "PROJECT EXECUTION PHASE - CLAUDE CODE SUBAGENT MODE" in prompt
    assert project.name in prompt
    assert "5 specialist agents" in prompt or "5 agents" in prompt
    assert "@" in prompt  # Subagent mention syntax
    assert orchestrator.job_id in prompt


@pytest.mark.asyncio
async def test_generate_execution_prompt_default_mode(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test execution prompt generation with default mode (should be multi-terminal)."""
    # Create test project
    project = Project(
        id="test-proj-exec-3",
        tenant_key=test_user.tenant_key,
        name="Default Mode Project",
        mission="Test default mode",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = MCPAgentJob(
        job_id="orch-exec-3",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate default mode",
        status="working",
    )
    db_session.add(orchestrator)

    await db_session.commit()

    # Generate execution prompt (no mode specified - should default to false)
    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should default to multi-terminal mode
    assert data["claude_code_mode"] is False
    assert "MULTI-TERMINAL MODE" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_execution_prompt_orchestrator_not_found(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test 404 error when orchestrator job doesn't exist."""
    non_existent_id = "non-existent-orch-id"

    response = await client.get(
        f"/api/v1/prompts/execution/{non_existent_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_generate_execution_prompt_wrong_agent_type(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test error when job is not an orchestrator type."""
    # Create test project
    project = Project(
        id="test-proj-exec-4",
        tenant_key=test_user.tenant_key,
        name="Wrong Type Project",
        mission="Test wrong type",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    # Create non-orchestrator job (implementer)
    implementer = MCPAgentJob(
        job_id="impl-not-orch",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="implementer",  # NOT orchestrator
        agent_name="Implementer #1",
        mission="Implement features",
        status="working",
    )
    db_session.add(implementer)

    await db_session.commit()

    # Try to generate execution prompt for non-orchestrator
    response = await client.get(
        f"/api/v1/prompts/execution/{implementer.job_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "orchestrator" in data["detail"].lower()


@pytest.mark.asyncio
async def test_generate_execution_prompt_multi_tenant_isolation(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test multi-tenant isolation - user cannot access other tenant's orchestrator."""
    # Create project and orchestrator for DIFFERENT tenant
    other_tenant_key = "other-tenant-key-123"

    project = Project(
        id="test-proj-exec-5",
        tenant_key=other_tenant_key,  # Different tenant
        name="Other Tenant Project",
        mission="Test isolation",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    orchestrator = MCPAgentJob(
        job_id="orch-other-tenant",
        tenant_key=other_tenant_key,  # Different tenant
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Other Orchestrator",
        mission="Other tenant mission",
        status="working",
    )
    db_session.add(orchestrator)

    await db_session.commit()

    # Try to access other tenant's orchestrator
    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers,
    )

    # Should get 404 (not 403) to avoid leaking existence
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_execution_prompt_no_agents(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test execution prompt generation when no specialist agents exist."""
    # Create test project
    project = Project(
        id="test-proj-exec-6",
        tenant_key=test_user.tenant_key,
        name="No Agents Project",
        mission="Test with no agents",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator job only (no specialist agents)
    orchestrator = MCPAgentJob(
        job_id="orch-no-agents",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Orchestrate with no agents",
        status="working",
    )
    db_session.add(orchestrator)

    await db_session.commit()

    # Generate execution prompt
    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should succeed but indicate no agents
    assert data["agent_count"] == 0
    assert "0 agents" in data["prompt"] or "No specialist agents" in data["prompt"]


@pytest.mark.asyncio
async def test_generate_execution_prompt_unauthenticated(
    client: AsyncClient, db_session: AsyncSession
):
    """Test 401 error when not authenticated."""
    response = await client.get("/api/v1/prompts/execution/some-orch-id")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_generate_execution_prompt_token_estimation(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test that token estimation is reasonable."""
    # Create test project
    project = Project(
        id="test-proj-exec-7",
        tenant_key=test_user.tenant_key,
        name="Token Test Project",
        mission="Test token estimation",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator
    orchestrator = MCPAgentJob(
        job_id="orch-token-test",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Test tokens",
        status="working",
    )
    db_session.add(orchestrator)

    # Create 4 agents
    for i in range(4):
        agent = MCPAgentJob(
            job_id=f"agent-token-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="implementer",
            mission=f"Agent {i} mission",
            status="waiting",
        )
        db_session.add(agent)

    await db_session.commit()

    # Test both modes
    for mode in [False, True]:
        response = await client.get(
            f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode={mode}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Token estimation should be reasonable (not zero, not huge)
        tokens = data["estimated_tokens"]
        assert tokens > 10, "Token estimate too low"
        assert tokens < 1000, "Token estimate too high for execution prompt"

        # Rough validation: ~4 chars per token
        prompt_length = len(data["prompt"])
        expected_tokens = prompt_length // 4
        assert abs(tokens - expected_tokens) < 50, "Token estimation inaccurate"


@pytest.mark.asyncio
async def test_generate_execution_prompt_includes_metadata(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test that response includes all required metadata fields."""
    # Create test project
    project = Project(
        id="test-proj-exec-8",
        tenant_key=test_user.tenant_key,
        name="Metadata Test Project",
        mission="Test metadata fields",
        description="Test project description",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator
    orchestrator = MCPAgentJob(
        job_id="orch-metadata-test",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        agent_name="Orchestrator #1",
        mission="Test metadata",
        status="working",
    )
    db_session.add(orchestrator)

    await db_session.commit()

    response = await client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify all required fields are present
    required_fields = [
        "success",
        "orchestrator_job_id",
        "project_id",
        "project_name",
        "claude_code_mode",
        "prompt",
        "agent_count",
        "estimated_tokens",
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify types
    assert isinstance(data["success"], bool)
    assert isinstance(data["orchestrator_job_id"], str)
    assert isinstance(data["project_id"], str)
    assert isinstance(data["project_name"], str)
    assert isinstance(data["claude_code_mode"], bool)
    assert isinstance(data["prompt"], str)
    assert isinstance(data["agent_count"], int)
    assert isinstance(data["estimated_tokens"], int)
