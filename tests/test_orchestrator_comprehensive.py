"""
Comprehensive tests for ProjectOrchestrator with full functionality.
Tests state transitions, agent lifecycle, handoffs, context tracking, and multi-project support.

Handover 0422: Cleaned up tests for removed dead token budget code.
Removed tests for: update_context_usage(), check_handoff_needed(), get_agent_context_status(),
handoff(), _context_monitors, _start_context_monitor(), _stop_context_monitor(),
_monitor_project_context(), _get_handoff_reason()
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.enums import ProjectStatus, ContextStatus
from src.giljo_mcp.orchestrator import AgentRole, ProjectOrchestrator


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    manager = AsyncMock()
    # Create a proper async context manager mock
    session_mock = AsyncMock()
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=session_mock)
    context_manager.__aexit__ = AsyncMock()
    manager.get_session_async = MagicMock(return_value=context_manager)
    return manager


@pytest.fixture
def orchestrator(mock_db_manager):
    """Create orchestrator with mocked database."""
    with patch("src.giljo_mcp.orchestrator.get_db_manager", return_value=mock_db_manager):
        orch = ProjectOrchestrator()
        orch.db_manager = mock_db_manager
        return orch


@pytest.fixture
def mock_project():
    """Create mock project object."""
    project = MagicMock()
    project.id = str(uuid4())
    project.tenant_key = "test-tenant"
    project.name = "Test Project"
    project.mission = "Test mission"
    project.status = ProjectStatus.INACTIVE.value
    project.created_at = datetime.now()
    project.context_budget = 150000
    project.context_used = 0
    return project


@pytest.fixture
def mock_agent():
    """Create mock agent object."""
    agent = MagicMock()
    agent.id = str(uuid4())
    agent.name = "test_agent"
    agent.role = AgentRole.ANALYZER.value
    agent.mission = "Analyze code"
    agent.status = "active"
    agent.context_budget = 50000
    agent.context_used = 0
    agent.project_id = str(uuid4())
    return agent


class TestProjectLifecycle:
    """Test project state machine and lifecycle methods."""

    @pytest.mark.asyncio
    async def test_create_project(self, orchestrator, mock_project):
        """Test project creation."""
        # Setup mock session
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Mock the add and commit
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Create project
        with patch("src.giljo_mcp.models.Project", return_value=mock_project):
            result = await orchestrator.create_project(
                tenant_key="test-tenant", name="Test Project", mission="Test mission"
            )

        assert result == mock_project
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_project_from_inactive(self, orchestrator, mock_project):
        """Test activating a project from inactive state."""
        mock_project.status = ProjectStatus.INACTIVE.value

        # Setup mock session
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()

        result = await orchestrator.activate_project(mock_project.id)

        assert result == mock_project
        assert mock_project.status == ProjectStatus.ACTIVE.value
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_project_invalid_state(self, orchestrator, mock_project):
        """Test that activation fails from completed state."""
        mock_project.status = ProjectStatus.COMPLETED.value

        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        with pytest.raises(ValueError, match="Cannot activate project"):
            await orchestrator.activate_project(mock_project.id)

    @pytest.mark.asyncio
    async def test_deactivate_active_project(self, orchestrator, mock_project):
        """Test deactivating an active project."""
        mock_project.status = ProjectStatus.ACTIVE.value
        mock_project.id = "test-project-id"

        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()

        result = await orchestrator.deactivate_project(mock_project.id)

        assert result == mock_project
        assert mock_project.status == ProjectStatus.INACTIVE.value
        # Verify context monitoring stopped
        assert mock_project.id not in orchestrator._context_monitors

    @pytest.mark.asyncio
    async def test_complete_project(self, orchestrator, mock_project):
        """Test completing an active project."""
        mock_project.status = ProjectStatus.ACTIVE.value

        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        # Mock agents
        mock_agents = [MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        mock_session.commit = AsyncMock()

        result = await orchestrator.complete_project(mock_project.id, summary="Project completed")

        assert result == mock_project
        assert mock_project.status == ProjectStatus.COMPLETED.value
        assert mock_project.completion_summary == "Project completed"
        assert mock_agents[0].status == "database_initialized"

    @pytest.mark.asyncio
    async def test_archive_completed_project(self, orchestrator, mock_project):
        """Test archiving a completed project."""
        mock_project.status = ProjectStatus.COMPLETED.value

        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.commit = AsyncMock()

        result = await orchestrator.archive_project(mock_project.id)

        assert result == mock_project
        assert mock_project.status == ProjectStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_state_transition_validation(self, orchestrator, mock_project):
        """Test invalid state transitions are prevented."""
        # Can't deactivate an already inactive project
        mock_project.status = ProjectStatus.INACTIVE.value

        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        with pytest.raises(ValueError, match="Cannot deactivate project"):
            await orchestrator.deactivate_project(mock_project.id)

        # Can't archive non-completed project
        mock_project.status = ProjectStatus.ACTIVE.value

        with pytest.raises(ValueError, match="Only completed projects"):
            await orchestrator.archive_project(mock_project.id)


class TestAgentManagement:
    """Test agent spawning and lifecycle management."""

    @pytest.mark.asyncio
    async def test_spawn_agent_with_role_template(self, orchestrator, mock_project):
        """Test spawning agent with correct role template."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Mock project lookup
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,  # First call for project
            None,  # Second call for existing agent check
        ]

        mock_agent = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.giljo_mcp.models.Agent", return_value=mock_agent):
            result = await orchestrator.spawn_agent(
                project_id=mock_project.id, agent_name="analyzer_1", role=AgentRole.ANALYZER
            )

        assert result == mock_agent
        assert mock_agent.role == AgentRole.ANALYZER.value
        assert "analyzer responsible for" in mock_agent.mission

    @pytest.mark.asyncio
    async def test_spawn_agent_custom_mission(self, orchestrator, mock_project):
        """Test spawning agent with custom mission overrides template."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_session.execute.return_value.scalar_one_or_none.side_effect = [mock_project, None]

        mock_agent = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.giljo_mcp.models.Agent", return_value=mock_agent):
            await orchestrator.spawn_agent(
                project_id=mock_project.id,
                agent_name="custom_agent",
                role=AgentRole.IMPLEMENTER,
                custom_mission="Custom implementation task",
            )

        assert mock_agent.mission == "Custom implementation task"

    @pytest.mark.asyncio
    async def test_spawn_duplicate_agent_prevented(self, orchestrator, mock_project, mock_agent):
        """Test that duplicate agents are not created."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Existing agent found
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [mock_project, mock_agent]  # Existing agent

        with pytest.raises(ValueError, match="already exists"):
            await orchestrator.spawn_agent(
                project_id=mock_project.id, agent_name=mock_agent.name, role=AgentRole.TESTER
            )

    @pytest.mark.asyncio
    async def test_get_project_agents(self, orchestrator, mock_project):
        """Test retrieving all agents for a project."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_agents = [
            MagicMock(name="agent1", role=AgentRole.ANALYZER.value),
            MagicMock(name="agent2", role=AgentRole.IMPLEMENTER.value),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents

        result = await orchestrator.get_project_agents(mock_project.id)

        assert len(result) == 2
        assert result[0].name == "agent1"
        assert result[1].name == "agent2"


# Handover 0422: Entire TestHandoffMechanism class removed - tests removed methods:
# - handoff() - method removed
# - check_handoff_needed() - method removed


# Handover 0422: Entire TestContextTracking class removed - tests removed methods:
# - update_context_usage() - method removed
# - get_agent_context_status() - method removed
# - _context_monitors attribute removed
# - _start_context_monitor() - method removed
# - _stop_context_monitor() - method removed


class TestMultiProjectSupport:
    """Test multi-project and multi-tenant functionality."""

    @pytest.mark.asyncio
    async def test_get_active_projects_by_tenant(self, orchestrator):
        """Test retrieving active projects for a tenant."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_projects = [
            MagicMock(id="proj1", name="Project 1", status=ProjectStatus.ACTIVE.value),
            MagicMock(id="proj2", name="Project 2", status=ProjectStatus.ACTIVE.value),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects

        result = await orchestrator.get_active_projects("test-tenant")

        assert len(result) == 2
        assert result[0].name == "Project 1"
        assert result[1].name == "Project 2"

    @pytest.mark.asyncio
    async def test_get_tenant_projects_all_statuses(self, orchestrator):
        """Test retrieving all projects for a tenant."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_projects = [
            MagicMock(status=ProjectStatus.DRAFT.value),
            MagicMock(status=ProjectStatus.ACTIVE.value),
            MagicMock(status=ProjectStatus.COMPLETED.value),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects

        result = await orchestrator.get_tenant_projects("test-tenant")

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_allocate_resources_single_project(self, orchestrator):
        """Test resource allocation for single active project."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_project = MagicMock()
        mock_project.id = "proj1"
        mock_project.status = ProjectStatus.ACTIVE.value
        mock_project.priority = 1

        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_project]
        mock_session.commit = AsyncMock()

        result = await orchestrator.allocate_resources(tenant_key="test-tenant", total_context_budget=100000)

        assert result["total_allocated"] == 100000
        assert result["projects"]["proj1"]["allocated"] == 100000
        assert mock_project.context_budget == 100000

    @pytest.mark.asyncio
    async def test_allocate_resources_multiple_projects(self, orchestrator):
        """Test resource allocation across multiple projects by priority."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_projects = [
            MagicMock(id="proj1", status=ProjectStatus.ACTIVE.value, priority=1),
            MagicMock(id="proj2", status=ProjectStatus.ACTIVE.value, priority=2),
            MagicMock(id="proj3", status=ProjectStatus.ACTIVE.value, priority=2),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects
        mock_session.commit = AsyncMock()

        result = await orchestrator.allocate_resources(tenant_key="test-tenant", total_context_budget=120000)

        # Priority 1 gets 50%, priority 2 projects share remaining 50%
        assert mock_projects[0].context_budget == 60000  # 50%
        assert mock_projects[1].context_budget == 30000  # 25%
        assert mock_projects[2].context_budget == 30000  # 25%
        assert result["total_allocated"] == 120000

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, orchestrator):
        """Test that projects are properly isolated by tenant."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Tenant 1 projects
        tenant1_projects = [MagicMock(tenant_key="tenant1", name="T1 Project")]

        # Query should filter by tenant
        mock_session.execute.return_value.scalars.return_value.all.return_value = tenant1_projects

        result = await orchestrator.get_tenant_projects("tenant1")

        assert len(result) == 1
        assert result[0].tenant_key == "tenant1"


