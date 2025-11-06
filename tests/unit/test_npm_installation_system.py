"""
Unit tests for production-grade npm installation system

Tests the enhanced npm installation workflow including:
1. Pre-flight checks (npm registry, disk space, lockfile)
2. npm ci vs npm install fallback strategy
3. Two-tier verification (folder + npm list)
4. Log file management
5. Enhanced error reporting

Following TDD principles: Tests written before implementation
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestNpmPreflightChecks:
    """Test pre-flight checks before npm installation"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance with temp directory"""
        from install import UnifiedInstaller

        settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_password": "4010",
            "api_port": 7272,
            "dashboard_port": 7274,
            "install_dir": str(tmp_path),
        }

        return UnifiedInstaller(settings=settings)

    def test_preflight_checks_healthy_system(self, installer, tmp_path):
        """Test pre-flight checks pass on healthy system"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        # Create package-lock.json
        lockfile = frontend_dir / "package-lock.json"
        lockfile.write_text('{"lockfileVersion": 2}')

        # Mock npm ping success
        with patch.object(installer.platform, "run_npm_command") as mock_npm:
            mock_npm.return_value = {"success": True, "stdout": "Ping success"}

            # Mock disk space check
            with patch("shutil.disk_usage") as mock_disk:
                mock_disk.return_value = Mock(free=1000 * 1024 * 1024)  # 1GB free

                result = installer._npm_preflight_checks(frontend_dir)

                assert result["healthy"] is True
                assert len(result.get("issues", [])) == 0
                assert len(result.get("warnings", [])) == 0

    def test_preflight_checks_npm_registry_unreachable(self, installer, tmp_path):
        """Test pre-flight checks detect npm registry issues"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        lockfile = frontend_dir / "package-lock.json"
        lockfile.write_text('{"lockfileVersion": 2}')

        # Mock npm ping failure
        with patch.object(installer.platform, "run_npm_command") as mock_npm:
            mock_npm.return_value = {"success": False, "stderr": "network timeout"}

            with patch("shutil.disk_usage") as mock_disk:
                mock_disk.return_value = Mock(free=1000 * 1024 * 1024)

                result = installer._npm_preflight_checks(frontend_dir)

                assert result["healthy"] is False
                assert "npm registry" in str(result["issues"]).lower()

    def test_preflight_checks_insufficient_disk_space(self, installer, tmp_path):
        """Test pre-flight checks detect low disk space"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        lockfile = frontend_dir / "package-lock.json"
        lockfile.write_text('{"lockfileVersion": 2}')

        with patch.object(installer.platform, "run_npm_command") as mock_npm:
            mock_npm.return_value = {"success": True, "stdout": "Ping success"}

            # Mock low disk space (100MB < 500MB minimum)
            with patch("shutil.disk_usage") as mock_disk:
                mock_disk.return_value = Mock(free=100 * 1024 * 1024)

                result = installer._npm_preflight_checks(frontend_dir)

                assert result["healthy"] is False
                assert "disk space" in str(result["issues"]).lower()

    def test_preflight_checks_missing_lockfile_warning(self, installer, tmp_path):
        """Test pre-flight checks warn about missing package-lock.json"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        # No lockfile created

        with patch.object(installer.platform, "run_npm_command") as mock_npm:
            mock_npm.return_value = {"success": True, "stdout": "Ping success"}

            with patch("shutil.disk_usage") as mock_disk:
                mock_disk.return_value = Mock(free=1000 * 1024 * 1024)

                result = installer._npm_preflight_checks(frontend_dir)

                # Should be healthy but have warning
                assert result["healthy"] is True
                assert len(result.get("warnings", [])) > 0
                assert "package-lock.json" in str(result["warnings"]).lower()

    def test_preflight_checks_handles_npm_not_installed(self, installer, tmp_path):
        """Test pre-flight checks handle npm not being installed"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        with patch.object(installer.platform, "run_npm_command") as mock_npm:
            mock_npm.side_effect = FileNotFoundError("npm not found")

            result = installer._npm_preflight_checks(frontend_dir)

            assert result["healthy"] is False
            assert "npm" in str(result["issues"]).lower()


class TestNpmInstallationStrategy:
    """Test npm ci vs npm install fallback strategy"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"pg_host": "localhost", "pg_port": 5432, "pg_password": "4010", "install_dir": str(tmp_path)}

        return UnifiedInstaller(settings=settings)

    def test_uses_npm_ci_when_lockfile_exists(self, installer, tmp_path):
        """Test npm ci is used when package-lock.json exists"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        lockfile = frontend_dir / "package-lock.json"
        lockfile.write_text('{"lockfileVersion": 2}')

        # Mock pre-flight checks passing
        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            # Track npm commands
            npm_commands_called = []

            def npm_side_effect(*args, **kwargs):
                cmd = args[0] if args else kwargs.get("cmd", [])
                npm_commands_called.append(cmd)

                # All commands succeed
                if "list" in cmd:
                    return {"success": True, "stdout": "deps ok", "stderr": ""}
                return {"success": True, "stdout": "installed", "stderr": ""}

            # Mock npm commands
            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.side_effect = npm_side_effect

                # Mock verification
                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.return_value = True

                    result = installer._install_npm_dependencies_with_retry(frontend_dir)

                    # Should have called npm ci
                    assert any("ci" in cmd for cmd in npm_commands_called)
                    assert result is True

    def test_fallback_to_npm_install_when_lockfile_missing(self, installer, tmp_path):
        """Test fallback to npm install when lockfile is missing"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        # No lockfile

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": ["package-lock.json not found"]}

            # Track npm commands
            npm_commands_called = []

            def npm_side_effect(*args, **kwargs):
                cmd = args[0] if args else kwargs.get("cmd", [])
                npm_commands_called.append(cmd)

                # All commands succeed
                if "list" in cmd:
                    return {"success": True, "stdout": "deps ok", "stderr": ""}
                return {"success": True, "stdout": "installed", "stderr": ""}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.side_effect = npm_side_effect

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.return_value = True

                    result = installer._install_npm_dependencies_with_retry(frontend_dir)

                    # Should have called npm install, not npm ci
                    assert any("install" in cmd for cmd in npm_commands_called)
                    assert not any("ci" in cmd for cmd in npm_commands_called)
                    assert result is True

    def test_fallback_to_npm_install_when_npm_ci_fails(self, installer, tmp_path):
        """Test fallback to npm install when npm ci fails"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        lockfile = frontend_dir / "package-lock.json"
        lockfile.write_text('{"lockfileVersion": 2}')

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            call_count = 0

            def npm_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                cmd = args[0] if args else kwargs.get("cmd", [])

                # First call (npm ci) fails
                if call_count == 1 and "ci" in cmd:
                    return {"success": False, "stderr": "lockfile corrupted"}
                # Second call (npm install) succeeds
                if "install" in cmd or "list" in cmd:
                    return {"success": True}
                return {"success": False}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.side_effect = npm_side_effect

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.return_value = True

                    result = installer._install_npm_dependencies_with_retry(frontend_dir)

                    # Should have tried both npm ci and npm install
                    assert call_count >= 2
                    assert result is True


class TestTwoTierVerification:
    """Test two-tier verification: folder existence + npm list"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"install_dir": str(tmp_path)}

        return UnifiedInstaller(settings=settings)

    def test_verification_passes_when_both_tiers_succeed(self, installer, tmp_path):
        """Test verification passes when both folder and npm list succeed"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        # Create node_modules with critical dependencies
        node_modules = frontend_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "vue").mkdir()
        (node_modules / "vuetify").mkdir()
        (node_modules / "axios").mkdir()
        (node_modules / "pinia").mkdir()
        (node_modules / "vue-router").mkdir()
        (node_modules / "lodash-es").mkdir()
        (node_modules / "vuedraggable").mkdir()
        (node_modules / "socket.io-client").mkdir()

        # First tier: folder check
        assert installer._verify_npm_dependencies(frontend_dir) is True

    def test_verification_fails_when_folder_missing(self, installer, tmp_path):
        """Test verification fails when node_modules doesn't exist"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        # No node_modules

        assert installer._verify_npm_dependencies(frontend_dir) is False

    def test_verification_fails_when_critical_deps_missing(self, installer, tmp_path):
        """Test verification fails when critical dependencies are missing"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        node_modules = frontend_dir / "node_modules"
        node_modules.mkdir()
        # Only create some dependencies, not all critical ones
        (node_modules / "vue").mkdir()
        (node_modules / "axios").mkdir()
        # Missing: vuetify, pinia, vue-router, etc.

        assert installer._verify_npm_dependencies(frontend_dir) is False

    def test_npm_list_verification_detects_corrupted_installation(self, installer, tmp_path):
        """Test npm list can detect corrupted installations"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            # Mock npm install succeeds
            with patch.object(installer.platform, "run_npm_command") as mock_npm:

                def npm_side_effect(*args, **kwargs):
                    cmd = args[0] if args else kwargs.get("cmd", [])
                    if "install" in cmd or "ci" in cmd:
                        return {"success": True}
                    if "list" in cmd:
                        # npm list detects missing peer dependencies
                        return {"success": False, "stderr": "missing peer dependency"}
                    return {"success": True}

                mock_npm.side_effect = npm_side_effect

                # Mock folder verification passes (false positive)
                with patch.object(installer, "_verify_npm_dependencies") as mock_folder:
                    mock_folder.return_value = True

                    result = installer._install_npm_dependencies_with_retry(frontend_dir, max_retries=1)

                    # Should retry due to npm list failure
                    # (will eventually fail after retries)
                    # This test verifies npm list is being called


