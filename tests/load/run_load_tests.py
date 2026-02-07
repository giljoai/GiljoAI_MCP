#!/usr/bin/env python3
"""
Load Test Runner for GiljoAI MCP

Orchestrates load test scenarios and generates comprehensive reports.

Usage:
    # Run all scenarios
    python tests/load/run_load_tests.py --all

    # Run specific scenario
    python tests/load/run_load_tests.py --scenario normal_load

    # Run against specific host
    python tests/load/run_load_tests.py --all --host http://192.168.1.100:7272
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class LoadTestRunner:
    """
    Run load tests and generate comprehensive reports.
    """

    def __init__(self, host: str = "http://localhost:7272"):
        self.host = host
        self.results_dir = Path("tests/load/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_scenario(
        self,
        name: str,
        users: int,
        spawn_rate: int,
        duration: str,
        tags: Optional[List[str]] = None,
        locustfile: str = "tests/load/locustfile.py",
    ) -> Dict:
        """
        Run a single load test scenario.

        Args:
            name: Scenario name
            users: Number of concurrent users
            spawn_rate: Users spawned per second
            duration: Test duration (e.g., "5m", "2h")
            tags: Locust tags to run (optional)
            locustfile: Path to locustfile (default: main locustfile.py)

        Returns:
            Test results dictionary
        """
        print(f"\n{'=' * 60}")
        print(f"Running: {name}")
        print(f"Users: {users}, Spawn Rate: {spawn_rate}/s, Duration: {duration}")
        if tags:
            print(f"Tags: {', '.join(tags)}")
        print(f"{'=' * 60}\n")

        # Build locust command
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_report = str(self.results_dir / f"{name}_{timestamp}.html")
        csv_prefix = str(self.results_dir / f"{name}_{timestamp}")

        cmd = [
            "locust",
            "-f",
            locustfile,
            "--host",
            self.host,
            "--headless",
            "-u",
            str(users),
            "-r",
            str(spawn_rate),
            "-t",
            duration,
            "--html",
            html_report,
            "--csv",
            csv_prefix,
            "--csv-full-history",
            "--logfile",
            str(self.results_dir / f"{name}_{timestamp}.log"),
        ]

        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        # Run load test
        start_time = time.time()
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._parse_duration_to_seconds(duration) + 60,
                check=False,  # Extra timeout buffer
            )
            duration_seconds = time.time() - start_time
            success = process.returncode == 0

        except subprocess.TimeoutExpired:
            duration_seconds = time.time() - start_time
            success = False
            process = type("obj", (object,), {"returncode": -1, "stdout": "", "stderr": "Test timed out"})

        # Parse results
        results = {
            "name": name,
            "users": users,
            "spawn_rate": spawn_rate,
            "duration": duration,
            "duration_seconds": duration_seconds,
            "success": success,
            "timestamp": timestamp,
            "html_report": html_report,
            "csv_prefix": csv_prefix,
            "stdout": process.stdout[-5000:] if process.stdout else "",  # Last 5000 chars
            "stderr": process.stderr[-5000:] if process.stderr else "",
        }

        # Save results
        results_file = self.results_dir / f"{name}_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"\n{status}: {name}")
        print(f"Duration: {duration_seconds:.2f}s")
        print(f"Results saved: {results_file}")
        print(f"HTML Report: {html_report}")

        return results

    def _parse_duration_to_seconds(self, duration: str) -> int:
        """Parse duration string (e.g., '5m', '2h') to seconds."""
        duration = duration.strip()
        if duration.endswith("s"):
            return int(duration[:-1])
        if duration.endswith("m"):
            return int(duration[:-1]) * 60
        if duration.endswith("h"):
            return int(duration[:-1]) * 3600
        return 300  # Default 5 minutes

    def run_all_scenarios(self) -> List[Dict]:
        """
        Run all defined load test scenarios.

        Scenarios:
        1. Normal Load: 10 users, 5 minutes
        2. Peak Load: 50 users, 5 minutes
        3. Stress Test: 100 users, 2 minutes
        4. Spike Test: 100 users, 1 minute (rapid spawn)
        5. Soak Test: 20 users, 30 minutes
        """
        scenarios = [
            {"name": "normal_load", "users": 10, "spawn_rate": 2, "duration": "5m", "tags": ["normal_load"]},
            {"name": "peak_load", "users": 50, "spawn_rate": 10, "duration": "5m", "tags": ["peak_load"]},
            {"name": "stress_test", "users": 100, "spawn_rate": 10, "duration": "2m", "tags": ["stress_test"]},
            {
                "name": "spike_test",
                "users": 100,
                "spawn_rate": 50,  # Rapid spawn
                "duration": "1m",
                "tags": ["stress_test"],
            },
            {"name": "soak_test", "users": 20, "spawn_rate": 2, "duration": "30m", "tags": ["normal_load"]},
        ]

        results = []
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'#' * 60}")
            print(f"Scenario {i}/{len(scenarios)}")
            print(f"{'#' * 60}")

            result = self.run_scenario(**scenario)
            results.append(result)

            # Cool down between tests (except after last test)
            if i < len(scenarios):
                cooldown = 30
                print(f"\n⏸️  Cool down period: {cooldown}s")
                time.sleep(cooldown)

        return results

    def generate_summary_report(self, results: List[Dict]) -> str:
        """Generate comprehensive summary report from all test results."""
        report = f"""# GiljoAI MCP Load Test Summary Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Host**: {self.host}
**Total Scenarios**: {len(results)}
**Test Duration**: {sum(r["duration_seconds"] for r in results):.2f}s

