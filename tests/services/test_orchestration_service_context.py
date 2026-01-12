"""
Test suite for OrchestrationService context tracking and succession integration (Handover 0502).

Tests cover:
- Context usage tracking and incrementation
- Automatic succession trigger at 90% threshold
- Token estimation using tiktoken
- Manual succession triggering
- Validation and error handling
- Context field initialization in spawn_agent_job
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.projects import Project


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Mock tenant manager."""
    tenant_manager = MagicMock()
    return tenant_manager


@pytest.fixture
def orchestration_service(mock_db_manager, mock_tenant_manager):
    """Create OrchestrationService with mocked dependencies."""
    db_manager, _ = mock_db_manager
    service = OrchestrationService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager
    )
    return service


@pytest.fixture
def mock_orchestrator_job():
    """Create mock orchestrator agent job."""
    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test",
        project_id=str(uuid4()),
        agent_display_name="orchestrator",
        agent_name="orchestrator-1",
        mission="Test orchestrator mission",
        status="working",
        context_used=150000,
        context_budget=200000,
        handover_to=None,
        succession_reason=None,
        metadata={}
    )
    return job


@pytest.mark.asyncio
async def test_report_progress_todo_updates_job_metadata_steps(mock_db_manager, mock_tenant_manager):
    """Test that report_progress(mode='todo') updates job_metadata with steps summary."""
    db_manager, session = mock_db_manager
    tenant_manager = mock_tenant_manager
    tenant_manager.get_current_tenant.return_value = "tenant-test-steps"

    service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

    # Stub MessageService to avoid hitting real queue/WebSocket
    mock_message_service = MagicMock()
    mock_message_service.send_message = AsyncMock(return_value={"success": True, "message_id": "msg-steps-001"})
    service._message_service = mock_message_service

    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test-steps",
        project_id=str(uuid4()),
        agent_display_name="implementer",
        agent_name="impl-steps-1",
        mission="Test mission for TODO steps",
        status="working",
        job_metadata={},
    )

    # Mock database lookup for job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    progress_payload = {
        "mode": "todo",
        "total_steps": 5,
        "completed_steps": 2,
        "current_step": "Writing tests for TODO steps",
    }

    response = await service.report_progress(
        job_id=job.job_id,
        progress=progress_payload,
        tenant_key="tenant-test-steps",
    )

    # Service call should succeed
    assert response["status"] == "success"

    # MessageService should be used
    mock_message_service.send_message.assert_awaited_once()

    # job_metadata should contain normalized TODO steps summary
    assert isinstance(job.job_metadata, dict)
    assert "todo_steps" in job.job_metadata
    steps = job.job_metadata["todo_steps"]
    assert steps["total_steps"] == 5
    assert steps["completed_steps"] == 2
    assert steps["current_step"] == "Writing tests for TODO steps"


@pytest.mark.asyncio
async def test_report_progress_non_todo_does_not_set_steps(mock_db_manager, mock_tenant_manager):
    """Test that non-todo progress payloads do not set todo_steps metadata."""
    db_manager, session = mock_db_manager
    tenant_manager = mock_tenant_manager
    tenant_manager.get_current_tenant.return_value = "tenant-test-steps"

    service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager)

    mock_message_service = MagicMock()
    mock_message_service.send_message = AsyncMock(return_value={"success": True, "message_id": "msg-progress-001"})
    service._message_service = mock_message_service

    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test-steps",
        project_id=str(uuid4()),
        agent_display_name="implementer",
        agent_name="impl-progress-1",
        mission="Test mission for regular progress",
        status="working",
        job_metadata={},
    )

    # Mock database lookup
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    progress_payload = {
        "percent": 50,
        "message": "Half done",
    }

    response = await service.report_progress(
        job_id=job.job_id,
        progress=progress_payload,
        tenant_key="tenant-test-steps",
    )

    assert response["status"] == "success"
    mock_message_service.send_message.assert_awaited_once()

    # No todo_steps summary should be set for non-todo progress
    assert isinstance(job.job_metadata, dict)
    assert "todo_steps" not in job.job_metadata


