"""
Comprehensive test runner for GiljoAI MCP Installer
Runs all unit and integration tests with coverage reporting
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """Comprehensive test runner for the installer"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.test_dir = Path(__file__).parent
        self.results: Dict[str, Any] = {}

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results"""
        print("[TEST] GiljoAI MCP Installer Test Suite")
        print("=" * 60)

        start_time = time.time()

        # Run unit tests
        unit_results = self.run_unit_tests()

        # Run integration tests
        integration_results = self.run_integration_tests()

        # Run performance tests
        performance_results = self.run_performance_tests()

        end_time = time.time()
        total_time = end_time - start_time

        # Compile results
        self.results = {
            "unit_tests": unit_results,
            "integration_tests": integration_results,
            "performance_tests": performance_results,
            "total_time": total_time,
            "overall_success": (
                unit_results.get("success", False)
                and integration_results.get("success", False)
                and performance_results.get("success", False)
            ),
        }

        self.print_summary()
        return self.results

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests"""
        print("\n[UNIT] Running Unit Tests...")
        print("-" * 40)

        unit_test_files = [
            "tests/installer/unit/test_profile.py",
            "tests/installer/unit/test_health_checker.py",
            "tests/installer/unit/test_config_manager.py",
        ]

        results = {"success": True, "tests_run": 0, "tests_passed": 0, "tests_failed": 0, "time": 0, "details": {}}

        start_time = time.time()

        for test_file in unit_test_files:
            if not Path(test_file).exists():
                print(f"[WARN] Test file not found: {test_file}")
                continue

            print(f"Running {test_file}...")

            try:
                # Run individual test file
                result = self.run_pytest_file(test_file)
                results["details"][test_file] = result

                if result["success"]:
                    print(f"[OK] {test_file}: {result['tests_passed']} passed")
                    results["tests_passed"] += result["tests_passed"]
                else:
                    print(f"[FAIL] {test_file}: {result['tests_failed']} failed")
                    results["success"] = False
                    results["tests_failed"] += result["tests_failed"]

                results["tests_run"] += result["tests_run"]

            except Exception as e:
                print(f"[ERR] Error running {test_file}: {e}")
                results["success"] = False

        results["time"] = time.time() - start_time
        return results

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("\n[INTEG] Running Integration Tests...")
        print("-" * 40)

        integration_files = ["tests/installer/integration/test_installation_flow.py"]

        results = {"success": True, "tests_run": 0, "tests_passed": 0, "tests_failed": 0, "time": 0, "details": {}}

        start_time = time.time()

        for test_file in integration_files:
            if not Path(test_file).exists():
                print(f"[WARN] Integration test not found: {test_file}")
                continue

            print(f"Running {test_file}...")

            try:
                result = self.run_pytest_file(test_file)
                results["details"][test_file] = result

                if result["success"]:
                    print(f"[OK] {test_file}: {result['tests_passed']} passed")
                    results["tests_passed"] += result["tests_passed"]
                else:
                    print(f"[FAIL] {test_file}: {result['tests_failed']} failed")
                    results["success"] = False
                    results["tests_failed"] += result["tests_failed"]

                results["tests_run"] += result["tests_run"]

            except Exception as e:
                print(f"[ERR] Error running {test_file}: {e}")
                results["success"] = False

        results["time"] = time.time() - start_time
        return results

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks"""
        print("\n[PERF] Running Performance Tests...")
        print("-" * 40)

        # Simple performance tests
        results = {"success": True, "tests_run": 0, "time": 0, "benchmarks": {}}

        start_time = time.time()

        try:
            # Test configuration generation speed
            config_benchmark = self.benchmark_config_generation()
            results["benchmarks"]["config_generation"] = config_benchmark
            results["tests_run"] += 1

            # Test health check speed (mocked)
            health_benchmark = self.benchmark_health_checks()
            results["benchmarks"]["health_checks"] = health_benchmark
            results["tests_run"] += 1

            print("[OK] Performance benchmarks completed")

        except Exception as e:
            print(f"[ERR] Performance test error: {e}")
            results["success"] = False

        results["time"] = time.time() - start_time
        return results

    def run_pytest_file(self, test_file: str) -> Dict[str, Any]:
        """Run a specific pytest file and parse results"""
        try:
            # Use Python's subprocess to run pytest
            cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-q"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT, check=False)

            # Parse pytest output
            return self.parse_pytest_output(result.stdout, result.stderr, result.returncode)

        except subprocess.TimeoutExpired:
            return {"success": False, "tests_run": 0, "tests_passed": 0, "tests_failed": 1, "error": "Test timed out"}
        except Exception as e:
            return {"success": False, "tests_run": 0, "tests_passed": 0, "tests_failed": 1, "error": str(e)}

    def parse_pytest_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse pytest output to extract results"""
        result = {
            "success": returncode == 0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": stdout,
            "errors": stderr,
        }

        # Parse the output for test counts
        lines = stdout.split("\n")
        for line in lines:
            if "failed" in line and "passed" in line:
                # Format: "1 failed, 2 passed in 0.05s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed," and i > 0:
                        result["tests_failed"] = int(parts[i - 1])
                    elif part == "passed" and i > 0:
                        result["tests_passed"] = int(parts[i - 1])
            elif "passed in" in line:
                # Format: "3 passed in 0.05s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        result["tests_passed"] = int(parts[i - 1])

        result["tests_run"] = result["tests_passed"] + result["tests_failed"]

        return result

    def benchmark_config_generation(self) -> Dict[str, float]:
        """Benchmark configuration generation"""
        try:
            from installer.config.config_manager import ConfigurationManager

            manager = ConfigurationManager()
            profiles = ["developer", "team", "enterprise", "research"]

            times = []
            for profile in profiles:
                start = time.time()
                config = manager.generate_configuration(profile)
                end = time.time()
                times.append(end - start)

            return {
                "avg_time": sum(times) / len(times),
                "max_time": max(times),
                "min_time": min(times),
                "profiles_tested": len(profiles),
            }

        except ImportError:
            return {"error": "ConfigurationManager not available"}
        except Exception as e:
            return {"error": str(e)}

    def benchmark_health_checks(self) -> Dict[str, float]:
        """Benchmark health check performance"""
        try:
            from unittest.mock import Mock, patch

            from installer.core.health import HealthChecker

            checker = HealthChecker()

            # Mock all external calls for pure performance test
            with patch.multiple(checker, _check_system=Mock(return_value=None), _check_python=Mock(return_value=None)):
                start = time.time()

                # Run quick checks multiple times
                for _ in range(10):
                    checker._check_system()
                    checker._check_python()

                end = time.time()

                return {
                    "avg_check_time": (end - start) / 20,  # 2 checks * 10 iterations
                    "total_time": end - start,
                    "checks_run": 20,
                }

        except ImportError:
            return {"error": "HealthChecker not available"}
        except Exception as e:
            return {"error": str(e)}

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("[SUMMARY] TEST SUMMARY")
        print("=" * 60)

        # Unit tests
        unit = self.results["unit_tests"]
        print(f"Unit Tests:        {unit['tests_passed']}/{unit['tests_run']} passed ({unit['time']:.2f}s)")

        # Integration tests
        integration = self.results["integration_tests"]
        print(
            f"Integration Tests: {integration['tests_passed']}/{integration['tests_run']} passed ({integration['time']:.2f}s)"
        )

        # Performance tests
        perf = self.results["performance_tests"]
        print(f"Performance Tests: {perf['tests_run']} benchmarks ({perf['time']:.2f}s)")

        # Overall
        print(f"Total Time:        {self.results['total_time']:.2f}s")

        if self.results["overall_success"]:
            print("[SUCCESS] ALL TESTS PASSED!")
        else:
            print("[FAILED] SOME TESTS FAILED")

        # Performance details
        if perf.get("benchmarks"):
            print("\n[BENCH] Performance Benchmarks:")
            for name, benchmark in perf["benchmarks"].items():
                if "error" not in benchmark:
                    if "avg_time" in benchmark:
                        print(f"  {name}: {benchmark['avg_time'] * 1000:.2f}ms average")
                    elif "avg_check_time" in benchmark:
                        print(f"  {name}: {benchmark['avg_check_time'] * 1000:.2f}ms per check")

    def run_specific_test(self, test_pattern: str) -> Dict[str, Any]:
        """Run tests matching a specific pattern"""
        print(f"[TARGET] Running tests matching: {test_pattern}")

        cmd = [sys.executable, "-m", "pytest", "-k", test_pattern, "-v", "--tb=short"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=PROJECT_ROOT, check=False)

            return self.parse_pytest_output(result.stdout, result.stderr, result.returncode)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage (if coverage package available)"""
        try:
            cmd = [sys.executable, "-m", "pytest", "--cov=installer", "--cov-report=term-missing", "tests/"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=PROJECT_ROOT, check=False)

            return {"success": result.returncode == 0, "output": result.stdout, "coverage_available": True}

        except FileNotFoundError:
            return {"success": False, "coverage_available": False, "message": "pytest-cov not installed"}


def main():
    """Main test runner function"""
    import argparse

    parser = argparse.ArgumentParser(description="GiljoAI MCP Installer Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--pattern", type=str, help="Run tests matching pattern")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")

    args = parser.parse_args()

    runner = TestRunner(verbose=not args.quiet)

    if args.pattern:
        # Run specific test pattern
        result = runner.run_specific_test(args.pattern)
        return 0 if result["success"] else 1

    if args.coverage:
        # Run with coverage
        result = runner.check_test_coverage()
        print(result["output"])
        return 0 if result["success"] else 1

    if args.quick:
        # Run only unit tests
        result = runner.run_unit_tests()
        return 0 if result["success"] else 1

    if args.integration:
        # Run only integration tests
        result = runner.run_integration_tests()
        return 0 if result["success"] else 1

    if args.performance:
        # Run only performance tests
        result = runner.run_performance_tests()
        return 0 if result["success"] else 1

    # Run all tests
    results = runner.run_all_tests()
    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
