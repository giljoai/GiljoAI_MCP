"""
Agent Prompt Endpoint Tests - Handover 0497a

TDD tests for the thin prompt endpoint: GET /api/v1/prompts/agent/{agent_id}
Validates that the endpoint returns the correct thin prompt pattern matching
the spawn-time prompt from orchestration_service.spawn_agent_job().

Test Coverage:
- Thin prompt format correctness (contains get_agent_mission instruction)
- Correct job_id and tenant_key in prompt
- Agent identity fields (agent_name, agent_display_name)
- All AgentPromptResponse fields populated
- 404 for non-existent agent
- Tenant isolation (agent from different tenant returns 404)
"""

from uuid import uuid4

import pytest
from passlib.hash import bcrypt

from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def tenant_a_setup(db_manager, clean_db):
    """Create tenant A user + org + project + agent job + agent execution.

    Depends on clean_db to ensure data creation happens after cleanup.
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import Project, User
    from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
    from src.giljo_mcp.models.organizations import Organization

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Org
        org = Organization(
            name=f"Prompt Test Org A {unique_id}",
            slug=f"prompt-test-a-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        # User
        user = User(
            username=f"prompt_test_a_{unique_id}",
            email=f"prompt_a_{unique_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.flush()

        # Project
        project = Project(
            name=f"Test Project {unique_id}",
            description="Test project for prompt endpoint tests",
            mission="Build the test feature",
            tenant_key=tenant_key,
        )
        session.add(project)
        await session.flush()

        # AgentJob
        job_id = f"job-{unique_id}"
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Implement the login feature with OAuth2 support and session management.",
            job_type="specialist",
            status="active",
        )
        session.add(agent_job)
        await session.flush()

        # AgentExecution
        agent_id = f"agent-{unique_id}"
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_name="backend-engineer",
            agent_display_name="Backend Engineer",
            tool_type="claude-code",
            status="working",
        )
        session.add(agent_execution)
        await session.commit()

        # JWT token
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=tenant_key,
        )

        return {
            "headers": {"Cookie": f"access_token={token}"},
            "agent_id": agent_id,
            "job_id": job_id,
            "tenant_key": tenant_key,
            "project_name": project.name,
            "agent_name": "backend-engineer",
            "agent_display_name": "Backend Engineer",
        }


@pytest.fixture
async def tenant_b_setup(db_manager, clean_db):
    """Create tenant B user (different tenant for isolation tests).

    Depends on clean_db to ensure data creation happens after cleanup.
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"Prompt Test Org B {unique_id}",
            slug=f"prompt-test-b-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"prompt_test_b_{unique_id}",
            email=f"prompt_b_{unique_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.commit()

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=tenant_key,
        )

        return {
            "headers": {"Cookie": f"access_token={token}"},
            "tenant_key": tenant_key,
        }


# ============================================================================
# THIN PROMPT FORMAT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_agent_prompt_contains_get_agent_mission(api_client, tenant_a_setup):
    """Endpoint returns thin prompt containing get_agent_mission MCP call."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert "mcp__giljo-mcp__get_agent_mission" in data["prompt"]


@pytest.mark.asyncio
async def test_agent_prompt_contains_correct_job_id(api_client, tenant_a_setup):
    """Thin prompt includes the correct job_id for mission lookup."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert setup["job_id"] in data["prompt"]


@pytest.mark.asyncio
async def test_agent_prompt_contains_correct_tenant_key(api_client, tenant_a_setup):
    """Thin prompt includes the correct tenant_key for mission lookup."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert setup["tenant_key"] in data["prompt"]


@pytest.mark.asyncio
async def test_agent_prompt_contains_agent_identity(api_client, tenant_a_setup):
    """Thin prompt includes agent name and display name."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    prompt = data["prompt"]
    assert setup["agent_name"] in prompt
    assert setup["agent_display_name"] in prompt


@pytest.mark.asyncio
async def test_agent_prompt_contains_project_name(api_client, tenant_a_setup):
    """Thin prompt includes the project name."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert setup["project_name"] in data["prompt"]


@pytest.mark.asyncio
async def test_agent_prompt_no_stale_bash_patterns(api_client, tenant_a_setup):
    """Thin prompt must NOT contain stale bash-script patterns."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    prompt = response.json()["prompt"]
    # Must not contain the old bash-script patterns
    assert "export AGENT_ID" not in prompt
    assert "mkdir -p .missions" not in prompt
    assert "-agent execute" not in prompt
    assert "cat > .missions/" not in prompt


# ============================================================================
# RESPONSE FIELD TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_agent_prompt_response_fields(api_client, tenant_a_setup):
    """All AgentPromptResponse fields are correctly populated."""
    setup = tenant_a_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{setup['agent_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == setup["agent_id"]
    assert data["agent_name"] is not None
    assert data["agent_display_name"] == setup["agent_display_name"]
    assert data["tool_type"] in ("claude-code", "universal")
    assert data["instructions"] is not None
    assert data["mission_preview"] is not None
    assert len(data["mission_preview"]) > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_agent_prompt_404_nonexistent(api_client, tenant_a_setup):
    """Returns 404 for non-existent agent_id."""
    setup = tenant_a_setup
    response = await api_client.get(
        "/api/v1/prompts/agent/nonexistent-agent-id",
        headers=setup["headers"],
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_prompt_401_unauthenticated(api_client):
    """Returns 401 when no authentication is provided."""
    response = await api_client.get("/api/v1/prompts/agent/any-agent-id")
    assert response.status_code in (401, 403)


# ============================================================================
# TENANT ISOLATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_agent_prompt_tenant_isolation(api_client, tenant_a_setup, tenant_b_setup):
    """Tenant B cannot access tenant A's agent prompt (returns 404)."""
    a_setup = tenant_a_setup
    b_setup = tenant_b_setup
    response = await api_client.get(
        f"/api/v1/prompts/agent/{a_setup['agent_id']}",
        headers=b_setup["headers"],
    )
    assert response.status_code == 404
