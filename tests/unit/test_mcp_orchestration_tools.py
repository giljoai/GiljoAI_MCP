"""
Comprehensive tests for orchestration.py tools (Handover 0020 Phase 3B)
Target: 95%+ coverage with TDD approach

Tests MCP tools for intelligent multi-agent orchestration:
- orchestrate_project
- get_agent_mission
- get_workflow_status

Following TDD: Write tests FIRST, then implement to make them pass.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from tests.utils.tools_helpers import MockMCPToolRegistrar, ToolsTestHelper


class TestOrchestrationTools:
    """Test class for orchestration MCP tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Generate valid tenant key (tk_ + 32 alphanumeric chars)
        self.tenant_key = TenantManager.generate_tenant_key()

        # Create test project and product
        async with self.db_manager.get_session_async() as session:
            from src.giljo_mcp.models import Product

            # Create test product with vision
            self.product = Product(
                id=str(uuid.uuid4()),
                name="Test Product",
                description="Test product for orchestration",
                tenant_key=self.tenant_key,
                vision_type="inline",
                vision_document="# Test Vision\n\nThis is a test product vision document.",
                chunked=True,
            )
            session.add(self.product)

            # Create test project
            self.project = await ToolsTestHelper.create_test_project(session, "Orchestration Test Project")
            self.project.tenant_key = self.tenant_key
            self.project.product_id = self.product.id
            await session.commit()

            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_orchestration_tools(self):
        """Test that orchestration tools are registered properly"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_orchestration_tools(mock_server, self.db_manager)

        # Should register orchestration tools
        registered_tools = registrar.get_all_tools()
        expected_tools = [
            "orchestrate_project",
            "get_agent_mission",
            "get_workflow_status",
        ]

        for tool_name in expected_tools:
            assert tool_name in registered_tools, f"Tool {tool_name} not registered. Available: {registered_tools}"

    @pytest.mark.asyncio
    async def test_orchestrate_project_success(self):
        """Test orchestrate_project tool - happy path"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock ProjectOrchestrator
        with patch("src.giljo_mcp.tools.orchestration.ProjectOrchestrator") as mock_orch_class:
            mock_orchestrator = Mock()
            mock_orchestrator.process_product_vision = AsyncMock(
                return_value={
                    "project_id": self.project.id,
                    "mission_plan": {"missions": [{"agent_type": "implementer", "mission": "Implement features"}]},
                    "selected_agents": ["implementer", "tester"],
                    "spawned_jobs": ["job-1", "job-2"],
                    "workflow_result": Mock(status="completed"),
                    "token_reduction": {"reduction_percent": 70.0},
                }
            )
            mock_orch_class.return_value = mock_orchestrator

            # Mock database session
            with patch.object(self.db_manager, "get_session_async") as mock_session:
                mock_db_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db_session

                # Mock project lookup
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = Mock(
                    id=self.project.id,
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    mission="Test mission",
                )
                mock_db_session.execute = AsyncMock(return_value=mock_result)

                register_orchestration_tools(mock_server, self.db_manager)
                orchestrate_project = registrar.get_registered_tool("orchestrate_project")

                result = await orchestrate_project(project_id=self.project.id, tenant_key=self.tenant_key)

                # Verify results
                assert isinstance(result, dict)
                assert result.get("project_id") == self.project.id
                assert "mission_plan" in result
                assert "selected_agents" in result
                assert "spawned_jobs" in result
                assert len(result["spawned_jobs"]) == 2
                assert result.get("token_reduction", {}).get("reduction_percent") == 70.0

    @pytest.mark.asyncio
    async def test_orchestrate_project_not_found(self):
        """Test orchestrate_project when project doesn't exist"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project not found
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            orchestrate_project = registrar.get_registered_tool("orchestrate_project")

            result = await orchestrate_project(project_id=str(uuid.uuid4()), tenant_key=self.tenant_key)

            # Should return error
            assert isinstance(result, dict)
            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_orchestrate_project_tenant_mismatch(self):
        """Test orchestrate_project with wrong tenant key"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Generate a different valid tenant key
        different_tenant_key = TenantManager.generate_tenant_key()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project not found due to tenant mismatch (WHERE clause filters it out)
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None  # Query with tenant filter returns None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            orchestrate_project = registrar.get_registered_tool("orchestrate_project")

            result = await orchestrate_project(project_id=self.project.id, tenant_key=different_tenant_key)

            # Should return not found (tenant isolation)
            assert isinstance(result, dict)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_orchestrate_project_orchestrator_failure(self):
        """Test orchestrate_project when orchestrator fails"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock ProjectOrchestrator with failure
        with patch("src.giljo_mcp.tools.orchestration.ProjectOrchestrator") as mock_orch_class:
            mock_orchestrator = Mock()
            mock_orchestrator.process_product_vision = AsyncMock(
                side_effect=ValueError("Orchestration failed: Invalid vision")
            )
            mock_orch_class.return_value = mock_orchestrator

            # Mock database session
            with patch.object(self.db_manager, "get_session_async") as mock_session:
                mock_db_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db_session

                # Mock project lookup
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = Mock(
                    id=self.project.id,
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    mission="Test mission",
                )
                mock_db_session.execute = AsyncMock(return_value=mock_result)

                register_orchestration_tools(mock_server, self.db_manager)
                orchestrate_project = registrar.get_registered_tool("orchestrate_project")

                result = await orchestrate_project(project_id=self.project.id, tenant_key=self.tenant_key)

                # Should return error
                assert isinstance(result, dict)
                assert "error" in result
                assert "Invalid vision" in result["error"]

    @pytest.mark.asyncio
    async def test_get_agent_mission_success(self):
        """Test get_agent_mission tool - happy path"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock agent lookup with mission (using MCPAgentJob)
            from src.giljo_mcp.models import MCPAgentJob

            mock_agent = Mock(spec=MCPAgentJob)
            mock_agent.job_id = str(uuid.uuid4())
            mock_agent.agent_name = "implementer"
            mock_agent.tenant_key = self.tenant_key
            mock_agent.mission = "# Mission: Implement Features\n\nImplement the required features."

            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            get_agent_mission = registrar.get_registered_tool("get_agent_mission")

            result = await get_agent_mission(agent_id=mock_agent.job_id, tenant_key=self.tenant_key)

            # Verify markdown mission returned
            assert isinstance(result, dict)
            assert "mission" in result
            assert result["mission"].startswith("# Mission:")
            assert "Implement Features" in result["mission"]

    @pytest.mark.asyncio
    async def test_get_agent_mission_not_found(self):
        """Test get_agent_mission when agent doesn't exist"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock agent not found
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            get_agent_mission = registrar.get_registered_tool("get_agent_mission")

            result = await get_agent_mission(agent_id=str(uuid.uuid4()), tenant_key=self.tenant_key)

            # Should return error
            assert isinstance(result, dict)
            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_agent_mission_no_mission(self):
        """Test get_agent_mission when agent has no mission"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock agent without mission (using MCPAgentJob)
            from src.giljo_mcp.models import MCPAgentJob

            mock_agent = Mock(spec=MCPAgentJob)
            mock_agent.job_id = str(uuid.uuid4())
            mock_agent.agent_name = "implementer"
            mock_agent.tenant_key = self.tenant_key
            mock_agent.mission = None  # No mission!

            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            get_agent_mission = registrar.get_registered_tool("get_agent_mission")

            result = await get_agent_mission(agent_id=mock_agent.job_id, tenant_key=self.tenant_key)

            # Should return error
            assert isinstance(result, dict)
            assert "error" in result
            assert "no mission" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self):
        """Test get_workflow_status tool - happy path"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project_result = Mock()
            mock_project_result.scalar_one_or_none.return_value = Mock(id=self.project.id, tenant_key=self.tenant_key)

            # Mock MCPAgentJob lookup
            from src.giljo_mcp.models import MCPAgentJob

            mock_jobs = [
                Mock(
                    spec=MCPAgentJob,
                    id=1,
                    job_id="job-1",
                    status="completed",
                    agent_type="implementer",
                ),
                Mock(
                    spec=MCPAgentJob,
                    id=2,
                    job_id="job-2",
                    status="completed",
                    agent_type="tester",
                ),
                Mock(
                    spec=MCPAgentJob,
                    id=3,
                    job_id="job-3",
                    status="active",
                    agent_type="documenter",
                ),
            ]

            mock_jobs_result = Mock()
            mock_jobs_result.scalars.return_value.all.return_value = mock_jobs

            # Execute returns different results for different queries
            mock_db_session.execute = AsyncMock(side_effect=[mock_project_result, mock_jobs_result])

            register_orchestration_tools(mock_server, self.db_manager)
            get_workflow_status = registrar.get_registered_tool("get_workflow_status")

            result = await get_workflow_status(project_id=self.project.id, tenant_key=self.tenant_key)

            # Verify status
            assert isinstance(result, dict)
            assert result["active_agents"] == 1
            assert result["completed_agents"] == 2
            assert result["failed_agents"] == 0
            assert "progress_percent" in result
            assert result["progress_percent"] > 0

    @pytest.mark.asyncio
    async def test_get_workflow_status_no_jobs(self):
        """Test get_workflow_status when no jobs exist"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project_result = Mock()
            mock_project_result.scalar_one_or_none.return_value = Mock(id=self.project.id, tenant_key=self.tenant_key)

            # Mock no jobs
            mock_jobs_result = Mock()
            mock_jobs_result.scalars.return_value.all.return_value = []

            mock_db_session.execute = AsyncMock(side_effect=[mock_project_result, mock_jobs_result])

            register_orchestration_tools(mock_server, self.db_manager)
            get_workflow_status = registrar.get_registered_tool("get_workflow_status")

            result = await get_workflow_status(project_id=self.project.id, tenant_key=self.tenant_key)

            # Should return zero counts
            assert isinstance(result, dict)
            assert result["active_agents"] == 0
            assert result["completed_agents"] == 0
            assert result["failed_agents"] == 0
            assert result["progress_percent"] == 0.0
            assert result["current_stage"] == "Not started"

    @pytest.mark.asyncio
    async def test_get_workflow_status_project_not_found(self):
        """Test get_workflow_status when project doesn't exist"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project not found
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            get_workflow_status = registrar.get_registered_tool("get_workflow_status")

            result = await get_workflow_status(project_id=str(uuid.uuid4()), tenant_key=self.tenant_key)

            # Should return error
            assert isinstance(result, dict)
            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_orchestration_tools_error_handling(self):
        """Test orchestration tools error handling"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database error
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            register_orchestration_tools(mock_server, self.db_manager)
            orchestrate_project = registrar.get_registered_tool("orchestrate_project")

            result = await orchestrate_project(project_id=self.project.id, tenant_key="tk_test")

            # Should handle error gracefully
            assert isinstance(result, dict)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_workflow_status_with_failed_jobs(self):
        """Test get_workflow_status with failed jobs"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project_result = Mock()
            mock_project_result.scalar_one_or_none.return_value = Mock(id=self.project.id, tenant_key=self.tenant_key)

            # Mock jobs with failures
            from src.giljo_mcp.models import MCPAgentJob

            mock_jobs = [
                Mock(
                    spec=MCPAgentJob,
                    id=1,
                    job_id="job-1",
                    status="failed",
                    agent_type="implementer",
                ),
                Mock(
                    spec=MCPAgentJob,
                    id=2,
                    job_id="job-2",
                    status="completed",
                    agent_type="tester",
                ),
            ]

            mock_jobs_result = Mock()
            mock_jobs_result.scalars.return_value.all.return_value = mock_jobs

            mock_db_session.execute = AsyncMock(side_effect=[mock_project_result, mock_jobs_result])

            register_orchestration_tools(mock_server, self.db_manager)
            get_workflow_status = registrar.get_registered_tool("get_workflow_status")

            result = await get_workflow_status(project_id=self.project.id, tenant_key=self.tenant_key)

            # Verify failed count
            assert isinstance(result, dict)
            assert result["failed_agents"] == 1
            assert result["completed_agents"] == 1

    @pytest.mark.asyncio
    async def test_orchestrate_project_invalid_alias_format(self):
        """Test orchestrate_project with invalid alias format"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock no project found
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            orchestrate_project = registrar.get_registered_tool("orchestrate_project")

            # Test with invalid alias (too long, special chars, etc.)
            result = await orchestrate_project(
                project_id=str(uuid.uuid4()),
                tenant_key=self.tenant_key,
            )

            # Should return error
            assert isinstance(result, dict)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_agent_mission_tenant_isolation(self):
        """Test get_agent_mission enforces tenant isolation"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Generate a different valid tenant key
        different_tenant_key = TenantManager.generate_tenant_key()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock agent not found due to tenant mismatch (WHERE clause filters it out)
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None  # Query with tenant filter returns None
            mock_db_session.execute = AsyncMock(return_value=mock_result)

            register_orchestration_tools(mock_server, self.db_manager)
            get_agent_mission = registrar.get_registered_tool("get_agent_mission")

            result = await get_agent_mission(agent_id=str(uuid.uuid4()), tenant_key=different_tenant_key)

            # Should return not found due to tenant mismatch
            assert isinstance(result, dict)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_orchestrate_project_null_tenant_key(self):
        """Test orchestrate_project with null/empty tenant key"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_orchestration_tools(mock_server, self.db_manager)
        orchestrate_project = registrar.get_registered_tool("orchestrate_project")

        # Test with empty tenant key
        result = await orchestrate_project(project_id=self.project.id, tenant_key="")

        # Should handle gracefully
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_workflow_status_calculates_progress(self):
        """Test get_workflow_status correctly calculates progress percentage"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database session
        with patch.object(self.db_manager, "get_session_async") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project
            mock_project_result = Mock()
            mock_project_result.scalar_one_or_none.return_value = Mock(id=self.project.id, tenant_key=self.tenant_key)

            # Mock 5 jobs: 3 completed, 1 active, 1 pending
            from src.giljo_mcp.models import MCPAgentJob

            mock_jobs = [
                Mock(spec=MCPAgentJob, status="completed"),
                Mock(spec=MCPAgentJob, status="completed"),
                Mock(spec=MCPAgentJob, status="completed"),
                Mock(spec=MCPAgentJob, status="active"),
                Mock(spec=MCPAgentJob, status="waiting"),
            ]

            mock_jobs_result = Mock()
            mock_jobs_result.scalars.return_value.all.return_value = mock_jobs

            mock_db_session.execute = AsyncMock(side_effect=[mock_project_result, mock_jobs_result])

            register_orchestration_tools(mock_server, self.db_manager)
            get_workflow_status = registrar.get_registered_tool("get_workflow_status")

            result = await get_workflow_status(project_id=self.project.id, tenant_key=self.tenant_key)

            # Progress should be 3/5 = 60%
            assert result["completed_agents"] == 3
            assert result["progress_percent"] == 60.0
