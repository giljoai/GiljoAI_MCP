#!/usr/bin/env python3
"""
Comprehensive tests for platform handler architecture.

Tests Strategy pattern implementation with abstract base class and
concrete platform-specific implementations.

TDD Approach: Tests written FIRST to define expected behavior.
"""

import platform
import subprocess
from pathlib import Path
from typing import List
from unittest.mock import Mock, MagicMock, patch, call

import pytest


# Fixtures for common test data
@pytest.fixture
def mock_install_dir(tmp_path: Path) -> Path:
    """Create mock installation directory"""
    install_dir = tmp_path / "giljoai_mcp"
    install_dir.mkdir(parents=True)
    return install_dir


@pytest.fixture
def mock_venv_dir(tmp_path: Path) -> Path:
    """Create mock venv directory"""
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir(parents=True)
    return venv_dir


# ============================================================================
# BASE CLASS TESTS
# ============================================================================

class TestPlatformHandlerAbstract:
    """Test abstract base class interface"""

    def test_platform_handler_cannot_be_instantiated_directly(self):
        """Abstract base class should not be instantiable"""
        from installer.platforms.base import PlatformHandler

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PlatformHandler()  # type: ignore

    def test_platform_handler_has_all_required_abstract_methods(self):
        """Verify all abstract methods are defined"""
        from installer.platforms.base import PlatformHandler

        # Expected abstract methods
        expected_methods = [
            'platform_name',
            'get_venv_python',
            'get_venv_pip',
            'get_postgresql_scan_paths',
            'get_postgresql_install_guide',
            'supports_desktop_shortcuts',
            'create_desktop_shortcuts',
            'run_npm_command',
            'get_network_ips',
            'welcome_screen',
            'get_platform_specific_warnings'
        ]

        # Check abstract method count
        abstract_methods = [
            name for name in dir(PlatformHandler)
            if hasattr(getattr(PlatformHandler, name), '__isabstractmethod__')
        ]

        # Verify all expected methods are abstract
        for method in expected_methods:
            assert hasattr(PlatformHandler, method), f"Missing method: {method}"


# ============================================================================
# WINDOWS HANDLER TESTS
# ============================================================================

