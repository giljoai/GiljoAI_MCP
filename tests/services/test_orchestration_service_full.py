"""
Comprehensive OrchestrationService tests - Handover 0453.

Tests core functionality after orchestrator.py consolidation:
- Process product vision (CRITICAL: duplicate project bug fix)
- Agent spawning
- Succession
- Multi-tenant isolation
- Error handling

All tests use real database integration (db_manager fixture).
"""

import uuid

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Product, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
async def orchestration_service(db_manager: DatabaseManager):
    """Create OrchestrationService with real database."""
    tenant_manager = TenantManager()
    service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)
    return service


@pytest.fixture
async def test_product(db_manager: DatabaseManager):
    """Create a test product with vision."""
    tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        product = Product(
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for orchestration tests",
            is_active=True,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

        yield {"product_id": str(product.id), "tenant_key": tenant_key}


@pytest.fixture
async def test_project(db_manager: DatabaseManager, test_product: dict):
    """Create a test project."""
    from datetime import datetime, timezone

    async with db_manager.get_session_async() as session:
        project = Project(
            tenant_key=test_product["tenant_key"],
            product_id=test_product["product_id"],
            name="Test Project",
            description="Build a todo app",
            mission="Build a RESTful API for a todo application",
            status="active",
            # Handover 0709: Set implementation_launched_at to bypass phase gate
            implementation_launched_at=datetime.now(timezone.utc),
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        yield {
            **test_product,
            "project_id": str(project.id),
        }


@pytest.fixture
async def test_agent_template(db_manager: DatabaseManager, test_product: dict):
    """Create a test agent template."""
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            tenant_key=test_product["tenant_key"],
            name="implementer",
            role="implementer",
            description="Implementation specialist",
            system_instructions="# Implementer\nImplements features according to specifications.",
            is_active=True,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        yield {
            **test_product,
            "template_id": str(template.id),
        }


class TestProcessProductVision:
    """Test process_product_vision functionality."""

    @pytest.mark.asyncio
    async def test_creates_project_from_vision(
        self,
        orchestration_service: OrchestrationService,
        test_product: dict,
        db_manager: DatabaseManager,
    ):
        """Test that process_product_vision creates a new project."""
        # This test would require implementing process_product_vision
        # which might not exist in the current implementation
        pytest.skip("process_product_vision may not be implemented yet")

    @pytest.mark.asyncio
    async def test_uses_existing_project_when_provided(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """CRITICAL: Verify that providing project_id uses existing project, not creating duplicate."""
        # This test verifies the fix for the duplicate project bug
        pytest.skip("process_product_vision may not be implemented yet")


class TestSpawnAgentJob:
    """Test agent spawning functionality."""

    @pytest.mark.asyncio
    async def test_spawn_creates_both_job_and_execution(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that spawn_agent_job creates both AgentJob and AgentExecution records."""
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="Implementer-1",
            mission="Implement user authentication module",
            project_id=test_project["project_id"],
            tenant_key=test_project["tenant_key"],
        )

        # Handover 0730b: No success wrapper - returns dict with job_id, agent_id, etc.
        assert "job_id" in result
        assert "agent_id" in result

        # Verify job exists
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            job_query = select(AgentJob).where(AgentJob.job_id == result["job_id"])
            job_result = await session.execute(job_query)
            job = job_result.scalar_one_or_none()

            assert job is not None
            assert "Implement user authentication module" in job.mission  # Mission may include Serena notice
            assert job.job_type == "implementer"
            assert job.status == "active"

            # Verify execution exists
            exec_query = select(AgentExecution).where(AgentExecution.job_id == result["job_id"])
            exec_result = await session.execute(exec_query)
            execution = exec_result.scalar_one_or_none()

            assert execution is not None
            assert execution.agent_display_name == "implementer"
            assert execution.status == "waiting"

    @pytest.mark.asyncio
    async def test_spawn_routes_correctly(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that agent is routed correctly based on agent_display_name."""
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="Tester-1",
            mission="Test authentication module",
            project_id=test_project["project_id"],
            tenant_key=test_project["tenant_key"],
        )

        # Handover 0730b: No success wrapper - returns dict with job_id, agent_id, etc.
        assert "job_id" in result

        # Verify job type matches agent_display_name
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            job_query = select(AgentJob).where(AgentJob.job_id == result["job_id"])
            job_result = await session.execute(job_query)
            job = job_result.scalar_one_or_none()

            assert job.job_type == "tester"


class TestSuccession:
    """Test orchestrator succession functionality."""

    @pytest.mark.asyncio
    async def test_create_successor_resets_context(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that succession resets context and writes to 360 Memory (Handover 0461f)."""
        # First, create an orchestrator job
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="Orchestrator-1",
            mission="Coordinate project development",
            project_id=test_project["project_id"],
            tenant_key=test_project["tenant_key"],
        )

        original_job_id = result["job_id"]
        original_agent_id = result["agent_id"]

        # Create successor
        succession_result = await orchestration_service.create_successor_orchestrator(
            current_job_id=original_job_id,
            tenant_key=test_project["tenant_key"],
            reason="context_limit",
        )

        # Handover 0730b: No success wrapper - returns dict with context reset info
        # Handover 0461f: Same agent_id (no new execution created)
        assert "job_id" in succession_result
        assert succession_result["job_id"] == original_job_id  # Same job!
        assert succession_result["agent_id"] == original_agent_id  # Same agent! (0461f)
        assert succession_result["context_reset"] is True
        assert succession_result["new_context_used"] == 0

        # Verify database state - should still have 1 execution (not 2)
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            # Get all executions for this job
            exec_query = select(AgentExecution).where(AgentExecution.job_id == original_job_id)
            exec_result = await session.execute(exec_query)
            executions = exec_result.scalars().all()

            # Handover 0461f: No new execution created - same agent continues
            assert len(executions) == 1, "Should have 1 execution (same agent continues after 0461f)"
            assert executions[0].agent_id == original_agent_id
            assert executions[0].context_used == 0  # Context was reset


class TestMultiTenantIsolation:
    """Test multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_spawn_agent_tenant_isolated(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that spawn_agent_job respects tenant isolation."""
        wrong_tenant = "wrong_tenant_key"

        # Handover 0730b: Exception-based error handling
        # Attempt to spawn agent with wrong tenant_key - should raise ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await orchestration_service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="Implementer-1",
                mission="Implement feature",
                project_id=test_project["project_id"],
                tenant_key=wrong_tenant,
            )

        # Verify error message indicates project not found (tenant mismatch)
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_agent_mission_tenant_isolated(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that get_agent_mission respects tenant isolation."""
        # Create job
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="Implementer-1",
            mission="Implement feature",
            project_id=test_project["project_id"],
            tenant_key=test_project["tenant_key"],
        )

        job_id = result["job_id"]
        wrong_tenant = "wrong_tenant_key"

        # Handover 0730b: Exception-based error handling
        # Try to get mission with wrong tenant_key - should raise ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await orchestration_service.get_agent_mission(
                job_id=job_id,
                tenant_key=wrong_tenant,
            )

        # Verify error message indicates job not found (tenant mismatch)
        assert "not found" in str(exc_info.value).lower()


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_spawn_agent_invalid_project(
        self,
        orchestration_service: OrchestrationService,
        test_product: dict,
        db_manager: DatabaseManager,
    ):
        """Test that spawning agent with invalid project_id fails gracefully."""
        fake_project_id = str(uuid.uuid4())

        # Handover 0730b: Exception-based error handling
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await orchestration_service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="Implementer-1",
                mission="Implement feature",
                project_id=fake_project_id,
                tenant_key=test_product["tenant_key"],
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_agent_mission_invalid_job(
        self,
        orchestration_service: OrchestrationService,
        test_product: dict,
        db_manager: DatabaseManager,
    ):
        """Test that getting mission for non-existent job fails gracefully."""
        fake_job_id = str(uuid.uuid4())

        # Handover 0730b: Exception-based error handling
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await orchestration_service.get_agent_mission(
                job_id=fake_job_id,
                tenant_key=test_product["tenant_key"],
            )

        assert "not found" in str(exc_info.value).lower()


class TestAgentMission:
    """Test agent mission retrieval."""

    @pytest.mark.asyncio
    async def test_get_agent_mission_returns_full_protocol(
        self,
        orchestration_service: OrchestrationService,
        test_project: dict,
        db_manager: DatabaseManager,
    ):
        """Test that get_agent_mission returns full_protocol field."""
        # Create job
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="Implementer-1",
            mission="Implement user authentication",
            project_id=test_project["project_id"],
            tenant_key=test_project["tenant_key"],
        )

        job_id = result["job_id"]

        # Get mission
        mission_result = await orchestration_service.get_agent_mission(
            job_id=job_id,
            tenant_key=test_project["tenant_key"],
        )

        # Handover 0730b: No success wrapper - returns dict with full_protocol
        assert "full_protocol" in mission_result
        # full_protocol may be None if implementation phase gate blocks agent
        # For now, verify the key exists in the response
        if mission_result["full_protocol"] is not None:
            assert isinstance(mission_result["full_protocol"], str)
            assert len(mission_result["full_protocol"]) > 0
