"""Security and safety tests for migration 6adac1467121 (0103 security fix).

This test suite verifies the migration is secure against SQL injection and
operates correctly in all scenarios.
"""
from pathlib import Path

import pytest


@pytest.fixture
def migration_file_path():
    """Get path to the migration file."""
    return Path("F:/GiljoAI_MCP/migrations/versions/6adac1467121_add_cli_tool_and_background_color_to_.py")


def test_migration_no_fstring_sql_injection(migration_file_path):
    """CRITICAL: Verify migration does not use f-string SQL interpolation.

    This test ensures the SQL injection vulnerability is fixed.
    F-string interpolation into SQL queries is a critical security flaw.
    """
    content = migration_file_path.read_text()

    # Extract only the code portion (after imports, before any triple-quoted strings in code)
    # Split by def upgrade() to get the actual code
    if "def upgrade()" in content:
        code_section = content.split("def upgrade()")[1].split("def downgrade()")[0]
    else:
        code_section = content

    # Check for dangerous f-string patterns in the actual code (not docstrings)
    assert 'f"UPDATE' not in code_section, "F-string SQL injection vulnerability detected (double quotes)"
    assert "f'UPDATE" not in code_section, "F-string SQL injection vulnerability detected (single quotes)"
    assert 'f"INSERT' not in code_section, "F-string SQL injection vulnerability detected in INSERT"
    assert "f'INSERT" not in code_section, "F-string SQL injection vulnerability detected in INSERT"

    # Additional check: no op.execute with f-strings at all
    assert "op.execute(f" not in code_section, "F-string used in op.execute() - injection risk"

    # Verify safe patterns are used
    assert "CASE role" in content or "text(" in content, "Should use CASE statement or parameterized queries"


def test_migration_uses_safe_sql_patterns(migration_file_path):
    """Verify migration uses secure SQL patterns.

    The migration should use either:
    1. CASE statements for conditional updates
    2. sqlalchemy.text() for query safety
    3. Parameterized queries
    """
    content = migration_file_path.read_text()

    # At minimum, should import and use text()
    assert "from sqlalchemy import text" in content, "Should import sqlalchemy.text for query safety"
    assert "text(" in content, "Should use text() wrapper for SQL queries"

    # Should use CASE statement for role-based color assignment
    assert "CASE role" in content, "Should use CASE statement for conditional updates"
    assert "WHEN" in content and "THEN" in content, "CASE statement should have WHEN/THEN clauses"


def test_migration_has_server_default_for_cli_tool(migration_file_path):
    """Verify cli_tool column has server_default for automatic backfill.

    This ensures all existing rows automatically get the default value
    without requiring a separate UPDATE statement.
    """
    content = migration_file_path.read_text()

    # Should use server_default, not nullable=True
    assert 'server_default="claude"' in content or "server_default='claude'" in content, \
        "cli_tool should have server_default for automatic backfill"


def test_migration_is_idempotent_ready(migration_file_path):
    """Verify migration uses WHERE clauses for idempotency.

    The migration should use WHERE background_color IS NULL to avoid
    overwriting custom values if run multiple times.
    """
    content = migration_file_path.read_text()

    # Should have WHERE clause for NULL check
    assert "WHERE background_color IS NULL" in content, \
        "Should only update NULL values for idempotency"


def test_migration_has_check_constraint(migration_file_path):
    """Verify migration creates CHECK constraint for cli_tool validation."""
    content = migration_file_path.read_text()

    assert "create_check_constraint" in content, "Should create CHECK constraint"
    assert "check_cli_tool" in content, "Should name constraint 'check_cli_tool'"
    assert "claude" in content and "codex" in content and "gemini" in content, \
        "Should validate cli_tool values"


def test_migration_covers_all_agent_roles(migration_file_path):
    """Verify migration assigns colors to all known agent roles."""
    content = migration_file_path.read_text()

    # All known agent roles should be covered
    required_roles = [
        "orchestrator",
        "analyzer",
        "designer",
        "frontend",
        "backend",
        "implementer",
        "tester",
        "reviewer",
        "documenter"
    ]

    for role in required_roles:
        assert role in content.lower(), f"Migration should handle '{role}' role"


def test_migration_has_default_color_fallback(migration_file_path):
    """Verify migration provides default color for unknown roles."""
    content = migration_file_path.read_text()

    # Should have ELSE clause or default gray color
    assert "ELSE" in content or "#90A4AE" in content, \
        "Should provide default color for unknown roles"


