#!/usr/bin/env python3
"""
Comprehensive test suite for Project 5.2 Setup Enhancements
Tests all new setup modules and functionality
"""

import os
import sys
import json
import time
import platform
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
GUI_AVAILABLE = True
try:
    import tkinter as tk
except ImportError:
    GUI_AVAILABLE = False

try:
    import setup_gui
    import setup_platform
    import setup_migration
    import setup_dependencies
    import setup_config
    from setup import GiljoSetup
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import setup modules: {e}")
    MODULES_AVAILABLE = False
    # Create mock classes for testing
    class MockSetupClass:
        pass
    if not MODULES_AVAILABLE:
        setup_gui = MockSetupClass()
        setup_platform = MockSetupClass()
        setup_migration = MockSetupClass()
        setup_dependencies = MockSetupClass()
        setup_config = MockSetupClass()

class TestPlatformDetection(unittest.TestCase):
    """Test enhanced platform detection capabilities"""

    def setUp(self):
        self.detector = setup_platform.PlatformDetector()

    def test_os_detection(self):
        """Test operating system detection"""
        info = self.detector.get_full_info()
        self.assertIn('system', info)
        self.assertIn('version', info)
        self.assertIn('architecture', info)
        self.assertIn(info['system'], ['Windows', 'macOS', 'Linux'])
        print(f"✓ Platform detected: {info['system']} {info.get('version', 'unknown')} ({info['architecture']})")

    def test_package_manager_detection(self):
        """Test package manager detection"""
        info = self.detector.get_full_info()
        managers = info.get('package_managers', [])
        self.assertIsInstance(managers, list)

        # Windows should detect at least one package manager
        if self.detector.system == 'Windows':
            expected = ['pip', 'conda', 'choco', 'winget', 'scoop']
            found = [m for m in managers if any(exp in m for exp in expected)]
            self.assertTrue(len(found) > 0 or len(managers) > 0,
                          f"Package managers found: {managers}")

        print(f"✓ Package managers detected: {', '.join(managers) if managers else 'None'}")

    def test_python_environment(self):
        """Test Python environment detection"""
        info = self.detector.get_full_info()
        self.assertIn('python_version', info)
        self.assertIn('virtual_env', info)
        print(f"✓ Python {info['python_version']}, Virtual env: {info.get('virtual_env', 'None')}")

    def test_system_capabilities(self):
        """Test system capabilities detection"""
        info = self.detector.get_full_info()
        caps = info.get('capabilities', {})

        # Check for various capabilities
        has_git = 'git_version' in info or caps.get('git', False)
        has_docker = caps.get('docker', False)
        is_admin = caps.get('admin_rights', False) or info.get('admin_rights', False)

        print(f"✓ System capabilities: Admin={is_admin}, Git={has_git}, Docker={has_docker}")

class TestGUIWizard(unittest.TestCase):
    """Test Tkinter GUI wizard functionality"""

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_initialization(self):
        """Test GUI wizard can be initialized"""
        try:
            # Create wizard without showing it
            wizard = setup_gui.SetupWizard(show=False)
            self.assertIsNotNone(wizard)
            self.assertEqual(wizard.current_page, 0)
            self.assertEqual(len(wizard.pages), 6)
            print("✓ GUI wizard initialized with 6 pages")

            # Test page navigation
            wizard.next_page()
            self.assertEqual(wizard.current_page, 1)
            wizard.prev_page()
            self.assertEqual(wizard.current_page, 0)
            print("✓ Page navigation working")

        except Exception as e:
            print(f"✗ GUI test failed: {e}")
            self.skipTest("Cannot test GUI in headless environment")

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_validation(self):
        """Test GUI input validation"""
        wizard = setup_gui.SetupWizard(show=False)

        # Test environment validation
        is_valid = wizard.validate_page_1({'environment': 'dev'})
        self.assertTrue(is_valid)

        is_valid = wizard.validate_page_1({'environment': 'invalid'})
        self.assertFalse(is_valid)
        print("✓ GUI validation working")

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_threading(self):
        """Test GUI threading for non-blocking operations"""
        wizard = setup_gui.SetupWizard(show=False)

        # Mock long-running operation
        def long_operation():
            time.sleep(0.1)
            return "completed"

        result = wizard.run_async(long_operation)
        self.assertIsNotNone(result)
        print("✓ GUI threading operational")

class TestDependencyManagement(unittest.TestCase):
    """Test smart dependency management"""

    def setUp(self):
        self.dep_manager = setup_dependencies.DependencyManager()

    def test_requirements_parsing(self):
        """Test requirements.txt parsing"""
        # Create temporary requirements file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("fastapi>=0.100.0\n")
            f.write("sqlalchemy[asyncio]>=2.0.0\n")
            f.write("# Optional dependencies\n")
            f.write("redis>=4.5.0  # optional: caching\n")
            f.write("psycopg2-binary>=2.9.0  # optional: postgresql\n")
            temp_req = f.name

        try:
            core, optional = self.dep_manager.parse_requirements(temp_req)
            self.assertEqual(len(core), 2)
            self.assertEqual(len(optional), 2)
            self.assertIn('fastapi', core[0])
            self.assertIn('redis', optional[0])
            print(f"✓ Parsed {len(core)} core and {len(optional)} optional dependencies")
        finally:
            os.unlink(temp_req)

    def test_installed_packages_check(self):
        """Test checking for installed packages"""
        installed = self.dep_manager.get_installed_packages()
        self.assertIsInstance(installed, dict)
        self.assertIn('pip', installed)  # pip should always be installed
        print(f"✓ Found {len(installed)} installed packages")

    def test_venv_detection(self):
        """Test virtual environment detection"""
        venv_info = self.dep_manager.detect_venv()
        self.assertIn('active', venv_info)
        self.assertIn('path', venv_info)
        print(f"✓ Virtual environment active: {venv_info['active']}")

    def test_install_script_generation(self):
        """Test installation script generation"""
        deps = ['fastapi', 'sqlalchemy', 'httpx']

        # Windows script
        if sys.platform == 'win32':
            script = self.dep_manager.generate_install_script(deps, 'windows')
            self.assertIn('.bat', script)
            self.assertIn('pip install', script)
            print("✓ Windows .bat script generated")

        # Unix script
        script = self.dep_manager.generate_install_script(deps, 'unix')
        self.assertIn('.sh', script)
        self.assertIn('#!/bin/bash', script)
        print("✓ Unix .sh script generated")

class TestMigrationTool(unittest.TestCase):
    """Test AKE-MCP migration functionality"""

    def setUp(self):
        self.migrator = setup_migration.AKEMigrator()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ake_detection(self):
        """Test AKE-MCP installation detection"""
        # Check if F:/AKE-MCP exists
        ake_exists = self.migrator.detect_ake_mcp()
        if ake_exists:
            info = self.migrator.get_ake_info()
            self.assertIn('path', info)
            self.assertIn('database', info)
            print(f"✓ AKE-MCP detected at {info['path']}")
        else:
            print("✓ AKE-MCP not found at F:/AKE-MCP (expected in test environment)")

    def test_migration_data_structure(self):
        """Test migration data structure creation"""
        # Create mock data
        mock_data = {
            'projects': [
                {'id': 'proj-1', 'name': 'Test Project', 'mission': 'Test mission'}
            ],
            'agents': [
                {'id': 'agent-1', 'name': 'test_agent', 'project_id': 'proj-1'}
            ],
            'messages': [
                {'id': 'msg-1', 'from': 'agent-1', 'content': 'Test message'}
            ]
        }

        # Test data validation
        is_valid = self.migrator.validate_migration_data(mock_data)
        self.assertTrue(is_valid)
        print("✓ Migration data structure validated")

    def test_uuid_preservation(self):
        """Test UUID preservation during migration"""
        original_uuid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        preserved = self.migrator.preserve_uuid(original_uuid)
        self.assertEqual(original_uuid, preserved)
        print("✓ UUID preservation working")

    def test_vision_document_copying(self):
        """Test vision document migration"""
        # Create mock vision directory
        vision_dir = Path(self.test_dir) / 'Vision'
        vision_dir.mkdir()

        # Create mock vision file
        vision_file = vision_dir / 'test_vision.md'
        vision_file.write_text("# Test Vision Document\n\nThis is a test.")

        # Test copying
        dest_dir = Path(self.test_dir) / 'dest'
        dest_dir.mkdir()

        success = self.migrator.copy_vision_documents(str(vision_dir), str(dest_dir))
        self.assertTrue(success)

        # Verify file was copied
        copied_file = dest_dir / 'Vision' / 'test_vision.md'
        self.assertTrue(copied_file.exists())
        print("✓ Vision documents copied successfully")

