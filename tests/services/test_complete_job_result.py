"""
Agent Completion Result Storage Tests - Handover 0497b

Validates that OrchestrationService.complete_job() correctly:
1. Stores the result dict in AgentExecution.result
2. Auto-creates a completion message to the orchestrator
3. Does NOT create a message when the completing agent IS the orchestrator
4. The new get_agent_result() method returns stored results
5. get_agent_result() returns None for incomplete jobs

These tests are written TDD-style: they define expected behavior for
features added in Handover 0497b (result persistence + auto-message).
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob, AgentTemplate, Message, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_key() -> str:
    """Generate a valid tenant key for test isolation."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def agent_templates(db_session, tenant_key):
    """Create agent templates needed by spawn_agent_job validation."""
    template_names = ["specialist-1", "orchestrator"]
    for name in template_names:
        template = AgentTemplate(
            tenant_key=tenant_key,
            name=name,
            role=name,
            description=f"Test template for {name}",
            system_instructions=f"# {name}\nTest agent.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def project(db_session, tenant_key, agent_templates) -> Project:
    """Create a test project with required fields."""
    from datetime import datetime, timezone

    proj = Project(
        id=str(uuid.uuid4()),
        name="Result Storage Test Project",
        description="Integration test project for 0497b",
        mission="Test completion result storage and auto-messaging",
        status="active",
        tenant_key=tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest_asyncio.fixture
async def service(db_session, db_manager) -> OrchestrationService:
    """Create OrchestrationService with shared test session."""
    tm = TenantManager()
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tm,
        test_session=db_session,
    )


# ============================================================================
# Test 1: complete_job stores result in AgentExecution.result
# ============================================================================


@pytest.mark.asyncio
class TestCompleteJobStoresResult:
    """Verify that calling complete_job persists the result dict on AgentExecution."""

    async def test_result_dict_stored_on_execution(
        self, db_session, service, project, tenant_key
    ):
        """complete_job should store the result dict in AgentExecution.result column."""
        # Arrange: spawn a specialist agent
        spawn = await service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do specialized work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        result_payload = {
            "summary": "Implemented the feature successfully",
            "artifacts": ["src/feature.py", "tests/test_feature.py"],
            "commits": ["abc123"],
        }

        # Act: complete the job with a result
        complete_result = await service.complete_job(
            job_id=spawn.job_id,
            result=result_payload,
            tenant_key=tenant_key,
        )

        # Assert: completion succeeded
        assert complete_result.status == "success"
        assert complete_result.result_stored is True

        # Assert: result persisted in database
        stmt = select(AgentExecution).where(AgentExecution.agent_id == spawn.agent_id)
        res = await db_session.execute(stmt)
        execution = res.scalar_one()

        assert execution.status == "complete"
        assert execution.result is not None
        assert execution.result == result_payload
        assert execution.result["summary"] == "Implemented the feature successfully"
        assert "src/feature.py" in execution.result["artifacts"]


# ============================================================================
# Test 2: complete_job auto-creates message to orchestrator
# ============================================================================


@pytest.mark.asyncio
class TestCompleteJobAutoMessage:
    """Verify that completing a specialist agent auto-sends a completion report to the orchestrator."""

    async def test_completion_report_message_created(
        self, db_session, service, project, tenant_key
    ):
        """When a specialist completes, a completion_report message should be sent to the orchestrator."""
        # Arrange: spawn orchestrator first, then specialist
        orch_spawn = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate the project",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        spec_spawn = await service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do specialized work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        result_payload = {
            "summary": "Refactored the auth module",
            "artifacts": ["src/auth.py"],
        }

        # Act: complete the specialist job
        await service.complete_job(
            job_id=spec_spawn.job_id,
            result=result_payload,
            tenant_key=tenant_key,
        )

        # Assert: a completion_report message was created
        msg_stmt = select(Message).where(
            Message.tenant_key == tenant_key,
            Message.project_id == project.id,
            Message.message_type == "completion_report",
        )
        msg_res = await db_session.execute(msg_stmt)
        messages = msg_res.scalars().all()

        assert len(messages) == 1, f"Expected 1 completion_report message, got {len(messages)}"

        msg = messages[0]
        assert orch_spawn.agent_id in msg.to_agents
        assert "COMPLETION REPORT" in msg.content
        assert "specialist" in msg.content
        assert "Refactored the auth module" in msg.content
        assert msg.status == "pending"

        # Verify sender stored in meta_data (Message has no from_agent column)
        assert msg.meta_data is not None
        assert msg.meta_data.get("_from_agent") == str(spec_spawn.agent_id)


# ============================================================================
# Test 3: Orchestrator completion does NOT create auto-message
# ============================================================================


@pytest.mark.asyncio
class TestOrchestratorCompletionNoMessage:
    """Verify that when the orchestrator itself completes, no auto-message is generated."""

    async def test_no_completion_report_for_orchestrator(
        self, db_session, service, project, tenant_key
    ):
        """Orchestrator completing should NOT create a completion_report message to itself."""
        # Arrange: spawn orchestrator only
        orch_spawn = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            mission="Orchestrate everything",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        result_payload = {
            "summary": "Project orchestration complete",
        }

        # Act: complete the orchestrator job
        await service.complete_job(
            job_id=orch_spawn.job_id,
            result=result_payload,
            tenant_key=tenant_key,
        )

        # Assert: NO completion_report message created
        msg_stmt = select(Message).where(
            Message.tenant_key == tenant_key,
            Message.project_id == project.id,
            Message.message_type == "completion_report",
        )
        msg_res = await db_session.execute(msg_stmt)
        messages = msg_res.scalars().all()

        assert len(messages) == 0, (
            f"Expected 0 completion_report messages for orchestrator self-completion, got {len(messages)}"
        )


# ============================================================================
# Test 4: get_agent_result returns stored result
# ============================================================================


@pytest.mark.asyncio
class TestGetAgentResult:
    """Verify get_agent_result() retrieves the stored completion result."""

    async def test_returns_stored_result_dict(
        self, db_session, service, project, tenant_key
    ):
        """get_agent_result should return the result dict after a job is completed."""
        # Arrange: spawn and complete an agent
        spawn = await service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Do work",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        result_payload = {
            "summary": "All tests passing",
            "artifacts": ["tests/test_auth.py"],
            "test_results": {"passed": 42, "failed": 0},
        }

        await service.complete_job(
            job_id=spawn.job_id,
            result=result_payload,
            tenant_key=tenant_key,
        )

        # Act: retrieve the result
        stored_result = await service.get_agent_result(
            job_id=spawn.job_id,
            tenant_key=tenant_key,
        )

        # Assert: matches what was stored
        assert stored_result is not None
        assert stored_result == result_payload
        assert stored_result["summary"] == "All tests passing"
        assert stored_result["test_results"]["passed"] == 42


# ============================================================================
# Test 5: get_agent_result returns None for incomplete jobs
# ============================================================================


@pytest.mark.asyncio
class TestGetAgentResultIncomplete:
    """Verify get_agent_result() returns None for jobs that have not completed."""

    async def test_returns_none_for_working_agent(
        self, db_session, service, project, tenant_key
    ):
        """get_agent_result should return None when the agent has not completed."""
        # Arrange: spawn an agent but do NOT complete it
        spawn = await service.spawn_agent_job(
            agent_display_name="specialist",
            agent_name="specialist-1",
            mission="Still working on it",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        # Act: try to retrieve result for an incomplete job
        stored_result = await service.get_agent_result(
            job_id=spawn.job_id,
            tenant_key=tenant_key,
        )

        # Assert: no result available
        assert stored_result is None
