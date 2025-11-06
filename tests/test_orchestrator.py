"""
Tests for ProjectOrchestrator class.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import ProjectStatus
from src.giljo_mcp.models import Project
from src.giljo_mcp.orchestrator import AgentRole, ContextStatus, ProjectOrchestrator
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest_asyncio.fixture
async def db_manager():
    """Create test database manager."""
    manager = DatabaseManager(database_url=PostgreSQLTestHelper.get_test_db_url(), is_async=True)
    await manager.create_tables_async()
    yield manager
    await manager.close_async()


@pytest_asyncio.fixture
async def orchestrator(db_manager):
    """Create orchestrator with test database."""
    with patch("src.giljo_mcp.orchestrator.get_db_manager", return_value=db_manager):
        orch = ProjectOrchestrator()
        yield orch


@pytest.mark.asyncio
class TestProjectLifecycle:
    """Test project lifecycle management."""

    async def test_create_project(self, orchestrator):
        """Test creating a new project."""
        project = await orchestrator.create_project(name="Test Project", mission="Test mission", context_budget=100000)

        assert project.name == "Test Project"
        assert project.mission == "Test mission"
        assert project.status == ProjectStatus.DRAFT.value
        assert project.context_budget == 100000
        assert project.context_used == 0
        assert project.tenant_key is not None

    async def test_activate_project(self, orchestrator):
        """Test activating a project."""
        # Create project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        # Activate it
        activated = await orchestrator.activate_project(project.id)

        assert activated.status == ProjectStatus.ACTIVE.value
        assert project.id in orchestrator._active_projects
        assert project.id in orchestrator._context_monitors

    async def test_deactivate_project(self, orchestrator):
        """Test deactivating an active project."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Deactivate it by setting status to inactive
        deactivated = await orchestrator.deactivate_project(project.id)

        assert deactivated.status == ProjectStatus.INACTIVE.value
        assert project.id not in orchestrator._context_monitors

    async def test_complete_project(self, orchestrator):
        """Test completing a project."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Complete it
        completed = await orchestrator.complete_project(project.id, summary="Project completed successfully")

        assert completed.status == ProjectStatus.COMPLETED.value
        assert completed.database_initialized_at is not None
        assert completed.meta_data["completion_summary"] == "Project completed successfully"
        assert project.id not in orchestrator._active_projects
        assert project.id not in orchestrator._context_monitors

    async def test_cancel_project(self, orchestrator):
        """Test cancelling an active project."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Cancel it
        cancelled = await orchestrator.cancel_project(project.id)

        assert cancelled.status == ProjectStatus.CANCELLED.value
        assert project.id not in orchestrator._active_projects
        assert project.id not in orchestrator._context_monitors

    async def test_invalid_state_transitions(self, orchestrator):
        """Test invalid state transitions raise errors."""
        # Create project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        # Cannot deactivate a non-active project
        with pytest.raises(ValueError, match="Can only deactivate active projects"):
            await orchestrator.deactivate_project(project.id)

        # Cannot complete non-active project
        with pytest.raises(ValueError, match="Can only complete active projects"):
            await orchestrator.complete_project(project.id)


@pytest.mark.asyncio
class TestAgentManagement:
    """Test agent spawning and management."""

    async def test_spawn_agent_with_template(self, orchestrator):
        """Test spawning agent with role template."""
        # Create project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        # Spawn analyzer agent
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        assert agent.name == "analyzer"
        assert agent.role == "analyzer"
        assert "Analyzer Agent" in agent.mission
        assert "Test Project" in agent.mission
        assert agent.status == "active"
        # Agent model doesn't have context_budget field

    async def test_spawn_agent_with_custom_mission(self, orchestrator):
        """Test spawning agent with custom mission."""
        # Create project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        # Spawn agent with custom mission
        custom_mission = "Custom mission for special agent"
        agent = await orchestrator.spawn_agent(project.id, AgentRole.IMPLEMENTER, custom_mission=custom_mission)

        assert custom_mission in agent.mission

    async def test_spawn_multiple_agents(self, orchestrator):
        """Test spawning multiple agents for a project."""
        # Create project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        # Spawn multiple agents
        agents = []
        for role in [AgentRole.ANALYZER, AgentRole.IMPLEMENTER, AgentRole.TESTER]:
            agent = await orchestrator.spawn_agent(project.id, role)
            agents.append(agent)

        # Get all project agents
        project_agents = await orchestrator.get_project_agents(project.id)

        assert len(project_agents) == 3
        assert {a.role for a in project_agents} == {"analyzer", "implementer", "tester"}


