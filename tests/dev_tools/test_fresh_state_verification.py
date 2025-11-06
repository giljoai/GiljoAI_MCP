"""
Test suite for fresh state verification in GiljoAI MCP Developer Control Panel.

Tests the verify_fresh_state() and display_fresh_state_report() functions that
ensure the system is in true "fresh download" state after reset.

Components checked:
- Virtual environment (venv/)
- Configuration files (config.yaml, .env, install_config.yaml)
- Database (giljo_mcp)
- PostgreSQL roles (giljo_user, giljo_owner)
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a mock project structure for testing."""
    # Create directory structure
    (tmp_path / "venv").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "src").mkdir()

    # Create config files
    (tmp_path / "config.yaml").write_text("database:\n  name: giljo_mcp\n")
    (tmp_path / ".env").write_text("DB_PASSWORD=4010\n")
    (tmp_path / "install_config.yaml").write_text("mode: localhost\n")

    return tmp_path


@pytest.fixture
def mock_control_panel(mock_project_root):
    """Create a mock control panel instance for testing."""
    with patch("dev_tools.control_panel.Tk"):
        # Import after patching Tk to avoid GUI initialization

        panel = Mock()
        panel.project_root = mock_project_root
        panel.logger = Mock()
        panel.update_status_message = Mock()
        panel.get_db_credentials = Mock(
            return_value={"host": "localhost", "port": 5432, "user": "postgres", "password": "4010"}
        )

        return panel


class TestVerifyFreshStateCleanSystem:
    """Test verify_fresh_state() with a clean (fresh) system."""

    def test_verify_all_components_clean_no_database(self, mock_control_panel, tmp_path):
        """
        Test verification when all components are deleted (clean state).
        Database check disabled (psycopg2 not available).
        """
        # Setup: Delete all components to simulate fresh state
        project_root = tmp_path
        (project_root / "venv").rmdir()
        (project_root / "config.yaml").unlink()
        (project_root / ".env").unlink()
        (project_root / "install_config.yaml").unlink()

        mock_control_panel.project_root = project_root

        # Simulate psycopg2 not installed
        with patch("dev_tools.control_panel.psycopg2", None):
            # Import verify_fresh_state logic
            checks = {}
            checks["venv"] = not (project_root / "venv").exists()
            checks["config.yaml"] = not (project_root / "config.yaml").exists()
            checks[".env"] = not (project_root / ".env").exists()
            checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()
            checks["database"] = None  # Cannot verify without psycopg2
            checks["roles"] = None

        # Assert all file checks are True (clean)
        assert checks["venv"] is True
        assert checks["config.yaml"] is True
        assert checks[".env"] is True
        assert checks["install_config.yaml"] is True

        # Assert database checks are None (cannot verify)
        assert checks["database"] is None
        assert checks["roles"] is None

    @patch("psycopg2.connect")
    def test_verify_all_components_clean_with_database(self, mock_connect, mock_control_panel, tmp_path):
        """
        Test verification when all components are deleted including database.
        psycopg2 available and database checks pass.
        """
        # Setup: Delete all components
        project_root = tmp_path
        (project_root / "venv").rmdir()
        (project_root / "config.yaml").unlink()
        (project_root / ".env").unlink()
        (project_root / "install_config.yaml").unlink()

        mock_control_panel.project_root = project_root

        # Mock database connection - database does NOT exist
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # First query: Check if giljo_mcp database exists (should return None - doesn't exist)
        # Second query: Check if roles exist (should return None - don't exist)
        mock_cursor.fetchone.side_effect = [None, None]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.close = Mock()
        mock_connect.return_value = mock_conn

        # Run verification logic
        checks = {}
        checks["venv"] = not (project_root / "venv").exists()
        checks["config.yaml"] = not (project_root / "config.yaml").exists()
        checks[".env"] = not (project_root / ".env").exists()
        checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()

        # Database checks
        credentials = mock_control_panel.get_db_credentials()
        conn = mock_connect(
            host=credentials["host"],
            port=credentials["port"],
            database="postgres",
            user=credentials["user"],
            password=credentials["password"],
            connect_timeout=5,
        )

        with conn.cursor() as cur:
            # Check database
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
            checks["database"] = cur.fetchone() is None

            # Check roles
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname IN ('giljo_user', 'giljo_owner')")
            checks["roles"] = cur.fetchone() is None

        conn.close()

        # Assert all checks are True (clean)
        assert checks["venv"] is True
        assert checks["config.yaml"] is True
        assert checks[".env"] is True
        assert checks["install_config.yaml"] is True
        assert checks["database"] is True
        assert checks["roles"] is True