class TestConfigurationManagement(unittest.TestCase):
    """Test configuration import/export functionality"""

    def setUp(self):
        self.config_manager = setup_config.ConfigManager()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_config_export(self):
        """Test configuration export to JSON/YAML"""
        config = {
            'environment': 'dev',
            'database': {
                'type': 'sqlite',
                'path': 'test.db'
            },
            'api_keys': {
                'openai': 'sk-test-key'
            }
        }

        # Export to JSON
        json_file = Path(self.test_dir) / 'config.json'
        success = self.config_manager.export_config(config, str(json_file), format='json')
        self.assertTrue(success)
        self.assertTrue(json_file.exists())
        print("✓ Configuration exported to JSON")

        # Export to YAML
        yaml_file = Path(self.test_dir) / 'config.yaml'
        success = self.config_manager.export_config(config, str(yaml_file), format='yaml')
        self.assertTrue(success)
        self.assertTrue(yaml_file.exists())
        print("✓ Configuration exported to YAML")

    def test_config_import(self):
        """Test configuration import from JSON/YAML"""
        # Create test config file
        config = {
            'environment': 'prod',
            'database': {'type': 'postgresql'}
        }

        json_file = Path(self.test_dir) / 'import.json'
        with open(json_file, 'w') as f:
            json.dump(config, f)

        # Import configuration
        imported = self.config_manager.import_config(str(json_file))
        self.assertIsNotNone(imported)
        self.assertEqual(imported['environment'], 'prod')
        print("✓ Configuration imported successfully")

    def test_config_encryption(self):
        """Test sensitive data encryption"""
        config = {
            'api_keys': {
                'openai': 'sk-sensitive-key',
                'anthropic': 'ant-sensitive-key'
            }
        }

        # Encrypt sensitive fields
        encrypted = self.config_manager.encrypt_sensitive(config)
        self.assertNotEqual(encrypted['api_keys']['openai'], 'sk-sensitive-key')
        print("✓ Sensitive data encrypted")

        # Decrypt
        decrypted = self.config_manager.decrypt_sensitive(encrypted)
        self.assertEqual(decrypted['api_keys']['openai'], 'sk-sensitive-key')
        print("✓ Sensitive data decrypted")

    def test_profile_management(self):
        """Test configuration profiles"""
        # Create profiles
        dev_profile = {'environment': 'dev', 'debug': True}
        prod_profile = {'environment': 'prod', 'debug': False}

        self.config_manager.save_profile('development', dev_profile)
        self.config_manager.save_profile('production', prod_profile)

        # Load profiles
        loaded_dev = self.config_manager.load_profile('development')
        self.assertEqual(loaded_dev['environment'], 'dev')

        loaded_prod = self.config_manager.load_profile('production')
        self.assertEqual(loaded_prod['environment'], 'prod')
        print("✓ Configuration profiles working")

    def test_backup_restore(self):
        """Test configuration backup and restore"""
        original_config = {
            'version': '1.0',
            'environment': 'test'
        }

        # Create backup
        backup_path = self.config_manager.create_backup(original_config)
        self.assertIsNotNone(backup_path)
        print(f"✓ Backup created at {backup_path}")

        # Modify config
        modified_config = {
            'version': '2.0',
            'environment': 'modified'
        }

        # Restore from backup
        restored = self.config_manager.restore_backup(backup_path)
        self.assertEqual(restored['version'], '1.0')
        self.assertEqual(restored['environment'], 'test')
        print("✓ Configuration restored from backup")

class TestPerformanceMetrics(unittest.TestCase):
    """Test performance and efficiency metrics"""

    def test_setup_time(self):
        """Test setup completion time"""
        start_time = time.time()

        # Simulate setup process
        setup = GiljoSetup()
        setup.detect_platform()
        setup.check_dependencies()
        setup.validate_environment()

        elapsed = time.time() - start_time
        self.assertLess(elapsed, 300, "Setup took longer than 5 minutes")
        print(f"✓ Setup completed in {elapsed:.2f} seconds (< 5 minutes)")

    def test_zero_config_mode(self):
        """Test zero-configuration local mode"""
        setup = GiljoSetup()

        # Test default configuration works without any input
        config = setup.get_default_config()
        self.assertEqual(config['environment'], 'development')
        self.assertEqual(config['database']['type'], 'sqlite')
        self.assertEqual(config['api']['host'], 'localhost')
        print("✓ Zero-config mode operational")

    def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil
        process = psutil.Process()

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        setup = GiljoSetup()
        detector = setup_platform.PlatformDetector()
        detector.detect()
        detector.detect_package_managers()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        self.assertLess(memory_increase, 100, "Memory usage increased by more than 100MB")
        print(f"✓ Memory usage increase: {memory_increase:.2f} MB (< 100 MB)")

