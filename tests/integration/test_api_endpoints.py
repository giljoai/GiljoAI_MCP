#!/usr/bin/env python
"""
Comprehensive API Endpoints Test Suite for GiljoAI MCP
Tests all REST API endpoints with performance metrics
"""

import asyncio
import sys
import time
from pathlib import Path


# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


from fastapi.testclient import TestClient

from api.app import create_app
from src.giljo_mcp.database import DatabaseManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class PerformanceMetrics:
    """Track performance metrics for API calls"""

    def __init__(self):
        self.metrics = {}

    def record(self, endpoint: str, method: str, duration: float, status: int):
        key = f"{method} {endpoint}"
        if key not in self.metrics:
            self.metrics[key] = {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "avg_time": 0,
                "status_codes": {},
            }

        m = self.metrics[key]
        m["count"] += 1
        m["total_time"] += duration
        m["min_time"] = min(m["min_time"], duration)
        m["max_time"] = max(m["max_time"], duration)
        m["avg_time"] = m["total_time"] / m["count"]
        m["status_codes"][status] = m["status_codes"].get(status, 0) + 1

    def print_summary(self):
        for _metrics in self.metrics.values():
            pass


class APITestSuite:
    """Comprehensive API endpoint testing"""

    def __init__(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.metrics = PerformanceMetrics()
        self.test_data = {}
        self.passed = 0
        self.failed = 0
        self.tests = []

    async def setup(self):
        """Initialize test environment"""

        # Initialize test database
        self.db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False), is_async=True)
        await self.db_manager.create_tables_async()

        # Store in app state
        self.app.state.api_state.db_manager = self.db_manager

    async def teardown(self):
        """Clean up test environment"""

        # Close database
        if self.db_manager:
            await self.db_manager.close_async()

        # Clean up test database file
        test_db = Path("test_api.db")
        if test_db.exists():
            test_db.unlink()

    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.tests.append({"name": test_name, "passed": passed, "details": details})

        if passed:
            self.passed += 1
            if details:
                pass
        else:
            self.failed += 1
            if details:
                pass

    def api_call(self, method: str, endpoint: str, **kwargs) -> tuple:
        """Make API call with metrics tracking"""
        start_time = time.time()

        if method == "GET":
            response = self.client.get(endpoint, **kwargs)
        elif method == "POST":
            response = self.client.post(endpoint, **kwargs)
        elif method == "PATCH":
            response = self.client.patch(endpoint, **kwargs)
        elif method == "DELETE":
            response = self.client.delete(endpoint, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        duration = time.time() - start_time
        self.metrics.record(endpoint, method, duration, response.status_code)

        return response, duration

    # Test Categories

    async def test_health_endpoints(self):
        """Test health check endpoints"""

        # Test root endpoint
        response, duration = self.api_call("GET", "/")
        self.record_test(
            "Root endpoint",
            response.status_code == 200,
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

        # Test health check
        response, duration = self.api_call("GET", "/health")
        self.record_test(
            "Health check endpoint",
            response.status_code == 200 and response.json()["status"] in ["healthy", "degraded"],
            f"Status: {response.json().get('status')}, Time: {duration * 1000:.2f}ms",
        )

    async def test_project_endpoints(self):
        """Test project management endpoints"""

        # Create project
        project_data = {
            "name": "Test Project",
            "mission": "Test mission for API validation",
            "agents": ["analyzer", "implementer"],
        }

        response, duration = self.api_call("POST", "/api/v1/projects/", json=project_data)
        self.record_test(
            "Create project",
            response.status_code == 200,
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

        if response.status_code == 200:
            self.test_data["project_id"] = response.json()["id"]

        # List projects
        response, duration = self.api_call("GET", "/api/v1/projects/")
        self.record_test(
            "List projects",
            response.status_code == 200 and isinstance(response.json(), list),
            f"Count: {len(response.json())}, Time: {duration * 1000:.2f}ms",
        )

        # Get specific project
        if "project_id" in self.test_data:
            response, duration = self.api_call("GET", f"/api/v1/projects/{self.test_data['project_id']}")
            self.record_test(
                "Get project details",
                response.status_code == 200,
                f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
            )

        # Update project
        if "project_id" in self.test_data:
            update_data = {"mission": "Updated mission"}
            response, duration = self.api_call(
                "PATCH", f"/api/v1/projects/{self.test_data['project_id']}", json=update_data
            )
            self.record_test(
                "Update project",
                response.status_code == 200,
                f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
            )

    async def test_agent_endpoints(self):
        """Test agent management endpoints"""

        if "project_id" not in self.test_data:
            return

        # Create agent
        agent_data = {
            "project_id": self.test_data["project_id"],
            "agent_name": "test_agent",
            "mission": "Test agent for API validation",
        }

        response, duration = self.api_call("POST", "/api/v1/agents/", json=agent_data)
        self.record_test(
            "Create agent",
            response.status_code == 200,
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

        # Get agent health
        response, duration = self.api_call("GET", "/api/v1/agents/test_agent/health")
        self.record_test(
            "Get agent health",
            response.status_code == 200,
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

    async def test_message_endpoints(self):
        """Test message management endpoints"""

        if "project_id" not in self.test_data:
            return

        # Send message
        message_data = {
            "to_agents": ["test_agent"],
            "content": "Test message content",
            "project_id": self.test_data["project_id"],
            "message_type": "direct",
            "priority": "high",
        }

        response, duration = self.api_call("POST", "/api/v1/messages/send", json=message_data)
        self.record_test(
            "Send message",
            response.status_code == 200,
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

        if response.status_code == 200:
            self.test_data["message_id"] = response.json()["id"]

        # Get messages
        response, duration = self.api_call(
            "GET", "/api/v1/messages/test_agent", params={"project_id": self.test_data["project_id"]}
        )
        self.record_test(
            "Get messages for agent",
            response.status_code == 200 and isinstance(response.json(), list),
            f"Count: {len(response.json())}, Time: {duration * 1000:.2f}ms",
        )

        # Acknowledge message
        if "message_id" in self.test_data:
            response, duration = self.api_call(
                "POST",
                f"/api/v1/messages/{self.test_data['message_id']}/acknowledge",
                params={"agent_name": "test_agent"},
            )
            self.record_test(
                "Acknowledge message",
                response.status_code == 200,
                f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
            )

    async def test_context_endpoints(self):
        """Test context and vision endpoints"""

        # Get context index
        response, duration = self.api_call("GET", "/api/v1/context/index")
        self.record_test(
            "Get context index",
            response.status_code in [200, 404],  # 404 is ok if no context
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

        # Get vision document
        response, duration = self.api_call("GET", "/api/v1/context/vision", params={"part": 1, "max_tokens": 1000})
        self.record_test(
            "Get vision document",
            response.status_code in [200, 404],  # 404 is ok if no vision
            f"Status: {response.status_code}, Time: {duration * 1000:.2f}ms",
        )

    async def test_error_handling(self):
        """Test error handling and validation"""

        # Test 404 for non-existent project
        response, duration = self.api_call("GET", "/api/v1/projects/non-existent-id")
        self.record_test("404 for non-existent project", response.status_code == 404, f"Status: {response.status_code}")

        # Test validation error
        response, duration = self.api_call("POST", "/api/v1/projects/", json={})
        self.record_test(
            "Validation error for missing fields", response.status_code == 422, f"Status: {response.status_code}"
        )

        # Test method not allowed
        response, _duration = self.api_call("POST", "/api/v1/projects/list")
        self.record_test("Method not allowed", response.status_code in [404, 405], f"Status: {response.status_code}")

    async def test_performance_targets(self):
        """Test performance against vision document targets"""

        # Target: API responses < 100ms
        fast_endpoints = ["/", "/health"]
        for endpoint in fast_endpoints:
            response, duration = self.api_call("GET", endpoint)
            self.record_test(f"Performance {endpoint} < 100ms", duration < 0.1, f"Time: {duration * 1000:.2f}ms")

        # Target: Database operations < 20ms
        if "project_id" in self.test_data:
            _response, duration = self.api_call("GET", f"/api/v1/projects/{self.test_data['project_id']}")
            self.record_test("Database query < 20ms", duration < 0.02, f"Time: {duration * 1000:.2f}ms (Target: <20ms)")

    async def run_all_tests(self):
        """Run complete test suite"""

        await self.setup()

        try:
            # Run test categories
            await self.test_health_endpoints()
            await self.test_project_endpoints()
            await self.test_agent_endpoints()
            await self.test_message_endpoints()
            await self.test_context_endpoints()
            await self.test_error_handling()
            await self.test_performance_targets()

            # Print results
            self.print_results()
            self.metrics.print_summary()

        finally:
            await self.teardown()

    def print_results(self):
        """Print test results summary"""

        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        if self.failed > 0:
            for test in self.tests:
                if not test["passed"]:
                    pass

        # Overall status
        if pass_rate >= 90 or pass_rate >= 75:
            pass
        else:
            pass


async def main():
    """Main test runner"""
    suite = APITestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