---

## Executive Summary

"""

        # Calculate summary statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        failed_tests = total_tests - passed_tests

        report += f"""
### Test Results

- **Total Tests**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} {"❌" if failed_tests > 0 else ""}
- **Success Rate**: {(passed_tests / total_tests * 100):.1f}%

---

## Scenario Results

"""

        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report += f"""
### {result["name"]} {status}

- **Users**: {result["users"]} concurrent
- **Spawn Rate**: {result["spawn_rate"]} users/second
- **Duration**: {result["duration"]} (target)
- **Actual Duration**: {result["duration_seconds"]:.2f}s
- **HTML Report**: `{result["html_report"]}`
- **CSV Data**: `{result["csv_prefix"]}_*.csv`

"""

        # Add capacity analysis
        report += """
---

## Capacity Analysis

Based on load test results:

"""

        # Find maximum successful concurrent users
        successful_tests = [r for r in results if r["success"]]
        if successful_tests:
            max_users = max(r["users"] for r in successful_tests)
            report += f"✅ **Maximum Verified Capacity**: {max_users} concurrent users\n\n"
        else:
            report += "⚠️ **No successful tests** - system may be experiencing issues\n\n"

        # Identify bottlenecks
        report += """### Potential Bottlenecks

Review the following based on test results:

1. **Database Connections**
   - Monitor connection pool utilization during peak load
   - Check for connection timeout errors in logs

2. **CPU Usage**
   - Review CPU usage during stress tests
   - Identify single-threaded bottlenecks

3. **Memory**
   - Check memory growth during soak test
   - Look for memory leaks or cache issues

4. **WebSocket Connections**
   - Review WebSocket connection scaling
   - Check for connection limit issues

---

## Recommendations

"""

        if passed_tests == total_tests:
            report += """
✅ **All tests passed** - System performing well under load

**Next Steps**:
1. Review individual scenario reports for detailed metrics
2. Monitor resource utilization patterns
3. Establish performance baselines for future testing
4. Set up continuous load testing in CI/CD pipeline
"""
        elif passed_tests >= total_tests * 0.7:
            report += """
⚠️ **Partial Success** - Some tests failed

**Action Required**:
1. Review failed test logs for specific errors
2. Check system resource limits (CPU, memory, connections)
3. Investigate bottlenecks identified in logs
4. Consider infrastructure scaling if needed
"""
        else:
            report += """
❌ **System Under Stress** - Multiple tests failed

**Critical Actions**:
1. Review application logs immediately
2. Check database connection pool settings
3. Verify system resources are adequate
4. Investigate critical bottlenecks
5. Consider load testing with reduced users to establish baseline
"""

        report += """
---

## Detailed Reports

For detailed metrics, review the following files:

"""

        for result in results:
            report += f"- **{result['name']}**: `{result['html_report']}`\n"

        report += """
---

## Next Steps

1. **Optimize Bottlenecks**: Address identified performance issues
2. **Set Baselines**: Document current performance as baseline
3. **Monitor Production**: Set up monitoring based on test findings
4. **Continuous Testing**: Integrate load testing into CI/CD pipeline
5. **Capacity Planning**: Use results for infrastructure sizing

---

**Report End**
"""

        # Save report
        report_file = self.results_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w") as f:
            f.write(report)

        print(f"\n{'=' * 60}")
        print("📊 Summary Report Generated")
        print(f"{'=' * 60}")
        print(f"Report: {report_file}")
        print("\nView HTML reports:")
        for result in results:
            print(f"  - {result['name']}: {result['html_report']}")

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run load tests for GiljoAI MCP", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default="http://localhost:7272", help="Target host (default: http://localhost:7272)")
    parser.add_argument(
        "--scenario", help="Run specific scenario (normal_load, peak_load, stress_test, spike_test, soak_test)"
    )
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users (for --scenario)")
    parser.add_argument("--spawn-rate", type=int, default=2, help="User spawn rate per second (for --scenario)")
    parser.add_argument("--duration", default="5m", help="Test duration (for --scenario, e.g., 5m, 2h)")

    args = parser.parse_args()

    runner = LoadTestRunner(host=args.host)

    if args.all:
        print(f"\n{'#' * 60}")
        print("Running ALL Load Test Scenarios")
        print(f"Host: {args.host}")
        print(f"{'#' * 60}\n")

        results = runner.run_all_scenarios()
        runner.generate_summary_report(results)

    elif args.scenario:
        print(f"\n{'#' * 60}")
        print(f"Running Single Scenario: {args.scenario}")
        print(f"Host: {args.host}")
        print(f"{'#' * 60}\n")

        result = runner.run_scenario(
            name=args.scenario, users=args.users, spawn_rate=args.spawn_rate, duration=args.duration
        )

        print("\n✅ Scenario complete")
        print(f"View report: {result['html_report']}")

    else:
        print("Error: Please specify --all or --scenario <name>\n")
        print("Available scenarios:")
        print("  - normal_load    : 10 users, 5 minutes")
        print("  - peak_load      : 50 users, 5 minutes")
        print("  - stress_test    : 100 users, 2 minutes")
        print("  - spike_test     : 0→100→0 rapid scaling")
        print("  - soak_test      : 20 users, 30 minutes")
        print("\nExamples:")
        print("  python tests/load/run_load_tests.py --all")
        print("  python tests/load/run_load_tests.py --scenario normal_load")
        print("  python tests/load/run_load_tests.py --scenario stress_test --users 50")
        sys.exit(1)


if __name__ == "__main__":
    main()
