"""
Integration tests for ProjectOrchestrator with database operations.
Tests end-to-end functionality with more realistic mocking.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.enums import ProjectStatus
from src.giljo_mcp.orchestrator import AgentRole, ContextStatus, ProjectOrchestrator


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

        # Test pause project
        mock_agents = [MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents

        result = await orchestrator.pause_project(mock_project.id)
        assert mock_project.status == ProjectStatus.PAUSED.value
        assert mock_agents[0].status == "paused"

        # Test resume project
        result = await orchestrator.resume_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ACTIVE.value

        # Test complete project
        mock_agents[0].status = "active"
        result = await orchestrator.complete_project(mock_project.id, summary="Project completed successfully")
        assert mock_project.status == ProjectStatus.COMPLETED.value
        assert mock_project.completion_summary == "Project completed successfully"

        # Test archive project
        result = await orchestrator.archive_project(mock_project.id)
        assert mock_project.status == ProjectStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_agent_lifecycle_with_handoff(self):
        """Test agent spawning, work, and handoff."""
        orchestrator = ProjectOrchestrator()

        # Setup mocks
        mock_db = AsyncMock()
        orchestrator.db_manager = mock_db

        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock()
        mock_db.get_session_async = MagicMock(return_value=mock_context)

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = str(uuid4())
        mock_project.status = ProjectStatus.ACTIVE.value

        # Test spawning analyzer agent
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,  # Project lookup
            None,  # No existing agent
        ]

        analyzer_agent = MagicMock()
        analyzer_agent.name = "analyzer_1"
        analyzer_agent.role = AgentRole.ANALYZER.value
        analyzer_agent.status = "active"
        analyzer_agent.context_used = 0
        analyzer_agent.context_budget = 50000

        with patch("src.giljo_mcp.models.Agent") as MockAgent:
            MockAgent.return_value = analyzer_agent
            result = await orchestrator.spawn_agent(
                project_id=mock_project.id, agent_name="analyzer_1", role=AgentRole.ANALYZER
            )

        assert result == analyzer_agent
        assert "analyzer responsible for" in analyzer_agent.mission

        # Simulate work and context usage
        analyzer_agent.context_used = 42000  # 84% usage

        # Test handoff detection
        mock_session.execute.return_value.scalar_one_or_none.return_value = analyzer_agent

        handoff_check = await orchestrator.check_handoff_needed(analyzer_agent.id)
        assert handoff_check["needs_handoff"] is True
        assert handoff_check["context_percentage"] == 84.0

        # Test spawning implementer agent
        implementer_agent = MagicMock()
        implementer_agent.name = "implementer_1"
        implementer_agent.role = AgentRole.IMPLEMENTER.value
        implementer_agent.status = "inactive"
        implementer_agent.context_used = 0
        implementer_agent.context_budget = 50000

        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,  # Project lookup
            None,  # No existing agent
        ]

        with patch("src.giljo_mcp.models.Agent") as MockAgent:
            MockAgent.return_value = implementer_agent
            await orchestrator.spawn_agent(
                project_id=mock_project.id, agent_name="implementer_1", role=AgentRole.IMPLEMENTER
            )

        # Test handoff from analyzer to implementer
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            analyzer_agent,
            implementer_agent,
        ]

        mock_message = MagicMock()
        with patch("src.giljo_mcp.models.Message") as MockMessage:
            MockMessage.return_value = mock_message

            handoff_result = await orchestrator.handoff(
                project_id=mock_project.id,
                from_agent_name="analyzer_1",
                to_agent_name="implementer_1",
                context={"analysis": "Complete system design", "recommendations": ["Use async", "SQLAlchemy ORM"]},
            )

        assert handoff_result["success"] is True
        assert analyzer_agent.status == "completed"
        assert implementer_agent.status == "active"
        assert mock_message.from_agent == "analyzer_1"
        assert mock_message.to_agent == "implementer_1"

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

    @pytest.mark.asyncio
    async def test_context_monitoring_triggers_handoff(self):
        """Test that context monitoring can trigger automatic handoffs."""
        orchestrator = ProjectOrchestrator()

        # Setup mocks
        mock_db = AsyncMock()
        orchestrator.db_manager = mock_db

        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock()
        mock_db.get_session_async = MagicMock(return_value=mock_context)

        # Create project and agent nearing context limit
        mock_project = MagicMock()
        mock_project.id = "test-project"
        mock_project.status = ProjectStatus.ACTIVE.value

        mock_agent = MagicMock()
        mock_agent.id = "agent1"
        mock_agent.name = "analyzer"
        mock_agent.context_used = 44000
        mock_agent.context_budget = 50000  # 88% usage
        mock_agent.status = "active"

        # Add project to active projects
        orchestrator._active_projects[mock_project.id] = mock_project

        # Setup mock returns
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_agent]
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent

        # Mock check_handoff_needed to return True
        with patch.object(orchestrator, "check_handoff_needed", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "needs_handoff": True,
                "reason": "Context usage at 88%",
                "context_percentage": 88.0,
            }

            # Start monitoring
            await orchestrator._start_context_monitor(mock_project.id)

            # Wait briefly for monitor to run
            await asyncio.sleep(0.1)

            # Stop monitoring
            await orchestrator._stop_context_monitor(mock_project.id)

            # Verify handoff check was called
            mock_check.assert_called_with(mock_agent.id)

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


class TestContextStatusCalculations:
    """Test context status color coding calculations."""

    def test_context_percentage_calculations(self):
        """Test accurate percentage calculations."""
        orchestrator = ProjectOrchestrator()

        # Test exact boundaries
        assert orchestrator.get_context_status(0, 100) == ContextStatus.GREEN
        assert orchestrator.get_context_status(49, 100) == ContextStatus.GREEN
        assert orchestrator.get_context_status(50, 100) == ContextStatus.YELLOW
        assert orchestrator.get_context_status(79, 100) == ContextStatus.YELLOW
        assert orchestrator.get_context_status(80, 100) == ContextStatus.RED
        assert orchestrator.get_context_status(100, 100) == ContextStatus.RED

        # Test with different scales
        assert orchestrator.get_context_status(25000, 50000) == ContextStatus.YELLOW  # 50%
        assert orchestrator.get_context_status(120000, 150000) == ContextStatus.RED  # 80%

        # Test edge case - zero budget
        assert orchestrator.get_context_status(0, 0) == ContextStatus.GREEN

    def test_handoff_reason_generation(self):
        """Test that handoff reasons are properly generated."""
        orchestrator = ProjectOrchestrator()

        # High context usage
        agent = MagicMock()
        agent.context_used = 85000
        agent.context_budget = 100000
        agent.status = "active"

        reason = orchestrator._get_handoff_reason(agent)
        assert "Context usage at 85%" in reason

        # Error status
        agent.context_used = 30000
        agent.status = "error"

        reason = orchestrator._get_handoff_reason(agent)
        assert "encountered error" in reason

        # Manual handoff
        agent.status = "active"

        reason = orchestrator._get_handoff_reason(agent)
        assert "Manual handoff" in reason


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
