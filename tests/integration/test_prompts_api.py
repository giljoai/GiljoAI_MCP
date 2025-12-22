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
            agent_type="implementer",
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
        agent_type="backend-developer",
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
    assert "agent_type" in data
    assert "tool_type" in data
    assert "instructions" in data
    assert "mission_preview" in data

    # Validate content
    assert data["agent_id"] == "agent-backend-001"
    assert data["agent_name"] == "Backend API Agent"
    assert data["agent_type"] == "backend-developer"
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
        agent_type="developer",
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
        agent_type="tester",
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
        agent_type="implementer",
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


# ============================================================================
# DEPRECATION TESTS FOR /api/prompts/execution ENDPOINT (Handover 0253 Phase 3)
# ============================================================================


@pytest.mark.asyncio
async def test_execution_endpoint_logs_deprecation_warning(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict, caplog
):
    """
    Test 1: Deprecation Warning Logged

    BEHAVIOR: When /api/prompts/execution is called, should log deprecation warning.
    Expected log message: "/api/prompts/execution called for orchestrator {id}.
                          Use /api/prompts/staging for universal prompt generation."

    TDD Status: RED ❌ - This test will FAIL until implementation
    """
    import logging

    # Create test product (required by generate_staging_prompt)
    product = Product(
        id="exec-deprecate-prod-001",
        tenant_key=test_user.tenant_key,
        name="Execution Deprecation Product",
        description="Product for execution endpoint deprecation tests",
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="exec-deprecate-proj-001",
        tenant_key=test_user.tenant_key,
        product_id=product.id,
        name="Execution Deprecation Test",
        mission="Test deprecation logging",
        description="Test project for execution endpoint deprecation",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = AgentExecution(
        job_id="exec-deprecate-orch-001",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Test orchestrator for deprecation",
        status="working",
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Call deprecated execution endpoint
    with caplog.at_level(logging.WARNING):
        response = await async_client.get(
            f"/api/v1/prompts/execution/{orchestrator.job_id}",
            headers=auth_headers
        )

    # Verify deprecation warning was logged
    assert response.status_code == status.HTTP_200_OK

    # Check for deprecation warning in logs
    deprecation_logged = any(
        "/api/prompts/execution called for orchestrator" in record.message and
        "Use /api/prompts/staging for universal prompt generation" in record.message
        for record in caplog.records
    )
    assert deprecation_logged, "Deprecation warning not found in logs"


@pytest.mark.asyncio
async def test_execution_endpoint_includes_deprecation_flags(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """
    Test 2: Response Includes Deprecation Flag

    BEHAVIOR: Response JSON should include:
        - deprecated: true
        - migration_note: "Use /api/prompts/staging/{project_id} for universal prompts"
    All existing response fields should remain (backward compatibility).

    TDD Status: RED ❌ - This test will FAIL until implementation
    """
    # Create test product (required by generate_staging_prompt)
    product = Product(
        id="exec-deprecate-prod-002",
        tenant_key=test_user.tenant_key,
        name="Deprecation Flags Product",
        description="Product for deprecation flags tests",
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="exec-deprecate-proj-002",
        tenant_key=test_user.tenant_key,
        product_id=product.id,
        name="Deprecation Flags Test",
        mission="Test deprecation response structure",
        description="Test project for response flags",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = AgentExecution(
        job_id="exec-deprecate-orch-002",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Test orchestrator for response flags",
        status="working",
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Call deprecated execution endpoint
    response = await async_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify deprecation flags are present
    assert "deprecated" in data, "Response missing 'deprecated' field"
    assert data["deprecated"] is True, "deprecated flag should be True"

    assert "migration_note" in data, "Response missing 'migration_note' field"
    expected_note = "Use /api/prompts/staging/{project_id} for universal prompts"
    assert data["migration_note"] == expected_note, f"Expected migration note: {expected_note}"

    # Verify backward compatibility - all existing fields still present
    assert "success" in data
    assert "orchestrator_job_id" in data
    assert "project_id" in data
    assert "project_name" in data
    assert "claude_code_mode" in data
    assert "prompt" in data
    assert "agent_count" in data
    assert "estimated_tokens" in data


@pytest.mark.asyncio
async def test_execution_endpoint_redirects_to_universal_generator(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict, monkeypatch
):
    """
    Test 3: Endpoint Redirects to Universal Generator

    BEHAVIOR: Endpoint should internally call ThinClientPromptGenerator.generate_staging_prompt()
    Should NOT call generate_execution_prompt()
    Parameters correctly mapped from orchestrator_job_id → fetch project_id → generate_staging_prompt()

    TDD Status: RED ❌ - This test will FAIL until implementation
    """
    # Create test product (required by generate_staging_prompt)
    product = Product(
        id="exec-deprecate-prod-003",
        tenant_key=test_user.tenant_key,
        name="Universal Generator Product",
        description="Product for universal generator tests",
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="exec-deprecate-proj-003",
        tenant_key=test_user.tenant_key,
        product_id=product.id,
        name="Universal Generator Test",
        mission="Test universal generator redirect",
        description="Test project for generator redirect",
        status="active",
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = AgentExecution(
        job_id="exec-deprecate-orch-003",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Test orchestrator for generator redirect",
        status="working",
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Track which generator methods are called
    staging_prompt_called = False
    execution_prompt_called = False

    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    original_generate_staging = ThinClientPromptGenerator.generate_staging_prompt
    original_generate_execution = ThinClientPromptGenerator.generate_execution_prompt

    async def mock_staging_prompt(self, orchestrator_id: str, project_id: str, claude_code_mode: bool = False):
        nonlocal staging_prompt_called
        staging_prompt_called = True
        # Call original to maintain functionality
        return await original_generate_staging(self, orchestrator_id, project_id, claude_code_mode)

    async def mock_execution_prompt(self, orchestrator_job_id: str, project_id: str, claude_code_mode: bool = False):
        nonlocal execution_prompt_called
        execution_prompt_called = True
        return await original_generate_execution(self, orchestrator_job_id, project_id, claude_code_mode)

    # Monkey patch the methods
    monkeypatch.setattr(
        "src.giljo_mcp.thin_prompt_generator.ThinClientPromptGenerator.generate_staging_prompt",
        mock_staging_prompt
    )
    monkeypatch.setattr(
        "src.giljo_mcp.thin_prompt_generator.ThinClientPromptGenerator.generate_execution_prompt",
        mock_execution_prompt
    )

    # Call deprecated execution endpoint
    response = await async_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK

    # Verify that staging prompt was called (universal generator)
    assert staging_prompt_called, "generate_staging_prompt() should be called (universal generator)"

    # Verify that execution prompt was NOT called (deprecated generator)
    assert not execution_prompt_called, "generate_execution_prompt() should NOT be called (deprecated)"


@pytest.mark.asyncio
async def test_execution_endpoint_backward_compatibility_maintained(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """
    Test 4: Backward Compatibility Maintained

    BEHAVIOR: Old clients calling /execution endpoint should still receive valid prompts.
    Response structure unchanged (except added deprecation fields).
    No breaking changes.

    TDD Status: RED ❌ - This test will FAIL until implementation
    """
    # Create test product (required by generate_staging_prompt)
    product = Product(
        id="exec-deprecate-prod-004",
        tenant_key=test_user.tenant_key,
        name="Backward Compatibility Product",
        description="Product for backward compatibility tests",
    )
    db_session.add(product)

    # Create test project
    project = Project(
        id="exec-deprecate-proj-004",
        tenant_key=test_user.tenant_key,
        product_id=product.id,
        name="Backward Compatibility Test",
        mission="Test backward compatibility",
        description="Test project for backward compatibility",
        status="active",
        meta_data={"path": "/home/user/test-project"},
    )
    db_session.add(project)

    # Create orchestrator job
    orchestrator = AgentExecution(
        job_id="exec-deprecate-orch-004",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Test orchestrator for backward compatibility",
        status="working",
    )
    db_session.add(orchestrator)

    # Create specialist agents
    for i in range(2):
        agent = AgentExecution(
            job_id=f"exec-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_type="implementer",
            mission=f"Implement feature {i}",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # Call deprecated execution endpoint (default mode: multi-terminal)
    response = await async_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}",
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify ALL original response fields are present and valid
    assert data["success"] is True
    assert data["orchestrator_job_id"] == orchestrator.job_id
    assert data["project_id"] == str(project.id)
    assert data["project_name"] == "Backward Compatibility Test"
    assert "claude_code_mode" in data  # Should default to False
    assert isinstance(data["prompt"], str)
    assert len(data["prompt"]) > 0, "Prompt should not be empty"
    assert data["agent_count"] == 2  # 2 specialist agents
    assert "estimated_tokens" in data
    assert data["estimated_tokens"] > 0

    # Verify prompt is valid and usable (contains expected instructions)
    prompt = data["prompt"]
    assert "orchestrator" in prompt.lower() or "staging" in prompt.lower(), \
        "Prompt should contain orchestrator or staging instructions"

    # Test with claude_code_mode=true
    response_cc = await async_client.get(
        f"/api/v1/prompts/execution/{orchestrator.job_id}?claude_code_mode=true",
        headers=auth_headers
    )

    assert response_cc.status_code == status.HTTP_200_OK
    data_cc = response_cc.json()
    assert data_cc["claude_code_mode"] is True
    assert isinstance(data_cc["prompt"], str)
    assert len(data_cc["prompt"]) > 0
