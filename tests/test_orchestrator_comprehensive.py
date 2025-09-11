"""
Comprehensive tests for ProjectOrchestrator with full functionality.
Tests state transitions, agent lifecycle, handoffs, context tracking, and multi-project support.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime
from uuid import uuid4

from src.giljo_mcp.orchestrator import (
    ProjectOrchestrator,
    ProjectState,
    AgentRole,
    ContextStatus
)


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
    with patch('src.giljo_mcp.orchestrator.get_db_manager', return_value=mock_db_manager):
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
    project.status = ProjectState.DRAFT.value
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
        with patch('src.giljo_mcp.models.Project', return_value=mock_project):
            result = await orchestrator.create_project(
                tenant_key="test-tenant",
                name="Test Project",
                mission="Test mission"
            )
        
        assert result == mock_project
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_project_from_draft(self, orchestrator, mock_project):
        """Test activating a project from draft state."""
        mock_project.status = ProjectState.DRAFT.value
        
        # Setup mock session
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.activate_project(mock_project.id)
        
        assert result == mock_project
        assert mock_project.status == ProjectState.ACTIVE.value
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_project_invalid_state(self, orchestrator, mock_project):
        """Test that activation fails from completed state."""
        mock_project.status = ProjectState.COMPLETED.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        with pytest.raises(ValueError, match="Cannot activate project"):
            await orchestrator.activate_project(mock_project.id)
    
    @pytest.mark.asyncio
    async def test_pause_active_project(self, orchestrator, mock_project):
        """Test pausing an active project."""
        mock_project.status = ProjectState.ACTIVE.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        # Mock agents query
        mock_agents = [MagicMock(status="active"), MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.pause_project(mock_project.id)
        
        assert result == mock_project
        assert mock_project.status == ProjectState.PAUSED.value
        for agent in mock_agents:
            assert agent.status == "paused"
    
    @pytest.mark.asyncio
    async def test_resume_paused_project(self, orchestrator, mock_project):
        """Test resuming a paused project."""
        mock_project.status = ProjectState.PAUSED.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.resume_project(mock_project.id)
        
        assert result == mock_project
        assert mock_project.status == ProjectState.ACTIVE.value
    
    @pytest.mark.asyncio
    async def test_complete_project(self, orchestrator, mock_project):
        """Test completing an active project."""
        mock_project.status = ProjectState.ACTIVE.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        # Mock agents
        mock_agents = [MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.complete_project(mock_project.id, summary="Project completed")
        
        assert result == mock_project
        assert mock_project.status == ProjectState.COMPLETED.value
        assert mock_project.completion_summary == "Project completed"
        assert mock_agents[0].status == "completed"
    
    @pytest.mark.asyncio
    async def test_archive_completed_project(self, orchestrator, mock_project):
        """Test archiving a completed project."""
        mock_project.status = ProjectState.COMPLETED.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.archive_project(mock_project.id)
        
        assert result == mock_project
        assert mock_project.status == ProjectState.ARCHIVED.value
    
    @pytest.mark.asyncio
    async def test_state_transition_validation(self, orchestrator, mock_project):
        """Test invalid state transitions are prevented."""
        # Can't pause a draft project
        mock_project.status = ProjectState.DRAFT.value
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        with pytest.raises(ValueError, match="Cannot pause project"):
            await orchestrator.pause_project(mock_project.id)
        
        # Can't archive non-completed project
        mock_project.status = ProjectState.ACTIVE.value
        
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
            None  # Second call for existing agent check
        ]
        
        mock_agent = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('src.giljo_mcp.models.Agent', return_value=mock_agent):
            result = await orchestrator.spawn_agent(
                project_id=mock_project.id,
                agent_name="analyzer_1",
                role=AgentRole.ANALYZER
            )
        
        assert result == mock_agent
        assert mock_agent.role == AgentRole.ANALYZER.value
        assert "analyzer responsible for" in mock_agent.mission
    
    @pytest.mark.asyncio
    async def test_spawn_agent_custom_mission(self, orchestrator, mock_project):
        """Test spawning agent with custom mission overrides template."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            None
        ]
        
        mock_agent = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('src.giljo_mcp.models.Agent', return_value=mock_agent):
            result = await orchestrator.spawn_agent(
                project_id=mock_project.id,
                agent_name="custom_agent",
                role=AgentRole.IMPLEMENTER,
                custom_mission="Custom implementation task"
            )
        
        assert mock_agent.mission == "Custom implementation task"
    
    @pytest.mark.asyncio
    async def test_spawn_duplicate_agent_prevented(self, orchestrator, mock_project, mock_agent):
        """Test that duplicate agents are not created."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        # Existing agent found
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            mock_agent  # Existing agent
        ]
        
        with pytest.raises(ValueError, match="already exists"):
            await orchestrator.spawn_agent(
                project_id=mock_project.id,
                agent_name=mock_agent.name,
                role=AgentRole.TESTER
            )
    
    @pytest.mark.asyncio
    async def test_get_project_agents(self, orchestrator, mock_project):
        """Test retrieving all agents for a project."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_agents = [
            MagicMock(name="agent1", role=AgentRole.ANALYZER.value),
            MagicMock(name="agent2", role=AgentRole.IMPLEMENTER.value)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        
        result = await orchestrator.get_project_agents(mock_project.id)
        
        assert len(result) == 2
        assert result[0].name == "agent1"
        assert result[1].name == "agent2"