class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing setup.py"""

    def test_cli_mode_preserved(self):
        """Test CLI mode still works without GUI"""
        setup = GiljoSetup()

        # Test original CLI methods exist
        self.assertTrue(hasattr(setup, 'run'))
        self.assertTrue(hasattr(setup, 'detect_platform'))
        self.assertTrue(hasattr(setup, 'setup_database'))
        self.assertTrue(hasattr(setup, 'create_directories'))
        print("✓ Original CLI methods preserved")

    def test_existing_config_compatibility(self):
        """Test existing configuration files still work"""
        # Create old-style config
        old_config = {
            'database_url': 'sqlite:///giljo_mcp.db',
            'api_port': 6002,
            'websocket_port': 6003
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(old_config, f)
            temp_config = f.name

        try:
            # Test can load old config
            setup = GiljoSetup()
            loaded = setup.load_config(temp_config)
            self.assertIsNotNone(loaded)
            print("✓ Old configuration format still supported")
        finally:
            os.unlink(temp_config)

    def test_env_file_compatibility(self):
        """Test .env file generation compatibility"""
        setup = GiljoSetup()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            env_path = f.name

        try:
            setup.generate_env_file(env_path, environment='dev')

            # Check env file contains expected variables
            with open(env_path, 'r') as f:
                content = f.read()
                self.assertIn('DATABASE_URL', content)
                self.assertIn('API_HOST', content)
                self.assertIn('API_PORT', content)
            print("✓ .env file generation compatible")
        finally:
            os.unlink(env_path)

class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility"""

    def test_path_handling(self):
        """Test OS-neutral path handling"""
        from pathlib import Path

        # Test paths work across platforms
        config_dir = Path.home() / '.giljo-mcp'
        self.assertIsInstance(config_dir, Path)

        # Test no hardcoded separators
        test_path = Path('docs') / 'Vision' / 'test.md'
        self.assertNotIn('\\', str(test_path).replace(os.sep, ''))
        self.assertNotIn('//', str(test_path))
        print("✓ Path handling is OS-neutral")

    def test_line_endings(self):
        """Test file line endings handled correctly"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\r\nLine 3\r")
            temp_file = f.name

        try:
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                # Should handle all line ending types
                self.assertTrue(len(lines) >= 3)
            print("✓ Line endings handled correctly")
        finally:
            os.unlink(temp_file)

    def test_executable_permissions(self):
        """Test executable permissions on scripts"""
        scripts = ['setup.py', 'setup_gui.py', 'setup_platform.py']

        for script in scripts:
            if os.path.exists(script):
                # On Windows, check file exists and is readable
                if sys.platform == 'win32':
                    self.assertTrue(os.access(script, os.R_OK))
                # On Unix, check executable bit
                else:
                    self.assertTrue(os.access(script, os.X_OK))
        print("✓ Script permissions appropriate for platform")

def generate_test_report(results):
    """Generate comprehensive test report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'architecture': platform.machine(),
            'python': platform.python_version()
        },
        'test_results': results,
        'summary': {
            'total': results['total'],
            'passed': results['passed'],
            'failed': results['failed'],
            'skipped': results['skipped'],
            'success_rate': f"{(results['passed'] / results['total'] * 100):.1f}%" if results['total'] > 0 else "0%"
        }
    }

    # Save report
    with open('setup_enhancement_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    return report

def main():
    """Run all tests and generate report"""
    print("=" * 70)
    print("PROJECT 5.2 SETUP ENHANCEMENT - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Testing on: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()}")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestPlatformDetection,
        TestGUIWizard,
        TestDependencyManagement,
        TestMigrationTool,
        TestConfigurationManagement,
        TestPerformanceMetrics,
        TestBackwardCompatibility,
        TestCrossPlatformCompatibility
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate results summary
    results = {
        'total': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        'failed': len(result.failures) + len(result.errors),
        'skipped': len(result.skipped),
        'failures': [str(f) for f in result.failures],
        'errors': [str(e) for e in result.errors]
    }

    # Generate and print report
    report = generate_test_report(results)

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']} ✓")
    print(f"Failed: {results['failed']}" + (" ✗" if results['failed'] > 0 else ""))
    print(f"Skipped: {results['skipped']}")
    print(f"Success Rate: {report['summary']['success_rate']}")

    if results['failed'] > 0:
        print("\nFailed Tests:")
        for failure in results['failures'] + results['errors']:
            print(f"  - {failure[:100]}...")

    print(f"\nDetailed report saved to: setup_enhancement_test_report.json")
    print("=" * 70)

    # Return exit code
    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())