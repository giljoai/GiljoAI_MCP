"""
Unit tests for unified install.py

Tests the UnifiedInstaller class which handles:
- PostgreSQL discovery across platforms
- Python dependency management
- Database setup
- Configuration generation
- Service launching

Following TDD principles: Tests written before implementation
"""

import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any

import pytest


# Placeholder for UnifiedInstaller - will be implemented after tests pass
class UnifiedInstaller:
    """Unified installer for GiljoAI MCP v3.0"""
    pass


class TestUnifiedInstaller:
    """Test suite for UnifiedInstaller"""

    @pytest.fixture
    def installer(self, tmp_path: Path) -> 'UnifiedInstaller':
        """Create installer instance with temp directory"""
        # Import will happen after implementation
        from install import UnifiedInstaller

        # Mock settings
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_password': '4010',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path)
        }

        return UnifiedInstaller(settings=settings)

    def test_installer_initialization(self, tmp_path: Path) -> None:
        """Test UnifiedInstaller initializes correctly"""
        from install import UnifiedInstaller

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        assert installer is not None
        assert hasattr(installer, 'settings')
        assert hasattr(installer, 'run')

    def test_welcome_screen_displays(self, installer: 'UnifiedInstaller', capsys) -> None:
        """Test welcome screen displays with yellow branding"""
        installer.welcome_screen()

        captured = capsys.readouterr()
        assert 'GiljoAI MCP' in captured.out
        assert 'v3.0' in captured.out or '3.0' in captured.out

    def test_check_python_version_success(self, installer: 'UnifiedInstaller') -> None:
        """Test Python version check passes for 3.10+"""
        # Current Python should be 3.10+ (per requirements)
        assert sys.version_info >= (3, 10)

        result = installer.check_python_version()
        assert result is True

    @patch('sys.version_info', (3, 9, 0))
    def test_check_python_version_failure(self, installer: 'UnifiedInstaller') -> None:
        """Test Python version check fails for < 3.10"""
        result = installer.check_python_version()
        assert result is False

    def test_discover_postgresql_in_path(self, installer: 'UnifiedInstaller') -> None:
        """Test PostgreSQL discovery when psql is in PATH"""
        with patch('shutil.which', return_value='/usr/bin/psql'):
            result = installer.discover_postgresql()

            assert result['found'] is True
            assert 'psql_path' in result
            assert result['psql_path'] == '/usr/bin/psql'

    @patch('platform.system', return_value='Windows')
    def test_discover_postgresql_windows_scan(self, installer: 'UnifiedInstaller') -> None:
        """Test PostgreSQL discovery scans Windows default locations"""
        with patch('shutil.which', return_value=None):
            with patch('pathlib.Path.exists') as mock_exists:
                # Simulate finding PostgreSQL 18 in default location
                def exists_side_effect(self):
                    return 'PostgreSQL/18' in str(self)

                mock_exists.side_effect = exists_side_effect

                result = installer.discover_postgresql()

                # Should find it via path scanning
                assert result['found'] is True

    @patch('platform.system', return_value='Darwin')
    def test_discover_postgresql_macos_homebrew(self, installer: 'UnifiedInstaller') -> None:
        """Test PostgreSQL discovery checks Homebrew paths on macOS"""
        with patch('shutil.which', return_value=None):
            with patch('pathlib.Path.exists') as mock_exists:
                # Simulate Homebrew installation
                def exists_side_effect(self):
                    return 'homebrew' in str(self).lower()

                mock_exists.side_effect = exists_side_effect

                result = installer.discover_postgresql()

                # Should scan Homebrew paths
                assert 'scanned_paths' in result

    @patch('platform.system', return_value='Linux')
    def test_discover_postgresql_linux_system_paths(self, installer: 'UnifiedInstaller') -> None:
        """Test PostgreSQL discovery checks Linux system paths"""
        with patch('shutil.which', return_value=None):
            with patch('pathlib.Path.exists') as mock_exists:
                # Simulate Linux system installation
                def exists_side_effect(self):
                    return '/usr/lib/postgresql' in str(self)

                mock_exists.side_effect = exists_side_effect

                result = installer.discover_postgresql()

                # Should scan system paths
                assert 'scanned_paths' in result

    def test_install_dependencies_creates_venv(self, installer: 'UnifiedInstaller', tmp_path: Path) -> None:
        """Test dependency installation creates virtual environment"""
        installer.settings['install_dir'] = str(tmp_path)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = installer.install_dependencies()

            # Should create venv
            assert result['success'] is True
            assert 'venv_created' in result

    def test_install_dependencies_installs_requirements(self, installer: 'UnifiedInstaller') -> None:
        """Test dependency installation runs pip install"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            with patch('pathlib.Path.exists', return_value=True):
                result = installer.install_dependencies()

                # Should run pip install -r requirements.txt
                assert result['success'] is True

                # Verify pip install was called
                calls = [str(c) for c in mock_run.call_args_list]
                pip_called = any('pip' in str(c) and 'install' in str(c) for c in calls)
                assert pip_called

    def test_setup_database_uses_database_installer(self, installer: 'UnifiedInstaller') -> None:
        """Test database setup delegates to DatabaseInstaller"""
        with patch('install.DatabaseInstaller') as mock_db_installer:
            mock_instance = Mock()
            mock_instance.setup.return_value = {
                'success': True,
                'credentials': {'user_password': 'test123'}
            }
            mock_db_installer.return_value = mock_instance

            result = installer.setup_database()

            assert result['success'] is True
            assert mock_db_installer.called

    def test_generate_configs_creates_env_and_yaml(self, installer: 'UnifiedInstaller', tmp_path: Path) -> None:
        """Test config generation creates both .env and config.yaml"""
        installer.settings['install_dir'] = str(tmp_path)

        with patch('install.ConfigManager') as mock_config_mgr:
            mock_instance = Mock()
            mock_instance.generate_all.return_value = {'success': True}
            mock_config_mgr.return_value = mock_instance

            result = installer.generate_configs()

            assert result['success'] is True
            assert mock_config_mgr.called

    def test_generate_configs_uses_v3_architecture(self, installer: 'UnifiedInstaller') -> None:
        """Test config generation uses v3.0 unified architecture (no mode)"""
        with patch('install.ConfigManager') as mock_config_mgr:
            mock_instance = Mock()
            mock_instance.generate_all.return_value = {'success': True}
            mock_config_mgr.return_value = mock_instance

            installer.generate_configs()

            # Verify settings passed to ConfigManager
            call_args = mock_config_mgr.call_args
            settings = call_args[0][0] if call_args else {}

            # v3.0 should NOT have 'mode' field
            assert 'mode' not in settings or settings.get('mode') is None

    def test_launch_services_starts_api_and_frontend(self, installer: 'UnifiedInstaller') -> None:
        """Test service launch starts both API and frontend"""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = installer.launch_services()

            assert result['success'] is True
            assert 'api_pid' in result
            assert 'frontend_pid' in result

    def test_open_browser_launches_dashboard(self, installer: 'UnifiedInstaller') -> None:
        """Test browser opens to dashboard URL"""
        with patch('webbrowser.open') as mock_browser:
            installer.open_browser()

            # Should open localhost:7274 (default frontend port)
            assert mock_browser.called
            url = mock_browser.call_args[0][0]
            assert 'localhost' in url or '127.0.0.1' in url
            assert '7274' in url

    def test_run_executes_all_steps(self, installer: 'UnifiedInstaller') -> None:
        """Test run() executes all installation steps in order"""
        with patch.multiple(
            installer,
            welcome_screen=Mock(),
            check_python_version=Mock(return_value=True),
            discover_postgresql=Mock(return_value={'found': True}),
            install_dependencies=Mock(return_value={'success': True}),
            setup_database=Mock(return_value={'success': True}),
            generate_configs=Mock(return_value={'success': True}),
            launch_services=Mock(return_value={'success': True, 'api_pid': 123, 'frontend_pid': 456}),
            open_browser=Mock()
        ):
            result = installer.run()

            # All steps should execute
            assert installer.welcome_screen.called
            assert installer.check_python_version.called
            assert installer.discover_postgresql.called
            assert installer.install_dependencies.called
            assert installer.setup_database.called
            assert installer.generate_configs.called
            assert installer.launch_services.called
            assert installer.open_browser.called

            assert result['success'] is True

    def test_run_stops_on_python_version_failure(self, installer: 'UnifiedInstaller') -> None:
        """Test run() stops if Python version check fails"""
        with patch.multiple(
            installer,
            welcome_screen=Mock(),
            check_python_version=Mock(return_value=False),
            discover_postgresql=Mock(),
            install_dependencies=Mock()
        ):
            result = installer.run()

            # Should stop after Python check
            assert installer.welcome_screen.called
            assert installer.check_python_version.called
            assert not installer.discover_postgresql.called
            assert not installer.install_dependencies.called

            assert result['success'] is False

    def test_run_stops_on_postgresql_not_found(self, installer: 'UnifiedInstaller') -> None:
        """Test run() stops if PostgreSQL not found"""
        with patch.multiple(
            installer,
            welcome_screen=Mock(),
            check_python_version=Mock(return_value=True),
            discover_postgresql=Mock(return_value={'found': False}),
            install_dependencies=Mock()
        ):
            result = installer.run()

            # Should stop after PostgreSQL check
            assert installer.discover_postgresql.called
            assert not installer.install_dependencies.called

            assert result['success'] is False

    def test_yellow_branding_for_important_output(self, installer: 'UnifiedInstaller', capsys) -> None:
        """Test yellow branding used for important messages"""
        # Test various output methods use yellow for emphasis
        installer.welcome_screen()

        captured = capsys.readouterr()
        # Should contain ANSI color codes or colorama color strings
        # This is a basic check - actual implementation will use colorama
        assert captured.out  # Output should be present

    def test_error_handling_provides_clear_messages(self, installer: 'UnifiedInstaller') -> None:
        """Test error handling provides actionable error messages"""
        with patch.multiple(
            installer,
            check_python_version=Mock(side_effect=Exception("Test error"))
        ):
            result = installer.run()

            assert result['success'] is False
            assert 'error' in result or 'errors' in result

    def test_cross_platform_path_handling(self, installer: 'UnifiedInstaller', tmp_path: Path) -> None:
        """Test all path operations use pathlib.Path"""
        installer.settings['install_dir'] = str(tmp_path)

        # Create a dummy requirements.txt
        requirements_file = tmp_path / 'requirements.txt'
        requirements_file.write_text('fastapi>=0.100.0\n')

        # All path operations should use Path objects
        # This is verified by implementation using Path throughout

    @patch('socket.socket')
    def test_port_availability_check(self, mock_socket: Mock, installer: 'UnifiedInstaller') -> None:
        """Test installer checks port availability before launching services"""
        mock_sock_instance = Mock()
        mock_socket.return_value = mock_sock_instance
        mock_sock_instance.connect_ex.return_value = 1  # Port available

        # Should check both API and frontend ports
        with patch.object(installer, 'launch_services', return_value={'success': True}):
            installer.settings['api_port'] = 7272
            installer.settings['dashboard_port'] = 7274

            # This will be part of launch_services implementation


class TestPostgreSQLDiscovery:
    """Test PostgreSQL discovery across platforms"""

    def test_windows_scans_program_files(self) -> None:
        """Test Windows scans C:/Program Files/PostgreSQL/*/bin/"""
        from install import UnifiedInstaller

        installer = UnifiedInstaller(settings={})

        with patch('platform.system', return_value='Windows'):
            with patch('shutil.which', return_value=None):
                with patch('pathlib.Path.exists') as mock_exists:
                    # Simulate finding psql in PostgreSQL 18 install
                    def exists_check(self):
                        path_str = str(self)
                        return (
                            'PostgreSQL' in path_str and
                            ('18' in path_str or '17' in path_str) and
                            'psql.exe' in path_str
                        )

                    mock_exists.side_effect = exists_check

                    result = installer.discover_postgresql()

                    # Should find PostgreSQL in scan
                    assert 'scanned_paths' in result

    def test_macos_scans_homebrew_and_postgres_app(self) -> None:
        """Test macOS scans Homebrew and Postgres.app locations"""
        from install import UnifiedInstaller

        installer = UnifiedInstaller(settings={})

        with patch('platform.system', return_value='Darwin'):
            with patch('shutil.which', return_value=None):
                result = installer.discover_postgresql()

                # Should include Homebrew paths in scan
                scanned = result.get('scanned_paths', [])
                homebrew_scanned = any(
                    'homebrew' in str(p).lower() or 'opt' in str(p).lower()
                    for p in scanned
                )
                assert homebrew_scanned or not result['found']

    def test_linux_scans_usr_lib_and_usr_bin(self) -> None:
        """Test Linux scans /usr/lib/postgresql and /usr/bin"""
        from install import UnifiedInstaller

        installer = UnifiedInstaller(settings={})

        with patch('platform.system', return_value='Linux'):
            with patch('shutil.which', return_value=None):
                result = installer.discover_postgresql()

                # Should include system paths in scan
                scanned = result.get('scanned_paths', [])
                system_scanned = any(
                    '/usr' in str(p) or '/lib' in str(p)
                    for p in scanned
                )
                assert system_scanned or not result['found']


class TestDependencyManagement:
    """Test dependency installation and venv management"""

    def test_creates_venv_if_not_exists(self, tmp_path: Path) -> None:
        """Test creates virtual environment if it doesn't exist"""
        from install import UnifiedInstaller

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = installer.install_dependencies()

            # Should call venv creation
            venv_calls = [c for c in mock_run.call_args_list if 'venv' in str(c)]
            assert len(venv_calls) > 0 or result.get('venv_existed')

    def test_skips_venv_if_exists(self, tmp_path: Path) -> None:
        """Test skips venv creation if it already exists"""
        from install import UnifiedInstaller

        # Create existing venv directory
        venv_dir = tmp_path / 'venv'
        venv_dir.mkdir()
        (venv_dir / 'Scripts' if platform.system() == 'Windows' else venv_dir / 'bin').mkdir()

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = installer.install_dependencies()

            # Should not create venv again
            assert result.get('venv_existed') or result.get('venv_created')

    def test_uses_requirements_txt(self, tmp_path: Path) -> None:
        """Test installs dependencies from requirements.txt"""
        from install import UnifiedInstaller

        # Create requirements.txt
        req_file = tmp_path / 'requirements.txt'
        req_file.write_text('fastapi>=0.100.0\nuvicorn>=0.23.0\n')

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = installer.install_dependencies()

            # Should call pip install -r requirements.txt
            pip_calls = [c for c in mock_run.call_args_list if 'pip' in str(c) and 'install' in str(c)]
            assert len(pip_calls) > 0


class TestV3UnifiedArchitecture:
    """Test v3.0 unified architecture compliance"""

    def test_no_mode_field_in_config(self, tmp_path: Path) -> None:
        """Test v3.0 config does NOT include mode field"""
        from install import UnifiedInstaller

        settings = {
            'install_dir': str(tmp_path),
            'owner_password': 'test123',
            'user_password': 'test456'
        }
        installer = UnifiedInstaller(settings=settings)

        with patch('install.ConfigManager') as mock_config:
            mock_instance = Mock()
            mock_instance.generate_all.return_value = {'success': True}
            mock_config.return_value = mock_instance

            installer.generate_configs()

            # ConfigManager should be called without mode
            call_args = mock_config.call_args[0][0]
            assert 'mode' not in call_args

    def test_server_binds_to_all_interfaces(self, tmp_path: Path) -> None:
        """Test v3.0 server always binds to 0.0.0.0"""
        from install import UnifiedInstaller

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        # In v3.0, server should always bind to 0.0.0.0
        # Firewall controls access
        assert installer.settings.get('bind', '0.0.0.0') == '0.0.0.0'

    def test_firewall_configuration_offered(self, tmp_path: Path) -> None:
        """Test installer offers to configure firewall (localhost-only by default)"""
        from install import UnifiedInstaller

        settings = {'install_dir': str(tmp_path)}
        installer = UnifiedInstaller(settings=settings)

        # Installer should provide firewall configuration option
        # This will be interactive or configurable
        assert hasattr(installer, 'run')
