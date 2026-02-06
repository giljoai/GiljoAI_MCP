"""
Tests for MCP Tool Catalog injection in ToolAccessor.get_orchestrator_instructions.

Following TDD principles:
1. Write tests FIRST (RED ❌)
2. Implement minimal code to pass tests (GREEN ✅)
3. Refactor if needed
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


class TestToolAccessorMCPCatalog:
    """Test suite for MCP Tool Catalog injection in ToolAccessor."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        session = AsyncMock()
        db_manager.get_session_async.return_value.__aenter__.return_value = session
        return db_manager

    @pytest.fixture
    def mock_tenant_manager(self):
        """Create mock tenant manager."""
        return MagicMock()

    @pytest.fixture
    def tool_accessor(self, mock_db_manager, mock_tenant_manager):
        """Create ToolAccessor instance with mock database manager and tenant manager."""
        return ToolAccessor(mock_db_manager, mock_tenant_manager)

    def setup_mock_session(self, session, mock_orchestrator_job, mock_project, mock_product):
        """Helper to setup database mock responses consistently."""
        # Mock database query results
        orchestrator_result = MagicMock()
        orchestrator_result.scalar_one_or_none = MagicMock(return_value=mock_orchestrator_job)

        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=mock_project)

        product_result = MagicMock()
        product_result.scalar_one_or_none = MagicMock(return_value=mock_product)

        templates_result = MagicMock()
        templates_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        # session.execute should return results in order
        async def mock_execute(*args, **kwargs):
            if not hasattr(mock_execute, "call_count"):
                mock_execute.call_count = 0
            mock_execute.call_count += 1

            if mock_execute.call_count == 1:
                return orchestrator_result
            elif mock_execute.call_count == 2:
                return project_result
            elif mock_execute.call_count == 3:
                return product_result
            else:
                return templates_result

        session.execute = mock_execute

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_includes_mcp_catalog_when_priority_enabled(
        self,
        tool_accessor,
        mock_db_manager,
    ):
        """
        Test that MCP tool catalog is included when field priority > 0.

        Expected behavior:
        1. Check field_priorities.get("mcp_tool_catalog", 1) > 0
        2. Generate catalog using MCPToolCatalogGenerator
        3. Append catalog to mission with separator
        4. Log catalog injection
        """
        # Create mock job with MCP catalog enabled
        mock_orchestrator_job = MagicMock()
        mock_orchestrator_job.job_id = "orch-123"
        mock_orchestrator_job.tenant_key = "tenant-abc"
        mock_orchestrator_job.agent_display_name = "orchestrator"
        mock_orchestrator_job.project_id = "proj-456"
        mock_orchestrator_job.context_budget = 150000
        mock_orchestrator_job.context_used = 0
        mock_orchestrator_job.job_metadata = {
            "field_priorities": {
                "product_core": 1,
                "mcp_tool_catalog": 1,  # Enabled
            },
            "user_id": "user-789",
        }

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = "proj-456"
        mock_project.tenant_key = "tenant-abc"
        mock_project.name = "Test Project"
        mock_project.description = "Test project description"
        mock_project.product_id = "prod-123"

        # Create mock product
        mock_product = MagicMock()
        mock_product.id = "prod-123"
        mock_product.tenant_key = "tenant-abc"
        mock_product.vision_summary = "Test vision"
        mock_product.product_context = {}
        mock_product.vision_documents = []

        # Setup session mock
        session = mock_db_manager.get_session_async.return_value.__aenter__.return_value
        self.setup_mock_session(session, mock_orchestrator_job, mock_project, mock_product)

        # Mock MissionPlanner to return simple mission
        with patch("giljo_mcp.mission_planner.MissionPlanner") as mock_planner_class:
            mock_planner = AsyncMock()
            mock_planner._build_context_with_priorities.return_value = "Base mission content"
            mock_planner_class.return_value = mock_planner

            # Mock config.yaml to disable Serena (to isolate MCP catalog test)
            with patch("builtins.open", side_effect=FileNotFoundError):
                # Act
                result = await tool_accessor.get_orchestrator_instructions(
                    orchestrator_id="orch-123",
                    tenant_key="tenant-abc"
                )

        # Assert
        assert result["orchestrator_id"] == "orch-123"
        assert "mission" in result
        mission = result["mission"]

        # Verify MCP catalog is included in mission
        assert "# MCP Tool Catalog" in mission, "MCP Tool Catalog header should be in mission"
        assert "---" in mission, "Separator should be present"
        assert "Base mission content" in mission, "Base mission should be preserved"

        # Verify catalog appears AFTER base mission (appended)
        base_index = mission.index("Base mission content")
        catalog_index = mission.index("# MCP Tool Catalog")
        assert catalog_index > base_index, "MCP catalog should be appended after base mission"

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_excludes_mcp_catalog_when_priority_zero(
        self,
        tool_accessor,
        mock_db_manager,
    ):
        """
        Test that MCP tool catalog is excluded when field priority = 0.

        Expected behavior:
        1. Check field_priorities.get("mcp_tool_catalog", 1) == 0
        2. Skip catalog generation entirely
        3. Mission should only contain base content
        """
        # Create mock job with MCP catalog DISABLED
        mock_orchestrator_job = MagicMock()
        mock_orchestrator_job.job_id = "orch-123"
        mock_orchestrator_job.tenant_key = "tenant-abc"
        mock_orchestrator_job.agent_display_name = "orchestrator"
        mock_orchestrator_job.project_id = "proj-456"
        mock_orchestrator_job.context_budget = 150000
        mock_orchestrator_job.context_used = 0
        mock_orchestrator_job.job_metadata = {
            "field_priorities": {
                "product_core": 1,
                "mcp_tool_catalog": 0,  # DISABLED
            },
            "user_id": "user-789",
        }

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = "proj-456"
        mock_project.tenant_key = "tenant-abc"
        mock_project.name = "Test Project"
        mock_project.description = "Test project description"
        mock_project.product_id = "prod-123"

        # Create mock product
        mock_product = MagicMock()
        mock_product.id = "prod-123"
        mock_product.tenant_key = "tenant-abc"
        mock_product.vision_summary = "Test vision"
        mock_product.product_context = {}
        mock_product.vision_documents = []

        # Setup session mock
        session = mock_db_manager.get_session_async.return_value.__aenter__.return_value
        self.setup_mock_session(session, mock_orchestrator_job, mock_project, mock_product)

        # Mock MissionPlanner
        with patch("giljo_mcp.mission_planner.MissionPlanner") as mock_planner_class:
            mock_planner = AsyncMock()
            mock_planner._build_context_with_priorities.return_value = "Base mission content"
            mock_planner_class.return_value = mock_planner

            # Mock config.yaml
            with patch("builtins.open", side_effect=FileNotFoundError):
                # Act
                result = await tool_accessor.get_orchestrator_instructions(
                    orchestrator_id="orch-123",
                    tenant_key="tenant-abc"
                )

        # Assert
        assert result["orchestrator_id"] == "orch-123"
        assert "mission" in result
        mission = result["mission"]

        # Verify MCP catalog is NOT included
        assert "# MCP Tool Catalog" not in mission, "MCP Tool Catalog should be excluded when priority=0"
        assert "Base mission content" in mission, "Base mission should still be present"

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_uses_default_priority_when_not_in_metadata(
        self,
        tool_accessor,
        mock_db_manager,
    ):
        """
        Test that MCP catalog uses default priority (1) when not specified in metadata.

        Expected behavior:
        1. field_priorities.get("mcp_tool_catalog", 1) returns 1 (default)
        2. Catalog should be included by default
        3. Fallback to default is safer than excluding
        """
        # Create mock job WITHOUT mcp_tool_catalog in field_priorities
        mock_orchestrator_job = MagicMock()
        mock_orchestrator_job.job_id = "orch-123"
        mock_orchestrator_job.tenant_key = "tenant-abc"
        mock_orchestrator_job.agent_display_name = "orchestrator"
        mock_orchestrator_job.project_id = "proj-456"
        mock_orchestrator_job.context_budget = 150000
        mock_orchestrator_job.context_used = 0
        mock_orchestrator_job.job_metadata = {
            "field_priorities": {
                "product_core": 1,
                # mcp_tool_catalog NOT specified - should default to 1
            },
            "user_id": "user-789",
        }

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = "proj-456"
        mock_project.tenant_key = "tenant-abc"
        mock_project.name = "Test Project"
        mock_project.description = "Test project description"
        mock_project.product_id = "prod-123"

        # Create mock product
        mock_product = MagicMock()
        mock_product.id = "prod-123"
        mock_product.tenant_key = "tenant-abc"
        mock_product.vision_summary = "Test vision"
        mock_product.product_context = {}
        mock_product.vision_documents = []

        # Setup session mock
        session = mock_db_manager.get_session_async.return_value.__aenter__.return_value
        self.setup_mock_session(session, mock_orchestrator_job, mock_project, mock_product)

        # Mock MissionPlanner
        with patch("giljo_mcp.mission_planner.MissionPlanner") as mock_planner_class:
            mock_planner = AsyncMock()
            mock_planner._build_context_with_priorities.return_value = "Base mission content"
            mock_planner_class.return_value = mock_planner

            # Mock config.yaml
            with patch("builtins.open", side_effect=FileNotFoundError):
                # Act
                result = await tool_accessor.get_orchestrator_instructions(
                    orchestrator_id="orch-123",
                    tenant_key="tenant-abc"
                )

        # Assert
        assert result["orchestrator_id"] == "orch-123"
        assert "mission" in result
        mission = result["mission"]

        # Verify MCP catalog IS included (default priority = 1)
        assert "# MCP Tool Catalog" in mission, "MCP Tool Catalog should be included by default"
        assert "Base mission content" in mission, "Base mission should be preserved"

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_handles_catalog_generation_exception(
        self,
        tool_accessor,
        mock_db_manager,
    ):
        """
        Test graceful handling of catalog generation exceptions.

        Expected behavior:
        1. If MCPToolCatalogGenerator raises exception, catch it
        2. Log warning
        3. Continue without catalog (mission still returned)
        4. No error returned to caller
        """
        # Create mock job
        mock_orchestrator_job = MagicMock()
        mock_orchestrator_job.job_id = "orch-123"
        mock_orchestrator_job.tenant_key = "tenant-abc"
        mock_orchestrator_job.agent_display_name = "orchestrator"
        mock_orchestrator_job.project_id = "proj-456"
        mock_orchestrator_job.context_budget = 150000
        mock_orchestrator_job.context_used = 0
        mock_orchestrator_job.job_metadata = {
            "field_priorities": {
                "product_core": 1,
                "mcp_tool_catalog": 1,  # Enabled but will fail
            },
            "user_id": "user-789",
        }

        # Create mock project
        mock_project = MagicMock()
        mock_project.id = "proj-456"
        mock_project.tenant_key = "tenant-abc"
        mock_project.name = "Test Project"
        mock_project.description = "Test project description"
        mock_project.product_id = "prod-123"

        # Create mock product
        mock_product = MagicMock()
        mock_product.id = "prod-123"
        mock_product.tenant_key = "tenant-abc"
        mock_product.vision_summary = "Test vision"
        mock_product.product_context = {}
        mock_product.vision_documents = []

        # Setup session mock
        session = mock_db_manager.get_session_async.return_value.__aenter__.return_value
        self.setup_mock_session(session, mock_orchestrator_job, mock_project, mock_product)

        # Mock MissionPlanner
        with patch("giljo_mcp.mission_planner.MissionPlanner") as mock_planner_class:
            mock_planner = AsyncMock()
            mock_planner._build_context_with_priorities.return_value = "Base mission content"
            mock_planner_class.return_value = mock_planner

            # Mock MCPToolCatalogGenerator to raise exception
            with patch("giljo_mcp.prompt_generation.mcp_tool_catalog.MCPToolCatalogGenerator") as mock_catalog_class:
                mock_catalog_class.return_value.generate_full_catalog.side_effect = Exception("Catalog generation failed")

                # Mock config.yaml
                with patch("builtins.open", side_effect=FileNotFoundError):
                    # Act
                    result = await tool_accessor.get_orchestrator_instructions(
                        orchestrator_id="orch-123",
                        tenant_key="tenant-abc"
                    )

        # Assert
        assert result["orchestrator_id"] == "orch-123"
        assert "mission" in result
        assert "error" not in result, "Should not return error when catalog generation fails"
        mission = result["mission"]

        # Verify base mission is present but catalog is not
        assert "Base mission content" in mission, "Base mission should still be present"
        assert "# MCP Tool Catalog" not in mission, "Failed catalog should not be included"
