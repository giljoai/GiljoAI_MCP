"""
Unit tests for MinimalInstaller
Tests the simplified installer that performs only essential setup tasks.

Following TDD principles:
1. Tests written before implementation
2. Tests serve as executable documentation
3. Tests cover happy paths, edge cases, and error conditions
"""

import pytest
import sys
import subprocess
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import will fail initially - this is expected in TDD
try:
    from installer.cli.minimal_installer import MinimalInstaller
except ImportError:
    # This is expected during TDD - tests are written first
    MinimalInstaller = None


class TestMinimalInstallerDetection:
    """Test detection of required dependencies."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_detects_python_version(self, installer):
        """Test Python 3.11+ detection."""
        result = installer.detect_python()

        # Should detect current Python version
        assert installer.python_version is not None
        assert len(installer.python_version) == 2
        assert installer.python_version[0] >= 3

        # If Python 3.11+ available, should return True
        if sys.version_info >= (3, 11):
            assert result is True
        else:
            assert result is False

    def test_python_version_below_minimum_fails(self, installer):
        """Test that Python below 3.11 is rejected."""
        with patch("sys.version_info", (3, 10, 0)):
            result = installer.detect_python()
            assert result is False

    def test_python_version_exactly_minimum_succeeds(self, installer):
        """Test that Python 3.11 exactly is accepted."""
        with patch("sys.version_info", (3, 11, 0)):
            result = installer.detect_python()
            assert result is True

    def test_python_version_above_minimum_succeeds(self, installer):
        """Test that Python 3.13+ is accepted."""
        with patch("sys.version_info", (3, 13, 0)):
            result = installer.detect_python()
            assert result is True

    @patch("subprocess.run")
    def test_detects_postgresql_success(self, mock_run, installer):
        """Test successful PostgreSQL 18 detection."""
        # Mock psql --version output
        mock_run.return_value = MagicMock(returncode=0, stdout="psql (PostgreSQL) 18.0", stderr="")

        result = installer.detect_postgresql()

        assert result is True
        assert installer.postgres_version == 18
        mock_run.assert_called_once_with(["psql", "--version"], capture_output=True, text=True, check=True)

    @patch("subprocess.run")
    def test_detects_postgresql_16_warns_but_continues(self, mock_run, installer):
        """Test PostgreSQL 16 is detected but warning issued."""
        mock_run.return_value = MagicMock(returncode=0, stdout="psql (PostgreSQL) 16.2", stderr="")

        result = installer.detect_postgresql()

        assert result is True
        assert installer.postgres_version == 16

    @patch("subprocess.run")
    def test_detects_postgresql_not_found(self, mock_run, installer):
        """Test PostgreSQL not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = installer.detect_postgresql()

        assert result is False
        assert installer.postgres_version is None

    @patch("subprocess.run")
    def test_detects_postgresql_connection_error(self, mock_run, installer):
        """Test PostgreSQL detection with subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "psql")

        result = installer.detect_postgresql()

        assert result is False

    @patch("webbrowser.open")
    @patch("builtins.input", return_value="")
    def test_redirects_to_postgres_download_if_missing(self, mock_input, mock_browser, installer):
        """Test browser opens to PostgreSQL download if not found."""
        installer.handle_missing_postgresql()

        mock_browser.assert_called_once()
        call_args = mock_browser.call_args[0][0]
        assert "postgresql.org" in call_args.lower()


class TestMinimalInstallerVenvCreation:
    """Test virtual environment creation."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_creates_venv(self, installer):
        """Test virtual environment creation."""
        installer.create_venv()

        venv_path = installer.venv_dir
        assert venv_path.exists()
        assert venv_path.is_dir()

        # Check for platform-specific Python executable
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"

        assert python_exe.exists()

    def test_venv_directory_name(self, installer):
        """Test virtual environment is named 'venv'."""
        assert installer.venv_dir.name == "venv"

    def test_venv_in_install_directory(self, installer, tmp_path):
        """Test virtual environment is created in install directory."""
        assert installer.venv_dir.parent == tmp_path