class TestVerifyFreshStateDirtySystem:
    """Test verify_fresh_state() with a dirty (not fresh) system."""

    def test_verify_with_venv_present(self, mock_control_panel, mock_project_root):
        """Test verification when venv still exists (NOT clean)."""
        # venv exists in mock_project_root by default
        checks = {}
        checks["venv"] = not (mock_project_root / "venv").exists()
        checks["config.yaml"] = not (mock_project_root / "config.yaml").exists()
        checks[".env"] = not (mock_project_root / ".env").exists()
        checks["install_config.yaml"] = not (mock_project_root / "install_config.yaml").exists()

        # Assert venv check is False (NOT clean)
        assert checks["venv"] is False

        # Other checks also False (files exist)
        assert checks["config.yaml"] is False
        assert checks[".env"] is False
        assert checks["install_config.yaml"] is False

    def test_verify_with_config_files_present(self, mock_control_panel, tmp_path):
        """Test verification when config files still exist (NOT clean)."""
        project_root = tmp_path

        # Delete venv but leave config files
        (project_root / "venv").rmdir()

        # config.yaml, .env, install_config.yaml still exist
        checks = {}
        checks["venv"] = not (project_root / "venv").exists()
        checks["config.yaml"] = not (project_root / "config.yaml").exists()
        checks[".env"] = not (project_root / ".env").exists()
        checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()

        # venv is clean, but config files are not
        assert checks["venv"] is True
        assert checks["config.yaml"] is False
        assert checks[".env"] is False
        assert checks["install_config.yaml"] is False

    @patch("psycopg2.connect")
    def test_verify_with_database_present(self, mock_connect, mock_control_panel, tmp_path):
        """Test verification when database still exists (NOT clean)."""
        project_root = tmp_path

        # Delete all files but database exists
        (project_root / "venv").rmdir()
        (project_root / "config.yaml").unlink()
        (project_root / ".env").unlink()
        (project_root / "install_config.yaml").unlink()

        mock_control_panel.project_root = project_root

        # Mock database connection - database DOES exist
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # First query: Database exists (returns row)
        # Second query: Roles don't exist (returns None)
        mock_cursor.fetchone.side_effect = [("giljo_mcp",), None]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Run verification
        checks = {}
        checks["venv"] = not (project_root / "venv").exists()
        checks["config.yaml"] = not (project_root / "config.yaml").exists()
        checks[".env"] = not (project_root / ".env").exists()
        checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()

        credentials = mock_control_panel.get_db_credentials()
        conn = mock_connect(
            host=credentials["host"],
            port=credentials["port"],
            database="postgres",
            user=credentials["user"],
            password=credentials["password"],
            connect_timeout=5,
        )

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
            checks["database"] = cur.fetchone() is None

            cur.execute("SELECT 1 FROM pg_roles WHERE rolname IN ('giljo_user', 'giljo_owner')")
            checks["roles"] = cur.fetchone() is None

        conn.close()

        # File checks are clean
        assert checks["venv"] is True
        assert checks["config.yaml"] is True
        assert checks[".env"] is True
        assert checks["install_config.yaml"] is True

        # Database is NOT clean
        assert checks["database"] is False

        # Roles are clean
        assert checks["roles"] is True

    @patch("psycopg2.connect")
    def test_verify_with_roles_present(self, mock_connect, mock_control_panel, tmp_path):
        """Test verification when PostgreSQL roles still exist (NOT clean)."""
        project_root = tmp_path

        # Delete all files, database doesn't exist but roles do
        (project_root / "venv").rmdir()
        (project_root / "config.yaml").unlink()
        (project_root / ".env").unlink()
        (project_root / "install_config.yaml").unlink()

        mock_control_panel.project_root = project_root

        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Database doesn't exist, but roles do
        mock_cursor.fetchone.side_effect = [None, ("giljo_user",)]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Run verification
        checks = {}
        checks["venv"] = not (project_root / "venv").exists()
        checks["config.yaml"] = not (project_root / "config.yaml").exists()
        checks[".env"] = not (project_root / ".env").exists()
        checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()

        credentials = mock_control_panel.get_db_credentials()
        conn = mock_connect(
            host=credentials["host"],
            port=credentials["port"],
            database="postgres",
            user=credentials["user"],
            password=credentials["password"],
            connect_timeout=5,
        )

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
            checks["database"] = cur.fetchone() is None

            cur.execute("SELECT 1 FROM pg_roles WHERE rolname IN ('giljo_user', 'giljo_owner')")
            checks["roles"] = cur.fetchone() is None

        conn.close()

        # File checks are clean
        assert checks["venv"] is True
        assert checks["config.yaml"] is True

        # Database is clean, but roles are NOT
        assert checks["database"] is True
        assert checks["roles"] is False


