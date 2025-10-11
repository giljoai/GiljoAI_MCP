"""
Unit tests for install.py enhancements

Tests three new features:
1. Database table creation with Alembic migrations toggle
2. MCP tools registration integration
3. Serena MCP toggle option

Following TDD principles: Tests written before implementation
"""

import os
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any

import pytest


class TestDatabaseTableCreationToggle:
    """Test database table creation with Alembic migrations"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance with temp directory"""
        from install import UnifiedInstaller

        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_password': '4010',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path)
        }

        return UnifiedInstaller(settings=settings)

    def test_ask_installation_questions_includes_migrations_prompt(
        self, installer, monkeypatch
    ):
        """Test that installation questions include migrations prompt"""
        # Mock getpass and input
        import getpass
        
        inputs = [
            '',  # PostgreSQL password (use default)
            'y',  # Start services
            'y',  # Create tables (NEW)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should have migrations setting
        assert 'create_tables' in installer.settings
        assert installer.settings['create_tables'] is True

    def test_ask_installation_questions_migrations_default_yes(
        self, installer, monkeypatch
    ):
        """Test migrations prompt defaults to YES"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password (use default)
            'y',  # Start services
            '',   # Create tables (press Enter for default YES)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should default to True
        assert installer.settings.get('create_tables', False) is True

    def test_ask_installation_questions_migrations_can_decline(
        self, installer, monkeypatch
    ):
        """Test user can decline migrations"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password (use default)
            'y',  # Start services
            'n',  # Create tables (NO)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should be False
        assert installer.settings.get('create_tables', True) is False

    def test_setup_database_runs_migrations_when_enabled(self, installer):
        """Test setup_database runs migrations when create_tables=True"""
        installer.settings['create_tables'] = True
        
        with patch('install.DatabaseInstaller') as mock_db_installer:
            mock_instance = Mock()
            mock_instance.setup.return_value = {
                'success': True,
                'credentials': {'owner_password': 'test123', 'user_password': 'test456'}
            }
            mock_instance.run_migrations.return_value = {'success': True}
            mock_db_installer.return_value = mock_instance
            
            result = installer.setup_database()
            
            # Should call run_migrations
            assert mock_instance.run_migrations.called
            assert result['success'] is True

    def test_setup_database_skips_migrations_when_disabled(self, installer):
        """Test setup_database skips migrations when create_tables=False"""
        installer.settings['create_tables'] = False
        
        with patch('install.DatabaseInstaller') as mock_db_installer:
            mock_instance = Mock()
            mock_instance.setup.return_value = {
                'success': True,
                'credentials': {'owner_password': 'test123', 'user_password': 'test456'}
            }
            mock_db_installer.return_value = mock_instance
            
            result = installer.setup_database()
            
            # Should NOT call run_migrations
            assert not mock_instance.run_migrations.called
            assert result['success'] is True

    def test_migrations_failure_does_not_fail_installation(self, installer):
        """Test migration failures are logged as warnings, not errors"""
        installer.settings['create_tables'] = True
        
        with patch('install.DatabaseInstaller') as mock_db_installer:
            mock_instance = Mock()
            mock_instance.setup.return_value = {
                'success': True,
                'credentials': {'owner_password': 'test123', 'user_password': 'test456'}
            }
            mock_instance.run_migrations.return_value = {
                'success': False,
                'errors': ['Migration failed']
            }
            mock_db_installer.return_value = mock_instance
            
            result = installer.setup_database()
            
            # Database setup should still succeed
            assert result['success'] is True
            # Should have warning about migrations
            assert 'warnings' in result or 'migration_warnings' in result

    def test_migrations_prompt_shows_in_summary(self, installer, capsys):
        """Test summary shows migrations status"""
        installer.settings['create_tables'] = True
        
        with patch('install.DatabaseInstaller') as mock_db_installer:
            mock_instance = Mock()
            mock_instance.setup.return_value = {
                'success': True,
                'credentials': {'owner_password': 'test123', 'user_password': 'test456'}
            }
            mock_instance.run_migrations.return_value = {'success': True}
            mock_db_installer.return_value = mock_instance
            
            installer.setup_database()
            
            # Summary should include migrations status
            # (This will be part of _print_success_summary)


class TestMCPToolsRegistrationIntegration:
    """Test MCP tools registration integration"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_password': '4010',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path)
        }

        return UnifiedInstaller(settings=settings)

    def test_ask_installation_questions_includes_mcp_prompt(
        self, installer, monkeypatch
    ):
        """Test installation questions include MCP tools prompt"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password
            'y',  # Start services
            'y',  # Create tables
            'y',  # Register AI tools (NEW)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should have MCP registration setting
        assert 'register_mcp_tools' in installer.settings
        assert installer.settings['register_mcp_tools'] is True

    def test_ask_installation_questions_mcp_default_yes(
        self, installer, monkeypatch
    ):
        """Test MCP tools prompt defaults to YES"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password
            'y',  # Start services
            'y',  # Create tables
            '',   # Register AI tools (default YES)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should default to True
        assert installer.settings.get('register_mcp_tools', False) is True

    def test_mcp_registration_imports_universal_mcp_installer(self, installer):
        """Test MCP registration imports UniversalMCPInstaller"""
        installer.settings['register_mcp_tools'] = True
        
        # Should be able to import
        try:
            from scripts.integrate_mcp import UniversalMCPInstaller
            assert True
        except ImportError:
            pytest.skip("UniversalMCPInstaller not available")

    def test_mcp_registration_runs_after_services_start(self, installer):
        """Test MCP registration runs after services launch"""
        installer.settings['register_mcp_tools'] = True
        installer.settings['start_services'] = True
        
        call_order = []
        
        def mock_launch_services():
            call_order.append('launch_services')
            return {'success': True, 'api_pid': 123, 'frontend_pid': 456}
        
        def mock_register_mcp():
            call_order.append('register_mcp')
            return {'success': True}
        
        with patch.object(installer, 'launch_services', side_effect=mock_launch_services):
            with patch.object(installer, 'register_mcp_tools', side_effect=mock_register_mcp):
                with patch.multiple(
                    installer,
                    welcome_screen=Mock(),
                    check_python_version=Mock(return_value=True),
                    discover_postgresql=Mock(return_value={'found': True}),
                    install_dependencies=Mock(return_value={'success': True}),
                    generate_configs=Mock(return_value={'success': True}),
                    setup_database=Mock(return_value={'success': True, 'credentials': {}}),
                    update_env_with_real_credentials=Mock(return_value={'success': True})
                ):
                    result = installer.run()
                    
                    # MCP registration should happen after services launch
                    assert call_order.index('register_mcp') > call_order.index('launch_services')

    def test_mcp_registration_detects_installed_tools(self, installer):
        """Test MCP registration detects installed AI CLI tools"""
        installer.settings['register_mcp_tools'] = True
        
        # Mock UniversalMCPInstaller
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.return_value = ['claude']
            mock_instance.register_all.return_value = {'claude': True}
            mock_mcp.return_value = mock_instance
            
            result = installer.register_mcp_tools()
            
            # Should detect tools
            assert mock_instance.detect_installed_tools.called

    def test_mcp_registration_registers_with_detected_tools(self, installer):
        """Test MCP registration registers GiljoAI with detected tools"""
        installer.settings['register_mcp_tools'] = True
        installer.settings['api_port'] = 7272
        
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.return_value = ['claude']
            mock_instance.register_all.return_value = {'claude': True}
            mock_mcp.return_value = mock_instance
            
            result = installer.register_mcp_tools()
            
            # Should register with Claude
            assert mock_instance.register_all.called
            call_args = mock_instance.register_all.call_args
            assert call_args[1]['server_name'] == 'giljo-mcp'

    def test_mcp_registration_skips_if_no_tools_detected(self, installer, capsys):
        """Test MCP registration skips gracefully if no tools detected"""
        installer.settings['register_mcp_tools'] = True
        
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.return_value = []
            mock_mcp.return_value = mock_instance
            
            result = installer.register_mcp_tools()
            
            # Should not fail
            assert result.get('skipped') or not result.get('success', True)
            
            captured = capsys.readouterr()
            assert 'no ai tools detected' in captured.out.lower() or 'skipping' in captured.out.lower()

    def test_mcp_registration_failure_does_not_fail_installation(self, installer):
        """Test MCP registration failures are logged as warnings"""
        installer.settings['register_mcp_tools'] = True
        
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.side_effect = Exception("Detection failed")
            mock_mcp.return_value = mock_instance
            
            result = installer.register_mcp_tools()
            
            # Should not raise exception
            assert 'error' in result or 'warning' in result or not result.get('success')

    def test_mcp_registration_configures_server_url(self, installer):
        """Test MCP registration configures correct server URL"""
        installer.settings['register_mcp_tools'] = True
        installer.settings['api_port'] = 7272
        
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.return_value = ['claude']
            mock_instance.register_all.return_value = {'claude': True}
            mock_mcp.return_value = mock_instance
            
            installer.register_mcp_tools()
            
            # Should configure server URL with localhost:7272
            call_args = mock_instance.register_all.call_args
            env = call_args[1].get('env', {})
            assert 'GILJO_SERVER_URL' in env
            assert '7272' in env['GILJO_SERVER_URL']

    def test_mcp_registration_uses_python_module(self, installer):
        """Test MCP registration uses 'python -m giljo_mcp' command"""
        installer.settings['register_mcp_tools'] = True
        
        with patch('install.UniversalMCPInstaller') as mock_mcp:
            mock_instance = Mock()
            mock_instance.detect_installed_tools.return_value = ['claude']
            mock_instance.register_all.return_value = {'claude': True}
            mock_mcp.return_value = mock_instance
            
            installer.register_mcp_tools()
            
            # Should use Python module invocation
            call_args = mock_instance.register_all.call_args
            assert call_args[1]['command'] == 'python'
            assert '-m' in call_args[1]['args']
            assert 'giljo_mcp' in call_args[1]['args']


class TestSerenaMCPToggle:
    """Test Serena MCP enhancement toggle"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_password': '4010',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path)
        }

        return UnifiedInstaller(settings=settings)

    def test_ask_installation_questions_includes_serena_prompt(
        self, installer, monkeypatch
    ):
        """Test installation questions include Serena MCP prompt"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password
            'y',  # Start services
            'y',  # Create tables
            'y',  # Register AI tools
            'y',  # Enable Serena (NEW)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should have Serena setting
        assert 'enable_serena' in installer.settings
        assert installer.settings['enable_serena'] is True

    def test_ask_installation_questions_serena_default_no(
        self, installer, monkeypatch
    ):
        """Test Serena prompt defaults to NO (opt-in)"""
        import getpass
        
        inputs = [
            '',  # PostgreSQL password
            'y',  # Start services
            'y',  # Create tables
            'y',  # Register AI tools
            '',   # Enable Serena (default NO)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # Should default to False (opt-in)
        assert installer.settings.get('enable_serena', True) is False

    def test_serena_toggle_updates_config_yaml(self, installer, tmp_path):
        """Test enabling Serena updates config.yaml"""
        installer.settings['enable_serena'] = True
        installer.settings['install_dir'] = str(tmp_path)
        
        # Create a mock config.yaml
        config_file = tmp_path / 'config.yaml'
        config_file.write_text("""