class TestHandoffMechanism:
    """Test agent handoff functionality."""
    
    @pytest.mark.asyncio
    async def test_handoff_creates_context_package(self, orchestrator, mock_project):
        """Test handoff creates proper context package."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        # Create mock agents
        from_agent = MagicMock()
        from_agent.name = "analyzer"
        from_agent.role = AgentRole.ANALYZER.value
        from_agent.status = "active"
        from_agent.context_used = 45000
        from_agent.context_budget = 50000
        
        to_agent = MagicMock()
        to_agent.name = "implementer"
        to_agent.role = AgentRole.IMPLEMENTER.value
        to_agent.status = "inactive"
        
        # Setup mock queries
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            from_agent,
            to_agent
        ]
        
        # Mock message creation
        mock_message = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('src.giljo_mcp.models.Message', return_value=mock_message):
            result = await orchestrator.handoff(
                project_id=mock_project.id,
                from_agent_name="analyzer",
                to_agent_name="implementer",
                context={
                    "analysis_results": "System architecture defined",
                    "key_decisions": ["Use async", "SQLAlchemy ORM"]
                }
            )
        
        assert result["success"] is True
        assert from_agent.status == "completed"
        assert to_agent.status == "active"
        
        # Check message was created
        mock_session.add.assert_called_once()
        created_message = mock_session.add.call_args[0][0]
        assert created_message.from_agent == "analyzer"
        assert created_message.to_agent == "implementer"
        assert "analysis_results" in created_message.content
    
    @pytest.mark.asyncio
    async def test_check_handoff_needed_at_threshold(self, orchestrator, mock_agent):
        """Test handoff detection at 80% threshold."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        # Set agent at 80% context usage
        mock_agent.context_used = 40000
        mock_agent.context_budget = 50000
        mock_agent.status = "active"
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await orchestrator.check_handoff_needed(mock_agent.id)
        
        assert result["needs_handoff"] is True
        assert result["reason"] == "Context usage at 80%"
        assert result["context_percentage"] == 80.0
    
    @pytest.mark.asyncio
    async def test_check_handoff_not_needed(self, orchestrator, mock_agent):
        """Test handoff not needed when under threshold."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        # Set agent at 50% context usage
        mock_agent.context_used = 25000
        mock_agent.context_budget = 50000
        mock_agent.status = "active"
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await orchestrator.check_handoff_needed(mock_agent.id)
        
        assert result["needs_handoff"] is False
        assert result["context_percentage"] == 50.0
    
    @pytest.mark.asyncio
    async def test_handoff_with_error_status(self, orchestrator, mock_agent):
        """Test handoff triggered by error status."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_agent.status = "error"
        mock_agent.context_used = 10000
        mock_agent.context_budget = 50000
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await orchestrator.check_handoff_needed(mock_agent.id)
        
        assert result["needs_handoff"] is True
        assert "encountered error" in result["reason"]


