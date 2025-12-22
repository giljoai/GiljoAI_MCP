"""
Unit tests for slash command handlers (Handover 0080a)
Tests the /gil_handover slash command functionality
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.slash_commands.handover import (
    _generate_launch_prompt,
    _get_active_orchestrator,
    handle_gil_handover,
)


@pytest.fixture
def mock_project(db_session, test_tenant):
    """Create test project"""
    project = Project(
        id="test-project-id",
        name="Test Project",
        tenant_key=test_tenant.tenant_key,
        product_id="test-product-id",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def mock_orchestrator(db_session, test_tenant, mock_project):
    """Create test orchestrator job"""
    orchestrator = AgentExecution(
        job_id="orch-test-12345",
        agent_type="orchestrator",
        status="working",
        tenant_key=test_tenant.tenant_key,
        project_id=mock_project.id,
        instance_number=1,
        context_used=50000,
        context_budget=200000,
        mission="Lead the test project",
    )
    db_session.add(orchestrator)
    db_session.commit()
    return orchestrator


class TestHandleGilHandover:
    """Tests for handle_gil_handover slash command handler"""

    @pytest.mark.asyncio
    async def test_creates_successor_orchestrator(self, db_session, test_tenant, mock_orchestrator):
        """Test /gil_handover creates successor orchestrator"""
        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
            orchestrator_job_id=mock_orchestrator.job_id,
        )

        assert result["success"] is True
        assert "successor_id" in result
        assert "launch_prompt" in result
        assert "handover_summary" in result
        assert "Instance 2" in result["message"]

        # Verify successor was created
        stmt = select(AgentExecution).where(AgentExecution.job_id == result["successor_id"])
        successor_result = db_session.execute(stmt)
        successor = successor_result.scalar_one()

        assert successor is not None
        assert successor.agent_type == "orchestrator"
        assert successor.instance_number == 2
        assert successor.status == "waiting"
        assert successor.spawned_by == mock_orchestrator.job_id

    @pytest.mark.asyncio
    async def test_rejects_non_orchestrator_agent(self, db_session, test_tenant):
        """Test /gil_handover rejects non-orchestrator agents"""
        # Create a non-orchestrator agent
        frontend_agent = AgentExecution(
            job_id="frontend-test-12345",
            agent_type="frontend-dev",
            status="working",
            tenant_key=test_tenant.tenant_key,
            project_id="test-project-id",
        )
        db_session.add(frontend_agent)
        db_session.commit()

        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
            orchestrator_job_id=frontend_agent.job_id,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_ORCHESTRATOR"
        assert "not an orchestrator" in result["message"]

    @pytest.mark.asyncio
    async def test_rejects_already_handed_over(self, db_session, test_tenant, mock_orchestrator):
        """Test /gil_handover rejects orchestrator that already handed over"""
        # Mark orchestrator as handed over
        mock_orchestrator.status = "complete"
        mock_orchestrator.handover_to = "orch-successor-12345"
        db_session.commit()

        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
            orchestrator_job_id=mock_orchestrator.job_id,
        )

        assert result["success"] is False
        assert result["error"] == "ALREADY_HANDED_OVER"
        assert "already been handed over" in result["message"]

    @pytest.mark.asyncio
    async def test_generates_launch_prompt(self, db_session, test_tenant, mock_orchestrator):
        """Test launch prompt generation"""
        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
            orchestrator_job_id=mock_orchestrator.job_id,
        )

        assert result["success"] is True
        launch_prompt = result["launch_prompt"]

        # Verify launch prompt contains required environment variables
        assert "GILJO_MCP_SERVER_URL" in launch_prompt
        assert "GILJO_AGENT_JOB_ID" in launch_prompt
        assert "GILJO_PROJECT_ID" in launch_prompt
        assert "codex mcp add giljo-orchestrator" in launch_prompt

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_session, test_tenant):
        """Test tenant isolation enforced"""
        # Create orchestrator for different tenant
        other_orchestrator = AgentExecution(
            job_id="orch-other-12345",
            agent_type="orchestrator",
            status="working",
            tenant_key="other-tenant-key",
            project_id="other-project-id",
            instance_number=1,
        )
        db_session.add(other_orchestrator)
        db_session.commit()

        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,  # Different tenant
            orchestrator_job_id=other_orchestrator.job_id,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_ORCHESTRATOR"

    @pytest.mark.asyncio
    async def test_no_active_orchestrator(self, db_session, test_tenant):
        """Test error when no active orchestrator found"""
        result = await handle_gil_handover(
            db_session=db_session,
            tenant_key=test_tenant.tenant_key,
            project_id="nonexistent-project-id",
        )

        assert result["success"] is False
        assert result["error"] == "NO_ORCHESTRATOR"
        assert "No active orchestrator found" in result["message"]


class TestGetActiveOrchestrator:
    """Tests for _get_active_orchestrator helper"""

    @pytest.mark.asyncio
    async def test_finds_active_orchestrator(self, db_session, test_tenant, mock_orchestrator):
        """Test finding active orchestrator by project"""
        orchestrator = await _get_active_orchestrator(db_session, test_tenant.tenant_key, mock_orchestrator.project_id)

        assert orchestrator is not None
        assert orchestrator.job_id == mock_orchestrator.job_id

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, db_session, test_tenant):
        """Test returns None when no active orchestrator"""
        orchestrator = await _get_active_orchestrator(db_session, test_tenant.tenant_key, "nonexistent-project-id")

        assert orchestrator is None


class TestGenerateLaunchPrompt:
    """Tests for _generate_launch_prompt helper"""

    def test_includes_environment_variables(self):
        """Test launch prompt includes all environment variables"""
        prompt = _generate_launch_prompt(
            server_url="http://10.1.0.164:7272",
            job_id="orch-successor-12345",
            project_id="test-project-id",
            handover_summary={
                "project_name": "Test Project",
                "project_status": 60,
                "active_agents": [{"agent_type": "frontend-dev"}],
                "next_steps": "Continue development",
            },
        )

        assert "export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272" in prompt
        assert "export GILJO_AGENT_JOB_ID=orch-successor-12345" in prompt
        assert "export GILJO_PROJECT_ID=test-project-id" in prompt

    def test_includes_handover_summary(self):
        """Test launch prompt includes handover summary"""
        prompt = _generate_launch_prompt(
            server_url="http://localhost:7272",
            job_id="orch-successor-12345",
            project_id="test-project-id",
            handover_summary={
                "project_name": "Test Project",
                "project_status": 60,
                "active_agents": [
                    {"agent_type": "frontend-dev"},
                    {"agent_type": "backend-api"},
                ],
                "next_steps": "Continue development",
            },
        )

        assert "Test Project" in prompt
        assert "60%" in prompt
        assert "2 agents" in prompt
        assert "Continue development" in prompt

    def test_includes_mcp_command(self):
        """Test launch prompt includes MCP add command"""
        prompt = _generate_launch_prompt(
            server_url="http://localhost:7272",
            job_id="orch-successor-12345",
            project_id="test-project-id",
            handover_summary={
                "project_name": "Test Project",
                "project_status": 0,
                "active_agents": [],
                "next_steps": "Start",
            },
        )

        assert "codex mcp add giljo-orchestrator" in prompt