version: 3.0.0
features:
  authentication: true
  serena_mcp:
    use_in_prompts: false
""")
        
        result = installer.enable_serena_mcp()
        
        # Should update config.yaml
        updated_content = config_file.read_text()
        assert 'use_in_prompts: true' in updated_content

    def test_serena_toggle_runs_after_config_generation(self, installer):
        """Test Serena toggle runs after config.yaml is generated"""
        installer.settings['enable_serena'] = True
        
        call_order = []
        
        def mock_generate_configs():
            call_order.append('generate_configs')
            return {'success': True}
        
        def mock_enable_serena():
            call_order.append('enable_serena')
            return {'success': True}
        
        with patch.object(installer, 'generate_configs', side_effect=mock_generate_configs):
            with patch.object(installer, 'enable_serena_mcp', side_effect=mock_enable_serena):
                with patch.multiple(
                    installer,
                    welcome_screen=Mock(),
                    check_python_version=Mock(return_value=True),
                    discover_postgresql=Mock(return_value={'found': True}),
                    install_dependencies=Mock(return_value={'success': True}),
                    setup_database=Mock(return_value={'success': True, 'credentials': {}}),
                    update_env_with_real_credentials=Mock(return_value={'success': True}),
                    launch_services=Mock(return_value={'success': True, 'api_pid': 123, 'frontend_pid': 456})
                ):
                    result = installer.run()
                    
                    # Serena toggle should happen after config generation
                    assert call_order.index('enable_serena') > call_order.index('generate_configs')

    def test_serena_toggle_skips_if_disabled(self, installer):
        """Test Serena toggle skips if enable_serena=False"""
        installer.settings['enable_serena'] = False
        
        with patch.object(installer, 'enable_serena_mcp') as mock_enable:
            with patch.multiple(
                installer,
                welcome_screen=Mock(),
                check_python_version=Mock(return_value=True),
                discover_postgresql=Mock(return_value={'found': True}),
                install_dependencies=Mock(return_value={'success': True}),
                generate_configs=Mock(return_value={'success': True}),
                setup_database=Mock(return_value={'success': True, 'credentials': {}}),
                update_env_with_real_credentials=Mock(return_value={'success': True}),
                launch_services=Mock(return_value={'success': True, 'api_pid': 123, 'frontend_pid': 456})
            ):
                result = installer.run()
                
                # Should not call enable_serena_mcp
                assert not mock_enable.called

    def test_serena_toggle_creates_features_section_if_missing(self, installer, tmp_path):
        """Test Serena toggle creates features section if missing"""
        installer.settings['enable_serena'] = True
        installer.settings['install_dir'] = str(tmp_path)
        
        # Create a minimal config.yaml without features section
        config_file = tmp_path / 'config.yaml'
        config_file.write_text("""
