import uuid

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest_asyncio.fixture
async def test_tenant_0367e() -> str:
    """Generate unique tenant key for 0367e tests."""
    return f"tk_0367e_{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def test_orchestrator_job_0367e(
    db_session: AsyncSession,
    test_tenant_0367e: str,
) -> AgentJob:
    """Create test AgentJob for orchestrator."""
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=test_tenant_0367e,
        project_id=str(uuid.uuid4()),
        mission="Test orchestrator mission for 0367e",
        job_type="orchestrator",
        status="active",
        job_metadata={},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_orchestrator_execution_0367e(
    db_session: AsyncSession,
    test_orchestrator_job_0367e: AgentJob,
    test_tenant_0367e: str,
) -> AgentExecution:
    """Create active orchestrator AgentExecution."""
    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=test_orchestrator_job_0367e.job_id,
        tenant_key=test_tenant_0367e,
        agent_display_name="orchestrator",        status="working",
        progress=10,
        context_used=0,
        context_budget=10000,
        tool_type="universal",
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


@pytest.mark.asyncio
async def test_handle_gil_handover_uses_agent_execution_only(
    db_session: AsyncSession,
    test_tenant_0367e: str,
    test_orchestrator_job_0367e: AgentJob,
    test_orchestrator_execution_0367e: AgentExecution,
):
    """
    handle_gil_handover should operate on AgentExecution, not MCPAgentJob.

    Given an active orchestrator execution for a job_id, the slash command
    should create a successor and return a launch prompt without requiring
    any MCPAgentJob records.
    """
    from src.giljo_mcp.slash_commands.handover import handle_gil_handover

    result = await handle_gil_handover(
        db_session=db_session,
        tenant_key=test_tenant_0367e,
        project_id=None,
        orchestrator_job_id=test_orchestrator_job_0367e.job_id,
    )

    assert result["success"] is True
    assert result.get("successor_id")
    assert isinstance(result.get("launch_prompt"), str)
    assert result["handover_summary"]  # Basic sanity check


@pytest.mark.asyncio
async def test_handle_gil_handover_returns_error_when_execution_not_found(
    db_session: AsyncSession,
    test_tenant_0367e: str,
):
    """
    handle_gil_handover should return a structured error when no active
    orchestrator execution exists for the given job_id/tenant.
    """
    from src.giljo_mcp.slash_commands.handover import handle_gil_handover

    fake_job_id = str(uuid.uuid4())

    result = await handle_gil_handover(
        db_session=db_session,
        tenant_key=test_tenant_0367e,
        project_id=None,
        orchestrator_job_id=fake_job_id,
    )

    assert result["success"] is False
    assert result.get("error") in {"NO_ORCHESTRATOR", "INVALID_ORCHESTRATOR"}
