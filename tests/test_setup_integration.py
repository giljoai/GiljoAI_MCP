"""
Integration tests for GiljoAI MCP setup.py script
Tests complete setup flows and interactions between components
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestCompleteSetupFlow(unittest.TestCase):
    """Test complete setup flows from start to finish"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="giljo_test_")
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_sqlite_setup_flow(self, mock_getpass, mock_input):
        """Test complete SQLite setup flow"""
        from setup import main

        # Mock user inputs for SQLite setup
        mock_input.side_effect = [
            "1",  # Choose SQLite
            "",  # Use default path
            "y",  # Confirm settings
        ]

        result = main()

        # Verify setup completed successfully
        assert result["success"]

        # Check that all required files/directories were created
        assert Path("data").exists()
        assert Path("logs").exists()
        assert Path("config").exists()
        assert Path(".env").exists()

        # Verify .env contains SQLite configuration
        with open(".env") as f:
            env_content = f.read()
            assert "DATABASE_URL=sqlite:///" in env_content
            assert "DASHBOARD_PORT=6000" in env_content
            assert "MCP_SERVER_PORT=6001" in env_content

    @patch("builtins.input")
    @patch("getpass.getpass")
    @patch("psycopg2.connect")
    def test_postgresql_setup_flow(self, mock_pg_connect, mock_getpass, mock_input):
        """Test complete PostgreSQL setup flow"""
        from setup import main

        # Mock successful PostgreSQL connection
        mock_pg_connect.return_value = MagicMock()

        # Mock user inputs for PostgreSQL setup
        mock_input.side_effect = [
            "2",  # Choose PostgreSQL
            "localhost",  # Host
            "5432",  # Port
            "giljo_user",  # Username
            "giljo_mcp",  # Database name
            "n",  # No SSL
            "y",  # Confirm settings
        ]
        mock_getpass.return_value = "secure_password"

        result = main()

        # Verify setup completed successfully
        assert result["success"]

        # Verify .env contains PostgreSQL configuration
        with open(".env") as f:
            env_content = f.read()
            assert "DATABASE_URL=postgresql://giljo_user:secure_password@localhost:5432/giljo_mcp" in env_content

        # Verify PostgreSQL connection was tested
        mock_pg_connect.assert_called()

    @patch("builtins.input")
    def test_setup_with_existing_env(self, mock_input):
        """Test setup with existing .env file (backup creation)"""
        from setup import main

        # Create existing .env file
        with open(".env", "w") as f:
            f.write("EXISTING_VAR=value\n")

        # Mock user inputs
        mock_input.side_effect = [
            "y",  # Confirm backup
            "1",  # Choose SQLite
            "",  # Use default path
            "y",  # Confirm settings
        ]

        main()

        # Verify backup was created
        backup_files = list(Path().glob(".env.backup*"))
        assert len(backup_files) > 0

        # Verify new .env was created
        with open(".env") as f:
            content = f.read()
            assert "DATABASE_URL" in content


class TestPortConflictHandling(unittest.TestCase):
    """Test port conflict detection and resolution"""

    @patch("socket.socket")
    @patch("builtins.input")
    def test_port_conflict_detection(self, mock_input, mock_socket):
        """Test detection and handling of port conflicts"""
        from setup import check_and_configure_ports

        # Mock port 6000 is occupied, 6100 is free
        def socket_bind_side_effect(address):
            port = address[1]
            if port == 6000:
                raise OSError("Address already in use")

        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.bind.side_effect = socket_bind_side_effect

        # User chooses alternative port
        mock_input.side_effect = ["6100"]

        port_config = check_and_configure_ports()

        # Verify alternative port was selected
        assert port_config["dashboard_port"] == 6100
        assert port_config["mcp_port"] == 6001  # Others remain default

    @patch("subprocess.run")
    @patch("builtins.input")
    def test_ake_mcp_port_conflict(self, mock_input, mock_subprocess):
        """Test detection of AKE-MCP running on conflicting ports"""
        from setup import check_ake_mcp_conflicts

        # Mock check_ports.py output showing AKE-MCP on port 5000
        mock_subprocess.return_value = MagicMock(
            stdout="Port 5000: IN USE (AKE-MCP)\nPort 6000: AVAILABLE", returncode=0
        )

        # User acknowledges conflict
        mock_input.return_value = "y"

        conflicts = check_ake_mcp_conflicts()

        # Verify conflict was detected
        assert not conflicts["port_5000_available"]

        # Verify check_ports.py was called
        mock_subprocess.assert_called()