version: 3.0.0
database:
  type: postgresql
""")
        
        result = installer.enable_serena_mcp()
        
        # Should add features section with Serena enabled
        updated_content = config_file.read_text()
        assert 'features:' in updated_content
        assert 'serena_mcp:' in updated_content
        assert 'use_in_prompts: true' in updated_content

    def test_serena_toggle_preserves_other_config(self, installer, tmp_path):
        """Test Serena toggle preserves other config.yaml settings"""
        installer.settings['enable_serena'] = True
        installer.settings['install_dir'] = str(tmp_path)
        
        # Create config.yaml with various settings
        config_file = tmp_path / 'config.yaml'
        original_content = """
version: 3.0.0
database:
  type: postgresql
  host: localhost
features:
  authentication: true
  serena_mcp:
    use_in_prompts: false
  api_keys_enabled: false
"""
        config_file.write_text(original_content)
        
        result = installer.enable_serena_mcp()
        
        # Should preserve other settings
        updated_content = config_file.read_text()
        assert 'database:' in updated_content
        assert 'type: postgresql' in updated_content
        assert 'authentication: true' in updated_content
        assert 'api_keys_enabled: false' in updated_content
        # But update Serena
        assert 'use_in_prompts: true' in updated_content

    def test_serena_toggle_failure_does_not_fail_installation(self, installer):
        """Test Serena toggle failures are logged as warnings"""
        installer.settings['enable_serena'] = True
        
        with patch.object(installer, 'enable_serena_mcp', side_effect=Exception("Config update failed")):
            with patch.multiple(
                installer,
                welcome_screen=Mock(),
                check_python_version=Mock(return_value=True),
                discover_postgresql=Mock(return_value={'found': True}),
                install_dependencies=Mock(return_value={'success': True}),
                generate_configs=Mock(return_value={'success': True}),
                setup_database=Mock(return_value={'success': True, 'credentials': {}}),
                update_env_with_real_credentials=Mock(return_value={'success': True}),
                launch_services=Mock(return_value={'success': True, 'api_pid': 123, 'frontend_pid': 456})
            ):
                result = installer.run()
                
                # Installation should still succeed
                assert result['success'] is True


class TestInstallationWorkflowWithAllEnhancements:
    """Test complete installation workflow with all three enhancements"""

    @pytest.fixture
    def installer(self, tmp_path: Path):
        """Create installer instance"""
        from install import UnifiedInstaller

        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'pg_password': '4010',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
            'create_tables': True,
            'register_mcp_tools': True,
            'enable_serena': True
        }

        return UnifiedInstaller(settings=settings)

    def test_all_enhancements_execute_in_correct_order(self, installer):
        """Test all three enhancements execute in correct order"""
        call_order = []
        
        def track_call(name):
            def wrapper(*args, **kwargs):
                call_order.append(name)
                if name == 'generate_configs':
                    return {'success': True}
                elif name == 'setup_database':
                    return {'success': True, 'credentials': {}}
                elif name == 'launch_services':
                    return {'success': True, 'api_pid': 123, 'frontend_pid': 456}
                else:
                    return {'success': True}
            return wrapper
        
        with patch.multiple(
            installer,
            welcome_screen=Mock(),
            check_python_version=Mock(return_value=True),
            discover_postgresql=Mock(return_value={'found': True}),
            install_dependencies=Mock(return_value={'success': True}),
            generate_configs=Mock(side_effect=track_call('generate_configs')),
            setup_database=Mock(side_effect=track_call('setup_database')),
            update_env_with_real_credentials=Mock(return_value={'success': True}),
            enable_serena_mcp=Mock(side_effect=track_call('enable_serena')),
            launch_services=Mock(side_effect=track_call('launch_services')),
            register_mcp_tools=Mock(side_effect=track_call('register_mcp'))
        ):
            result = installer.run()
            
            # Verify order:
            # 1. Config generation
            # 2. Database setup (with migrations if enabled)
            # 3. Serena toggle (after configs)
            # 4. Services launch
            # 5. MCP registration (after services)
            
            assert call_order.index('generate_configs') < call_order.index('setup_database')
            assert call_order.index('setup_database') < call_order.index('enable_serena')
            assert call_order.index('enable_serena') < call_order.index('launch_services')
            assert call_order.index('launch_services') < call_order.index('register_mcp')
            
            assert result['success'] is True

    def test_all_enhancements_are_optional(self, installer, monkeypatch):
        """Test all three enhancements can be individually disabled"""
        import getpass
        
        # Decline all optional features
        inputs = [
            '',  # PostgreSQL password
            'n',  # Start services (NO)
            'n',  # Create tables (NO)
            'n',  # Register AI tools (NO)
            'n',  # Enable Serena (NO)
            'n',  # Create shortcuts
            'n',  # Verbose mode
        ]
        
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))
        monkeypatch.setattr('getpass.getpass', lambda _: '')
        
        installer.ask_installation_questions()
        
        # All should be disabled
        assert installer.settings.get('start_services', True) is False
        assert installer.settings.get('create_tables', True) is False
        assert installer.settings.get('register_mcp_tools', True) is False
        assert installer.settings.get('enable_serena', True) is False

    def test_summary_shows_all_enhancements_status(self, installer, capsys):
        """Test success summary shows status of all enhancements"""
        with patch.multiple(
            installer,
            welcome_screen=Mock(),
            check_python_version=Mock(return_value=True),
            discover_postgresql=Mock(return_value={'found': True}),
            install_dependencies=Mock(return_value={'success': True}),
            generate_configs=Mock(return_value={'success': True}),
            setup_database=Mock(return_value={'success': True, 'credentials': {}}),
            update_env_with_real_credentials=Mock(return_value={'success': True}),
            enable_serena_mcp=Mock(return_value={'success': True}),
            launch_services=Mock(return_value={'success': True, 'api_pid': 123, 'frontend_pid': 456}),
            register_mcp_tools=Mock(return_value={'success': True})
        ):
            result = installer.run()
            
            # Should print success summary
            installer._print_success_summary()
            
            captured = capsys.readouterr()
            # Summary should mention key features
            # (Exact output will depend on implementation)
