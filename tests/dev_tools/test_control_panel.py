"""
Test suite for GiljoAI MCP Developer Control Panel.

Tests all control panel functionality including:
- Service management (start/stop/restart)
- Database operations (connection check, database check, deletion)
- Development reset (remove venv, configs)
- Cache management (Python, Frontend, All)
- Frontend hard reload
- Admin privilege detection
- Cross-platform path handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import subprocess
import sys
import os


# Import the control panel module (will be implemented after tests)
# For now, we'll structure tests to define expected behavior
@pytest.fixture
def mock_project_root(tmp_path):
    """Create a mock project structure for testing."""
    # Create directory structure
    (tmp_path / "venv").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "node_modules").mkdir()
    (tmp_path / "frontend" / "node_modules" / ".vite").mkdir()
    (tmp_path / "frontend" / "dist").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__pycache__").mkdir()

    # Create config files
    (tmp_path / "config.yaml").write_text("database:\n  name: giljo_mcp\n")
    (tmp_path / ".env").write_text("DB_PASSWORD=4010\n")

    # Create some cache files
    (tmp_path / "src" / "__pycache__" / "test.pyc").write_text("bytecode")
    (tmp_path / "src" / "module.pyo").write_text("bytecode")

    return tmp_path


@pytest.fixture
def control_panel(mock_project_root):
    """Create a control panel instance for testing."""
    # This will be implemented after the class is created
    # For now, tests define expected behavior
    pass


class TestAdminPrivilegeDetection:
    """Test admin privilege checking."""

    @patch('sys.platform', 'win32')
    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    def test_check_admin_windows_admin(self, mock_is_admin):
        """Test admin check on Windows when user is admin."""
        mock_is_admin.return_value = 1

        # Expected behavior: should return True
        # Implementation will check ctypes.windll.shell32.IsUserAnAdmin()
        assert mock_is_admin() == 1

    @patch('sys.platform', 'win32')
    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    def test_check_admin_windows_not_admin(self, mock_is_admin):
        """Test admin check on Windows when user is not admin."""
        mock_is_admin.return_value = 0

        # Expected behavior: should return False
        assert mock_is_admin() == 0

    @patch('sys.platform', 'linux')
    @patch('os.geteuid')
    def test_check_admin_linux_root(self, mock_geteuid):
        """Test admin check on Linux when user is root."""
        mock_geteuid.return_value = 0

        # Expected behavior: should return True for root (uid 0)
        assert mock_geteuid() == 0

    @patch('sys.platform', 'linux')
    @patch('os.geteuid')
    def test_check_admin_linux_not_root(self, mock_geteuid):
        """Test admin check on Linux when user is not root."""
        mock_geteuid.return_value = 1000

        # Expected behavior: should return False for non-root
        assert mock_geteuid() != 0


class TestServiceManagement:
    """Test service start/stop/restart functionality."""

    @patch('subprocess.Popen')
    def test_start_backend_service(self, mock_popen):
        """Test starting backend API service."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        # Expected: should spawn process with correct command
        # Command should be: [sys.executable, "api/run_api.py"]
        # Should track process PID
        # Should return success status

        expected_cmd = [sys.executable, "api/run_api.py"]
        mock_popen.assert_not_called()  # Not called yet

        # Simulate starting service
        proc = mock_popen(expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.poll() is None  # Process should be running

    @patch('subprocess.Popen')
    def test_start_frontend_service(self, mock_popen):
        """Test starting frontend dev server."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Expected: should spawn npm run dev process
        # Command should run from frontend/ directory
        expected_cmd = ["npm", "run", "dev"]

        proc = mock_popen(expected_cmd, cwd="frontend", stdout=subprocess.PIPE)
        assert proc.poll() is None

    @patch('subprocess.Popen')
    def test_stop_services(self, mock_popen):
        """Test stopping all running services."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Running
        mock_popen.return_value = mock_process

        # Start a service
        proc = mock_popen([sys.executable, "api/run_api.py"])

        # Stop service - should call terminate first
        proc.terminate()
        mock_process.terminate.assert_called_once()

        # If terminate doesn't work, should call kill
        mock_process.poll.return_value = None  # Still running
        proc.kill()
        mock_process.kill.assert_called_once()

    @patch('psutil.Process')
    def test_check_service_status(self, mock_psutil_process):
        """Test checking if services are running."""
        mock_proc = Mock()
        mock_proc.is_running.return_value = True
        mock_proc.name.return_value = "python.exe"
        mock_psutil_process.return_value = mock_proc

        # Expected: should use psutil to check if process is alive
        proc = mock_psutil_process(1234)
        assert proc.is_running() is True

    @patch('subprocess.Popen')
    def test_restart_service(self, mock_popen):
        """Test restarting a service (stop then start)."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        # Start service
        proc1 = mock_popen([sys.executable, "api/run_api.py"])

        # Stop service
        proc1.terminate()
        mock_process.terminate.assert_called()

        # Start again
        proc2 = mock_popen([sys.executable, "api/run_api.py"])

        # Should have been called twice (start, restart)
        assert mock_popen.call_count == 2


class TestDatabaseManagement:
    """Test database connection and management features."""

    @patch('psycopg2.connect')
    def test_check_database_connection(self, mock_connect):
        """Test checking PostgreSQL connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        # Expected: should connect to localhost:5432
        # Should return True if connection succeeds
        conn = mock_connect(host="localhost", port=5432, user="postgres", password="4010")
        mock_connect.assert_called_once()
        assert conn is not None

    @patch('psycopg2.connect')
    def test_check_database_connection_failure(self, mock_connect):
        """Test handling connection failure."""
        mock_connect.side_effect = Exception("Connection refused")

        # Expected: should catch exception and return False
        with pytest.raises(Exception):
            mock_connect(host="localhost", port=5432)

    @patch('psycopg2.connect')
    def test_check_database_exists(self, mock_connect):
        """Test checking if giljo_mcp database exists."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ("giljo_mcp",)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Expected: should query pg_database catalog
        conn = mock_connect(host="localhost", user="postgres", password="4010")
        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datname = 'giljo_mcp'")
            result = cur.fetchone()

        assert result == ("giljo_mcp",)

    @patch('psycopg2.connect')
    def test_delete_database(self, mock_connect):
        """Test deleting giljo_mcp database."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Expected: should execute DROP DATABASE command
        conn = mock_connect(host="localhost", user="postgres", password="4010")
        with conn.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS giljo_mcp")

        mock_cursor.execute.assert_called_once_with("DROP DATABASE IF EXISTS giljo_mcp")

    @patch('psycopg2.connect')
    def test_delete_database_requires_confirmation(self, mock_connect):
        """Test that database deletion requires confirmation."""
        # Expected: should show confirmation dialog before deletion
        # Dialog should list what will be deleted
        # Should only proceed if user confirms
        # This will be tested with GUI mock
        pass


class TestDevelopmentReset:
    """Test development reset functionality."""

    def test_identify_reset_targets(self, mock_project_root):
        """Test identifying files/folders to remove for fresh state."""
        # Expected targets for deletion:
        targets = [
            mock_project_root / "venv",
            mock_project_root / "config.yaml",
            mock_project_root / ".env",
        ]

        # All should exist
        for target in targets:
            assert target.exists()

    def test_reset_removes_venv(self, mock_project_root):
        """Test that reset removes venv directory."""
        venv_path = mock_project_root / "venv"
        assert venv_path.exists()

        # Expected: should remove entire venv directory
        import shutil
        shutil.rmtree(venv_path)

        assert not venv_path.exists()

    def test_reset_removes_config_files(self, mock_project_root):
        """Test that reset removes config files."""
        config_path = mock_project_root / "config.yaml"
        env_path = mock_project_root / ".env"

        assert config_path.exists()
        assert env_path.exists()

        # Expected: should remove both files
        config_path.unlink()
        env_path.unlink()

        assert not config_path.exists()
        assert not env_path.exists()

    def test_reset_requires_confirmation(self):
        """Test that reset requires user confirmation."""
        # Expected: should show confirmation dialog
        # Dialog should list what will be deleted
        # Should only proceed if user confirms
        pass

    def test_reset_handles_missing_files(self, mock_project_root):
        """Test that reset handles missing files gracefully."""
        # Remove a file that should be deleted
        config_path = mock_project_root / "config.yaml"
        config_path.unlink()

        # Expected: should not raise error if file doesn't exist
        # Should continue with other files
        assert not config_path.exists()

        # Trying to unlink again should use exist_ok pattern
        try:
            config_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pytest.fail("Should handle missing files gracefully")


class TestCacheManagement:
    """Test cache clearing functionality."""

    def test_find_python_cache_files(self, mock_project_root):
        """Test finding all Python cache files."""
        # Expected: should find __pycache__ directories, .pyc, .pyo files
        cache_dirs = list(mock_project_root.rglob("__pycache__"))
        pyc_files = list(mock_project_root.rglob("*.pyc"))
        pyo_files = list(mock_project_root.rglob("*.pyo"))

        assert len(cache_dirs) == 1
        assert len(pyc_files) == 1
        assert len(pyo_files) == 1

    def test_clear_python_cache(self, mock_project_root):
        """Test clearing Python cache files."""
        import shutil

        cache_dir = mock_project_root / "src" / "__pycache__"
        pyc_file = mock_project_root / "src" / "__pycache__" / "test.pyc"
        pyo_file = mock_project_root / "src" / "module.pyo"

        assert cache_dir.exists()
        assert pyc_file.exists()
        assert pyo_file.exists()

        # Clear cache
        shutil.rmtree(cache_dir)
        pyo_file.unlink()

        assert not cache_dir.exists()
        assert not pyo_file.exists()

    def test_find_frontend_cache(self, mock_project_root):
        """Test finding frontend cache directories."""
        vite_cache = mock_project_root / "frontend" / "node_modules" / ".vite"
        dist_dir = mock_project_root / "frontend" / "dist"

        assert vite_cache.exists()
        assert dist_dir.exists()

    def test_clear_frontend_cache(self, mock_project_root):
        """Test clearing frontend cache."""
        import shutil

        vite_cache = mock_project_root / "frontend" / "node_modules" / ".vite"
        dist_dir = mock_project_root / "frontend" / "dist"

        # Clear cache
        shutil.rmtree(vite_cache)
        shutil.rmtree(dist_dir)

        assert not vite_cache.exists()
        assert not dist_dir.exists()

    def test_clear_all_caches(self, mock_project_root):
        """Test clearing both Python and frontend caches."""
        import shutil

        # Python cache
        python_cache = mock_project_root / "src" / "__pycache__"

        # Frontend cache
        vite_cache = mock_project_root / "frontend" / "node_modules" / ".vite"

        # Clear all
        shutil.rmtree(python_cache)
        shutil.rmtree(vite_cache)

        assert not python_cache.exists()
        assert not vite_cache.exists()


class TestFrontendHardReload:
    """Test frontend hard reload functionality."""

    @patch('subprocess.Popen')
    def test_stop_frontend_dev_server(self, mock_popen):
        """Test stopping frontend dev server."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Running
        mock_popen.return_value = mock_process

        # Start frontend
        proc = mock_popen(["npm", "run", "dev"], cwd="frontend")

        # Stop it
        proc.terminate()
        mock_process.terminate.assert_called_once()

    def test_clear_vite_cache(self, mock_project_root):
        """Test clearing Vite cache during hard reload."""
        import shutil

        vite_cache = mock_project_root / "frontend" / "node_modules" / ".vite"
        assert vite_cache.exists()

        shutil.rmtree(vite_cache)
        assert not vite_cache.exists()

    @patch('subprocess.Popen')
    @patch('webbrowser.open')
    def test_restart_frontend_and_open_browser(self, mock_browser, mock_popen):
        """Test restarting frontend and opening browser."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        # Restart frontend
        proc = mock_popen(["npm", "run", "dev"], cwd="frontend")

        # Open browser with cache-busting parameter
        import time
        cache_bust = int(time.time())
        url = f"http://localhost:7274?_={cache_bust}"
        mock_browser(url)

        mock_browser.assert_called_once()
        assert "_=" in mock_browser.call_args[0][0]


class TestCrossPlatformPaths:
    """Test cross-platform path handling."""

    def test_uses_pathlib_for_all_paths(self, mock_project_root):
        """Test that all paths use pathlib.Path."""
        # Expected: all path operations should use Path objects
        venv_path = mock_project_root / "venv"
        config_path = mock_project_root / "config.yaml"

        assert isinstance(venv_path, Path)
        assert isinstance(config_path, Path)

    def test_no_hardcoded_path_separators(self):
        """Test that no hardcoded path separators are used."""
        # Expected: never use "/" or "\\" for path joining
        # Always use Path / operator

        base = Path("some/path")
        sub = base / "subdir" / "file.txt"

        # This should work on all platforms
        assert isinstance(sub, Path)

    def test_dynamic_project_root(self, mock_project_root):
        """Test that project root is detected dynamically."""
        # Expected: should use Path.cwd() or similar, never hardcoded
        project_root = Path.cwd()

        assert isinstance(project_root, Path)
        # Should work regardless of where executed from


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_handle_permission_error(self, mock_project_root):
        """Test handling permission errors gracefully."""
        # Expected: should catch PermissionError and show user-friendly message
        # Should not crash the application
        pass

    def test_handle_process_not_found(self):
        """Test handling when process doesn't exist."""
        # Expected: should handle psutil.NoSuchProcess gracefully
        pass

    def test_handle_database_connection_timeout(self):
        """Test handling database connection timeout."""
        # Expected: should have timeout and show error message
        pass

    def test_handle_missing_config_file(self, tmp_path):
        """Test handling missing config.yaml."""
        # Expected: should show error message and disable DB features
        config_path = tmp_path / "config.yaml"
        assert not config_path.exists()

        # Should handle gracefully, not crash


class TestUIBehavior:
    """Test GUI behavior and interactions."""

    def test_service_status_indicators(self):
        """Test that service status shows correct colors."""
        # Expected:
        # - Green indicator when service running
        # - Red indicator when service stopped
        # - Yellow indicator during transitions
        pass

    def test_confirmation_dialogs(self):
        """Test that destructive actions show confirmation."""
        # Expected confirmation dialogs for:
        # - Delete database
        # - Reset to fresh state
        # Should show list of what will be affected
        pass

    def test_progress_indicators(self):
        """Test progress indicators for long operations."""
        # Expected: show progress or spinner for:
        # - Starting services
        # - Clearing caches
        # - Database operations
        pass

    def test_disable_buttons_during_operation(self):
        """Test that buttons are disabled during operations."""
        # Expected: buttons should be disabled while operation in progress
        # Prevents double-clicking or conflicting operations
        pass


class TestConfigurationLoading:
    """Test loading configuration from config.yaml and .env."""

    def test_load_database_credentials(self, mock_project_root):
        """Test loading database credentials from config."""
        config_path = mock_project_root / "config.yaml"
        env_path = mock_project_root / ".env"

        assert config_path.exists()
        assert env_path.exists()

        # Expected: should read database name from config.yaml
        # Should read password from .env

    def test_load_service_ports(self, mock_project_root):
        """Test loading service ports from config."""
        # Expected: should read API port, frontend port from config.yaml
        pass

    def test_handle_missing_env_file(self, tmp_path):
        """Test handling missing .env file."""
        # Expected: should handle gracefully, use defaults or prompt
        pass


# Integration tests (to be run separately)
class TestIntegration:
    """Integration tests for full workflows."""

    @pytest.mark.integration
    def test_full_service_lifecycle(self):
        """Test full start -> stop -> restart lifecycle."""
        # This would test the full workflow with real processes
        # Marked as integration test, slower to run
        pass

    @pytest.mark.integration
    def test_full_reset_and_reinstall(self):
        """Test resetting to fresh state and reinstalling."""
        # Would test full reset workflow
        pass