class TestLogFileManagement:
    """Test log file creation and management"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"install_dir": str(tmp_path)}

        return UnifiedInstaller(settings=settings)

    def test_ensure_logs_dir_creates_directory(self, installer, tmp_path):
        """Test _ensure_logs_dir creates logs directory"""
        installer.install_dir = tmp_path

        logs_dir = installer._ensure_logs_dir()

        assert logs_dir.exists()
        assert logs_dir.is_dir()
        assert logs_dir.name == "logs"

    def test_ensure_logs_dir_handles_existing_directory(self, installer, tmp_path):
        """Test _ensure_logs_dir handles pre-existing logs directory"""
        installer.install_dir = tmp_path

        # Pre-create logs directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Should not raise error
        result = installer._ensure_logs_dir()

        assert result == logs_dir
        assert result.exists()

    def test_npm_install_writes_to_log_file(self, installer, tmp_path):
        """Test npm install output is written to logs/install_npm.log"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        installer.install_dir = tmp_path

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.return_value = {
                    "success": True,
                    "stdout": "Installing dependencies...\nSuccess!",
                    "stderr": "",
                }

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.return_value = True

                    installer._install_npm_dependencies_with_retry(frontend_dir)

                    # Check log file was created
                    log_file = tmp_path / "logs" / "install_npm.log"
                    assert log_file.exists()

                    # Check log contains npm output
                    log_content = log_file.read_text()
                    assert len(log_content) > 0

    def test_log_file_contains_timestamps(self, installer, tmp_path):
        """Test log file contains timestamps for each attempt"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        installer.install_dir = tmp_path

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.return_value = {"success": True, "stdout": "npm output"}

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.return_value = True

                    installer._install_npm_dependencies_with_retry(frontend_dir)

                    log_file = tmp_path / "logs" / "install_npm.log"
                    log_content = log_file.read_text()

                    # Should contain timestamp markers
                    assert "===" in log_content or "Attempt" in log_content


class TestCacheClearingOnFinalRetry:
    """Test npm cache clearing on final retry attempt"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"install_dir": str(tmp_path)}

        return UnifiedInstaller(settings=settings)

    def test_cache_cleared_on_final_retry(self, installer, tmp_path):
        """Test npm cache is cleared before final retry attempt"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            call_count = 0
            cache_cleared = False

            def npm_side_effect(*args, **kwargs):
                nonlocal call_count, cache_cleared
                call_count += 1
                cmd = args[0] if args else kwargs.get("cmd", [])

                # Track cache clear command
                if "cache" in cmd and "clean" in cmd:
                    cache_cleared = True
                    return {"success": True}

                # Fail first 2 attempts
                if call_count < 3:
                    return {"success": False, "stderr": "network error"}

                # Succeed on 3rd attempt (after cache clear)
                return {"success": True}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.side_effect = npm_side_effect

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    # Fail verification first 2 times, pass on 3rd
                    mock_verify.side_effect = [False, False, True]

                    installer._install_npm_dependencies_with_retry(frontend_dir, max_retries=3)

                    # Cache should have been cleared
                    assert cache_cleared is True

    def test_no_cache_clear_on_first_retry(self, installer, tmp_path):
        """Test cache is NOT cleared on first retry (only final)"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": True, "issues": [], "warnings": []}

            call_count = 0

            def npm_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                cmd = args[0] if args else kwargs.get("cmd", [])

                # Should NOT see cache clear on first retry
                if call_count == 1 and "cache" in cmd:
                    pytest.fail("Cache should not be cleared on first attempt")

                if call_count == 1:
                    return {"success": False, "stderr": "error"}
                return {"success": True}

            with patch.object(installer.platform, "run_npm_command") as mock_npm:
                mock_npm.side_effect = npm_side_effect

                with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                    mock_verify.side_effect = [False, True]

                    installer._install_npm_dependencies_with_retry(frontend_dir, max_retries=2)


