"""
Final comprehensive test suite for ProjectOrchestrator.
Tests all functionality with proper mocking and coverage tracking.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from src.giljo_mcp.orchestrator import (
    ProjectOrchestrator,
    ProjectState,
    AgentRole,
    ContextStatus
)


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
        
        await orchestrator.create_project(
            name="Test Project",
            mission="Test mission"
        )
        
        assert created_project is not None
        assert created_project.tenant_key == "test-tenant-123"
        assert created_project.status == ProjectState.DRAFT.value
        assert created_project.name == "Test Project"
    
    @pytest.mark.asyncio
    async def test_state_transitions(self, orchestrator):
        """Test valid state transitions through project lifecycle."""
        mock_session = orchestrator._mock_session
        
        # Create mock project
        mock_project = MagicMock()
        mock_project.id = str(uuid4())
        mock_project.status = ProjectState.DRAFT.value
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        mock_session.commit = AsyncMock()
        
        # Draft -> Active
        await orchestrator.activate_project(mock_project.id)
        assert mock_project.status == ProjectState.ACTIVE.value
        
        # Active -> Paused (with agents)
        mock_agents = [MagicMock(status="active")]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_agents
        
        await orchestrator.pause_project(mock_project.id)
        assert mock_project.status == ProjectState.PAUSED.value
        assert mock_agents[0].status == "paused"
        
        # Paused -> Active
        await orchestrator.resume_project(mock_project.id)
        assert mock_project.status == ProjectState.ACTIVE.value
        
        # Active -> Completed
        mock_agents[0].status = "active"
        await orchestrator.complete_project(mock_project.id, "Done")
        assert mock_project.status == ProjectState.COMPLETED.value
        assert mock_agents[0].status == "completed"
        
        # Completed -> Archived
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        await orchestrator.archive_project(mock_project.id)
        assert mock_project.status == ProjectState.ARCHIVED.value
    
    @pytest.mark.asyncio
    async def test_invalid_state_transitions(self, orchestrator):
        """Test that invalid state transitions raise errors."""
        mock_session = orchestrator._mock_session
        mock_project = MagicMock()
        mock_project.id = str(uuid4())
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project
        
        # Can't pause draft project
        mock_project.status = ProjectState.DRAFT.value
        with pytest.raises(ValueError, match="Cannot pause"):
            await orchestrator.pause_project(mock_project.id)
        
        # Can't activate completed project
        mock_project.status = ProjectState.COMPLETED.value
        with pytest.raises(ValueError, match="Cannot activate"):
            await orchestrator.activate_project(mock_project.id)
        
        # Can't archive active project
        mock_project.status = ProjectState.ACTIVE.value
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
            None  # No existing agent
        ]
        
        # Capture created agent
        created_agent = None
        def capture_add(obj):
            nonlocal created_agent
            created_agent = obj
        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        await orchestrator.spawn_agent(
            project_id=mock_project.id,
            role=AgentRole.ANALYZER
        )
        
        assert created_agent is not None
        assert created_agent.role == AgentRole.ANALYZER.value
        assert "analyzer responsible for" in created_agent.mission
        assert created_agent.name == f"analyzer_{mock_project.id[:8]}"
    
    @pytest.mark.asyncio
    async def test_spawn_agent_custom_mission(self, orchestrator):
        """Test custom mission overrides template."""
        mock_session = orchestrator._mock_session
        
        mock_project = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            None
        ]
        
        created_agent = None
        def capture_add(obj):
            nonlocal created_agent
            created_agent = obj
        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        await orchestrator.spawn_agent(
            project_id=str(uuid4()),
            role=AgentRole.TESTER,
            custom_mission="Custom test mission"
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
            existing_agent  # Agent already exists
        ]
        
        with pytest.raises(ValueError, match="already exists"):
            await orchestrator.spawn_agent(
                project_id=str(uuid4()),
                role=AgentRole.IMPLEMENTER
            )


class TestHandoffMechanism:
    """Test agent handoff functionality."""
    
    @pytest.mark.asyncio
    async def test_handoff_workflow(self, orchestrator):
        """Test complete handoff workflow."""
        mock_session = orchestrator._mock_session
        
        mock_project = MagicMock()
        from_agent = MagicMock()
        from_agent.name = "analyzer"
        from_agent.status = "active"
        from_agent.context_used = 45000
        from_agent.context_budget = 50000
        
        to_agent = MagicMock()
        to_agent.name = "implementer"
        to_agent.status = "inactive"
        
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_project,
            from_agent,
            to_agent
        ]
        
        created_message = None
        def capture_add(obj):
            nonlocal created_message
            created_message = obj
        mock_session.add = MagicMock(side_effect=capture_add)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        result = await orchestrator.handoff(
            project_id=str(uuid4()),
            from_agent_name="analyzer",
            to_agent_name="implementer",
            context={"analysis": "complete"}
        )
        
        assert result["success"] is True
        assert from_agent.status == "completed"
        assert to_agent.status == "active"
        assert created_message.from_agent == "analyzer"
        assert created_message.to_agent == "implementer"
    
    @pytest.mark.asyncio
    async def test_check_handoff_needed(self, orchestrator):
        """Test handoff detection logic."""
        mock_session = orchestrator._mock_session
        mock_agent = MagicMock()
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        # Test at 80% threshold
        mock_agent.context_used = 40000
        mock_agent.context_budget = 50000
        mock_agent.status = "active"
        
        result = await orchestrator.check_handoff_needed("agent-id")
        assert result["needs_handoff"] is True
        assert result["context_percentage"] == 80.0
        
        # Test below threshold
        mock_agent.context_used = 20000
        
        result = await orchestrator.check_handoff_needed("agent-id")
        assert result["needs_handoff"] is False
        assert result["context_percentage"] == 40.0
        
        # Test error status triggers handoff
        mock_agent.status = "error"
        
        result = await orchestrator.check_handoff_needed("agent-id")
        assert result["needs_handoff"] is True


class TestContextTracking:
    """Test context usage tracking."""
    
    def test_context_status_indicators(self):
        """Test color-coded status indicators."""
        orch = ProjectOrchestrator()
        
        # Test boundaries
        assert orch.get_context_status(0, 100) == ContextStatus.GREEN
        assert orch.get_context_status(49, 100) == ContextStatus.GREEN
        assert orch.get_context_status(50, 100) == ContextStatus.YELLOW
        assert orch.get_context_status(79, 100) == ContextStatus.YELLOW
        assert orch.get_context_status(80, 100) == ContextStatus.RED
        assert orch.get_context_status(100, 100) == ContextStatus.RED
        
        # Test with larger numbers
        assert orch.get_context_status(25000, 50000) == ContextStatus.YELLOW
        assert orch.get_context_status(120000, 150000) == ContextStatus.RED
        
        # Test zero budget edge case
        assert orch.get_context_status(50, 0) == ContextStatus.RED
    
    @pytest.mark.asyncio
    async def test_update_context_usage(self, orchestrator):
        """Test updating agent and project context."""
        mock_session = orchestrator._mock_session
        
        mock_agent = MagicMock()
        mock_agent.context_used = 10000
        mock_agent.context_budget = 50000
        
        mock_project = MagicMock()
        mock_project.context_used = 20000
        
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_agent,
            mock_project
        ]
        mock_session.commit = AsyncMock()
        
        result = await orchestrator.update_context_usage("agent-id", 5000)
        
        assert mock_agent.context_used == 15000
        assert mock_project.context_used == 25000
        assert result["agent_total"] == 15000
        assert result["project_total"] == 25000
        assert result["status"] == ContextStatus.YELLOW  # 30% usage


class TestMultiProjectSupport:
    """Test multi-project and tenant isolation."""
    
    @pytest.mark.asyncio
    async def test_get_active_projects(self, orchestrator):
        """Test retrieving active projects for tenant."""
        mock_session = orchestrator._mock_session
        
        mock_projects = [
            MagicMock(status=ProjectState.ACTIVE.value),
            MagicMock(status=ProjectState.ACTIVE.value)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_projects
        
        result = await orchestrator.get_active_projects("tenant-key")
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_resource_allocation(self, orchestrator):
        """Test resource allocation across projects."""
        mock_session = orchestrator._mock_session
        
        projects = [
            MagicMock(id="p1", priority=1, status=ProjectState.ACTIVE.value),
            MagicMock(id="p2", priority=2, status=ProjectState.ACTIVE.value),
            MagicMock(id="p3", priority=2, status=ProjectState.ACTIVE.value)
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
        
        tenant1_projects = [
            MagicMock(tenant_key="tenant1"),
            MagicMock(tenant_key="tenant1")
        ]
        
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
    
    @pytest.mark.asyncio
    async def test_agent_not_found(self, orchestrator):
        """Test handling of non-existent agent."""
        mock_session = orchestrator._mock_session
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await orchestrator.check_handoff_needed("non-existent")
        assert result["needs_handoff"] is False
        assert result["error"] == "Agent not found"
    
    def test_handoff_reason_generation(self):
        """Test handoff reason generation."""
        orch = ProjectOrchestrator()
        
        agent = MagicMock()
        agent.context_used = 85000
        agent.context_budget = 100000
        agent.status = "active"
        
        reason = orch._get_handoff_reason(agent)
        assert "85%" in reason
        
        agent.status = "error"
        reason = orch._get_handoff_reason(agent)
        assert "error" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.giljo_mcp.orchestrator", "--cov-report=term-missing"])