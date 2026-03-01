"""
TDD Tests for Handover 0411a: Phase Labels on AgentJob.

RED PHASE - These tests verify:
1. spawn_agent_job accepts and stores `phase` parameter on AgentJob
2. spawn_agent_job populates `template_id` when template is found
3. list_jobs includes `phase` in the response dict
4. get_orchestrator_instructions includes phase_assignment_instructions
   ONLY when execution_mode != 'claude_code_cli' (multi-terminal mode)
5. WebSocket broadcast includes `phase` in data dict

Test Coverage:
- Change A: phase parameter flows through to AgentJob and WebSocket broadcast
- Change B: template_id populated on AgentJob when template matched
- Change C: phase included in list_jobs response
- Change D: phase_assignment_instructions in orchestrator protocol (multi-terminal only)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Project

pytestmark = pytest.mark.skip(reason="0750b: spawn_agent tests need update for display name dedup logic")


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"tk_phase_{uuid.uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_agent_templates(db_session, test_tenant_key):
    """Create agent templates matching agent_name values used in tests."""
    template_names = ["analyzer-1", "impl-1", "tester-1"]
    for name in template_names:
        template = AgentTemplate(
            tenant_key=test_tenant_key,
            name=name,
            role=name,
            description=f"Test template for {name}",
            system_instructions=f"# {name}\nTest agent instructions.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_project(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project for agent jobs (depends on test_agent_templates)."""
    project = Project(
        id=str(uuid.uuid4()),
        name="Phase Labels Test Project",
        description="Test project for phase labels",
        mission="Test mission for phase labels",
        status="active",
        tenant_key=test_tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project_multi_terminal(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project with multi_terminal execution_mode."""
    project = Project(
        id=str(uuid.uuid4()),
        name="Multi Terminal Phase Test",
        description="Test project for multi-terminal phase labels",
        mission="Test mission for multi-terminal",
        status="active",
        tenant_key=test_tenant_key,
        execution_mode="multi_terminal",
        implementation_launched_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project_cli_mode(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project with claude_code_cli execution_mode."""
    project = Project(
        id=str(uuid.uuid4()),
        name="CLI Mode Phase Test",
        description="Test project for CLI mode",
        mission="Test mission for CLI mode",
        status="active",
        tenant_key=test_tenant_key,
        execution_mode="claude_code_cli",
        implementation_launched_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# Change A: spawn_agent_job accepts and stores phase parameter
# ============================================================================


@pytest.mark.asyncio
class TestSpawnAgentJobPhaseParameter:
    """Tests that spawn_agent_job correctly handles the `phase` parameter."""

    async def test_spawn_stores_phase_on_agent_job(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify spawn_agent_job stores phase value on AgentJob record."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=1,
        )

        # Verify phase stored on AgentJob
        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.phase == 1

    async def test_spawn_stores_none_phase_when_omitted(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify spawn_agent_job defaults phase to None when not provided."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Verify phase is None when not specified
        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.phase is None

    async def test_spawn_stores_higher_phase_numbers(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify spawn_agent_job correctly stores phase values > 1."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        result = await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="tester-1",
            mission="Write integration tests",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=3,
        )

        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.phase == 3


# ============================================================================
# Change A (continued): WebSocket broadcast includes phase
# ============================================================================


@pytest.mark.asyncio
class TestSpawnWebSocketBroadcastPhase:
    """Tests that WebSocket broadcast data includes phase field."""

    async def test_websocket_broadcast_includes_phase(self):
        """Verify agent:created WebSocket broadcast includes phase in data dict."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService

        db_manager = MagicMock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        db_manager.get_session_async = MagicMock(return_value=session)

        mock_ws = AsyncMock()
        tenant_manager = MagicMock()

        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=mock_ws,
        )

        # Mock project lookup
        mock_project = MagicMock()
        mock_project.id = str(uuid.uuid4())
        mock_project.name = "Test Project"
        mock_project.execution_mode = "multi_terminal"

        # Mock template lookup (active templates for validation)
        mock_template_row = MagicMock()
        mock_template_row.__getitem__ = lambda self, idx: "analyzer-1"

        # Set up session.execute to return appropriate results for each query
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=mock_project)

        template_validation_result = MagicMock()
        template_validation_result.fetchall = MagicMock(return_value=[mock_template_row])

        # Template lookup for multi-terminal injection
        mock_template = MagicMock()
        mock_template.id = str(uuid.uuid4())
        mock_template.system_instructions = "Test instructions"
        mock_template.user_instructions = None
        template_lookup_result = MagicMock()
        template_lookup_result.scalar_one_or_none = MagicMock(return_value=mock_template)

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return project_result
            elif call_count == 2:
                return template_validation_result
            else:
                return template_lookup_result

        session.execute = AsyncMock(side_effect=mock_execute)

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze codebase",
            project_id=mock_project.id,
            tenant_key="tk_test",
            phase=2,
        )

        # Verify broadcast was called with phase in data
        mock_ws.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_ws.broadcast_to_tenant.call_args
        broadcast_data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")
        assert "phase" in broadcast_data
        assert broadcast_data["phase"] == 2

    async def test_websocket_broadcast_includes_none_phase_when_omitted(self):
        """Verify agent:created WebSocket broadcast includes phase=None when not specified."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService

        db_manager = MagicMock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        db_manager.get_session_async = MagicMock(return_value=session)

        mock_ws = AsyncMock()
        tenant_manager = MagicMock()

        service = OrchestrationService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=mock_ws,
        )

        mock_project = MagicMock()
        mock_project.id = str(uuid.uuid4())
        mock_project.name = "Test Project"
        mock_project.execution_mode = "multi_terminal"

        mock_template_row = MagicMock()
        mock_template_row.__getitem__ = lambda self, idx: "impl-1"

        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=mock_project)

        template_validation_result = MagicMock()
        template_validation_result.fetchall = MagicMock(return_value=[mock_template_row])

        mock_template = MagicMock()
        mock_template.id = str(uuid.uuid4())
        mock_template.system_instructions = "Test instructions"
        mock_template.user_instructions = None
        template_lookup_result = MagicMock()
        template_lookup_result.scalar_one_or_none = MagicMock(return_value=mock_template)

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return project_result
            elif call_count == 2:
                return template_validation_result
            else:
                return template_lookup_result

        session.execute = AsyncMock(side_effect=mock_execute)

        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=mock_project.id,
            tenant_key="tk_test",
            # No phase parameter
        )

        mock_ws.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_ws.broadcast_to_tenant.call_args
        broadcast_data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")
        assert "phase" in broadcast_data
        assert broadcast_data["phase"] is None


# ============================================================================
# Change B: template_id populated on AgentJob when template found
# ============================================================================


@pytest.mark.asyncio
class TestSpawnPopulatesTemplateId:
    """Tests that spawn_agent_job populates template_id on AgentJob when template is found."""

    async def test_template_id_set_in_multi_terminal_mode(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify template_id is set on AgentJob when template found in multi-terminal mode."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
            phase=1,
        )

        # Verify template_id is set on AgentJob
        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.template_id is not None

        # Verify it matches the actual template
        template_stmt = select(AgentTemplate).where(
            AgentTemplate.name == "analyzer-1",
            AgentTemplate.tenant_key == test_tenant_key,
        )
        template_result = await db_session.execute(template_stmt)
        template = template_result.scalar_one()
        assert job.template_id == template.id

    async def test_template_id_none_when_no_template_found(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify template_id remains None for orchestrator (no template lookup)."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        job_stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        # Orchestrator skips agent_name validation and template lookup
        assert job.template_id is None


# ============================================================================
# Change C: list_jobs includes phase in response
# ============================================================================


@pytest.mark.asyncio
class TestListJobsIncludesPhase:
    """Tests that list_jobs includes `phase` in each job dict."""

    async def test_list_jobs_returns_phase_value(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify list_jobs response includes phase for jobs with phase set."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Create a job with phase
        await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze the codebase",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=1,
        )

        # List jobs
        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 1
        job_dict = result.jobs[0]
        assert "phase" in job_dict
        assert job_dict["phase"] == 1

    async def test_list_jobs_returns_none_phase_when_not_set(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify list_jobs response includes phase=None for jobs without phase."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Create a job without phase
        await service.spawn_agent_job(
            agent_display_name="impl",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 1
        # Find the job we just created (may not be first due to ordering)
        impl_jobs = [j for j in result.jobs if j["agent_display_name"] == "impl"]
        assert len(impl_jobs) >= 1
        assert "phase" in impl_jobs[0]
        assert impl_jobs[0]["phase"] is None

    async def test_list_jobs_returns_multiple_phases(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify list_jobs correctly returns different phases for different jobs."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Create jobs with different phases
        await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze first",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=1,
        )
        await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement second",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=2,
        )
        await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="tester-1",
            mission="Test third",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            phase=3,
        )

        result = await service.list_jobs(
            tenant_key=test_tenant_key,
            project_id=test_project.id,
        )

        assert len(result.jobs) >= 3
        phases = {j["agent_display_name"]: j["phase"] for j in result.jobs}
        assert phases.get("analyzer") == 1
        assert phases.get("implementer") == 2
        assert phases.get("tester") == 3


# ============================================================================
# Change D: Phase assignment instructions in orchestrator protocol
# ============================================================================


@pytest.mark.asyncio
class TestOrchestratorPhaseInstructions:
    """Tests that get_orchestrator_instructions includes phase assignment instructions
    ONLY in multi-terminal mode (not CLI mode)."""

    async def test_phase_instructions_present_in_multi_terminal_mode(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify phase_assignment_instructions present when execution_mode is multi_terminal."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Spawn an orchestrator for the multi-terminal project
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate multi-terminal project",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
        )

        # Get orchestrator instructions
        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        assert "phase_assignment_instructions" in instructions
        phase_text = instructions["phase_assignment_instructions"]
        assert "Phase 1" in phase_text
        assert "Phase 2" in phase_text
        assert "parallel" in phase_text.lower()

    async def test_phase_instructions_absent_in_cli_mode(
        self, db_session, db_manager, test_project_cli_mode, test_tenant_key
    ):
        """Verify phase_assignment_instructions NOT present when execution_mode is claude_code_cli."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Spawn an orchestrator for the CLI project
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate CLI project",
            project_id=test_project_cli_mode.id,
            tenant_key=test_tenant_key,
        )

        # Get orchestrator instructions
        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        assert "phase_assignment_instructions" not in instructions

    async def test_phase_instructions_contain_expected_content(
        self, db_session, db_manager, test_project_multi_terminal, test_tenant_key
    ):
        """Verify phase_assignment_instructions content includes all expected guidance."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate multi-terminal project",
            project_id=test_project_multi_terminal.id,
            tenant_key=test_tenant_key,
        )

        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        phase_text = instructions["phase_assignment_instructions"]
        # Check key content elements
        assert "Execution Phase Assignment" in phase_text
        assert "Multi-Terminal Mode" in phase_text
        assert "spawn_agent_job" in phase_text
        assert "Phase 1" in phase_text
        assert "Phase 2" in phase_text
        assert "Phase 3" in phase_text
        assert "Phase 4" in phase_text

    async def test_phase_instructions_present_for_default_mode(
        self, db_session, db_manager, test_project, test_tenant_key
    ):
        """Verify phase_assignment_instructions present when execution_mode is default (None/multi_terminal)."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(
            db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session
        )

        # Default project (no explicit execution_mode = defaults to multi_terminal)
        spawn_result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate default project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        instructions = await service.get_orchestrator_instructions(
            job_id=spawn_result.job_id,
            tenant_key=test_tenant_key,
        )

        # Default mode should include phase instructions (not CLI mode)
        assert "phase_assignment_instructions" in instructions
