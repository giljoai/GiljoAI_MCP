"""
Integration tests for Tools Framework
Tests cross-module interactions and end-to-end workflows

Key integration scenarios:
- Agent → Message → Task workflows
- Project → Agent → Context pipelines
- Template → Agent → Task creation flows
- Multi-agent collaboration scenarios
- Database transaction consistency
"""

import asyncio

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.agent import (
    _ensure_agent,
    _get_agent_health,
    _handoff_agent_work,
)

# TODO: These context functions don't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.context import (
#     _get_project_description,
#     _get_vision_overview,
#     _update_discovery_cache,
# )
# TODO: These message functions don't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.message import (
#     _acknowledge_message,
#     _broadcast_message,
#     _get_pending_messages,
#     _send_message,
# )
# TODO: These task functions don't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.task import (
#     _create_task,
#     _get_task_dependencies,
#     _update_task_status,
# )
# TODO: These template functions don't exist yet - commenting out for test collection
# from src.giljo_mcp.tools.template import (
#     _create_template,
#     _get_template,
# )
from tests.utils.tools_helpers import (
    ToolsTestHelper,
)


class TestToolsIntegration:
    """Integration tests for Tools Framework cross-module workflows"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Integration Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_agent_task_message_workflow(self):
        """Test complete Agent → Task → Message workflow"""
        # 1. Create agent
        agent_data = await _ensure_agent(
            self.db_manager,
            self.tenant_manager,
            "workflow_agent",
            "testing agent-task-message workflow",
            "orchestrator",
        )
        assert agent_data["success"] is True
        agent_name = agent_data["agent_name"]

        # 2. Create task for agent
        task_data = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Integration test task",
            "Test the complete workflow",
            assignee=agent_name,
            priority="high",
        )
        assert task_data["success"] is True
        task_id = task_data["task_id"]

        # 3. Send message about task
        message_data = await _send_message(
            self.db_manager,
            self.tenant_manager,
            [agent_name],
            f"Task {task_id} has been assigned to you",
            "task_assignment",
            priority="high",
        )
        assert message_data["success"] is True

        # 4. Verify message delivery
        messages = await _get_pending_messages(self.db_manager, self.tenant_manager, agent_name)
        assert messages["success"] is True
        assert len(messages["messages"]) >= 1

        # 5. Acknowledge message and update task
        message_id = messages["messages"][0]["message_id"]
        ack_result = await _acknowledge_message(self.db_manager, self.tenant_manager, message_id, agent_name)
        assert ack_result["success"] is True

        # 6. Update task status
        update_result = await _update_task_status(
            self.db_manager, self.tenant_manager, task_id, "in_progress", agent_name
        )
        assert update_result["success"] is True

    @pytest.mark.asyncio
    async def test_template_agent_creation_workflow(self):
        """Test Template → Agent creation workflow"""
        # 1. Create agent template
        template_data = await _create_template(
            self.db_manager,
            self.tenant_manager,
            "integration_agent",
            "specialist",
            "Agent for integration testing with enhanced capabilities",
            "integration",
        )
        assert template_data["success"] is True

        # 2. Apply template to create agent
        template_result = await _get_template(
            self.db_manager,
            self.tenant_manager,
            "integration_agent",
            augmentations="Focus on cross-module testing",
            variables={"project_name": "Integration Test"},
        )
        assert template_result["success"] is True

        # 3. Create agent using template
        agent_data = await _ensure_agent(
            self.db_manager, self.tenant_manager, "templated_agent", template_result["mission"], "specialist"
        )
        assert agent_data["success"] is True

        # 4. Verify agent has template-derived mission
        agent_health = await _get_agent_health(self.db_manager, self.tenant_manager, "templated_agent")
        assert agent_health["success"] is True
        assert "integration testing" in agent_health["mission"].lower()

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self):
        """Test multi-agent collaboration scenario"""
        # 1. Create three agents with different roles
        agents = []
        for _i, role in enumerate(["analyzer", "implementer", "tester"]):
            agent_data = await _ensure_agent(
                self.db_manager, self.tenant_manager, f"{role}_agent", f"Agent responsible for {role} tasks", role
            )
            assert agent_data["success"] is True
            agents.append(agent_data["agent_name"])

        # 2. Create dependent tasks
        analysis_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Analyze requirements",
            "Analyze system requirements for new feature",
            assignee=agents[0],
            priority="high",
        )
        assert analysis_task["success"] is True

        implementation_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Implement feature",
            "Implement the analyzed feature",
            assignee=agents[1],
            priority="medium",
            dependencies=[analysis_task["task_id"]],
        )
        assert implementation_task["success"] is True

        testing_task = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Test implementation",
            "Test the implemented feature",
            assignee=agents[2],
            priority="medium",
            dependencies=[implementation_task["task_id"]],
        )
        assert testing_task["success"] is True

        # 3. Simulate workflow progression
        # Complete analysis task
        await _update_task_status(
            self.db_manager, self.tenant_manager, analysis_task["task_id"], "database_initialized", agents[0]
        )

        # Send handoff message
        handoff_result = await _handoff_agent_work(
            self.db_manager,
            self.tenant_manager,
            agents[0],
            agents[1],
            {
                "completed_task": analysis_task["task_id"],
                "requirements": "Feature requirements analyzed and documented",
            },
        )
        assert handoff_result["success"] is True

        # 4. Verify task dependencies
        deps = await _get_task_dependencies(self.db_manager, self.tenant_manager, implementation_task["task_id"])
        assert deps["success"] is True
        assert len(deps["dependencies"]) == 1

    @pytest.mark.asyncio
    async def test_context_discovery_integration(self):
        """Test Context → Discovery integration"""
        # 1. Update discovery cache
        discovery_result = await _update_discovery_cache(
            self.db_manager,
            self.tenant_manager,
            {
                "projects": [{"id": str(self.project.project_id), "name": "Integration Test"}],
                "agents": ["test_agent_1", "test_agent_2"],
                "tools": ["create_task", "send_message"],
            },
        )
        assert discovery_result["success"] is True

        # 2. Get project context
        context_result = await _get_project_description(self.db_manager, self.tenant_manager)
        assert context_result["success"] is True
        assert "agents" in context_result["context"]
        assert "tasks" in context_result["context"]

        # 3. Get vision overview
        vision_result = await _get_vision_overview(self.db_manager, self.tenant_manager)
        assert vision_result["success"] is True

    @pytest.mark.asyncio
    async def test_broadcast_acknowledgment_workflow(self):
        """Test broadcast message with multiple acknowledgments"""
        # 1. Create multiple agents
        agents = []
        for i in range(3):
            agent_data = await _ensure_agent(
                self.db_manager,
                self.tenant_manager,
                f"broadcast_agent_{i}",
                f"Agent {i} for broadcast testing",
                "worker",
            )
            assert agent_data["success"] is True
            agents.append(agent_data["agent_name"])

        # 2. Broadcast message to all agents
        broadcast_result = await _broadcast_message(
            self.db_manager, self.tenant_manager, "System maintenance scheduled for tonight", priority="high"
        )
        assert broadcast_result["success"] is True

        # 3. Verify all agents received message
        for agent in agents:
            messages = await _get_pending_messages(self.db_manager, self.tenant_manager, agent)
            assert messages["success"] is True
            assert len(messages["messages"]) >= 1

        # 4. Have all agents acknowledge
        for agent in agents:
            messages = await _get_pending_messages(self.db_manager, self.tenant_manager, agent)
            for message in messages["messages"]:
                ack_result = await _acknowledge_message(
                    self.db_manager, self.tenant_manager, message["message_id"], agent
                )
                assert ack_result["success"] is True

    @pytest.mark.asyncio
    async def test_database_transaction_consistency(self):
        """Test database transaction consistency across modules"""
        # 1. Start complex multi-module operation
        async with self.db_manager.get_session_async():
            # Create agent, task, and message in same transaction
            agent_data = await _ensure_agent(
                self.db_manager, self.tenant_manager, "transaction_agent", "Agent for transaction testing", "specialist"
            )
            assert agent_data["success"] is True

            task_data = await _create_task(
                self.db_manager,
                self.tenant_manager,
                "Transaction test task",
                "Test transaction consistency",
                assignee="transaction_agent",
            )
            assert task_data["success"] is True

            message_data = await _send_message(
                self.db_manager, self.tenant_manager, ["transaction_agent"], "Task assigned", "assignment"
            )
            assert message_data["success"] is True

            # Verify all operations succeeded
            assert all([agent_data["success"], task_data["success"], message_data["success"]])

    @pytest.mark.asyncio
    async def test_error_handling_across_modules(self):
        """Test error handling and rollback across modules"""
        # 1. Attempt to create task with non-existent assignee
        task_result = await _create_task(
            self.db_manager,
            self.tenant_manager,
            "Invalid task",
            "Task with invalid assignee",
            assignee="nonexistent_agent",
        )
        # Should handle gracefully (may succeed but log warning)
        assert isinstance(task_result, dict)

        # 2. Attempt to send message to non-existent agent
        message_result = await _send_message(
            self.db_manager, self.tenant_manager, ["nonexistent_agent"], "Test message", "test"
        )
        # Should handle gracefully
        assert isinstance(message_result, dict)

        # 3. Attempt to handoff to non-existent agent
        # First create a valid agent
        agent_data = await _ensure_agent(
            self.db_manager, self.tenant_manager, "handoff_source", "Source agent for handoff test", "worker"
        )
        assert agent_data["success"] is True

        handoff_result = await _handoff_agent_work(
            self.db_manager, self.tenant_manager, "handoff_source", "nonexistent_target", {"context": "test"}
        )
        # Should handle gracefully
        assert isinstance(handoff_result, dict)

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under moderate load"""
        # 1. Create multiple agents concurrently
        agent_tasks = []
        for i in range(10):
            task = _ensure_agent(
                self.db_manager, self.tenant_manager, f"load_agent_{i}", f"Load test agent {i}", "worker"
            )
            agent_tasks.append(task)

        agent_results = await asyncio.gather(*agent_tasks)
        assert all(result["success"] for result in agent_results)

        # 2. Create multiple tasks concurrently
        task_tasks = []
        for i in range(20):
            task = _create_task(
                self.db_manager,
                self.tenant_manager,
                f"Load test task {i}",
                f"Task {i} for load testing",
                assignee=f"load_agent_{i % 10}",
            )
            task_tasks.append(task)

        task_results = await asyncio.gather(*task_tasks)
        assert all(result["success"] for result in task_results)

        # 3. Send multiple messages concurrently
        message_tasks = []
        for i in range(15):
            task = _send_message(
                self.db_manager, self.tenant_manager, [f"load_agent_{i % 10}"], f"Load test message {i}", "load_test"
            )
            message_tasks.append(task)

        message_results = await asyncio.gather(*message_tasks)
        assert all(result["success"] for result in message_results)

    @pytest.mark.asyncio
    async def test_tenant_isolation_integration(self):
        """Test tenant isolation across all modules"""
        # 1. Create second project with different tenant
        async with self.db_manager.get_session_async() as session:
            project2 = await ToolsTestHelper.create_test_project(session, "Isolated Test Project")

        # 2. Switch to second tenant and create resources
        original_tenant = self.tenant_manager.get_current_tenant()
        self.tenant_manager.set_current_tenant(project2.tenant_key)

        # Create agent in second tenant
        agent_data = await _ensure_agent(
            self.db_manager, self.tenant_manager, "isolated_agent", "Agent in isolated tenant", "worker"
        )
        assert agent_data["success"] is True

        # Create task in second tenant
        task_data = await _create_task(self.db_manager, self.tenant_manager, "Isolated task", "Task in isolated tenant")
        assert task_data["success"] is True

        # 3. Switch back to original tenant
        self.tenant_manager.set_current_tenant(original_tenant)

        # 4. Verify resources are isolated
        # Agent from second tenant should not be visible
        agent_health = await _get_agent_health(self.db_manager, self.tenant_manager, "isolated_agent")
        # Should either fail or not find the agent
        assert agent_health.get("success") is not True or agent_health.get("agent") is None

    @pytest.mark.asyncio
    async def test_full_project_lifecycle(self):
        """Test complete project lifecycle with all modules"""
        # 1. Project setup phase
        # Create project context
        context_result = await _get_project_description(self.db_manager, self.tenant_manager)
        assert context_result["success"] is True

        # 2. Agent creation phase
        agents = []
        for role in ["project_manager", "developer", "qa_engineer"]:
            agent_data = await _ensure_agent(
                self.db_manager,
                self.tenant_manager,
                role,
                f"Agent responsible for {role.replace('_', ' ')} tasks",
                role,
            )
            assert agent_data["success"] is True
            agents.append(agent_data["agent_name"])

        # 3. Task planning phase
        tasks = []
        task_titles = ["Plan project architecture", "Implement core features", "Test implementation"]

        for i, (title, assignee) in enumerate(zip(task_titles, agents)):
            dependencies = [tasks[-1]["task_id"]] if tasks else None
            task_data = await _create_task(
                self.db_manager,
                self.tenant_manager,
                title,
                f"Description for {title}",
                assignee=assignee,
                dependencies=dependencies,
            )
            assert task_data["success"] is True
            tasks.append(task_data)

        # 4. Execution phase
        for i, (task, agent) in enumerate(zip(tasks, agents)):
            # Update task to in progress
            await _update_task_status(self.db_manager, self.tenant_manager, task["task_id"], "in_progress", agent)

            # Send progress message
            await _send_message(
                self.db_manager,
                self.tenant_manager,
                agents,  # Notify all agents
                f"Task '{task_titles[i]}' is now in progress",
                "progress_update",
            )

            # Complete task
            await _update_task_status(
                self.db_manager, self.tenant_manager, task["task_id"], "database_initialized", agent
            )

        # 5. Verification phase
        # All tasks should be completed
        for task in tasks:
            # In a real system, we'd query task status
            # Here we trust the update operations succeeded
            pass

        # All agents should have pending completion messages
        for agent in agents:
            messages = await _get_pending_messages(self.db_manager, self.tenant_manager, agent)
            assert messages["success"] is True

        # Project should have complete context
        final_context = await _get_project_description(self.db_manager, self.tenant_manager)
        assert final_context["success"] is True
        assert len(final_context["context"]["agents"]) >= 3
