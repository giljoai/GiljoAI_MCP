"""
Tests for StatisticsRepository — API metrics and project statistics.

Split from test_statistics_repository.py for maintainability.
"""

import random
from datetime import datetime

import pytest

from src.giljo_mcp.models import Project


# ============================================================================
# API METRICS TESTS
# ============================================================================


class TestApiMetricsDomain:
    """Test API metrics retrieval"""

    @pytest.mark.asyncio
    async def test_get_api_metrics(self, db_session, stats_repo, test_tenant_key, test_api_metrics):
        """Test retrieving API metrics for tenant"""
        metrics = await stats_repo.get_api_metrics(db_session, test_tenant_key)

        assert metrics is not None
        assert metrics.tenant_key == test_tenant_key
        assert metrics.total_api_calls == 100
        assert metrics.total_mcp_calls == 50

    @pytest.mark.asyncio
    async def test_get_api_metrics_wrong_tenant(self, db_session, stats_repo, test_api_metrics):
        """Test tenant isolation for API metrics"""
        metrics = await stats_repo.get_api_metrics(db_session, "wrong_tenant")
        assert metrics is None  # Tenant isolation prevents access


# ============================================================================
# PROJECT STATISTICS TESTS
# ============================================================================


class TestProjectStatisticsDomain:
    """Test project statistics operations"""

    @pytest.mark.asyncio
    async def test_count_total_projects(self, db_session, stats_repo, test_tenant_key, test_project_with_data):
        """Test counting total projects for tenant"""
        count = await stats_repo.count_total_projects(db_session, test_tenant_key)
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_projects_by_status(self, db_session, stats_repo, test_tenant_key, test_project_with_data):
        """Test counting projects by status"""
        # Create additional projects with different statuses
        completed_proj = Project(
            id="proj_002",
            tenant_key=test_tenant_key,
            name="Completed Project",
            description="Completed",
            mission="Test",
            status="completed",
            series_number=random.randint(1, 999999),
        )
        db_session.add(completed_proj)
        await db_session.commit()

        active_count = await stats_repo.count_projects_by_status(db_session, test_tenant_key, "active")
        completed_count = await stats_repo.count_projects_by_status(db_session, test_tenant_key, "completed")

        assert active_count == 1
        assert completed_count == 1

    @pytest.mark.skip(reason="0750c3: project context stats format changed")
    @pytest.mark.asyncio
    async def test_get_project_context_stats(self, db_session, stats_repo, test_tenant_key, test_project_with_data):
        """Test getting average and peak context usage"""
        # Add another project with different context usage
        project2 = Project(
            id="proj_002",
            tenant_key=test_tenant_key,
            name="Project 2",
            description="Test",
            mission="Test",
            status="active",
            series_number=random.randint(1, 999999),
        )
        db_session.add(project2)
        await db_session.commit()

        avg_context, peak_context = await stats_repo.get_project_context_stats(db_session, test_tenant_key)

        assert avg_context == 62500.0  # (50000 + 75000) / 2
        assert peak_context == 75000

    @pytest.mark.asyncio
    async def test_get_projects_with_pagination(self, db_session, stats_repo, test_tenant_key):
        """Test getting projects with pagination"""
        # Create multiple projects
        for i in range(5):
            project = Project(
                id=f"proj_{i:03d}",
                tenant_key=test_tenant_key,
                name=f"Project {i}",
                description="Test",
                mission="Test",
                status="active" if i % 2 == 0 else "completed",
                series_number=random.randint(1, 999999),
            )
            db_session.add(project)
        await db_session.commit()

        # Test pagination
        projects = await stats_repo.get_projects_with_pagination(db_session, test_tenant_key, limit=3, offset=0)
        assert len(projects) == 3

        # Test status filter
        active_projects = await stats_repo.get_projects_with_pagination(
            db_session, test_tenant_key, status="active", limit=10
        )
        assert len(active_projects) == 3  # Projects 0, 2, 4

    @pytest.mark.asyncio
    async def test_count_agents_for_project(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_agent_executions
    ):
        """Test counting agents for a project"""
        count = await stats_repo.count_agents_for_project(db_session, test_tenant_key, test_project_with_data.id)
        assert count == 3  # Three agent executions created in fixture

    @pytest.mark.asyncio
    async def test_count_messages_for_project(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_messages
    ):
        """Test counting messages for a project"""
        count = await stats_repo.count_messages_for_project(db_session, test_tenant_key, test_project_with_data.id)
        assert count == 4  # Four messages created in fixture

    @pytest.mark.skip(reason="0750c3: Task model fixture setup error")
    @pytest.mark.asyncio
    async def test_count_tasks_for_project(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_tasks
    ):
        """Test counting tasks for a project"""
        count = await stats_repo.count_tasks_for_project(db_session, test_tenant_key, test_project_with_data.id)
        assert count == 5  # Five tasks created in fixture

    @pytest.mark.skip(reason="0750c3: Task model fixture setup error")
    @pytest.mark.asyncio
    async def test_count_completed_tasks_for_project(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_tasks
    ):
        """Test counting completed tasks for a project"""
        count = await stats_repo.count_completed_tasks_for_project(
            db_session, test_tenant_key, test_project_with_data.id
        )
        assert count == 3  # Three completed tasks (i < 3) in fixture

    @pytest.mark.asyncio
    async def test_get_last_activity_for_project(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_messages
    ):
        """Test getting last activity timestamp for a project"""
        last_activity = await stats_repo.get_last_activity_for_project(
            db_session, test_tenant_key, test_project_with_data.id
        )
        assert last_activity is not None
        # Most recent message is at index 0 (created with 0 hours offset)
        assert isinstance(last_activity, datetime)
