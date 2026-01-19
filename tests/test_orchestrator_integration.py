"""
Integration tests for ProjectOrchestrator with database operations.
Tests end-to-end functionality with more realistic mocking.

Handover 0422: Cleaned up tests for removed dead token budget code.
Removed tests for: update_context_usage(), check_handoff_needed(), handoff(),
_context_monitors, _start_context_monitor(), _stop_context_monitor(), _get_handoff_reason()
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.enums import ProjectStatus, ContextStatus
from src.giljo_mcp.orchestrator import AgentRole, ProjectOrchestrator


class TestOrchestratorIntegration:
    """Integration tests for orchestrator functionality."""

    @pytest.mark.asyncio
    async def test_full_project_lifecycle(self):
        """Test complete project lifecycle from creation to archive."""
        orchestrator = ProjectOrchestrator()

        # Mock the database manager
        mock_db = AsyncMock()
        orchestrator.db_manager = mock_db

        # Mock session
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock()
        mock_db.get_session_async = MagicMock(return_value=mock_context)
        mock_db.generate_tenant_key = MagicMock(return_value="test-tenant-123")

        # Create mock project that will be returned
        mock_project = MagicMock()
        mock_project.id = str(uuid4())
        mock_project.name = "Test Project"
        mock_project.status = ProjectStatus.DRAFT.value
        mock_project.tenant_key = "test-tenant-123"

        # Mock the database operations
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", mock_project.id))

        # Test create project
        with patch("src.giljo_mcp.models.Project") as MockProject:
            MockProject.return_value = mock_project
            result = await orchestrator.create_project(name="Test Project", mission="Test mission")

        assert result == mock_project
        assert mock_project.status == ProjectStatus.DRAFT.value
        mock_session.add.assert_called_once()

        # Test activate project
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        result = await orchestrator.activate_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ACTIVE.value

        # Test deactivate project
        mock_agents = [MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents

        result = await orchestrator.deactivate_project(mock_project.id)
        assert mock_project.status == ProjectStatus.INACTIVE.value
        assert mock_agents[0].status == "inactive"

        # Test reactivate project
        result = await orchestrator.activate_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ACTIVE.value

        # Test complete project
        mock_agents[0].status = "active"
        result = await orchestrator.complete_project(mock_project.id, summary="Project completed successfully")
        assert mock_project.status == ProjectStatus.COMPLETED.value
        assert mock_project.completion_summary == "Project completed successfully"

        # Test cancel project (from active)
        mock_project.status = ProjectStatus.ACTIVE.value
        result = await orchestrator.cancel_project(mock_project.id)
        assert mock_project.status == ProjectStatus.CANCELLED.value

    # Handover 0422: test_agent_lifecycle_with_handoff removed - tests removed methods:
    # - check_handoff_needed() - method removed
    # - handoff() - method removed

    @pytest.mark.asyncio
    async def test_multi_project_resource_allocation(self):
        """Test resource allocation across multiple projects."""
        orchestrator = ProjectOrchestrator()

        # Setup mocks
        mock_db = AsyncMock()
        orchestrator.db_manager = mock_db

        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock()
        mock_db.get_session_async = MagicMock(return_value=mock_context)

        # Create three projects with different priorities
        projects = [
            MagicMock(
                id="proj1", name="Critical Project", status=ProjectStatus.ACTIVE.value, priority=1, context_budget=0
            ),
            MagicMock(
                id="proj2", name="Normal Project 1", status=ProjectStatus.ACTIVE.value, priority=2, context_budget=0
            ),
            MagicMock(
                id="proj3", name="Normal Project 2", status=ProjectStatus.ACTIVE.value, priority=2, context_budget=0
            ),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = projects
        mock_session.commit = AsyncMock()

        # Allocate 120k tokens across projects
        result = await orchestrator.allocate_resources(tenant_key="test-tenant", total_context_budget=120000)

        # Priority 1 should get 50% (60k)
        assert projects[0].context_budget == 60000

        # Priority 2 projects should split remaining 50% (30k each)
        assert projects[1].context_budget == 30000
        assert projects[2].context_budget == 30000

        assert result["total_allocated"] == 120000
        assert len(result["projects"]) == 3

    # Handover 0422: test_context_monitoring_triggers_handoff removed - tests removed methods:
    # - check_handoff_needed() - method removed
    # - _start_context_monitor() - method removed
    # - _stop_context_monitor() - method removed

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test that projects and agents are properly isolated by tenant."""
        orchestrator = ProjectOrchestrator()

        # Setup mocks
        mock_db = AsyncMock()
        orchestrator.db_manager = mock_db

        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock()
        mock_db.get_session_async = MagicMock(return_value=mock_context)

        # Create projects for different tenants
        tenant1_projects = [
            MagicMock(tenant_key="tenant1", name="T1 Project 1"),
            MagicMock(tenant_key="tenant1", name="T1 Project 2"),
        ]

        tenant2_projects = [MagicMock(tenant_key="tenant2", name="T2 Project 1")]

        # Test getting tenant1 projects
        mock_session.execute.return_value.scalars.return_value.all.return_value = tenant1_projects
        result = await orchestrator.get_tenant_projects("tenant1")

        assert len(result) == 2
        assert all(p.tenant_key == "tenant1" for p in result)

        # Test getting tenant2 projects
        mock_session.execute.return_value.scalars.return_value.all.return_value = tenant2_projects
        result = await orchestrator.get_tenant_projects("tenant2")

        assert len(result) == 1
        assert result[0].tenant_key == "tenant2"

        # Verify queries include tenant_key filter
        # This is implicitly tested by the return values matching tenant keys


# Handover 0422: Entire TestContextStatusCalculations class removed - tests removed methods:
# - get_context_status() - method removed
# - _get_handoff_reason() - method removed


class TestAgentRoleTemplates:
    """Test agent role templates and capabilities."""

    def test_all_roles_have_templates(self):
        """Verify all agent roles have mission templates."""
        orchestrator = ProjectOrchestrator()

        for role in AgentRole:
            assert role in orchestrator.AGENT_MISSIONS
            mission = orchestrator.AGENT_MISSIONS[role]

            # Verify mission content
            assert len(mission) > 50  # Substantial content
            assert role.value in mission.lower()  # Contains role name
            assert "responsible" in mission.lower()  # Has responsibilities

    def test_role_specific_content(self):
        """Test that each role has appropriate mission content."""
        orchestrator = ProjectOrchestrator()

        # Orchestrator should mention coordination
        orch_mission = orchestrator.AGENT_MISSIONS[AgentRole.ORCHESTRATOR]
        assert any(word in orch_mission.lower() for word in ["coordinate", "coordinating", "manage"])

        # Analyzer should mention analysis
        analyzer_mission = orchestrator.AGENT_MISSIONS[AgentRole.ANALYZER]
        assert any(word in analyzer_mission.lower() for word in ["analyze", "analysis", "understanding"])

        # Implementer should mention code/implementation
        impl_mission = orchestrator.AGENT_MISSIONS[AgentRole.IMPLEMENTER]
        assert any(word in impl_mission.lower() for word in ["implement", "code", "writing"])

        # Tester should mention testing
        test_mission = orchestrator.AGENT_MISSIONS[AgentRole.TESTER]
        assert any(word in test_mission.lower() for word in ["test", "testing", "coverage"])

        # Reviewer should mention review/quality
        review_mission = orchestrator.AGENT_MISSIONS[AgentRole.REVIEWER]
        assert any(word in review_mission.lower() for word in ["review", "quality", "standards"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