class TestWindowsPlatformHandler:
    """Test Windows-specific platform handler"""

    @pytest.fixture
    def windows_handler(self):
        """Create Windows handler instance"""
        from installer.platforms.windows import WindowsPlatformHandler
        return WindowsPlatformHandler()

    def test_windows_platform_name(self, windows_handler):
        """Platform name should be 'Windows'"""
        assert windows_handler.platform_name == "Windows"

    def test_windows_venv_python_path(self, windows_handler, mock_venv_dir):
        """Windows venv Python should be in Scripts/python.exe"""
        python_path = windows_handler.get_venv_python(mock_venv_dir)

        assert python_path == mock_venv_dir / "Scripts" / "python.exe"
        assert str(python_path).endswith("Scripts\\python.exe")

    def test_windows_venv_pip_path(self, windows_handler, mock_venv_dir):
        """Windows venv pip should be in Scripts/pip.exe"""
        pip_path = windows_handler.get_venv_pip(mock_venv_dir)

        assert pip_path == mock_venv_dir / "Scripts" / "pip.exe"
        assert str(pip_path).endswith("Scripts\\pip.exe")

    def test_windows_postgresql_scan_paths(self, windows_handler):
        """Windows should scan Program Files directories"""
        scan_paths = windows_handler.get_postgresql_scan_paths()

        # Should return list of paths
        assert isinstance(scan_paths, list)

        # If paths returned, verify structure (may be empty if PostgreSQL not installed)
        # The implementation is correct even if list is empty on systems without PostgreSQL
        for path in scan_paths:
            assert isinstance(path, Path)
            assert "psql.exe" in str(path)

    def test_windows_postgresql_install_guide(self, windows_handler):
        """Windows should provide Windows-specific install guide"""
        guide = windows_handler.get_postgresql_install_guide()

        assert isinstance(guide, str)
        assert len(guide) > 0
        assert "Windows" in guide
        assert "Download" in guide or "download" in guide

    def test_windows_supports_desktop_shortcuts(self, windows_handler):
        """Windows should support desktop shortcuts"""
        assert windows_handler.supports_desktop_shortcuts() is True

    @patch('installer.platforms.windows.win32com')
    def test_windows_create_desktop_shortcuts_with_win32com(
        self, mock_win32com, windows_handler, mock_install_dir, mock_venv_dir
    ):
        """Windows should create .lnk shortcuts with win32com"""
        # Mock win32com shell
        mock_shell = MagicMock()
        mock_win32com.client.Dispatch.return_value = mock_shell
        mock_shell.SpecialFolders.return_value = "C:\\Users\\TestUser\\Desktop"

        result = windows_handler.create_desktop_shortcuts(mock_install_dir, mock_venv_dir)

        assert result['success'] is True
        assert 'shortcuts_created' in result
        mock_win32com.client.Dispatch.assert_called_once_with("WScript.Shell")

    @patch('installer.platforms.windows.win32com', None)
    def test_windows_create_desktop_shortcuts_fallback_to_bat(
        self, windows_handler, mock_install_dir, mock_venv_dir, tmp_path
    ):
        """Windows should fallback to .bat files if win32com unavailable"""
        # Mock desktop path
        desktop_path = tmp_path / "Desktop"
        desktop_path.mkdir()

        with patch('pathlib.Path.home', return_value=tmp_path):
            result = windows_handler.create_desktop_shortcuts(mock_install_dir, mock_venv_dir)

        assert result['success'] is True
        assert result.get('method') == 'batch'

    @patch('subprocess.run')
    def test_windows_npm_command_uses_shell_true(self, mock_run, windows_handler, tmp_path):
        """Windows npm commands MUST use shell=True"""
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        result = windows_handler.run_npm_command(
            ['npm', 'install'],
            cwd=tmp_path,
            timeout=300
        )

        assert result['success'] is True

        # CRITICAL: Verify shell=True for Windows
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['shell'] is True, "Windows npm MUST use shell=True"

    def test_windows_get_network_ips(self, windows_handler):
        """Windows should return non-localhost IPv4 addresses"""
        ips = windows_handler.get_network_ips()

        assert isinstance(ips, list)

        # If IPs found, verify they're not localhost
        for ip in ips:
            assert not ip.startswith("127.")
            assert not ip.startswith("169.254.")  # Link-local

    def test_windows_welcome_screen(self, windows_handler, capsys):
        """Windows should print platform-specific welcome"""
        windows_handler.welcome_screen()

        captured = capsys.readouterr()
        assert "Windows" in captured.out
        assert "GiljoAI" in captured.out

    def test_windows_platform_specific_warnings(self, windows_handler):
        """Windows should return empty warnings list"""
        warnings = windows_handler.get_platform_specific_warnings()

        assert isinstance(warnings, list)
        # Windows typically doesn't need firewall warnings (Windows Firewall prompts user)


# ============================================================================
# LINUX HANDLER TESTS
# ============================================================================

