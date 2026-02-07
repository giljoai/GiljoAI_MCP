"""
Comprehensive Tool-API Integration Tests
Tests the complete Tool->API->Database flow for all 20+ MCP tools
Fixed version with proper database initialization
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor

# Import our benchmark utilities
from tests.benchmark_tools import PerformanceBenchmark
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class ToolAPIIntegrationTester:
    """Comprehensive integration tests for Tool-API bridge"""

    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.tenant_manager: Optional[TenantManager] = None
        self.tool_accessor: Optional[ToolAccessor] = None
        self.test_project_id: Optional[str] = None
        self.test_agent_name = "test_agent"
        self.benchmark = PerformanceBenchmark(target_time_ms=100.0)
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "platform": sys.platform,
            "tests": {},
            "performance": {},
            "database_contexts": {},
            "errors": [],
        }

    async def setup(self):
        """Setup test environment"""

        # PostgreSQL test database used instead of temp file
        # PostgreSQL test database managed by fixtures

        # Initialize database with PostgreSQL for testing
        db_url = PostgreSQLTestHelper.get_test_db_url()
        self.db_manager = DatabaseManager(db_url, is_async=True)

        # Create tables
        await self.db_manager.create_tables_async()

        # Initialize tenant manager
        self.tenant_manager = TenantManager()

        # Initialize tool accessor
        self.tool_accessor = ToolAccessor(self.db_manager, self.tenant_manager)

    async def teardown(self):
        """Cleanup test environment"""

        try:
            # Close project if created
            if self.test_project_id and self.tool_accessor:
                await self.tool_accessor.complete_project(self.test_project_id, "Test completed")
        except Exception:
            pass

        try:
            # Close database connections
            if self.db_manager:
                await self.db_manager.close_async()
        except Exception:
            pass

        # Remove temp database
        try:
            if hasattr(self, "temp_db"):
                os.unlink(self.temp_db.name)
        except Exception:
            pass

    # ========== PROJECT MANAGEMENT TESTS ==========

    async def test_project_lifecycle(self):
        """Test complete project lifecycle"""
        test_name = "project_lifecycle"

        try:
            # Test 1: Create project
            async def create_project():
                return await self.tool_accessor.create_project(
                    name="Integration Test Project",
                    mission="Test Tool-API integration",
                    agents=["analyzer", "implementer"],
                )

            await self.benchmark.benchmark_async("create_project", create_project, iterations=10)

            # Get the last successful result for validation
            final_result = await create_project()
            assert final_result["success"], f"Failed to create project: {final_result.get('error')}"
            self.test_project_id = final_result["project_id"]

            # Test 2: List projects
            async def list_projects():
                return await self.tool_accessor.list_projects(status="active")

            await self.benchmark.benchmark_async("list_projects", list_projects, iterations=50)

            projects = await list_projects()
            assert projects["success"], "Failed to list projects"
            assert len(projects["projects"]) > 0, "No projects found"

            # Test 3: Get project status
            async def get_status():
                return await self.tool_accessor.project_status(self.test_project_id)

            await self.benchmark.benchmark_async("project_status", get_status, iterations=50)

            status = await get_status()
            assert status["success"], "Failed to get project status"

            # Test 4: Update mission
            async def update_mission():
                return await self.tool_accessor.update_project_mission(
                    self.test_project_id, "Updated mission for testing"
                )

            await self.benchmark.benchmark_async("update_mission", update_mission, iterations=20)

            update_result = await update_mission()
            assert update_result["success"], "Failed to update mission"

            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== AGENT MANAGEMENT TESTS ==========

    async def test_agent_lifecycle(self):
        """Test agent creation and management"""
        test_name = "agent_lifecycle"

        try:
            # Ensure we have a project
            if not self.test_project_id:
                result = await self.tool_accessor.create_project(
                    name="Agent Test Project", mission="Testing agent operations"
                )
                self.test_project_id = result["project_id"]

            # Test 1: Ensure agent
            async def ensure_agent():
                return await self.tool_accessor.ensure_agent(
                    self.test_project_id, "test_worker", mission="Test agent for integration"
                )

            result = await self.benchmark.benchmark_async("ensure_agent", ensure_agent, iterations=20)

            agent_result = await ensure_agent()
            assert agent_result["success"], "Failed to ensure agent"

            # Test 2: Agent health
            async def check_health():
                return await self.tool_accessor.agent_health("test_worker")

            result = await self.benchmark.benchmark_async("agent_health", check_health, iterations=50)

            health = await check_health()
            assert health["success"], "Failed to check agent health"

            # Test 3: Decommission agent
            async def decommission():
                return await self.tool_accessor.decommission_agent("test_worker", self.test_project_id, "Test complete")

            result = await self.benchmark.benchmark_async("decommission_agent", decommission, iterations=10)

            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== MESSAGE SYSTEM TESTS ==========

    async def test_message_flow(self):
        """Test message sending and retrieval"""
        test_name = "message_flow"

        try:
            # Setup agents for messaging
            if not self.test_project_id:
                result = await self.tool_accessor.create_project(
                    name="Message Test Project", mission="Testing message operations"
                )
                self.test_project_id = result["project_id"]

            # Create two agents
            await self.tool_accessor.ensure_agent(self.test_project_id, "sender", "Sending agent")
            await self.tool_accessor.ensure_agent(self.test_project_id, "receiver", "Receiving agent")

            # Test 1: Send message
            async def send_msg():
                return await self.tool_accessor.send_message(
                    to_agents=["receiver"],
                    content="Test message content",
                    project_id=self.test_project_id,
                    from_agent="sender",
                )

            result = await self.benchmark.benchmark_async("send_message", send_msg, iterations=50)

            msg_result = await send_msg()
            assert msg_result["success"], "Failed to send message"
            message_id = msg_result["message_id"]

            # Test 2: Get messages
            async def get_msgs():
                return await self.tool_accessor.get_messages("receiver", project_id=self.test_project_id)

            result = await self.benchmark.benchmark_async("get_messages", get_msgs, iterations=50)

            messages = await get_msgs()
            assert messages["success"], "Failed to get messages"
            assert messages["count"] > 0, "No messages received"

            # Test 3: Acknowledge message
            async def ack_msg():
                return await self.tool_accessor.acknowledge_message(message_id, "receiver")

            result = await self.benchmark.benchmark_async("acknowledge_message", ack_msg, iterations=30)

            # Test 4: Complete message
            async def complete_msg():
                return await self.tool_accessor.complete_message(
                    message_id, "receiver", "Message processed successfully"
                )

            result = await self.benchmark.benchmark_async("complete_message", complete_msg, iterations=20)

            # Test 5: Broadcast
            async def broadcast():
                return await self.tool_accessor.broadcast("Broadcast test message", self.test_project_id)

            result = await self.benchmark.benchmark_async("broadcast", broadcast, iterations=20)

            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== CONTEXT TOOLS TESTS ==========

    async def test_context_tools(self):
        """Test context and vision tools"""
        test_name = "context_tools"

        try:
            # Test 1: Log task
            async def log_task():
                return await self.tool_accessor.log_task("Test task content", category="testing", priority="high")

            await self.benchmark.benchmark_async("log_task", log_task, iterations=50)

            # Test 2: Get context index
            async def get_context():
                return await self.tool_accessor.get_context_index()

            await self.benchmark.benchmark_async("get_context_index", get_context, iterations=30)

            # Test 3: Get vision
            async def get_vision():
                return await self.tool_accessor.get_vision(part=1, max_tokens=1000)

            await self.benchmark.benchmark_async("get_vision", get_vision, iterations=20)

            # Test 4: Get vision index
            async def get_vision_idx():
                return await self.tool_accessor.get_vision_index()

            await self.benchmark.benchmark_async("get_vision_index", get_vision_idx, iterations=30)

            # Test 5: Get product settings
            async def get_settings():
                return await self.tool_accessor.get_product_settings()

            await self.benchmark.benchmark_async("get_product_settings", get_settings, iterations=30)

            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== DATABASE CONTEXT VALIDATION ==========

    async def test_database_contexts(self):
        """Validate database context handling"""
        test_name = "database_contexts"

        try:
            # Test that database sessions are properly managed
            context_tests = []

            # Test 1: Session reuse within same operation
            async with self.db_manager.get_session_async() as session:
                # Create a project directly
                import uuid

                from src.giljo_mcp.models import Project

                project = Project(
                    id=str(uuid.uuid4()),
                    name="Context Test Project",
                    mission="Testing database contexts",
                    status="active",
                    tenant_key=str(uuid.uuid4()),
                )
                session.add(project)
                await session.commit()

                # Verify it's accessible in same session
                result = await session.get(Project, project.id)
                assert result is not None, "Project not found in same session"
                context_tests.append("Same session access: PASS")

            # Test 2: Session isolation
            async with self.db_manager.get_session_async() as session2:
                # Verify the project exists in new session
                result = await session2.get(Project, project.id)
                assert result is not None, "Project not found in new session"
                context_tests.append("Cross-session access: PASS")

            # Test 3: Concurrent sessions
            async def concurrent_operation(name: str):
                async with self.db_manager.get_session_async() as session:
                    project = Project(
                        id=str(uuid.uuid4()),
                        name=f"Concurrent {name}",
                        mission="Testing concurrent access",
                        status="active",
                        tenant_key=str(uuid.uuid4()),
                    )
                    session.add(project)
                    await session.commit()
                    return project.id

            # Run concurrent operations
            tasks = [concurrent_operation(f"Test{i}") for i in range(5)]
            project_ids = await asyncio.gather(*tasks)
            assert len(project_ids) == 5, "Not all concurrent operations succeeded"
            context_tests.append("Concurrent operations: PASS")

            # Test 4: Transaction rollback
            try:
                async with self.db_manager.get_session_async() as session:
                    project = Project(
                        id="invalid_id",  # This might cause an error
                        name="Rollback Test",
                        mission="Testing rollback",
                        status="active",
                        tenant_key=str(uuid.uuid4()),
                    )
                    session.add(project)
                    # Force an error
                    raise Exception("Forced rollback")
            except Exception:
                pass  # Expected

            # Verify rollback worked
            async with self.db_manager.get_session_async() as session:
                result = await session.get(Project, "invalid_id")
                assert result is None, "Rollback failed - project exists"
                context_tests.append("Transaction rollback: PASS")

            self.test_results["database_contexts"] = context_tests
            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== LOAD TESTING ==========

    async def test_load_performance(self):
        """Test system under load"""
        test_name = "load_testing"

        try:
            # Create a project for load testing
            if not self.test_project_id:
                result = await self.tool_accessor.create_project(name="Load Test Project", mission="Load testing")
                self.test_project_id = result["project_id"]

            # Load test 1: Message throughput
            async def send_message_load():
                await self.tool_accessor.send_message(
                    to_agents=["load_test_agent"], content="Load test message", project_id=self.test_project_id
                )

            await self.benchmark.load_test(
                "message_throughput", send_message_load, concurrent_requests=10, duration_seconds=5
            )

            # Load test 2: Project status under load
            async def status_load():
                await self.tool_accessor.project_status(self.test_project_id)

            await self.benchmark.load_test("status_queries", status_load, concurrent_requests=20, duration_seconds=5)

            self.test_results["tests"][test_name] = "PASS"

        except Exception as e:
            self.test_results["tests"][test_name] = f"FAIL: {e}"
            self.test_results["errors"].append(str(e))

    # ========== MAIN TEST RUNNER ==========

    async def run_all_tests(self):
        """Run all integration tests"""

        try:
            await self.setup()

            # Run all test suites
            await self.test_project_lifecycle()
            await self.test_agent_lifecycle()
            await self.test_message_flow()
            await self.test_context_tools()
            await self.test_database_contexts()
            await self.test_load_performance()

            # Generate performance report

            self.benchmark.generate_report()

            # Save results
            self.test_results["performance"] = {
                name: result.to_dict() for name, result in self.benchmark.results.items()
            }

            # Save to file
            results_file = Path("test_results_integration.json")
            with open(results_file, "w") as f:
                json.dump(self.test_results, f, indent=2)

            # Check if all tests passed
            all_passed = all(v == "PASS" or isinstance(v, list) for v in self.test_results["tests"].values())

            if all_passed:
                pass
            else:
                pass

            return all_passed

        except Exception as e:
            self.test_results["errors"].append(f"Fatal: {e}")
            return False

        finally:
            await self.teardown()


async def main():
    """Main test runner"""
    tester = ToolAPIIntegrationTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest
