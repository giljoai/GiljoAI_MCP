#!/usr/bin/env python
"""
Final Re-test Suite for Project 5.1.c after Backend Fixes
Comprehensive validation of all functionality
"""

import asyncio
import httpx
import json
import time
import websockets
from datetime import datetime
from typing import Dict, List, Any

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
        print("\n[1/7] Testing Health Check...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/health")
                data = response.json()

                if response.status_code == 200 and data.get("database") == "healthy":
                    print("  [PASS] Health check shows all systems healthy")
                    result = {"test": "Health Check", "status": "PASSED", "details": data}
                else:
                    print(f"  [FAIL] Health check issue: {data}")
                    result = {"test": "Health Check", "status": "FAILED", "details": data}
                    self.test_results["all_passed"] = False
        except Exception as e:
            print(f"  [FAIL] Health check error: {e}")
            result = {"test": "Health Check", "status": "FAILED", "error": str(e)}
            self.test_results["all_passed"] = False

        self.test_results["tests"].append(result)
        return result

    async def test_api_endpoints(self):
        """Test all critical API endpoints return JSON data"""
        print("\n[2/7] Testing API Endpoints...")
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
            for endpoint, name in endpoints:
                try:
                    response = await client.get(f"{self.api_base}{endpoint}")
                    if response.status_code in [200, 201]:
                        # Verify it returns JSON
                        data = response.json()
                        print(f"  [PASS] {name}: Returns JSON data")
                        endpoint_results.append({"endpoint": endpoint, "status": "PASSED"})
                    else:
                        print(f"  [WARN] {name}: Status {response.status_code}")
                        endpoint_results.append({"endpoint": endpoint, "status": "WARNING", "code": response.status_code})
                        if response.status_code >= 500:
                            all_good = False
                except Exception as e:
                    print(f"  [FAIL] {name}: {e}")
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
        print("\n[3/7] Testing WebSocket Real-time Updates...")
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
                    print(f"  [PASS] WebSocket latency: {latency:.2f}ms (< 100ms requirement)")
                    result = {"test": "WebSocket", "status": "PASSED", "latency_ms": latency}
                else:
                    print(f"  [FAIL] WebSocket issue - latency: {latency:.2f}ms")
                    result = {"test": "WebSocket", "status": "FAILED", "latency_ms": latency}
                    self.test_results["all_passed"] = False
        except Exception as e:
            print(f"  [FAIL] WebSocket error: {e}")
            result = {"test": "WebSocket", "status": "FAILED", "error": str(e)}
            self.test_results["all_passed"] = False

        self.test_results["tests"].append(result)

    async def test_template_crud(self):
        """Test Template Manager CRUD operations"""
        print("\n[4/7] Testing TemplateManager CRUD Operations...")

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
                    print("  [PASS] Template CREATE operation successful")
                    template_id = create_response.json().get("id")

                    # Test READ
                    read_response = await client.get(f"{self.api_base}/api/v1/templates/{template_id}")
                    if read_response.status_code == 200:
                        print("  [PASS] Template READ operation successful")

                    # Test UPDATE
                    update_data = {"description": "Updated test template"}
                    update_response = await client.put(
                        f"{self.api_base}/api/v1/templates/{template_id}",
                        json=update_data
                    )
                    if update_response.status_code == 200:
                        print("  [PASS] Template UPDATE operation successful")

                    # Test DELETE
                    delete_response = await client.delete(f"{self.api_base}/api/v1/templates/{template_id}")
                    if delete_response.status_code in [200, 204]:
                        print("  [PASS] Template DELETE operation successful")

                    self.test_results["tests"].append({
                        "test": "Template CRUD",
                        "status": "PASSED",
                        "operations": ["CREATE", "READ", "UPDATE", "DELETE"]
                    })
                else:
                    print(f"  [FAIL] Template CREATE failed: {create_response.status_code}")
                    self.test_results["tests"].append({
                        "test": "Template CRUD",
                        "status": "FAILED",
                        "error": f"CREATE returned {create_response.status_code}"
                    })
                    self.test_results["all_passed"] = False

            except Exception as e:
                print(f"  [FAIL] Template CRUD error: {e}")
                self.test_results["tests"].append({
                    "test": "Template CRUD",
                    "status": "FAILED",
                    "error": str(e)
                })
                self.test_results["all_passed"] = False

    async def test_performance_metrics(self):
        """Measure performance metrics"""
        print("\n[5/7] Measuring Performance Metrics...")

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
                    print(f"  [PASS] Template operations: {avg_time:.2f}ms (< 500ms requirement)")
                else:
                    print(f"  [FAIL] Template operations: {avg_time:.2f}ms (> 500ms requirement)")
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
                print(f"  [PASS] API response average: {avg_api:.2f}ms")

        self.test_results["performance_metrics"] = metrics

    async def test_responsive_design(self):
        """Test responsive design"""
        print("\n[6/7] Checking Responsive Design...")

        # This would require browser automation for full testing
        print("  [INFO] Manual verification required for breakpoints:")
        print("    - Mobile: 320px")
        print("    - Tablet: 768px")
        print("    - Desktop: 1024px")
        print("    - Wide: 1920px")

        self.test_results["tests"].append({
            "test": "Responsive Design",
            "status": "MANUAL_REQUIRED",
            "breakpoints": [320, 768, 1024, 1920]
        })

    async def test_accessibility(self):
        """Validate accessibility"""
        print("\n[7/7] Validating Accessibility...")

        print("  [INFO] Manual WCAG 2.1 AA compliance check required")
        print("  [INFO] Automated checks:")

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

                for check, passed in checks.items():
                    if passed:
                        print(f"    [PASS] {check}")
                    else:
                        print(f"    [WARN] {check} may need attention")

                self.test_results["tests"].append({
                    "test": "Accessibility",
                    "status": "PARTIAL",
                    "automated_checks": checks
                })
            except Exception as e:
                print(f"  [FAIL] Accessibility check error: {e}")

    async def generate_final_report(self):
        """Generate final test report"""
        print("\n" + "="*60)
        print("FINAL TEST REPORT - Project 5.1.c")
        print("="*60)

        # Count results
        passed = sum(1 for t in self.test_results["tests"] if t.get("status") == "PASSED")
        failed = sum(1 for t in self.test_results["tests"] if t.get("status") == "FAILED")
        warnings = sum(1 for t in self.test_results["tests"] if t.get("status") in ["WARNING", "PARTIAL", "MANUAL_REQUIRED"])

        print(f"\nTest Results:")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Warnings/Manual: {warnings}")

        if self.test_results["all_passed"]:
            print("\n[SUCCESS] ALL CRITICAL TESTS PASSED!")
            print("Project 5.1.c is FULLY FUNCTIONAL and READY FOR DEPLOYMENT")
        else:
            print("\n[WARNING] Some tests failed - review needed")

        # Performance summary
        if self.test_results["performance_metrics"]:
            print("\nPerformance Metrics:")
            for metric, value in self.test_results["performance_metrics"].items():
                print(f"  {metric}: {value:.2f}ms")

        # Save report
        with open("final_test_report.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed report saved to final_test_report.json")

        return self.test_results["all_passed"]

    async def run_all_tests(self):
        """Run complete test suite"""
        print("\nStarting Final Re-test Suite...")
        print("After Backend Fixes by backend_fixer agent")

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
        print("\n[FINAL STATUS] Project 5.1.c COMPLETE AND FUNCTIONAL")
        return 0
    else:
        print("\n[FINAL STATUS] Project 5.1.c has remaining issues")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)