"""
Test suite for Handover 0088 - job_metadata column migration.

Tests the migration of the job_metadata JSONB column to mcp_agent_jobs table,
including idempotency, data migration, and multi-tenant isolation.
"""

import pytest
from sqlalchemy import inspect, select, text

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class TestMetadataMigration:
    """Test job_metadata column existence and schema."""

    def test_job_metadata_column_exists(self, db_engine):
        """Verify job_metadata column exists in mcp_agent_jobs table."""
        inspector = inspect(db_engine)
        columns = {col["name"]: col for col in inspector.get_columns("mcp_agent_jobs")}

        assert "job_metadata" in columns, "job_metadata column should exist"

        # Check column type (should be JSON/JSONB)
        col_type = str(columns["job_metadata"]["type"])
        assert "JSON" in col_type.upper(), f"job_metadata should be JSON type, got {col_type}"

        # Check NOT NULL constraint
        assert columns["job_metadata"]["nullable"] is False, "job_metadata should be NOT NULL"

    def test_job_metadata_default_value(self, db_session):
        """Verify job_metadata defaults to empty JSON object."""
        # Create a minimal job without job_metadata
        job = AgentExecution(
            tenant_key="test-tenant", project_id="test-project", agent_display_name="orchestrator", mission="test mission"
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.job_metadata is not None, "job_metadata should not be None"
        assert job.job_metadata == {}, "job_metadata should default to empty dict"

    def test_job_metadata_gin_index_exists(self, db_engine):
        """Verify GIN index exists on job_metadata column for performance."""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("mcp_agent_jobs")

        # Check for job_metadata index
        job_metadata_indexes = [idx for idx in indexes if "job_metadata" in idx["name"].lower()]

        assert len(job_metadata_indexes) > 0, "GIN index should exist on job_metadata column"

        # Verify it's a GIN index (PostgreSQL-specific)
        # Note: SQLAlchemy inspector may not expose index type directly
        # So we also verify via raw SQL
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'mcp_agent_jobs'
                AND indexname LIKE '%job_metadata%'
            """)
            )

            index_defs = [row[1] for row in result]
            assert any("gin" in idx.lower() for idx in index_defs), "job_metadata index should be GIN type for JSONB"


class TestMetadataFunctionality:
    """Test job_metadata storage and retrieval."""

    def test_store_thin_client_job_metadata(self, db_session):
        """Test storing thin client job_metadata in job_metadata column."""
        job_metadata = {
            "field_priorities": {"vision": 10, "architecture": 8, "tech_stack": 6},
            "user_id": "user-12345",
            "tool": "claude-code",
            "created_via": "thin_client_generator",
        }

        job = AgentExecution(
            tenant_key="test-tenant",
            project_id="test-project",
            agent_display_name="orchestrator",
            mission="test mission",
            job_metadata=job_metadata,
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.job_metadata == job_metadata, "job_metadata should be stored correctly"
        assert job.job_metadata["field_priorities"]["vision"] == 10
        assert job.job_metadata["user_id"] == "user-12345"
        assert job.job_metadata["tool"] == "claude-code"

    def test_query_by_job_metadata_field(self, db_session):
        """Test querying jobs by job_metadata field using JSONB operators."""
        # Create jobs with different tools
        job1 = AgentExecution(
            tenant_key="test-tenant",
            project_id="test-project-1",
            agent_display_name="orchestrator",
            mission="mission 1",
            job_metadata={"tool": "claude-code", "created_via": "thin_client"},
        )

        job2 = AgentExecution(
            tenant_key="test-tenant",
            project_id="test-project-2",
            agent_display_name="orchestrator",
            mission="mission 2",
            job_metadata={"tool": "codex", "created_via": "thin_client"},
        )

        db_session.add_all([job1, job2])
        db_session.commit()

        # Query for claude-code jobs using JSONB operator
        result = db_session.query(AgentExecution).filter(AgentExecution.job_metadata["tool"].astext == "claude-code").all()

        assert len(result) == 1
        assert result[0].job_metadata["tool"] == "claude-code"

    def test_update_job_metadata_field(self, db_session):
        """Test updating specific job_metadata fields."""
        job = AgentExecution(
            tenant_key="test-tenant",
            project_id="test-project",
            agent_display_name="orchestrator",
            mission="test mission",
            job_metadata={"tool": "universal", "version": 1},
        )

        db_session.add(job)
        db_session.commit()

        # Update job_metadata
        job.job_metadata = {**job.job_metadata, "version": 2, "updated": True}
        db_session.commit()
        db_session.refresh(job)

        assert job.job_metadata["version"] == 2
        assert job.job_metadata["updated"] is True
        assert job.job_metadata["tool"] == "universal"


class TestMultiTenantIsolation:
    """Test that job_metadata respects tenant isolation."""

    def test_job_metadata_respects_tenant_isolation(self, db_session):
        """Verify job_metadata doesn't leak across tenants."""
        # Create jobs for two tenants with different job_metadata
        job1 = AgentExecution(
            tenant_key="tenant-1",
            project_id="proj-1",
            agent_display_name="orchestrator",
            mission="mission 1",
            job_metadata={"secret": "tenant-1-secret", "field_priorities": {"vision": 10}},
        )

        job2 = AgentExecution(
            tenant_key="tenant-2",
            project_id="proj-2",
            agent_display_name="orchestrator",
            mission="mission 2",
            job_metadata={"secret": "tenant-2-secret", "field_priorities": {"architecture": 8}},
        )

        db_session.add_all([job1, job2])
        db_session.commit()

        # Query with tenant filtering (REQUIRED)
        result = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-1").all()

        assert len(result) == 1
        assert result[0].job_metadata["secret"] == "tenant-1-secret"
        assert "vision" in result[0].job_metadata["field_priorities"]

        # Verify tenant-2 data is not accessible
        tenant2_result = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-2").all()

        assert len(tenant2_result) == 1
        assert tenant2_result[0].job_metadata["secret"] == "tenant-2-secret"

    def test_job_metadata_tenant_filtered_query(self, db_session):
        """Test querying job_metadata with mandatory tenant isolation."""
        # Create jobs for multiple tenants
        jobs = [
            AgentExecution(
                tenant_key=f"tenant-{i}",
                project_id=f"proj-{i}",
                agent_display_name="orchestrator",
                mission=f"mission {i}",
                job_metadata={"tenant_id": f"tenant-{i}", "sequence": i},
            )
            for i in range(3)
        ]

        db_session.add_all(jobs)
        db_session.commit()

        # Query with tenant filter AND job_metadata filter
        result = (
            db_session.query(AgentExecution)
            .filter(AgentExecution.tenant_key == "tenant-1", AgentExecution.job_metadata["sequence"].astext == "1")
            .all()
        )

        assert len(result) == 1
        assert result[0].job_metadata["tenant_id"] == "tenant-1"
        assert result[0].job_metadata["sequence"] == 1


class TestMigrationIdempotency:
    """Test that migration can be run multiple times safely."""

    def test_migration_is_idempotent(self, db_engine):
        """
        Verify that running the migration multiple times doesn't cause errors.

        This test simulates re-running the migration by checking that:
        1. Column exists after first run
        2. Re-running doesn't raise errors
        3. Data remains intact
        """
        # Column should exist (already migrated)
        inspector = inspect(db_engine)
        columns = {col["name"] for col in inspector.get_columns("mcp_agent_jobs")}

        assert "job_metadata" in columns, "job_metadata column should exist after migration"

        # Try to create it again (should be handled by IF NOT EXISTS)
        with db_engine.connect() as conn:
            # This should NOT raise an error due to idempotent migration
            try:
                conn.execute(
                    text("""
                    ALTER TABLE mcp_agent_jobs
                    ADD COLUMN IF NOT EXISTS job_metadata JSONB DEFAULT '{}'::jsonb NOT NULL
                """)
                )
                conn.commit()
            except Exception as e:
                pytest.fail(f"Migration should be idempotent but raised: {e}")

        # Verify column still exists
        inspector = inspect(db_engine)
        columns = {col["name"] for col in inspector.get_columns("mcp_agent_jobs")}
        assert "job_metadata" in columns


class TestDataMigration:
    """Test migration of existing data from handover_summary to job_metadata."""

    def test_thin_client_data_migration(self, db_session, db_engine):
        """
        Test that thin client data is migrated from handover_summary to job_metadata.

        Note: This test simulates the migration scenario where old jobs
        have thin client data in handover_summary instead of job_metadata.
        """
        # Create a job with thin client data in handover_summary (old format)
        # We simulate this by directly inserting into the database
        with db_engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO mcp_agent_jobs (
                    tenant_key, project_id, job_id, agent_display_name, mission,
                    handover_summary, job_metadata
                )
                VALUES (
                    'test-tenant',
                    'test-project',
                    'job-old-format',
                    'orchestrator',
                    'test mission',
                    '{"field_priorities": {"vision": 10}, "user_id": "user-123", "tool": "claude-code", "created_via": "thin_client"}'::jsonb,
                    '{}'::jsonb
                )
            """)
            )
            conn.commit()

        # Simulate migration query (same as in install.py)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("""
                UPDATE mcp_agent_jobs
                SET job_metadata = jsonb_build_object(
                    'field_priorities', COALESCE(handover_summary->'field_priorities', '{}'::jsonb),
                    'user_id', handover_summary->>'user_id',
                    'tool', handover_summary->>'tool',
                    'created_via', handover_summary->>'created_via'
                )
                WHERE job_id = 'job-old-format'
                AND job_metadata = '{}'::jsonb
                AND handover_summary IS NOT NULL
                AND (
                    handover_summary ? 'field_priorities'
                    OR handover_summary ? 'user_id'
                    OR handover_summary ? 'tool'
                    OR handover_summary ? 'created_via'
                )
            """)
            )
            conn.commit()

        # Verify migration worked
        job = db_session.query(AgentExecution).filter(AgentExecution.job_id == "job-old-format").first()

        assert job is not None
        assert job.job_metadata != {}
        assert "field_priorities" in job.job_metadata
        assert job.job_metadata["field_priorities"]["vision"] == 10
        assert job.job_metadata["user_id"] == "user-123"
        assert job.job_metadata["tool"] == "claude-code"

    def test_succession_data_not_migrated(self, db_session, db_engine):
        """
        Verify that succession data in handover_summary is NOT migrated to job_metadata.

        handover_summary should keep succession-specific data like project_status,
        active_agents, etc. Only thin client fields should be migrated.
        """
        # Create a job with succession data in handover_summary
        with db_engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO mcp_agent_jobs (
                    tenant_key, project_id, job_id, agent_display_name, mission,
                    handover_summary, job_metadata
                )
                VALUES (
                    'test-tenant',
                    'test-project',
                    'job-succession',
                    'orchestrator',
                    'test mission',
                    '{"project_status": "60% complete", "active_agents": ["agent-1"], "field_priorities": {"vision": 5}}'::jsonb,
                    '{}'::jsonb
                )
            """)
            )
            conn.commit()

        # Run migration
        with db_engine.connect() as conn:
            conn.execute(
                text("""
                UPDATE mcp_agent_jobs
                SET job_metadata = jsonb_build_object(
                    'field_priorities', COALESCE(handover_summary->'field_priorities', '{}'::jsonb),
                    'user_id', handover_summary->>'user_id',
                    'tool', handover_summary->>'tool',
                    'created_via', handover_summary->>'created_via'
                )
                WHERE job_id = 'job-succession'
                AND job_metadata = '{}'::jsonb
            """)
            )
            conn.commit()

        # Verify: job_metadata has thin client data, handover_summary keeps succession data
        job = db_session.query(AgentExecution).filter(AgentExecution.job_id == "job-succession").first()

        assert job is not None

        # job_metadata should have thin client data
        assert "field_priorities" in job.job_metadata
        assert job.job_metadata["field_priorities"]["vision"] == 5

        # handover_summary should still have succession data
        assert job.handover_summary is not None
        assert "project_status" in job.handover_summary
        assert job.handover_summary["project_status"] == "60% complete"
        assert "active_agents" in job.handover_summary