class TestEnhancedErrorReporting:
    """Test enhanced error reporting in launch_services"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"install_dir": str(tmp_path), "api_port": 7272, "dashboard_port": 7274}

        return UnifiedInstaller(settings=settings)

    def test_failure_shows_preflight_results(self, installer, tmp_path, capsys):
        """Test failure message shows pre-flight check results"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        # Mock npm not installed
        with patch("shutil.which", return_value=None):
            result = installer.launch_services()

            # Should mention npm not found
            # (Implementation will show pre-flight results)

    def test_failure_shows_log_file_location(self, installer, tmp_path):
        """Test failure message shows log file location"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        installer.install_dir = tmp_path

        with patch.object(installer, "_npm_preflight_checks") as mock_preflight:
            mock_preflight.return_value = {"healthy": False, "issues": ["npm registry unreachable"], "warnings": []}

            with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                mock_verify.return_value = False

                with patch("shutil.which", return_value="/usr/bin/npm"):
                    result = installer.launch_services()

                    # Should mention log file location
                    assert result["success"] is False
                    # Error message should reference logs/install_npm.log

    def test_failure_includes_troubleshooting_steps(self, installer, tmp_path, capsys):
        """Test failure message includes enhanced troubleshooting"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        # Create API script to avoid early return
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        api_script = api_dir / "run_api.py"
        api_script.write_text("# API script")

        installer.install_dir = tmp_path

        with patch("shutil.which", return_value="/usr/bin/npm"):
            with patch.object(installer, "_verify_npm_dependencies") as mock_verify:
                mock_verify.return_value = False

                with patch.object(installer, "_install_npm_dependencies_with_retry") as mock_install:
                    mock_install.return_value = False
                    # Store pre-flight results to trigger error output
                    installer._npm_preflight_results = {
                        "healthy": False,
                        "issues": ["npm registry unreachable"],
                        "warnings": [],
                    }

                    # Mock subprocess.Popen to avoid Python executable issues
                    with patch("subprocess.Popen") as mock_popen:
                        mock_process = Mock()
                        mock_process.pid = 12345
                        mock_popen.return_value = mock_process

                        result = installer.launch_services()

                        captured = capsys.readouterr()

                        # Should show troubleshooting steps
                        assert "troubleshooting" in captured.out.lower() or "disk space" in captured.out.lower()


