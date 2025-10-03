#!/usr/bin/env python3
"""
GiljoAI MCP Comprehensive Test Scenarios
Complete test suite for Phase 4 validation
"""

import os
import sys
import json
import time
import subprocess
import socket
import psutil
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class TestScenarioRunner:
    """Comprehensive test scenario runner"""

    def __init__(self):
        self.root_dir = Path.cwd()
        self.test_dir = Path("C:/install_test/Giljo_MCP")
        self.log_dir = Path("C:/install_test/test_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        self.start_time = None

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_test(self, name: str, test_func, *args, **kwargs) -> bool:
        """Run a single test"""
        self.log(f"Running test: {name}")
        try:
            result = test_func(*args, **kwargs)
            status = "PASS" if result else "FAIL"
            self.results.append((name, status, None))
            self.log(f"Test {name}: {status}")
            return result
        except Exception as e:
            self.results.append((name, "ERROR", str(e)))
            self.log(f"Test {name}: ERROR - {e}", "ERROR")
            return False

    # ========== INSTALLATION TESTS ==========

    def test_clean_install_localhost(self) -> bool:
        """Test clean installation in localhost mode"""
        self.log("Testing clean localhost installation...")

        # Remove existing installation
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        # Copy project
        shutil.copytree(self.root_dir, self.test_dir,
                       ignore=shutil.ignore_patterns('__pycache__', '.git', 'venv'))

        # Run installer
        cmd = [
            sys.executable,
            str(self.test_dir / "installer" / "cli" / "install.py"),
            "--mode", "localhost",
            "--pg-host", "localhost",
            "--pg-port", "5432",
            "--pg-password", "4010",
            "--batch"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Verify installation
        config_exists = (self.test_dir / "config.yaml").exists()
        env_exists = (self.test_dir / ".env").exists()

        return result.returncode == 0 and config_exists and env_exists

    def test_clean_install_server(self) -> bool:
        """Test clean installation in server mode"""
        self.log("Testing clean server installation...")

        # Remove existing installation
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        # Copy project
        shutil.copytree(self.root_dir, self.test_dir,
                       ignore=shutil.ignore_patterns('__pycache__', '.git', 'venv'))

        # Run installer
        cmd = [
            sys.executable,
            str(self.test_dir / "installer" / "cli" / "install.py"),
            "--mode", "server",
            "--pg-host", "localhost",
            "--pg-port", "5432",
            "--pg-password", "4010",
            "--bind", "0.0.0.0",
            "--admin-username", "admin",
            "--admin-password", "test123",
            "--generate-api-key",
            "--batch"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Verify installation
        config_exists = (self.test_dir / "config.yaml").exists()
        env_exists = (self.test_dir / ".env").exists()

        # Check for server-specific configs
        if config_exists:
            import yaml
            with open(self.test_dir / "config.yaml") as f:
                config = yaml.safe_load(f)
                server_mode = config.get('mode') == 'server'
                return result.returncode == 0 and server_mode

        return False

    def test_upgrade_installation(self) -> bool:
        """Test upgrading existing installation"""
        self.log("Testing upgrade installation...")

        if not self.test_dir.exists():
            self.log("No existing installation to upgrade", "WARNING")
            return False

        # Save existing data
        data_dir = self.test_dir / "data"
        has_data = data_dir.exists()

        # Run installer in upgrade mode
        cmd = [
            sys.executable,
            str(self.test_dir / "installer" / "cli" / "install.py"),
            "--mode", "localhost",
            "--pg-host", "localhost",
            "--pg-port", "5432",
            "--pg-password", "4010",
            "--batch"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Verify data preserved
        if has_data:
            data_preserved = data_dir.exists()
            return result.returncode == 0 and data_preserved

        return result.returncode == 0

    # ========== SERVICE LAUNCH TESTS ==========

    def test_service_launch(self) -> bool:
        """Test launching services"""
        self.log("Testing service launch...")

        if not self.test_dir.exists():
            self.log("No installation found", "ERROR")
            return False

        os.chdir(self.test_dir)

        # Start services
        launcher_path = self.test_dir / "start_giljo.py"
        if not launcher_path.exists():
            self.log("Launcher not found", "ERROR")
            return False

        # Start in background
        process = subprocess.Popen(
            [sys.executable, str(launcher_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for startup
        time.sleep(10)

        # Check services
        services_running = self.check_services_running()

        # Stop services
        process.terminate()
        process.wait(timeout=5)

        os.chdir(self.root_dir)
        return services_running

    def check_services_running(self) -> bool:
        """Check if services are running"""
        ports = [8000, 8001]  # API and WebSocket

        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result != 0:
                self.log(f"Service on port {port} not running", "WARNING")
                return False

        return True

    # ========== UNINSTALL TESTS ==========

    def test_dev_uninstall(self) -> bool:
        """Test development uninstaller"""
        self.log("Testing development uninstaller...")

        if not self.test_dir.exists():
            self.log("No installation to uninstall", "WARNING")
            return False

        os.chdir(self.test_dir)

        # Run devuninstall
        uninstall_path = self.test_dir / "devuninstall.py"
        if not uninstall_path.exists():
            self.log("devuninstall.py not found", "ERROR")
            return False

        # Run with option 1 (remove files, keep PostgreSQL)
        result = subprocess.run(
            [sys.executable, str(uninstall_path)],
            input="1\nRESET\n",
            capture_output=True,
            text=True,
            timeout=60
        )

        os.chdir(self.root_dir)

        # Verify files removed
        files_removed = not (self.test_dir / "config.yaml").exists()
        return result.returncode == 0 and files_removed

    def test_production_uninstall(self) -> bool:
        """Test production uninstaller (careful!)"""
        self.log("Testing production uninstaller...")

        # This is destructive - only run in test environment
        if not self.test_dir.exists():
            self.log("No installation to uninstall", "WARNING")
            return False

        # For safety, we'll just verify the uninstaller exists
        uninstall_path = self.test_dir / "uninstall.py"
        return uninstall_path.exists()

    # ========== ERROR RECOVERY TESTS ==========

    def test_port_conflict_recovery(self) -> bool:
        """Test recovery from port conflicts"""
        self.log("Testing port conflict recovery...")

        # Block a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 8000))

        try:
            # Try to start services
            if not self.test_dir.exists():
                return False

            os.chdir(self.test_dir)

            launcher_path = self.test_dir / "start_giljo.py"
            if not launcher_path.exists():
                return False

            # This should fail gracefully
            process = subprocess.Popen(
                [sys.executable, str(launcher_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(5)

            # Check if process handled error
            if process.poll() is not None:
                # Process exited (good - detected conflict)
                return True

            process.terminate()
            return False

        finally:
            sock.close()
            os.chdir(self.root_dir)

    def test_database_connection_failure(self) -> bool:
        """Test handling of database connection failures"""
        self.log("Testing database connection failure handling...")

        if not self.test_dir.exists():
            return False

        # Temporarily modify config with bad database settings
        config_file = self.test_dir / "config.yaml"
        if not config_file.exists():
            return False

        import yaml

        # Backup original
        with open(config_file) as f:
            original = f.read()
            config = yaml.safe_load(original)

        # Modify with bad settings
        config['database']['host'] = 'nonexistent.host'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        try:
            os.chdir(self.test_dir)

            # Try to start services
            launcher_path = self.test_dir / "start_giljo.py"
            process = subprocess.Popen(
                [sys.executable, str(launcher_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(5)

            # Should fail gracefully
            graceful_failure = process.poll() is not None

            if process.poll() is None:
                process.terminate()

            return graceful_failure

        finally:
            # Restore original config
            with open(config_file, 'w') as f:
                f.write(original)
            os.chdir(self.root_dir)

    # ========== CONFIGURATION TESTS ==========

    def test_config_validation(self) -> bool:
        """Test configuration file validation"""
        self.log("Testing configuration validation...")

        if not self.test_dir.exists():
            return False

        config_file = self.test_dir / "config.yaml"
        env_file = self.test_dir / ".env"

        # Check both files exist
        if not config_file.exists() or not env_file.exists():
            return False

        # Validate YAML syntax
        try:
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)

            # Check required fields
            required = ['mode', 'database', 'services']
            for field in required:
                if field not in config:
                    self.log(f"Missing required field: {field}", "ERROR")
                    return False

            return True

        except yaml.YAMLError as e:
            self.log(f"Invalid YAML: {e}", "ERROR")
            return False

    def test_environment_variables(self) -> bool:
        """Test environment variable configuration"""
        self.log("Testing environment variables...")

        if not self.test_dir.exists():
            return False

        env_file = self.test_dir / ".env"
        if not env_file.exists():
            return False

        # Parse .env file
        env_vars = {}
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

        # Check required variables
        required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        for var in required:
            if var not in env_vars:
                self.log(f"Missing environment variable: {var}", "ERROR")
                return False

        return True

    # ========== PERFORMANCE TESTS ==========

    def test_installation_performance(self) -> bool:
        """Test installation completes within time limit"""
        self.log("Testing installation performance...")

        start_time = time.time()

        # Run a clean install
        result = self.test_clean_install_localhost()

        elapsed = time.time() - start_time
        self.log(f"Installation took {elapsed:.1f} seconds")

        # Should complete in under 5 minutes
        return result and elapsed < 300

    def test_startup_performance(self) -> bool:
        """Test service startup performance"""
        self.log("Testing startup performance...")

        if not self.test_dir.exists():
            return False

        os.chdir(self.test_dir)
        start_time = time.time()

        launcher_path = self.test_dir / "start_giljo.py"
        process = subprocess.Popen(
            [sys.executable, str(launcher_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for services
        services_up = False
        for _ in range(30):  # 30 second timeout
            if self.check_services_running():
                services_up = True
                break
            time.sleep(1)

        elapsed = time.time() - start_time
        self.log(f"Services started in {elapsed:.1f} seconds")

        process.terminate()
        process.wait(timeout=5)

        os.chdir(self.root_dir)

        # Should start in under 30 seconds
        return services_up and elapsed < 30

    # ========== MAIN TEST RUNNER ==========

    def run_all_tests(self):
        """Run all test scenarios"""
        self.start_time = time.time()

        print("\n" + "="*70)
        print("   GiljoAI MCP Comprehensive Test Suite")
        print("="*70)
        print()

        # Define test categories
        test_categories = [
            ("INSTALLATION", [
                ("Clean Install - Localhost", self.test_clean_install_localhost),
                ("Clean Install - Server", self.test_clean_install_server),
                ("Upgrade Installation", self.test_upgrade_installation),
            ]),
            ("SERVICE LAUNCH", [
                ("Service Launch", self.test_service_launch),
            ]),
            ("UNINSTALL", [
                ("Development Uninstall", self.test_dev_uninstall),
                ("Production Uninstall Check", self.test_production_uninstall),
            ]),
            ("ERROR RECOVERY", [
                ("Port Conflict Recovery", self.test_port_conflict_recovery),
                ("Database Connection Failure", self.test_database_connection_failure),
            ]),
            ("CONFIGURATION", [
                ("Config Validation", self.test_config_validation),
                ("Environment Variables", self.test_environment_variables),
            ]),
            ("PERFORMANCE", [
                ("Installation Performance", self.test_installation_performance),
                ("Startup Performance", self.test_startup_performance),
            ])
        ]

        # Run tests by category
        for category, tests in test_categories:
            print(f"\n{category} TESTS")
            print("-" * 40)

            for test_name, test_func in tests:
                self.run_test(test_name, test_func)

        # Show summary
        self.show_summary()

    def show_summary(self):
        """Display test results summary"""
        elapsed = time.time() - self.start_time

        print("\n" + "="*70)
        print("   Test Results Summary")
        print("="*70)
        print()

        passed = sum(1 for _, status, _ in self.results if status == "PASS")
        failed = sum(1 for _, status, _ in self.results if status == "FAIL")
        errors = sum(1 for _, status, _ in self.results if status == "ERROR")
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Time: {elapsed:.1f} seconds")
        print()

        if failed > 0 or errors > 0:
            print("FAILED TESTS:")
            for name, status, error in self.results:
                if status in ["FAIL", "ERROR"]:
                    print(f"  - {name}: {status}")
                    if error:
                        print(f"    {error}")

        print("\n" + "="*70)
        if failed == 0 and errors == 0:
            print("   ALL TESTS PASSED!")
        else:
            print("   TESTS FAILED - Review errors above")
        print("="*70)

        # Save results to file
        results_file = self.log_dir / f"test_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'time': elapsed,
                'results': [(n, s, e) for n, s, e in self.results]
            }, f, indent=2)

        print(f"\nResults saved to: {results_file}")


def main():
    """Main entry point"""
    runner = TestScenarioRunner()

    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if hasattr(runner, test_name):
            test_func = getattr(runner, test_name)
            runner.run_test(test_name, test_func)
        else:
            print(f"Unknown test: {test_name}")
            print("\nAvailable tests:")
            for attr in dir(runner):
                if attr.startswith('test_'):
                    print(f"  {attr}")
    else:
        # Run all tests
        runner.run_all_tests()


if __name__ == "__main__":
    main()
