# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test suite for Handover 0830: Orchestrator Staging-to-Implementation Harmonization.

Covers 6 changes:
1. Thin prompt stripped to <=15 lines
2. agent_identity populated for orchestrator
3. Orchestrator protocol fork (3-phase vs 5-phase)
4. current_team_state in MissionResponse
5. implementation_launched_at phase gate for orchestrator
6. get_orchestrator_instructions redirect branches on implementation_launched_at
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import MissionResponse
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Mock tenant manager."""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant = MagicMock(return_value="tenant-test")
    return tenant_manager


@pytest.fixture
def orchestration_service(mock_db_manager, mock_tenant_manager):
    """Create OrchestrationService with mocked dependencies."""
    db_manager, _ = mock_db_manager
    return OrchestrationService(db_manager=db_manager, tenant_manager=mock_tenant_manager)


@pytest.fixture
def sample_project():
    """Create a mock project for prompt testing."""
    project = MagicMock()
    project.name = "Test Project"
    project.id = str(uuid4())
    return project


# ---------------------------------------------------------------------------
# Change 1: Thin prompt stripped to <=15 lines
# ---------------------------------------------------------------------------


class TestThinPromptStrippedToFifteenLines:
    """Verify _build_multi_terminal_orchestrator_prompt is genuinely thin."""

    def _generate_prompt(self, project) -> str:
        """Helper to generate orchestrator prompt via ThinClientPromptGenerator."""
        mock_session = AsyncMock()
        gen = ThinClientPromptGenerator(db=mock_session, tenant_key="tenant-test")
        orchestrator_id = str(uuid4())
        return gen.generate_implementation_prompt(
            prompt_type="multi_terminal_orchestrator",
            orchestrator_id=orchestrator_id,
            project=project,
            agent_jobs=[],
        )

    def test_output_is_at_most_15_lines(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        line_count = len(prompt.strip().splitlines())
        assert line_count <= 15, f"Prompt has {line_count} lines, expected <=15"

    def test_contains_health_check(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "health_check" in prompt

    def test_contains_job_id_and_project_id(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert str(sample_project.id) in prompt, "Prompt must contain project_id"
        # job_id is the orchestrator_id passed in — it appears as Job ID in the prompt
        assert "Job ID:" in prompt

    def test_contains_get_agent_mission_call(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "get_agent_mission" in prompt

    def test_does_not_contain_team_roster(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "YOUR TEAM" not in prompt
        assert "Agent |" not in prompt

    def test_does_not_contain_behavioral_protocol(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "Phase 1: STARTUP" not in prompt
        assert "Phase 2: EXECUTION" not in prompt
        assert "lifecycle" not in prompt.lower()

    def test_does_not_contain_tool_catalog(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "report_progress" not in prompt
        assert "complete_job" not in prompt
        assert "send_message" not in prompt

    def test_does_not_contain_closeout_instructions(self, sample_project):
        prompt = self._generate_prompt(sample_project)
        assert "write_360_memory" not in prompt
        assert "CLOSEOUT" not in prompt


# ---------------------------------------------------------------------------
# Change 2: agent_identity populated for orchestrator
# ---------------------------------------------------------------------------


class TestOrchestratorIdentityPopulated:
    """Verify get_agent_mission sets hardcoded identity for orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_identity_is_non_null(self, orchestration_service, mock_db_manager):
        _db_manager, session = mock_db_manager
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Coordinate implementation",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="waiting",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            implementation_launched_at=datetime.now(timezone.utc),
            series_number=random.randint(1, 999999),
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)
        all_exec_result = MagicMock()
        all_exec_result.all = MagicMock(return_value=[(execution, job)])

        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result, all_exec_result])

        response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key="tenant-test")

        assert response.agent_identity is not None, "Orchestrator identity must be set"

    @pytest.mark.asyncio
    async def test_orchestrator_identity_contains_orchestrator_keyword(self, orchestration_service, mock_db_manager):
        _db_manager, session = mock_db_manager
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Coordinate implementation",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="waiting",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            implementation_launched_at=datetime.now(timezone.utc),
            series_number=random.randint(1, 999999),
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)
        all_exec_result = MagicMock()
        all_exec_result.all = MagicMock(return_value=[(execution, job)])

        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result, all_exec_result])

        response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key="tenant-test")

        assert "ORCHESTRATOR" in response.agent_identity

    @pytest.mark.asyncio
    async def test_orchestrator_identity_contains_behavioral_phrases(self, orchestration_service, mock_db_manager):
        _db_manager, session = mock_db_manager
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Coordinate implementation",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="waiting",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            implementation_launched_at=datetime.now(timezone.utc),
            series_number=random.randint(1, 999999),
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)
        all_exec_result = MagicMock()
        all_exec_result.all = MagicMock(return_value=[(execution, job)])

        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result, all_exec_result])

        response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key="tenant-test")

        identity = response.agent_identity
        assert "coordinate" in identity.lower(), "Identity must mention coordination"
        assert "do not implement" in identity.lower(), "Identity must prohibit implementation"


