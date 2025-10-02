#!/usr/bin/env python3
"""
Phase 3 Launch Validation Tests
Tests all Phase 3 implementation components
"""

import sys
import os
import time
import unittest
import tempfile
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.launch_validator import LaunchValidator
from installer.core.service_manager import ServiceManager
from installer.core.recovery import ErrorRecovery


class TestLaunchValidator(unittest.TestCase):
    """Test the launch validator component"""

    def setUp(self):
        self.validator = LaunchValidator(verbose=False)

    def test_check_config_files(self):
        """Test config file validation"""
        # Create temporary config files
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='POSTGRES_PASSWORD=test123')):
                with patch('yaml.safe_load', return_value={
                    'installation': {'mode': 'localhost'},
                    'services': {'api_port': 8000},
                    'features': {'ssl_enabled': False}
                }):
                    result = self.validator.check_config_files()
                    self.assertTrue(result)

    def test_check_ports_available(self):
        """Test port availability checking"""
        # Mock config
        self.validator.config = {
            'services': {
                'api_port': 58000,  # Use high port unlikely to be in use
                'websocket_port': 58001,
                'dashboard_port': 58002
            }
        }

        result = self.validator.check_ports_available()
        self.assertTrue(result)

    def test_check_dependencies(self):
        """Test Python package dependency checking"""
        # All required packages should be installed
        result = self.validator.check_dependencies()
        self.assertTrue(result)

    def test_validation_errors_collection(self):
        """Test that errors are properly collected"""
        # Force a validation failure
        with patch('pathlib.Path.exists', return_value=False):
            self.validator.check_config_files()

        errors = self.validator.get_errors()
        self.assertGreater(len(errors), 0)
        self.assertIn("Missing", errors[0])


class TestServiceManager(unittest.TestCase):
    """Test the service manager component"""

    def setUp(self):
        # Create a test config
        self.test_config = {
            'services': {
                'bind': '127.0.0.1',
                'api_port': 58000,
                'websocket_port': 58001,
                'dashboard_port': 58002
            },
            'features': {
                'ssl_enabled': False
            }
        }

        with patch.object(ServiceManager, 'load_config', return_value=self.test_config):
            self.manager = ServiceManager()

    def test_service_order(self):
        """Test that services have correct startup order"""
        expected_order = ['database', 'api', 'websocket', 'dashboard']
        self.assertEqual(ServiceManager.SERVICE_ORDER, expected_order)

    def test_wait_for_service(self):
        """Test service availability waiting"""
        # Test with a port that's definitely not in use
        result = self.manager.wait_for_service('localhost', 59999, timeout=1)
        self.assertFalse(result)

        # Test with a mock server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))  # Bind to any available port
            sock.listen(1)
            port = sock.getsockname()[1]

            result = self.manager.wait_for_service('localhost', port, timeout=1)
            self.assertTrue(result)

    def test_check_service_health(self):
        """Test service health checking"""
        # Mock a running process
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is running
        self.manager.processes['api'] = mock_proc

        result = self.manager.check_service_health('api')
        self.assertTrue(result)

        # Mock a stopped process
        mock_proc.poll.return_value = 1  # Process has exited
        result = self.manager.check_service_health('api')
        self.assertFalse(result)

    def test_retry_logic(self):
        """Test that service startup includes retry logic"""
        # This is tested implicitly in start_all
        self.assertEqual(self.manager.retry_attempts, 3)
        self.assertEqual(self.manager.startup_timeout, 30)


class TestErrorRecovery(unittest.TestCase):
    """Test the error recovery component"""

    def setUp(self):
        self.recovery = ErrorRecovery(verbose=False)

    def test_find_free_port(self):
        """Test finding an available port"""
        # Should find a free port
        port = self.recovery.find_free_port(50000)
        self.assertIsNotNone(port)
        self.assertGreaterEqual(port, 50000)
        self.assertLess(port, 50100)

    def test_is_our_service(self):
        """Test identifying our own services"""
        # Without a real service running, should return False
        result = self.recovery.is_our_service(8000)
        self.assertFalse(result)

    @patch('platform.system')
    def test_recover_database_windows(self, mock_platform):
        """Test database recovery on Windows"""
        mock_platform.return_value = "Windows"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1  # Simulate failure
            result = self.recovery.recover_database()
            self.assertFalse(result)

            # Check that Windows-specific commands were attempted
            calls = [str(call) for call in mock_run.call_args_list]
            self.assertTrue(any('net' in str(call) for call in calls))

    def test_update_config_port(self):
        """Test configuration port update"""
        # Create temporary config file
        config_data = """
services:
  api_port: 8000
  websocket_port: 8001
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_data)
            temp_config = f.name

        self.recovery.config_path = Path(temp_config)

        try:
            # Update port
            result = self.recovery.update_config_port(8000, 8080)
            self.assertTrue(result)

            # Verify update
            import yaml
            with open(temp_config) as f:
                updated_config = yaml.safe_load(f)
            self.assertEqual(updated_config['services']['api_port'], 8080)

        finally:
            # Cleanup
            os.unlink(temp_config)

    def test_recover_missing_config(self):
        """Test recovery from missing configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.recovery.config_path = Path(temp_dir) / 'config.yaml'
            self.recovery.env_path = Path(temp_dir) / '.env'

            result = self.recovery.recover_missing_config()

            # Should create both files
            self.assertTrue(self.recovery.config_path.exists())
            self.assertTrue(self.recovery.env_path.exists())


class TestIntegration(unittest.TestCase):
    """Integration tests for Phase 3 components"""

    def test_validator_integration(self):
        """Test that validator integrates properly"""
        validator = LaunchValidator(verbose=False)

        # Should be able to run without crashing
        try:
            validator.validate_all()
            # Don't assert result as it depends on system state
        except Exception as e:
            self.fail(f"Validator crashed: {e}")

    def test_recovery_integration(self):
        """Test that recovery integrates with validator errors"""
        validator = LaunchValidator(verbose=False)
        recovery = ErrorRecovery(verbose=False)

        # Mock some errors
        test_errors = [
            "Port 8000 (API) in use",
            "Missing .env"
        ]

        # Should handle errors without crashing
        try:
            recovery.recover_all(test_errors)
        except Exception as e:
            self.fail(f"Recovery crashed: {e}")


class TestPerformance(unittest.TestCase):
    """Test performance requirements"""

    def test_validation_performance(self):
        """Test that validation completes quickly"""
        validator = LaunchValidator(verbose=False)

        start_time = time.time()
        validator.check_config_files()
        validator.check_ports_available()
        validator.check_dependencies()
        duration = time.time() - start_time

        # Should complete basic checks in under 2 seconds
        self.assertLess(duration, 2.0)

    def test_recovery_performance(self):
        """Test that recovery attempts are timely"""
        recovery = ErrorRecovery(verbose=False)

        start_time = time.time()
        recovery.find_free_port(50000)
        duration = time.time() - start_time

        # Port scanning should be quick
        self.assertLess(duration, 0.5)


def run_phase3_tests():
    """Run all Phase 3 tests and report results"""
    print("=" * 60)
    print("   Phase 3 Launch Validation Test Suite")
    print("=" * 60)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestLaunchValidator,
        TestServiceManager,
        TestErrorRecovery,
        TestIntegration,
        TestPerformance
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 60)
    print("   Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\nFailed tests:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nTests with errors:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_phase3_tests()
    sys.exit(0 if success else 1)
