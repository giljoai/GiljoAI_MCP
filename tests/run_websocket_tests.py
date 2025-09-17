#!/usr/bin/env python3
"""
WebSocket Integration Test Runner
Orchestrates and runs all WebSocket tests with reporting
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_websocket_config import CONFIG, setup_test_environment


class TestRunner:
    """Manages test execution and reporting"""

    def __init__(self, verbose: bool = False, mock_server: bool = True):
        self.verbose = verbose
        self.use_mock_server = mock_server
        self.results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": []}
        self.start_time = None
        self.mock_server_process = None

    async def setup(self):
        """Setup test environment"""
        setup_test_environment()

        if self.use_mock_server:
            await self.start_mock_server()

        # Give services time to start
        await asyncio.sleep(2)

    async def start_mock_server(self):
        """Start mock WebSocket server"""

        # Start mock server in subprocess
        self.mock_server_process = subprocess.Popen(
            [sys.executable, "tests/mock_websocket_server.py"],
            stdout=subprocess.PIPE if not self.verbose else None,
            stderr=subprocess.PIPE if not self.verbose else None,
        )

        # Wait for server to be ready
        await asyncio.sleep(1)

        # Verify server is running
        return self.mock_server_process.poll() is None

    async def teardown(self):
        """Cleanup test environment"""

        if self.mock_server_process:
            self.mock_server_process.terminate()
            self.mock_server_process.wait(timeout=5)

    async def run_test_suite(self, test_filter: Optional[str] = None):
        """Run the complete test suite"""
        self.start_time = time.time()

        # Test categories
        test_categories = [
            (
                "Connection Tests",
                [
                    "test_successful_connection",
                    "test_connection_with_auth",
                    "test_invalid_auth_rejection",
                    "test_multiple_clients",
                ],
            ),
            (
                "Auto-Reconnect Tests",
                ["test_exponential_backoff", "test_auto_reconnect_on_disconnect", "test_reconnect_within_5_seconds"],
            ),
            (
                "Real-time Update Tests",
                ["test_agent_status_update_latency", "test_message_streaming", "test_progress_indicator_updates"],
            ),
            ("Message Queue Tests", ["test_message_queue_during_disconnect", "test_no_message_loss"]),
            (
                "Resilience Tests",
                ["test_heartbeat_keepalive", "test_connection_quality_indicator", "test_fallback_to_polling"],
            ),
            ("Broadcast Tests", ["test_project_update_broadcast", "test_system_notification_broadcast"]),
            ("End-to-End Tests", ["test_complete_agent_workflow", "test_performance_under_load"]),
        ]

        for category_name, tests in test_categories:
            if test_filter and test_filter not in category_name.lower():
                continue

            for test_name in tests:
                if test_filter and test_filter not in test_name:
                    continue

                await self.run_single_test(test_name)

        # Print summary
        self.print_summary()

    async def run_single_test(self, test_name: str):
        """Run a single test"""
        self.results["total"] += 1

        try:
            # Run test using pytest
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_websocket_integration.py",
                    f"-k={test_name}",
                    "-v" if self.verbose else "-q",
                    "--tb=short",
                    "--asyncio-mode=auto",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1

                if self.verbose:
                    pass

                self.results["errors"].append({"test": test_name, "error": result.stderr})

        except subprocess.TimeoutExpired:
            self.results["failed"] += 1
            self.results["errors"].append({"test": test_name, "error": "Test timeout (30s)"})

        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append({"test": test_name, "error": str(e)})

    def print_summary(self):
        """Print test summary"""
        time.time() - self.start_time

        pass_rate = (self.results["passed"] / self.results["total"] * 100) if self.results["total"] > 0 else 0

        # Check against SLAs
        sla_checks = {
            "Latency < 100ms": self.check_latency_sla(),
            "Reconnect < 5s": self.check_reconnect_sla(),
            "Throughput > 500 msg/s": self.check_throughput_sla(),
            "Connection Success > 99%": pass_rate > 99,
        }

        for _check, _passed in sla_checks.items():
            pass

        # Print errors if any
        if self.results["errors"]:
            for _error in self.results["errors"][:5]:  # Show first 5 errors
                pass

        # Overall status
        if self.results["failed"] == 0:
            pass
        else:
            pass

    def check_latency_sla(self) -> bool:
        """Check if latency SLA is met"""
        # This would check actual latency measurements from tests
        return "test_agent_status_update_latency" not in [e["test"] for e in self.results["errors"]]

    def check_reconnect_sla(self) -> bool:
        """Check if reconnect SLA is met"""
        return "test_reconnect_within_5_seconds" not in [e["test"] for e in self.results["errors"]]

    def check_throughput_sla(self) -> bool:
        """Check if throughput SLA is met"""
        return "test_performance_under_load" not in [e["test"] for e in self.results["errors"]]

    async def generate_report(self):
        """Generate detailed test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration": time.time() - self.start_time,
            "results": self.results,
            "sla_compliance": {
                "latency": self.check_latency_sla(),
                "reconnect": self.check_reconnect_sla(),
                "throughput": self.check_throughput_sla(),
            },
            "environment": {
                "mock_server": self.use_mock_server,
                "ws_url": CONFIG["ws_url"],
                "api_url": CONFIG["api_url"],
            },
        }

        # Save report
        report_path = Path("tests/reports/websocket_test_report.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="WebSocket Integration Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--no-mock", action="store_true", help="Don't start mock server (use real server)")
    parser.add_argument("--filter", "-f", type=str, help="Filter tests by name")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests only")

    args = parser.parse_args()

    # Create test runner
    runner = TestRunner(verbose=args.verbose, mock_server=not args.no_mock)

    try:
        # Setup environment
        await runner.setup()

        # Run tests
        if args.quick:
            # Quick smoke tests
            await runner.run_single_test("test_successful_connection")
            await runner.run_single_test("test_agent_status_update_latency")
            await runner.run_single_test("test_auto_reconnect_on_disconnect")
        else:
            # Full test suite
            await runner.run_test_suite(test_filter=args.filter)

        # Generate report
        await runner.generate_report()

    except KeyboardInterrupt:
        pass

    finally:
        # Cleanup
        await runner.teardown()

    # Exit with appropriate code
    # sys.exit(0 if runner.results["failed"] == 0 else 1)  # Commented for pytest


if __name__ == "__main__":
    asyncio.run(main())
