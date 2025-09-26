"""
API Test Runner with Coverage Reporting
Executes comprehensive API tests and generates coverage report
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class APITestRunner:
    """Comprehensive API test runner with coverage analysis"""

    def __init__(self):
        self.start_time = datetime.now()
        self.results = {"summary": {}, "coverage": {}, "performance": {}, "security": {}, "issues": []}

    def run_comprehensive_tests(self):
        """Run all API tests with coverage"""

        try:
            # 1. Run comprehensive API tests
            self._run_test_file("test_api_comprehensive.py")

            # 2. Run security tests
            self._run_test_file("test_api_security.py")

            # 3. Generate coverage report
            self._generate_coverage_report()

            # 4. Run performance analysis
            self._analyze_performance()

            # 5. Generate final report
            self._generate_final_report()

        except Exception:
            return False

        return True

    def _run_test_file(self, test_file):
        """Run a specific test file"""
        test_path = Path(__file__).parent / test_file

        if not test_path.exists():
            return False

        try:
            # Run pytest with detailed output
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                "--maxfail=10",
                "--capture=no",
                "--durations=10",
            ]

            start_time = time.time()
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            end_time = time.time()

            duration = end_time - start_time

            if result.stdout:
                pass

            if result.stderr:
                pass

            # Parse results
            self._parse_test_results(test_file, result, duration)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _parse_test_results(self, test_file, result, duration):
        """Parse test results from pytest output"""
        stdout = result.stdout

        # Count tests
        passed = stdout.count(" PASSED")
        failed = stdout.count(" FAILED")
        skipped = stdout.count(" SKIPPED")
        errors = stdout.count(" ERROR")

        self.results["summary"][test_file] = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "duration": duration,
            "return_code": result.returncode,
        }

        # Extract warnings and issues
        if "warning" in stdout.lower() or "error" in stdout.lower():
            lines = stdout.split("\\n")
            for line in lines:
                if any(keyword in line.lower() for keyword in ["warning", "error", "failed"]):
                    if line.strip():
                        self.results["issues"].append(f"{test_file}: {line.strip()}")

    def _generate_coverage_report(self):
        """Generate coverage report for API endpoints"""

        try:
            # Try to run coverage if available
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "--cov=src/giljo_mcp/api",
                "--cov-report=json",
                "--cov-report=term",
                str(Path(__file__).parent / "test_api_comprehensive.py"),
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Try to load coverage.json if it exists
                coverage_file = Path("coverage.json")
                if coverage_file.exists():
                    try:
                        with open(coverage_file) as f:
                            coverage_data = json.load(f)

                        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                        self.results["coverage"]["total_percent"] = total_coverage
                        self.results["coverage"]["details"] = coverage_data

                    except Exception:
                        pass

            else:
                self._manual_coverage_analysis()

        except subprocess.TimeoutExpired:
            pass
        except Exception:
            self._manual_coverage_analysis()

    def _manual_coverage_analysis(self):
        """Manual analysis of API endpoint coverage"""

        # Count implemented endpoints
        api_files = [
            "src/giljo_mcp/api/endpoints/projects.py",
            "src/giljo_mcp/api/endpoints/agents.py",
            "src/giljo_mcp/api/endpoints/messages.py",
            "src/giljo_mcp/api/endpoints/tasks.py",
            "src/giljo_mcp/api/endpoints/templates.py",
        ]

        total_endpoints = 0
        implemented_endpoints = 0

        for api_file in api_files:
            file_path = Path(__file__).parent.parent / api_file
            if file_path.exists():
                try:
                    with open(file_path) as f:
                        content = f.read()

                    # Count router decorators (endpoints)
                    endpoint_count = content.count("@router.")
                    total_endpoints += endpoint_count

                    # Count implemented endpoints (not just stubs)
                    implemented_count = 0
                    lines = content.split("\\n")
                    for i, line in enumerate(lines):
                        if "@router." in line and i + 5 < len(lines):
                            # Check if next few lines have actual implementation
                            next_lines = "\\n".join(lines[i : i + 10])
                            if "try:" in next_lines or "register_" in next_lines or "mcp.call_tool" in next_lines:
                                implemented_count += 1

                    implemented_endpoints += implemented_count

                except Exception:
                    pass

        coverage_percent = (implemented_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0

        self.results["coverage"]["total_endpoints"] = total_endpoints
        self.results["coverage"]["implemented_endpoints"] = implemented_endpoints
        self.results["coverage"]["manual_percent"] = coverage_percent

    def _analyze_performance(self):
        """Analyze API performance"""

        try:
            from fastapi.testclient import TestClient

            from src.giljo_mcp.api.app import create_app

            app = create_app()
            client = TestClient(app)

            # Test endpoint response times
            endpoints = [
                "/",
                "/health",
                "/api/v1/projects/",
                "/api/v1/agents/",
                "/api/v1/messages/",
                "/api/v1/tasks/",
                "/api/v1/templates/",
            ]

            performance_results = {}

            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = client.get(endpoint)
                    end_time = time.time()

                    duration_ms = (end_time - start_time) * 1000

                    performance_results[endpoint] = {
                        "response_time_ms": duration_ms,
                        "status_code": response.status_code,
                        "success": 200 <= response.status_code < 500,
                    }

                except Exception as e:
                    performance_results[endpoint] = {"error": str(e), "success": False}

            self.results["performance"] = performance_results

            # Calculate average response time
            valid_times = [r["response_time_ms"] for r in performance_results.values() if "response_time_ms" in r]

            if valid_times:
                avg_response_time = sum(valid_times) / len(valid_times)
                self.results["performance"]["average_response_time"] = avg_response_time

        except Exception:
            pass

    def _generate_final_report(self):
        """Generate comprehensive final report"""
        end_time = datetime.now()
        (end_time - self.start_time).total_seconds()

        # Summary
        total_passed = sum(r.get("passed", 0) for r in self.results["summary"].values())
        total_failed = sum(r.get("failed", 0) for r in self.results["summary"].values())
        total_tests = total_passed + total_failed

        if total_tests > 0:
            (total_passed / total_tests) * 100

        # Coverage
        coverage_percent = self.results["coverage"].get("total_percent") or self.results["coverage"].get(
            "manual_percent", 0
        )

        if coverage_percent >= 80:
            pass
        else:
            pass

        # Performance
        avg_response = self.results["performance"].get("average_response_time", 0)

        if avg_response < 100:
            pass
        else:
            pass

        # Issues
        if self.results["issues"]:
            for _issue in self.results["issues"][:10]:  # Limit to first 10
                pass
            if len(self.results["issues"]) > 10:
                pass

        # Final status

        success_criteria = [
            total_failed == 0,  # No failed tests
            coverage_percent >= 80,  # 80%+ coverage
            avg_response < 200,  # Reasonable performance
            len(self.results["issues"]) < 5,  # Few issues
        ]

        if all(success_criteria) or sum(success_criteria) >= 3:
            pass
        else:
            pass

        # Save detailed report
        self._save_detailed_report()

    def _save_detailed_report(self):
        """Save detailed report to file"""
        try:
            report_file = Path(__file__).parent / "api_test_report.json"

            with open(report_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)

        except Exception:
            pass


def main():
    """Main test runner"""

    runner = APITestRunner()
    success = runner.run_comprehensive_tests()

    if success:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
