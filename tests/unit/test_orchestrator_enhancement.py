"""
Unit tests for ProjectOrchestrator Phase 2 enhancements.

Tests the 4 new orchestration methods:
- process_product_vision() - Main orchestration workflow
- generate_mission_plan() - Mission generation
- select_agents_for_mission() - Agent selection delegation
- coordinate_agent_workflow() - Workflow coordination delegation

Critical: All existing tests must continue to pass - no breaking changes!
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.enums import AgentRole, ProjectStatus
from src.giljo_mcp.models import Product
from src.giljo_mcp.orchestrator import ProjectOrchestrator


@pytest.fixture
def orch_with_mocks(db_manager):
    """Create orchestrator with mocked Phase 1 components"""
    # Initialize global database manager before creating orchestrator
    from src.giljo_mcp.database import get_db_manager

    get_db_manager(database_url=db_manager.database_url, is_async=True)

    orch = ProjectOrchestrator()

    # Mock the Phase 1 components that don't exist yet
    orch.mission_planner = Mock()
    orch.mission_planner.analyze_requirements = AsyncMock(
        return_value=Mock(complexity="medium", agent_roles=["orchestrator", "analyzer"])
    )
    orch.mission_planner.generate_missions = AsyncMock(
        return_value={
            "orchestrator": Mock(agent_role="orchestrator", token_count=1000, to_dict=lambda: {"role": "orchestrator"}),
            "analyzer": Mock(agent_role="analyzer", token_count=1000, to_dict=lambda: {"role": "analyzer"}),
        }
    )

    orch.agent_selector = Mock()
    orch.agent_selector.select_agents = AsyncMock(
        return_value=[Mock(role="orchestrator", mission=None), Mock(role="analyzer", mission=None)]
    )

    orch.workflow_engine = Mock()
    orch.workflow_engine.execute_workflow = AsyncMock(
        return_value=Mock(status="completed", completed=[Mock(stage=1, job_ids=["job-1"])], failed=[])
    )

    return orch


class TestOrchestratorEnhancement:
    """Test suite for ProjectOrchestrator Phase 2 enhancements"""

    # ==================== Initialization Tests ====================

    @pytest.mark.asyncio
    async def test_init_enhancement(self, db_manager):
        """Test that __init__ properly initializes new components"""
        # Initialize global database manager before creating orchestrator
        from src.giljo_mcp.database import get_db_manager

        get_db_manager(database_url=db_manager.database_url, is_async=True)

        orch = ProjectOrchestrator()

        # Verify new components are initialized
        assert hasattr(orch, "mission_planner")
        assert hasattr(orch, "agent_selector")
        assert hasattr(orch, "workflow_engine")

        # Verify existing components still present
        assert hasattr(orch, "db_manager")
        assert hasattr(orch, "template_generator")

    # ==================== generate_mission_plan() Tests ====================

    @pytest.mark.asyncio
    async def test_generate_mission_plan_exists(self, orch_with_mocks):
        """Test that generate_mission_plan method exists and is callable"""
        assert hasattr(orch_with_mocks, "generate_mission_plan")
        assert callable(orch_with_mocks.generate_mission_plan)

    # ==================== select_agents_for_mission() Tests ====================

    @pytest.mark.asyncio
    async def test_select_agents_for_mission_exists(self, orch_with_mocks):
        """Test that select_agents_for_mission method exists and is callable"""
        assert hasattr(orch_with_mocks, "select_agents_for_mission")
        assert callable(orch_with_mocks.select_agents_for_mission)

    # ==================== coordinate_agent_workflow() Tests ====================

    @pytest.mark.asyncio
    async def test_coordinate_agent_workflow_exists(self, orch_with_mocks):
        """Test that coordinate_agent_workflow method exists and is callable"""
        assert hasattr(orch_with_mocks, "coordinate_agent_workflow")
        assert callable(orch_with_mocks.coordinate_agent_workflow)

    # ==================== process_product_vision() Tests ====================

    @pytest.mark.asyncio
    async def test_process_product_vision_exists(self, orch_with_mocks):
        """Test that process_product_vision method exists and is callable"""
        assert hasattr(orch_with_mocks, "process_product_vision")
        assert callable(orch_with_mocks.process_product_vision)

    @pytest.mark.asyncio
    async def test_process_product_vision_product_not_found(self, orch_with_mocks, db_manager):
        """Test that process_product_vision raises error for non-existent product"""
        fake_product_id = "00000000-0000-0000-0000-000000000000"
        tenant_key = db_manager.generate_tenant_key()

        with pytest.raises(ValueError, match="not found"):
            await orch_with_mocks.process_product_vision(
                tenant_key=tenant_key, product_id=fake_product_id, project_requirements="Cannot find product"
            )

    @pytest.mark.asyncio
    async def test_process_product_vision_no_vision_raises_error(self, orch_with_mocks, db_manager):
        """Test that process_product_vision raises error when product has no vision"""
        tenant_key = db_manager.generate_tenant_key()

        # Create product without vision
        async with db_manager.get_session_async() as session:
            product = Product(tenant_key=tenant_key, name="No Vision Product", vision_type="none")
            session.add(product)
            await session.commit()
            await session.refresh(product)

            product_id = product.id

        # Should raise ValueError
        with pytest.raises(ValueError, match="has no vision document"):
            await orch_with_mocks.process_product_vision(
                tenant_key=tenant_key, product_id=product_id, project_requirements="Cannot process"
            )

    @pytest.mark.asyncio
    async def test_process_product_vision_inline_success(self, orch_with_mocks, db_manager):
        """Test full process_product_vision workflow with inline vision"""
        tenant_key = db_manager.generate_tenant_key()

        # Create product with inline vision (already chunked)
        async with db_manager.get_session_async() as session:
            product = Product(
                tenant_key=tenant_key,
                name="Test Product",
                vision_document="This is a test vision document.",
                vision_type="inline",
                chunked=True,
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)

            product_id = product.id

        # Execute full workflow
        result = await orch_with_mocks.process_product_vision(
            tenant_key=tenant_key, product_id=product_id, project_requirements="Build a web application"
        )

        # Assertions
        assert result is not None
        assert "project_id" in result
        assert "mission_plan" in result
        assert "selected_agents" in result
        assert "spawned_jobs" in result
        assert "workflow_result" in result
        assert "token_reduction" in result

    # ==================== No Breaking Changes Tests ====================

    @pytest.mark.asyncio
    async def test_existing_methods_unchanged(self, db_manager):
        """Verify existing methods still work correctly - no breaking changes"""
        # Initialize global database manager
        from src.giljo_mcp.database import get_db_manager

        get_db_manager(database_url=db_manager.database_url, is_async=True)

        orch = ProjectOrchestrator()
        tenant_key = db_manager.generate_tenant_key()

        # Test create_project (existing method)
        project = await orch.create_project(
            name="Legacy Test Project",
            mission="Test existing functionality",
            tenant_key=tenant_key,
            context_budget=150000,
        )

        assert project is not None
        assert project.name == "Legacy Test Project"
        assert project.status == ProjectStatus.PLANNING.value

        # Test spawn_agent (existing method)
        agent = await orch.spawn_agent(project_id=project.id, role=AgentRole.ANALYZER)

        assert agent is not None
        assert agent.role == AgentRole.ANALYZER.value
        assert agent.project_id == project.id

    @pytest.mark.asyncio
    async def test_existing_context_tracking_unchanged(self, db_manager):
        """Verify existing context tracking methods unchanged"""
        # Initialize global database manager
        from src.giljo_mcp.database import get_db_manager

        get_db_manager(database_url=db_manager.database_url, is_async=True)

        orch = ProjectOrchestrator()
        tenant_key = db_manager.generate_tenant_key()

        # Create project and agent
        project = await orch.create_project(name="Context Test", mission="Test context", tenant_key=tenant_key)

        agent = await orch.spawn_agent(project_id=project.id, role=AgentRole.IMPLEMENTER)

        # Test update_context_usage (existing method)
        updated_agent = await orch.update_context_usage(agent_id=agent.id, tokens_used=5000)

        assert updated_agent.context_used == 5000

        # Test get_agent_context_status (existing method)
        status = await orch.get_agent_context_status(agent.id)
        assert status["context_used"] == 5000
        assert status["usage_percentage"] < 100