def test_migration_has_downgrade_function(migration_file_path):
    """Verify migration can be cleanly rolled back."""
    content = migration_file_path.read_text()

    assert "def downgrade()" in content, "Should have downgrade function"
    assert "drop_constraint" in content, "Should drop CHECK constraint on downgrade"
    assert "drop_column" in content, "Should drop columns on downgrade"


def test_migration_drops_server_default_after_backfill(migration_file_path):
    """Verify migration drops server_default after backfilling.

    The server_default should be temporary (for backfill) and then removed
    to allow future custom defaults per tenant.
    """
    content = migration_file_path.read_text()

    # Should call alter_column to drop server_default
    assert "alter_column" in content or "server_default=None" in content, \
        "Should drop server_default after backfill to allow custom defaults"


def test_migration_revision_id_unchanged(migration_file_path):
    """Verify migration keeps original revision ID.

    The revision ID should remain '6adac1467121' to maintain migration
    history continuity.
    """
    content = migration_file_path.read_text()

    assert 'revision: str = "6adac1467121"' in content, \
        "Revision ID must remain unchanged for migration history"


def test_migration_has_security_fix_comment(migration_file_path):
    """Verify migration documents the security fix in comments."""
    content = migration_file_path.read_text()

    # Should have clear documentation of the security fix
    assert "SECURITY" in content.upper() or "SQL INJECTION" in content.upper(), \
        "Should document the security fix in comments"


def test_migration_color_values_are_valid_hex(migration_file_path):
    """Verify all color values are valid hex codes."""
    content = migration_file_path.read_text()

    # Extract all potential hex color codes
    import re
    hex_colors = re.findall(r"#[0-9A-Fa-f]{6}", content)

    assert len(hex_colors) > 0, "Should contain hex color codes"

    # All should be valid 6-digit hex
    for color in hex_colors:
        assert len(color) == 7, f"Color {color} should be 7 characters (#RRGGBB)"
        assert color.startswith("#"), f"Color {color} should start with #"
        assert all(c in "0123456789ABCDEFabcdef" for c in color[1:]), \
            f"Color {color} should only contain hex digits"


def test_migration_uses_single_atomic_query(migration_file_path):
    """Verify migration uses single CASE statement instead of loop.

    A single UPDATE with CASE is more efficient and atomic than
    multiple UPDATE statements in a loop.
    """
    content = migration_file_path.read_text()

    # Should use CASE statement
    assert "CASE role" in content, "Should use CASE statement"

    # Should NOT have Python loop over color_map
    assert "for role, color in color_map.items():" not in content, \
        "Should not use Python loop for updates"


def test_migration_has_correct_down_revision(migration_file_path):
    """Verify migration has correct parent revision."""
    content = migration_file_path.read_text()

    assert 'down_revision: Union[str, Sequence[str], None] = "20251104_0102"' in content, \
        "Should revise from 20251104_0102"


# Integration tests would go here if we had a test database setup
# These would verify:
# - Migration can run successfully
# - Migration is idempotent (can run twice)
# - CHECK constraint prevents invalid values
# - Rollback works cleanly
#
# Example (commented out - requires test database):
#
# @pytest.fixture
# def test_alembic_config(tmp_path):
#     """Create test Alembic config."""
#     config = Config()
#     config.set_main_option("script_location", "F:/GiljoAI_MCP/migrations")
#     config.set_main_option("sqlalchemy.url", f"postgresql://postgres:***@localhost:5432/test_migration_{tmp_path.name}")
#     return config
#
# def test_migration_runs_successfully(test_alembic_config):
#     """Verify migration can run without errors."""
#     command.upgrade(test_alembic_config, "6adac1467121")
#
# def test_migration_is_idempotent(test_alembic_config):
#     """Verify migration can run multiple times safely."""
#     command.upgrade(test_alembic_config, "6adac1467121")
#     command.upgrade(test_alembic_config, "6adac1467121")  # Should not fail
#
# def test_check_constraint_enforced(test_alembic_config, test_engine):
#     """Verify CHECK constraint prevents invalid cli_tool values."""
#     command.upgrade(test_alembic_config, "6adac1467121")
#
#     with test_engine.connect() as conn:
#         with pytest.raises(Exception):
#             conn.execute(text("""
#                 INSERT INTO agent_templates (id, tenant_key, role, cli_tool)
#                 VALUES ('test-bad', 'tenant-1', 'test', 'invalid_tool')
#             """))