# ---------------------------------------------------------------------------
# Change 3: Orchestrator protocol fork
# ---------------------------------------------------------------------------


class TestOrchestratorProtocolFork:
    """Verify _generate_agent_protocol returns 3-phase for orchestrator, 5-phase for worker."""

    def test_orchestrator_returns_three_phase_protocol(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="orchestrator-1",
            agent_id=str(uuid4()),
            job_type="orchestrator",
        )
        assert "PHASE 1" in protocol
        assert "PHASE 2" in protocol
        assert "PHASE 3" in protocol

    def test_orchestrator_protocol_does_not_contain_worker_phases(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="orchestrator-1",
            agent_id=str(uuid4()),
            job_type="orchestrator",
        )
        assert "Phase 4: COMPLETION" not in protocol
        assert "Phase 5: ERROR HANDLING" not in protocol

    def test_orchestrator_protocol_contains_todo_append(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="orchestrator-1",
            agent_id=str(uuid4()),
            job_type="orchestrator",
        )
        assert "todo_append" in protocol

    def test_orchestrator_protocol_contains_never_todo_items_warning(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="orchestrator-1",
            agent_id=str(uuid4()),
            job_type="orchestrator",
        )
        assert "NEVER" in protocol
        assert "todo_items" in protocol

    def test_worker_returns_five_phase_protocol(self):
        """Regression check: worker agents still get the 5-phase lifecycle."""
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="implementer-1",
            agent_id=str(uuid4()),
            job_type="agent",
        )
        assert "Phase 1: STARTUP" in protocol
        assert "Phase 2: EXECUTION" in protocol
        assert "Phase 3: PROGRESS REPORTING" in protocol
        assert "Phase 4: COMPLETION" in protocol
        assert "Phase 5: ERROR HANDLING" in protocol

    def test_orchestrator_protocol_has_startup_reactive_closeout_labels(self):
        protocol = _generate_agent_protocol(
            job_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_name="orchestrator-1",
            agent_id=str(uuid4()),
            job_type="orchestrator",
        )
        assert "STARTUP" in protocol
        assert "ACTIVE COORDINATION" in protocol
        assert "CLOSEOUT" in protocol


# ---------------------------------------------------------------------------
# Change 4: current_team_state in MissionResponse
# ---------------------------------------------------------------------------


class TestMissionResponseCurrentTeamState:
    """Verify MissionResponse schema accepts and serializes current_team_state."""

    def test_accepts_current_team_state_field(self):
        team_state = [
            {"agent_id": "abc", "status": "active", "role": "implementer"},
            {"agent_id": "def", "status": "waiting", "role": "tester"},
        ]
        response = MissionResponse(job_id="j1", current_team_state=team_state)
        assert response.current_team_state == team_state

    def test_current_team_state_defaults_to_none(self):
        response = MissionResponse(job_id="j1")
        assert response.current_team_state is None

    def test_current_team_state_serializes_with_model_dump(self):
        team_state = [{"agent_id": "abc", "status": "active"}]
        response = MissionResponse(job_id="j1", current_team_state=team_state)
        dumped = response.model_dump()
        assert "current_team_state" in dumped
        assert dumped["current_team_state"] == team_state

    def test_current_team_state_none_serializes_correctly(self):
        response = MissionResponse(job_id="j1")
        dumped = response.model_dump()
        assert dumped["current_team_state"] is None


# ---------------------------------------------------------------------------
# Change 5: implementation_launched_at phase gate for orchestrator
# ---------------------------------------------------------------------------


class TestOrchestratorPhaseGate:
    """Verify orchestrator-specific blocked message when implementation not launched."""

    @pytest.mark.asyncio
    async def test_orchestrator_blocked_when_implementation_not_launched(self, orchestration_service, mock_db_manager):
        _db_manager, session = mock_db_manager
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Coordinate",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="waiting",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            implementation_launched_at=None,
            series_number=random.randint(1, 999999),
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result])

        response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key="tenant-test")

        assert response.blocked is True
        assert response.mission is None
        assert response.full_protocol is None
        assert "BLOCKED" in (response.error or "")

    @pytest.mark.asyncio
    async def test_orchestrator_blocked_message_mentions_dashboard_and_implement(
        self, orchestration_service, mock_db_manager
    ):
        _db_manager, session = mock_db_manager
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Coordinate",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="waiting",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            implementation_launched_at=None,
            series_number=random.randint(1, 999999),
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none = MagicMock(return_value=job)
        exec_result = MagicMock()
        exec_result.scalar_one_or_none = MagicMock(return_value=execution)
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        session.execute = AsyncMock(side_effect=[job_result, exec_result, project_result])

        response = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key="tenant-test")

        assert "dashboard" in response.user_instruction.lower()
        assert "Implement" in response.user_instruction