@pytest.mark.asyncio
class TestHandoffMechanism:
    """Test intelligent handoff between agents."""

    async def test_basic_handoff(self, orchestrator):
        """Test basic handoff between agents."""
        # Create project and agents
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        analyzer = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
        implementer = await orchestrator.spawn_agent(project.id, AgentRole.IMPLEMENTER)

        # Perform handoff
        context = {"design_doc": "Architecture design", "decisions": ["Use async", "SQLite for local"]}

        message = await orchestrator.handoff(analyzer.id, implementer.id, context)

        assert message.message_type == "handoff"
        assert message.from_agent_id == analyzer.id
        assert "implementer" in message.to_agents
        assert message.priority == "high"
        assert "transfer_data" in message.content

    async def test_handoff_check_threshold(self, orchestrator):
        """Test handoff threshold detection."""
        # Create project and agent
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")

        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # Update context to 79% - should not need handoff
        await orchestrator.update_context_usage(agent.id, 23700)  # 79% of 30000
        needs_handoff, reason = await orchestrator.check_handoff_needed(agent.id)
        assert not needs_handoff

        # Update to 81% - should need handoff
        await orchestrator.update_context_usage(agent.id, 600)  # Now 81%
        needs_handoff, reason = await orchestrator.check_handoff_needed(agent.id)
        assert needs_handoff
        assert "80% threshold" in reason

    async def test_handoff_validation(self, orchestrator):
        """Test handoff validation."""
        # Create two projects with agents
        project1 = await orchestrator.create_project(name="Project 1", mission="Mission 1")
        project2 = await orchestrator.create_project(name="Project 2", mission="Mission 2")

        agent1 = await orchestrator.spawn_agent(project1.id, AgentRole.ANALYZER)
        agent2 = await orchestrator.spawn_agent(project2.id, AgentRole.IMPLEMENTER)

        # Should fail - agents in different projects
        with pytest.raises(ValueError, match="same project"):
            await orchestrator.handoff(agent1.id, agent2.id, {})


