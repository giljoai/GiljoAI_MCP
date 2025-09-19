"""
Comprehensive tests for agent.py tools
Target: 3.65% → 95%+ coverage

Tests all agent tool functions:
- register_agent_tools
- ensure_agent
- activate_agent
- assign_job
- handoff
- agent_health
- decommission_agent
- spawn_and_log_sub_agent
- log_sub_agent_completion
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import Agent, Job, Project
from src.giljo_mcp.tools.agent import register_agent_tools
from tests.utils.tools_helpers import (
    AssertionHelpers,
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestAgentTools:
    """Test class for agent tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup['db_manager']
        self.tenant_manager = tools_test_setup['tenant_manager']
        self.mock_server = tools_test_setup['mcp_server']

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Agent Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_agent_tools(self):
        """Test that all agent tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)

        # Verify all expected tools are registered
        expected_tools = [
            "ensure_agent",
            "activate_agent",
            "assign_job",
            "handoff",
            "agent_health",
            "decommission_agent",
            "spawn_and_log_sub_agent",
            "log_sub_agent_completion"
        ]

        registered_tools = registrar.get_all_tools()
        for tool in expected_tools:
            AssertionHelpers.assert_tool_registered(registrar, tool)

        assert len(registered_tools) >= len(expected_tools)

    # ensure_agent tests
    @pytest.mark.asyncio
    async def test_ensure_agent_create_new(self):
        """Test ensure_agent creates new agent when it doesn't exist"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")

        result = await ensure_agent(
            project_id=self.project.id,
            agent_name="test_agent",
            mission="Test agent mission"
        )

        AssertionHelpers.assert_success_response(result, ["agent", "job_id", "context"])
        assert result["agent"] == "test_agent"
        assert result["is_reopen"] is False

    @pytest.mark.asyncio
    async def test_ensure_agent_return_existing(self):
        """Test ensure_agent returns existing agent (idempotent)"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create existing agent
        async with self.db_manager.get_session_async() as session:
            existing_agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "test_agent"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")

        result = await ensure_agent(
            project_id=self.project.id,
            agent_name="test_agent"
        )

        AssertionHelpers.assert_success_response(result, ["agent", "is_reopen"])
        assert result["agent"] == "test_agent"
        assert result["is_reopen"] is True

    @pytest.mark.asyncio
    async def test_ensure_agent_invalid_project(self):
        """Test ensure_agent with invalid project ID"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")

        result = await ensure_agent(
            project_id=str(uuid.uuid4()),  # Non-existent project
            agent_name="test_agent"
        )

        AssertionHelpers.assert_error_response(result, "Project not found")

    # activate_agent tests
    @pytest.mark.asyncio
    async def test_activate_agent_orchestrator(self):
        """Test activate_agent for orchestrator (starts working immediately)"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        activate_agent = registrar.get_registered_tool("activate_agent")

        with patch('src.giljo_mcp.tools.agent.DiscoveryManager') as mock_discovery:
            mock_discovery_instance = MagicMock()
            mock_discovery_instance.discover_context = AsyncMock(return_value={
                "context": "test_context"
            })
            mock_discovery.return_value = mock_discovery_instance

            result = await activate_agent(
                project_id=self.project.id,
                agent_name="orchestrator3",
                mission="Orchestrate project development"
            )

        AssertionHelpers.assert_success_response(result, ["agent", "context", "discovery"])
        assert result["agent"] == "orchestrator3"

    @pytest.mark.asyncio
    async def test_activate_agent_worker(self):
        """Test activate_agent for worker agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        activate_agent = registrar.get_registered_tool("activate_agent")

        result = await activate_agent(
            project_id=self.project.id,
            agent_name="worker_agent",
            mission="Work on specific tasks"
        )

        AssertionHelpers.assert_success_response(result, ["agent", "context"])
        assert result["agent"] == "worker_agent"

    # assign_job tests
    @pytest.mark.asyncio
    async def test_assign_job_new(self):
        """Test assigning new job to agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test agent
        async with self.db_manager.get_session_async() as session:
            agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "test_agent"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        assign_job = registrar.get_registered_tool("assign_job")

        result = await assign_job(
            agent_name="test_agent",
            job_type="analysis",
            project_id=self.project.id,
            tasks=["Analyze requirements", "Create documentation"],
            scope_boundary="Focus on API analysis only",
            vision_alignment="Align with project goals"
        )

        AssertionHelpers.assert_success_response(result, ["job_id", "agent", "job_type"])
        assert result["agent"] == "test_agent"
        assert result["job_type"] == "analysis"

    @pytest.mark.asyncio
    async def test_assign_job_update_existing(self):
        """Test updating existing active job (idempotent)"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test agent and existing job
        async with self.db_manager.get_session_async() as session:
            agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "test_agent"
            )

            existing_job = Job(
                id=str(uuid.uuid4()),
                agent_name="test_agent",
                job_type="analysis",
                status="active",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc)
            )
            session.add(existing_job)
            await session.commit()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        assign_job = registrar.get_registered_tool("assign_job")

        result = await assign_job(
            agent_name="test_agent",
            job_type="implementation",
            project_id=self.project.id,
            tasks=["Implement features"]
        )

        AssertionHelpers.assert_success_response(result, ["job_id", "updated"])
        assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_assign_job_agent_not_found(self):
        """Test assigning job to non-existent agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        assign_job = registrar.get_registered_tool("assign_job")

        result = await assign_job(
            agent_name="nonexistent_agent",
            job_type="analysis",
            project_id=self.project.id
        )

        AssertionHelpers.assert_error_response(result, "Agent not found")

    # handoff tests
    @pytest.mark.asyncio
    async def test_handoff_success(self):
        """Test successful work handoff between agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create source and target agents
        async with self.db_manager.get_session_async() as session:
            source_agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "source_agent"
            )
            target_agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "target_agent"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        handoff = registrar.get_registered_tool("handoff")

        context = {
            "completed_tasks": ["Task 1", "Task 2"],
            "pending_work": ["Task 3"],
            "notes": "Handoff notes"
        }

        result = await handoff(
            from_agent="source_agent",
            to_agent="target_agent",
            project_id=self.project.id,
            context=context
        )

        AssertionHelpers.assert_success_response(result, ["handoff_id", "from_agent", "to_agent"])
        assert result["from_agent"] == "source_agent"
        assert result["to_agent"] == "target_agent"

    @pytest.mark.asyncio
    async def test_handoff_invalid_agents(self):
        """Test handoff with invalid source or target agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        handoff = registrar.get_registered_tool("handoff")

        result = await handoff(
            from_agent="nonexistent_source",
            to_agent="nonexistent_target",
            project_id=self.project.id,
            context={"test": "data"}
        )

        AssertionHelpers.assert_error_response(result, "Agent not found")

    # agent_health tests
    @pytest.mark.asyncio
    async def test_agent_health_specific_agent(self):
        """Test getting health metrics for specific agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test agent with job
        async with self.db_manager.get_session_async() as session:
            agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "test_agent"
            )

            job = Job(
                id=str(uuid.uuid4()),
                agent_name="test_agent",
                job_type="analysis",
                status="active",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc)
            )
            session.add(job)
            await session.commit()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        agent_health = registrar.get_registered_tool("agent_health")

        result = await agent_health(agent_name="test_agent")

        AssertionHelpers.assert_success_response(result, ["agent", "health"])
        assert result["agent"] == "test_agent"
        assert "status" in result["health"]
        assert "active_jobs" in result["health"]

    @pytest.mark.asyncio
    async def test_agent_health_all_agents(self):
        """Test getting health metrics for all agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create multiple test agents
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_agent(session, self.project.id, "agent1")
            await ToolsTestHelper.create_test_agent(session, self.project.id, "agent2")

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        agent_health = registrar.get_registered_tool("agent_health")

        result = await agent_health()

        AssertionHelpers.assert_success_response(result, ["agents", "summary"])
        assert len(result["agents"]) == 2
        assert "total_agents" in result["summary"]

    # decommission_agent tests
    @pytest.mark.asyncio
    async def test_decommission_agent_success(self):
        """Test successful agent decommissioning"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test agent
        async with self.db_manager.get_session_async() as session:
            agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "test_agent"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        decommission_agent = registrar.get_registered_tool("decommission_agent")

        result = await decommission_agent(
            agent_name="test_agent",
            project_id=self.project.id,
            reason="Task completed successfully"
        )

        AssertionHelpers.assert_success_response(result, ["agent", "status", "reason"])
        assert result["agent"] == "test_agent"
        assert result["status"] == "decommissioned"

    @pytest.mark.asyncio
    async def test_decommission_agent_not_found(self):
        """Test decommissioning non-existent agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        decommission_agent = registrar.get_registered_tool("decommission_agent")

        result = await decommission_agent(
            agent_name="nonexistent_agent",
            project_id=self.project.id
        )

        AssertionHelpers.assert_error_response(result, "Agent not found")

    # spawn_and_log_sub_agent tests
    @pytest.mark.asyncio
    async def test_spawn_and_log_sub_agent(self):
        """Test spawning and logging sub-agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent agent
        async with self.db_manager.get_session_async() as session:
            parent_agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "parent_agent"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        spawn_sub_agent = registrar.get_registered_tool("spawn_and_log_sub_agent")

        result = await spawn_sub_agent(
            parent_agent="parent_agent",
            sub_agent_name="sub_agent",
            sub_agent_type="analyzer",
            mission="Analyze specific component",
            project_id=self.project.id,
            scope="Limited to authentication module"
        )

        AssertionHelpers.assert_success_response(result, ["sub_agent_id", "log_id", "spawned"])
        assert result["sub_agent_name"] == "sub_agent"
        assert result["spawned"] is True

    @pytest.mark.asyncio
    async def test_spawn_sub_agent_invalid_parent(self):
        """Test spawning sub-agent with invalid parent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        spawn_sub_agent = registrar.get_registered_tool("spawn_and_log_sub_agent")

        result = await spawn_sub_agent(
            parent_agent="nonexistent_parent",
            sub_agent_name="sub_agent",
            sub_agent_type="analyzer",
            mission="Test mission",
            project_id=self.project.id
        )

        AssertionHelpers.assert_error_response(result, "Parent agent not found")

    # log_sub_agent_completion tests
    @pytest.mark.asyncio
    async def test_log_sub_agent_completion(self):
        """Test logging sub-agent completion"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent agent and sub-agent log
        async with self.db_manager.get_session_async() as session:
            parent_agent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "parent_agent"
            )

            # SubAgentLog model not available - skip this test section
            # sub_agent_log = SubAgentLog(
            #     id=str(uuid.uuid4()),
            #     parent_agent="parent_agent",
            #     sub_agent_name="sub_agent",
            #     sub_agent_type="analyzer",
            #     mission="Test mission",
            #     status="active",
            #     project_id=self.project.id,
            #     tenant_key=self.project.tenant_key,
            #     created_at=datetime.now(timezone.utc)
            # )
            # session.add(sub_agent_log)
            await session.commit()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        log_completion = registrar.get_registered_tool("log_sub_agent_completion")

        result = await log_completion(
            sub_agent_log_id=sub_agent_log.id,
            completion_status="success",
            results_summary="Successfully analyzed authentication module",
            artifacts_created=["analysis_report.md", "test_results.json"]
        )

        AssertionHelpers.assert_success_response(result, ["log_id", "status", "completion_time"])
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_log_sub_agent_completion_not_found(self):
        """Test logging completion for non-existent sub-agent log"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        log_completion = registrar.get_registered_tool("log_sub_agent_completion")

        result = await log_completion(
            sub_agent_log_id=str(uuid.uuid4()),
            completion_status="success",
            results_summary="Test summary"
        )

        AssertionHelpers.assert_error_response(result, "Sub-agent log not found")

    # Error handling and edge cases
    @pytest.mark.asyncio
    async def test_agent_tools_no_active_project(self):
        """Test agent tools with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")

        result = await ensure_agent(
            project_id=self.project.id,
            agent_name="test_agent"
        )

        AssertionHelpers.assert_error_response(result, "No active project")

    @pytest.mark.asyncio
    async def test_agent_tools_database_error_handling(self):
        """Test that agent tools handle database errors gracefully"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database to raise exception
        with patch.object(self.db_manager, 'get_session_async') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
            agent_health = registrar.get_registered_tool("agent_health")

            result = await agent_health()

        AssertionHelpers.assert_error_response(result, "Database connection failed")

    @pytest.mark.asyncio
    async def test_agent_context_usage_tracking(self):
        """Test agent context usage tracking"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create agent with high context usage
        async with self.db_manager.get_session_async() as session:
            agent = Agent(
                id=str(uuid.uuid4()),
                name="high_context_agent",
                type="analyzer",
                status="active",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                context_used=95000,  # High usage
                created_at=datetime.now(timezone.utc)
            )
            session.add(agent)
            await session.commit()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        agent_health = registrar.get_registered_tool("agent_health")

        result = await agent_health(agent_name="high_context_agent")

        AssertionHelpers.assert_success_response(result)
        assert result["health"]["context_usage_percent"] > 90

    @pytest.mark.asyncio
    async def test_agent_status_transitions(self):
        """Test valid agent status transitions"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")
        decommission_agent = registrar.get_registered_tool("decommission_agent")

        # Create agent (active)
        result1 = await ensure_agent(
            project_id=self.project.id,
            agent_name="test_agent"
        )
        AssertionHelpers.assert_success_response(result1)

        # Decommission agent (active -> decommissioned)
        result2 = await decommission_agent(
            agent_name="test_agent",
            project_id=self.project.id
        )
        AssertionHelpers.assert_success_response(result2)

        # Ensure same agent again (should reactivate)
        result3 = await ensure_agent(
            project_id=self.project.id,
            agent_name="test_agent"
        )
        AssertionHelpers.assert_success_response(result3)
        assert result3["is_reopen"] is True

    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self):
        """Test concurrent agent operations"""
        import asyncio

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        ensure_agent = registrar.get_registered_tool("ensure_agent")

        # Run multiple concurrent agent creations
        tasks = [
            ensure_agent(
                project_id=self.project.id,
                agent_name=f"agent_{i}"
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            AssertionHelpers.assert_success_response(result)

    @pytest.mark.asyncio
    async def test_agent_hierarchy_management(self):
        """Test managing agent hierarchies with sub-agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent agent
        async with self.db_manager.get_session_async() as session:
            parent = await ToolsTestHelper.create_test_agent(
                session, self.project.id, "orchestrator"
            )

        register_agent_tools(mock_server, self.db_manager, self.tenant_manager)
        spawn_sub_agent = registrar.get_registered_tool("spawn_and_log_sub_agent")
        log_completion = registrar.get_registered_tool("log_sub_agent_completion")

        # Spawn sub-agent
        spawn_result = await spawn_sub_agent(
            parent_agent="orchestrator",
            sub_agent_name="analyzer",
            sub_agent_type="code_analyzer",
            mission="Analyze codebase",
            project_id=self.project.id
        )
        AssertionHelpers.assert_success_response(spawn_result)

        # Complete sub-agent work
        completion_result = await log_completion(
            sub_agent_log_id=spawn_result["log_id"],
            completion_status="success",
            results_summary="Analysis completed"
        )
        AssertionHelpers.assert_success_response(completion_result)

        # Verify hierarchy is tracked
        agent_health = registrar.get_registered_tool("agent_health")
        health_result = await agent_health(agent_name="orchestrator")
        AssertionHelpers.assert_success_response(health_result)
        assert "sub_agents" in health_result["health"]