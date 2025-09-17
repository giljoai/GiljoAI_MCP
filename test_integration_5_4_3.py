#!/usr/bin/env python
"""
Integration test for Project 5.4.3 - Production Code Unification Verification
Tests that frontend and backend integrate seamlessly without workarounds
"""

import asyncio
import logging
from datetime import datetime

import httpx


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_V1_PREFIX = "/api/v1"


class IntegrationTester:
    """Test all API integration points"""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)
        self.results = []
        self.test_project_id = None
        self.test_agent_id = None
        self.test_message_id = None

    async def test_health(self):
        """Test health endpoint"""
        try:
            response = await self.client.get("/health")
            success = response.status_code == 200
            self.results.append(
                {
                    "test": "Health Check",
                    "endpoint": "/health",
                    "status": response.status_code,
                    "success": success,
                }
            )
            return success
        except Exception as e:
            self.results.append({"test": "Health Check", "endpoint": "/health", "success": False, "error": str(e)})
            return False

    async def test_projects_crud(self):
        """Test project CRUD operations"""
        try:
            # Create project
            create_data = {"name": f"Integration Test {datetime.now()}", "mission": "Test API integration"}
            response = await self.client.post(f"{API_V1_PREFIX}/projects/", json=create_data)
            success = response.status_code == 200
            if success:
                self.test_project_id = response.json().get("id")
            self.results.append(
                {
                    "test": "Create Project",
                    "endpoint": f"{API_V1_PREFIX}/projects/",
                    "status": response.status_code,
                    "success": success,
                }
            )

            if self.test_project_id:
                # Get project
                response = await self.client.get(f"{API_V1_PREFIX}/projects/{self.test_project_id}")
                success = response.status_code == 200
                self.results.append(
                    {
                        "test": "Get Project",
                        "endpoint": f"{API_V1_PREFIX}/projects/{self.test_project_id}",
                        "status": response.status_code,
                        "success": success,
                    }
                )

                # List projects
                response = await self.client.get(f"{API_V1_PREFIX}/projects/")
                success = response.status_code == 200
                self.results.append(
                    {
                        "test": "List Projects",
                        "endpoint": f"{API_V1_PREFIX}/projects/",
                        "status": response.status_code,
                        "success": success,
                    }
                )

                # Update project
                update_data = {"mission": "Updated mission"}
                response = await self.client.patch(f"{API_V1_PREFIX}/projects/{self.test_project_id}", json=update_data)
                success = response.status_code == 200
                self.results.append(
                    {
                        "test": "Update Project",
                        "endpoint": f"{API_V1_PREFIX}/projects/{self.test_project_id}",
                        "status": response.status_code,
                        "success": success,
                    }
                )

                # Close project (using DELETE as per backend implementation)
                response = await self.client.delete(
                    f"{API_V1_PREFIX}/projects/{self.test_project_id}", params={"summary": "Test complete"}
                )
                success = response.status_code == 200
                self.results.append(
                    {
                        "test": "Close Project",
                        "endpoint": f"{API_V1_PREFIX}/projects/{self.test_project_id}",
                        "status": response.status_code,
                        "success": success,
                    }
                )

            return all(r["success"] for r in self.results if r["test"].startswith("Create") or r["test"].startswith("Get"))
        except Exception as e:
            self.results.append({"test": "Projects CRUD", "success": False, "error": str(e)})
            return False

    async def test_agents(self):
        """Test agent endpoints"""
        try:
            if not self.test_project_id:
                # Create a project first
                create_data = {"name": f"Agent Test {datetime.now()}", "mission": "Test agents"}
                response = await self.client.post(f"{API_V1_PREFIX}/projects/", json=create_data)
                if response.status_code == 200:
                    self.test_project_id = response.json().get("id")

            if self.test_project_id:
                # Create agent
                agent_data = {
                    "project_id": self.test_project_id,
                    "agent_name": "test_agent",
                    "mission": "Test integration",
                }
                response = await self.client.post(f"{API_V1_PREFIX}/agents/", json=agent_data)
                success = response.status_code == 200
                if success:
                    self.test_agent_id = response.json().get("id")
                self.results.append(
                    {
                        "test": "Create Agent",
                        "endpoint": f"{API_V1_PREFIX}/agents/",
                        "status": response.status_code,
                        "success": success,
                    }
                )

                # Get agent health
                response = await self.client.get(f"{API_V1_PREFIX}/agents/{self.test_agent_id}/health")
                success = response.status_code == 200
                self.results.append(
                    {
                        "test": "Agent Health",
                        "endpoint": f"{API_V1_PREFIX}/agents/{self.test_agent_id}/health",
                        "status": response.status_code,
                        "success": success,
                    }
                )

            return True
        except Exception as e:
            self.results.append({"test": "Agents", "success": False, "error": str(e)})
            return False

    async def test_messages(self):
        """Test messaging endpoints"""
        try:
            if not self.test_project_id:
                return False

            # Send message
            message_data = {
                "to_agents": ["test_agent"],
                "content": "Test message",
                "project_id": self.test_project_id,
                "from_agent": "orchestrator",
                "message_type": "direct",
            }
            response = await self.client.post(f"{API_V1_PREFIX}/messages/", json=message_data)
            success = response.status_code == 200
            if success:
                self.test_message_id = response.json().get("id")
            self.results.append(
                {
                    "test": "Send Message",
                    "endpoint": f"{API_V1_PREFIX}/messages/",
                    "status": response.status_code,
                    "success": success,
                }
            )

            # Get messages
            response = await self.client.get(
                f"{API_V1_PREFIX}/messages/agent/test_agent", params={"project_id": self.test_project_id}
            )
            success = response.status_code == 200
            self.results.append(
                {
                    "test": "Get Messages",
                    "endpoint": f"{API_V1_PREFIX}/messages/agent/test_agent",
                    "status": response.status_code,
                    "success": success,
                }
            )

            return True
        except Exception as e:
            self.results.append({"test": "Messages", "success": False, "error": str(e)})
            return False

    async def test_context(self):
        """Test context/vision endpoints"""
        try:
            # Get context index
            response = await self.client.get(f"{API_V1_PREFIX}/context/index")
            success = response.status_code in [200, 404]  # 404 is ok if no context
            self.results.append(
                {
                    "test": "Context Index",
                    "endpoint": f"{API_V1_PREFIX}/context/index",
                    "status": response.status_code,
                    "success": success,
                }
            )

            # Get vision document (chunked)
            response = await self.client.get(f"{API_V1_PREFIX}/context/vision", params={"part": 1, "max_tokens": 1000})
            success = response.status_code in [200, 404]  # 404 is ok if no vision doc
            self.results.append(
                {
                    "test": "Vision Document",
                    "endpoint": f"{API_V1_PREFIX}/context/vision",
                    "status": response.status_code,
                    "success": success,
                }
            )

            # Get vision index
            response = await self.client.get(f"{API_V1_PREFIX}/context/vision/index")
            success = response.status_code in [200, 404]
            self.results.append(
                {
                    "test": "Vision Index",
                    "endpoint": f"{API_V1_PREFIX}/context/vision/index",
                    "status": response.status_code,
                    "success": success,
                }
            )

            return True
        except Exception as e:
            self.results.append({"test": "Context", "success": False, "error": str(e)})
            return False

    async def test_config(self):
        """Test configuration endpoints"""
        try:
            # Get config
            response = await self.client.get(f"{API_V1_PREFIX}/config/")
            success = response.status_code == 200
            self.results.append(
                {
                    "test": "Get Config",
                    "endpoint": f"{API_V1_PREFIX}/config/",
                    "status": response.status_code,
                    "success": success,
                }
            )

            return True
        except Exception as e:
            self.results.append({"test": "Config", "success": False, "error": str(e)})
            return False

    async def test_stats(self):
        """Test statistics endpoints"""
        try:
            # Get system stats
            response = await self.client.get(f"{API_V1_PREFIX}/stats/system")
            success = response.status_code == 200
            self.results.append(
                {
                    "test": "System Stats",
                    "endpoint": f"{API_V1_PREFIX}/stats/system",
                    "status": response.status_code,
                    "success": success,
                }
            )

            return True
        except Exception as e:
            self.results.append({"test": "Stats", "success": False, "error": str(e)})
            return False

    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("Starting API Integration Tests...")
        logger.info("=" * 60)

        await self.test_health()
        await self.test_projects_crud()
        await self.test_agents()
        await self.test_messages()
        await self.test_context()
        await self.test_config()
        await self.test_stats()

        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("INTEGRATION TEST RESULTS")
        logger.info("=" * 60)

        passed = 0
        failed = 0
        for result in self.results:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            logger.info(f"{status} - {result['test']}: {result.get('endpoint', 'N/A')} (Status: {result.get('status', 'ERROR')})")
            if result.get("error"):
                logger.error(f"  Error: {result['error']}")
            if result.get("success"):
                passed += 1
            else:
                failed += 1

        logger.info("=" * 60)
        logger.info(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        success_rate = (passed / len(self.results) * 100) if self.results else 0
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info("=" * 60)

        # Close client
        await self.client.aclose()

        return failed == 0


async def main():
    """Main test runner"""
    tester = IntegrationTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
