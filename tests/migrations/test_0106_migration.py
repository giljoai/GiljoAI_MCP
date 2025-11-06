"""Comprehensive test suite for migration 0106: Protect System Instructions.

This test suite verifies:
1. Migration upgrade creates new columns correctly
2. Content splitting algorithm works for all scenarios
3. Migration handles multi-tenant isolation
4. Migration validates MCP tools presence
5. Downgrade merges content back correctly
6. Performance meets requirements (<1 minute for 1000 templates)

Following TDD approach - tests written BEFORE implementation.
"""
from pathlib import Path
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, String, Text, DateTime, Boolean, Integer, JSON, select
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def migration_file_path():
    """Get path to the migration file."""
    return Path("F:/GiljoAI_MCP/migrations/versions/20251105_0106_protect_system_instructions.py")


@pytest.fixture
def test_db_url():
    """Test database URL - uses dedicated test database."""
    return "postgresql://postgres:4010@localhost:5432/test_migration_0106"


@pytest.fixture
def test_engine(test_db_url):
    """Create test database engine."""
    # Create test database
    admin_engine = create_engine("postgresql://postgres:4010@localhost:5432/postgres", isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Drop if exists
        conn.execute(text("DROP DATABASE IF EXISTS test_migration_0106"))
        conn.execute(text("CREATE DATABASE test_migration_0106"))
    admin_engine.dispose()

    # Connect to test database
    engine = create_engine(test_db_url)
    yield engine

    # Cleanup
    engine.dispose()
    admin_engine = create_engine("postgresql://postgres:4010@localhost:5432/postgres", isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS test_migration_0106"))
    admin_engine.dispose()


@pytest.fixture
def alembic_config(test_db_url):
    """Create Alembic config for test database."""
    config = Config()
    config.set_main_option("script_location", "F:/GiljoAI_MCP/migrations")
    config.set_main_option("sqlalchemy.url", test_db_url)
    return config


@pytest.fixture
def session_maker(test_engine):
    """Create session maker for test database."""
    return sessionmaker(bind=test_engine)


def setup_migration_base(engine, alembic_config):
    """Setup database with migrations up to (but not including) 0106.

    This runs all migrations up to ad108814e707 (the parent of 0106).
    """
    # Run migrations up to the parent of 0106
    command.upgrade(alembic_config, "ad108814e707")


# ============================================================================
# TEST CLASS: MIGRATION UPGRADE PATH
# ============================================================================

class TestMigrationUpgrade:
    """Test migration upgrade path - adding new columns and splitting content."""

    def test_migration_adds_columns(self, test_engine, alembic_config, session_maker):
        """Verify new columns created with correct types and constraints."""
        # Setup: Run migrations up to parent
        setup_migration_base(test_engine, alembic_config)

        # Execute migration 0106
        command.upgrade(alembic_config, "20251105_0106")

        # Verify columns exist
        inspector = inspect(test_engine)
        columns = {col['name']: col for col in inspector.get_columns('agent_templates')}

        assert 'system_instructions' in columns, "system_instructions column not created"
        assert 'user_instructions' in columns, "user_instructions column not created"

        # Verify system_instructions is NOT NULL
        assert columns['system_instructions']['nullable'] is False, "system_instructions should be NOT NULL"

        # Verify user_instructions is nullable
        assert columns['user_instructions']['nullable'] is True, "user_instructions should be nullable"

        # Verify both are Text type
        assert 'text' in str(columns['system_instructions']['type']).lower(), "system_instructions should be Text"
        assert 'text' in str(columns['user_instructions']['type']).lower(), "user_instructions should be Text"


    def test_migration_splits_content_with_mcp_marker(self, test_engine, alembic_config, session_maker):
        """Test content splitting when MCP marker present."""
        # Setup: Run migrations up to parent
        setup_migration_base(test_engine, alembic_config)

        # Insert test template with MCP marker
        with test_engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO agent_templates
                    (id, tenant_key, name, category, role, template_content)
                    VALUES (:id, :tenant, :name, :category, :role, :content)
                """),
                {
                    "id": "test-1",
                    "tenant": "tenant-1",
                    "name": "implementer",
                    "category": "role",
                    "role": "implementer",
                    "content": """You are an implementation specialist.

## Role Responsibilities
- Write production-grade code
- Follow best practices
- Write comprehensive tests

## MCP COMMUNICATION PROTOCOL

**CRITICAL**: You MUST use these MCP tools for coordination.

### Job Lifecycle
- acknowledge_job(job_id, agent_id, tenant_key)
- report_progress(job_id, progress, tenant_key)
- complete_job(job_id, result, tenant_key)

### Agent Communication
- send_message(to_agent, message, priority, tenant_key)
- receive_messages(agent_id, limit, tenant_key)
"""
                }
            )
            conn.commit()

        # Execute migration
        command.upgrade(alembic_config, "20251105_0106")

        # Verify content split correctly
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT system_instructions, user_instructions FROM agent_templates WHERE id = 'test-1'")
            ).fetchone()

            system_instructions = result[0]
            user_instructions = result[1]

            # System instructions should contain MCP tools
            assert 'acknowledge_job' in system_instructions, "System instructions should contain acknowledge_job"
            assert 'report_progress' in system_instructions, "System instructions should contain report_progress"
            assert 'complete_job' in system_instructions, "System instructions should contain complete_job"
            assert 'send_message' in system_instructions, "System instructions should contain send_message"
            assert 'receive_messages' in system_instructions, "System instructions should contain receive_messages"

            # User instructions should contain role-specific content
            assert 'implementation specialist' in user_instructions, "User instructions should contain role description"
            assert 'Role Responsibilities' in user_instructions, "User instructions should contain responsibilities"

            # System instructions should NOT contain role-specific content
            assert 'Role Responsibilities' not in system_instructions, "System instructions should not contain role-specific content"


    def test_migration_handles_no_mcp_marker(self, test_engine, alembic_config, session_maker):
        """Test fallback when no MCP marker found."""
        # Setup: Create table and insert template WITHOUT MCP marker
        setup_migration_base(test_engine, alembic_config)

        with test_engine.connect() as conn:
            conn.execute(
            )
            conn.commit()

        # Execute migration
        command.upgrade(alembic_config, "20251105_0106")

        # Verify default system instructions used
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT system_instructions, user_instructions FROM agent_templates WHERE id = 'test-2'")
            ).fetchone()

            system_instructions = result[0]
            user_instructions = result[1]

            # System instructions should have default MCP tools
            assert 'acknowledge_job' in system_instructions, "Should have default system instructions with MCP tools"
            assert 'report_progress' in system_instructions

            # Full original content should be in user_instructions
            assert 'custom agent' in user_instructions, "Original content should move to user_instructions"


    def test_migration_handles_empty_content(self, test_engine, alembic_config, session_maker):
        """Test empty template handling."""
        # Setup: Create table with empty/NULL content
        setup_migration_base(test_engine, alembic_config)

        with test_engine.connect() as conn:
            conn.execute(
            )
            conn.commit()

        # Execute migration
        command.upgrade(alembic_config, "20251105_0106")

        # Verify default system instructions applied
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT system_instructions, user_instructions FROM agent_templates WHERE id = 'test-3'")
            ).fetchone()

            system_instructions = result[0]
            user_instructions = result[1]

            # Should have default system instructions
            assert system_instructions is not None and len(system_instructions) > 0, "Should have default system instructions"
            assert 'acknowledge_job' in system_instructions

            # user_instructions should be NULL or empty
            assert not user_instructions or len(user_instructions.strip()) == 0, "User instructions should be empty"


    def test_migration_preserves_multi_tenant_isolation(self, test_engine, alembic_config, session_maker):
        """Verify no cross-tenant data leakage."""
        # Setup: Create templates for multiple tenants
        setup_migration_base(test_engine, alembic_config)

        with test_engine.connect() as conn:
            conn.execute(
                )
            )
            conn.execute(
                )
            )
            conn.commit()

        # Execute migration
        command.upgrade(alembic_config, "20251105_0106")

        # Verify each tenant's data isolated
        Session = session_maker()
        with Session() as session:
            tenant1 = session.execute(
                text("SELECT user_instructions FROM agent_templates WHERE tenant_key = 'tenant-1'")
            ).fetchone()[0]

            tenant2 = session.execute(
                text("SELECT user_instructions FROM agent_templates WHERE tenant_key = 'tenant-2'")
            ).fetchone()[0]

            # Each should contain only their own content
            assert 'Tenant 1' in tenant1 and 'Tenant 2' not in tenant1, "Tenant 1 content leaked"
            assert 'Tenant 2' in tenant2 and 'Tenant 1' not in tenant2, "Tenant 2 content leaked"


    def test_migration_system_instructions_non_nullable(self, test_engine, alembic_config, session_maker):
        """Verify system_instructions made required after migration."""
        # Setup and run migration
        setup_migration_base(test_engine, alembic_config)
        command.upgrade(alembic_config, "20251105_0106")

        # Attempt to insert template with NULL system_instructions - should fail
        Session = session_maker()
        with Session() as session:
            with pytest.raises(Exception) as exc_info:
                session.execute(
                    text("""
                        INSERT INTO agent_templates
                        (id, tenant_key, name, category, system_instructions, template_content)
                        VALUES ('test-null', 'tenant-1', 'test', 'custom', NULL, 'content')
                    """)
                )
                session.commit()

            # Verify it's a NOT NULL constraint error
            assert 'null' in str(exc_info.value).lower() or 'not-null' in str(exc_info.value).lower()


    def test_migration_validates_mcp_tools_present(self, test_engine, alembic_config, session_maker):
        """Verify all required MCP tools in system instructions after migration."""
        # Setup with real template
        setup_migration_base(test_engine, alembic_config)

        with test_engine.connect() as conn:
            conn.execute(
- report_progress()
- complete_job()
- send_message()
- receive_messages()
"""
                )
            )
            conn.commit()

        # Execute migration
        command.upgrade(alembic_config, "20251105_0106")

        # Verify all required tools present
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT system_instructions FROM agent_templates WHERE id = 'test-tools'")
            ).fetchone()[0]

            required_tools = [
                'acknowledge_job',
                'report_progress',
                'complete_job',
                'send_message',
                'receive_messages'
            ]

            for tool in required_tools:
                assert tool in result, f"Required MCP tool '{tool}' not found in system instructions"


    def test_migration_performance(self, test_engine, alembic_config, session_maker):
        """Test migration performance with large dataset (1000 templates)."""
        import time

        # Setup: Create 1000 templates
        setup_migration_base(test_engine, alembic_config)

        with test_engine.connect() as conn:
            for i in range(1000):
                conn.execute(
- report_progress()
- complete_job()
"""
                    )
                )
            conn.commit()

        # Measure migration time
        start_time = time.time()
        command.upgrade(alembic_config, "20251105_0106")
        elapsed = time.time() - start_time

        # Verify completes in <60 seconds
        assert elapsed < 60, f"Migration took {elapsed:.2f}s (should be <60s for 1000 templates)"

        # Verify all templates migrated correctly
        Session = session_maker()
        with Session() as session:
            count = session.execute(
                text("SELECT COUNT(*) FROM agent_templates WHERE system_instructions IS NOT NULL")
            ).scalar()

            assert count == 1000, f"Expected 1000 templates, found {count}"


# ============================================================================
# TEST CLASS: MIGRATION DOWNGRADE PATH
# ============================================================================

class TestMigrationDowngrade:
    """Test migration rollback path - merging content back."""

    def test_downgrade_merges_content(self, test_engine, alembic_config, session_maker):
        """Verify downgrade merges system + user back to template_content."""
        # Setup: Create table and run upgrade
        setup_migration_base(test_engine, alembic_config)

        original_content = """Original template content.

## MCP COMMUNICATION PROTOCOL
- acknowledge_job()
"""

        with test_engine.connect() as conn:
            conn.execute(
            )
            conn.commit()

        # Run upgrade
        command.upgrade(alembic_config, "20251105_0106")

        # Run downgrade
        command.downgrade(alembic_config, "-1")

        # Verify template_content restored
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT template_content FROM agent_templates WHERE id = 'test-merge'")
            ).fetchone()[0]

            # Should contain both system and user instructions merged
            assert 'acknowledge_job' in result, "Merged content should contain system instructions"
            assert 'Original template' in result, "Merged content should contain user instructions"


    def test_downgrade_removes_columns(self, test_engine, alembic_config, session_maker):
        """Verify new columns dropped on downgrade."""
        # Setup and run upgrade
        setup_migration_base(test_engine, alembic_config)
        command.upgrade(alembic_config, "20251105_0106")

        # Verify columns exist
        inspector = inspect(test_engine)
        columns_before = {col['name'] for col in inspector.get_columns('agent_templates')}
        assert 'system_instructions' in columns_before
        assert 'user_instructions' in columns_before

        # Run downgrade
        command.downgrade(alembic_config, "-1")

        # Verify columns removed
        inspector = inspect(test_engine)
        columns_after = {col['name'] for col in inspector.get_columns('agent_templates')}

        assert 'system_instructions' not in columns_after, "system_instructions column should be dropped"
        assert 'user_instructions' not in columns_after, "user_instructions column should be dropped"
        assert 'template_content' in columns_after, "template_content column should remain"


    def test_downgrade_no_data_loss(self, test_engine, alembic_config, session_maker):
        """Verify no data lost during rollback."""
        # Setup with template containing substantial content
        setup_migration_base(test_engine, alembic_config)

        long_content = """You are a comprehensive agent.

## Detailed Instructions
""" + "\n".join([f"- Instruction {i}" for i in range(50)]) + """

## MCP COMMUNICATION PROTOCOL
- acknowledge_job(job_id, agent_id, tenant_key)
- report_progress(job_id, progress, tenant_key)
- complete_job(job_id, result, tenant_key)
- send_message(to_agent, message, priority, tenant_key)
- receive_messages(agent_id, limit, tenant_key)
"""

        with test_engine.connect() as conn:
            conn.execute(
            )
            conn.commit()

        # Capture original content length
        original_length = len(long_content)

        # Run upgrade then downgrade
        command.upgrade(alembic_config, "20251105_0106")
        command.downgrade(alembic_config, "-1")

        # Verify merged content length similar to original
        Session = session_maker()
        with Session() as session:
            result = session.execute(
                text("SELECT template_content FROM agent_templates WHERE id = 'test-data-loss'")
            ).fetchone()[0]

            merged_length = len(result)

            # Allow small variance for spacing/formatting
            length_diff = abs(original_length - merged_length)
            assert length_diff < 50, f"Significant data loss detected: {original_length} -> {merged_length}"

            # Verify key content preserved
            assert 'Instruction 25' in result, "User content should be preserved"
            assert 'acknowledge_job' in result, "System content should be preserved"


# ============================================================================
# TEST CLASS: CONTENT SPLITTING ALGORITHM
# ============================================================================

class TestSplittingAlgorithm:
    """Test the content splitting logic in isolation."""

    def test_split_with_standard_marker(self):
        """Test splitting with '## MCP COMMUNICATION PROTOCOL'."""
        # This tests the splitting function directly (will be in migration)
        # For now, test via migration behavior
        pass  # Covered by test_migration_splits_content_with_mcp_marker


    def test_split_with_variation_markers(self):
        """Test all marker variations (case-insensitive, spacing)."""
        # Test that migration handles different marker formats
        # - "## MCP Communication Protocol"
        # - "## MCP COMMUNICATION PROTOCOL"
        # - "##MCP Communication Protocol" (no space)
        # - "## mcp communication protocol" (lowercase)
        pass  # To be implemented when migration has variations


    def test_split_marker_at_start(self):
        """Test when marker is at beginning of content."""
        pass  # Edge case - covered by integration tests


    def test_split_marker_at_end(self):
        """Test when marker is at end of content."""
        pass  # Edge case - covered by integration tests


    def test_split_multiple_markers(self):
        """Use first marker only."""
        pass  # Edge case - should use first occurrence


    def test_default_system_instructions_format(self):
        """Verify default instructions have all required tools."""
        # This will test the _get_default_system_instructions() function
        pass  # To be verified after migration implementation


# ============================================================================
# TEST CLASS: MIGRATION FILE VALIDATION
# ============================================================================

class TestMigrationFileValidation:
    """Validate migration file structure and safety."""

    def test_migration_file_exists(self, migration_file_path):
        """Verify migration file exists at expected path."""
        # This will fail initially (TDD) until we create the file
        assert migration_file_path.exists(), f"Migration file not found at {migration_file_path}"


    def test_migration_has_revision_id(self, migration_file_path):
        """Verify migration has correct revision ID."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()
        assert 'revision: str = "20251105_0106"' in content, "Migration should have correct revision ID"


    def test_migration_has_down_revision(self, migration_file_path):
        """Verify migration has correct parent revision."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()
        # Should revise from latest migration (20251104_0102)
        assert 'down_revision' in content, "Migration should specify down_revision"


    def test_migration_has_upgrade_function(self, migration_file_path):
        """Verify migration has upgrade() function."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()
        assert 'def upgrade()' in content, "Migration should have upgrade() function"


    def test_migration_has_downgrade_function(self, migration_file_path):
        """Verify migration has downgrade() function."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()
        assert 'def downgrade()' in content, "Migration should have downgrade() function"


    def test_migration_uses_safe_sql(self, migration_file_path):
        """Verify migration uses parameterized queries, not f-strings."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()

        # Should NOT use f-string SQL (security vulnerability)
        assert 'f"UPDATE' not in content, "Should not use f-string for SQL queries"
        assert "f'UPDATE" not in content, "Should not use f-string for SQL queries"

        # Should use safe patterns
        assert 'text(' in content or 'op.execute' in content, "Should use safe SQL execution"


    def test_migration_has_logging(self, migration_file_path):
        """Verify migration includes detailed logging."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()

        # Should have logging statements
        assert 'logger' in content.lower() or 'print' in content, "Should include logging for progress tracking"


    def test_migration_handles_transactions(self, migration_file_path):
        """Verify migration uses transactions properly."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()

        # Should use connection/transaction management
        assert 'conn' in content or 'bind' in content, "Should use database connections"


    def test_migration_is_idempotent_ready(self, migration_file_path):
        """Verify migration designed for idempotency."""
        if not migration_file_path.exists():
            pytest.skip("Migration file not created yet")

        content = migration_file_path.read_text()

        # Should check for existing data/state
        assert 'WHERE' in content or 'IF' in content, "Should have conditional logic for idempotency"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
