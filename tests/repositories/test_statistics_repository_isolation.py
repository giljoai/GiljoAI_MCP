"""
Tests for StatisticsRepository — tenant isolation and edge cases.

Split from test_statistics_repository.py for maintainability.
"""

import random

import pytest

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


# ============================================================================
# TENANT ISOLATION TESTS (CRITICAL SECURITY)
# ============================================================================


class TestTenantIsolation:
    """Test multi-tenant isolation across all statistics methods"""

    @pytest.mark.skip(reason="0750c3: project context stats format changed")
    @pytest.mark.asyncio
    @pytest.mark.tenant_isolation
    async def test_project_stats_tenant_isolation(self, db_session, stats_repo):
        """Test that project statistics respect tenant boundaries"""
        # Create projects for two different tenants
        project1 = Project(
            id="proj_tenant1",
            tenant_key="tenant_1",
            name="Tenant 1 Project",
            description="Test",
            mission="Test",
            status="active",
            series_number=random.randint(1, 999999),
        )
        project2 = Project(
            id="proj_tenant2",
            tenant_key="tenant_2",
            name="Tenant 2 Project",
            description="Test",
            mission="Test",
            status="active",
            series_number=random.randint(1, 999999),
        )
        db_session.add_all([project1, project2])
        await db_session.commit()

        # Verify tenant 1 can only see their project
        tenant1_count = await stats_repo.count_total_projects(db_session, "tenant_1")
        assert tenant1_count == 1

        # Verify tenant 2 can only see their project
        tenant2_count = await stats_repo.count_total_projects(db_session, "tenant_2")
        assert tenant2_count == 1

        # Verify context stats are isolated
        avg1, peak1 = await stats_repo.get_project_context_stats(db_session, "tenant_1")
        avg2, peak2 = await stats_repo.get_project_context_stats(db_session, "tenant_2")

        assert peak1 == 50000
        assert peak2 == 75000

    @pytest.mark.asyncio
    @pytest.mark.tenant_isolation
    async def test_message_stats_tenant_isolation(
        self, db_session, stats_repo, test_project_with_data, test_tenant_key
    ):
        """Test that message statistics respect tenant boundaries"""
        # Create messages for different tenants
        msg1 = Message(
            id="msg_tenant1",
            tenant_key=test_tenant_key,
            project_id=test_project_with_data.id,
            # NOTE: from_agent removed in Handover 0116
            to_agents=["agent2"],
            content="Tenant 1 message",
            message_type="direct",
            status="pending",
        )
        msg2 = Message(
            id="msg_tenant2",
            tenant_key="tenant_2",
            project_id=test_project_with_data.id,  # Same project ID, different tenant
            # NOTE: from_agent removed in Handover 0116
            to_agents=["agent4"],
            content="Tenant 2 message",
            message_type="direct",
            status="pending",
        )
        db_session.add_all([msg1, msg2])
        await db_session.commit()

        # Verify tenant isolation
        tenant1_count = await stats_repo.count_total_messages(db_session, test_tenant_key)
        tenant2_count = await stats_repo.count_total_messages(db_session, "tenant_2")

        assert tenant1_count == 1
        assert tenant2_count == 1

    @pytest.mark.asyncio
    @pytest.mark.tenant_isolation
    async def test_agent_stats_tenant_isolation(self, db_session, stats_repo, test_project_with_data):
        """Test that agent statistics respect tenant boundaries"""
        # Create agent jobs for different tenants
        job1 = AgentJob(
            job_id="job_tenant1",
            tenant_key="tenant_1",
            project_id=test_project_with_data.id,
            job_type="worker",
            mission="Test",
            status="active",
        )
        job2 = AgentJob(
            job_id="job_tenant2",
            tenant_key="tenant_2",
            project_id=test_project_with_data.id,
            job_type="worker",
            mission="Test",
            status="active",
        )
        db_session.add_all([job1, job2])

        # Create agent executions
        exec1 = AgentExecution(
            agent_id="agent_tenant1",
            job_id=job1.job_id,
            tenant_key="tenant_1",
            agent_display_name="worker",
            agent_name="Agent 1",
            status="waiting",
            progress=0,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        exec2 = AgentExecution(
            agent_id="agent_tenant2",
            job_id=job2.job_id,
            tenant_key="tenant_2",
            agent_display_name="worker",
            agent_name="Agent 2",
            status="waiting",
            progress=0,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add_all([exec1, exec2])
        await db_session.commit()

        # Verify tenant isolation
        tenant1_count = await stats_repo.count_total_agents(db_session, "tenant_1")
        tenant2_count = await stats_repo.count_total_agents(db_session, "tenant_2")

        assert tenant1_count == 1
        assert tenant2_count == 1


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_database_returns_zero(self, db_session, stats_repo, test_tenant_key):
        """Test that counting on empty database returns 0, not None"""
        count = await stats_repo.count_total_projects(db_session, test_tenant_key)
        assert count == 0  # Should return 0, not None

    @pytest.mark.asyncio
    async def test_nonexistent_tenant_returns_empty(self, db_session, stats_repo):
        """Test that queries with nonexistent tenant return empty results"""
        count = await stats_repo.count_total_projects(db_session, "nonexistent_tenant")
        assert count == 0

    @pytest.mark.asyncio
    async def test_pagination_with_limit_zero(self, db_session, stats_repo, test_tenant_key):
        """Test pagination with limit=0 returns empty list"""
        projects = await stats_repo.get_projects_with_pagination(db_session, test_tenant_key, limit=0)
        assert len(projects) == 0

    @pytest.mark.asyncio
    async def test_last_activity_with_no_messages(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data
    ):
        """Test getting last activity when no messages exist"""
        last_activity = await stats_repo.get_last_activity_for_project(
            db_session, test_tenant_key, test_project_with_data.id
        )
        assert last_activity is None  # No messages, so no activity
