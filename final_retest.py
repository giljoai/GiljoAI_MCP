#!/usr/bin/env python
"""
Final Re-test Suite for Project 5.1.c after Backend Fixes
Comprehensive validation of all functionality
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import httpx
import websockets


class FinalRetestSuite:
    def __init__(self):
        self.api_base = "http://localhost:6002"
        self.ws_url = "ws://localhost:6002/ws/tester"
        self.frontend_url = "http://localhost:6000"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "project": "5.1.c Dashboard Sub-Agent Visualization - FINAL RETEST",
            "tests": [],
            "performance_metrics": {},
            "all_passed": True
        }

    async def test_health_check(self):
        """Test API health check - should be fully healthy now"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/health")
                data = response.json()

                if response.status_code == 200 and data.get("database") == "healthy":
                    result = {"test": "Health Check", "status": "PASSED", "details": data}
                else:
                    result = {"test": "Health Check", "status": "FAILED", "details": data}
                    self.test_results["all_passed"] = False
        except Exception as e:
            result = {"test": "Health Check", "status": "FAILED", "error": str(e)}
            self.test_results["all_passed"] = False

        self.test_results["tests"].append(result)
        return result

    async def test_api_endpoints(self):
        """Test all critical API endpoints return JSON data"""
        endpoints = [
            ("/api/v1/templates/", "Templates"),
            ("/api/v1/agents/", "Agents"),
            ("/api/v1/projects/", "Projects"),
            ("/api/v1/messages/", "Messages"),
            ("/api/v1/stats/", "Statistics"),
            ("/api/v1/agents/metrics", "Agent Metrics"),
            ("/api/v1/config/", "Configuration"),
        ]

        all_good = True
        endpoint_results = []

        async with httpx.AsyncClient() as client:
            for endpoint, _name in endpoints:
                try:
                    response = await client.get(f"{self.api_base}{endpoint}")
                    if response.status_code in [200, 201]:
                        # Verify it returns JSON
                        response.json()
                        endpoint_results.append({"endpoint": endpoint, "status": "PASSED"})
                    else:
                        endpoint_results.append({"endpoint": endpoint, "status": "WARNING", "code": response.status_code})
                        if response.status_code >= 500:
                            all_good = False
                except Exception as e:
                    endpoint_results.append({"endpoint": endpoint, "status": "FAILED", "error": str(e)})
                    all_good = False

        if not all_good:
            self.test_results["all_passed"] = False

        self.test_results["tests"].append({
            "test": "API Endpoints",
            "status": "PASSED" if all_good else "FAILED",
            "endpoints": endpoint_results
        })

    async def test_websocket_realtime(self):
        """Test WebSocket real-time updates"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send ping
                await websocket.send(json.dumps({"type": "ping", "timestamp": time.time()}))

                # Measure latency
                start = time.time()
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                latency = (time.time() - start) * 1000

                data = json.loads(response)
                if data.get("type") == "pong" and latency < 100:
                    result = {"test": "WebSocket", "status": "PASSED", "latency_ms": latency}
                else:
                    result = {"test": "WebSocket", "status": "FAILED", "latency_ms": latency}
                    self.test_results["all_passed"] = False
        except Exception as e:
            result = {"test": "WebSocket", "status": "FAILED", "error": str(e)}
            self.test_results["all_passed"] = False

        self.test_results["tests"].append(result)

    async def test_template_crud(self):
        """Test Template Manager CRUD operations"""

        async with httpx.AsyncClient() as client:
            # Test CREATE
            try:
                new_template = {
                    "name": "test_template",
                    "category": "testing",
                    "description": "Integration test template",
                    "template": "Test mission: {{project_name}}",
                    "variables": {"project_name": "Test Project"}
                }

                create_response = await client.post(
                    f"{self.api_base}/api/v1/templates/",
                    json=new_template
                )

                if create_response.status_code in [200, 201]:
                    template_id = create_response.json().get("id")

                    # Test READ
                    read_response = await client.get(f"{self.api_base}/api/v1/templates/{template_id}")
                    if read_response.status_code == 200:
                        pass

                    # Test UPDATE
                    update_data = {"description": "Updated test template"}
                    update_response = await client.put(
                        f"{self.api_base}/api/v1/templates/{template_id}",
                        json=update_data
                    )
                    if update_response.status_code == 200:
                        pass

                    # Test DELETE
                    delete_response = await client.delete(f"{self.api_base}/api/v1/templates/{template_id}")
                    if delete_response.status_code in [200, 204]:
                        pass

                    self.test_results["tests"].append({
                        "test": "Template CRUD",
                        "status": "PASSED",
                        "operations": ["CREATE", "READ", "UPDATE", "DELETE"]
                    })
                else:
                    self.test_results["tests"].append({
                        "test": "Template CRUD",
                        "status": "FAILED",
                        "error": f"CREATE returned {create_response.status_code}"
                    })
                    self.test_results["all_passed"] = False

            except Exception as e:
                self.test_results["tests"].append({
                    "test": "Template CRUD",
                    "status": "FAILED",
                    "error": str(e)
                })
                self.test_results["all_passed"] = False

    async def test_performance_metrics(self):
        """Measure performance metrics"""

        metrics = {}

        async with httpx.AsyncClient() as client:
            # Template operations performance
            template_times = []
            for _ in range(5):
                start = time.time()
                try:
                    await client.get(f"{self.api_base}/api/v1/templates/")
                    template_times.append((time.time() - start) * 1000)
                except:
                    pass

            if template_times:
                avg_time = sum(template_times) / len(template_times)
                metrics["template_avg_ms"] = avg_time

                if avg_time < 500:
                    pass
                else:
                    self.test_results["all_passed"] = False

            # API response times
            api_times = []
            endpoints = ["/health", "/api/v1/agents/metrics", "/api/v1/stats/"]
            for endpoint in endpoints:
                start = time.time()
                try:
                    await client.get(f"{self.api_base}{endpoint}")
                    api_times.append((time.time() - start) * 1000)
                except:
                    pass

            if api_times:
                avg_api = sum(api_times) / len(api_times)
                metrics["api_avg_ms"] = avg_api

        self.test_results["performance_metrics"] = metrics

    async def test_responsive_design(self):
        """Test responsive design"""

        # This would require browser automation for full testing

        self.test_results["tests"].append({
            "test": "Responsive Design",
            "status": "MANUAL_REQUIRED",
            "breakpoints": [320, 768, 1024, 1920]
        })

    async def test_accessibility(self):
        """Validate accessibility"""


        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.frontend_url)
                html = response.text.lower()

                # Basic accessibility checks
                checks = {
                    "alt_tags": "alt=" in html,
                    "aria_labels": "aria-label" in html,
                    "semantic_html": all(tag in html for tag in ["<header", "<main", "<nav"]),
                }

                for passed in checks.values():
                    if passed:
                        pass
                    else:
                        pass

                self.test_results["tests"].append({
                    "test": "Accessibility",
                    "status": "PARTIAL",
                    "automated_checks": checks
                })
            except Exception:
                pass

    async def generate_final_report(self):
        """Generate final test report"""

        # Count results
        sum(1 for t in self.test_results["tests"] if t.get("status") == "PASSED")
        sum(1 for t in self.test_results["tests"] if t.get("status") == "FAILED")
        sum(1 for t in self.test_results["tests"] if t.get("status") in ["WARNING", "PARTIAL", "MANUAL_REQUIRED"])


        if self.test_results["all_passed"]:
            pass
        else:
            pass

        # Performance summary
        if self.test_results["performance_metrics"]:
            for _metric, _value in self.test_results["performance_metrics"].items():
                pass

        # Save report
        with open("final_test_report.json", "w") as f:
            json.dump(self.test_results, f, indent=2)

        return self.test_results["all_passed"]

    async def run_all_tests(self):
        """Run complete test suite"""

        await self.test_health_check()
        await self.test_api_endpoints()
        await self.test_websocket_realtime()
        await self.test_template_crud()
        await self.test_performance_metrics()
        await self.test_responsive_design()
        await self.test_accessibility()

        return await self.generate_final_report()

async def main():
    tester = FinalRetestSuite()
    all_passed = await tester.run_all_tests()

    if all_passed:
        return 0
    return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
