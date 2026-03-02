"""
Tests for StatisticsRepository — agent, message, task statistics and health checks.

Split from test_statistics_repository.py for maintainability.
"""

from datetime import datetime, timedelta, timezone

import pytest


# ============================================================================
# AGENT STATISTICS TESTS
# ============================================================================


class TestAgentStatisticsDomain:
    """Test agent statistics operations"""

    @pytest.mark.asyncio
    async def test_count_total_agents(self, db_session, stats_repo, test_tenant_key, test_agent_executions):
        """Test counting total agents for tenant"""
        count = await stats_repo.count_total_agents(db_session, test_tenant_key)
        assert count == 3  # Three agent executions in fixture

    @pytest.mark.asyncio
    async def test_count_active_agents(self, db_session, stats_repo, test_tenant_key, test_agent_executions):
        """Test counting active agents (waiting or working status)"""
        count = await stats_repo.count_active_agents(db_session, test_tenant_key)
        assert count == 2  # Two agents with 'waiting' and 'working' status

    @pytest.mark.asyncio
    async def test_count_completed_agents(self, db_session, stats_repo, test_tenant_key, test_agent_executions):
        """Test counting completed agents"""
        count = await stats_repo.count_completed_agents(db_session, test_tenant_key)
        assert count == 1  # One agent with 'complete' status

    @pytest.mark.asyncio
    async def test_get_agent_executions_with_filters(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_agent_executions
    ):
        """Test getting agent executions with various filters"""
        # Test without filters
        all_agents = await stats_repo.get_agent_executions_with_filters(db_session, test_tenant_key, limit=100)
        assert len(all_agents) == 3

        # Test with project filter
        project_agents = await stats_repo.get_agent_executions_with_filters(
            db_session, test_tenant_key, project_id=test_project_with_data.id
        )
        assert len(project_agents) == 3

        # Test with status filter (active = waiting + working)
        active_agents = await stats_repo.get_agent_executions_with_filters(db_session, test_tenant_key, status="active")
        assert len(active_agents) == 2

        # Test with specific status
        working_agents = await stats_repo.get_agent_executions_with_filters(
            db_session, test_tenant_key, status="working"
        )
        assert len(working_agents) == 1

    @pytest.mark.asyncio
    async def test_count_messages_received_by_agent(self, db_session, stats_repo, test_tenant_key, test_messages):
        """Test counting messages received by an agent"""
        count = await stats_repo.count_messages_received_by_agent(db_session, test_tenant_key, "test_agent_2")
        assert count == 4  # All test messages are to 'test_agent_2'

    @pytest.mark.asyncio
    async def test_get_agent_job_by_job_id(self, db_session, stats_repo, test_tenant_key, test_agent_executions):
        """Test getting AgentJob by job_id"""
        job, _ = test_agent_executions
        retrieved_job = await stats_repo.get_agent_job_by_job_id(db_session, test_tenant_key, job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.project_id == job.project_id


# ============================================================================
# MESSAGE STATISTICS TESTS
# ============================================================================


class TestMessageStatisticsDomain:
    """Test message statistics operations"""

    @pytest.mark.asyncio
    async def test_count_total_messages(self, db_session, stats_repo, test_tenant_key, test_messages):
        """Test counting total messages for tenant"""
        count = await stats_repo.count_total_messages(db_session, test_tenant_key)
        assert count == 4  # Four messages in fixture

    @pytest.mark.asyncio
    async def test_count_messages_by_status(self, db_session, stats_repo, test_tenant_key, test_messages):
        """Test counting messages by status"""
        pending_count = await stats_repo.count_messages_by_status(db_session, test_tenant_key, "pending")
        acknowledged_count = await stats_repo.count_messages_by_status(db_session, test_tenant_key, "acknowledged")
        completed_count = await stats_repo.count_messages_by_status(db_session, test_tenant_key, "completed")
        failed_count = await stats_repo.count_messages_by_status(db_session, test_tenant_key, "failed")

        assert pending_count == 1
        assert acknowledged_count == 1
        assert completed_count == 1
        assert failed_count == 1

    @pytest.mark.asyncio
    async def test_count_messages_with_filters(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_messages
    ):
        """Test counting messages with filters"""
        # Test project filter
        count = await stats_repo.count_messages_with_filters(
            db_session, test_tenant_key, project_id=test_project_with_data.id
        )
        assert count == 4

        # Test time filter (messages created in last 5 hours)
        since = datetime.now(timezone.utc) - timedelta(hours=5)
        count = await stats_repo.count_messages_with_filters(db_session, test_tenant_key, since=since)
        assert count == 4  # All messages within 5 hours

    @pytest.mark.asyncio
    async def test_count_messages_by_status_with_filters(
        self, db_session, stats_repo, test_tenant_key, test_project_with_data, test_messages
    ):
        """Test counting messages by status with filters"""
        count = await stats_repo.count_messages_by_status_with_filters(
            db_session, test_tenant_key, status="pending", project_id=test_project_with_data.id
        )
        assert count == 1

        # Test with time filter
        since = datetime.now(timezone.utc) - timedelta(hours=2)
        count = await stats_repo.count_messages_by_status_with_filters(
            db_session, test_tenant_key, status="pending", since=since
        )
        assert count >= 1  # At least one pending message in last 2 hours


# ============================================================================
# TASK STATISTICS TESTS
# ============================================================================


class TestTaskStatisticsDomain:
    """Test task statistics operations"""

    pass


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthCheckDomain:
    """Test health check operations"""

    @pytest.mark.asyncio
    async def test_execute_health_check(self, db_session, stats_repo):
        """Test database health check"""
        is_healthy = await stats_repo.execute_health_check(db_session)
        assert is_healthy is True
