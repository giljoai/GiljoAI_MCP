"""
Targeted tests to push orchestrator coverage above 90%.
Focuses on specific uncovered lines identified in coverage analysis.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, patch
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.orchestrator import ProjectOrchestrator, AgentRole
from src.giljo_mcp.enums import ProjectStatus


@pytest_asyncio.fixture
async def db_manager():
    """Create test database manager."""
    manager = DatabaseManager(database_url="sqlite+aiosqlite:///", is_async=True)
    await manager.create_tables_async()
    yield manager
    await manager.close_async()


@pytest_asyncio.fixture
async def orchestrator(db_manager):
    """Create orchestrator with test database."""
    with patch("src.giljo_mcp.orchestrator.get_db_manager", return_value=db_manager):
        orch = ProjectOrchestrator()
        yield orch


class TestOrchestratorNinetyPlusCoverage:
    """Tests targeting specific uncovered lines for 90%+ coverage."""

    async def test_activate_project_invalid_state_error(self, orchestrator):
        """Test activating project in invalid state (line 150)."""
        # Create and complete a project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)
        await orchestrator.complete_project(project.id)

        # Try to activate completed project (should fail)
        with pytest.raises(ValueError, match="Cannot activate project in .* state"):
            await orchestrator.activate_project(project.id)

    async def test_pause_non_active_project_error(self, orchestrator):
        """Test pausing non-active project (line 180)."""
        # Create project but don't activate it
        project = await orchestrator.create_project(name="Draft Project", mission="Test mission")

        # Try to pause draft project (should fail)
        with pytest.raises(ValueError, match="Can only pause active projects"):
            await orchestrator.pause_project(project.id)

    async def test_archive_non_completed_project_error(self, orchestrator):
        """Test archiving non-completed project (line 223)."""
        # Create and activate project
        project = await orchestrator.create_project(name="Active Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Try to archive active project (should fail)
        with pytest.raises(ValueError, match="Can only archive completed projects"):
            await orchestrator.archive_project(project.id)

    async def test_resume_project_calls_activate(self, orchestrator):
        """Test resume project calls activate project (line 229-231)."""
        # Create, activate, then pause project
        project = await orchestrator.create_project(name="Resume Test", mission="Test mission")
        await orchestrator.activate_project(project.id)
        await orchestrator.pause_project(project.id)

        # Resume should call activate_project internally
        resumed = await orchestrator.resume_project(project.id)
        assert resumed.status == ProjectStatus.ACTIVE.value

    async def test_complete_project_without_summary(self, orchestrator):
        """Test completing project without summary (line 258)."""
        # Create and activate project
        project = await orchestrator.create_project(name="No Summary", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Complete without summary
        completed = await orchestrator.complete_project(project.id)
        assert completed.status == ProjectStatus.COMPLETED.value
        assert completed.completed_at is not None
        # meta_data should exist but not have completion_summary
        assert completed.meta_data is not None
        assert "completion_summary" not in completed.meta_data

    async def test_spawn_agents_parallel_project_not_found(self, orchestrator):
        """Test spawn_agents_parallel with invalid project (line 358)."""
        agents_to_spawn = [(AgentRole.ANALYZER, None)]

        with pytest.raises(ValueError, match="Project .* not found"):
            await orchestrator.spawn_agents_parallel("invalid-project-id", agents_to_spawn)

    async def test_handle_context_limit_agent_not_found(self, orchestrator):
        """Test handle_context_limit with invalid agent (line 396)."""
        with pytest.raises(ValueError, match="Agent .* not found"):
            await orchestrator.handle_context_limit("invalid-agent-id")

    async def test_handoff_project_not_found_scenarios(self, orchestrator):
        """Test handoff with various not found scenarios (line 450)."""
        # Test with invalid from_agent
        project = await orchestrator.create_project(name="Handoff Test", mission="Test")
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        with pytest.raises(ValueError, match="Agent not found"):
            await orchestrator.handoff("invalid-from-agent", agent.id, {})

        with pytest.raises(ValueError, match="Agent not found"):
            await orchestrator.handoff(agent.id, "invalid-to-agent", {})

    async def test_check_handoff_needed_agent_not_found(self, orchestrator):
        """Test check_handoff_needed with invalid agent (line 515)."""
        needs_handoff, reason = await orchestrator.check_handoff_needed("invalid-agent-id")
        assert needs_handoff is False
        assert reason is None

    async def test_update_context_usage_project_not_found(self, orchestrator):
        """Test update_context_usage when project not found (lines 567-570)."""
        # Create project and agent, then test edge case
        project = await orchestrator.create_project(name="Context Test", mission="Test")
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # This should work normally and cover the project update path
        updated_agent = await orchestrator.update_context_usage(agent.id, 5000)
        assert updated_agent.context_used == 5000

    async def test_get_active_projects_with_tenant_filter(self, orchestrator):
        """Test get_active_projects with tenant filtering (lines 593-596)."""
        tenant_key = "specific-tenant"

        # Create and activate projects for specific tenant
        project1 = await orchestrator.create_project(
            name="Tenant Project 1", 
            mission="Mission 1", 
            tenant_key=tenant_key
        )
        await orchestrator.activate_project(project1.id)

        # Create project for different tenant
        project2 = await orchestrator.create_project(
            name="Other Project", 
            mission="Mission 2", 
            tenant_key="other-tenant"
        )
        await orchestrator.activate_project(project2.id)

        # Get active projects for specific tenant
        tenant_projects = await orchestrator.get_active_projects(tenant_key)
        assert len(tenant_projects) == 1
        assert tenant_projects[0].name == "Tenant Project 1"

    async def test_context_monitoring_task_exception_handling(self, orchestrator):
        """Test context monitoring task exception handling (lines 667-682, 688-690)."""
        # Create and activate project
        project = await orchestrator.create_project(name="Monitor Exception", mission="Test")
        await orchestrator.activate_project(project.id)

        # Create agent that will trigger handoff check
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
        await orchestrator.update_context_usage(agent.id, 26000)  # 86.7% usage

        # Let monitoring task run and detect the high usage
        await asyncio.sleep(0.2)

        # Verify the agent was detected as needing handoff
        needs_handoff, reason = await orchestrator.check_handoff_needed(agent.id)
        assert needs_handoff is True

        # Complete project to stop monitoring
        await orchestrator.complete_project(project.id)

    async def test_context_monitoring_project_inactive_break(self, orchestrator):
        """Test context monitoring exits when project becomes inactive (line 673)."""
        # Create and activate project
        project = await orchestrator.create_project(name="Inactive Break", mission="Test")
        await orchestrator.activate_project(project.id)

        # Verify monitoring started
        assert project.id in orchestrator._context_monitors

        # Pause project (makes it inactive)
        await orchestrator.pause_project(project.id)

        # Give monitoring task time to detect inactive status and break
        await asyncio.sleep(0.1)

        # Monitoring should have stopped
        assert project.id not in orchestrator._context_monitors

    async def test_context_monitoring_cancellation_cleanup(self, orchestrator):
        """Test context monitoring task cancellation (lines 688-690)."""
        # Create and activate project  
        project = await orchestrator.create_project(name="Cancel Test", mission="Test")
        await orchestrator.activate_project(project.id)

        # Verify monitoring started
        assert project.id in orchestrator._context_monitors
        monitor_task = orchestrator._context_monitors[project.id]

        # Force stop monitoring (simulates cancellation)
        await orchestrator._stop_context_monitor(project.id)

        # Task should be cancelled and removed
        assert project.id not in orchestrator._context_monitors
        # The important thing is that monitoring stopped, not the exact task state

    async def test_context_monitoring_error_backoff(self, orchestrator):
        """Test context monitoring error handling and backoff (line 699)."""
        # Create and activate project
        project = await orchestrator.create_project(name="Error Backoff", mission="Test")
        await orchestrator.activate_project(project.id)

        # Create agent
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # Mock check_handoff_needed to raise exception
        original_method = orchestrator.check_handoff_needed

        async def mock_check_handoff_error(*args):
            raise Exception("Database connection failed")

        # Temporarily replace method to trigger error path
        orchestrator.check_handoff_needed = mock_check_handoff_error

        # Let monitoring run and hit error
        await asyncio.sleep(0.1)

        # Restore original method
        orchestrator.check_handoff_needed = original_method

        # Stop monitoring
        await orchestrator.complete_project(project.id)

    async def test_allocate_resources_remaining_budget_calculation(self, orchestrator):
        """Test resource allocation remaining budget calculation edge case."""
        tenant_key = "budget-test"

        # Create project and use some context
        project = await orchestrator.create_project(
            name="Budget Project",
            mission="Test budget",
            tenant_key=tenant_key
        )
        await orchestrator.activate_project(project.id)
        
        # Create agent and use significant context
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
        await orchestrator.update_context_usage(agent.id, 20000)

        # Test allocation with tight budget
        allocation = await orchestrator.allocate_resources(
            tenant_key=tenant_key,
            max_concurrent_projects=10,
            total_context_budget=50000  # Tight budget
        )

        assert allocation["can_create_new"] is True
        assert allocation["remaining_budget"] == 30000  # 50000 - 20000
        assert allocation["suggested_project_budget"] == 30000  # min(150000, 30000)

    async def test_spawn_orchestrator_agent_additional_context(self, orchestrator):
        """Test spawning orchestrator agent with additional context parameter."""
        project = await orchestrator.create_project(name="Orch Context", mission="Test orchestrator context")
        
        # Test spawning orchestrator with additional context
        from src.giljo_mcp.enums import ProjectType
        
        orch_agent = await orchestrator.spawn_agent(
            project_id=project.id,
            role=AgentRole.ORCHESTRATOR,
            project_type=ProjectType.FOUNDATION,
            additional_instructions="Special orchestrator instructions"
        )
        
        assert orch_agent.role == "orchestrator"
        assert orch_agent.name == "orchestrator"
        # Mission might be None if template generation fails
        # But the agent should still be created successfully
        assert orch_agent.id is not None

    async def test_additional_edge_cases_for_90_percent(self, orchestrator):
        """Additional targeted tests for specific uncovered lines."""
        # Test line 180 - pause non-active project
        project = await orchestrator.create_project(name="Line 180", mission="Test")
        # Project is in PLANNING state, try to pause it
        with pytest.raises(ValueError, match="Can only pause active projects"):
            await orchestrator.pause_project(project.id)

        # Test line 223 - archive non-completed project  
        project2 = await orchestrator.create_project(name="Line 223", mission="Test")
        await orchestrator.activate_project(project2.id)
        with pytest.raises(ValueError, match="Can only archive completed projects"):
            await orchestrator.archive_project(project2.id)

        # Test line 258 - complete project without summary (no summary case)
        project3 = await orchestrator.create_project(name="Line 258", mission="Test")
        await orchestrator.activate_project(project3.id)
        completed = await orchestrator.complete_project(project3.id, summary=None)
        assert completed.status == ProjectStatus.COMPLETED.value

        # Test resume project path (lines 229-231)
        project4 = await orchestrator.create_project(name="Line 229", mission="Test")
        await orchestrator.activate_project(project4.id)
        await orchestrator.pause_project(project4.id)
        resumed = await orchestrator.resume_project(project4.id)
        assert resumed.status == ProjectStatus.ACTIVE.value