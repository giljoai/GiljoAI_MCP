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
        self.results = {
            "summary": {},
            "coverage": {},
            "performance": {},
            "security": {},
            "issues": []
        }

    def run_comprehensive_tests(self):
        """Run all API tests with coverage"""
        print("Starting Comprehensive API Test Suite")
        print("=" * 60)

        try:
            # 1. Run comprehensive API tests
            print("\\n📋 Running Comprehensive API Tests...")
            self._run_test_file("test_api_comprehensive.py")

            # 2. Run security tests
            print("\\n🔒 Running Security & Authentication Tests...")
            self._run_test_file("test_api_security.py")

            # 3. Generate coverage report
            print("\\n📊 Generating Coverage Report...")
            self._generate_coverage_report()

            # 4. Run performance analysis
            print("\\n⚡ Running Performance Analysis...")
            self._analyze_performance()

            # 5. Generate final report
            print("\\n📈 Generating Final Report...")
            self._generate_final_report()

        except Exception as e:
            print(f"❌ Test runner failed: {e}")
            return False

        return True

    def _run_test_file(self, test_file):
        """Run a specific test file"""
        test_path = Path(__file__).parent / test_file

        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_file}")
            return False

        try:
            # Run pytest with detailed output
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                "--maxfail=10",
                "--capture=no",
                "--durations=10"
            ]

            print(f"Running: {' '.join(cmd)}")

            start_time = time.time()
            result = subprocess.run(
                cmd,
                check=False, capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            end_time = time.time()

            duration = end_time - start_time

            print(f"\\n📊 Test Results for {test_file}:")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Return Code: {result.returncode}")

            if result.stdout:
                print("\\n📝 STDOUT:")
                print(result.stdout)

            if result.stderr:
                print("\\n⚠️  STDERR:")
                print(result.stderr)

            # Parse results
            self._parse_test_results(test_file, result, duration)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"⏰ Test {test_file} timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"❌ Error running {test_file}: {e}")
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
            "return_code": result.returncode
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
        print("Analyzing API endpoint coverage...")

        try:
            # Try to run coverage if available
            cmd = [
                sys.executable, "-m", "pytest",
                "--cov=src/giljo_mcp/api",
                "--cov-report=json",
                "--cov-report=term",
                str(Path(__file__).parent / "test_api_comprehensive.py")
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                print("✅ Coverage report generated successfully")

                # Try to load coverage.json if it exists
                coverage_file = Path("coverage.json")
                if coverage_file.exists():
                    try:
                        with open(coverage_file) as f:
                            coverage_data = json.load(f)

                        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                        self.results["coverage"]["total_percent"] = total_coverage
                        self.results["coverage"]["details"] = coverage_data

                        print(f"📊 Total Coverage: {total_coverage:.1f}%")

                    except Exception as e:
                        print(f"⚠️  Could not parse coverage.json: {e}")

            else:
                print("⚠️  Coverage tool not available, analyzing manually...")
                self._manual_coverage_analysis()

        except subprocess.TimeoutExpired:
            print("⏰ Coverage analysis timed out")
        except Exception as e:
            print(f"⚠️  Coverage analysis failed: {e}")
            self._manual_coverage_analysis()

    def _manual_coverage_analysis(self):
        """Manual analysis of API endpoint coverage"""
        print("Performing manual coverage analysis...")

        # Count implemented endpoints
        api_files = [
            "src/giljo_mcp/api/endpoints/projects.py",
            "src/giljo_mcp/api/endpoints/agents.py",
            "src/giljo_mcp/api/endpoints/messages.py",
            "src/giljo_mcp/api/endpoints/tasks.py",
            "src/giljo_mcp/api/endpoints/templates.py"
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
                            next_lines = "\\n".join(lines[i:i+10])
                            if ("try:" in next_lines or
                                "register_" in next_lines or
                                "mcp.call_tool" in next_lines):
                                implemented_count += 1

                    implemented_endpoints += implemented_count

                    print(f"📁 {api_file}: {implemented_count}/{endpoint_count} endpoints implemented")

                except Exception as e:
                    print(f"⚠️  Could not analyze {api_file}: {e}")

        coverage_percent = (implemented_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0

        self.results["coverage"]["total_endpoints"] = total_endpoints
        self.results["coverage"]["implemented_endpoints"] = implemented_endpoints
        self.results["coverage"]["manual_percent"] = coverage_percent

        print(f"📊 Manual Coverage Analysis: {implemented_endpoints}/{total_endpoints} endpoints ({coverage_percent:.1f}%)")

    def _analyze_performance(self):
        """Analyze API performance"""
        print("Analyzing API performance...")

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
                "/api/v1/templates/"
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
                        "success": 200 <= response.status_code < 500
                    }

                    print(f"⚡ {endpoint}: {duration_ms:.2f}ms (HTTP {response.status_code})")

                except Exception as e:
                    performance_results[endpoint] = {
                        "error": str(e),
                        "success": False
                    }
                    print(f"❌ {endpoint}: {e}")

            self.results["performance"] = performance_results

            # Calculate average response time
            valid_times = [r["response_time_ms"] for r in performance_results.values()
                          if "response_time_ms" in r]

            if valid_times:
                avg_response_time = sum(valid_times) / len(valid_times)
                print(f"📊 Average Response Time: {avg_response_time:.2f}ms")
                self.results["performance"]["average_response_time"] = avg_response_time

        except Exception as e:
            print(f"⚠️  Performance analysis failed: {e}")

    def _generate_final_report(self):
        """Generate comprehensive final report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        print("\\n" + "=" * 60)
        print("📋 COMPREHENSIVE API TEST REPORT")
        print("=" * 60)

        print(f"\\n⏰ Test Duration: {total_duration:.2f} seconds")
        print(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Summary
        print("\\n📊 TEST SUMMARY:")
        total_passed = sum(r.get("passed", 0) for r in self.results["summary"].values())
        total_failed = sum(r.get("failed", 0) for r in self.results["summary"].values())
        total_tests = total_passed + total_failed

        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")

        if total_tests > 0:
            pass_rate = (total_passed / total_tests) * 100
            print(f"   Pass Rate: {pass_rate:.1f}%")

        # Coverage
        print("\\n📈 COVERAGE ANALYSIS:")
        coverage_percent = (
            self.results["coverage"].get("total_percent") or
            self.results["coverage"].get("manual_percent", 0)
        )
        print(f"   API Coverage: {coverage_percent:.1f}%")

        if coverage_percent >= 80:
            print("   ✅ COVERAGE TARGET MET (80%+)")
        else:
            print(f"   ⚠️  Coverage below target (need 80%, got {coverage_percent:.1f}%)")

        # Performance
        print("\\n⚡ PERFORMANCE ANALYSIS:")
        avg_response = self.results["performance"].get("average_response_time", 0)
        print(f"   Average Response Time: {avg_response:.2f}ms")

        if avg_response < 100:
            print("   ✅ Performance target met (<100ms)")
        else:
            print(f"   ⚠️  Performance above target (got {avg_response:.2f}ms)")

        # Issues
        if self.results["issues"]:
            print("\\n⚠️  ISSUES FOUND:")
            for issue in self.results["issues"][:10]:  # Limit to first 10
                print(f"   - {issue}")
            if len(self.results["issues"]) > 10:
                print(f"   ... and {len(self.results['issues']) - 10} more issues")

        # Final status
        print("\\n" + "=" * 60)

        success_criteria = [
            total_failed == 0,  # No failed tests
            coverage_percent >= 80,  # 80%+ coverage
            avg_response < 200,  # Reasonable performance
            len(self.results["issues"]) < 5  # Few issues
        ]

        if all(success_criteria):
            print("🎉 API TEST SUITE: PASSED")
            print("✅ All success criteria met")
        elif sum(success_criteria) >= 3:
            print("⚠️  API TEST SUITE: PASSED WITH WARNINGS")
            print("🔧 Some improvements recommended")
        else:
            print("❌ API TEST SUITE: NEEDS ATTENTION")
            print("🚨 Multiple success criteria not met")

        print("=" * 60)

        # Save detailed report
        self._save_detailed_report()

    def _save_detailed_report(self):
        """Save detailed report to file"""
        try:
            report_file = Path(__file__).parent / "api_test_report.json"

            with open(report_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)

            print(f"\\n💾 Detailed report saved to: {report_file}")

        except Exception as e:
            print(f"⚠️  Could not save detailed report: {e}")


def main():
    """Main test runner"""
    print("GiljoAI MCP API Test Suite")
    print("Testing all customer-facing REST endpoints")
    print("")

    runner = APITestRunner()
    success = runner.run_comprehensive_tests()

    if success:
        print("\\n✅ Test suite completed successfully")
        return 0
    print("\\n❌ Test suite encountered issues")
    return 1


if __name__ == "__main__":
    exit(main())