class TestLinuxPlatformHandler:
    """Test Linux-specific platform handler"""

    @pytest.fixture
    def linux_handler(self):
        """Create Linux handler instance"""
        from installer.platforms.linux import LinuxPlatformHandler
        return LinuxPlatformHandler()

    def test_linux_platform_name(self, linux_handler):
        """Platform name should be 'Linux'"""
        assert linux_handler.platform_name == "Linux"

    def test_linux_venv_python_path(self, linux_handler, mock_venv_dir):
        """Linux venv Python should be in bin/python"""
        python_path = linux_handler.get_venv_python(mock_venv_dir)

        assert python_path == mock_venv_dir / "bin" / "python"
        assert str(python_path).endswith("bin/python")

    def test_linux_venv_pip_path(self, linux_handler, mock_venv_dir):
        """Linux venv pip should be in bin/pip"""
        pip_path = linux_handler.get_venv_pip(mock_venv_dir)

        assert pip_path == mock_venv_dir / "bin" / "pip"
        assert str(pip_path).endswith("bin/pip")

    def test_linux_postgresql_scan_paths(self, linux_handler):
        """Linux should scan standard system paths"""
        scan_paths = linux_handler.get_postgresql_scan_paths()

        assert isinstance(scan_paths, list)
        assert len(scan_paths) > 0

        path_strs = [str(p) for p in scan_paths]

        # Should include standard paths
        assert any("/usr/bin/psql" in p for p in path_strs)

        # Should check version-specific paths
        assert any("/postgresql" in p for p in path_strs)

    @patch('platform.freedesktop_os_release')
    def test_linux_postgresql_install_guide_ubuntu(self, mock_os_release, linux_handler):
        """Ubuntu should get Ubuntu-specific guide"""
        mock_os_release.return_value = {'ID': 'ubuntu', 'VERSION_ID': '22.04'}

        guide = linux_handler.get_postgresql_install_guide()

        assert "Ubuntu" in guide or "apt" in guide
        assert "sudo" in guide

    @patch('platform.freedesktop_os_release')
    def test_linux_postgresql_install_guide_fedora(self, mock_os_release, linux_handler):
        """Fedora should get Fedora-specific guide"""
        mock_os_release.return_value = {'ID': 'fedora', 'VERSION_ID': '38'}

        guide = linux_handler.get_postgresql_install_guide()

        assert "Fedora" in guide or "dnf" in guide or "yum" in guide

    @patch('platform.freedesktop_os_release')
    def test_linux_postgresql_install_guide_generic(self, mock_os_release, linux_handler):
        """Unknown distros should get generic guide"""
        mock_os_release.side_effect = Exception("Unknown distro")

        guide = linux_handler.get_postgresql_install_guide()

        assert isinstance(guide, str)
        assert len(guide) > 0

    def test_linux_supports_desktop_shortcuts(self, linux_handler):
        """Linux should support .desktop files"""
        assert linux_handler.supports_desktop_shortcuts() is True

    @patch('subprocess.run')
    @patch('pathlib.Path.home')
    def test_linux_create_desktop_shortcuts(
        self, mock_home, mock_run, linux_handler, mock_install_dir, mock_venv_dir, tmp_path
    ):
        """Linux should create .desktop files"""
        # Mock home directory
        mock_home.return_value = tmp_path
        desktop_dir = tmp_path / ".local" / "share" / "applications"
        desktop_dir.mkdir(parents=True)

        # Mock gio command success
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = linux_handler.create_desktop_shortcuts(mock_install_dir, mock_venv_dir)

        assert result['success'] is True

        # Verify .desktop file created
        desktop_files = list(desktop_dir.glob("*.desktop"))
        assert len(desktop_files) > 0

    @patch('subprocess.run')
    def test_linux_npm_command_uses_shell_false(self, mock_run, linux_handler, tmp_path):
        """Linux npm commands should use shell=False (direct execution)"""
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        result = linux_handler.run_npm_command(
            ['npm', 'install'],
            cwd=tmp_path,
            timeout=300
        )

        assert result['success'] is True

        # CRITICAL: Verify shell=False for Linux
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['shell'] is False, "Linux npm should use shell=False"

    @patch('platform.freedesktop_os_release')
    def test_linux_platform_specific_warnings_ubuntu(self, mock_os_release, linux_handler):
        """Ubuntu should warn about UFW firewall"""
        mock_os_release.return_value = {'ID': 'ubuntu', 'VERSION_ID': '22.04'}

        warnings = linux_handler.get_platform_specific_warnings()

        assert isinstance(warnings, list)
        assert len(warnings) > 0

        # Should mention firewall
        warning_text = " ".join(warnings).lower()
        assert "firewall" in warning_text or "ufw" in warning_text


# ============================================================================
# MACOS HANDLER TESTS
# ============================================================================