class TestMigrationFlow(unittest.TestCase):
    """Test migration from existing AKE-MCP installation"""

    def setUp(self):
        """Set up test environment with mock AKE-MCP"""
        self.temp_dir = tempfile.mkdtemp(prefix="giljo_migration_")
        self.ake_dir = Path(self.temp_dir) / "AKE-MCP"
        self.ake_dir.mkdir()

        # Create mock AKE-MCP config
        config_dir = self.ake_dir / "config"
        config_dir.mkdir()

        with open(config_dir / "config.yaml", "w") as f:
            f.write(
                """
database:
  url: postgresql://ake:pass@localhost/ake_mcp
api:
  host: 0.0.0.0
  port: 5000
"""
            )

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("builtins.input")
    @patch("pathlib.Path.home")
    def test_migration_detection_and_prompt(self, mock_home, mock_input):
        """Test detection of AKE-MCP and migration prompt"""
        from setup import detect_and_migrate_ake_mcp

        mock_home.return_value = Path(self.temp_dir)

        # User chooses to migrate
        mock_input.side_effect = [
            "y",  # Yes, migrate
            "1",  # Import configuration
        ]

        with patch("pathlib.Path.exists", return_value=True):
            migration_result = detect_and_migrate_ake_mcp()

        assert migration_result["migration_offered"]
        assert migration_result["config_imported"]

    @patch("builtins.input")
    def test_migration_config_import(self, mock_input):
        """Test importing configuration from AKE-MCP"""
        from setup import import_ake_config

        # Mock user confirmation
        mock_input.return_value = "y"

        imported_config = import_ake_config(str(self.ake_dir))

        # Verify configuration was imported correctly
        assert imported_config["database"]["url"] == "postgresql://ake:pass@localhost/ake_mcp"
        assert imported_config["api"]["port"] == 5000