@pytest.mark.asyncio
async def test_update_context_usage_increments_correctly(orchestration_service, mock_db_manager, mock_orchestrator_job):
    """Test that update_context_usage correctly increments context_used."""
    db_manager, session = mock_db_manager
    job = mock_orchestrator_job

    # Mock database query to return job
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Test: Add 10000 tokens (should not trigger succession at 80%)
    response = await orchestration_service.update_context_usage(
        job_id=job.job_id,
        additional_tokens=10000,
        tenant_key="tenant-test"
    )

    # Verify
    assert response["success"] is True
    assert response["context_used"] == 160000
    assert response["context_budget"] == 200000
    assert response["usage_percentage"] == 80.0
    assert response["succession_triggered"] is False
    assert job.context_used == 160000

    # Verify session.commit was called
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_context_usage_triggers_succession_at_90_percent(orchestration_service, mock_db_manager, mock_orchestrator_job):
    """Test that update_context_usage triggers auto-succession at 90% threshold."""
    db_manager, session = mock_db_manager
    job = mock_orchestrator_job
    job.context_used = 170000  # 85% usage

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock OrchestratorSuccessionManager
    with patch("src.giljo_mcp.services.orchestration_service.OrchestratorSuccessionManager") as MockSuccessionManager:
        mock_succession = AsyncMock()
        successor_job = MagicMock()
        successor_job.job_id = str(uuid4())
        mock_succession.create_successor = AsyncMock(return_value=successor_job)
        MockSuccessionManager.return_value = mock_succession

        # Test: Add 15000 tokens (170000 + 15000 = 185000 = 92.5%)
        response = await orchestration_service.update_context_usage(
            job_id=job.job_id,
            additional_tokens=15000,
            tenant_key="tenant-test"
        )

        # Verify succession was triggered
        assert response["success"] is True
        assert response["context_used"] == 185000
        assert response["usage_percentage"] == 92.5
        assert response["succession_triggered"] is True
        assert job.handover_to == successor_job.job_id
        assert job.succession_reason == "context_limit"

        # Verify create_successor was called with correct params
        mock_succession.create_successor.assert_called_once()
        call_kwargs = mock_succession.create_successor.call_args[1]
        assert call_kwargs["current_job_id"] == job.job_id
        assert call_kwargs["reason"] == "context_limit"


@pytest.mark.asyncio
async def test_update_context_usage_does_not_trigger_if_already_succeeded(orchestration_service, mock_db_manager, mock_orchestrator_job):
    """Test that update_context_usage does not trigger succession if handover_to is already set."""
    db_manager, session = mock_db_manager
    job = mock_orchestrator_job
    job.context_used = 170000
    job.handover_to = str(uuid4())  # Already has successor

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    with patch("src.giljo_mcp.services.orchestration_service.OrchestratorSuccessionManager") as MockSuccessionManager:
        mock_succession = AsyncMock()
        MockSuccessionManager.return_value = mock_succession

        # Test: Add tokens to reach 92.5%
        response = await orchestration_service.update_context_usage(
            job_id=job.job_id,
            additional_tokens=15000,
            tenant_key="tenant-test"
        )

        # Verify succession was NOT triggered
        assert response["success"] is True
        assert response["succession_triggered"] is False
        mock_succession.create_successor.assert_not_called()


@pytest.mark.asyncio
async def test_update_context_usage_job_not_found(orchestration_service, mock_db_manager):
    """Test that update_context_usage raises ValueError when job not found."""
    db_manager, session = mock_db_manager

    # Mock database query to return None
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result)

    # Test: Should raise ValueError
    with pytest.raises(ValueError, match="Job not found"):
        await orchestration_service.update_context_usage(
            job_id="nonexistent-job",
            additional_tokens=1000,
            tenant_key="tenant-test"
        )


@pytest.mark.asyncio
async def test_estimate_message_tokens_uses_tiktoken(orchestration_service):
    """Test that estimate_message_tokens uses tiktoken cl100k_base encoding."""
    # Test with known message
    message = "Hello, world! This is a test message for token estimation."

    token_count = await orchestration_service.estimate_message_tokens(message)

    # Verify token count is reasonable (should be ~12-15 tokens)
    assert isinstance(token_count, int)
    assert 10 <= token_count <= 20

    # Test with empty message
    empty_count = await orchestration_service.estimate_message_tokens("")
    assert empty_count == 0

    # Test with longer message
    long_message = "This is a much longer message that contains multiple sentences. " * 10
    long_count = await orchestration_service.estimate_message_tokens(long_message)
    assert long_count > token_count


@pytest.mark.asyncio
async def test_trigger_succession_manual_creates_successor(orchestration_service, mock_db_manager, mock_orchestrator_job):
    """Test that trigger_succession manually creates successor."""
    db_manager, session = mock_db_manager
    job = mock_orchestrator_job

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Mock OrchestratorSuccessionManager
    with patch("src.giljo_mcp.services.orchestration_service.OrchestratorSuccessionManager") as MockSuccessionManager:
        mock_succession = AsyncMock()
        successor_job = MagicMock()
        successor_job.job_id = str(uuid4())
        successor_job.agent_name = "orchestrator-2"
        successor_job.instance_number = 2
        mock_succession.create_successor = AsyncMock(return_value=successor_job)
        MockSuccessionManager.return_value = mock_succession

        # Test: Manual trigger
        response = await orchestration_service.trigger_succession(
            job_id=job.job_id,
            reason="manual",
            tenant_key="tenant-test"
        )

        # Verify
        assert response["success"] is True
        assert response["successor_job_id"] == successor_job.job_id
        assert job.handover_to == successor_job.job_id
        assert job.succession_reason == "manual"

        # Verify create_successor called with manual reason
        mock_succession.create_successor.assert_called_once()
        call_kwargs = mock_succession.create_successor.call_args[1]
        assert call_kwargs["reason"] == "manual"