@pytest.mark.asyncio
class TestContextTracking:
    """Test context usage tracking and indicators."""

    async def test_context_status_indicators(self, orchestrator):
        """Test context status color indicators."""
        # Test GREEN status (< 50%)
        status = orchestrator.get_context_status(4000, 10000)
        assert status == ContextStatus.GREEN

        # Test YELLOW status (50-80%)
        status = orchestrator.get_context_status(6000, 10000)
        assert status == ContextStatus.YELLOW

        status = orchestrator.get_context_status(7900, 10000)
        assert status == ContextStatus.YELLOW

        # Test RED status (> 80%)
        status = orchestrator.get_context_status(8100, 10000)
        assert status == ContextStatus.RED

    async def test_update_context_usage(self, orchestrator):
        """Test updating context usage for agent and project."""
        # Create project and agent
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # Update context usage
        updated_agent = await orchestrator.update_context_usage(agent.id, 5000)

        assert updated_agent.context_used == 5000

        # Check project context also updated
        async with orchestrator.db_manager.get_session_async() as session:
            from sqlalchemy import select

            result = await session.execute(select(Project).where(Project.id == project.id))
            updated_project = result.scalar_one()
            assert updated_project.context_used == 5000

    async def test_agent_context_status_details(self, orchestrator):
        """Test getting detailed context status."""
        # Create project and agent
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # Update context to 60%
        await orchestrator.update_context_usage(agent.id, 18000)

        # Get status details
        status = await orchestrator.get_agent_context_status(agent.id)

        assert status["agent_name"] == "analyzer"
        assert status["context_used"] == 18000
        assert status["context_budget"] == 30000
        assert status["usage_ratio"] == 0.6
        assert status["usage_percentage"] == 60.0
        assert status["status"] == "yellow"
        assert status["needs_handoff"] is False

    async def test_context_monitoring(self, orchestrator):
        """Test background context monitoring."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Create agent with high context usage
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
        await orchestrator.update_context_usage(agent.id, 25000)  # 83%

        # Monitor task should be running
        assert project.id in orchestrator._context_monitors
        monitor_task = orchestrator._context_monitors[project.id]
        assert not monitor_task.done()

        # Stop monitoring
        await orchestrator._stop_context_monitor(project.id)
        assert project.id not in orchestrator._context_monitors


@pytest.mark.asyncio
class TestMultiProjectSupport:
    """Test multi-project and multi-tenant support."""

    async def test_tenant_isolation(self, orchestrator):
        """Test projects are isolated by tenant."""
        tenant1 = "tenant-key-1"
        tenant2 = "tenant-key-2"

        # Create projects for different tenants
        await orchestrator.create_project(name="Tenant1 Project", mission="Mission 1", tenant_key=tenant1)
        await orchestrator.create_project(name="Tenant2 Project", mission="Mission 2", tenant_key=tenant2)

        # Get tenant1 projects
        tenant1_projects = await orchestrator.get_tenant_projects(tenant1)
        assert len(tenant1_projects) == 1
        assert tenant1_projects[0].name == "Tenant1 Project"

        # Get tenant2 projects
        tenant2_projects = await orchestrator.get_tenant_projects(tenant2)
        assert len(tenant2_projects) == 1
        assert tenant2_projects[0].name == "Tenant2 Project"

    async def test_concurrent_active_projects(self, orchestrator):
        """Test multiple concurrent active projects."""
        tenant_key = "test-tenant"

        # Create and activate multiple projects
        projects = []
        for i in range(3):
            project = await orchestrator.create_project(
                name=f"Project {i + 1}", mission=f"Mission {i + 1}", tenant_key=tenant_key
            )
            await orchestrator.activate_project(project.id)
            projects.append(project)

        # Get active projects
        active = await orchestrator.get_active_projects(tenant_key)
        assert len(active) == 3

        # All should be monitored
        for project in projects:
            assert project.id in orchestrator._context_monitors

    async def test_resource_allocation(self, orchestrator):
        """Test resource allocation for tenant."""
        tenant_key = "test-tenant"

        # Create projects with context usage
        for i in range(3):
            project = await orchestrator.create_project(
                name=f"Project {i + 1}", mission=f"Mission {i + 1}", tenant_key=tenant_key, context_budget=100000
            )
            if i < 2:  # Activate first 2
                await orchestrator.activate_project(project.id)

            # Simulate context usage
            agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
            await orchestrator.update_context_usage(agent.id, 20000)

        # Check resource allocation
        allocation = await orchestrator.allocate_resources(
            tenant_key, max_concurrent_projects=5, total_context_budget=500000
        )

        assert allocation["can_create_new"] is True
        assert allocation["active_projects"] == 2
        assert allocation["max_concurrent"] == 5
        assert allocation["total_context_used"] == 60000  # 3 * 20000
        assert allocation["remaining_budget"] == 440000

    async def test_max_concurrent_projects_limit(self, orchestrator):
        """Test maximum concurrent projects limit."""
        tenant_key = "test-tenant"

        # Create max concurrent projects
        for i in range(3):
            project = await orchestrator.create_project(
                name=f"Project {i + 1}", mission=f"Mission {i + 1}", tenant_key=tenant_key
            )
            await orchestrator.activate_project(project.id)

        # Check allocation with limit reached
        allocation = await orchestrator.allocate_resources(
            tenant_key,
            max_concurrent_projects=3,
            total_context_budget=500000,  # Same as created
        )

        assert allocation["can_create_new"] is False
        assert "Maximum 3 concurrent projects reached" in allocation["reason"]


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in orchestrator."""

    async def test_project_not_found(self, orchestrator):
        """Test handling of non-existent project."""
        fake_id = "non-existent-id"

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.activate_project(fake_id)

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.spawn_agent(fake_id, AgentRole.ANALYZER)

    async def test_agent_not_found(self, orchestrator):
        """Test handling of non-existent agent."""
        fake_id = "non-existent-agent"

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.update_context_usage(fake_id, 1000)

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.get_agent_context_status(fake_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