class TestErrorRecovery(unittest.TestCase):
    """Test error handling and recovery mechanisms"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="giljo_error_")
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("builtins.input")
    def test_database_connection_failure_recovery(self, mock_input):
        """Test recovery from database connection failure"""
        from setup import main

        with patch("psycopg2.connect", side_effect=Exception("Connection failed")):
            # First attempt with PostgreSQL fails, retry with SQLite
            mock_input.side_effect = [
                "2",  # Choose PostgreSQL
                "badhost",  # Invalid host
                "5432",  # Port
                "user",  # Username
                "pass",  # Password
                "db",  # Database
                "n",  # No SSL
                "y",  # Try to continue (will fail)
                "y",  # Retry setup
                "1",  # Choose SQLite this time
                "",  # Default path
                "y",  # Confirm
            ]

            result = main()

            # Should succeed with SQLite after PostgreSQL failure
            assert result["success"]

            with open(".env") as f:
                content = f.read()
                assert PostgreSQLTestHelper.get_test_db_url(async_driver=False) in content

    @patch("builtins.input")
    @patch("pathlib.Path.mkdir")
    def test_permission_error_handling(self, mock_mkdir, mock_input):
        """Test handling of permission errors during directory creation"""
        from setup import create_directories_with_fallback

        # Mock permission error on first attempt
        mock_mkdir.side_effect = [
            PermissionError("Access denied"),
            None,  # Success on retry
            None,
            None,
        ]

        # User chooses alternative location
        mock_input.side_effect = [
            str(Path.home() / "giljo_mcp"),  # Alternative path
            "y",  # Confirm
        ]

        result = create_directories_with_fallback()

        assert result["success"]
        assert "alternative" in result["message"].lower()

    def test_rollback_on_critical_failure(self):
        """Test rollback mechanism on critical failure"""
        from setup import SetupManager

        manager = SetupManager(base_path=self.temp_dir)

        # Simulate partial setup
        Path("data").mkdir()
        Path("logs").mkdir()
        manager.steps_completed = ["directories_created", "env_started"]

        # Create partial .env
        with open(".env", "w") as f:
            f.write("PARTIAL=true\n")

        # Trigger rollback
        manager.rollback()

        # Verify cleanup
        assert not Path(".env").exists()
        assert len(manager.steps_completed) == 0


class TestUserExperience(unittest.TestCase):
    """Test user experience and interaction flow"""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_help_text_display(self, mock_print, mock_input):
        """Test help text and guidance display"""
        from setup import show_help

        show_help()

        # Verify help information was displayed
        print_calls = [str(call) for call in mock_print.call_args_list]

        # Check for key help topics
        help_topics = ["database configuration", "port settings", "migration", "environment variables"]

        for topic in help_topics:
            assert any(topic.lower() in call.lower() for call in print_calls), (
                f"Help topic '{topic}' not found in output"
            )

    @patch("builtins.input")
    def test_configuration_review(self, mock_input):
        """Test configuration review before confirmation"""
        from setup import review_configuration

        config = {
            "database": {"type": "sqlite", "path": "./data/giljo_mcp.db"},
            "ports": {"dashboard": 6000, "mcp": 6001, "api": 6002, "websocket": 6003},
        }

        # User reviews and confirms
        mock_input.return_value = "y"

        confirmed = review_configuration(config)
        assert confirmed

        # User reviews and cancels
        mock_input.return_value = "n"
        confirmed = review_configuration(config)
        assert not confirmed

    @patch("builtins.input")
    @patch("builtins.print")
    def test_progress_indicators(self, mock_print, mock_input):
        """Test progress indicators during setup"""
        from setup import SetupManager

        manager = SetupManager()

        # Mock setup steps
        with patch.object(manager, "create_directories"), patch.object(manager, "generate_env"):
            manager.run_setup()

        # Verify progress messages were shown
        print_calls = [str(call) for call in mock_print.call_args_list]

        progress_indicators = ["Creating", "Configuring", "Generating", "Complete"]
        for indicator in progress_indicators:
            assert any(indicator in call for call in print_calls), f"Progress indicator '{indicator}' not found"


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility"""

    def test_windows_specific_paths(self):
        """Test Windows-specific path handling"""
        from setup import get_default_paths

        with patch("sys.platform", "win32"):
            paths = get_default_paths()

            # Windows should use APPDATA or user profile
            assert "AppData" in str(paths["config"]) or "Users" in str(paths["config"])

    def test_unix_specific_paths(self):
        """Test Unix-specific path handling"""
        from setup import get_default_paths

        with patch("sys.platform", "darwin"):
            paths = get_default_paths()

            # macOS should use ~/Library or ~/.config
            config_str = str(paths["config"])
            assert "Library" in config_str or ".config" in config_str

        with patch("sys.platform", "linux"):
            paths = get_default_paths()

            # Linux should use ~/.config or ~/.local
            config_str = str(paths["config"])
            assert ".config" in config_str or ".local" in config_str

    def test_path_separator_handling(self):
        """Test proper path separator handling across platforms"""
        from setup import build_path

        # Test Windows
        with patch("os.sep", "\\"):
            path = build_path("C:", "Users", "test", "data")
            assert path == "C:\\Users\\test\\data"

        # Test Unix
        with patch("os.sep", "/"):
            path = build_path("/", "home", "test", "data")
            assert path == "/home/test/data"


if __name__ == "__main__":
    unittest.main()
