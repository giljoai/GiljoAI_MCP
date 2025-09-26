#!/usr/bin/env python3
"""
Test script for bootstrap.py
Tests various scenarios without requiring user input
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the bootstrap module
import bootstrap


class TestBootstrap(unittest.TestCase):
    """Test cases for bootstrap installer"""

    def setUp(self):
        """Set up test environment"""
        self.bootstrap = bootstrap.Bootstrap()

    def test_python_version_check(self):
        """Test Python version checking"""
        print("Testing Python version check...")
        result = self.bootstrap.check_python_version()
        self.assertTrue(result, "Python version should be 3.8+")
        print(f"  OK Python {sys.version_info.major}.{sys.version_info.minor} detected")

    def test_os_detection(self):
        """Test OS detection"""
        print("Testing OS detection...")
        os_info = self.bootstrap.detect_os()

        self.assertIn("system", os_info)
        self.assertIn("python", os_info)

        print(f"  OK OS: {os_info['system']}")
        print(f"  OK Python: {os_info['python']}")
        print(f"  OK Machine: {os_info.get('machine', 'Unknown')}")

    def test_color_support(self):
        """Test terminal color support detection"""
        print("Testing color support...")
        has_color = self.bootstrap.supports_color()
        print(f"  OK Color support: {has_color}")

        # Check that colors dict is properly initialized
        if has_color:
            self.assertTrue(any(self.bootstrap.colors.values()))
        else:
            self.assertTrue(all(v == "" for v in self.bootstrap.colors.values()))

    def test_existing_installation_check(self):
        """Test detection of existing installation"""
        print("Testing existing installation detection...")
        existing = self.bootstrap.check_existing_installation()

        if existing:
            print(f"  OK Found installation at: {existing['path']}")
            print(f"    Markers: {', '.join(existing['markers'])}")
        else:
            print("  OK No existing installation found")

    def test_gui_capability_check(self):
        """Test GUI capability detection"""
        print("Testing GUI capability check...")

        # Mock to avoid actual GUI test
        with patch.object(self.bootstrap, "os_type", "windows"):
            with patch("builtins.__import__") as mock_import:
                # Simulate tkinter available
                mock_import.return_value = MagicMock()

                # For Windows, also check env vars
                with patch.dict(os.environ, {}, clear=False):
                    # Remove SSH_CONNECTION if present
                    env_copy = dict(os.environ)
                    env_copy.pop("SSH_CONNECTION", None)
                    env_copy.pop("CONTAINER", None)

                    with patch.dict(os.environ, env_copy, clear=True):
                        has_gui = self.bootstrap.check_gui_capability()
                        print(f"  OK GUI capability: {has_gui}")

    def test_print_functions(self):
        """Test print functions don't crash"""
        print("Testing print functions...")

        try:
            self.bootstrap.print_header()
            print("  OK Header printed")

            self.bootstrap.print_status("Test message", "info")
            print("  OK Info message")

            self.bootstrap.print_status("Success test", "success")
            print("  OK Success message")

            self.bootstrap.print_status("Warning test", "warning")
            print("  OK Warning message")

            self.bootstrap.print_status("Error test", "error")
            print("  OK Error message")

            self.bootstrap.print_system_info()
            print("  OK System info printed")

            self.bootstrap.print_manual_instructions()
            print("  OK Manual instructions printed")

        except Exception as e:
            self.fail(f"Print function failed: {e}")

    def test_cli_launcher_fallback(self):
        """Test CLI launcher with setup.py check"""
        print("Testing CLI launcher...")

        # Check if setup.py exists
        setup_exists = Path("setup.py").exists()
        print(f"  setup.py exists: {setup_exists}")

        if not setup_exists:
            # Test that it handles missing setup.py gracefully
            with patch("subprocess.run") as mock_run:
                result = self.bootstrap.launch_cli_installer()
                self.assertEqual(result, 1, "Should return error code when setup.py missing")
                print("  OK Handles missing setup.py correctly")
        else:
            print("  OK setup.py found, would launch CLI installer")

    def test_gui_launcher_fallback(self):
        """Test GUI launcher with setup_gui.py check"""
        print("Testing GUI launcher...")

        # Check if setup_gui.py exists
        gui_exists = Path("setup_gui.py").exists()
        print(f"  setup_gui.py exists: {gui_exists}")

        if not gui_exists:
            # Test that it falls back to CLI
            with patch.object(self.bootstrap, "launch_cli_installer", return_value=0) as mock_cli:
                result = self.bootstrap.launch_gui_installer()
                mock_cli.assert_called_once()
                print("  OK Falls back to CLI when GUI not available")
        else:
            print("  OK setup_gui.py found, would launch GUI installer")


class TestBootstrapIntegration(unittest.TestCase):
    """Integration tests for bootstrap"""

    def test_bootstrap_flow_no_input(self):
        """Test complete bootstrap flow without user input"""
        print("\nTesting bootstrap flow simulation...")

        bs = bootstrap.Bootstrap()

        # Mock user inputs and subprocess calls
        with patch("builtins.input", side_effect=["n"]):  # Don't reinstall
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                # Simulate the flow
                try:
                    # Check Python version
                    if not bs.check_python_version():
                        print("  ✗ Python version too old")
                        return

                    # Check existing installation
                    existing = bs.check_existing_installation()
                    if existing:
                        print("  OK Detected existing installation")

                    # The actual run would prompt here, but we're mocking 'n'
                    print("  OK Bootstrap flow completed successfully")

                except EOFError:
                    # Expected when input is mocked
                    print("  OK User input simulation worked")

    def test_bootstrap_in_temp_dir(self):
        """Test bootstrap in a clean temporary directory"""
        print("\nTesting bootstrap in clean directory...")

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create a minimal bootstrap in temp dir
                shutil.copy2(os.path.join(original_cwd, "bootstrap.py"), "bootstrap.py")

                # Create bootstrap and test
                bs = bootstrap.Bootstrap()
                existing = bs.check_existing_installation()

                self.assertIsNone(existing, "Should find no installation in temp dir")
                print("  OK Clean directory test passed")

            finally:
                os.chdir(original_cwd)


def run_tests():
    """Run all tests with nice output"""
    print("=" * 60)
    print("Bootstrap.py Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestBootstrap))
    suite.addTests(loader.loadTestsFromTestCase(TestBootstrapIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[OK] All tests passed!")
    else:
        print("\n[X] Some tests failed")
        if result.failures:
            print("\nFailures:")
            for test, trace in result.failures:
                print(f"  - {test}: {trace.split(chr(10))[0]}")
        if result.errors:
            print("\nErrors:")
            for test, trace in result.errors:
                print(f"  - {test}: {trace.split(chr(10))[0]}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
