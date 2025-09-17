"""
Unit tests for GiljoAI MCP setup.py script
Tests platform detection, path handling, and core utilities
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.original_platform = sys.platform

    def tearDown(self):
        """Restore original platform"""
        sys.platform = self.original_platform

    @patch("sys.platform", "win32")
    def test_windows_detection(self):
        """Test Windows platform detection"""
        from setup import detect_platform

        platform_info = detect_platform()

        assert platform_info["os"] == "windows"
        assert platform_info["path_separator"] == "\\"
        assert platform_info["is_windows"]
        assert not platform_info["is_unix"]

    @patch("sys.platform", "darwin")
    def test_macos_detection(self):
        """Test macOS platform detection"""
        from setup import detect_platform

        platform_info = detect_platform()

        assert platform_info["os"] == "macos"
        assert platform_info["path_separator"] == "/"
        assert not platform_info["is_windows"]
        assert platform_info["is_unix"]

    @patch("sys.platform", "linux")
    def test_linux_detection(self):
        """Test Linux platform detection"""
        from setup import detect_platform

        platform_info = detect_platform()

        assert platform_info["os"] == "linux"
        assert platform_info["path_separator"] == "/"
        assert not platform_info["is_windows"]
        assert platform_info["is_unix"]


class TestPathHandling(unittest.TestCase):
    """Test cross-platform path handling"""

    def test_path_normalization_windows(self):
        """Test path normalization on Windows"""
        from setup import normalize_path

        # Test various Windows path formats
        paths = [
            ("C:\\Users\\test\\data", "C:\\Users\\test\\data"),
            ("C:/Users/test/data", "C:\\Users\\test\\data"),
            ("~/data", str(Path.home() / "data")),
            ("./data", str(Path.cwd() / "data")),
        ]

        with patch("sys.platform", "win32"):
            for input_path, expected in paths:
                result = normalize_path(input_path)
                assert str(result) == expected

    def test_path_normalization_unix(self):
        """Test path normalization on Unix systems"""
        from setup import normalize_path

        # Test various Unix path formats
        paths = [
            ("/home/user/data", "/home/user/data"),
            ("~/data", str(Path.home() / "data")),
            ("./data", str(Path.cwd() / "data")),
        ]

        with patch("sys.platform", "linux"):
            for input_path, expected in paths:
                result = normalize_path(input_path)
                assert str(result) == expected

    def test_directory_creation(self):
        """Test directory creation with proper permissions"""
        from setup import create_directory_structure

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create directory structure
            dirs_created = create_directory_structure(base_path)

            # Verify all required directories exist
            expected_dirs = ["data", "logs", "config", "temp"]
            for dir_name in expected_dirs:
                dir_path = base_path / dir_name
                assert dir_path.exists()
                assert dir_path.is_dir()

            # Verify return value
            assert len(dirs_created) == len(expected_dirs)


class TestDatabaseConfiguration(unittest.TestCase):
    """Test database configuration handling"""

    def test_sqlite_connection_string(self):
        """Test SQLite connection string generation"""
        from setup import generate_database_url

        db_config = {"type": "sqlite", "path": "./data/giljo_mcp.db"}

        url = generate_database_url(db_config)
        assert url.startswith("sqlite:///")
        assert "giljo_mcp.db" in url

    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation"""
        from setup import generate_database_url

        db_config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "user": "testuser",
            "password": "testpass",
            "database": "giljo_mcp",
        }

        url = generate_database_url(db_config)
        assert url == "postgresql://testuser:testpass@localhost:5432/giljo_mcp"

    def test_postgresql_with_ssl(self):
        """Test PostgreSQL connection string with SSL"""
        from setup import generate_database_url

        db_config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "user": "testuser",
            "password": "testpass",
            "database": "giljo_mcp",
            "ssl": True,
        }

        url = generate_database_url(db_config)
        assert "sslmode=require" in url