@pytest.mark.asyncio
async def test_trigger_succession_rejects_non_orchestrator(orchestration_service, mock_db_manager):
    """Test that trigger_succession rejects non-orchestrator agents."""
    db_manager, session = mock_db_manager

    # Create non-orchestrator job
    job = AgentExecution(
        job_id=str(uuid4()),
        tenant_key="tenant-test",
        project_id=str(uuid4()),
        agent_display_name="implementer",  # Not orchestrator
        agent_name="impl-1",
        mission="Test mission",
        status="working",
        metadata={}
    )

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Test: Should raise ValueError
    with pytest.raises(ValueError, match="Only orchestrator agents can trigger succession"):
        await orchestration_service.trigger_succession(
            job_id=job.job_id,
            reason="manual",
            tenant_key="tenant-test"
        )


@pytest.mark.asyncio
async def test_trigger_succession_rejects_already_succeeded(orchestration_service, mock_db_manager, mock_orchestrator_job):
    """Test that trigger_succession rejects jobs that already have successors."""
    db_manager, session = mock_db_manager
    job = mock_orchestrator_job
    job.handover_to = str(uuid4())  # Already has successor

    # Mock database query
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=job)
    session.execute = AsyncMock(return_value=result)

    # Test: Should raise ValueError
    with pytest.raises(ValueError, match="Job already has a successor"):
        await orchestration_service.trigger_succession(
            job_id=job.job_id,
            reason="manual",
            tenant_key="tenant-test"
        )


@pytest.mark.asyncio
async def test_trigger_succession_job_not_found(orchestration_service, mock_db_manager):
    """Test that trigger_succession raises ValueError when job not found."""
    db_manager, session = mock_db_manager

    # Mock database query to return None
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result)

    # Test: Should raise ValueError
    with pytest.raises(ValueError, match="Job not found"):
        await orchestration_service.trigger_succession(
            job_id="nonexistent-job",
            reason="manual",
            tenant_key="tenant-test"
        )


@pytest.mark.asyncio
async def test_spawn_agent_job_sets_context_fields_for_orchestrator(orchestration_service, mock_db_manager):
    """Test that spawn_agent_job initializes context fields for orchestrator agents."""
    db_manager, session = mock_db_manager

    # Mock project query
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key="tenant-test",
        product_id=str(uuid4()),
        status="active",
        metadata={}
    )
    project_result = MagicMock()
    project_result.scalar_one_or_none = MagicMock(return_value=project)

    # Mock httpx for WebSocket bridge
    with patch("httpx.AsyncClient") as MockHttpxClient:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        MockHttpxClient.return_value = mock_client

        # Track added jobs
        added_jobs = []

        def capture_add(job):
            added_jobs.append(job)

        session.add = capture_add
        session.execute = AsyncMock(return_value=project_result)

        # Test: Spawn orchestrator agent
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            mission="Test orchestrator mission for context tracking",
            project_id=project.id,
            tenant_key="tenant-test"
        )

        # Verify response
        assert result["success"] is True
        assert "job_id" in result

        # Verify context fields were set
        assert len(added_jobs) == 1
        job = added_jobs[0]
        assert job.agent_display_name == "orchestrator"
        assert job.context_budget == 200000
        assert job.context_used is not None
        assert job.context_used > 0  # Should estimate initial mission tokens
        assert job.context_used < job.context_budget


@pytest.mark.asyncio
async def test_spawn_agent_job_does_not_set_context_for_non_orchestrator(orchestration_service, mock_db_manager):
    """Test that spawn_agent_job does NOT set context fields for non-orchestrator agents."""
    db_manager, session = mock_db_manager

    # Mock project query
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key="tenant-test",
        product_id=str(uuid4()),
        status="active",
        metadata={}
    )
    project_result = MagicMock()
    project_result.scalar_one_or_none = MagicMock(return_value=project)

    # Mock httpx for WebSocket bridge
    with patch("httpx.AsyncClient") as MockHttpxClient:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        MockHttpxClient.return_value = mock_client

        # Track added jobs
        added_jobs = []

        def capture_add(job):
            added_jobs.append(job)

        session.add = capture_add
        session.execute = AsyncMock(return_value=project_result)

        # Test: Spawn implementer agent
        result = await orchestration_service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Test implementer mission",
            project_id=project.id,
            tenant_key="tenant-test"
        )

        # Verify response
        assert result["success"] is True

        # Verify context fields were NOT set
        assert len(added_jobs) == 1
        job = added_jobs[0]
        assert job.agent_display_name == "implementer"
        assert job.context_budget is None
        assert job.context_used is None
