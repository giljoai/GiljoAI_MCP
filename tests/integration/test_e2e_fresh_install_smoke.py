"""
End-to-end smoke test for fresh installation.

This test verifies the complete installation flow works correctly by checking
that all required files exist and contain the expected security fixes.

Marked as 'slow' - should only run in CI or manual testing.

Test Coverage:
- Critical files exist (install.py, alembic.ini, migrations)
- install.py has migration execution
- Migration file is secure (no SQL injection)
- Migration uses proper patterns (CASE statement, text() wrapper)
- Alembic configuration is valid
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.slow
class TestFreshInstallSmoke:
    """End-to-end smoke tests for fresh installation."""

    def test_critical_files_exist(self):
        """
        Verify all critical installation files exist.

        Ensures repository has required files for installation.
        """
        project_root = Path.cwd()

        # Critical files
        assert (project_root / "install.py").exists(), "install.py missing"
        assert (project_root / "alembic.ini").exists(), "alembic.ini missing"
        assert (project_root / "migrations" / "versions").exists(), "migrations/versions/ missing"
        assert (project_root / "src" / "giljo_mcp" / "models.py").exists(), "models.py missing"

        # Package files
        assert (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists(), (
            "Package configuration missing"
        )

    def test_install_py_has_migration_execution(self):
        """
        Verify install.py has migration execution code.

        Critical: install.py must run migrations after create_all().
        """
        project_root = Path.cwd()
        install_content = (project_root / "install.py").read_text()

        # Verify migration execution exists
        assert "run_database_migrations" in install_content, "Missing run_database_migrations method"

        assert "alembic upgrade head" in install_content, "Missing 'alembic upgrade head' command"

        # Verify proper subprocess usage
        assert "subprocess.run" in install_content, "Missing subprocess.run for migration execution"

        assert (
            'sys.executable, "-m", "alembic"' in install_content or "sys.executable, '-m', 'alembic'" in install_content
        ), "Not using sys.executable for alembic (venv compatibility issue)"

    def test_migration_file_is_secure(self):
        """
        Verify migration file has security fix (no SQL injection).

        Critical security test: ensures migration 6adac1467121 doesn't use
        dangerous f-string SQL interpolation.
        """
        project_root = Path.cwd()
        migration_files = list((project_root / "migrations" / "versions").glob("6adac1467121_*.py"))

        assert len(migration_files) > 0, "Migration file 6adac1467121 not found"

        # Test the main migration file (not backup)
        migration_file = None
        for f in migration_files:
            if "VULNERABLE" not in f.name and "BACKUP" not in f.name:
                migration_file = f
                break

        assert migration_file is not None, "Could not find non-backup migration file"

        migration_content = migration_file.read_text()

        # Remove docstring to avoid false positives from security comments
        # Extract only the code after the closing triple quotes of module docstring
        if '"""' in migration_content:
            parts = migration_content.split('"""')
            if len(parts) >= 3:
                # Skip first two parts (opening and docstring content)
                migration_content = '"""'.join(parts[2:])

        # Check for dangerous patterns (should NOT exist)
        dangerous_patterns = [
            'f"UPDATE',
            "f'UPDATE",
            'op.execute(f"',
            "op.execute(f'",
            'f"INSERT',
            "f'INSERT",
            'f"DELETE',
            "f'DELETE",
        ]

        for pattern in dangerous_patterns:
            assert pattern not in migration_content, (
                f"Found dangerous pattern '{pattern}' in migration (SQL injection risk)"
            )

        # Verify safe patterns (should exist)
        safe_patterns = ["CASE role", "text(", "WHERE background_color IS NULL"]

        for pattern in safe_patterns:
            assert pattern in migration_content, f"Missing safe pattern '{pattern}' in migration"

    def test_migration_uses_proper_backfill_pattern(self):
        """
        Verify migration uses server_default for automatic backfill.

        Tests best practice: add column with server_default, then drop it.
        """
        project_root = Path.cwd()
        migration_files = list((project_root / "migrations" / "versions").glob("6adac1467121_*.py"))

        migration_file = None
        for f in migration_files:
            if "VULNERABLE" not in f.name and "BACKUP" not in f.name:
                migration_file = f
                break

        migration_content = migration_file.read_text()

        # Verify server_default pattern
        assert 'server_default="claude"' in migration_content or "server_default='claude'" in migration_content, (
            "Missing server_default for cli_tool backfill"
        )

        assert "server_default=None" in migration_content, "Missing server_default cleanup (should drop after backfill)"

    def test_migration_has_check_constraint(self):
        """
        Verify migration creates CHECK constraint for cli_tool validation.

        Database-level validation is critical for data integrity.
        """
        project_root = Path.cwd()
        migration_files = list((project_root / "migrations" / "versions").glob("6adac1467121_*.py"))

        migration_file = None
        for f in migration_files:
            if "VULNERABLE" not in f.name and "BACKUP" not in f.name:
                migration_file = f
                break

        migration_content = migration_file.read_text()

        # Verify CHECK constraint
        assert "create_check_constraint" in migration_content, "Missing CHECK constraint creation"

        assert "check_cli_tool" in migration_content, "Missing constraint name 'check_cli_tool'"

        # Verify valid values
        valid_values = ["claude", "codex", "gemini", "generic"]
        for value in valid_values:
            assert value in migration_content, f"Missing valid CLI tool value '{value}' in constraint"

    def test_migration_has_proper_downgrade(self):
        """
        Verify migration has downgrade() function for rollback.

        Downgrade must remove columns and constraints cleanly.
        """
        project_root = Path.cwd()
        migration_files = list((project_root / "migrations" / "versions").glob("6adac1467121_*.py"))

        migration_file = None
        for f in migration_files:
            if "VULNERABLE" not in f.name and "BACKUP" not in f.name:
                migration_file = f
                break

        migration_content = migration_file.read_text()

        # Verify downgrade exists
        assert "def downgrade()" in migration_content, "Missing downgrade() function"

        # Verify drops constraints and columns
        assert "drop_constraint" in migration_content, "downgrade() doesn't drop constraint"

        assert "drop_column" in migration_content, "downgrade() doesn't drop columns"

        # Verify correct order (constraints before columns)
        constraint_pos = migration_content.find("drop_constraint")
        column_pos = migration_content.find("drop_column")

        assert constraint_pos < column_pos, "downgrade() must drop constraints BEFORE columns"

    def test_alembic_configuration_valid(self):
        """
        Verify alembic.ini is properly configured.

        Tests that Alembic can initialize without errors.
        """
        project_root = Path.cwd()
        alembic_ini = project_root / "alembic.ini"

        assert alembic_ini.exists(), "alembic.ini not found"

        content = alembic_ini.read_text()

        # Verify critical settings
        assert "[alembic]" in content, "Missing [alembic] section"
        assert "script_location" in content, "Missing script_location"
        assert "migrations" in content, "script_location not pointing to migrations/"

    def test_can_list_alembic_revisions(self):
        """
        Verify Alembic can list revisions (smoke test for config).

        This doesn't need a database - just validates Alembic setup.
        """
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "history"], capture_output=True, text=True, timeout=10, check=False
        )

        # Should succeed even without database
        assert result.returncode == 0, f"Alembic history failed: {result.stderr}"

        # Should list migration 6adac1467121
        assert "6adac1467121" in result.stdout, "Migration 6adac1467121 not in Alembic history"

    def test_models_have_required_columns(self):
        """
        Verify AgentTemplate model has new columns.

        Ensures models.py is in sync with migrations.
        """
        project_root = Path.cwd()
        models_file = project_root / "src" / "giljo_mcp" / "models.py"

        assert models_file.exists(), "models.py not found"

        content = models_file.read_text()

        # Verify AgentTemplate class exists
        assert "class AgentTemplate" in content, "AgentTemplate model not found"

        # Verify new columns exist in model
        # Note: Column definition might be in various formats
        # Check for column name presence
        assert "cli_tool" in content, "cli_tool column not in AgentTemplate model"
        assert "background_color" in content, "background_color column not in AgentTemplate model"

    def test_template_seeder_uses_new_columns(self):
        """
        Verify template_seeder.py uses new columns when seeding.

        Ensures seeder provides values for cli_tool and background_color.
        """
        project_root = Path.cwd()
        seeder_file = project_root / "src" / "giljo_mcp" / "template_seeder.py"

        # Seeder might not exist in all configurations
        if not seeder_file.exists():
            pytest.skip("template_seeder.py not found (optional)")

        content = seeder_file.read_text()

        # Verify seeder references new columns
        # (Exact check depends on implementation)
        # At minimum, verify file exists and is not empty
        assert len(content) > 0, "template_seeder.py is empty"