class TestAgentCapabilityMatrix:
    """Test agent capability definitions and role-based features."""

    def test_agent_roles_have_missions(self, orchestrator):
        """Test all agent roles have defined missions."""
        for role in AgentRole:
            assert role in orchestrator.AGENT_MISSIONS
            assert len(orchestrator.AGENT_MISSIONS[role]) > 0

    def test_mission_templates_format(self, orchestrator):
        """Test mission templates have proper format."""
        for role, mission in orchestrator.AGENT_MISSIONS.items():
            # Check mission contains role name
            assert role.value in mission.lower()

            # Check mission has substantial content
            assert len(mission) > 100

            # Check mission has responsibilities
            assert "responsible for" in mission or "responsibilities" in mission.lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_project_not_found(self, orchestrator):
        """Test handling of non-existent project."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError, match="Project .* not found"):
            await orchestrator.activate_project("non-existent-id")

    # Handover 0422: test_agent_not_found removed - tested check_handoff_needed() which is removed

    @pytest.mark.asyncio
    async def test_database_connection_error(self, orchestrator):
        """Test handling of database connection errors."""
        orchestrator.db_manager.get_session.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await orchestrator.create_project("tenant", "project", "mission")

    @pytest.mark.asyncio
    async def test_concurrent_project_limit(self, orchestrator):
        """Test handling of too many concurrent projects."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Create many active projects
        many_projects = [MagicMock(status=ProjectStatus.ACTIVE.value) for _ in range(10)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = many_projects

        # Should handle gracefully
        result = await orchestrator.get_active_projects("tenant")
        assert len(result) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.orchestrator", "--cov-report=term-missing"])