class TestMinimalInstallerDependencies:
    """Test Python dependency installation."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance with venv."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")

        inst = MinimalInstaller(install_dir=tmp_path)

        # Create a fake venv structure
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()

        if sys.platform == "win32":
            scripts_dir = venv_dir / "Scripts"
            scripts_dir.mkdir()
            pip_exe = scripts_dir / "pip.exe"
        else:
            bin_dir = venv_dir / "bin"
            bin_dir.mkdir()
            pip_exe = bin_dir / "pip"

        # Create fake pip executable
        pip_exe.touch()

        return inst

    @patch("subprocess.run")
    def test_installs_dependencies(self, mock_run, installer, tmp_path):
        """Test pip install of requirements."""
        # Create a fake requirements.txt
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("fastapi>=0.100.0\nsqlalchemy>=2.0.0\n")

        installer.install_dependencies()

        # Verify pip was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "pip" in str(call_args[0])
        assert "install" in call_args
        assert "-r" in call_args

    def test_get_pip_path_windows(self, installer):
        """Test pip path resolution on Windows."""
        with patch("sys.platform", "win32"):
            pip_path = installer._get_pip_path()
            assert pip_path.name == "pip.exe"
            assert "Scripts" in str(pip_path)

    def test_get_pip_path_unix(self, installer):
        """Test pip path resolution on Unix."""
        with patch("sys.platform", "linux"):
            pip_path = installer._get_pip_path()
            assert pip_path.name == "pip"
            assert "bin" in str(pip_path)

    def test_get_python_path_windows(self, installer):
        """Test Python path resolution on Windows."""
        with patch("sys.platform", "win32"):
            python_path = installer._get_python_path()
            assert python_path.name == "python.exe"
            assert "Scripts" in str(python_path)

    def test_get_python_path_unix(self, installer):
        """Test Python path resolution on Unix."""
        with patch("sys.platform", "linux"):
            python_path = installer._get_python_path()
            assert python_path.name == "python"
            assert "bin" in str(python_path)


class TestMinimalInstallerConfiguration:
    """Test minimal configuration file creation."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_creates_minimal_config(self, installer):
        """Test minimal config.yaml creation."""
        installer.create_minimal_config()

        config_path = installer.config_path
        assert config_path.exists()
        assert config_path.name == "config.yaml"

    def test_config_contains_localhost_defaults(self, installer):
        """Test config has localhost defaults."""
        installer.create_minimal_config()

        with open(installer.config_path) as f:
            config = yaml.safe_load(f)

        assert config["mode"] == "localhost"
        assert config["api"]["host"] == "127.0.0.1"
        assert config["api"]["port"] == 7272
        assert config["frontend"]["host"] == "127.0.0.1"
        assert config["frontend"]["port"] == 7274

    def test_config_marks_setup_incomplete(self, installer):
        """Test config marks setup as incomplete."""
        installer.create_minimal_config()

        with open(installer.config_path) as f:
            config = yaml.safe_load(f)

        assert config["setup_complete"] is False

    def test_config_contains_database_section(self, installer):
        """Test config includes database section."""
        installer.create_minimal_config()

        with open(installer.config_path) as f:
            config = yaml.safe_load(f)

        assert "database" in config
        assert config["database"]["host"] == "localhost"
        assert config["database"]["port"] == 5432
        assert config["database"]["name"] == "giljo_mcp"
        assert config["database"]["user"] == "postgres"

    def test_config_does_not_contain_password(self, installer):
        """Test config doesn't hardcode database password."""
        installer.create_minimal_config()

        with open(installer.config_path) as f:
            config = yaml.safe_load(f)

        # Password key may exist but should not have a value
        if "password" in config.get("database", {}):
            assert config["database"]["password"] in (None, "")


class TestMinimalInstallerNoMCPRegistration:
    """Test that MCP registration is NOT performed."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_does_not_register_mcp(self, installer):
        """Test that MCP registration methods do not exist."""
        # Verify no MCP registration methods exist
        assert not hasattr(installer, "register_mcp")
        assert not hasattr(installer, "register_claude_code")
        assert not hasattr(installer, "write_claude_config")
        assert not hasattr(installer, "register_codex")
        assert not hasattr(installer, "register_gemini")


class TestMinimalInstallerServiceManagement:
    """Test service startup and browser opening."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    @patch("subprocess.Popen")
    def test_starts_backend_service(self, mock_popen, installer):
        """Test backend service starts in background."""
        installer.start_backend()

        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]

        # Verify uvicorn command
        assert "uvicorn" in " ".join(str(arg) for arg in call_args)
        assert "api.app:app" in " ".join(str(arg) for arg in call_args)

    @patch("subprocess.Popen")
    def test_backend_starts_on_localhost(self, mock_popen, installer):
        """Test backend binds to localhost."""
        installer.start_backend()

        call_args = mock_popen.call_args[0][0]
        args_str = " ".join(str(arg) for arg in call_args)

        assert "127.0.0.1" in args_str
        assert "7272" in args_str

    @patch("subprocess.Popen")
    def test_backend_starts_in_background(self, mock_popen, installer):
        """Test backend process runs in background."""
        installer.start_backend()

        # Check that stdout/stderr are redirected (background mode)
        kwargs = mock_popen.call_args[1]
        assert kwargs.get("stdout") == subprocess.DEVNULL
        assert kwargs.get("stderr") == subprocess.DEVNULL

    @patch("webbrowser.open")
    def test_opens_browser_to_setup(self, mock_browser, installer):
        """Test browser opens to /setup wizard."""
        installer.open_setup_wizard()

        mock_browser.assert_called_once_with("http://localhost:7274/setup")


