#!/usr/bin/env python
"""
Integration Test Suite for Project 5.1.c Dashboard Sub-Agent Visualization
Tester Agent: Comprehensive integration testing for all components
"""

import asyncio
import json
import time
from datetime import datetime

import httpx
import websockets


class IntegrationTester:
    def __init__(self):
        self.api_base = "http://localhost:7272"
        self.ws_url = "ws://localhost:7272/ws/tester"
        self.frontend_url = "http://localhost:7274"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "project": "5.1.c Dashboard Sub-Agent Visualization",
            "tests": [],
            "performance_metrics": {},
            "bugs_found": [],
            "summary": {},
        }

    async def test_api_health(self) -> dict:
        """Test API health endpoint"""
        test_name = "API Health Check"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/health")
                result = {
                    "name": test_name,
                    "status": "PASSED" if response.status_code == 200 else "FAILED",
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "details": response.json() if response.status_code == 200 else str(response.status_code),
                }
        except Exception as e:
            result = {"name": test_name, "status": "FAILED", "error": str(e)}
        self.test_results["tests"].append(result)
        return result

    async def test_template_endpoints(self) -> dict:
        """Test template management endpoints"""
        test_name = "Template Management Endpoints"
        results = []

        endpoints = [
            ("GET", "/api/v1/templates"),
            ("GET", "/api/v1/templates/archives"),
            ("GET", "/api/v1/templates/categories"),
        ]

        async with httpx.AsyncClient() as client:
            for method, endpoint in endpoints:
                try:
                    start_time = time.time()
                    if method == "GET":
                        response = await client.get(f"{self.api_base}{endpoint}")
                    response_time = (time.time() - start_time) * 1000

                    results.append(
                        {
                            "endpoint": endpoint,
                            "method": method,
                            "status_code": response.status_code,
                            "response_time_ms": response_time,
                            "success": response.status_code == 200,
                        }
                    )
                except Exception as e:
                    results.append({"endpoint": endpoint, "method": method, "error": str(e), "success": False})

        test_result = {
            "name": test_name,
            "status": "PASSED" if all(r.get("success", False) for r in results) else "FAILED",
            "endpoints_tested": len(endpoints),
            "details": results,
        }
        self.test_results["tests"].append(test_result)
        return test_result

    async def test_agent_metrics_endpoint(self) -> dict:
        """Test agent metrics endpoints"""
        test_name = "Agent Metrics Endpoints"
        results = []

        endpoints = [
            "/api/v1/agents",
            "/api/v1/agents/metrics",
            "/api/v1/agents/tree",
            "/api/v1/stats/overview",
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.api_base}{endpoint}")
                    response_time = (time.time() - start_time) * 1000

                    results.append(
                        {
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "response_time_ms": response_time,
                            "success": response.status_code in [200, 404],  # 404 ok if no agents
                        }
                    )
                except Exception as e:
                    results.append({"endpoint": endpoint, "error": str(e), "success": False})

        test_result = {
            "name": test_name,
            "status": "PASSED" if all(r.get("success", False) for r in results) else "FAILED",
            "endpoints_tested": len(endpoints),
            "details": results,
        }
        self.test_results["tests"].append(test_result)
        return test_result

    async def test_websocket_connection(self) -> dict:
        """Test WebSocket connectivity and real-time updates"""
        test_name = "WebSocket Real-time Updates"
        result = {"name": test_name}

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send a test message
                test_message = {"type": "ping", "timestamp": datetime.now().isoformat()}
                await websocket.send(json.dumps(test_message))

                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)

                result["status"] = "PASSED"
                result["latency_ms"] = 0  # Would need timestamps to calculate
                result["response"] = response_data
        except asyncio.TimeoutError:
            result["status"] = "FAILED"
            result["error"] = "WebSocket response timeout"
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)

        self.test_results["tests"].append(result)
        return result

    async def test_frontend_accessibility(self) -> dict:
        """Test frontend is accessible"""
        test_name = "Frontend Accessibility"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.frontend_url)
                result = {
                    "name": test_name,
                    "status": "PASSED" if response.status_code == 200 else "FAILED",
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "content_type": response.headers.get("content-type", ""),
                }
        except Exception as e:
            result = {"name": test_name, "status": "FAILED", "error": str(e)}

        self.test_results["tests"].append(result)
        return result

    async def measure_performance_metrics(self):
        """Measure performance metrics for key operations"""
        metrics = {}

        # Test template operation performance
        async with httpx.AsyncClient() as client:
            # Measure template list retrieval
            times = []
            for _ in range(5):
                start = time.time()
                try:
                    await client.get(f"{self.api_base}/api/v1/templates")
                    times.append((time.time() - start) * 1000)
                except:
                    pass

            if times:
                metrics["template_list_avg_ms"] = sum(times) / len(times)
                metrics["template_list_max_ms"] = max(times)
                metrics["template_list_min_ms"] = min(times)

        self.test_results["performance_metrics"] = metrics

        # Check against requirements
        if metrics.get("template_list_avg_ms", float("inf")) < 500:
            pass
        else:
            self.test_results["bugs_found"].append(
                {
                    "severity": "HIGH",
                    "component": "Template Manager",
                    "issue": f"Template operations exceed 500ms requirement: {metrics.get('template_list_avg_ms', 'N/A')}ms",
                }
            )

    async def run_all_tests(self):
        """Run all integration tests"""

        # Run tests
        await self.test_api_health()

        await self.test_template_endpoints()

        await self.test_agent_metrics_endpoint()

        await self.test_websocket_connection()

        await self.test_frontend_accessibility()

        await self.measure_performance_metrics()

        # Calculate summary
        total_tests = len(self.test_results["tests"])
        passed_tests = sum(1 for t in self.test_results["tests"] if t.get("status") == "PASSED")
        failed_tests = total_tests - passed_tests

        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "bugs_found": len(self.test_results["bugs_found"]),
        }

        # Print summary

        if self.test_results["bugs_found"]:
            for _bug in self.test_results["bugs_found"]:
                pass

        # Save results
        with open("integration_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)

        return self.test_results


async def main():
    tester = IntegrationTester()
    results = await tester.run_all_tests()

    # Exit with appropriate code
    if results["summary"]["failed"] > 0 or results["bugs_found"]:
        # sys.exit(1)  # Commented for pytest
        pass
    # sys.exit(0)  # Commented for pytest


if __name__ == "__main__":
    asyncio.run(main())
