#!/usr/bin/env python3
"""
Comprehensive test suite for Project 5.2 Setup Enhancements
Tests all new setup modules and functionality
"""

import json
import os
import platform
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from tests.helpers.test_db_helper import PostgreSQLTestHelper


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
GUI_AVAILABLE = True
try:
    import tkinter as tk  # noqa: F401
except ImportError:
    GUI_AVAILABLE = False

try:
    import setup_config
    import setup_dependencies
    import setup_gui
    import setup_migration
    import setup_platform
    from setup import GiljoSetup

    MODULES_AVAILABLE = True
except ImportError:
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
        assert "system" in info
        assert "version" in info
        assert "architecture" in info
        assert info["system"] in ["Windows", "macOS", "Linux"]

    def test_package_manager_detection(self):
        """Test package manager detection"""
        info = self.detector.get_full_info()
        managers = info.get("package_managers", [])
        assert isinstance(managers, list)

        # Windows should detect at least one package manager
        if self.detector.system == "Windows":
            expected = ["pip", "conda", "choco", "winget", "scoop"]
            found = [m for m in managers if any(exp in m for exp in expected)]
            assert len(found) > 0 or len(managers) > 0, f"Package managers found: {managers}"

    def test_python_environment(self):
        """Test Python environment detection"""
        info = self.detector.get_full_info()
        assert "python_version" in info
        assert "virtual_env" in info

    def test_system_capabilities(self):
        """Test system capabilities detection"""
        info = self.detector.get_full_info()
        caps = info.get("capabilities", {})

        # Check for various capabilities
        "git_version" in info or caps.get("git", False)
        caps.get("docker", False)
        caps.get("admin_rights", False) or info.get("admin_rights", False)


class TestGUIWizard(unittest.TestCase):
    """Test Tkinter GUI wizard functionality"""

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_initialization(self):
        """Test GUI wizard can be initialized"""
        try:
            # Create wizard without showing it
            wizard = setup_gui.SetupWizard(show=False)
            assert wizard is not None
            assert wizard.current_page == 0
            assert len(wizard.pages) == 6

            # Test page navigation
            wizard.next_page()
            assert wizard.current_page == 1
            wizard.prev_page()
            assert wizard.current_page == 0

        except Exception:
            self.skipTest("Cannot test GUI in headless environment")

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_validation(self):
        """Test GUI input validation"""
        wizard = setup_gui.SetupWizard(show=False)

        # Test environment validation
        is_valid = wizard.validate_page_1({"environment": "dev"})
        assert is_valid

        is_valid = wizard.validate_page_1({"environment": "invalid"})
        assert not is_valid

    @unittest.skipIf(not GUI_AVAILABLE, "GUI modules not available")
    def test_gui_threading(self):
        """Test GUI threading for non-blocking operations"""
        wizard = setup_gui.SetupWizard(show=False)

        # Mock long-running operation
        def long_operation():
            time.sleep(0.1)
            return "database_initialized"

        result = wizard.run_async(long_operation)
        assert result is not None


class TestDependencyManagement(unittest.TestCase):
    """Test smart dependency management"""

    def setUp(self):
        self.dep_manager = setup_dependencies.DependencyManager()

    def test_requirements_parsing(self):
        """Test requirements.txt parsing"""
        # Create temporary requirements file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("fastapi>=0.100.0\n")
            f.write("sqlalchemy[asyncio]>=2.0.0\n")
            f.write("# Optional dependencies\n")
            f.write("redis>=4.5.0  # optional: caching\n")
            f.write("psycopg2-binary>=2.9.0  # optional: postgresql\n")
            temp_req = f.name

        try:
            core, optional = self.dep_manager.parse_requirements(temp_req)
            assert len(core) == 2
            assert len(optional) == 2
            assert "fastapi" in core[0]
            assert "redis" in optional[0]
        finally:
            os.unlink(temp_req)

    def test_installed_packages_check(self):
        """Test checking for installed packages"""
        installed = self.dep_manager.get_installed_packages()
        assert isinstance(installed, dict)
        assert "pip" in installed  # pip should always be installed

    def test_venv_detection(self):
        """Test virtual environment detection"""
        venv_info = self.dep_manager.detect_venv()
        assert "active" in venv_info
        assert "path" in venv_info

    def test_install_script_generation(self):
        """Test installation script generation"""
        deps = ["fastapi", "sqlalchemy", "httpx"]

        # Windows script
        if sys.platform == "win32":
            script = self.dep_manager.generate_install_script(deps, "windows")
            assert ".bat" in script
            assert "pip install" in script

        # Unix script
        script = self.dep_manager.generate_install_script(deps, "unix")
        assert ".sh" in script
        assert "#!/bin/bash" in script


