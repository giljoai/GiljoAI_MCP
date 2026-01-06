"""
Tests for job_id column naming consistency in tasks table.

These tests verify that:
1. Tasks table uses 'job_id' column (not 'agent_job_id')
2. Foreign key references agent_jobs.job_id correctly
3. Indexes use job_id naming
4. Fresh installs create correct schema

Context:
- agent_id = Identity ("who are you")
- job_id = Work order ("what are we doing")
- The SQLAlchemy model is CORRECT (uses job_id)
"""

import pytest
import asyncpg
from pathlib import Path


@pytest.fixture
async def db_connection():
    """Create a database connection for testing."""
    conn = await asyncpg.connect("postgresql://postgres:***@localhost/giljo_mcp")
    yield conn
    await conn.close()


class TestJobIdColumnConsistency:
    """Test suite for job_id column naming consistency."""

    @pytest.mark.asyncio
    async def test_tasks_table_has_job_id_column(self, db_connection):
        """Verify tasks table has job_id column (not agent_job_id)."""
        result = await db_connection.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'job_id'
            """
        )
        assert len(result) == 1, "tasks table should have job_id column"

    @pytest.mark.asyncio
    async def test_tasks_table_does_not_have_agent_job_id_column(self, db_connection):
        """Verify tasks table does NOT have agent_job_id column."""
        result = await db_connection.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'agent_job_id'
            """
        )
        assert len(result) == 0, "tasks table should NOT have agent_job_id column"

    @pytest.mark.asyncio
    async def test_foreign_key_references_agent_jobs_job_id(self, db_connection):
        """Verify FK constraint references agent_jobs.job_id."""
        result = await db_connection.fetch(
            """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'tasks'
                AND kcu.column_name = 'job_id'
            """
        )

        assert len(result) == 1, "Should have exactly one FK constraint on job_id"
        fk = result[0]
        assert fk["foreign_table_name"] == "mcp_agent_jobs", "FK should reference mcp_agent_jobs table"
        assert fk["foreign_column_name"] == "job_id", "FK should reference job_id column"
        assert "fk_task_job" in fk["constraint_name"], "FK constraint should have job naming"

    @pytest.mark.asyncio
    async def test_indexes_use_job_id_naming(self, db_connection):
        """Verify indexes use job_id naming (not agent_job_id)."""
        # Get all indexes on tasks table that involve job column
        result = await db_connection.fetch(
            """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'tasks'
                AND (indexname LIKE '%job%' OR indexdef LIKE '%job_id%')
            """
        )

        # Should have at least 2 indexes: idx_task_job and idx_task_tenant_job
        assert len(result) >= 2, "Should have at least 2 indexes on job_id"

        # Check each index uses job_id (not agent_job_id)
        for idx in result:
            index_name = idx["indexname"]
            index_def = idx["indexdef"]

            # Index name should not contain "agent_job"
            assert "agent_job" not in index_name, f"Index {index_name} should use job naming"

            # Index definition should reference job_id
            assert "job_id" in index_def, f"Index {index_name} should reference job_id column"

    @pytest.mark.asyncio
    async def test_sqlalchemy_model_matches_database(self, db_connection):
        """Verify SQLAlchemy model column name matches database."""
        # Read the model file
        model_path = Path("F:/GiljoAI_MCP/src/giljo_mcp/models/tasks.py")
        model_content = model_path.read_text()

        # Check model uses job_id (around line 62)
        assert 'job_id = Column(String' in model_content, "Model should define job_id column"
        assert 'agent_job_id = Column(String' not in model_content, "Model should NOT define agent_job_id"

        # Verify database has matching column
        result = await db_connection.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'job_id'
            """
        )
        assert len(result) == 1, "Database should match model with job_id column"

    @pytest.mark.asyncio
    async def test_baseline_migration_uses_job_id(self):
        """Verify baseline migration creates job_id column (not agent_job_id)."""
        # Read the baseline migration file
        migration_path = Path(
            "F:/GiljoAI_MCP/migrations/versions/caeddfdbb2a0_unified_baseline_all_tables.py"
        )
        migration_content = migration_path.read_text()

        # Should create job_id column
        assert "'job_id'" in migration_content or '"job_id"' in migration_content, \
            "Baseline migration should create job_id column"

        # Should NOT create agent_job_id column in tasks table context
        # (Need to check around line 886 in tasks table creation)
        lines = migration_content.split('\n')

        # Find tasks table creation (around line 875-920)
        in_tasks_table = False
        has_job_id = False
        has_agent_job_id = False

        for i, line in enumerate(lines):
            if "op.create_table('tasks'" in line or 'op.create_table("tasks"' in line:
                in_tasks_table = True
            elif in_tasks_table and 'job_id' in line.lower():
                if "'job_id'" in line or '"job_id"' in line:
                    has_job_id = True
                if "'agent_job_id'" in line or '"agent_job_id"' in line:
                    has_agent_job_id = True
            elif in_tasks_table and (')' in line and 'sa.Column' not in line):
                # End of table definition
                in_tasks_table = False

        assert has_job_id, "Baseline migration should create job_id column in tasks table"
        assert not has_agent_job_id, "Baseline migration should NOT create agent_job_id in tasks table"

    @pytest.mark.asyncio
    async def test_column_data_type_is_string(self, db_connection):
        """Verify job_id column has correct data type."""
        result = await db_connection.fetch(
            """
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'job_id'
            """
        )

        assert len(result) == 1, "Should find job_id column"
        col = result[0]
        assert col["data_type"] == "character varying", "job_id should be VARCHAR type"

    @pytest.mark.asyncio
    async def test_foreign_key_is_nullable(self, db_connection):
        """Verify job_id FK is nullable (tasks can exist without jobs)."""
        result = await db_connection.fetch(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'job_id'
            """
        )

        assert len(result) == 1, "Should find job_id column"
        assert result[0]["is_nullable"] == "YES", "job_id should be nullable"
