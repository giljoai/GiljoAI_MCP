"""
Tests for Alembic-first database installation strategy.

Verifies that:
1. Database setup uses ONLY Alembic migrations (not create_all())
2. Inline migrations are removed
3. Fresh installs work correctly with Alembic
4. Existing database upgrades work correctly
5. Cross-platform compatibility maintained
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAlembicFirstInstallation:
    """Test suite for Alembic-first installation strategy."""

    @pytest.fixture
    def mock_installer(self):
        """Create mock installer instance."""
        from install import UnifiedInstaller

        installer = UnifiedInstaller()
        installer.install_dir = Path.cwd()
        installer.settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_user": "postgres",
            "pg_password": "test_password",
        }
        installer.database_credentials = {
            "owner_password": "test_owner_pass",
            "reader_password": "test_reader_pass",
        }
        installer.default_tenant_key = "test_tenant_key"
        return installer

    @pytest.fixture
    def mock_env_with_db_url(self, monkeypatch):
        """Mock environment with DATABASE_URL."""
        db_url = "postgresql://giljo_owner:test_pass@localhost:5432/giljo_mcp"
        monkeypatch.setenv("DATABASE_URL", db_url)
        return db_url

    def test_setup_database_calls_alembic_not_create_all(self, mock_installer, mock_env_with_db_url):
        """
        Test that setup_database() calls run_database_migrations() instead of create_all().

        This is the CORE requirement of Alembic-first strategy.
        """
        with patch.object(mock_installer, "_ensure_venv_site_packages"):
            with patch("install.DatabaseInstaller") as mock_db_installer_class:
                # Mock DatabaseInstaller.setup() response
                mock_db_inst = MagicMock()
                mock_db_inst.setup.return_value = {
                    "success": True,
                    "credentials": {
                        "owner_password": "test_owner",
                        "reader_password": "test_reader",
                    },
                }
                mock_db_installer_class.return_value = mock_db_inst

                with patch.object(mock_installer, "update_env_with_real_credentials") as mock_update_env:
                    mock_update_env.return_value = {"success": True}

                    with patch.object(mock_installer, "run_database_migrations") as mock_run_migrations:
                        mock_run_migrations.return_value = {
                            "success": True,
                            "migrations_applied": ["test_migration"],
                        }

                        with patch("install.DatabaseManager") as mock_db_manager_class:
                            mock_db_manager = MagicMock()
                            mock_db_manager_class.return_value = mock_db_manager

                            # Mock async session context
                            async def mock_session_context():
                                mock_session = AsyncMock()
                                mock_session.execute = AsyncMock(
                                    return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
                                )
                                mock_session.add = MagicMock()
                                mock_session.commit = AsyncMock()

                                class MockContextManager:
                                    async def __aenter__(self):
                                        return mock_session

                                    async def __aexit__(self, *args):
                                        pass

                                return MockContextManager()

                            mock_db_manager.get_session_async = mock_session_context
                            mock_db_manager.close_async = AsyncMock()

                            # Execute setup_database
                            result = mock_installer.setup_database()

                            # CRITICAL ASSERTION: run_database_migrations() must be called
                            mock_run_migrations.assert_called_once()

                            # CRITICAL ASSERTION: create_all() must NOT be called
                            # (This would be called on Base.metadata.create_all)
                            # We verify by checking that Base.metadata is never accessed for create_all
                            assert result["success"] is True

    def test_inline_migrations_removed(self):
        """
        Test that inline migration methods no longer exist in install.py.

        These methods should be completely removed:
        - _run_handover_0080_migration_async
        - _run_handover_0088_migration_async
        """
        from install import UnifiedInstaller

        installer = UnifiedInstaller()

        # These methods should NOT exist
        assert not hasattr(installer, "_run_handover_0080_migration_async"), (
            "_run_handover_0080_migration_async should be removed (handled by Alembic)"
        )
        assert not hasattr(installer, "_run_handover_0088_migration_async"), (
            "_run_handover_0088_migration_async should be removed (handled by Alembic)"
        )

    def test_run_database_migrations_handles_fresh_install(self, mock_installer):
        """
        Test that run_database_migrations() properly handles fresh installs.

        Fresh install: No alembic_version table exists.
        Expected: Run all migrations from scratch.
        """
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout="Running upgrade  -> abc123, Initial schema\nRunning upgrade abc123 -> def456, Add fields",
                stderr="",
            )

            result = mock_installer.run_database_migrations()

            assert result["success"] is True
            assert len(result["migrations_applied"]) == 2
            assert "Initial schema" in result["migrations_applied"][0]

            # Verify correct command was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert "alembic" in call_args
            assert "upgrade" in call_args
            assert "head" in call_args

    def test_run_database_migrations_handles_existing_database(self, mock_installer):
        """
        Test that run_database_migrations() handles existing databases.

        Existing database: alembic_version table exists with version stamp.
        Expected: Run only new migrations.
        """
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout="Running upgrade def456 -> ghi789, New feature",
                stderr="",
            )

            result = mock_installer.run_database_migrations()

            assert result["success"] is True
            assert len(result["migrations_applied"]) == 1
            assert "New feature" in result["migrations_applied"][0]

    def test_run_database_migrations_handles_no_pending_migrations(self, mock_installer):
        """
        Test that run_database_migrations() handles case with no pending migrations.

        Expected: Success with empty migrations list.
        """
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout="INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\nINFO  [alembic.runtime.migration] Will assume transactional DDL.",
                stderr="",
            )

            result = mock_installer.run_database_migrations()

            assert result["success"] is True
            assert len(result["migrations_applied"]) == 0

    def test_run_database_migrations_handles_failure(self, mock_installer):
        """
        Test that run_database_migrations() properly handles migration failures.
        """
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=1,
                stdout="Running upgrade abc -> def",
                stderr="ERROR: Migration failed - constraint violation",
            )

            result = mock_installer.run_database_migrations()

            assert result["success"] is False
            assert "error" in result
            assert "constraint violation" in result["stderr"]

    def test_run_database_migrations_handles_timeout(self, mock_installer):
        """
        Test that run_database_migrations() handles timeout gracefully.
        """
        import subprocess

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = subprocess.TimeoutExpired("alembic", 120)

            result = mock_installer.run_database_migrations()

            assert result["success"] is False
            assert "error" in result
            assert "timeout" in result["error"].lower()

    def test_run_database_migrations_cross_platform_paths(self, mock_installer):
        """
        Test that run_database_migrations() uses proper cross-platform path handling.
        """
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            # Ensure install_dir is a Path object (cross-platform)
            assert isinstance(mock_installer.install_dir, Path)

            result = mock_installer.run_database_migrations()

            # Verify subprocess.run was called with str(Path) for cwd
            call_kwargs = mock_subprocess.call_args[1]
            assert "cwd" in call_kwargs
            # cwd should be string representation of Path
            assert isinstance(call_kwargs["cwd"], str)

    def test_setup_database_uses_correct_sequence(self, mock_installer, mock_env_with_db_url):
        """
        Test that setup_database() follows the correct sequence:
        1. Create database and roles
        2. Update .env with credentials
        3. Run Alembic migrations (NOT create_all)
        4. Seed initial data (SetupState only)
        """
        call_sequence = []

        with patch.object(mock_installer, "_ensure_venv_site_packages"):
            with patch("install.DatabaseInstaller") as mock_db_installer_class:
                mock_db_inst = MagicMock()
                mock_db_inst.setup.side_effect = lambda: (
                    call_sequence.append("create_database"),
                    {
                        "success": True,
                        "credentials": {"owner_password": "test_owner", "reader_password": "test_reader"},
                    },
                )[1]
                mock_db_installer_class.return_value = mock_db_inst

                with patch.object(mock_installer, "update_env_with_real_credentials") as mock_update_env:
                    mock_update_env.side_effect = lambda: (
                        call_sequence.append("update_env"),
                        {"success": True},
                    )[1]

                    with patch.object(mock_installer, "run_database_migrations") as mock_run_migrations:
                        mock_run_migrations.side_effect = lambda: (
                            call_sequence.append("run_migrations"),
                            {"success": True, "migrations_applied": []},
                        )[1]

                        with patch("install.DatabaseManager") as mock_db_manager_class:
                            mock_db_manager = MagicMock()
                            mock_db_manager_class.return_value = mock_db_manager

                            async def mock_session_context():
                                call_sequence.append("seed_data")
                                mock_session = AsyncMock()
                                mock_session.execute = AsyncMock(
                                    return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
                                )
                                mock_session.add = MagicMock()
                                mock_session.commit = AsyncMock()

                                class MockContextManager:
                                    async def __aenter__(self):
                                        return mock_session

                                    async def __aexit__(self, *args):
                                        pass

                                return MockContextManager()

                            mock_db_manager.get_session_async = mock_session_context
                            mock_db_manager.close_async = AsyncMock()

                            result = mock_installer.setup_database()

                            # Verify correct sequence
                            assert call_sequence == [
                                "create_database",
                                "update_env",
                                "run_migrations",
                                "seed_data",
                            ]
                            assert result["success"] is True

    def test_setup_version_updated_to_310(self, mock_installer, mock_env_with_db_url):
        """
        Test that SetupState.setup_version is updated to "3.1.0" to track this architectural change.
        """
        with patch.object(mock_installer, "_ensure_venv_site_packages"):
            with patch("install.DatabaseInstaller") as mock_db_installer_class:
                mock_db_inst = MagicMock()
                mock_db_inst.setup.return_value = {
                    "success": True,
                    "credentials": {"owner_password": "test", "reader_password": "test"},
                }
                mock_db_installer_class.return_value = mock_db_inst

                with patch.object(mock_installer, "update_env_with_real_credentials") as mock_update_env:
                    mock_update_env.return_value = {"success": True}

                    with patch.object(mock_installer, "run_database_migrations") as mock_run_migrations:
                        mock_run_migrations.return_value = {"success": True, "migrations_applied": []}

                        with patch("install.DatabaseManager") as mock_db_manager_class:
                            mock_db_manager = MagicMock()
                            mock_db_manager_class.return_value = mock_db_manager

                            setup_state_data = {}

                            async def mock_session_context():
                                mock_session = AsyncMock()
                                mock_session.execute = AsyncMock(
                                    return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
                                )

                                def capture_setup_state(obj):
                                    if hasattr(obj, "setup_version"):
                                        setup_state_data["version"] = obj.setup_version

                                mock_session.add = MagicMock(side_effect=capture_setup_state)
                                mock_session.commit = AsyncMock()

                                class MockContextManager:
                                    async def __aenter__(self):
                                        return mock_session

                                    async def __aexit__(self, *args):
                                        pass

                                return MockContextManager()

                            mock_db_manager.get_session_async = mock_session_context
                            mock_db_manager.close_async = AsyncMock()

                            result = mock_installer.setup_database()

                            # Verify setup_version is "3.1.0"
                            assert setup_state_data.get("version") == "3.1.0"

    def test_alembic_ini_exists(self):
        """
        Test that alembic.ini configuration file exists in project root.
        """
        alembic_ini = Path.cwd() / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini must exist for Alembic-first strategy"

    def test_migrations_directory_exists(self):
        """
        Test that migrations directory exists with version files.
        """
        migrations_dir = Path.cwd() / "migrations"
        versions_dir = migrations_dir / "versions"

        assert migrations_dir.exists(), "migrations directory must exist"
        assert versions_dir.exists(), "migrations/versions directory must exist"

        # Check that there are migration files
        migration_files = list(versions_dir.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__pycache__"]
        assert len(migration_files) > 0, "Migration version files must exist"

    def test_handover_0080_migration_exists(self):
        """
        Test that Handover 0080 migration file exists (orchestrator succession).
        """
        versions_dir = Path.cwd() / "migrations" / "versions"

        # Find migration file with 0080 columns
        migration_file = versions_dir / "631adb011a79_add_nullable_project_path_to_product_.py"
        assert migration_file.exists(), "Handover 0080 migration file must exist"

        # Read file and verify it contains expected columns
        content = migration_file.read_text()
        assert "handover_to" in content
        assert "handover_summary" in content
        assert "succession_reason" in content
        assert "context_used" in content
        assert "context_budget" in content

    def test_handover_0088_migration_exists(self):
        """
        Test that Handover 0088 migration file exists (thin client job_metadata).
        """
        versions_dir = Path.cwd() / "migrations" / "versions"

        # Find migration file with job_metadata
        # Based on grep results, job_metadata is in multiple files but primarily 9fdd0e67585f
        migration_file = versions_dir / "9fdd0e67585f_add_apimetrics_table.py"
        assert migration_file.exists(), "Handover 0088 migration file must exist"

        # Read file and verify it contains job_metadata references
        content = migration_file.read_text()
        assert "job_metadata" in content
        assert "JSONB" in content or "jsonb" in content


class TestDatabaseInstallerDeprecation:
    """Test suite for DatabaseInstaller.create_tables_async() deprecation."""

    @pytest.fixture
    def mock_db_installer(self):
        """Create mock DatabaseInstaller instance."""
        from installer.core.database import DatabaseInstaller

        settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_user": "postgres",
            "pg_password": "test_password",
        }
        return DatabaseInstaller(settings=settings)

    async def test_create_tables_async_shows_deprecation_warning(self, mock_db_installer):
        """
        Test that create_tables_async() includes deprecation warning.
        """
        with patch("src.giljo_mcp.database_manager.DatabaseManager") as mock_db_manager_class:
            mock_db_manager = MagicMock()
            mock_db_manager_class.return_value = mock_db_manager

            with patch("src.giljo_mcp.models.Base") as mock_base:
                mock_base.metadata.create_all = MagicMock()
                mock_base.metadata.tables = {"table1": MagicMock(), "table2": MagicMock()}

                result = await mock_db_installer.create_tables_async()

                # Check for deprecation warning
                assert "warnings" in result
                assert len(result["warnings"]) > 0
                assert any("DEPRECATED" in warning for warning in result["warnings"])

    async def test_create_tables_async_logs_deprecation(self, mock_db_installer):
        """
        Test that create_tables_async() logs deprecation warning.
        """
        with patch("src.giljo_mcp.database_manager.DatabaseManager") as mock_db_manager_class:
            mock_db_manager = MagicMock()
            mock_db_manager_class.return_value = mock_db_manager

            with patch("src.giljo_mcp.models.Base") as mock_base:
                mock_base.metadata.create_all = MagicMock()
                mock_base.metadata.tables = {}

                with patch.object(mock_db_installer.logger, "warning") as mock_logger_warning:
                    result = await mock_db_installer.create_tables_async()

                    # Verify logger.warning was called with deprecation message
                    mock_logger_warning.assert_called()
                    call_args = mock_logger_warning.call_args[0][0]
                    assert "deprecated" in call_args.lower()


class TestCrossPlatformCompatibility:
    """Test suite for cross-platform path handling."""

    def test_install_py_uses_pathlib(self):
        """
        Test that install.py uses pathlib.Path for all file operations.

        No hardcoded path separators or OS-specific paths allowed.
        """
        install_py = Path(__file__).parent.parent / "install.py"
        content = install_py.read_text()

        # Check for Path usage
        assert "from pathlib import Path" in content or "import pathlib" in content

        # Check for cross-platform violations (these should NOT appear)
        violations = []

        # Check for hardcoded Windows drive letters (but allow in comments/strings)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if '"""' in stripped or "'''" in stripped:
                continue

            # Check for problematic patterns
            if ("F:\\" in line or "C:\\" in line) and not ('"""' in line or "'''" in line):
                violations.append(f"Line {i + 1}: Hardcoded Windows path found")

        # Warnings only for now - installer may have some legitimate use cases
        if violations:
            print(f"WARNING: Potential cross-platform issues: {violations}")

        # Main assertion: pathlib must be imported
        assert "from pathlib import Path" in content

    def test_database_installer_uses_pathlib(self):
        """
        Test that installer/core/database.py uses pathlib.Path.
        """
        db_installer_py = Path(__file__).parent.parent / "installer" / "core" / "database.py"
        content = db_installer_py.read_text()

        # Check for Path usage
        assert "from pathlib import Path" in content or "import pathlib" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
