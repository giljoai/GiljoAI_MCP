"""
Implementation Prompt Endpoint Tests - Handover 0497c

TDD tests for multi-terminal orchestrator implementation prompt:
- GET /api/v1/prompts/implementation/{project_id} now supports both CLI and multi-terminal modes
- New _build_multi_terminal_orchestrator_prompt() method in ThinClientPromptGenerator
- CLI mode regression: must remain completely untouched

Test Coverage:
1. Prompt builder unit tests (5 sections of multi-terminal prompt)
2. Endpoint mode-aware routing (multi_terminal vs claude_code_cli)
3. CLI regression (CRITICAL)
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from passlib.hash import bcrypt

from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# PROMPT BUILDER UNIT TESTS (no DB needed)
# ============================================================================


def _make_project(name="Test Project", project_id=None, product_id=None):
    """Create a mock project with required attributes."""
    return SimpleNamespace(
        id=project_id or str(uuid4()),
        name=name,
        product_id=product_id or str(uuid4()),
    )


def _make_agent_execution(agent_name, display_name, job_id=None, status="waiting", mission="Do work"):
    """Create a mock agent execution with job relationship."""
    job = SimpleNamespace(mission=mission)
    return SimpleNamespace(
        agent_id=str(uuid4()),
        agent_name=agent_name,
        agent_display_name=display_name,
        job_id=job_id or str(uuid4()),
        status=status,
        job=job,
    )


def _build_prompt(orchestrator_id=None, project=None, agent_jobs=None, git_enabled=False):
    """Helper: instantiate generator and call _build_multi_terminal_orchestrator_prompt."""
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    mock_db = MagicMock()
    gen = ThinClientPromptGenerator(mock_db, "tk_test_tenant")
    return gen._build_multi_terminal_orchestrator_prompt(
        orchestrator_id=orchestrator_id or str(uuid4()),
        project=project or _make_project(),
        agent_jobs=agent_jobs or [],
        git_enabled=git_enabled,
    )


class TestMultiTerminalPromptBuilder:
    """Unit tests for _build_multi_terminal_orchestrator_prompt()."""

    def test_section1_identity_and_context(self):
        """Prompt contains orchestrator identity: project name, job_id, health_check."""
        project = _make_project(name="My Cool Project")
        orch_id = "orch-job-123"
        prompt = _build_prompt(orchestrator_id=orch_id, project=project)

        assert "My Cool Project" in prompt
        assert orch_id in prompt
        assert "health_check" in prompt
        assert "ORCHESTRATOR" in prompt

    def test_section2_team_roster(self):
        """Prompt contains team roster with agent names, IDs, roles, and statuses."""
        agents = [
            _make_agent_execution("tdd-implementor", "implementer", status="waiting"),
            _make_agent_execution("backend-engineer", "backend", status="working"),
        ]
        prompt = _build_prompt(agent_jobs=agents)

        assert "tdd-implementor" in prompt
        assert "backend-engineer" in prompt
        assert "implementer" in prompt
        assert "backend" in prompt
        # Agent IDs should be present for coordination
        assert agents[0].agent_id in prompt
        assert agents[1].agent_id in prompt

    def test_section3_reactive_coordinator_role(self):
        """Prompt contains reactive coordinator instructions: no polling, wait for user."""
        prompt = _build_prompt()

        # Must mention reactive/idle behavior
        assert "reactive" in prompt.lower() or "idle" in prompt.lower()
        # Must explicitly say no polling
        assert "poll" in prompt.lower() or "loop" in prompt.lower()
        # Must mention available MCP tools
        assert "get_workflow_status" in prompt
        assert "receive_messages" in prompt
        assert "send_message" in prompt
        assert "report_progress" in prompt
        assert "get_orchestrator_instructions" in prompt

    def test_section4_handling_agent_issues(self):
        """Prompt contains guidance for handling agent issues (spawn_agent_job)."""
        prompt = _build_prompt()

        assert "spawn_agent_job" in prompt

    def test_section5_project_closeout(self):
        """Prompt contains project closeout instructions."""
        prompt = _build_prompt()

        assert "complete_job" in prompt
        assert "write_360_memory" in prompt
        assert "get_workflow_status" in prompt

    def test_no_task_tool_spawning(self):
        """Multi-terminal prompt must NOT contain Task tool spawning (that's CLI mode)."""
        prompt = _build_prompt()

        assert "Task(" not in prompt
        assert "subagent_type" not in prompt

    def test_git_closeout_when_enabled(self):
        """When git_enabled=True, prompt includes git closeout guidance."""
        project = _make_project(name="Git Project")
        prompt = _build_prompt(project=project, git_enabled=True)

        assert "git" in prompt.lower() or "closeout" in prompt.lower()

    def test_prompt_token_budget(self):
        """Prompt should be within ~800-1200 token budget (roughly 4 chars per token)."""
        agents = [
            _make_agent_execution("tdd-implementor", "implementer"),
            _make_agent_execution("backend-engineer", "backend"),
            _make_agent_execution("frontend-designer", "frontend"),
        ]
        prompt = _build_prompt(agent_jobs=agents, git_enabled=True)

        estimated_tokens = len(prompt) // 4
        # Allow some flexibility: 500-1800 tokens
        assert estimated_tokens < 1800, f"Prompt too long: ~{estimated_tokens} tokens"
        assert estimated_tokens > 300, f"Prompt too short: ~{estimated_tokens} tokens"

    def test_empty_agent_list(self):
        """Prompt handles empty agent list gracefully."""
        prompt = _build_prompt(agent_jobs=[])
        # Should still produce a valid prompt
        assert "ORCHESTRATOR" in prompt


# ============================================================================
# ENDPOINT INTEGRATION TESTS
# ============================================================================


@pytest.fixture
async def multi_terminal_setup(db_manager, clean_db):
    """Create a multi_terminal mode project with orchestrator + 2 agents.

    Depends on clean_db to ensure data creation happens after cleanup.
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import Project, User
    from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.models.products import Product

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Org
        org = Organization(
            name=f"MT Org {unique_id}",
            slug=f"mt-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        # User
        user = User(
            username=f"mt_user_{unique_id}",
            email=f"mt_{unique_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.flush()

        # Product (needed for git_enabled check in endpoint)
        product = Product(
            name=f"MT Product {unique_id}",
            tenant_key=tenant_key,
        )
        session.add(product)
        await session.flush()

        # Project — multi_terminal mode
        project = Project(
            name=f"MT Project {unique_id}",
            description="Multi-terminal test project",
            mission="Build a feature",
            tenant_key=tenant_key,
            execution_mode="multi_terminal",
            product_id=product.id,
        )
        session.add(project)
        await session.flush()

        # Orchestrator job + execution
        orch_job_id = f"orch-{unique_id}"
        orch_agent_id = f"orch-agent-{unique_id}"
        orch_job = AgentJob(
            job_id=orch_job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Orchestrate the team",
            job_type="orchestrator",
            status="active",
        )
        session.add(orch_job)
        await session.flush()

        orch_exec = AgentExecution(
            agent_id=orch_agent_id,
            job_id=orch_job_id,
            tenant_key=tenant_key,
            agent_name="orchestrator",
            agent_display_name="orchestrator",
            tool_type="claude-code",
            status="working",
        )
        session.add(orch_exec)
        await session.flush()

        # Specialist agents (spawned by orchestrator)
        agent1_job_id = f"agent1-{unique_id}"
        agent1_id = f"agent1-exec-{unique_id}"
        agent1_job = AgentJob(
            job_id=agent1_job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Implement the backend",
            job_type="specialist",
            status="active",
        )
        session.add(agent1_job)
        await session.flush()

        agent1_exec = AgentExecution(
            agent_id=agent1_id,
            job_id=agent1_job_id,
            tenant_key=tenant_key,
            agent_name="backend-engineer",
            agent_display_name="backend",
            tool_type="claude-code",
            status="waiting",
            spawned_by=orch_agent_id,
        )
        session.add(agent1_exec)

        agent2_job_id = f"agent2-{unique_id}"
        agent2_id = f"agent2-exec-{unique_id}"
        agent2_job = AgentJob(
            job_id=agent2_job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Write the tests",
            job_type="specialist",
            status="active",
        )
        session.add(agent2_job)
        await session.flush()

        agent2_exec = AgentExecution(
            agent_id=agent2_id,
            job_id=agent2_job_id,
            tenant_key=tenant_key,
            agent_name="tdd-implementor",
            agent_display_name="tester",
            tool_type="claude-code",
            status="waiting",
            spawned_by=orch_agent_id,
        )
        session.add(agent2_exec)

        await session.commit()

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=tenant_key,
        )

        return {
            "headers": {"Cookie": f"access_token={token}"},
            "project_id": str(project.id),
            "project_name": project.name,
            "orch_job_id": orch_job_id,
            "orch_agent_id": orch_agent_id,
            "agent1_name": "backend-engineer",
            "agent2_name": "tdd-implementor",
            "agent1_id": agent1_id,
            "agent2_id": agent2_id,
            "tenant_key": tenant_key,
        }


@pytest.fixture
async def cli_mode_setup(db_manager, clean_db):
    """Create a claude_code_cli mode project with orchestrator + 1 agent.

    For CLI mode regression testing.
    """
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.models import Project, User
    from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.models.products import Product

    unique_id = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"CLI Org {unique_id}",
            slug=f"cli-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"cli_user_{unique_id}",
            email=f"cli_{unique_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.flush()

        product = Product(
            name=f"CLI Product {unique_id}",
            tenant_key=tenant_key,
        )
        session.add(product)
        await session.flush()

        project = Project(
            name=f"CLI Project {unique_id}",
            description="CLI mode test project",
            mission="Build CLI feature",
            tenant_key=tenant_key,
            execution_mode="claude_code_cli",
            product_id=product.id,
        )
        session.add(project)
        await session.flush()

        orch_job_id = f"cli-orch-{unique_id}"
        orch_agent_id = f"cli-orch-agent-{unique_id}"
        orch_job = AgentJob(
            job_id=orch_job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Orchestrate CLI project",
            job_type="orchestrator",
            status="active",
        )
        session.add(orch_job)
        await session.flush()

        orch_exec = AgentExecution(
            agent_id=orch_agent_id,
            job_id=orch_job_id,
            tenant_key=tenant_key,
            agent_name="orchestrator",
            agent_display_name="orchestrator",
            tool_type="claude-code",
            status="working",
        )
        session.add(orch_exec)
        await session.flush()

        agent_job_id = f"cli-agent-{unique_id}"
        agent_id = f"cli-agent-exec-{unique_id}"
        agent_job = AgentJob(
            job_id=agent_job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Implement CLI feature",
            job_type="specialist",
            status="active",
        )
        session.add(agent_job)
        await session.flush()

        agent_exec = AgentExecution(
            agent_id=agent_id,
            job_id=agent_job_id,
            tenant_key=tenant_key,
            agent_name="backend-engineer",
            agent_display_name="backend",
            tool_type="claude-code",
            status="waiting",
            spawned_by=orch_agent_id,
        )
        session.add(agent_exec)

        await session.commit()

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=tenant_key,
        )

        return {
            "headers": {"Cookie": f"access_token={token}"},
            "project_id": str(project.id),
            "project_name": project.name,
            "orch_job_id": orch_job_id,
        }


# ============================================================================
# MULTI-TERMINAL ENDPOINT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_implementation_endpoint_multi_terminal_returns_200(api_client, multi_terminal_setup):
    """GET /implementation/{project_id} returns 200 for multi_terminal projects."""
    setup = multi_terminal_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_implementation_endpoint_multi_terminal_contains_team(api_client, multi_terminal_setup):
    """Multi-terminal implementation prompt contains agent team roster."""
    setup = multi_terminal_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    data = response.json()
    prompt = data["prompt"]

    assert setup["agent1_name"] in prompt
    assert setup["agent2_name"] in prompt


@pytest.mark.asyncio
async def test_implementation_endpoint_multi_terminal_no_task_tool(api_client, multi_terminal_setup):
    """Multi-terminal prompt must NOT contain Task() spawning syntax."""
    setup = multi_terminal_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    prompt = response.json()["prompt"]

    assert "Task(" not in prompt
    assert "subagent_type" not in prompt


@pytest.mark.asyncio
async def test_implementation_endpoint_multi_terminal_reactive_role(api_client, multi_terminal_setup):
    """Multi-terminal prompt contains reactive coordinator instructions."""
    setup = multi_terminal_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    prompt = response.json()["prompt"]

    # Should mention MCP tools
    assert "get_workflow_status" in prompt
    assert "receive_messages" in prompt


@pytest.mark.asyncio
async def test_implementation_endpoint_multi_terminal_agent_count(api_client, multi_terminal_setup):
    """Response includes correct agent_count for multi-terminal mode."""
    setup = multi_terminal_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    data = response.json()
    assert data["agent_count"] == 2


# ============================================================================
# CLI MODE REGRESSION TESTS (CRITICAL)
# ============================================================================


@pytest.mark.asyncio
async def test_implementation_endpoint_cli_still_works(api_client, cli_mode_setup):
    """CLI mode implementation endpoint still returns 200 (regression)."""
    setup = cli_mode_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_implementation_endpoint_cli_contains_task_spawning(api_client, cli_mode_setup):
    """CLI mode prompt still contains Task tool spawning template (regression)."""
    setup = cli_mode_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    prompt = response.json()["prompt"]

    # CLI prompt must contain Task tool spawning
    assert "Task(" in prompt or "subagent_type" in prompt
    # CLI prompt must contain agent template reference
    assert ".claude/agents/" in prompt


@pytest.mark.asyncio
async def test_implementation_endpoint_cli_contains_cli_constraints(api_client, cli_mode_setup):
    """CLI mode prompt still contains CLI-specific constraints (regression)."""
    setup = cli_mode_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    prompt = response.json()["prompt"]

    assert "CLI Mode" in prompt


@pytest.mark.asyncio
async def test_implementation_endpoint_cli_no_reactive_coordinator(api_client, cli_mode_setup):
    """CLI mode prompt must NOT contain multi-terminal reactive coordinator language."""
    setup = cli_mode_setup
    response = await api_client.get(
        f"/api/v1/prompts/implementation/{setup['project_id']}",
        headers=setup["headers"],
    )
    prompt = response.json()["prompt"]

    assert "Reactive Coordinator" not in prompt
    assert "idle by default" not in prompt