# ---------------------------------------------------------------------------
# Change 6: get_orchestrator_instructions redirect branches
# ---------------------------------------------------------------------------


class TestGetOrchestratorInstructionsRedirectBranches:
    """Verify redirect logic based on implementation_launched_at."""

    def _make_fixtures(self, *, implementation_launched_at):
        """Build job, execution, and project with given launch timestamp."""
        job_id = str(uuid4())
        project_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-test",
            project_id=project_id,
            mission="Orchestrate",
            job_type="orchestrator",
            status="active",
            created_at=datetime.now(timezone.utc),
        )

        execution = AgentExecution(
            job_id=job_id,
            agent_id=str(uuid4()),
            tenant_key="tenant-test",
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            status="active",
        )

        project = Project(
            id=project_id,
            tenant_key="tenant-test",
            name="Redirect Test Project",
            description="Test desc",
            mission="Test mission",
            status="active",
            staging_status="staging_complete",
            implementation_launched_at=implementation_launched_at,
            series_number=random.randint(1, 999999),
        )

        return job_id, job, execution, project

    def _mock_session_for_get_orchestrator_instructions(self, session, execution, project):
        """Wire session.execute for the get_orchestrator_instructions query pattern."""
        # First query: AgentExecution with joined AgentJob
        exec_scalars = MagicMock()
        exec_scalars.first = MagicMock(return_value=execution)
        exec_result = MagicMock()
        exec_result.scalars = MagicMock(return_value=exec_scalars)

        # Second query: Project lookup
        project_result = MagicMock()
        project_result.scalar_one_or_none = MagicMock(return_value=project)

        session.execute = AsyncMock(side_effect=[exec_result, project_result])

    @pytest.mark.asyncio
    async def test_redirect_to_get_agent_mission_when_launched(self, orchestration_service, mock_db_manager):
        """When implementation_launched_at IS NOT NULL, returns redirect=get_agent_mission."""
        _, session = mock_db_manager
        job_id, job, execution, project = self._make_fixtures(
            implementation_launched_at=datetime.now(timezone.utc),
        )
        # Wire execution.job to return the AgentJob
        execution.job = job

        self._mock_session_for_get_orchestrator_instructions(session, execution, project)

        result = await orchestration_service.get_orchestrator_instructions(job_id=job_id, tenant_key="tenant-test")

        assert result["staging_complete"] is True
        assert result["redirect"] == "get_agent_mission"
        assert "already launched" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_no_redirect_when_not_launched(self, orchestration_service, mock_db_manager):
        """When implementation_launched_at IS NULL, returns redirect=None."""
        _, session = mock_db_manager
        job_id, job, execution, project = self._make_fixtures(
            implementation_launched_at=None,
        )
        execution.job = job

        self._mock_session_for_get_orchestrator_instructions(session, execution, project)

        result = await orchestration_service.get_orchestrator_instructions(job_id=job_id, tenant_key="tenant-test")

        assert result["staging_complete"] is True
        assert result["redirect"] is None
        assert "click Implement" in result["message"]

    @pytest.mark.asyncio
    async def test_launched_response_contains_identity_fields(self, orchestration_service, mock_db_manager):
        """Redirect response includes job_id, project_id, project_name."""
        _, session = mock_db_manager
        job_id, job, execution, project = self._make_fixtures(
            implementation_launched_at=datetime.now(timezone.utc),
        )
        execution.job = job

        self._mock_session_for_get_orchestrator_instructions(session, execution, project)

        result = await orchestration_service.get_orchestrator_instructions(job_id=job_id, tenant_key="tenant-test")

        identity = result["identity"]
        assert identity["job_id"] == job_id
        assert identity["project_id"] == str(project.id)
        assert identity["project_name"] == project.name

    @pytest.mark.asyncio
    async def test_not_launched_response_contains_identity_fields(self, orchestration_service, mock_db_manager):
        """Not-launched response also includes identity fields."""
        _, session = mock_db_manager
        job_id, job, execution, project = self._make_fixtures(
            implementation_launched_at=None,
        )
        execution.job = job

        self._mock_session_for_get_orchestrator_instructions(session, execution, project)

        result = await orchestration_service.get_orchestrator_instructions(job_id=job_id, tenant_key="tenant-test")

        identity = result["identity"]
        assert identity["job_id"] == job_id
        assert identity["project_id"] == str(project.id)
        assert identity["project_name"] == project.name
