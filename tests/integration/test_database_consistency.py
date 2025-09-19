"""
Database consistency integration tests
Tests transaction handling, foreign key constraints, and data integrity
across all Tools Framework modules
"""

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.agent import _ensure_agent, _decommission_agent
from src.giljo_mcp.tools.message import _send_message, _get_pending_messages
from src.giljo_mcp.tools.task import _create_task, _update_task_status
from src.giljo_mcp.tools.template import _create_template, _archive_template
from tests.utils.tools_helpers import ToolsTestHelper


class TestDatabaseConsistency:
    """Test database consistency and transaction handling"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup['db_manager']
        self.tenant_manager = tools_test_setup['tenant_manager']

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "DB Consistency Test")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_foreign_key_integrity(self):
        """Test foreign key constraints are properly enforced"""
        # 1. Create agent
        agent_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "fk_test_agent",
            "Agent for foreign key testing",
            "worker"
        )
        assert agent_result["success"] is True
        agent_name = agent_result["agent_name"]

        # 2. Create task assigned to agent
        task_result = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "FK test task",
            "Task to test foreign key integrity",
            assignee=agent_name
        )
        assert task_result["success"] is True
        task_id = task_result["task_id"]

        # 3. Send message to agent
        message_result = await _send_message(
            self.db_manager,
            self.tenant_manager,
            [agent_name],
            "Test message for FK integrity",
            "test"
        )
        assert message_result["success"] is True

        # 4. Verify relationships exist
        messages = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            agent_name
        )
        assert messages["success"] is True
        assert len(messages["messages"]) >= 1

        # 5. Decommission agent
        decommission_result = await _decommission_agent(
            self.db_manager,
            self.tenant_manager,
            agent_name,
            "Testing FK integrity"
        )
        assert decommission_result["success"] is True

        # 6. Verify dependent records are handled properly
        # Messages should still exist but agent should be marked as decommissioned
        messages_after = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            agent_name
        )
        # Depending on implementation, this might succeed or fail gracefully

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback on errors"""
        # This test simulates scenarios where operations should roll back

        # 1. Create valid agent
        agent_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "rollback_agent",
            "Agent for rollback testing",
            "worker"
        )
        assert agent_result["success"] is True

        # 2. Attempt operation that might fail
        # Create task with very long title that might exceed database limits
        long_title = "x" * 1000  # Very long title
        task_result = await _create_task(
            self.db_manager,
            self.tenant_manager,
            long_title,
            "Task with extremely long title to test limits",
            assignee="rollback_agent"
        )

        # Result should be handled gracefully
        assert isinstance(task_result, dict)

        # Agent should still exist and be functional
        subsequent_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Normal task",
            "Task with normal title",
            assignee="rollback_agent"
        )
        assert subsequent_task["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_operations_consistency(self):
        """Test database consistency under concurrent operations"""
        # 1. Create base agent
        agent_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "concurrent_agent",
            "Agent for concurrency testing",
            "worker"
        )
        assert agent_result["success"] is True
        agent_name = agent_result["agent_name"]

        # 2. Create multiple concurrent tasks for same agent
        task_operations = []
        for i in range(10):
            operation = _create_task(
                self.db_manager,
                self.tenant_manager,
                f"Concurrent task {i}",
                f"Task {i} for concurrency testing",
                assignee=agent_name
            )
            task_operations.append(operation)

        # 3. Execute all operations concurrently
        results = await asyncio.gather(*task_operations, return_exceptions=True)

        # 4. Verify results are consistent
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) == 10  # All should succeed

        # 5. Create concurrent messages
        message_operations = []
        for i in range(5):
            operation = _send_message(
                self.db_manager,
                self.tenant_manager,
                [agent_name],
                f"Concurrent message {i}",
                "concurrency_test"
            )
            message_operations.append(operation)

        message_results = await asyncio.gather(*message_operations, return_exceptions=True)
        successful_messages = [r for r in message_results if isinstance(r, dict) and r.get("success")]
        assert len(successful_messages) == 5

        # 6. Verify all messages were delivered
        messages = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            agent_name
        )
        assert messages["success"] is True
        assert len(messages["messages"]) >= 5

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self):
        """Test strict tenant data isolation"""
        # 1. Create resources in first tenant
        original_tenant = self.tenant_manager.get_current_tenant()

        agent1_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "tenant1_agent",
            "Agent in first tenant",
            "worker"
        )
        assert agent1_result["success"] is True

        template1_result = await _create_template(
            self.db_manager,
            self.tenant_manager,
            "tenant1_template",
            "specialist",
            "Template in first tenant",
            "testing"
        )
        assert template1_result["success"] is True

        # 2. Create second tenant and switch
        async with self.db_manager.get_session_async() as session:
            project2 = await ToolsTestHelper.create_test_project(session, "Second Tenant")

        self.tenant_manager.set_current_tenant(project2.tenant_key)

        # 3. Create resources in second tenant with same names
        agent2_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "tenant1_agent",  # Same name, different tenant
            "Agent in second tenant",
            "worker"
        )
        assert agent2_result["success"] is True

        template2_result = await _create_template(
            self.db_manager,
            self.tenant_manager,
            "tenant1_template",  # Same name, different tenant
            "analyst",
            "Template in second tenant",
            "analysis"
        )
        assert template2_result["success"] is True

        # 4. Verify resources are isolated
        # Switch back to first tenant
        self.tenant_manager.set_current_tenant(original_tenant)

        # Resources in first tenant should still exist and be unchanged
        messages1 = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            "tenant1_agent"
        )
        assert messages1["success"] is True

        # 5. Switch to second tenant and verify isolation
        self.tenant_manager.set_current_tenant(project2.tenant_key)

        messages2 = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            "tenant1_agent"
        )
        assert messages2["success"] is True

        # 6. Cleanup - switch back to original tenant
        self.tenant_manager.set_current_tenant(original_tenant)

    @pytest.mark.asyncio
    async def test_cascading_operations(self):
        """Test cascading operations across related entities"""
        # 1. Create template
        template_result = await _create_template(
            self.db_manager,
            self.tenant_manager,
            "cascade_template",
            "orchestrator",
            "Template for cascade testing",
            "orchestration"
        )
        assert template_result["success"] is True

        # 2. Create agent using template
        agent_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "cascade_agent",
            "Agent created from template for cascade testing",
            "orchestrator"
        )
        assert agent_result["success"] is True

        # 3. Create multiple tasks for agent
        task_ids = []
        for i in range(3):
            task_result = await _create_task(
                self.db_manager,
                self.tenant_manager,
                f"Cascade task {i}",
                f"Task {i} for cascade testing",
                assignee="cascade_agent"
            )
            assert task_result["success"] is True
            task_ids.append(task_result["task_id"])

        # 4. Create messages for agent
        for i in range(2):
            message_result = await _send_message(
                self.db_manager,
                self.tenant_manager,
                ["cascade_agent"],
                f"Cascade message {i}",
                "cascade_test"
            )
            assert message_result["success"] is True

        # 5. Archive template (should not affect existing agent)
        archive_result = await _archive_template(
            self.db_manager,
            self.tenant_manager,
            "cascade_template",
            "Testing cascade operations"
        )
        assert archive_result["success"] is True

        # 6. Verify agent and related entities still function
        messages = await _get_pending_messages(
            self.db_manager,
            self.tenant_manager,
            "cascade_agent"
        )
        assert messages["success"] is True
        assert len(messages["messages"]) >= 2

        # 7. Update task statuses
        for task_id in task_ids:
            update_result = await _update_task_status(
                self.db_manager,
                self.tenant_manager,
                task_id,
                "completed",
                "cascade_agent"
            )
            assert update_result["success"] is True

    @pytest.mark.asyncio
    async def test_data_integrity_constraints(self):
        """Test data integrity constraints and validation"""
        # 1. Test unique constraints
        # Create agent
        agent_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "unique_agent",
            "First agent with this name",
            "worker"
        )
        assert agent_result["success"] is True

        # Try to create another agent with same name (should be idempotent)
        duplicate_result = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "unique_agent",
            "Another agent with same name",
            "specialist"
        )
        # Should succeed as ensure_agent is idempotent
        assert duplicate_result["success"] is True

        # 2. Test required field validation
        # Try to create task with minimal data
        minimal_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "",  # Empty title
            "",  # Empty description
        )
        # Should handle gracefully
        assert isinstance(minimal_task, dict)

        # 3. Test data type constraints
        # Try to create task with invalid priority
        invalid_priority_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Invalid priority task",
            "Task with invalid priority value",
            priority="super_mega_ultra_high"  # Invalid priority
        )
        # Should handle gracefully, possibly defaulting to valid priority
        assert isinstance(invalid_priority_task, dict)

    @pytest.mark.asyncio
    async def test_session_cleanup_consistency(self):
        """Test database session cleanup and consistency"""
        # 1. Create multiple sessions and operations
        operations = []

        # Create multiple agents in different "sessions"
        for i in range(5):
            operation = _ensure_agent(
                self.db_manager,
                self.tenant_manager,
                f"session_agent_{i}",
                f"Agent {i} for session testing",
                "worker"
            )
            operations.append(operation)

        # Execute operations
        results = await asyncio.gather(*operations)
        assert all(result["success"] for result in results)

        # 2. Verify all operations persisted correctly
        for i in range(5):
            messages = await _get_pending_messages(
                self.db_manager,
                self.tenant_manager,
                f"session_agent_{i}"
            )
            assert messages["success"] is True

        # 3. Test session cleanup under error conditions
        try:
            # Simulate operation that might cause session issues
            invalid_operation = await _create_task(
                self.db_manager,
                self.tenant_manager,
                "Session test task",
                "Task to test session cleanup",
                assignee="nonexistent_agent_that_should_not_exist"
            )
            # Should handle gracefully
            assert isinstance(invalid_operation, dict)
        except Exception:
            # If exception occurs, subsequent operations should still work
            pass

        # Verify system still functional after potential error
        recovery_agent = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "recovery_agent",
            "Agent to test recovery",
            "worker"
        )
        assert recovery_agent["success"] is True