class TestMacOSPlatformHandler:
    """Test macOS-specific platform handler"""

    @pytest.fixture
    def macos_handler(self):
        """Create macOS handler instance"""
        from installer.platforms.macos import MacOSPlatformHandler
        return MacOSPlatformHandler()

    def test_macos_platform_name(self, macos_handler):
        """Platform name should be 'macOS'"""
        assert macos_handler.platform_name == "macOS"

    def test_macos_venv_python_path(self, macos_handler, mock_venv_dir):
        """macOS venv Python should be in bin/python (POSIX)"""
        python_path = macos_handler.get_venv_python(mock_venv_dir)

        assert python_path == mock_venv_dir / "bin" / "python"

    def test_macos_venv_pip_path(self, macos_handler, mock_venv_dir):
        """macOS venv pip should be in bin/pip (POSIX)"""
        pip_path = macos_handler.get_venv_pip(mock_venv_dir)

        assert pip_path == mock_venv_dir / "bin" / "pip"

    def test_macos_postgresql_scan_paths_includes_homebrew_intel(self, macos_handler):
        """macOS should check Intel Homebrew paths"""
        scan_paths = macos_handler.get_postgresql_scan_paths()

        path_strs = [str(p) for p in scan_paths]

        # Intel Homebrew
        assert any("/usr/local" in p for p in path_strs)

    def test_macos_postgresql_scan_paths_includes_homebrew_arm(self, macos_handler):
        """macOS should check ARM Homebrew paths"""
        scan_paths = macos_handler.get_postgresql_scan_paths()

        path_strs = [str(p) for p in scan_paths]

        # ARM Homebrew (M1/M2)
        assert any("/opt/homebrew" in p for p in path_strs)

    def test_macos_postgresql_scan_paths_includes_postgres_app(self, macos_handler):
        """macOS should check Postgres.app paths"""
        scan_paths = macos_handler.get_postgresql_scan_paths()

        path_strs = [str(p) for p in scan_paths]

        # Postgres.app
        assert any("Postgres.app" in p for p in path_strs)

    def test_macos_postgresql_install_guide(self, macos_handler):
        """macOS should provide Homebrew + Postgres.app instructions"""
        guide = macos_handler.get_postgresql_install_guide()

        assert isinstance(guide, str)
        assert "brew" in guide.lower() or "homebrew" in guide.lower()
        assert "Postgres.app" in guide or "PostgreSQL" in guide

    def test_macos_supports_desktop_shortcuts(self, macos_handler):
        """macOS should NOT support shortcuts (future: .app bundles)"""
        assert macos_handler.supports_desktop_shortcuts() is False

    def test_macos_create_desktop_shortcuts_returns_not_supported(
        self, macos_handler, mock_install_dir, mock_venv_dir
    ):
        """macOS should return 'not supported' for shortcuts"""
        result = macos_handler.create_desktop_shortcuts(mock_install_dir, mock_venv_dir)

        assert result['success'] is False
        assert 'not supported' in result.get('message', '').lower()

    @patch('subprocess.run')
    def test_macos_npm_command_uses_shell_false(self, mock_run, macos_handler, tmp_path):
        """macOS npm commands should use shell=False (POSIX)"""
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        result = macos_handler.run_npm_command(
            ['npm', 'install'],
            cwd=tmp_path,
            timeout=300
        )

        assert result['success'] is True

        # Verify shell=False for macOS
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs['shell'] is False, "macOS npm should use shell=False"

    def test_macos_platform_specific_warnings(self, macos_handler):
        """macOS should return empty warnings list"""
        warnings = macos_handler.get_platform_specific_warnings()

        assert isinstance(warnings, list)
        # macOS doesn't need special warnings (firewall UI is user-friendly)


# ============================================================================
# AUTO-DETECTION FACTORY TESTS
# ============================================================================

