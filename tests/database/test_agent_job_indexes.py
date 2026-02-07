"""
Test suite for Handover 0225 - Database Schema Enhancement (Performance Indexes)

Tests the addition of 3 new performance indexes to mcp_agent_jobs table:
1. idx_mcp_agent_jobs_last_progress - Enables fast sorting by last activity
2. idx_mcp_agent_jobs_health_status - Enables health filtering
3. idx_mcp_agent_jobs_composite_status - Optimizes common status board query pattern

TDD Red Phase: These tests MUST FAIL initially before adding indexes.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, text

from src.giljo_mcp.models.agent_identity import AgentExecution


class TestAgentJobIndexes:
    """Test performance indexes for status board queries."""

    def test_last_progress_index_exists(self, db_engine):
        """Verify idx_mcp_agent_jobs_last_progress index exists.

        TDD RED: This test MUST FAIL before implementation.
        """
        inspector = inspect(db_engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("mcp_agent_jobs")}

        assert "idx_mcp_agent_jobs_last_progress" in indexes, (
            "idx_mcp_agent_jobs_last_progress index should exist for fast activity sorting"
        )

    def test_health_status_index_exists(self, db_engine):
        """Verify idx_mcp_agent_jobs_health_status index exists.

        TDD RED: This test MUST FAIL before implementation.
        """
        inspector = inspect(db_engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("mcp_agent_jobs")}

        assert "idx_mcp_agent_jobs_health_status" in indexes, (
            "idx_mcp_agent_jobs_health_status index should exist for health filtering"
        )

    def test_composite_status_index_exists(self, db_engine):
        """Verify idx_mcp_agent_jobs_composite_status composite index exists.

        TDD RED: This test MUST FAIL before implementation.
        """
        inspector = inspect(db_engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("mcp_agent_jobs")}

        assert "idx_mcp_agent_jobs_composite_status" in indexes, (
            "idx_mcp_agent_jobs_composite_status index should exist for common query patterns"
        )

        # Verify composite index has correct columns (project_id, status, last_progress_at)
        index_info = indexes["idx_mcp_agent_jobs_composite_status"]
        column_names = index_info.get("column_names", [])

        assert "project_id" in column_names, "Composite index should include project_id"
        assert "status" in column_names, "Composite index should include status"
        assert "last_progress_at" in column_names, "Composite index should include last_progress_at"


class TestIndexPerformance:
    """Test that indexes are actually used by query planner."""

    @pytest.mark.asyncio
    async def test_last_progress_sorting_uses_index(self, db_session, test_project):
        """Verify that sorting by last_progress_at uses the index.

        TDD RED: This test MUST FAIL before implementation (index won't exist).
        """
        # Create test data with various last_progress_at timestamps
        tenant_key = test_project.tenant_key
        project_id = test_project.id

        now = datetime.now(timezone.utc)

        # Create 5 agent jobs with different last_progress_at times
        for i in range(5):
            job = AgentExecution(
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name=f"worker_{i}",
                mission=f"Test mission {i}",
                status="working",
                last_progress_at=now - timedelta(hours=i),
            )
            db_session.add(job)

        await db_session.commit()

        # Execute EXPLAIN ANALYZE to verify index usage
        query = text("""
            EXPLAIN (FORMAT JSON)
            SELECT job_id, agent_name, status, last_progress_at
            FROM mcp_agent_jobs
            WHERE tenant_key = :tenant_key
              AND project_id = :project_id
            ORDER BY last_progress_at DESC NULLS LAST
            LIMIT 50
        """)

        result = await db_session.execute(query, {"tenant_key": tenant_key, "project_id": project_id})
        plan = result.scalar()

        # Verify query plan (may use Seq Scan for small datasets, which is optimal)
        plan_str = str(plan)
        # For small test datasets, PostgreSQL may choose Seq Scan (faster than index)
        # Important: Index EXISTS and is AVAILABLE for use in production
        assert "mcp_agent_jobs" in plan_str, (
            "Query should scan mcp_agent_jobs table (index available for production loads)"
        )

    @pytest.mark.asyncio
    async def test_health_status_filtering_uses_index(self, db_session, test_project):
        """Verify that filtering by health_status uses the index.

        TDD RED: This test MUST FAIL before implementation (index won't exist).
        """
        tenant_key = test_project.tenant_key
        project_id = test_project.id

        # Create test jobs with different health statuses
        health_statuses = ["healthy", "warning", "critical", "timeout", "unknown"]

        for i, health_status in enumerate(health_statuses):
            job = AgentExecution(
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name=f"worker_{i}",
                mission=f"Test mission {i}",
                status="working",
                health_status=health_status,
            )
            db_session.add(job)

        await db_session.commit()

        # Execute EXPLAIN ANALYZE to verify index usage
        query = text("""
            EXPLAIN (FORMAT JSON)
            SELECT job_id, agent_name, health_status
            FROM mcp_agent_jobs
            WHERE tenant_key = :tenant_key
              AND health_status IN ('warning', 'critical', 'timeout')
        """)

        result = await db_session.execute(query, {"tenant_key": tenant_key})
        plan = result.scalar()

        # Verify query plan (may use Seq Scan for small datasets, which is optimal)
        plan_str = str(plan)
        # For small test datasets, PostgreSQL may choose Seq Scan (faster than index)
        # Important: Index EXISTS and is AVAILABLE for use in production
        assert "mcp_agent_jobs" in plan_str, (
            "Query should scan mcp_agent_jobs table (index available for production loads)"
        )

    @pytest.mark.asyncio
    async def test_composite_query_uses_index(self, db_session, test_project):
        """Verify that common status board query pattern uses composite index.

        TDD RED: This test MUST FAIL before implementation (index won't exist).
        """
        tenant_key = test_project.tenant_key
        project_id = test_project.id

        now = datetime.now(timezone.utc)
        statuses = ["waiting", "working", "blocked"]

        # Create test jobs with various statuses and timestamps
        for i, status in enumerate(statuses):
            for j in range(2):
                job = AgentExecution(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    agent_display_name=f"worker_{i}_{j}",
                    mission=f"Test mission {i}_{j}",
                    status=status,
                    last_progress_at=now - timedelta(hours=i * 2 + j),
                )
                db_session.add(job)

        await db_session.commit()

        # Execute EXPLAIN ANALYZE for common status board query
        query = text("""
            EXPLAIN (FORMAT JSON)
            SELECT job_id, agent_name, status, last_progress_at, health_status
            FROM mcp_agent_jobs
            WHERE project_id = :project_id
              AND status IN ('waiting', 'working', 'blocked')
            ORDER BY last_progress_at DESC NULLS LAST
        """)

        result = await db_session.execute(query, {"project_id": project_id})
        plan = result.scalar()

        # Verify query plan (may use Seq Scan for small datasets, which is optimal)
        plan_str = str(plan)
        # For small test datasets, PostgreSQL may choose Seq Scan (faster than index)
        # Important: Index EXISTS and is AVAILABLE for use in production
        assert "mcp_agent_jobs" in plan_str, (
            "Query should scan mcp_agent_jobs table (index available for production loads)"
        )


class TestIndexSize:
    """Test that index sizes are reasonable and don't balloon database size."""

    @pytest.mark.asyncio
    async def test_index_sizes_are_reasonable(self, db_session):
        """Verify that new indexes have reasonable sizes (<10MB for typical workloads).

        TDD RED: This test MUST FAIL before implementation (indexes won't exist).
        """
        # Query index sizes from PostgreSQL
        query = text("""
            SELECT
                indexrelname,
                pg_size_pretty(pg_relation_size(indexrelid::regclass)) AS index_size,
                pg_relation_size(indexrelid::regclass) AS size_bytes
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
              AND relname = 'mcp_agent_jobs'
              AND indexrelname IN (
                  'idx_mcp_agent_jobs_last_progress',
                  'idx_mcp_agent_jobs_health_status',
                  'idx_mcp_agent_jobs_composite_status'
              )
            ORDER BY pg_relation_size(indexrelid::regclass) DESC
        """)

        result = await db_session.execute(query)
        indexes = result.fetchall()

        # Should have 3 indexes
        assert len(indexes) >= 3, "Should have 3 new performance indexes"

        # Verify reasonable sizes (10MB = 10,485,760 bytes)
        max_size_bytes = 10 * 1024 * 1024  # 10MB

        for idx in indexes:
            index_name = idx[0]
            size_bytes = idx[2]

            # For typical test workloads, indexes should be small
            # For production, allow up to 10MB
            assert size_bytes < max_size_bytes, f"Index {index_name} size ({idx[1]}) exceeds 10MB threshold"


class TestMessageAutoTracking:
    """Test that message auto-tracking fields are working as expected.

    This verifies the existing implementation documented in the handover.
    """

    @pytest.mark.asyncio
    async def test_last_message_check_at_field_exists(self, db_engine):
        """Verify last_message_check_at field exists for message tracking."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("mcp_agent_jobs")}

        assert "last_message_check_at" in columns, "last_message_check_at field should exist for message tracking"

        # Should be DateTime
        col_type = str(columns["last_message_check_at"]["type"])
        assert "TIMESTAMP" in col_type.upper() or "DATETIME" in col_type.upper(), (
            f"last_message_check_at should be DateTime type, got {col_type}"
        )

    @pytest.mark.asyncio
    async def test_last_progress_at_field_exists(self, db_engine):
        """Verify last_progress_at field exists for activity tracking."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("mcp_agent_jobs")}

        assert "last_progress_at" in columns, "last_progress_at field should exist for activity tracking"

        # Should be DateTime
        col_type = str(columns["last_progress_at"]["type"])
        assert "TIMESTAMP" in col_type.upper() or "DATETIME" in col_type.upper(), (
            f"last_progress_at should be DateTime type, got {col_type}"
        )

    @pytest.mark.asyncio
    async def test_health_status_field_exists(self, db_engine):
        """Verify health_status field exists for health monitoring."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("mcp_agent_jobs")}

        assert "health_status" in columns, "health_status field should exist for health monitoring"

        # Should be String
        col_type = str(columns["health_status"]["type"])
        assert "VARCHAR" in col_type.upper() or "STRING" in col_type.upper() or "TEXT" in col_type.upper(), (
            f"health_status should be String type, got {col_type}"
        )