class TestContextTracking:
    """Test context usage tracking and monitoring."""
    
    @pytest.mark.asyncio
    async def test_update_context_usage(self, orchestrator, mock_agent):
        """Test updating agent context usage."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_agent.context_used = 10000
        mock_agent.context_budget = 50000
        mock_project = MagicMock()
        mock_project.context_used = 20000
        
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_agent,
            mock_project
        ]
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.update_context_usage(
            agent_id=mock_agent.id,
            tokens_used=5000
        )
        
        assert result["agent_total"] == 15000
        assert result["project_total"] == 25000
        assert result["status"] == ContextStatus.YELLOW  # 30% usage
        assert mock_agent.context_used == 15000
        assert mock_project.context_used == 25000
    
    @pytest.mark.asyncio
    async def test_get_agent_context_status(self, orchestrator, mock_agent):
        """Test getting agent context status with color coding."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_agent.context_used = 42500
        mock_agent.context_budget = 50000
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await orchestrator.get_agent_context_status(mock_agent.id)
        
        assert result["agent_id"] == mock_agent.id
        assert result["context_used"] == 42500
        assert result["context_budget"] == 50000
        assert result["percentage"] == 85.0
        assert result["status"] == ContextStatus.RED
        assert result["needs_handoff"] is True
    
    @pytest.mark.asyncio
    async def test_context_monitor_task(self, orchestrator, mock_project):
        """Test context monitoring background task."""
        mock_project.id = "test-project-id"
        mock_project.status = ProjectState.ACTIVE.value
        
        # Add project to active projects
        orchestrator._active_projects[mock_project.id] = mock_project
        
        # Create mock agents with varying context usage
        mock_agents = [
            MagicMock(id="agent1", context_used=45000, context_budget=50000, status="active"),
            MagicMock(id="agent2", context_used=20000, context_budget=50000, status="active")
        ]
        
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        
        # Mock check_handoff_needed
        with patch.object(orchestrator, 'check_handoff_needed', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = [
                {"needs_handoff": True, "reason": "Context at 90%"},
                {"needs_handoff": False}
            ]
            
            # Start monitor
            monitor_task = await orchestrator._start_context_monitor(mock_project.id)
            
            # Let it run one iteration
            await asyncio.sleep(0.1)
            
            # Stop monitor
            await orchestrator._stop_context_monitor(mock_project.id)
            
            # Verify check was called for high-usage agent
            mock_check.assert_called()


class TestMultiProjectSupport:
    """Test multi-project and multi-tenant functionality."""
    
    @pytest.mark.asyncio
    async def test_get_active_projects_by_tenant(self, orchestrator):
        """Test retrieving active projects for a tenant."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_projects = [
            MagicMock(id="proj1", name="Project 1", status=ProjectState.ACTIVE.value),
            MagicMock(id="proj2", name="Project 2", status=ProjectState.ACTIVE.value)
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
            MagicMock(status=ProjectState.DRAFT.value),
            MagicMock(status=ProjectState.ACTIVE.value),
            MagicMock(status=ProjectState.COMPLETED.value)
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
        mock_project.status = ProjectState.ACTIVE.value
        mock_project.priority = 1
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_project]
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.allocate_resources(
            tenant_key="test-tenant",
            total_context_budget=100000
        )
        
        assert result["total_allocated"] == 100000
        assert result["projects"]["proj1"]["allocated"] == 100000
        assert mock_project.context_budget == 100000
    
    @pytest.mark.asyncio
    async def test_allocate_resources_multiple_projects(self, orchestrator):
        """Test resource allocation across multiple projects by priority."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        
        mock_projects = [
            MagicMock(id="proj1", status=ProjectState.ACTIVE.value, priority=1),
            MagicMock(id="proj2", status=ProjectState.ACTIVE.value, priority=2),
            MagicMock(id="proj3", status=ProjectState.ACTIVE.value, priority=2)
        ]
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.allocate_resources(
            tenant_key="test-tenant",
            total_context_budget=120000
        )
        
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
        tenant1_projects = [
            MagicMock(tenant_key="tenant1", name="T1 Project")
        ]
        
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
    
    @pytest.mark.asyncio
    async def test_agent_not_found(self, orchestrator):
        """Test handling of non-existent agent."""
        mock_session = AsyncMock()
        orchestrator.db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await orchestrator.check_handoff_needed("non-existent-agent")
        
        assert result["needs_handoff"] is False
        assert result["error"] == "Agent not found"
    
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
        many_projects = [MagicMock(status=ProjectState.ACTIVE.value) for _ in range(10)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = many_projects
        
        # Should handle gracefully
        result = await orchestrator.get_active_projects("tenant")
        assert len(result) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.orchestrator", "--cov-report=term-missing"])