#!/usr/bin/env python3
"""
CI Performance Report Generator
Generates comprehensive performance analysis from CI test results
"""

import json
import sys
from datetime import datetime
from pathlib import Path


class CIPerformanceAnalyzer:
    """Analyzes CI performance test results and generates reports"""

    def __init__(self):
        self.test_results = {}
        self.analysis = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0,
            "status": "UNKNOWN",
            "agent_scalability": False,
            "message_throughput": False,
            "websocket_capacity": False,
            "database_performance": False,
            "vision_processing": False,
            "critical_failures": [],
            "recommendations": [],
            "test_summary": {}
        }

    def load_test_results(self):
        """Load all available test result files"""
        result_files = [
            "baseline_report.json",
            "test_concurrent_agents_report.json",
            "test_message_queue_load_report.json",
            "test_database_benchmarks_report.json",
            "test_websocket_stress_report.json",
            "test_multi_tenant_load_report.json",
            "test_vision_chunking_load_report.json",
            "performance_test_report.json",
            "stress_test_report.json"
        ]

        for result_file in result_files:
            file_path = Path(result_file)
            if file_path.exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        self.test_results[result_file] = data
                        print(f"✅ Loaded {result_file}")
                except Exception as e:
                    print(f"⚠️  Failed to load {result_file}: {e}")

        # Also look for results in artifact directories
        artifact_dirs = [d for d in Path().iterdir() if d.is_dir() and "performance" in d.name]
        for artifact_dir in artifact_dirs:
            for result_file in artifact_dir.glob("*.json"):
                try:
                    with open(result_file) as f:
                        data = json.load(f)
                        self.test_results[result_file.name] = data
                        print(f"✅ Loaded {result_file}")
                except Exception as e:
                    print(f"⚠️  Failed to load {result_file}: {e}")

        print(f"\nTotal result files loaded: {len(self.test_results)}")

    def analyze_agent_performance(self):
        """Analyze agent scalability performance"""
        agent_tests = [
            "test_concurrent_agents_report.json",
            "baseline_report.json"
        ]

        passed_tests = 0
        total_tests = 0
        critical_issues = []

        for test_file in agent_tests:
            if test_file in self.test_results:
                data = self.test_results[test_file]

                # Check pytest results
                if "tests" in data:
                    for test in data["tests"]:
                        total_tests += 1
                        if test.get("outcome") == "passed":
                            passed_tests += 1
                        elif "100_production_requirement" in test.get("nodeid", ""):
                            critical_issues.append(f"Critical agent test failed: {test.get('nodeid')}")

                # Check for specific performance metrics in summary
                summary = data.get("summary", {})
                if summary.get("failed", 0) > 0:
                    failed_tests = [t for t in data.get("tests", []) if t.get("outcome") == "failed"]
                    for failed_test in failed_tests:
                        if "agent" in failed_test.get("nodeid", "").lower():
                            critical_issues.append(f"Agent performance test failed: {failed_test.get('nodeid')}")

        # Determine agent scalability status
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.analysis["agent_scalability"] = success_rate >= 80 and len(critical_issues) == 0

        if critical_issues:
            self.analysis["critical_failures"].extend(critical_issues)
            self.analysis["recommendations"].append(
                "CRITICAL: Agent scalability issues detected - optimize agent spawning for production loads"
            )

        self.analysis["test_summary"]["agent_tests"] = {
            "passed": passed_tests,
            "total": total_tests,
            "success_rate": success_rate,
            "critical_issues": len(critical_issues)
        }

    def analyze_message_performance(self):
        """Analyze message queue performance"""
        message_tests = ["test_message_queue_load_report.json"]

        passed_tests = 0
        total_tests = 0
        throughput_issues = []

        for test_file in message_tests:
            if test_file in self.test_results:
                data = self.test_results[test_file]

                if "tests" in data:
                    for test in data["tests"]:
                        total_tests += 1
                        if test.get("outcome") == "passed":
                            passed_tests += 1
                        elif "saturation" in test.get("nodeid", "") or "throughput" in test.get("nodeid", ""):
                            throughput_issues.append(f"Message throughput test failed: {test.get('nodeid')}")

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.analysis["message_throughput"] = success_rate >= 80 and len(throughput_issues) == 0

        if throughput_issues:
            self.analysis["critical_failures"].extend(throughput_issues)
            self.analysis["recommendations"].append(
                "Message queue performance insufficient - optimize for 10,000+ messages/minute"
            )

        self.analysis["test_summary"]["message_tests"] = {
            "passed": passed_tests,
            "total": total_tests,
            "success_rate": success_rate,
            "throughput_issues": len(throughput_issues)
        }

    def analyze_database_performance(self):
        """Analyze database performance"""
        db_tests = ["test_database_benchmarks_report.json"]

        passed_tests = 0
        total_tests = 0
        latency_issues = []

        for test_file in db_tests:
            if test_file in self.test_results:
                data = self.test_results[test_file]

                if "tests" in data:
                    for test in data["tests"]:
                        total_tests += 1
                        if test.get("outcome") == "passed":
                            passed_tests += 1
                        elif "latency" in test.get("nodeid", "") or "concurrent" in test.get("nodeid", ""):
                            latency_issues.append(f"Database performance test failed: {test.get('nodeid')}")

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.analysis["database_performance"] = success_rate >= 80 and len(latency_issues) == 0

        if latency_issues:
            self.analysis["critical_failures"].extend(latency_issues)
            self.analysis["recommendations"].append(
                "Database performance issues detected - optimize for sub-100ms operations"
            )

        self.analysis["test_summary"]["database_tests"] = {
            "passed": passed_tests,
            "total": total_tests,
            "success_rate": success_rate,
            "latency_issues": len(latency_issues)
        }

    def analyze_websocket_performance(self):
        """Analyze WebSocket performance"""
        ws_tests = ["test_websocket_stress_report.json"]

        passed_tests = 0
        total_tests = 0
        connection_issues = []

        for test_file in ws_tests:
            if test_file in self.test_results:
                data = self.test_results[test_file]

                if "tests" in data:
                    for test in data["tests"]:
                        total_tests += 1
                        if test.get("outcome") == "passed":
                            passed_tests += 1
                        elif "100" in test.get("nodeid", "") and "connection" in test.get("nodeid", ""):
                            connection_issues.append(f"WebSocket capacity test failed: {test.get('nodeid')}")

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.analysis["websocket_capacity"] = success_rate >= 70  # Lower threshold for WebSocket

        if connection_issues:
            self.analysis["recommendations"].append(
                "WebSocket capacity issues detected - optimize for 100+ concurrent connections"
            )

        self.analysis["test_summary"]["websocket_tests"] = {
            "passed": passed_tests,
            "total": total_tests,
            "success_rate": success_rate,
            "connection_issues": len(connection_issues)
        }

    def analyze_vision_performance(self):
        """Analyze vision document processing performance"""
        vision_tests = ["test_vision_chunking_load_report.json"]

        passed_tests = 0
        total_tests = 0
        chunking_issues = []

        for test_file in vision_tests:
            if test_file in self.test_results:
                data = self.test_results[test_file]

                if "tests" in data:
                    for test in data["tests"]:
                        total_tests += 1
                        if test.get("outcome") == "passed":
                            passed_tests += 1
                        elif "50k" in test.get("nodeid", "").lower():
                            chunking_issues.append(f"Vision processing test failed: {test.get('nodeid')}")

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.analysis["vision_processing"] = success_rate >= 80 and len(chunking_issues) == 0

        if chunking_issues:
            self.analysis["recommendations"].append(
                "Vision document processing issues - optimize for 50K+ token documents"
            )

        self.analysis["test_summary"]["vision_tests"] = {
            "passed": passed_tests,
            "total": total_tests,
            "success_rate": success_rate,
            "chunking_issues": len(chunking_issues)
        }

    def calculate_overall_score(self):
        """Calculate overall performance score"""
        components = {
            "agent_scalability": 30,  # 30% weight
            "message_throughput": 25,  # 25% weight
            "database_performance": 20,  # 20% weight
            "websocket_capacity": 15,   # 15% weight
            "vision_processing": 10     # 10% weight
        }

        total_score = 0
        for component, weight in components.items():
            if self.analysis[component]:
                total_score += weight

        self.analysis["overall_score"] = total_score

        # Determine status
        if total_score >= 90:
            self.analysis["status"] = "PRODUCTION_READY"
        elif total_score >= 75:
            self.analysis["status"] = "MOSTLY_READY"
        elif total_score >= 50:
            self.analysis["status"] = "NEEDS_IMPROVEMENT"
        else:
            self.analysis["status"] = "NOT_READY"

    def generate_html_report(self):
        """Generate HTML report for CI"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CI Performance Test Report</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
                .score-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .status-good {{ color: #27ae60; }}
                .status-poor {{ color: #e74c3c; }}
                .status-warning {{ color: #f39c12; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
                .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; }}
                .critical {{ border-left-color: #e74c3c; }}
                .warning {{ border-left-color: #f39c12; }}
                .good {{ border-left-color: #27ae60; }}
                .timestamp {{ color: #7f8c8d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 CI Performance Test Report</h1>
                    <p>Automated Performance Analysis</p>
                    <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
                </div>

                <div class="score-card">
                    <h2>Overall Performance Score</h2>
                    <div style="font-size: 48px; font-weight: bold;" class="status-{'good' if self.analysis['overall_score'] >= 75 else 'poor'}">
                        {self.analysis['overall_score']}%
                    </div>
                    <div style="font-size: 18px; margin-top: 10px;">
                        Status: <span class="status-{'good' if self.analysis['status'] in ['PRODUCTION_READY', 'MOSTLY_READY'] else 'poor'}">{self.analysis['status'].replace('_', ' ')}</span>
                    </div>
                </div>

                <div class="metric-grid">
                    <div class="metric-card {'good' if self.analysis['agent_scalability'] else 'critical'}">
                        <h3>Agent Scalability</h3>
                        <div>Status: {'✅ PASS' if self.analysis['agent_scalability'] else '❌ FAIL'}</div>
                        <div>Weight: 30%</div>
                    </div>
                    <div class="metric-card {'good' if self.analysis['message_throughput'] else 'critical'}">
                        <h3>Message Throughput</h3>
                        <div>Status: {'✅ PASS' if self.analysis['message_throughput'] else '❌ FAIL'}</div>
                        <div>Weight: 25%</div>
                    </div>
                    <div class="metric-card {'good' if self.analysis['database_performance'] else 'critical'}">
                        <h3>Database Performance</h3>
                        <div>Status: {'✅ PASS' if self.analysis['database_performance'] else '❌ FAIL'}</div>
                        <div>Weight: 20%</div>
                    </div>
                    <div class="metric-card {'good' if self.analysis['websocket_capacity'] else 'warning'}">
                        <h3>WebSocket Capacity</h3>
                        <div>Status: {'✅ PASS' if self.analysis['websocket_capacity'] else '⚠️ WARN'}</div>
                        <div>Weight: 15%</div>
                    </div>
                    <div class="metric-card {'good' if self.analysis['vision_processing'] else 'warning'}">
                        <h3>Vision Processing</h3>
                        <div>Status: {'✅ PASS' if self.analysis['vision_processing'] else '⚠️ WARN'}</div>
                        <div>Weight: 10%</div>
                    </div>
                </div>
        """

        # Add test summary
        if self.analysis["test_summary"]:
            html_content += """
                <div class="score-card">
                    <h2>Test Summary</h2>
                    <div class="metric-grid">
            """

            for test_type, summary in self.analysis["test_summary"].items():
                success_rate = summary.get("success_rate", 0)
                status_class = "good" if success_rate >= 80 else "warning" if success_rate >= 60 else "critical"

                html_content += f"""
                    <div class="metric-card {status_class}">
                        <h3>{test_type.replace('_', ' ').title()}</h3>
                        <div>Passed: {summary.get('passed', 0)}/{summary.get('total', 0)}</div>
                        <div>Success Rate: {success_rate:.1f}%</div>
                    </div>
                """

            html_content += "</div></div>"

        # Add recommendations
        if self.analysis["recommendations"]:
            html_content += """
                <div class="score-card">
                    <h2>Recommendations</h2>
                    <ul>
            """
            for rec in self.analysis["recommendations"]:
                html_content += f"<li>{rec}</li>"

            html_content += "</ul></div>"

        # Add critical failures
        if self.analysis["critical_failures"]:
            html_content += """
                <div class="score-card critical">
                    <h2>Critical Failures</h2>
                    <ul>
            """
            for failure in self.analysis["critical_failures"]:
                html_content += f"<li>{failure}</li>"

            html_content += "</ul></div>"

        html_content += """
            </div>
        </body>
        </html>
        """

        return html_content

    def run_analysis(self):
        """Run complete performance analysis"""
        print("🔍 Starting CI performance analysis...")

        # Load test results
        self.load_test_results()

        if not self.test_results:
            print("⚠️  No test results found. Creating minimal report.")
            self.analysis["status"] = "NO_DATA"
            self.analysis["recommendations"].append("No performance test data available")
        else:
            # Analyze each component
            self.analyze_agent_performance()
            self.analyze_message_performance()
            self.analyze_database_performance()
            self.analyze_websocket_performance()
            self.analyze_vision_performance()

            # Calculate overall score
            self.calculate_overall_score()

        # Generate reports
        html_report = self.generate_html_report()

        # Save HTML report
        with open("ci_performance_report.html", "w", encoding="utf-8") as f:
            f.write(html_report)

        # Save JSON analysis
        with open("ci_performance_analysis.json", "w") as f:
            json.dump(self.analysis, f, indent=2, default=str)

        print("\n✅ CI Performance Analysis Complete")
        print(f"   Overall Score: {self.analysis['overall_score']}%")
        print(f"   Status: {self.analysis['status']}")
        print(f"   Critical Failures: {len(self.analysis['critical_failures'])}")
        print(f"   Recommendations: {len(self.analysis['recommendations'])}")

        # Return exit code based on performance
        if self.analysis["overall_score"] < 50 or len(self.analysis["critical_failures"]) > 0:
            print("❌ Performance below acceptable threshold")
            return 1
        print("✅ Performance acceptable")
        return 0


def main():
    """Main entry point"""
    analyzer = CIPerformanceAnalyzer()
    exit_code = analyzer.run_analysis()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
