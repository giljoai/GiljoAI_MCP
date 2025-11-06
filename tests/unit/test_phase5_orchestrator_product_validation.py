"""
Unit tests for Phase 5 - Orchestrator Product Validation (Handover 0050).

Tests product is_active validation in:
- orchestrator.process_product_vision()
- orchestrator.spawn_agent()

Ensures agents can only be spawned for active products.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.enums import AgentRole
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.orchestrator import ProjectOrchestrator


class TestOrchestratorProductValidation:
    """Test product activation validation in orchestrator methods."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance with mocked db_manager."""
        with patch("src.giljo_mcp.orchestrator.get_db_manager") as mock_get_db:
            mock_db_manager = MagicMock()
            mock_get_db.return_value = mock_db_manager
            orchestrator = ProjectOrchestrator()
            orchestrator.db_manager = mock_db_manager
            yield orchestrator

    @pytest.fixture
    def active_product(self):
        """Create an active product fixture."""
        return Product(
            id="prod-active-123",
            tenant_key="tenant-test",
            name="Active Product",
            is_active=True,
            vision_type="inline",
            vision_document="Test vision content",
            chunked=True,
        )

    @pytest.fixture
    def inactive_product(self):
        """Create an inactive product fixture."""
        return Product(
            id="prod-inactive-456",
            tenant_key="tenant-test",
            name="Inactive Product",
            is_active=False,
            vision_type="inline",
            vision_document="Test vision content",
            chunked=True,
        )

    @pytest.fixture
    def test_project_with_active_product(self):
        """Create project linked to active product."""
        return Project(
            id="proj-123",
            tenant_key="tenant-test",
            product_id="prod-active-123",
            name="Test Project",
            mission="Test mission",
            status="active",
        )

    @pytest.fixture
    def test_project_with_inactive_product(self):
        """Create project linked to inactive product."""
        return Project(
            id="proj-456",
            tenant_key="tenant-test",
            product_id="prod-inactive-456",
            name="Test Project",
            mission="Test mission",
            status="active",
        )

    # ========================================================================
    # Test process_product_vision() with inactive product
    # ========================================================================

    @pytest.mark.asyncio
    async def test_process_product_vision_rejects_inactive_product(self, orchestrator, inactive_product):
        """Test that process_product_vision() rejects inactive products."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=inactive_product)
        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Attempt to process inactive product vision
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key="tenant-test", product_id="prod-inactive-456", project_requirements="Test requirements"
            )

        # Verify error message
        error_msg = str(exc_info.value)
        assert "not active" in error_msg
        assert "Inactive Product" in error_msg
        assert "Activate the product" in error_msg

    @pytest.mark.asyncio
    async def test_process_product_vision_accepts_active_product(self, orchestrator, active_product):
        """Test that process_product_vision() accepts active products."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=active_product)
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Mock downstream dependencies
        with patch.object(orchestrator, "create_project") as mock_create_project:
            mock_project = MagicMock()
            mock_project.id = "proj-123"
            mock_project.name = "Test Project"
            mock_create_project.return_value = mock_project

            with patch.object(orchestrator, "generate_mission_plan") as mock_gen_missions:
                mock_gen_missions.return_value = {}

                with patch.object(orchestrator.mission_planner, "analyze_requirements") as mock_analyze:
                    mock_analyze.return_value = MagicMock()

                    with patch.object(orchestrator, "select_agents_for_mission") as mock_select:
                        mock_select.return_value = []

                        with patch.object(orchestrator, "coordinate_agent_workflow") as mock_coord:
                            mock_result = MagicMock()
                            mock_result.status = "completed"
                            mock_result.completed = []
                            mock_coord.return_value = mock_result

                            # Should NOT raise error
                            result = await orchestrator.process_product_vision(
                                tenant_key="tenant-test",
                                product_id="prod-active-123",
                                project_requirements="Test requirements",
                            )

                            # Verify result structure
                            assert result is not None
                            assert "project_id" in result

    @pytest.mark.asyncio
    async def test_process_product_vision_product_not_found(self, orchestrator):
        """Test that process_product_vision() raises error for missing product."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=None)
        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Attempt to process non-existent product
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key="tenant-test", product_id="prod-nonexistent", project_requirements="Test requirements"
            )

        error_msg = str(exc_info.value)
        assert "not found" in error_msg

    # ========================================================================
    # Test spawn_agent() with inactive product
    # ========================================================================

    @pytest.mark.asyncio
    async def test_spawn_agent_rejects_inactive_product(
        self, orchestrator, test_project_with_inactive_product, inactive_product
    ):
        """Test that spawn_agent() rejects projects with inactive products."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none = MagicMock(return_value=test_project_with_inactive_product)
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.get = AsyncMock(return_value=inactive_product)

        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Attempt to spawn agent for project with inactive product
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.spawn_agent(project_id="proj-456", role=AgentRole.IMPLEMENTER)

        # Verify error message
        error_msg = str(exc_info.value)
        assert "not active" in error_msg
        assert "Inactive Product" in error_msg

    @pytest.mark.asyncio
    async def test_spawn_agent_accepts_active_product(
        self, orchestrator, test_project_with_active_product, active_product
    ):
        """Test that spawn_agent() accepts projects with active products."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none = MagicMock(return_value=test_project_with_active_product)
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.get = AsyncMock(return_value=active_product)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Mock downstream dependencies
        with patch.object(orchestrator, "_get_agent_template") as mock_get_template:
            mock_get_template.return_value = None  # Force fallback to legacy logic

            with patch.object(orchestrator.template_generator, "generate_agent_mission") as mock_gen_mission:
                mock_gen_mission.return_value = "Test mission"

                with patch.object(orchestrator, "_get_serena_optimizer") as mock_optimizer:
                    mock_optimizer.return_value = MagicMock()

                    # Should NOT raise error
                    agent = await orchestrator.spawn_agent(project_id="proj-123", role=AgentRole.IMPLEMENTER)

                    # Verify agent created
                    assert agent is not None
                    assert agent.role == AgentRole.IMPLEMENTER.value

    @pytest.mark.asyncio
    async def test_spawn_agent_project_without_product(self, orchestrator):
        """Test that spawn_agent() succeeds for projects without product_id."""
        # Create project without product_id
        project_no_product = Project(
            id="proj-no-prod",
            tenant_key="tenant-test",
            product_id=None,  # No product
            name="Standalone Project",
            mission="Test mission",
            status="active",
        )

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none = MagicMock(return_value=project_no_product)
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Mock downstream dependencies
        with patch.object(orchestrator, "_get_agent_template") as mock_get_template:
            mock_get_template.return_value = None

            with patch.object(orchestrator.template_generator, "generate_agent_mission") as mock_gen_mission:
                mock_gen_mission.return_value = "Test mission"

                with patch.object(orchestrator, "_get_serena_optimizer") as mock_optimizer:
                    mock_optimizer.return_value = MagicMock()

                    # Should NOT raise error (no product validation needed)
                    agent = await orchestrator.spawn_agent(project_id="proj-no-prod", role=AgentRole.TESTER)

                    assert agent is not None

    # ========================================================================
    # Multi-tenant isolation tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_process_product_vision_tenant_isolation(self, orchestrator, active_product):
        """Test that process_product_vision() enforces tenant isolation."""
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=active_product)
        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Attempt to access product with wrong tenant_key
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key="wrong-tenant", product_id="prod-active-123", project_requirements="Test requirements"
            )

        error_msg = str(exc_info.value)
        assert "not found" in error_msg

    # ========================================================================
    # Edge case tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_spawn_agent_product_becomes_inactive_race_condition(
        self, orchestrator, test_project_with_active_product
    ):
        """Test race condition where product becomes inactive during spawn."""
        # Mock database session where product is active first, then inactive
        mock_session = AsyncMock(spec=AsyncSession)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none = MagicMock(return_value=test_project_with_active_product)
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        # Return inactive product on second call
        inactive_prod = Product(
            id="prod-active-123", tenant_key="tenant-test", name="Previously Active", is_active=False
        )
        mock_session.get = AsyncMock(return_value=inactive_prod)

        orchestrator.db_manager.get_session_async = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session))
        )

        # Should reject due to inactive product
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.spawn_agent(project_id="proj-123", role=AgentRole.ANALYZER)

        error_msg = str(exc_info.value)
        assert "not active" in error_msg
