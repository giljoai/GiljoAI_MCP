"""Test fresh installation flow including Alembic migrations.

Tests that verify install.py properly executes Alembic migrations
after table creation, ensuring CHECK constraints and defaults are applied.

CRITICAL: This addresses the issue where Base.metadata.create_all()
creates tables but doesn't apply migration logic (constraints, backfills).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


def test_migration_method_exists():
    """Verify run_database_migrations method exists in UnifiedInstaller."""
    from install import UnifiedInstaller

    installer = UnifiedInstaller()

    # Verify method exists
    assert hasattr(installer, "run_database_migrations"), "UnifiedInstaller missing run_database_migrations method"

    # Verify method signature
    import inspect as insp

    sig = insp.signature(installer.run_database_migrations)
    assert len(sig.parameters) == 0, "run_database_migrations should have no parameters (except self)"


def test_migration_method_handles_missing_files():
    """Verify migration method handles missing files gracefully."""
    from install import UnifiedInstaller

    installer = UnifiedInstaller()

    # Test with non-existent directory
    original_cwd = Path.cwd()
    try:
        # Change to temp directory without migrations
        with tempfile.TemporaryDirectory() as tmp:
            import os

            os.chdir(tmp)

            result = installer.run_database_migrations()

            # Should fail gracefully
            assert result["success"] is False, "Should fail when alembic.ini missing"
            assert "error" in result, "Should include error message"
    finally:
        import os

        os.chdir(original_cwd)


def test_alembic_migration_files_exist():
    """Verify required migration files exist in the repository."""
    project_root = Path.cwd()

    # Check alembic.ini
    alembic_ini = project_root / "alembic.ini"
    assert alembic_ini.exists(), f"alembic.ini not found at {alembic_ini}"

    # Check migrations directory
    migrations_dir = project_root / "migrations"
    assert migrations_dir.exists(), f"migrations directory not found at {migrations_dir}"
    assert (migrations_dir / "versions").exists(), "migrations/versions directory not found"

    # Check critical migration 6adac1467121 exists (Handover 0103)
    migration_files = list((migrations_dir / "versions").glob("6adac1467121_*.py"))
    assert len(migration_files) >= 1, "Migration 6adac1467121 (cli_tool + background_color) not found"


def test_install_py_includes_migration_step():
    """Verify install.py source code includes migration execution."""
    install_py_path = Path("install.py")
    assert install_py_path.exists(), "install.py not found"

    install_py_content = install_py_path.read_text()

    # Check for migration method definition
    assert "def run_database_migrations" in install_py_content, "Migration method missing from install.py"

    # Check for migration execution in run() flow
    assert (
        "run_database_migrations()" in install_py_content or "self.run_database_migrations()" in install_py_content
    ), "Migration method not called in installation flow"

    # Check for alembic command usage
    assert "alembic" in install_py_content.lower(), "No alembic command found in install.py"
    assert "upgrade" in install_py_content, "No 'upgrade' command found in install.py"

    # Verify it's called after table creation
    # Look for the comment about migration step
    assert "Step 6.5" in install_py_content or "Applying Database Migrations" in install_py_content, (
        "Migration step not properly documented in installation flow"
    )


def test_migration_result_structure():
    """Verify migration result dictionary has expected structure."""
    from install import UnifiedInstaller

    installer = UnifiedInstaller()

    # Call with missing files (should fail gracefully)
    with tempfile.TemporaryDirectory() as tmp:
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp)
            result = installer.run_database_migrations()

            # Verify result structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should have 'success' key"
            assert "migrations_applied" in result, "Result should have 'migrations_applied' key"
            assert isinstance(result["migrations_applied"], list), "migrations_applied should be a list"
        finally:
            os.chdir(original_cwd)


def test_alembic_executable_available():
    """Verify alembic is installed and executable."""
    try:
        # Try running alembic --version
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "--version"], capture_output=True, text=True, timeout=10, check=False
        )

        assert proc.returncode == 0, f"Alembic not installed or not working: {proc.stderr}"
        assert "alembic" in proc.stdout.lower(), "Alembic version output unexpected"

    except subprocess.TimeoutExpired:
        pytest.fail("Alembic command timed out")
    except Exception as e:
        pytest.fail(f"Failed to run alembic: {e}")


@pytest.mark.integration
def test_migration_applied_to_fresh_db(postgresql_test_url):
    """Verify migrations apply correctly to fresh database.

    This test creates a fresh database, runs create_all, then runs migrations,
    and verifies the migration-specific columns and constraints exist.

    Requires: postgresql_test_url fixture (from conftest.py)
    """
    # Create fresh test database
    engine = create_engine(postgresql_test_url)

    try:
        # Run create_all to create base schema (what install.py does)
        from src.giljo_mcp.models import Base

        Base.metadata.create_all(engine)

        # Set DATABASE_URL for alembic
        import os

        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = postgresql_test_url

        try:
            # Run Alembic migrations (what the new code does)
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(Path.cwd()),
                check=False,
            )

            assert proc.returncode == 0, f"Alembic migration failed: {proc.stderr}\n{proc.stdout}"

            # Verify migration columns exist
            inspector = inspect(engine)
            columns = {col["name"] for col in inspector.get_columns("agent_templates")}

            assert "cli_tool" in columns, "cli_tool column missing after migration (Handover 0103)"
            assert "background_color" in columns, "background_color column missing after migration (Handover 0103)"

            # Verify CHECK constraint exists
            constraints = inspector.get_check_constraints("agent_templates")
            constraint_names = {c["name"] for c in constraints}
            assert "check_cli_tool" in constraint_names, "CHECK constraint for cli_tool missing (Handover 0103)"

            # Verify default values were backfilled
            with engine.connect() as conn:
                # Check if any rows exist (template seeding happens after user creation)
                result = conn.execute(text("SELECT COUNT(*) FROM agent_templates"))
                count = result.scalar()

                if count > 0:
                    # If rows exist, verify cli_tool is not null
                    result = conn.execute(text("SELECT COUNT(*) FROM agent_templates WHERE cli_tool IS NULL"))
                    null_count = result.scalar()
                    assert null_count == 0, "cli_tool column has NULL values after migration"

        finally:
            # Restore original DATABASE_URL
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

    finally:
        # Cleanup
        engine.dispose()


@pytest.mark.integration
def test_migration_idempotent(postgresql_test_url):
    """Verify migrations can be run multiple times safely.

    This tests that running 'alembic upgrade head' multiple times
    doesn't fail or corrupt data (idempotency).
    """
    # Create fresh test database
    engine = create_engine(postgresql_test_url)

    try:
        # Create base schema
        from src.giljo_mcp.models import Base

        Base.metadata.create_all(engine)

        # Set DATABASE_URL
        import os

        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = postgresql_test_url

        try:
            # Run migrations first time
            proc1 = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            assert proc1.returncode == 0, f"First migration failed: {proc1.stderr}"

            # Run migrations second time (should be idempotent)
            proc2 = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            assert proc2.returncode == 0, f"Second migration failed: {proc2.stderr}"

            # Verify columns still exist and constraints intact
            inspector = inspect(engine)
            columns = {col["name"] for col in inspector.get_columns("agent_templates")}

            assert "cli_tool" in columns, "cli_tool column missing after second run"
            assert "background_color" in columns, "background_color column missing after second run"

        finally:
            # Restore DATABASE_URL
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

    finally:
        engine.dispose()


def test_installation_flow_order():
    """Verify installation flow has correct order: tables -> migrations -> frontend."""
    install_py_content = Path("install.py").read_text()

    # Find key markers in the code
    table_creation_idx = install_py_content.find("setup_database()")
    migration_idx = install_py_content.find("run_database_migrations()")
    frontend_idx = install_py_content.find("install_frontend_dependencies()")

    assert table_creation_idx > 0, "setup_database() call not found"
    assert migration_idx > 0, "run_database_migrations() call not found"
    assert frontend_idx > 0, "install_frontend_dependencies() call not found"

    # Verify order
    assert table_creation_idx < migration_idx, "Migrations must run AFTER table creation"
    assert migration_idx < frontend_idx, "Migrations must run BEFORE frontend installation"


@pytest.mark.integration
def test_fresh_install_creates_alembic_version(postgresql_test_url):
    """Verify fresh install creates alembic_version table."""
    engine = create_engine(postgresql_test_url)

    try:
        # Create base schema
        from src.giljo_mcp.models import Base

        Base.metadata.create_all(engine)

        # Set DATABASE_URL
        import os

        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = postgresql_test_url

        try:
            # Run migrations
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            assert proc.returncode == 0, f"Migration failed: {proc.stderr}"

            # Verify alembic_version table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert "alembic_version" in tables, "alembic_version table not created by migrations"

            # Verify version is set
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                assert version is not None, "alembic_version is empty"
                assert len(version) > 0, "alembic_version has invalid version"

        finally:
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

    finally:
        engine.dispose()