class TestEnvironmentFileGeneration(unittest.TestCase):
    """Test .env file generation"""

    def test_env_template_parsing(self):
        """Test parsing of .env.example template"""
        from setup import parse_env_template

        template_content = """
# Database Configuration
DATABASE_URL=${DATABASE_URL}

# API Configuration
API_HOST=${API_HOST}
API_PORT=${API_PORT}

# Security
SECRET_KEY=${SECRET_KEY}
"""

        with patch("builtins.open", mock_open(read_data=template_content)):
            variables = parse_env_template(".env.example")

            expected_vars = ["DATABASE_URL", "API_HOST", "API_PORT", "SECRET_KEY"]
            for var in expected_vars:
                assert var in variables

    def test_env_file_generation(self):
        """Test .env file generation with values"""
        from setup import generate_env_file

        config = {
            "DATABASE_URL": "sqlite:///./data/giljo_mcp.db",
            "API_HOST": "0.0.0.0",
            "API_PORT": "6002",
            "DASHBOARD_PORT": "6000",
            "MCP_SERVER_PORT": "6001",
            "WEBSOCKET_PORT": "6003",
            "SECRET_KEY": "test-secret-key-123",
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            env_path = f.name

        try:
            generate_env_file(env_path, config)

            # Read and verify generated file
            with open(env_path) as f:
                content = f.read()

            for key, value in config.items():
                assert f"{key}={value}" in content
        finally:
            os.unlink(env_path)

    def test_env_backup_creation(self):
        """Test backup of existing .env file"""
        from setup import backup_existing_env

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("EXISTING=value")

            backup_path = backup_existing_env(env_path)

            assert backup_path.exists()
            assert ".env.backup" in str(backup_path)
            assert backup_path.read_text() == "EXISTING=value"


class TestPortValidation(unittest.TestCase):
    """Test port availability and validation"""

    @patch("socket.socket")
    def test_port_availability_check(self, mock_socket):
        """Test checking if a port is available"""
        from setup import is_port_available

        # Mock available port
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.bind.return_value = None

        assert is_port_available(6000)
        mock_sock.bind.assert_called_with(("", 6000))
        mock_sock.close.assert_called()

    @patch("socket.socket")
    def test_port_conflict_detection(self, mock_socket):
        """Test detection of port conflicts"""
        from setup import is_port_available

        # Mock occupied port
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.bind.side_effect = OSError("Address already in use")

        assert not is_port_available(5000)

    def test_port_range_validation(self):
        """Test port number range validation"""
        from setup import validate_port

        # Valid ports
        assert validate_port(80)
        assert validate_port(8080)
        assert validate_port(65535)

        # Invalid ports
        assert not validate_port(0)
        assert not validate_port(-1)
        assert not validate_port(65536)
        assert not validate_port("not_a_port")


class TestMigrationDetection(unittest.TestCase):
    """Test AKE-MCP migration detection"""

    @patch("pathlib.Path.exists")
    def test_ake_mcp_detection(self, mock_exists):
        """Test detection of existing AKE-MCP installation"""
        from setup import detect_ake_mcp

        # Mock AKE-MCP exists
        mock_exists.return_value = True

        ake_info = detect_ake_mcp()
        assert ake_info["found"]
        assert "path" in ake_info
        assert "config_exists" in ake_info

    @patch("pathlib.Path.exists")
    def test_no_ake_mcp(self, mock_exists):
        """Test when AKE-MCP is not present"""
        from setup import detect_ake_mcp

        # Mock AKE-MCP doesn't exist
        mock_exists.return_value = False

        ake_info = detect_ake_mcp()
        assert not ake_info["found"]


class TestInputValidation(unittest.TestCase):
    """Test user input validation"""

    def test_yes_no_validation(self):
        """Test yes/no input validation"""
        from setup import validate_yes_no

        # Valid inputs
        valid_inputs = ["y", "Y", "yes", "YES", "n", "N", "no", "NO"]
        for input_val in valid_inputs:
            assert validate_yes_no(input_val)

        # Invalid inputs
        invalid_inputs = ["maybe", "1", "true", "", " "]
        for input_val in invalid_inputs:
            assert not validate_yes_no(input_val)

    def test_database_type_validation(self):
        """Test database type selection validation"""
        from setup import validate_database_type

        # Valid types
        assert validate_database_type("sqlite")
        assert validate_database_type("postgresql")
        assert validate_database_type("1")  # Option number
        assert validate_database_type("2")  # Option number

        # Invalid types
        assert not validate_database_type("mysql")
        assert not validate_database_type("3")
        assert not validate_database_type("")

    def test_path_validation(self):
        """Test file path validation"""
        from setup import validate_path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Valid path
            assert validate_path(temp_dir)

            # Invalid path
            assert not validate_path("/nonexistent/path")

            # Empty path
            assert not validate_path("")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery"""

    def test_rollback_on_failure(self):
        """Test rollback mechanism on setup failure"""
        from setup import SetupManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SetupManager(base_path=temp_dir)

            # Simulate partial setup
            manager.create_directories()
            manager.steps_completed.append("directories")

            # Trigger rollback
            manager.rollback()

            # Verify cleanup
            assert len(manager.steps_completed) == 0

    @patch("builtins.print")
    def test_error_message_formatting(self, mock_print):
        """Test error message formatting and display"""
        from setup import display_error

        error_msg = "Database connection failed"
        display_error(error_msg)

        # Verify error was printed with formatting
        calls = mock_print.call_args_list
        assert any("ERROR" in str(call) for call in calls)
        assert any(error_msg in str(call) for call in calls)

    def test_interrupt_handling(self):
        """Test handling of keyboard interrupt"""
        from setup import SetupManager

        manager = SetupManager()

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = manager.run()
            assert not result["success"]
            assert "interrupted" in result["message"].lower()


if __name__ == "__main__":
    unittest.main()
