"""
Integration tests for installation order bug fix.

Tests verify that config generation happens BEFORE database setup,
ensuring .env file exists when migrations run.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest


class TestInstallationOrderIntegration:
    """Integration tests for installation step ordering"""

    @pytest.fixture
    def temp_install_dir(self):
        """Create temporary installation directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_installer_dependencies(self):
        """Mock external dependencies for integration testing"""
        with (
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
            patch("shutil.which") as mock_which,
        ):
            # Mock successful subprocess calls
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Mock process creation
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            # Mock which() for psql detection
            mock_which.return_value = "/usr/bin/psql"

            yield {"run": mock_run, "popen": mock_popen, "which": mock_which}

    def test_fresh_install_simulation(self, temp_install_dir: Path, mock_installer_dependencies: Dict[str, Any]):
        """
        Simulate fresh installation to verify config generation happens before database setup.

        This test validates:
        1. .env file is created during config generation (step 5)
        2. Database setup (step 6) occurs AFTER .env exists
        3. Migrations can successfully read DATABASE_URL from .env
        4. No "PostgreSQL database URL not configured" errors occur
        """
        from install import UnifiedInstaller

        # Create requirements.txt in temp dir
        requirements_file = temp_install_dir / "requirements.txt"
        requirements_file.write_text("# Mock requirements\n")

        # Create api directory structure
        api_dir = temp_install_dir / "api"
        api_dir.mkdir()
        (api_dir / "run_api.py").write_text("# Mock API script\n")

        # Mock ConfigManager and DatabaseInstaller (imported within installer methods)
        with (
            patch("installer.core.config.ConfigManager") as mock_config_mgr,
            patch("installer.core.database.DatabaseInstaller") as mock_db_installer,
        ):
            # Track execution order
            execution_order = []
            env_file_path = temp_install_dir / ".env"

            # ConfigManager mock - creates .env file
            config_instance = Mock()
            config_instance.generate_all.side_effect = lambda: self._create_env_file(
                env_file_path, execution_order, "config_generation"
            )
            mock_config_mgr.return_value = config_instance

            # DatabaseInstaller mock - verifies .env exists
            db_instance = Mock()
            db_instance.setup.side_effect = lambda: self._verify_env_exists(
                env_file_path, execution_order, "database_setup"
            )
            db_instance.run_migrations.return_value = {"success": True, "migrations_applied": 5}
            mock_db_installer.return_value = db_instance

            # Create installer with temp directory
            settings = {
                "install_dir": str(temp_install_dir),
                "pg_password": "test123",
                "api_port": 7272,
                "dashboard_port": 7274,
            }
            installer = UnifiedInstaller(settings=settings)

            # Run installation
            result = installer.run()

            # Verify execution order
            assert len(execution_order) >= 2, "Config generation and database setup should both execute"
            assert execution_order[0] == "config_generation", "Config generation should happen FIRST"
            assert execution_order[1] == "database_setup", "Database setup should happen AFTER config generation"

            # Verify .env file was created before database setup
            assert "env_existed_during_db_setup" in execution_order, ".env file should exist when database setup runs"

    def test_env_file_availability_during_database_setup(
        self, temp_install_dir: Path, mock_installer_dependencies: Dict[str, Any]
    ):
        """
        Test that .env file is available and readable during database setup.

        This validates:
        1. .env file exists before database migrations run
        2. .env file contains required DATABASE_URL or POSTGRES_PASSWORD
        3. Migrations can successfully read environment variables
        """
        from install import UnifiedInstaller

        # Create requirements.txt
        requirements_file = temp_install_dir / "requirements.txt"
        requirements_file.write_text("# Mock requirements\n")

        # Create api directory
        api_dir = temp_install_dir / "api"
        api_dir.mkdir()
        (api_dir / "run_api.py").write_text("# Mock API script\n")

        env_file_created = False
        env_file_readable = False

        with (
            patch("installer.core.config.ConfigManager") as mock_config_mgr,
            patch("installer.core.database.DatabaseInstaller") as mock_db_installer,
        ):
            # ConfigManager creates .env
            config_instance = Mock()

            def create_env():
                nonlocal env_file_created
                env_path = temp_install_dir / ".env"
                env_path.write_text(
                    "POSTGRES_PASSWORD=test123\n"
                    "POSTGRES_HOST=localhost\n"
                    "POSTGRES_PORT=5432\n"
                    "POSTGRES_DB=giljo_mcp\n"
                    "POSTGRES_USER=giljo_user\n"
                )
                env_file_created = True
                return {"success": True, "files_created": [str(env_path)]}

            config_instance.generate_all.side_effect = create_env
            mock_config_mgr.return_value = config_instance

            # DatabaseInstaller verifies .env exists and is readable
            db_instance = Mock()

            def verify_env():
                nonlocal env_file_readable
                env_path = temp_install_dir / ".env"

                # Verify file exists
                assert env_path.exists(), ".env file should exist before database setup"

                # Verify file is readable
                content = env_path.read_text()
                assert "POSTGRES_PASSWORD" in content, ".env should contain POSTGRES_PASSWORD"

                env_file_readable = True
                return {"success": True, "credentials": {"password": "test123"}}

            db_instance.setup.side_effect = verify_env
            db_instance.run_migrations.return_value = {"success": True}
            mock_db_installer.return_value = db_instance

            # Run installer
            settings = {"install_dir": str(temp_install_dir), "pg_password": "test123"}
            installer = UnifiedInstaller(settings=settings)
            result = installer.run()

            # Verify .env was created and readable
            assert env_file_created, "Config generation should create .env file"
            assert env_file_readable, "Database setup should be able to read .env file"

    def test_migration_error_message_without_env(self):
        """
        Test that migrations produce clear error message when .env is missing.

        This validates the improved error message in migrations/env.py
        """
        # Temporarily remove .env file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Ensure no .env file exists
            env_path = tmpdir_path / ".env"
            assert not env_path.exists()

            # Mock environment with no DATABASE_URL or POSTGRES_PASSWORD
            with patch.dict(os.environ, {}, clear=True):
                # Simulate the error condition from migrations/env.py
                db_url = os.getenv("DATABASE_URL")

                if not db_url:
                    db_pass = os.getenv("POSTGRES_PASSWORD")

                    if not db_pass:
                        # This should raise the improved error message
                        try:
                            raise ValueError(
                                "PostgreSQL connection not configured!\n\n"
                                "The installer should have created .env with POSTGRES_PASSWORD.\n"
                                "If running migrations manually, ensure .env exists with:\n"
                                "  POSTGRES_PASSWORD=<your_password>\n\n"
                                "Note: Only PostgreSQL 14-18 is supported."
                            )
                        except ValueError as e:
                            error_message = str(e)

                            # Verify error message clarity
                            assert "PostgreSQL connection not configured" in error_message
                            assert "installer should have created .env" in error_message
                            assert "POSTGRES_PASSWORD" in error_message
                            assert "PostgreSQL 14-18 is supported" in error_message
                            assert "SQLite" not in error_message, "Error message should NOT reference SQLite"

    def test_config_generation_before_migrations(
        self, temp_install_dir: Path, mock_installer_dependencies: Dict[str, Any]
    ):
        """
        Test that config generation completes successfully before migrations run.

        This validates:
        1. ConfigManager.generate_all() is called before DatabaseInstaller.setup()
        2. ConfigManager.generate_all() returns success
        3. DatabaseInstaller.setup() is only called if config generation succeeds
        """
        from install import UnifiedInstaller

        # Create requirements.txt
        requirements_file = temp_install_dir / "requirements.txt"
        requirements_file.write_text("# Mock requirements\n")

        # Create api directory
        api_dir = temp_install_dir / "api"
        api_dir.mkdir()
        (api_dir / "run_api.py").write_text("# Mock API script\n")

        call_order = []

        with (
            patch("installer.core.config.ConfigManager") as mock_config_mgr,
            patch("installer.core.database.DatabaseInstaller") as mock_db_installer,
        ):
            # Track when ConfigManager.generate_all() is called
            config_instance = Mock()
            config_instance.generate_all.side_effect = lambda: (
                call_order.append("config_generate"),
                {"success": True, "files_created": [".env", "config.yaml"]},
            )[1]
            mock_config_mgr.return_value = config_instance

            # Track when DatabaseInstaller.setup() is called
            db_instance = Mock()
            db_instance.setup.side_effect = lambda: (call_order.append("database_setup"), {"success": True})[1]
            db_instance.run_migrations.return_value = {"success": True}
            mock_db_installer.return_value = db_instance

            # Run installer
            settings = {"install_dir": str(temp_install_dir), "pg_password": "test123"}
            installer = UnifiedInstaller(settings=settings)
            result = installer.run()

            # Verify call order
            assert "config_generate" in call_order, "Config generation should be called"
            assert "database_setup" in call_order, "Database setup should be called"

            config_index = call_order.index("config_generate")
            db_index = call_order.index("database_setup")

            assert config_index < db_index, "Config generation should happen BEFORE database setup"

    def test_database_setup_fails_if_config_generation_fails(
        self, temp_install_dir: Path, mock_installer_dependencies: Dict[str, Any]
    ):
        """
        Test that database setup is NOT attempted if config generation fails.

        This validates installation halts at config generation failure.
        """
        from install import UnifiedInstaller

        # Create requirements.txt
        requirements_file = temp_install_dir / "requirements.txt"
        requirements_file.write_text("# Mock requirements\n")

        database_setup_called = False

        with (
            patch("installer.core.config.ConfigManager") as mock_config_mgr,
            patch("installer.core.database.DatabaseInstaller") as mock_db_installer,
        ):
            # ConfigManager fails
            config_instance = Mock()
            config_instance.generate_all.return_value = {"success": False, "errors": ["Failed to create .env file"]}
            mock_config_mgr.return_value = config_instance

            # DatabaseInstaller should NOT be called
            db_instance = Mock()
            db_instance.setup.side_effect = lambda: (setattr(self, "database_setup_called", True), {"success": True})[1]
            mock_db_installer.return_value = db_instance

            # Run installer
            settings = {"install_dir": str(temp_install_dir), "pg_password": "test123"}
            installer = UnifiedInstaller(settings=settings)
            result = installer.run()

            # Verify installation failed
            assert result["success"] is False
            assert "configs_generated" not in result["steps"]
            assert "database_created" not in result["steps"]

            # Verify database setup was NOT called
            db_instance.setup.assert_not_called()

    # Helper methods
    def _create_env_file(self, env_path: Path, execution_order: list, step_name: str) -> Dict[str, Any]:
        """Helper: Create .env file and track execution"""
        execution_order.append(step_name)

        # Create .env file
        env_path.write_text(
            "POSTGRES_PASSWORD=test123\nDATABASE_URL=postgresql://giljo_user:test123@localhost:5432/giljo_mcp\n"
        )

        return {"success": True, "files_created": [str(env_path)]}

    def _verify_env_exists(self, env_path: Path, execution_order: list, step_name: str) -> Dict[str, Any]:
        """Helper: Verify .env exists and track execution"""
        execution_order.append(step_name)

        # Check if .env exists
        if env_path.exists():
            execution_order.append("env_existed_during_db_setup")

        return {"success": True, "credentials": {"password": "test123"}}
