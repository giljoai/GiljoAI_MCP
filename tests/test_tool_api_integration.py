"""
Comprehensive Tool-API Integration Tests
Tests the complete Tool->API->Database flow for all 20+ MCP tools
"""

import asyncio
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager

# Import the components we're testing
from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestToolAPIIntegration:
    """Comprehensive integration tests for Tool-API bridge"""

    # Class-level attributes instead of __init__
    db_manager = None
    tenant_manager = None
    tool_accessor = None
    test_project_id = None
    test_agent_name = "test_agent"
    performance_metrics = {}

    async def setup(self):
        """Setup test environment"""

        # Initialize database with async in-memory SQLite for testing
        db_url = PostgreSQLTestHelper.get_test_db_url()
        self.db_manager = DatabaseManager(database_url=db_url, is_async=True)
        await self.db_manager.create_tables_async()

        # Initialize tenant manager
        self.tenant_manager = TenantManager()

        # Initialize tool accessor
        self.tool_accessor = ToolAccessor(self.db_manager, self.tenant_manager)

    async def teardown(self):
        """Cleanup test environment"""

        # Close project if created
        if self.test_project_id:
            await self.tool_accessor.complete_project(self.test_project_id, "Test completed")

        # Close database connections
        if self.db_manager:
            await self.db_manager.close_async()

    def measure_performance(self, operation: str):
        """Decorator to measure operation performance"""

        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000

                if operation not in self.performance_metrics:
                    self.performance_metrics[operation] = []
                self.performance_metrics[operation].append(duration_ms)

                return result

            return wrapper

        return decorator

    # PROJECT MANAGEMENT TESTS

    async def test_project_lifecycle(self):
        """Test complete project lifecycle"""

        # Create project
        start = time.perf_counter()
        result = await self.tool_accessor.create_project(
            name="Integration Test Project", mission="Test Tool-API integration", agents=["analyzer", "implementer"]
        )
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to create project: {result.get('error')}"
        self.test_project_id = result["project_id"]
        self.performance_metrics["create_project"] = [duration]

        # List projects
        start = time.perf_counter()
        result = await self.tool_accessor.list_projects(status="active")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to list projects: {result.get('error')}"
        assert len(result["projects"]) > 0, "No projects found"
        self.performance_metrics["list_projects"] = [duration]

        # Get project status
        start = time.perf_counter()
        result = await self.tool_accessor.project_status(self.test_project_id)
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to get status: {result.get('error')}"
        assert result["project"]["id"] == self.test_project_id
        self.performance_metrics["project_status"] = [duration]

        # Update mission
        start = time.perf_counter()
        result = await self.tool_accessor.update_project_mission(self.test_project_id, "Updated mission for testing")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to update mission: {result.get('error')}"
        self.performance_metrics["update_mission"] = [duration]

    # AGENT MANAGEMENT TESTS

    async def test_agent_lifecycle(self):
        """Test complete agent lifecycle"""

        # Ensure agent exists
        start = time.perf_counter()
        result = await self.tool_accessor.ensure_agent(self.test_project_id, self.test_agent_name, "Test agent mission")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to ensure agent: {result.get('error')}"
        agent_id = result["agent_id"]
        self.performance_metrics["ensure_agent"] = [duration]

        # Test idempotency - ensure same agent again
        start = time.perf_counter()
        result = await self.tool_accessor.ensure_agent(self.test_project_id, self.test_agent_name, "Test agent mission")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], "Idempotent ensure_agent failed"
        assert result["agent_id"] == agent_id, "Different agent ID returned"

        # Check agent health
        start = time.perf_counter()
        result = await self.tool_accessor.agent_health(self.test_agent_name)
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to check health: {result.get('error')}"
        assert result["health"]["name"] == self.test_agent_name
        self.performance_metrics["agent_health"] = [duration]

        # Decommission agent
        start = time.perf_counter()
        result = await self.tool_accessor.decommission_agent(
            self.test_agent_name, self.test_project_id, "Test completed"
        )
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to decommission: {result.get('error')}"
        self.performance_metrics["decommission_agent"] = [duration]

    # MESSAGE SYSTEM TESTS

    async def test_message_flow(self):
        """Test complete message flow with acknowledgment"""

        # Create test agents
        await self.tool_accessor.ensure_agent(self.test_project_id, "sender", "Sender agent")
        await self.tool_accessor.ensure_agent(self.test_project_id, "receiver", "Receiver agent")

        # Send message
        start = time.perf_counter()
        result = await self.tool_accessor.send_message(
            to_agents=["receiver"],
            content="Test message content",
            project_id=self.test_project_id,
            message_type="direct",
            priority="high",
            from_agent="sender",
        )
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to send message: {result.get('error')}"
        message_id = result["message_id"]
        self.performance_metrics["send_message"] = [duration]

        # Get messages for receiver
        start = time.perf_counter()
        result = await self.tool_accessor.get_messages("receiver", self.test_project_id)
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to get messages: {result.get('error')}"
        assert result["count"] > 0, "No messages found"
        self.performance_metrics["get_messages"] = [duration]

        # Acknowledge message
        start = time.perf_counter()
        result = await self.tool_accessor.acknowledge_message(message_id, "receiver")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to acknowledge: {result.get('error')}"
        self.performance_metrics["acknowledge_message"] = [duration]

        # Complete message
        start = time.perf_counter()
        result = await self.tool_accessor.complete_message(message_id, "receiver", "Message processed successfully")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to complete: {result.get('error')}"
        self.performance_metrics["complete_message"] = [duration]

    async def test_broadcast(self):
        """Test broadcast message to all agents"""

        # Create multiple agents
        agents = ["agent1", "agent2", "agent3"]
        for agent in agents:
            await self.tool_accessor.ensure_agent(self.test_project_id, agent, f"{agent} mission")

        # Broadcast message
        start = time.perf_counter()
        result = await self.tool_accessor.broadcast(
            content="Broadcast test message", project_id=self.test_project_id, priority="high"
        )
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to broadcast: {result.get('error')}"
        self.performance_metrics["broadcast"] = [duration]

        # Verify all agents received message
        for agent in agents:
            result = await self.tool_accessor.get_messages(agent, self.test_project_id)
            assert result["count"] > 0, f"Agent {agent} didn't receive broadcast"

    # TASK MANAGEMENT TESTS

    async def test_task_logging(self):
        """Test task logging functionality"""

        # Log task
        start = time.perf_counter()
        result = await self.tool_accessor.log_task(content="Test task content", category="testing", priority="high")
        duration = (time.perf_counter() - start) * 1000

        assert result["success"], f"Failed to log task: {result.get('error')}"
        self.performance_metrics["log_task"] = [duration]

    # ERROR HANDLING TESTS

    async def test_error_handling(self):
        """Test error handling for invalid operations"""

        # Test invalid project ID
        result = await self.tool_accessor.project_status("invalid-uuid")
        assert not result["success"], "Should have failed with invalid UUID"

        # Test missing project
        result = await self.tool_accessor.update_project_mission("00000000-0000-0000-0000-000000000000", "New mission")
        assert not result["success"], "Should have failed with missing project"

        # Test missing agent
        result = await self.tool_accessor.agent_health("nonexistent_agent")
        assert not result["success"], "Should have failed with missing agent"

    # PERFORMANCE TESTS

    async def test_performance_under_load(self):
        """Test performance with multiple concurrent operations"""

        # Create multiple projects concurrently
        tasks = []
        for i in range(10):
            task = self.tool_accessor.create_project(
                name=f"Load Test Project {i}", mission=f"Testing load {i}", agents=["agent1", "agent2"]
            )
            tasks.append(task)

        start = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        (time.perf_counter() - start) * 1000

        sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        # Clean up created projects
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                await self.tool_accessor.complete_project(result["project_id"], "Load test completed")

    async def test_database_context_management(self):
        """Test that database context is properly maintained"""

        # Test that sessions are properly closed
        initial_sessions = len(self.db_manager._sessions) if hasattr(self.db_manager, "_sessions") else 0

        # Perform multiple operations
        for _ in range(5):
            await self.tool_accessor.list_projects()

        # Check sessions are not leaking
        final_sessions = len(self.db_manager._sessions) if hasattr(self.db_manager, "_sessions") else 0
        assert final_sessions <= initial_sessions + 1, "Database sessions are leaking"

    def print_performance_summary(self):
        """Print performance metrics summary"""

        for times in self.performance_metrics.values():
            if times:
                sum(times) / len(times)
                min(times)
                max(times)

        # Check against requirements (all operations < 100ms)
        all_under_100ms = all(max(times) < 100 for times in self.performance_metrics.values() if times)

        if all_under_100ms:
            pass
        else:
            pass

    async def run_all_tests(self):
        """Run all integration tests"""

        try:
            await self.setup()

            # Run all test categories
            await self.test_project_lifecycle()
            await self.test_agent_lifecycle()
            await self.test_message_flow()
            await self.test_broadcast()
            await self.test_task_logging()
            await self.test_error_handling()
            await self.test_performance_under_load()
            await self.test_database_context_management()

            # Print summary
            self.print_performance_summary()

        except Exception:
            import traceback

            traceback.print_exc()

        finally:
            await self.teardown()


async def main():
    """Main entry point"""
    test_suite = TestToolAPIIntegration()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
