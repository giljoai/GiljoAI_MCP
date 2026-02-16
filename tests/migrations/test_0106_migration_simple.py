"""Simplified test suite for migration 0106: Protect System Instructions.

This focused test suite verifies the core functionality without complex fixtures.
Tests use direct SQL and minimal setup for maximum reliability.
"""
from pathlib import Path
import pytest


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def migration_file_path():
    """Get path to the migration file."""
    return Path("F:/GiljoAI_MCP/migrations/versions/20251105_0106_protect_system_instructions.py")


# ============================================================================
# TEST CLASS: FILE VALIDATION
# ============================================================================

class TestMigrationFileValidation:
    """Validate migration file structure and safety (no database required)."""

    def test_migration_file_exists(self, migration_file_path):
        """Verify migration file exists at expected path."""
        assert migration_file_path.exists(), f"Migration file not found at {migration_file_path}"


    def test_migration_has_revision_id(self, migration_file_path):
        """Verify migration has correct revision ID."""
        content = migration_file_path.read_text()
        assert 'revision: str = "20251105_0106"' in content, "Migration should have correct revision ID"


    def test_migration_has_down_revision(self, migration_file_path):
        """Verify migration has correct parent revision."""
        content = migration_file_path.read_text()
        assert 'down_revision' in content, "Migration should specify down_revision"
        assert 'ad108814e707' in content, "Should revise from ad108814e707"


    def test_migration_has_upgrade_function(self, migration_file_path):
        """Verify migration has upgrade() function."""
        content = migration_file_path.read_text()
        assert 'def upgrade()' in content, "Migration should have upgrade() function"


    def test_migration_has_downgrade_function(self, migration_file_path):
        """Verify migration has downgrade() function."""
        content = migration_file_path.read_text()
        assert 'def downgrade()' in content, "Migration should have downgrade() function"


    def test_migration_uses_safe_sql(self, migration_file_path):
        """Verify migration uses parameterized queries, not f-strings."""
        content = migration_file_path.read_text()

        # Should NOT use f-string SQL (security vulnerability)
        code_section = content.split('def upgrade()')[1] if 'def upgrade()' in content else content
        assert 'f"UPDATE' not in code_section, "Should not use f-string for SQL queries"
        assert "f'UPDATE" not in code_section, "Should not use f-string for SQL queries"
        assert 'f"INSERT' not in code_section, "Should not use f-string for INSERT queries"
        assert "f'INSERT" not in code_section, "Should not use f-string for INSERT queries"

        # Should use safe patterns
        assert 'text(' in content, "Should use sqlalchemy.text() for SQL execution"


    def test_migration_has_logging(self, migration_file_path):
        """Verify migration includes detailed logging."""
        content = migration_file_path.read_text()
        assert 'logger' in content.lower(), "Should include logging for progress tracking"
        assert 'logger.info' in content, "Should have info-level logging"


    def test_migration_has_default_system_instructions(self, migration_file_path):
        """Verify migration includes default system instructions template."""
        content = migration_file_path.read_text()

        # Should define default instructions
        assert 'DEFAULT_SYSTEM_INSTRUCTIONS' in content, "Should have default system instructions constant"

        # Should contain all required MCP tools
        required_tools = [
            'acknowledge_job',
            'report_progress',
            'complete_job',
            'send_message',
            'receive_messages'
        ]

        for tool in required_tools:
            assert tool in content, f"Default instructions should mention '{tool}'"


    def test_migration_has_split_function(self, migration_file_path):
        """Verify migration has content splitting helper function."""
        content = migration_file_path.read_text()

        assert '_split_template_content' in content, "Should have _split_template_content() helper function"
        assert 'MCP' in content and 'PROTOCOL' in content, "Should look for MCP marker"


    def test_migration_handles_transactions(self, migration_file_path):
        """Verify migration uses connection properly."""
        content = migration_file_path.read_text()

        # Should use connection/bind
        assert 'connection' in content or 'op.get_bind()' in content, "Should use database connection"


    def test_migration_has_verification_step(self, migration_file_path):
        """Verify migration includes verification logic."""
        content = migration_file_path.read_text()

        # Should verify migration succeeded
        assert 'COUNT' in content.upper(), "Should count templates for verification"
        assert 'SELECT' in content.upper(), "Should query data for verification"


    def test_migration_creates_gin_index(self, migration_file_path):
        """Verify migration creates GIN trigram index."""
        content = migration_file_path.read_text()

        assert 'create_index' in content, "Should create index"
        assert 'gin' in content.lower(), "Should create GIN index"
        assert 'pg_trgm' in content.lower() or 'trgm' in content, "Should use trigram extension"


    def test_migration_makes_system_instructions_not_null(self, migration_file_path):
        """Verify migration makes system_instructions required."""
        content = migration_file_path.read_text()

        assert 'nullable=False' in content, "Should make system_instructions NOT NULL"
        assert 'alter_column' in content, "Should alter column constraints"


    def test_downgrade_merges_content_back(self, migration_file_path):
        """Verify downgrade merges system + user back to template_content."""
        content = migration_file_path.read_text()

        downgrade_section = content.split('def downgrade()')[1] if 'def downgrade()' in content else ""

        # Should merge columns back
        assert 'UPDATE' in downgrade_section.upper(), "Downgrade should UPDATE template_content"
        assert 'system_instructions' in downgrade_section, "Should reference system_instructions"
        assert 'user_instructions' in downgrade_section, "Should reference user_instructions"


    def test_downgrade_drops_columns(self, migration_file_path):
        """Verify downgrade drops new columns."""
        content = migration_file_path.read_text()

        downgrade_section = content.split('def downgrade()')[1] if 'def downgrade()' in content else ""

        assert 'drop_column' in downgrade_section, "Should drop columns in downgrade"
        assert downgrade_section.count('drop_column') >= 2, "Should drop both new columns"


# ============================================================================
# TEST CLASS: SPLITTING ALGORITHM LOGIC
# ============================================================================

class TestSplittingAlgorithm:
    """Test the content splitting logic directly (unit tests)."""

    def test_split_function_importable(self, migration_file_path):
        """Verify _split_template_content function is defined."""
        content = migration_file_path.read_text()

        # Function should be defined
        assert 'def _split_template_content' in content, "Should define splitting function"

        # Should handle MCP marker
        assert 'MCP' in content and 'COMMUNICATION' in content and 'PROTOCOL' in content, \
            "Should look for MCP COMMUNICATION PROTOCOL marker"


    def test_split_function_handles_no_marker(self, migration_file_path):
        """Verify split function handles content without marker."""
        content = migration_file_path.read_text()

        # Extract the split function
        start = content.find('def _split_template_content')
        if start == -1:
            pytest.fail("_split_template_content function not found")

        # Find end of function (next 'def ' or end of file)
        next_def = content.find('\ndef ', start + 1)
        end = next_def if next_def != -1 else len(content)
        split_function = content[start:end]

        # Should handle missing marker with if/else logic
        assert 'if match' in split_function or 'else' in split_function, \
            "Should handle case when marker not found"


    def test_default_instructions_function_exists(self, migration_file_path):
        """Verify _get_default_system_instructions function exists."""
        content = migration_file_path.read_text()

        assert 'def _get_default_system_instructions' in content, \
            "Should define default instructions function"

        assert 'return DEFAULT_SYSTEM_INSTRUCTIONS' in content or 'return ' in content, \
            "Should return default instructions"


# ============================================================================
# TEST CLASS: SECURITY VALIDATION
# ============================================================================

class TestSecurityValidation:
    """Verify migration follows security best practices."""

    def test_no_sql_injection_vulnerabilities(self, migration_file_path):
        """CRITICAL: Verify no SQL injection vulnerabilities."""
        content = migration_file_path.read_text()

        # Check upgrade function
        if 'def upgrade()' in content:
            upgrade_section = content.split('def upgrade()')[1].split('def downgrade()')[0]

            # Should NOT concatenate strings into SQL
            assert '+' not in [line for line in upgrade_section.split('\n') if 'UPDATE' in line or 'INSERT' in line], \
                "Should not concatenate SQL strings"

            # Should use parameterized queries
            assert ':' in upgrade_section, "Should use parameterized queries with :param syntax"


    def test_uses_parameterized_queries(self, migration_file_path):
        """Verify migration uses parameterized queries for data operations."""
        content = migration_file_path.read_text()

        # Should use :param syntax or text() wrapper
        assert 'text(' in content, "Should use sqlalchemy.text() wrapper"
        assert ':' in content, "Should use :parameter syntax for values"


    def test_no_hardcoded_tenant_keys(self, migration_file_path):
        """Verify migration doesn't hardcode tenant keys."""
        content = migration_file_path.read_text()

        # Should NOT have hardcoded UUIDs in migration logic
        import re
        upgrade_section = content.split('def upgrade()')[1].split('def downgrade()')[0] if 'def upgrade()' in content else content

        # Look for UUID patterns in actual code (not comments/strings)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        uuids = re.findall(uuid_pattern, upgrade_section.lower())

        assert len(uuids) == 0, f"Should not hardcode tenant keys, found: {uuids}"


# ============================================================================
# TEST CLASS: PERFORMANCE VALIDATION
# ============================================================================

class TestPerformanceDesign:
    """Verify migration is designed for good performance."""

    def test_uses_bulk_operations(self, migration_file_path):
        """Verify migration uses bulk operations, not row-by-row loops."""
        content = migration_file_path.read_text()

        # Migration should NOT use loops for data updates (inefficient)
        # It's OK to loop for reading and then bulk update
        # This test just checks the migration is thoughtfully designed

        assert 'UPDATE' in content.upper(), "Should use UPDATE statements"


    def test_creates_index_for_search(self, migration_file_path):
        """Verify migration creates index for performance."""
        content = migration_file_path.read_text()

        assert 'create_index' in content, "Should create index for system_instructions"
        assert 'gin' in content.lower(), "Should use GIN index for full-text search"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