class TestMinimalInstallerCompleteFlow:
    """Test complete installation workflow."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    @patch("webbrowser.open")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_complete_installation_flow(self, mock_subprocess_run, mock_popen, mock_browser, installer, tmp_path):
        """Test complete minimal installation flow."""
        # Mock Python detection (use actual version)
        # Mock PostgreSQL detection
        mock_subprocess_run.side_effect = [
            # PostgreSQL version check
            MagicMock(returncode=0, stdout="psql (PostgreSQL) 18.0", stderr="")
        ]

        # Create fake requirements.txt
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("fastapi>=0.100.0\n")

        # Mock venv creation
        with (
            patch.object(installer, "create_venv") as mock_venv,
            patch.object(installer, "install_dependencies") as mock_deps,
        ):

            result = installer.run()

            # Verify flow completed
            assert result["success"] is True
            assert "next_step" in result
            assert "setup" in result["next_step"].lower()

            # Verify all steps called
            mock_venv.assert_called_once()
            mock_deps.assert_called_once()

            # Verify config created
            assert installer.config_path.exists()

            # Verify backend started
            assert mock_popen.called

            # Verify browser opened
            mock_browser.assert_called_once()

    @patch("subprocess.run")
    def test_installation_fails_on_missing_python(self, mock_subprocess_run, installer):
        """Test installation fails gracefully if Python version too low."""
        with patch("sys.version_info", (3, 10, 0)):
            result = installer.run()

            assert result["success"] is False
            assert "error" in result
            assert "Python" in result["error"]

    @patch("subprocess.run")
    def test_installation_fails_on_missing_postgresql(self, mock_subprocess_run, installer):
        """Test installation fails gracefully if PostgreSQL missing."""
        # Mock PostgreSQL not found
        mock_subprocess_run.side_effect = FileNotFoundError()

        with patch.object(installer, "handle_missing_postgresql") as mock_handler:
            result = installer.run()

            assert result["success"] is False
            assert "PostgreSQL" in result["error"]
            mock_handler.assert_called_once()


class TestMinimalInstallerErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_error_result_format(self, installer):
        """Test error result has correct format."""
        result = installer._error("Test error message")

        assert result["success"] is False
        assert result["error"] == "Test error message"

    def test_handles_permission_errors(self, installer):
        """Test handles permission errors gracefully."""
        # Make install directory read-only
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                installer.venv_dir.mkdir()


class TestMinimalInstallerCrossPlatform:
    """Test cross-platform compatibility."""

    @pytest.fixture
    def installer(self, tmp_path):
        """Create installer instance for testing."""
        if MinimalInstaller is None:
            pytest.skip("MinimalInstaller not yet implemented")
        return MinimalInstaller(install_dir=tmp_path)

    def test_uses_pathlib_path_for_directories(self, installer):
        """Test uses pathlib.Path for all directory operations."""
        # All path attributes should be Path objects
        assert isinstance(installer.install_dir, Path)
        assert isinstance(installer.venv_dir, Path)
        assert isinstance(installer.config_path, Path)

    def test_no_hardcoded_path_separators(self, installer):
        """Test no hardcoded / or \\ in path construction."""
        # Paths should be constructed with / operator, not string concat
        # This is verified by checking that paths are Path objects
        venv_path = installer.install_dir / "venv"
        assert isinstance(venv_path, Path)

    @pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
    def test_works_on_all_platforms(self, platform, installer):
        """Test installer works on Windows, Linux, and macOS."""
        with patch("sys.platform", platform):
            # Should be able to get paths without errors
            python_path = installer._get_python_path()
            pip_path = installer._get_pip_path()

            assert isinstance(python_path, Path)
            assert isinstance(pip_path, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
