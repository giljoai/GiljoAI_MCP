"""
Target specific uncovered lines for 90%+ coverage breakthrough.
Focuses on the easier lines to cover: 180, 223, 229-231, 258, 567-570, 593-596.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import ProjectStatus
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


class TestOrchestratorTargetedLines:
    """Target specific lines for 90%+ coverage."""

    async def test_deactivate_non_active_project(self, orchestrator):
        """Test deactivating non-active project error."""
        # Create project but keep it in DRAFT state (don't activate)
        project = await orchestrator.create_project(name="Deactivate Test", mission="Test deactivate")

        # Project is in DRAFT state, try to deactivate it
        with pytest.raises(ValueError, match="Cannot deactivate project"):
            await orchestrator.deactivate_project(project.id)

    async def test_line_223_archive_non_completed_project(self, orchestrator):
        """Target line 223: 'Can only archive completed projects' error."""
        # Create and activate project (but don't complete it)
        project = await orchestrator.create_project(name="Line 223 Test", mission="Test line 223")
        await orchestrator.activate_project(project.id)

        # Try to archive active project (should hit line 223)
        with pytest.raises(ValueError, match="Can only archive completed projects"):
            await orchestrator.archive_project(project.id)

    async def test_reactivate_inactive_project(self, orchestrator):
        """Test reactivating an inactive project."""
        # Create, activate, then deactivate project
        project = await orchestrator.create_project(name="Reactivate Test", mission="Test reactivate")
        await orchestrator.activate_project(project.id)
        await orchestrator.deactivate_project(project.id)

        # Reactivate project
        reactivated_project = await orchestrator.activate_project(project.id)
        assert reactivated_project.status == ProjectStatus.ACTIVE.value

    async def test_line_258_complete_project_without_summary(self, orchestrator):
        """Target line 258: complete project without summary."""
        # Create and activate project
        project = await orchestrator.create_project(name="Line 258 Test", mission="Test line 258")
        await orchestrator.activate_project(project.id)

        # Complete project without summary (should hit line 258)
        completed_project = await orchestrator.complete_project(project.id, summary=None)
        assert completed_project.status == ProjectStatus.COMPLETED.value
        # Verify no completion_summary in metadata
        assert "completion_summary" not in (completed_project.meta_data or {})

    async def test_lines_567_570_update_context_with_project(self, orchestrator):
        """Target lines 567-570: update_context_usage project update path."""
        # Create project and agent
        project = await orchestrator.create_project(name="Lines 567-570 Test", mission="Test lines 567-570")
        await orchestrator.activate_project(project.id)
        agent = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)

        # Update context usage (should hit lines 567-570 where it updates project total_context_used)
        updated_agent = await orchestrator.update_context_usage(agent.id, 15000)
        assert updated_agent.context_used == 15000

        # Verify project's total context was also updated
        projects = await orchestrator.get_active_projects()
        project_updated = next(p for p in projects if p.id == project.id)
        assert project_updated.context_used == 15000

    async def test_lines_593_596_get_active_projects_with_tenant(self, orchestrator):
        """Target lines 593-596: get_active_projects with specific tenant."""
        tenant_key = "specific-tenant-593-596"

        # Create and activate project for specific tenant
        project1 = await orchestrator.create_project(
            name="Lines 593-596 Test 1", mission="Test lines 593-596", tenant_key=tenant_key
        )
        await orchestrator.activate_project(project1.id)

        # Create project for different tenant
        project2 = await orchestrator.create_project(
            name="Lines 593-596 Test 2", mission="Test lines 593-596", tenant_key="different-tenant"
        )
        await orchestrator.activate_project(project2.id)

        # Get active projects for specific tenant (should hit lines 593-596)
        tenant_projects = await orchestrator.get_active_projects(tenant_key)
        assert len(tenant_projects) == 1
        assert tenant_projects[0].name == "Lines 593-596 Test 1"

    async def test_additional_edge_cases_for_coverage(self, orchestrator):
        """Additional edge cases to push coverage higher."""
        # Test complete project with empty string summary
        project1 = await orchestrator.create_project(name="Empty Summary", mission="Test empty summary")
        await orchestrator.activate_project(project1.id)
        completed = await orchestrator.complete_project(project1.id, summary="")
        assert completed.status == ProjectStatus.COMPLETED.value

        # Test deactivate project that is already inactive
        project2 = await orchestrator.create_project(name="Already Inactive", mission="Test already inactive")
        await orchestrator.activate_project(project2.id)
        await orchestrator.deactivate_project(project2.id)

        # Try to deactivate already inactive project
        with pytest.raises(ValueError, match="Cannot deactivate project"):
            await orchestrator.deactivate_project(project2.id)

    async def test_context_usage_edge_cases(self, orchestrator):
        """Test context usage update edge cases."""
        # Create project and multiple agents
        project = await orchestrator.create_project(name="Context Edge", mission="Test context edge cases")
        await orchestrator.activate_project(project.id)

        agent1 = await orchestrator.spawn_agent(project.id, AgentRole.ANALYZER)
        agent2 = await orchestrator.spawn_agent(project.id, AgentRole.IMPLEMENTER)

        # Update context for multiple agents to ensure project total is calculated correctly
        await orchestrator.update_context_usage(agent1.id, 10000)
        await orchestrator.update_context_usage(agent2.id, 8000)

        # Verify total context calculation
        projects = await orchestrator.get_active_projects()
        project_updated = next(p for p in projects if p.id == project.id)
        assert project_updated.context_used == 18000

    async def test_project_state_transition_edge_cases(self, orchestrator):
        """Test various project state transitions to hit more lines."""
        # Test completing -> archiving workflow
        project = await orchestrator.create_project(name="State Transitions", mission="Test state transitions")
        await orchestrator.activate_project(project.id)

        # Complete with detailed summary
        summary = "Detailed completion summary for testing"
        completed = await orchestrator.complete_project(project.id, summary=summary)
        assert completed.status == ProjectStatus.COMPLETED.value
        assert completed.meta_data["completion_summary"] == summary

        # Archive completed project
        archived = await orchestrator.archive_project(project.id)
        assert archived.status == ProjectStatus.ARCHIVED.value