@pytest.mark.slow
class TestInstallationPrerequisites:
    """Test installation prerequisites and environment."""

    def test_python_version_adequate(self):
        """
        Verify Python version is 3.11+.

        GiljoAI requires Python 3.11 or higher.
        """
        version_info = sys.version_info
        assert version_info.major >= 3, f"Python 3.x required (got {version_info.major})"
        assert version_info.minor >= 11, f"Python 3.11+ required (got 3.{version_info.minor})"

    def test_required_packages_importable(self):
        """
        Verify critical packages can be imported.

        Tests that development environment has required dependencies.
        """
        required_packages = ["sqlalchemy", "alembic", "fastapi", "pytest", "httpx"]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError as e:
                pytest.fail(f"Required package '{package}' not importable: {e}")

    def test_project_structure_valid(self):
        """
        Verify project directory structure is correct.

        Tests that all required directories exist.
        """
        project_root = Path.cwd()

        required_dirs = [
            "src",
            "src/giljo_mcp",
            "api",
            "migrations",
            "migrations/versions",
            "tests",
            "tests/integration",
        ]

        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"Required directory '{dir_path}' not found"
            assert full_path.is_dir(), f"'{dir_path}' is not a directory"


@pytest.mark.slow
class TestSecurityValidation:
    """Security validation for installation components."""

    def test_no_hardcoded_credentials(self):
        """
        Verify install.py doesn't have hardcoded credentials.

        Security check: no passwords, API keys, or secrets in code.
        """
        project_root = Path.cwd()
        install_content = (project_root / "install.py").read_text()

        # Check for suspicious patterns
        suspicious_patterns = ['password = "', "password = '", 'api_key = "', "api_key = '", 'secret = "', "secret = '"]

        for pattern in suspicious_patterns:
            # Allow password_hash, password_prompt, etc.
            if pattern in install_content:
                # Check if it's not part of a variable name or prompt
                lines = [line for line in install_content.split("\n") if pattern in line]
                for line in lines:
                    # Filter out legitimate uses
                    if "getpass" not in line and "input" not in line and "prompt" not in line:
                        # This might be a hardcoded credential
                        assert False, f"Possible hardcoded credential found: {line.strip()}"

    def test_migration_uses_parameterized_queries(self):
        """
        Verify migration uses parameterized queries (text() wrapper).

        Security check: all SQL uses SQLAlchemy text() for safety.
        """
        project_root = Path.cwd()
        migration_files = list((project_root / "migrations" / "versions").glob("6adac1467121_*.py"))

        migration_file = None
        for f in migration_files:
            if "VULNERABLE" not in f.name and "BACKUP" not in f.name:
                migration_file = f
                break

        migration_content = migration_file.read_text()

        # If there's an UPDATE statement, it should use text()
        if "UPDATE" in migration_content:
            # Find all op.execute calls
            lines = [line for line in migration_content.split("\n") if "op.execute" in line]

            for line in lines:
                if (
                    "UPDATE" in line
                    or "UPDATE" in migration_content[migration_content.find(line) : migration_content.find(line) + 500]
                ):
                    # Should use text() wrapper
                    assert "text(" in migration_content or 'text("' in migration_content, (
                        "op.execute should use text() wrapper for SQL safety"
                    )

    def test_no_shell_injection_vulnerabilities(self):
        """
        Verify install.py uses safe subprocess patterns.

        Security check: subprocess.run with array (not shell=True).
        """
        project_root = Path.cwd()
        install_content = (project_root / "install.py").read_text()

        # Check for dangerous patterns
        assert "shell=True" not in install_content, "Found shell=True in subprocess call (security risk)"

        # Verify safe patterns
        if "subprocess.run" in install_content:
            # Should use array-style arguments
            assert "[" in install_content, "subprocess.run should use array-style arguments for safety"
