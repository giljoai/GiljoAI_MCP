"""
Performance Load Test Runner
Orchestrates all performance tests and generates comprehensive reports

This script runs the complete performance test suite and validates
production readiness for 100+ concurrent agents deployment.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import psutil
import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class PerformanceTestSuite:
    """Complete performance test suite runner"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.get_system_info(),
            "test_results": {},
            "performance_metrics": {},
            "production_readiness": {
                "agent_scalability": False,
                "message_throughput": False,
                "websocket_capacity": False,
                "tenant_isolation": False,
                "vision_processing": False,
                "database_performance": False,
                "overall_score": 0,
            },
            "recommendations": [],
        }

    def get_system_info(self) -> dict[str, Any]:
        """Capture system information for the test report"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_memory_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "python_version": sys.version,
            "platform": sys.platform,
            "process_id": os.getpid(),
        }

    async def run_test_module(self, module_name: str, test_filter: Optional[str] = None) -> dict[str, Any]:
        """Run a specific test module and capture results"""

        start_time = time.perf_counter()

        # Build pytest command
        cmd_args = [
            f"tests/performance/{module_name}",
            "-v",
            "-s",
            "--tb=short",
            "--json-report",
            f"--json-report-file=performance_{module_name}_report.json",
        ]

        if test_filter:
            cmd_args.extend(["-k", test_filter])

        # Run pytest
        exit_code = pytest.main(cmd_args)

        execution_time = (time.perf_counter() - start_time) * 1000

        # Load test results if available
        report_file = Path(f"performance_{module_name}_report.json")
        test_details = {}

        if report_file.exists():
            try:
                with open(report_file) as f:
                    test_details = json.load(f)
                report_file.unlink()  # Clean up
            except Exception:
                pass

        return {
            "module": module_name,
            "exit_code": exit_code,
            "execution_time_ms": execution_time,
            "status": "PASSED" if exit_code == 0 else "FAILED",
            "details": test_details,
        }

    async def run_concurrent_agent_tests(self) -> dict[str, Any]:
        """Run concurrent agent performance tests"""
        result = await self.run_test_module(
            "test_concurrent_agents.py", "test_concurrent_agent_spawning_100_production_requirement"
        )

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["agent_scalability"] = True
            self.results["performance_metrics"]["agent_spawning"] = {
                "100_agents_supported": True,
                "latency_requirement_met": True,
            }
        else:
            self.results["recommendations"].append(
                "CRITICAL: Agent scalability failed - optimize agent spawning for 100+ concurrent agents"
            )

        return result

    async def run_message_queue_tests(self) -> dict[str, Any]:
        """Run message queue performance tests"""
        result = await self.run_test_module("test_message_queue_load.py", "test_message_saturation_1000_messages")

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["message_throughput"] = True
            self.results["performance_metrics"]["message_queue"] = {
                "10k_messages_per_minute": True,
                "broadcast_to_100_agents": True,
            }
        else:
            self.results["recommendations"].append(
                "CRITICAL: Message queue throughput insufficient - optimize for 10,000+ messages/minute"
            )

        return result

    async def run_websocket_tests(self) -> dict[str, Any]:
        """Run WebSocket stress tests"""
        result = await self.run_test_module(
            "test_websocket_stress.py", "test_concurrent_websocket_connections_100_production_requirement"
        )

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["websocket_capacity"] = True
            self.results["performance_metrics"]["websocket"] = {
                "100_concurrent_connections": True,
                "real_time_latency": True,
            }
        else:
            self.results["recommendations"].append(
                "WebSocket capacity issue - optimize for 100+ concurrent connections"
            )

        return result

    async def run_multi_tenant_tests(self) -> dict[str, Any]:
        """Run multi-tenant isolation tests"""
        result = await self.run_test_module("test_multi_tenant_load.py", "test_five_tenant_concurrent_load")

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["tenant_isolation"] = True
            self.results["performance_metrics"]["multi_tenant"] = {
                "data_isolation_verified": True,
                "performance_isolation_verified": True,
            }
        else:
            self.results["recommendations"].append(
                "Multi-tenant isolation issues detected - ensure complete tenant separation"
            )

        return result

    async def run_vision_chunking_tests(self) -> dict[str, Any]:
        """Run vision document chunking tests"""
        result = await self.run_test_module("test_vision_chunking_load.py", "test_large_document_chunking_50k_tokens")

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["vision_processing"] = True
            self.results["performance_metrics"]["vision_chunking"] = {
                "50k_tokens_supported": True,
                "chunking_performance_acceptable": True,
            }
        else:
            self.results["recommendations"].append(
                "Vision document processing issues - optimize for 50K+ token documents"
            )

        return result

    async def run_database_tests(self) -> dict[str, Any]:
        """Run database performance tests"""
        result = await self.run_test_module(
            "test_database_benchmarks.py",
            "test_single_record_operations_latency or test_concurrent_database_operations",
        )

        # Validate production requirements
        if result["status"] == "PASSED":
            self.results["production_readiness"]["database_performance"] = True
            self.results["performance_metrics"]["database"] = {
                "sub_100ms_operations": True,
                "concurrent_load_supported": True,
            }
        else:
            self.results["recommendations"].append(
                "Database performance bottlenecks detected - optimize for sub-100ms operations"
            )

        return result

    async def run_complete_test_suite(self):
        """Run the complete performance test suite"""

        start_time = time.perf_counter()

        # Run all test modules
        test_modules = [
            ("Concurrent Agent Tests", self.run_concurrent_agent_tests()),
            ("Message Queue Tests", self.run_message_queue_tests()),
            ("WebSocket Stress Tests", self.run_websocket_tests()),
            ("Multi-Tenant Tests", self.run_multi_tenant_tests()),
            ("Vision Chunking Tests", self.run_vision_chunking_tests()),
            ("Database Benchmark Tests", self.run_database_tests()),
        ]

        # Execute all tests
        for test_name, test_coro in test_modules:
            try:
                result = await test_coro
                self.results["test_results"][test_name] = result

                if result["status"] == "PASSED":
                    pass
                else:
                    pass

            except Exception as e:
                self.results["test_results"][test_name] = {"status": "CRASHED", "error": str(e), "execution_time_ms": 0}

        total_time = (time.perf_counter() - start_time) * 1000

        # Calculate overall production readiness score
        readiness_checks = self.results["production_readiness"]
        passed_checks = sum(1 for check, passed in readiness_checks.items() if isinstance(passed, bool) and passed)
        total_checks = sum(1 for check, passed in readiness_checks.items() if isinstance(passed, bool))

        overall_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        self.results["production_readiness"]["overall_score"] = overall_score

        self.results["execution_summary"] = {
            "total_execution_time_ms": total_time,
            "total_execution_time_minutes": total_time / 60000,
            "tests_passed": sum(1 for r in self.results["test_results"].values() if r.get("status") == "PASSED"),
            "tests_failed": sum(1 for r in self.results["test_results"].values() if r.get("status") == "FAILED"),
            "tests_crashed": sum(1 for r in self.results["test_results"].values() if r.get("status") == "CRASHED"),
        }

        # Generate final report
        self.generate_final_report()

    def generate_final_report(self):
        """Generate comprehensive performance test report"""

        # System Information
        self.results["system_info"]

        # Execution Summary
        self.results["execution_summary"]

        # Production Readiness Assessment
        readiness = self.results["production_readiness"]

        # Performance Metrics
        for metrics in self.results["performance_metrics"].values():
            for _metric, _value in metrics.items():
                pass

        # Recommendations
        if self.results["recommendations"]:
            for _i, _rec in enumerate(self.results["recommendations"], 1):
                pass

        # Overall Assessment
        if readiness["overall_score"] >= 90 or readiness["overall_score"] >= 75 or readiness["overall_score"] >= 50:
            pass
        else:
            pass

        # Save detailed report to file
        report_file = Path("performance_test_report.json")
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Generate CSV summary for spreadsheet analysis
        self.generate_csv_summary()

    def generate_csv_summary(self):
        """Generate CSV summary for analysis"""
        import csv

        csv_file = Path("performance_summary.csv")

        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)

            # Headers
            writer.writerow(
                [
                    "Timestamp",
                    "Test Category",
                    "Status",
                    "Execution Time (ms)",
                    "Production Ready",
                    "Score",
                    "Recommendations",
                ]
            )

            # Data rows
            for test_name, result in self.results["test_results"].items():
                writer.writerow(
                    [
                        self.results["timestamp"],
                        test_name,
                        result.get("status", "UNKNOWN"),
                        result.get("execution_time_ms", 0),
                        "Yes" if self.results["production_readiness"]["overall_score"] >= 90 else "No",
                        f"{self.results['production_readiness']['overall_score']:.1f}%",
                        "; ".join(self.results["recommendations"][:2]),  # First 2 recommendations
                    ]
                )


async def main():
    """Main entry point for performance test suite"""
    import os

    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    # Create and run test suite
    test_suite = PerformanceTestSuite()
    await test_suite.run_complete_test_suite()


if __name__ == "__main__":
    # Ensure we're running in an async context
    asyncio.run(main())