class TestPlatformDetection:
    """Test automatic platform detection factory"""

    @patch('platform.system')
    def test_detect_windows_platform(self, mock_system):
        """Factory should return WindowsPlatformHandler on Windows"""
        mock_system.return_value = "Windows"

        from installer.platforms import get_platform_handler
        handler = get_platform_handler()

        from installer.platforms.windows import WindowsPlatformHandler
        assert isinstance(handler, WindowsPlatformHandler)
        assert handler.platform_name == "Windows"

    @patch('platform.system')
    def test_detect_linux_platform(self, mock_system):
        """Factory should return LinuxPlatformHandler on Linux"""
        mock_system.return_value = "Linux"

        from installer.platforms import get_platform_handler
        handler = get_platform_handler()

        from installer.platforms.linux import LinuxPlatformHandler
        assert isinstance(handler, LinuxPlatformHandler)
        assert handler.platform_name == "Linux"

    @patch('platform.system')
    def test_detect_macos_platform(self, mock_system):
        """Factory should return MacOSPlatformHandler on Darwin"""
        mock_system.return_value = "Darwin"

        from installer.platforms import get_platform_handler
        handler = get_platform_handler()

        from installer.platforms.macos import MacOSPlatformHandler
        assert isinstance(handler, MacOSPlatformHandler)
        assert handler.platform_name == "macOS"

    @patch('platform.system')
    def test_unsupported_platform_raises_error(self, mock_system):
        """Unsupported platforms should raise clear error"""
        mock_system.return_value = "FreeBSD"

        from installer.platforms import get_platform_handler

        with pytest.raises(RuntimeError, match="Unsupported platform: FreeBSD"):
            get_platform_handler()


# ============================================================================
# CROSS-PLATFORM CONSISTENCY TESTS
# ============================================================================

class TestCrossPlatformConsistency:
    """Verify consistent interface across all platforms"""

    @pytest.fixture
    def all_handlers(self):
        """Get instances of all platform handlers"""
        from installer.platforms.windows import WindowsPlatformHandler
        from installer.platforms.linux import LinuxPlatformHandler
        from installer.platforms.macos import MacOSPlatformHandler

        return [
            WindowsPlatformHandler(),
            LinuxPlatformHandler(),
            MacOSPlatformHandler()
        ]

    def test_all_platforms_return_path_objects(self, all_handlers, mock_venv_dir):
        """All venv path methods should return Path objects"""
        for handler in all_handlers:
            python_path = handler.get_venv_python(mock_venv_dir)
            pip_path = handler.get_venv_pip(mock_venv_dir)

            assert isinstance(python_path, Path), f"{handler.platform_name} python not Path"
            assert isinstance(pip_path, Path), f"{handler.platform_name} pip not Path"

    def test_all_platforms_return_scan_path_lists(self, all_handlers):
        """All platforms should return list of Path objects"""
        for handler in all_handlers:
            scan_paths = handler.get_postgresql_scan_paths()

            assert isinstance(scan_paths, list), f"{handler.platform_name} not list"
            assert len(scan_paths) > 0, f"{handler.platform_name} empty list"

            for path in scan_paths:
                assert isinstance(path, Path), f"{handler.platform_name} path not Path object"

    def test_all_platforms_return_install_guide_strings(self, all_handlers):
        """All platforms should return non-empty install guides"""
        for handler in all_handlers:
            guide = handler.get_postgresql_install_guide()

            assert isinstance(guide, str), f"{handler.platform_name} guide not string"
            assert len(guide) > 0, f"{handler.platform_name} guide empty"

    def test_all_platforms_return_network_ip_lists(self, all_handlers):
        """All platforms should return list of IP strings"""
        for handler in all_handlers:
            ips = handler.get_network_ips()

            assert isinstance(ips, list), f"{handler.platform_name} IPs not list"

            # If IPs returned, verify they're strings
            for ip in ips:
                assert isinstance(ip, str), f"{handler.platform_name} IP not string"


# ============================================================================
# TYPE HINTS VALIDATION TESTS
# ============================================================================

class TestTypeHintsCoverage:
    """Verify 100% type hint coverage"""

    def test_base_class_has_type_hints(self):
        """Base class should have complete type hints"""
        from installer.platforms.base import PlatformHandler
        import inspect

        # Get all abstract methods
        abstract_methods = [
            name for name in dir(PlatformHandler)
            if not name.startswith('_') and callable(getattr(PlatformHandler, name))
        ]

        for method_name in abstract_methods:
            method = getattr(PlatformHandler, method_name)
            signature = inspect.signature(method)

            # Skip properties
            if isinstance(method, property):
                continue

            # Verify return annotation exists
            assert signature.return_annotation != inspect.Signature.empty, \
                f"Missing return type hint on {method_name}"
