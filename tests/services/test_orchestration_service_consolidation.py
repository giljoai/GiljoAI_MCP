"""
Tests for OrchestrationService consolidation (Handover 0450).

These methods are being moved from orchestrator.py to OrchestrationService:
- process_product_vision() - Main orchestration workflow
- generate_mission_plan() - Generate missions from vision
- select_agents_for_mission() - Smart agent selection
- coordinate_agent_workflow() - Workflow coordination
- _get_agent_template_internal() - Template resolution with cascade

NOTE: spawn_agent_legacy() removed in 0700 cleanup - use spawn_agent_job() instead.

All tests should FAIL initially (RED phase) since the methods don't exist yet.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, Product

# These imports should work after implementation
from src.giljo_mcp.services.orchestration_service import OrchestrationService


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_mission_planner():
    """Mock MissionPlanner for testing."""
    planner = MagicMock()
    planner.analyze_requirements = AsyncMock(return_value={"required_agents": ["implementer", "tester"]})
    planner.generate_mission = AsyncMock(
        return_value={
            "implementer": MagicMock(token_count=1000, to_dict=MagicMock(return_value={"role": "implementer"})),
            "tester": MagicMock(token_count=800, to_dict=MagicMock(return_value={"role": "tester"})),
        }
    )
    return planner


@pytest.fixture
def mock_agent_selector():
    """Mock AgentSelector for testing."""
    selector = MagicMock()
    selector.select_agents = AsyncMock(
        return_value=[
            MagicMock(role="implementer", mission=None),
            MagicMock(role="tester", mission=None),
        ]
    )
    return selector


@pytest.fixture
def mock_workflow_engine():
    """Mock WorkflowEngine for testing."""
    engine = MagicMock()
    workflow_result = MagicMock()
    workflow_result.completed = [MagicMock(job_ids=["job-1", "job-2"])]
    workflow_result.failed = []
    workflow_result.status = "completed"
    engine.execute_workflow = AsyncMock(return_value=workflow_result)
    return engine


# ============================================================================
# TestProcessProductVision
# ============================================================================


class TestProcessProductVision:
    """Tests for process_product_vision() method."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Complex integration test - requires full database setup with eager loading of relationships"
    )
    async def test_creates_project_from_vision(
        self,
        db_session: AsyncSession,
        test_tenant_key,
        test_product,
        mock_mission_planner,
        mock_agent_selector,
        mock_workflow_engine,
    ):
        """Test process_product_vision creates project and returns workflow result."""
        # Create mock product with vision properties already set (avoid lazy loading)
        mock_product = MagicMock()
        mock_product.id = test_product.id
        mock_product.name = "Test Product"
        mock_product.tenant_key = test_tenant_key
        mock_product.is_active = True
        mock_product.vision_is_chunked = True  # Pre-chunked
        mock_product.primary_vision_storage_type = "inline"
        mock_product.primary_vision_text = "# Test Vision\nThis is a test vision document."
        mock_product.vision_documents = [MagicMock(chunked=True)]

        # Create a mock project that will be "created"
        created_project = MagicMock()
        created_project.id = str(uuid4())
        created_project.name = "Vision Project"
        created_project.mission = "Build authentication system"

        # Create service with mocked dependencies
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.mission_planner = mock_mission_planner
        service.agent_selector = mock_agent_selector
        service.workflow_engine = mock_workflow_engine

        # Mock the session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_product)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Use context manager that yields our mock session
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        service._get_session = mock_get_session

        # Mock ProjectService.create_project
        with patch("src.giljo_mcp.services.orchestration_service.ProjectService") as MockProjectService:
            mock_project_service = MagicMock()
            mock_project_service.create_project = AsyncMock(return_value=created_project)
            MockProjectService.return_value = mock_project_service

            # Act: Call process_product_vision()
            result = await service.process_product_vision(
                tenant_key=test_tenant_key,
                product_id=test_product.id,
                project_requirements="Build authentication system",
                user_id=None,
            )

        # Assert: Project created, missions generated, agents selected
        assert "project_id" in result
        assert "mission_plan" in result
        assert "selected_agents" in result
        assert "spawned_jobs" in result
        assert "workflow_result" in result
        assert "token_reduction" in result
        assert len(result["selected_agents"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Complex integration test - requires full database setup with eager loading of relationships"
    )
    async def test_uses_existing_project_when_provided(
        self, db_session: AsyncSession, test_tenant_key, test_product, test_project
    ):
        """Test process_product_vision uses existing project instead of creating new (duplicate bug fix)."""
        # Create mock product with vision properties already set
        mock_product = MagicMock()
        mock_product.id = test_product.id
        mock_product.name = "Test Product"
        mock_product.tenant_key = test_tenant_key
        mock_product.is_active = True
        mock_product.vision_is_chunked = True
        mock_product.primary_vision_storage_type = "inline"
        mock_product.primary_vision_text = "# Test Vision"
        mock_product.vision_documents = [MagicMock(chunked=True)]

        # Create mock existing project - MUST be a regular object, not coroutine
        mock_existing_project = MagicMock()
        mock_existing_project.id = test_project.id
        mock_existing_project.name = "Existing Project"

        # Create service with mocked dependencies
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.mission_planner = MagicMock()
        service.mission_planner.analyze_requirements = AsyncMock(return_value={})
        service.mission_planner.generate_mission = AsyncMock(return_value={})
        service.agent_selector = MagicMock()
        service.agent_selector.select_agents = AsyncMock(return_value=[])
        service.workflow_engine = MagicMock()
        workflow_result = MagicMock()
        workflow_result.completed = []
        workflow_result.failed = []
        workflow_result.status = "completed"
        service.workflow_engine.execute_workflow = AsyncMock(return_value=workflow_result)

        # Mock the session with proper async behavior
        mock_session = MagicMock()  # Use MagicMock, not AsyncMock, for the session itself

        # session.get needs to return the right object based on which model/id is requested
        async def mock_get(model, id):
            if model.__name__ == "Product":
                return mock_product
            if model.__name__ == "Project":
                return mock_existing_project
            return None

        mock_session.get = mock_get
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        service._get_session = mock_get_session

        # Act: Call with existing project_id
        result = await service.process_product_vision(
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            project_requirements="Build authentication system",
            project_id=test_project.id,  # Use existing project
        )

        # Assert: Should use existing project, not create new one
        assert result["project_id"] == test_project.id

    @pytest.mark.asyncio
    async def test_requires_active_product(self, db_session: AsyncSession, test_tenant_key):
        """Test process_product_vision raises ValueError for inactive product."""
        # Setup: Create inactive product
        inactive_product = Product(
            id=str(uuid4()),
            name="Inactive Product",
            description="Test product that is inactive",
            tenant_key=test_tenant_key,
            is_active=False,  # Inactive
            product_memory={},
        )
        db_session.add(inactive_product)
        await db_session.commit()

        # Create service with test session injection
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service._test_session = db_session

        # Act & Assert: Should raise ValidationError for inactive product
        # Handover 0731c: Service now raises giljo_mcp ValidationError instead of ValueError
        from src.giljo_mcp.exceptions import ValidationError as GiljoValidationError

        with pytest.raises(GiljoValidationError, match="not active"):
            await service.process_product_vision(
                tenant_key=test_tenant_key,
                product_id=inactive_product.id,
                project_requirements="Build something",
            )

    @pytest.mark.asyncio
    async def test_enforces_tenant_isolation(self, db_session: AsyncSession):
        """Test process_product_vision enforces multi-tenant isolation."""
        # Setup: Create products in different tenants
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"

        product_a = Product(
            id=str(uuid4()),
            name="Product A",
            description="Product in tenant A",
            tenant_key=tenant_a,
            is_active=True,
            product_memory={},
        )
        db_session.add(product_a)
        await db_session.commit()

        # Create service with test session injection
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service._test_session = db_session

        # Act & Assert: Tenant B should not access tenant A's product
        # Handover 0731c: Service now raises ResourceNotFoundError instead of ValueError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError, match="not found"):
            await service.process_product_vision(
                tenant_key=tenant_b,  # Different tenant
                product_id=product_a.id,
                project_requirements="Build something",
            )


# ============================================================================
# TestGenerateMissionPlan
# ============================================================================


class TestGenerateMissionPlan:
    """Tests for generate_mission_plan() method."""

    @pytest.mark.asyncio
    async def test_generates_missions_for_product(self, db_session: AsyncSession, test_product, mock_mission_planner):
        """Test generate_mission_plan creates missions from product vision."""
        # Create service with mocked planner
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.mission_planner = mock_mission_planner

        # Act: Generate mission plan
        missions = await service.generate_mission_plan(
            product=test_product, project_description="Build authentication system", user_id=None
        )

        # Assert: Missions returned
        assert "implementer" in missions
        assert "tester" in missions
        mock_mission_planner.generate_mission.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_user_id_for_field_priorities(
        self, db_session: AsyncSession, test_product, mock_mission_planner
    ):
        """Test user_id is propagated for field priority configuration."""
        # Create service with mocked planner
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.mission_planner = mock_mission_planner

        user_id = str(uuid4())

        # Act: Generate mission plan with user_id
        await service.generate_mission_plan(
            product=test_product, project_description="Build authentication system", user_id=user_id
        )

        # Assert: user_id passed to planner
        mock_mission_planner.generate_mission.assert_called_once()
        call_kwargs = mock_mission_planner.generate_mission.call_args.kwargs
        assert call_kwargs.get("user_id") == user_id


# ============================================================================
# TestSelectAgentsForMission
# ============================================================================


class TestSelectAgentsForMission:
    """Tests for select_agents_for_mission() method."""

    @pytest.mark.asyncio
    async def test_selects_agents_from_requirements(
        self, db_session: AsyncSession, test_tenant_key, mock_agent_selector
    ):
        """Test select_agents_for_mission returns agent configs."""
        # Create service with mocked selector
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.agent_selector = mock_agent_selector

        requirements = {"required_agents": ["implementer", "tester"]}

        # Act: Select agents
        agent_configs = await service.select_agents_for_mission(
            requirements=requirements, tenant_key=test_tenant_key, product_id=None
        )

        # Assert: Agent configs returned
        assert len(agent_configs) == 2
        assert agent_configs[0].role == "implementer"
        assert agent_configs[1].role == "tester"
        mock_agent_selector.select_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_enforces_tenant_isolation(self, db_session: AsyncSession, test_tenant_key, mock_agent_selector):
        """Test agent selection respects tenant boundaries."""
        # Create service with mocked selector
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.agent_selector = mock_agent_selector

        requirements = {"required_agents": ["implementer"]}

        # Act: Select agents
        await service.select_agents_for_mission(requirements=requirements, tenant_key=test_tenant_key, product_id=None)

        # Assert: Tenant key passed to selector
        mock_agent_selector.select_agents.assert_called_once()
        call_kwargs = mock_agent_selector.select_agents.call_args.kwargs
        assert call_kwargs["tenant_key"] == test_tenant_key


# ============================================================================
# TestCoordinateAgentWorkflow
# ============================================================================


class TestCoordinateAgentWorkflow:
    """Tests for coordinate_agent_workflow() method."""

    @pytest.mark.asyncio
    async def test_executes_waterfall_workflow(
        self, db_session: AsyncSession, test_tenant_key, test_project, mock_workflow_engine
    ):
        """Test coordinate_agent_workflow executes via WorkflowEngine."""
        # Create service with mocked engine
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())
        service.workflow_engine = mock_workflow_engine

        agent_configs = [
            MagicMock(role="implementer", mission=None),
            MagicMock(role="tester", mission=None),
        ]

        # Act: Coordinate workflow
        workflow_result = await service.coordinate_agent_workflow(
            agent_configs=agent_configs,
            workflow_type="waterfall",
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        # Assert: Workflow executed
        assert workflow_result.status == "completed"
        assert len(workflow_result.completed) == 1
        mock_workflow_engine.execute_workflow.assert_called_once()


# ============================================================================
# TestGetAgentTemplateInternal
# ============================================================================


class TestGetAgentTemplateInternal:
    """Tests for _get_agent_template_internal() method."""

    @pytest.mark.asyncio
    async def test_prefers_product_specific_template(self, db_session: AsyncSession, test_tenant_key, test_product):
        """Test template resolution prioritizes product-specific templates."""
        # Setup: Create templates at different levels
        # 1. System default
        system_template = AgentTemplate(
            id=str(uuid4()),
            name="System Implementer",
            category="role",
            role="implementer",
            tool="claude",
            tenant_key="system",  # System templates use "system" tenant_key
            is_default=True,
            system_instructions="System template",
        )
        # 2. Tenant-specific
        tenant_template = AgentTemplate(
            id=str(uuid4()),
            name="Tenant Implementer",
            category="role",
            role="implementer",
            tool="claude",
            tenant_key=test_tenant_key,
            is_default=False,
            system_instructions="Tenant template",
        )
        # 3. Product-specific
        product_template = AgentTemplate(
            id=str(uuid4()),
            name="Product Implementer",
            category="role",
            role="implementer",
            tool="claude",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            is_default=False,
            system_instructions="Product template",
        )
        db_session.add_all([system_template, tenant_template, product_template])
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())

        # Act: Get template with product_id
        template = await service._get_agent_template_internal(
            role="implementer", tenant_key=test_tenant_key, product_id=test_product.id, session=db_session
        )

        # Assert: Should return product-specific template
        assert template is not None
        assert template.system_instructions == "Product template"
        assert template.product_id == test_product.id

    @pytest.mark.asyncio
    async def test_falls_back_to_tenant_template(self, db_session: AsyncSession, test_tenant_key, test_product):
        """Test template resolution falls back to tenant templates."""
        # Setup: Create templates (no product-specific)
        # 1. System default
        system_template = AgentTemplate(
            id=str(uuid4()),
            name="System Implementer",
            category="role",
            role="implementer",
            tool="claude",
            tenant_key="system",  # System templates use "system" tenant_key
            is_default=True,
            system_instructions="System template",
        )
        # 2. Tenant-specific
        tenant_template = AgentTemplate(
            id=str(uuid4()),
            name="Tenant Implementer",
            category="role",
            role="implementer",
            tool="claude",
            tenant_key=test_tenant_key,
            is_default=False,
            system_instructions="Tenant template",
        )
        db_session.add_all([system_template, tenant_template])
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())

        # Act: Get template with product_id (but no product-specific template exists)
        template = await service._get_agent_template_internal(
            role="implementer", tenant_key=test_tenant_key, product_id=test_product.id, session=db_session
        )

        # Assert: Should fall back to tenant template
        assert template is not None
        assert template.system_instructions == "Tenant template"
        assert template.product_id is None
        assert template.tenant_key == test_tenant_key

    @pytest.mark.asyncio
    async def test_falls_back_to_system_default(self, db_session: AsyncSession, test_tenant_key, test_product):
        """Test template resolution falls back to system defaults."""
        # Use unique role to avoid conflicts with real system defaults
        unique_role = f"test_role_{uuid4().hex[:8]}"

        # Setup: Create only system default template
        system_template = AgentTemplate(
            id=str(uuid4()),
            name=f"System {unique_role.title()}",
            category="role",
            role=unique_role,
            tool="claude",
            tenant_key="system",  # System templates use "system" tenant_key
            is_default=True,
            system_instructions="System template",
        )
        db_session.add(system_template)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())

        # Act: Get template with product_id (no product/tenant templates exist)
        template = await service._get_agent_template_internal(
            role=unique_role, tenant_key=test_tenant_key, product_id=test_product.id, session=db_session
        )

        # Assert: Should fall back to system default
        assert template is not None
        assert template.system_instructions == "System template"
        assert template.is_default is True
        assert template.tenant_key == "system"


# ============================================================================
# TestMultiTenantIsolation
# ============================================================================


class TestMultiTenantIsolation:
    """Tests ensuring all methods enforce tenant isolation."""

    @pytest.mark.asyncio
    async def test_process_vision_tenant_isolated(self, db_session: AsyncSession):
        """Test process_product_vision blocks cross-tenant access."""
        # Setup: Create products in different tenants
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"

        product_a = Product(
            id=str(uuid4()),
            name="Product A",
            description="Product in tenant A",
            tenant_key=tenant_a,
            is_active=True,
            product_memory={},
        )
        db_session.add(product_a)
        await db_session.commit()

        # Create service
        service = OrchestrationService(db_manager=MagicMock(), tenant_manager=MagicMock())

        # Act & Assert: Tenant B should not access tenant A's product
        # Handover 0731c: Service now raises ResourceNotFoundError instead of ValueError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            await service.process_product_vision(
                tenant_key=tenant_b,  # Different tenant
                product_id=product_a.id,
                project_requirements="Build something",
            )