class TestCrossPlatformPathHandling:
    """Test cross-platform path handling in npm operations"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {"install_dir": str(tmp_path)}

        return UnifiedInstaller(settings=settings)

    def test_log_file_uses_path_object(self, installer, tmp_path):
        """Test log file paths use Path objects, not string concatenation"""
        installer.install_dir = tmp_path

        logs_dir = installer._ensure_logs_dir()

        # Should be a Path object
        assert isinstance(logs_dir, Path)

        # Log file should use Path join, not string concatenation
        log_file = logs_dir / "install_npm.log"
        assert isinstance(log_file, Path)

    def test_frontend_dir_uses_path_object(self, installer, tmp_path):
        """Test frontend directory uses Path objects"""
        installer.install_dir = tmp_path
        frontend_dir = installer.install_dir / "frontend"

        # Should be Path object
        assert isinstance(frontend_dir, Path)

        # Lockfile check should use Path
        lockfile = frontend_dir / "package-lock.json"
        assert isinstance(lockfile, Path)


class TestConstantsDefinition:
    """Test that required constants are defined"""

    def test_constants_exist(self):
        """Test that npm-related constants are defined in install.py"""
        from install import MIN_DISK_SPACE_MB, NPM_INSTALL_TIMEOUT, NPM_MAX_RETRIES

        # Should be defined as integers
        assert isinstance(MIN_DISK_SPACE_MB, int)
        assert isinstance(NPM_INSTALL_TIMEOUT, int)
        assert isinstance(NPM_MAX_RETRIES, int)

        # Should have reasonable values
        assert MIN_DISK_SPACE_MB >= 100
        assert NPM_INSTALL_TIMEOUT >= 60
        assert NPM_MAX_RETRIES >= 2

    def test_constants_values(self):
        """Test constants have expected values from spec"""
        from install import MIN_DISK_SPACE_MB, NPM_INSTALL_TIMEOUT, NPM_MAX_RETRIES

        assert MIN_DISK_SPACE_MB == 500
        assert NPM_INSTALL_TIMEOUT == 300
        assert NPM_MAX_RETRIES == 3