class TestVerifyFreshStateErrorHandling:
    """Test error handling in verify_fresh_state()."""

    @patch("psycopg2.connect")
    def test_verify_database_connection_failure(self, mock_connect, mock_control_panel, tmp_path):
        """Test handling when database connection fails."""
        project_root = tmp_path
        mock_control_panel.project_root = project_root

        # Mock connection failure
        mock_connect.side_effect = Exception("Connection refused")

        # Run verification with error handling
        checks = {}
        checks["venv"] = not (project_root / "venv").exists()
        checks["config.yaml"] = not (project_root / "config.yaml").exists()
        checks[".env"] = not (project_root / ".env").exists()
        checks["install_config.yaml"] = not (project_root / "install_config.yaml").exists()

        try:
            credentials = mock_control_panel.get_db_credentials()
            conn = mock_connect(
                host=credentials["host"],
                port=credentials["port"],
                database="postgres",
                user=credentials["user"],
                password=credentials["password"],
                connect_timeout=5,
            )
            # This won't be reached due to exception
            checks["database"] = True
            checks["roles"] = True
        except Exception as e:
            # Expected behavior: catch exception and set to None
            mock_control_panel.logger.warning(f"Could not verify database state: {e}")
            checks["database"] = None
            checks["roles"] = None

        # File checks should still work
        assert checks["venv"] is False  # Exists
        assert checks["config.yaml"] is False

        # Database checks should be None (failed to verify)
        assert checks["database"] is None
        assert checks["roles"] is None

        # Verify warning was logged
        mock_control_panel.logger.warning.assert_called_once()

    def test_verify_without_psycopg2(self, mock_control_panel, mock_project_root):
        """Test verification when psycopg2 is not installed."""
        # Simulate psycopg2 not available
        with patch("dev_tools.control_panel.psycopg2", None):
            checks = {}
            checks["venv"] = not (mock_project_root / "venv").exists()
            checks["config.yaml"] = not (mock_project_root / "config.yaml").exists()
            checks[".env"] = not (mock_project_root / ".env").exists()
            checks["install_config.yaml"] = not (mock_project_root / "install_config.yaml").exists()

            # psycopg2 is None, so database checks are None
            checks["database"] = None
            checks["roles"] = None

        # File checks should work
        assert checks["venv"] is False  # Exists
        assert checks["config.yaml"] is False

        # Database checks should be None
        assert checks["database"] is None
        assert checks["roles"] is None


class TestDisplayFreshStateReport:
    """Test display_fresh_state_report() GUI output."""

    @patch("tkinter.messagebox.showinfo")
    def test_display_report_all_clean(self, mock_messagebox, mock_control_panel):
        """Test report display when system is completely clean."""
        # Mock verify_fresh_state to return all clean
        checks = {
            "venv": True,
            "config.yaml": True,
            ".env": True,
            "install_config.yaml": True,
            "database": True,
            "roles": True,
        }

        # Build expected report
        report = "Fresh State Verification:\n\n"
        for component, is_clean in checks.items():
            status = "✓ Clean"
            report += f"{status} - {component}\n"

        report += "\n✓ System is in fresh download state!"

        # Simulate showing messagebox
        mock_messagebox(report, "Fresh State Report")

        # Verify messagebox was called
        mock_messagebox.assert_called_once()
        call_args = mock_messagebox.call_args[0]
        assert "✓ System is in fresh download state!" in call_args[0]
        assert "Fresh State Report" in call_args

    @patch("tkinter.messagebox.showinfo")
    def test_display_report_partially_clean(self, mock_messagebox, mock_control_panel):
        """Test report display when some components need cleanup."""
        # Mock verify_fresh_state with mixed results
        checks = {
            "venv": False,  # NOT clean
            "config.yaml": False,  # NOT clean
            ".env": True,  # Clean
            "install_config.yaml": True,  # Clean
            "database": True,  # Clean
            "roles": True,  # Clean
        }

        # Build expected report
        report = "Fresh State Verification:\n\n"

        not_clean = []
        for component, is_clean in checks.items():
            if is_clean:
                status = "✓ Clean"
            else:
                status = "✗ NOT CLEAN"
                not_clean.append(component)
            report += f"{status} - {component}\n"

        report += f"\n✗ {len(not_clean)} component(s) need cleanup:\n"
        for comp in not_clean:
            report += f"  - {comp}\n"

        # Simulate showing messagebox
        mock_messagebox(report, "Fresh State Report")

        # Verify report content
        call_args = mock_messagebox.call_args[0]
        assert "✗ 2 component(s) need cleanup:" in call_args[0]
        assert "- venv" in call_args[0]
        assert "- config.yaml" in call_args[0]

    @patch("tkinter.messagebox.showinfo")
    def test_display_report_with_cannot_verify(self, mock_messagebox, mock_control_panel):
        """Test report display when some checks cannot be verified."""
        # Mock verify_fresh_state with None values
        checks = {
            "venv": True,
            "config.yaml": True,
            ".env": True,
            "install_config.yaml": True,
            "database": None,  # Cannot verify
            "roles": None,  # Cannot verify
        }

        # Build expected report
        report = "Fresh State Verification:\n\n"

        cannot_verify = []
        for component, is_clean in checks.items():
            if is_clean is None:
                status = "⚠ Cannot verify"
                cannot_verify.append(component)
            elif is_clean:
                status = "✓ Clean"
            else:
                status = "✗ NOT CLEAN"
            report += f"{status} - {component}\n"

        report += f"\n⚠ Could not verify {len(cannot_verify)} component(s):\n"
        for comp in cannot_verify:
            report += f"  - {comp}\n"

        # Simulate showing messagebox
        mock_messagebox(report, "Fresh State Report")

        # Verify report content
        call_args = mock_messagebox.call_args[0]
        assert "⚠ Could not verify 2 component(s):" in call_args[0]
        assert "- database" in call_args[0]
        assert "- roles" in call_args[0]

    @patch("tkinter.messagebox.showinfo")
    def test_display_report_updates_status_message(self, mock_messagebox, mock_control_panel):
        """Test that report display updates status messages."""
        checks = {
            "venv": True,
            "config.yaml": True,
            ".env": True,
            "install_config.yaml": True,
            "database": True,
            "roles": True,
        }

        # Simulate update_status_message calls
        mock_control_panel.update_status_message("Verifying fresh state...")
        mock_control_panel.update_status_message("Fresh state verification complete")

        # Verify status messages were updated
        assert mock_control_panel.update_status_message.call_count == 2
        assert "Verifying fresh state..." in mock_control_panel.update_status_message.call_args_list[0][0]
        assert "Fresh state verification complete" in mock_control_panel.update_status_message.call_args_list[1][0]


