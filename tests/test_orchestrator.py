"""
Tests for ProjectOrchestrator class.

Handover 0422: Cleaned up tests for removed dead token budget code.
Removed tests for: update_context_usage(), get_context_status(), check_handoff_needed(),
get_agent_context_status(), handoff(), _context_monitors, _start_context_monitor(),
_stop_context_monitor(), _monitor_project_context(), _get_handoff_reason(),
estimate_message_tokens(), _trigger_auto_succession()
"""

from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import ProjectStatus
from src.giljo_mcp.models import Project
from src.giljo_mcp.orchestrator import AgentRole, ProjectOrchestrator
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

    async def test_deactivate_project(self, orchestrator):
        """Test deactivating an active project."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Deactivate it by setting status to inactive
        deactivated = await orchestrator.deactivate_project(project.id)

        assert deactivated.status == ProjectStatus.INACTIVE.value

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

    async def test_cancel_project(self, orchestrator):
        """Test cancelling an active project."""
        # Create and activate project
        project = await orchestrator.create_project(name="Test Project", mission="Test mission")
        await orchestrator.activate_project(project.id)

        # Cancel it
        cancelled = await orchestrator.cancel_project(project.id)

        assert cancelled.status == ProjectStatus.CANCELLED.value
        assert project.id not in orchestrator._active_projects

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


# Handover 0422: Entire TestHandoffMechanism class removed - tests removed methods:
# - handoff() - method removed
# - update_context_usage() - method removed
# - check_handoff_needed() - method removed


# Handover 0422: Entire TestContextTracking class removed - tests removed methods:
# - get_context_status() - method removed
# - update_context_usage() - method removed
# - get_agent_context_status() - method removed
# - _context_monitors attribute removed
# - _stop_context_monitor() - method removed


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
