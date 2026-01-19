"""
Final comprehensive test suite for ProjectOrchestrator.
Tests all functionality with proper mocking and coverage tracking.

Handover 0422: Cleaned up tests for removed dead token budget code.
Removed tests for: update_context_usage(), get_context_status(), check_handoff_needed(),
handoff(), _get_handoff_reason()
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.enums import ProjectStatus, ContextStatus
from src.giljo_mcp.orchestrator import AgentRole, ProjectOrchestrator


@pytest.fixture
def orchestrator():
    """Create orchestrator instance with mocked database."""
    orch = ProjectOrchestrator()

    # Mock database manager
    mock_db = AsyncMock()
    mock_session = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock()
    mock_db.get_session_async = MagicMock(return_value=mock_context)
    mock_db.generate_tenant_key = MagicMock(return_value="test-tenant-123")

    orch.db_manager = mock_db
    orch._mock_session = mock_session  # Store for test access

    return orch


class TestProjectLifecycle:
    """Test project state machine and transitions."""

    @pytest.mark.asyncio
    async def test_create_project_generates_tenant_key(self, orchestrator):
        """Test project creation generates tenant key when not provided."""
        mock_session = orchestrator._mock_session
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Capture the Project object that gets created
        created_project = None

        def capture_add(obj):
            nonlocal created_project
            created_project = obj

        mock_session.add.side_effect = capture_add

        await orchestrator.create_project(name="Test Project", mission="Test mission")

        assert created_project is not None
        assert created_project.tenant_key == "test-tenant-123"
        assert created_project.status == ProjectStatus.DRAFT.value
        assert created_project.name == "Test Project"

    @pytest.mark.asyncio
    async def test_state_transitions(self, orchestrator):
        """Test valid state transitions through project lifecycle."""
        mock_session = orchestrator._mock_session

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = str(uuid4())
        mock_project.status = ProjectStatus.INACTIVE.value

        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()

        # Inactive -> Active
        await orchestrator.activate_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ACTIVE.value

        # Active -> Inactive (deactivate)
        mock_project.id = "test-project-id"
        await orchestrator.deactivate_project(mock_project.id)
        assert mock_project.status == ProjectStatus.INACTIVE.value

        # Active -> Completed
        mock_agents[0].status = "active"
        await orchestrator.complete_project(mock_project.id, "Done")
        assert mock_project.status == ProjectStatus.COMPLETED.value
        assert mock_agents[0].status == "database_initialized"

        # Completed -> Archived
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        await orchestrator.archive_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_invalid_state_transitions(self, orchestrator):
        """Test that invalid state transitions raise errors."""
        mock_session = orchestrator._mock_session
        mock_project = MagicMock()
        mock_project.id = str(uuid4())

        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        # Can't deactivate inactive project
        mock_project.status = ProjectStatus.INACTIVE.value
        with pytest.raises(ValueError, match="Cannot deactivate"):
            await orchestrator.deactivate_project(mock_project.id)

        # Can't activate completed project
        mock_project.status = ProjectStatus.COMPLETED.value
        with pytest.raises(ValueError, match="Cannot activate"):
            await orchestrator.activate_project(mock_project.id)

        # Can't archive active project
        mock_project.status = ProjectStatus.ACTIVE.value
        with pytest.raises(ValueError, match="Only completed"):
            await orchestrator.archive_project(mock_project.id)


class TestAgentManagement:
    """Test agent spawning and lifecycle."""

    @pytest.mark.asyncio
    async def test_spawn_agent_with_role_template(self, orchestrator):
        """Test spawning agent uses correct role template."""
        mock_session = orchestrator._mock_session

        mock_project = MagicMock()
        mock_project.id = str(uuid4())

        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,  # Project lookup
            None,  # No existing agent
        ]

        # Capture created agent
        created_agent = None

        def capture_add(obj):
            nonlocal created_agent
            created_agent = obj

        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        await orchestrator.spawn_agent(project_id=mock_project.id, role=AgentRole.ANALYZER)

        assert created_agent is not None
        assert created_agent.role == AgentRole.ANALYZER.value
        assert "analyzer responsible for" in created_agent.mission
        assert created_agent.name == f"analyzer_{mock_project.id[:8]}"

    @pytest.mark.asyncio
    async def test_spawn_agent_custom_mission(self, orchestrator):
        """Test custom mission overrides template."""
        mock_session = orchestrator._mock_session

        mock_project = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [mock_project, None]

        created_agent = None

        def capture_add(obj):
            nonlocal created_agent
            created_agent = obj

        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        await orchestrator.spawn_agent(
            project_id=str(uuid4()), role=AgentRole.TESTER, custom_mission="Custom test mission"
        )

        assert created_agent.mission == "Custom test mission"

    @pytest.mark.asyncio
    async def test_duplicate_agent_prevention(self, orchestrator):
        """Test that duplicate agents are not created."""
        mock_session = orchestrator._mock_session

        mock_project = MagicMock()
        existing_agent = MagicMock()
        existing_agent.name = "existing_agent"

        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            existing_agent,  # Agent already exists
        ]

        with pytest.raises(ValueError, match="already exists"):
            await orchestrator.spawn_agent(project_id=str(uuid4()), role=AgentRole.IMPLEMENTER)


# Handover 0422: Entire TestHandoffMechanism class removed - tests removed methods:
# - handoff() - method removed
# - check_handoff_needed() - method removed


# Handover 0422: Entire TestContextTracking class removed - tests removed methods:
# - get_context_status() - method removed
# - update_context_usage() - method removed


class TestMultiProjectSupport:
    """Test multi-project and tenant isolation."""

    @pytest.mark.asyncio
    async def test_get_active_projects(self, orchestrator):
        """Test retrieving active projects for tenant."""
        mock_session = orchestrator._mock_session

        mock_projects = [MagicMock(status=ProjectStatus.ACTIVE.value), MagicMock(status=ProjectStatus.ACTIVE.value)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects

        result = await orchestrator.get_active_projects("tenant-key")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_resource_allocation(self, orchestrator):
        """Test resource allocation across projects."""
        mock_session = orchestrator._mock_session

        projects = [
            MagicMock(id="p1", priority=1, status=ProjectStatus.ACTIVE.value),
            MagicMock(id="p2", priority=2, status=ProjectStatus.ACTIVE.value),
            MagicMock(id="p3", priority=2, status=ProjectStatus.ACTIVE.value),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = projects
        mock_session.commit = AsyncMock()

        result = await orchestrator.allocate_resources("tenant", 120000)

        # Priority 1 gets 50%
        assert projects[0].context_budget == 60000
        # Priority 2 projects split remaining
        assert projects[1].context_budget == 30000
        assert projects[2].context_budget == 30000
        assert result["total_allocated"] == 120000

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, orchestrator):
        """Test projects are isolated by tenant."""
        mock_session = orchestrator._mock_session

        tenant1_projects = [MagicMock(tenant_key="tenant1"), MagicMock(tenant_key="tenant1")]

        mock_session.execute.return_value.scalars.return_value.all.return_value = tenant1_projects

        result = await orchestrator.get_tenant_projects("tenant1")
        assert len(result) == 2
        assert all(p.tenant_key == "tenant1" for p in result)


class TestAgentRoleTemplates:
    """Test agent mission templates."""

    def test_all_roles_have_templates(self):
        """Test all roles have mission templates."""
        orch = ProjectOrchestrator()

        for role in AgentRole:
            assert role in orch.AGENT_MISSIONS
            mission = orch.AGENT_MISSIONS[role]
            assert len(mission) > 100
            assert role.value in mission.lower()

    def test_template_content_quality(self):
        """Test mission templates have quality content."""
        orch = ProjectOrchestrator()

        # Check each role has appropriate keywords
        orch_mission = orch.AGENT_MISSIONS[AgentRole.ORCHESTRATOR]
        assert any(w in orch_mission.lower() for w in ["coordinate", "manage", "organize"])

        analyzer_mission = orch.AGENT_MISSIONS[AgentRole.ANALYZER]
        assert any(w in analyzer_mission.lower() for w in ["analyze", "understand", "design"])

        impl_mission = orch.AGENT_MISSIONS[AgentRole.IMPLEMENTER]
        assert any(w in impl_mission.lower() for w in ["implement", "code", "build"])

        test_mission = orch.AGENT_MISSIONS[AgentRole.TESTER]
        assert any(w in test_mission.lower() for w in ["test", "verify", "coverage"])

        review_mission = orch.AGENT_MISSIONS[AgentRole.REVIEWER]
        assert any(w in review_mission.lower() for w in ["review", "quality", "standards"])


class TestErrorHandling:
    """Test error conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_project_not_found(self, orchestrator):
        """Test handling of non-existent project."""
        mock_session = orchestrator._mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.activate_project("non-existent")

    # Handover 0422: test_agent_not_found removed - tested check_handoff_needed() which is removed
    # Handover 0422: test_handoff_reason_generation removed - tested _get_handoff_reason() which is removed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.orchestrator", "--cov-report=term-missing"])