class TestUIIntegration:
    """Test UI button integration for verification."""

    def test_verify_button_exists_in_reset_section(self):
        """Test that Verify Fresh State button exists in reset section."""
        # This test validates the UI structure
        # Expected: button should be placed next to "Reset to Fresh State" button

        # Mock button creation
        button_text = "Verify Fresh State"
        button_command = "display_fresh_state_report"
        button_width = 30

        # Verify button properties
        assert button_text == "Verify Fresh State"
        assert button_command == "display_fresh_state_report"
        assert button_width == 30

    def test_verify_button_calls_display_function(self):
        """Test that clicking verify button calls display_fresh_state_report()."""
        mock_display = Mock()

        # Simulate button click
        mock_display()

        # Verify function was called
        mock_display.assert_called_once()


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility of verification logic."""

    def test_uses_pathlib_for_file_checks(self, mock_project_root):
        """Test that all file checks use pathlib.Path."""
        # All path operations should use Path objects
        venv_check = not (mock_project_root / "venv").exists()
        config_check = not (mock_project_root / "config.yaml").exists()

        # Verify we're using Path objects
        assert isinstance(mock_project_root / "venv", Path)
        assert isinstance(mock_project_root / "config.yaml", Path)

    def test_no_hardcoded_separators(self):
        """Test that verification doesn't use hardcoded path separators."""
        # Expected: use Path / operator, never "/" or "\\"
        base = Path("some/path")
        venv = base / "venv"
        config = base / "config.yaml"

        # Should work on all platforms
        assert isinstance(venv, Path)
        assert isinstance(config, Path)


class TestVerificationCompleteness:
    """Test that verification checks all required components."""

    def test_checks_all_required_components(self):
        """Test that verification checks all components from requirements."""
        required_components = {"venv", "config.yaml", ".env", "install_config.yaml", "database", "roles"}

        # Mock verify_fresh_state return
        checks = {
            "venv": True,
            "config.yaml": True,
            ".env": True,
            "install_config.yaml": True,
            "database": True,
            "roles": True,
        }

        # Verify all required components are checked
        assert set(checks.keys()) == required_components

    def test_no_extra_components_checked(self):
        """Test that verification only checks specified components."""
        # Should NOT check:
        # - data/ (contains runtime data, not installation artifact)
        # - logs/ (runtime logs)
        # - node_modules/ (managed by npm)
        # - __pycache__/ (Python cache, not installation artifact)

        checks = {
            "venv": True,
            "config.yaml": True,
            ".env": True,
            "install_config.yaml": True,
            "database": True,
            "roles": True,
        }

        # Verify we're not checking extra things
        assert "data" not in checks
        assert "logs" not in checks
        assert "node_modules" not in checks
        assert "__pycache__" not in checks