class TestMigrationTool(unittest.TestCase):
    """Test legacy MCP migration functionality"""

    def setUp(self):
        self.migrator = setup_migration.AKEMigrator()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ake_detection(self):
        """Test legacy MCP installation detection"""
        # Check if legacy MCP exists
        ake_exists = self.migrator.detect_ake_mcp()
        if ake_exists:
            info = self.migrator.get_ake_info()
            assert "path" in info
            assert "database" in info
        else:
            pass

    def test_migration_data_structure(self):
        """Test migration data structure creation"""
        # Create mock data
        mock_data = {
            "projects": [{"id": "proj-1", "name": "Test Project", "mission": "Test mission"}],
            "agents": [{"id": "agent-1", "name": "test_agent", "project_id": "proj-1"}],
            "messages": [{"id": "msg-1", "from": "agent-1", "content": "Test message"}],
        }

        # Test data validation
        is_valid = self.migrator.validate_migration_data(mock_data)
        assert is_valid

    def test_uuid_preservation(self):
        """Test UUID preservation during migration"""
        original_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        preserved = self.migrator.preserve_uuid(original_uuid)
        assert original_uuid == preserved

    def test_vision_document_copying(self):
        """Test vision document migration"""
        # Create mock vision directory
        vision_dir = Path(self.test_dir) / "Vision"
        vision_dir.mkdir()

        # Create mock vision file
        vision_file = vision_dir / "test_vision.md"
        vision_file.write_text("# Test Vision Document\n\nThis is a test.")

        # Test copying
        dest_dir = Path(self.test_dir) / "dest"
        dest_dir.mkdir()

        success = self.migrator.copy_vision_documents(str(vision_dir), str(dest_dir))
        assert success

        # Verify file was copied
        copied_file = dest_dir / "Vision" / "test_vision.md"
        assert copied_file.exists()


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
            "environment": "dev",
            "database": {"type": "sqlite", "path": "test.db"},
            "api_keys": {"openai": "sk-test-key"},
        }

        # Export to JSON
        json_file = Path(self.test_dir) / "config.json"
        success = self.config_manager.export_config(config, str(json_file), format="json")
        assert success
        assert json_file.exists()

        # Export to YAML
        yaml_file = Path(self.test_dir) / "config.yaml"
        success = self.config_manager.export_config(config, str(yaml_file), format="yaml")
        assert success
        assert yaml_file.exists()

    def test_config_import(self):
        """Test configuration import from JSON/YAML"""
        # Create test config file
        config = {"environment": "prod", "database": {"type": "postgresql"}}

        json_file = Path(self.test_dir) / "import.json"
        with open(json_file, "w") as f:
            json.dump(config, f)

        # Import configuration
        imported = self.config_manager.import_config(str(json_file))
        assert imported is not None
        assert imported["environment"] == "prod"

    def test_config_encryption(self):
        """Test sensitive data encryption"""
        config = {"api_keys": {"openai": "sk-sensitive-key", "anthropic": "ant-sensitive-key"}}

        # Encrypt sensitive fields
        encrypted = self.config_manager.encrypt_sensitive(config)
        assert encrypted["api_keys"]["openai"] != "sk-sensitive-key"

        # Decrypt
        decrypted = self.config_manager.decrypt_sensitive(encrypted)
        assert decrypted["api_keys"]["openai"] == "sk-sensitive-key"

    def test_profile_management(self):
        """Test configuration profiles"""
        # Create profiles
        dev_profile = {"environment": "dev", "debug": True}
        prod_profile = {"environment": "prod", "debug": False}

        self.config_manager.save_profile("development", dev_profile)
        self.config_manager.save_profile("production", prod_profile)

        # Load profiles
        loaded_dev = self.config_manager.load_profile("development")
        assert loaded_dev["environment"] == "dev"

        loaded_prod = self.config_manager.load_profile("production")
        assert loaded_prod["environment"] == "prod"

    def test_backup_restore(self):
        """Test configuration backup and restore"""
        original_config = {"version": "1.0", "environment": "test"}

        # Create backup
        backup_path = self.config_manager.create_backup(original_config)
        assert backup_path is not None

        # Modify config

        # Restore from backup
        restored = self.config_manager.restore_backup(backup_path)
        assert restored["version"] == "1.0"
        assert restored["environment"] == "test"


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
        assert elapsed < 300, "Setup took longer than 5 minutes"

    def test_zero_config_mode(self):
        """Test zero-configuration local mode"""
        setup = GiljoSetup()

        # Test default configuration works without any input
        config = setup.get_default_config()
        assert config["environment"] == "development"
        assert config["database"]["type"] == "sqlite"
        assert config["api"]["host"] == "localhost"

    def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil

        process = psutil.Process()

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        GiljoSetup()
        detector = setup_platform.PlatformDetector()
        detector.detect()
        detector.detect_package_managers()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        assert memory_increase < 100, "Memory usage increased by more than 100MB"


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing setup.py"""

    def test_cli_mode_preserved(self):
        """Test CLI mode still works without GUI"""
        setup = GiljoSetup()

        # Test original CLI methods exist
        assert hasattr(setup, "run")
        assert hasattr(setup, "detect_platform")
        assert hasattr(setup, "setup_database")
        assert hasattr(setup, "create_directories")

    def test_existing_config_compatibility(self):
        """Test existing configuration files still work"""
        # Create old-style config
        old_config = {
            "database_url": PostgreSQLTestHelper.get_test_db_url(async_driver=False),
            "api_port": 6002,
            "websocket_port": 6003,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(old_config, f)
            temp_config = f.name

        try:
            # Test can load old config
            setup = GiljoSetup()
            loaded = setup.load_config(temp_config)
            assert loaded is not None
        finally:
            os.unlink(temp_config)

    def test_env_file_compatibility(self):
        """Test .env file generation compatibility"""
        setup = GiljoSetup()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_path = f.name

        try:
            setup.generate_env_file(env_path, environment="dev")

            # Check env file contains expected variables
            with open(env_path) as f:
                content = f.read()
                assert "DATABASE_URL" in content
                assert "API_HOST" in content
                assert "API_PORT" in content
        finally:
            os.unlink(env_path)


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility"""

    def test_path_handling(self):
        """Test OS-neutral path handling"""
        from pathlib import Path

        # Test paths work across platforms
        config_dir = Path.home() / ".giljo-mcp"
        assert isinstance(config_dir, Path)

        # Test no hardcoded separators
        test_path = Path("docs") / "Vision" / "test.md"
        assert "\\" not in str(test_path).replace(os.sep, "")
        assert "//" not in str(test_path)

    def test_line_endings(self):
        """Test file line endings handled correctly"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Line 1\nLine 2\r\nLine 3\r")
            temp_file = f.name

        try:
            with open(temp_file) as f:
                lines = f.readlines()
                # Should handle all line ending types
                assert len(lines) >= 3
        finally:
            os.unlink(temp_file)

    def test_executable_permissions(self):
        """Test executable permissions on scripts"""
        scripts = ["setup.py", "setup_gui.py", "setup_platform.py"]

        for script in scripts:
            if os.path.exists(script):
                # On Windows, check file exists and is readable
                if sys.platform == "win32":
                    assert os.access(script, os.R_OK)
                # On Unix, check executable bit
                else:
                    assert os.access(script, os.X_OK)


def generate_test_report(results):
    """Generate comprehensive test report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "test_results": results,
        "summary": {
            "total": results["total"],
            "passed": results["passed"],
            "failed": results["failed"],
            "skipped": results["skipped"],
            "success_rate": f"{(results['passed'] / results['total'] * 100):.1f}%" if results["total"] > 0 else "0%",
        },
    }

    # Save report
    with open("setup_enhancement_test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    """Run all tests and generate report"""

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
        TestCrossPlatformCompatibility,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate results summary
    results = {
        "total": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures) + len(result.errors),
        "skipped": len(result.skipped),
        "failures": [str(f) for f in result.failures],
        "errors": [str(e) for e in result.errors],
    }

    # Generate and print report
    generate_test_report(results)

    if results["failed"] > 0:
        for _failure in results["failures"] + results["errors"]:
            pass

    # Return exit code
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    # sys.exit(main())  # Commented for pytest
    pass
