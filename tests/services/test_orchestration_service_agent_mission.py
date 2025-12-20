"""
Test suite for OrchestrationService.get_agent_mission() protocol enhancement (Handover 0334).

Tests cover:
- full_protocol field presence when include_protocol=True
- 6-phase lifecycle protocol embedded in response
- Phase markers (Phase 1 through Phase 6)
- MCP tools reference in protocol
- Backward compatibility (include_protocol defaults to True)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models.agents import MCPAgentJob


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
def mock_agent_job():
    """Create mock agent job."""
    job = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key="tenant-test",
        project_id=str(uuid4()),
        agent_type="implementer",
        agent_name="implementer-1",
        mission="Implement the user authentication module with JWT tokens.",
        status="waiting",
        mission_acknowledged_at=None,
        started_at=None,
    )
    return job


class TestGetAgentMissionFullProtocol:
    """Test suite for full_protocol field in get_agent_mission response."""

    @pytest.mark.asyncio
    async def test_get_agent_mission_returns_full_protocol_by_default(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that get_agent_mission returns full_protocol field by default."""
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query to return job
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        # Stub httpx to avoid real WebSocket bridge calls
        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        # Verify full_protocol field exists
        assert "full_protocol" in response, "Response must include full_protocol field"
        assert isinstance(response["full_protocol"], str)
        assert len(response["full_protocol"]) > 0

    @pytest.mark.asyncio
    async def test_full_protocol_contains_five_phases(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that full_protocol contains all 5 lifecycle phases (Handover 0359)."""
        db_manager, session = mock_db_manager
        job = mock_agent_job

        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response["full_protocol"]

        # Verify all 5 phases are present (Handover 0359: consolidated from 6 to 5)
        assert "Phase 1" in protocol or "STARTUP" in protocol.upper(), "Protocol must include Phase 1 (Startup)"
        assert "Phase 2" in protocol or "EXECUTION" in protocol.upper(), "Protocol must include Phase 2 (Execution)"
        assert "Phase 3" in protocol or "PROGRESS" in protocol.upper(), "Protocol must include Phase 3 (Progress)"
        assert "Phase 4" in protocol or "COMPLETION" in protocol.upper(), "Protocol must include Phase 4 (Completion)"
        assert "Phase 5" in protocol or "ERROR" in protocol.upper(), "Protocol must include Phase 5 (Error Handling)"

    @pytest.mark.asyncio
    async def test_full_protocol_references_mcp_tools(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that full_protocol references required MCP tools."""
        db_manager, session = mock_db_manager
        job = mock_agent_job

        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response["full_protocol"]

        # Verify MCP tool references
        assert "report_progress" in protocol.lower(), "Protocol must reference report_progress tool"
        assert "complete_job" in protocol.lower(), "Protocol must reference complete_job tool"

    @pytest.mark.asyncio
    async def test_full_protocol_includes_job_context(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that full_protocol includes job-specific context."""
        db_manager, session = mock_db_manager
        job = mock_agent_job
        job.job_id = "unique-job-id-12345"

        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response["full_protocol"]

        # Protocol should include job ID for proper MCP tool calls
        assert job.job_id in protocol, "Protocol must include job_id for MCP tool calls"

    @pytest.mark.asyncio
    async def test_response_backward_compatible_with_existing_fields(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that full_protocol addition maintains backward compatibility."""
        db_manager, session = mock_db_manager
        job = mock_agent_job

        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        # Verify all existing fields are still present
        assert response.get("success") is True
        assert "agent_job_id" in response
        assert "agent_name" in response
        assert "agent_type" in response
        assert "mission" in response
        assert "project_id" in response
        assert "estimated_tokens" in response
        assert "thin_client" in response
        assert "status" in response
        # NEW field
        assert "full_protocol" in response

    @pytest.mark.asyncio
    async def test_protocol_includes_message_handling_instructions(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Test that protocol includes message handling instructions (Issue 0361-5)."""
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        assert response.get("success") is True
        protocol = response.get("full_protocol", "")

        # Verify message handling instructions present (Issue 0361-5)
        assert "MESSAGE HANDLING" in protocol
        assert "receive_messages()" in protocol
        assert "list_messages()" in protocol
        assert "auto-acknowledges" in protocol or "auto-acknowledge" in protocol


class TestAgentProtocolMessageHandlingEnhancements:
    """Test suite for Handover 0355 - Protocol Message Handling enhancements."""

    @pytest.mark.asyncio
    async def test_agent_protocol_phase2_includes_message_check_after_tasks(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Phase 2 EXECUTION should instruct agents to check messages after each TodoWrite task.

        This ensures agents check for orchestrator instructions during long-running work,
        not just at startup and completion.
        """
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response.get("full_protocol", "")

        # Extract Phase 2 section
        phase2_start = protocol.find("### Phase 2")
        phase2_end = protocol.find("### Phase 3")
        phase2_section = protocol[phase2_start:phase2_end] if phase2_start != -1 and phase2_end != -1 else ""

        # BEHAVIOR: Phase 2 must include message check instruction
        assert "receive_messages()" in phase2_section, \
            "Phase 2 EXECUTION must instruct agents to check messages after each task"

        # BEHAVIOR: Instruction should mention checking after tasks/TodoWrite
        assert ("after" in phase2_section.lower() or "completing" in phase2_section.lower()), \
            "Phase 2 must specify WHEN to check messages (after each task)"

    @pytest.mark.asyncio
    async def test_agent_protocol_phase3_checks_messages_before_reporting(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Phase 3 PROGRESS should check messages BEFORE reporting progress.

        This prevents agents from reporting progress without incorporating
        orchestrator feedback first.
        """
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response.get("full_protocol", "")

        # Extract Phase 3 section
        phase3_start = protocol.find("### Phase 3")
        phase3_end = protocol.find("### Phase 4")
        phase3_section = protocol[phase3_start:phase3_end] if phase3_start != -1 and phase3_end != -1 else ""

        # BEHAVIOR: receive_messages() must come BEFORE report_progress() in Phase 3
        receive_pos = phase3_section.find("receive_messages()")
        report_pos = phase3_section.find("report_progress(")

        assert receive_pos != -1, "Phase 3 must include receive_messages() call"
        assert report_pos != -1, "Phase 3 must include report_progress() call"
        assert receive_pos < report_pos, \
            "Phase 3 must check messages BEFORE reporting progress (receive_messages before report_progress)"

        # BEHAVIOR: Should emphasize this is MANDATORY/BEFORE
        assert ("before" in phase3_section.lower() or "mandatory" in phase3_section.lower()), \
            "Phase 3 must clearly state messages should be checked BEFORE reporting"

    @pytest.mark.asyncio
    async def test_agent_protocol_phase4_requires_empty_queue_before_completion(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Phase 4 COMPLETION should require empty message queue before complete_job().

        This prevents agents from completing while orchestrator has pending instructions.
        """
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response.get("full_protocol", "")

        # Extract Phase 4 section
        phase4_start = protocol.find("### Phase 4")
        phase4_end = protocol.find("### Phase 5")
        phase4_section = protocol[phase4_start:phase4_end] if phase4_start != -1 and phase4_end != -1 else ""

        # BEHAVIOR: Phase 4 must include receive_messages() instruction
        assert "receive_messages()" in phase4_section, \
            "Phase 4 COMPLETION must instruct agents to check messages before completing"

        # BEHAVIOR: Should mention queue must be empty or similar gate language
        queue_gate_indicators = ["queue", "empty", "no pending", "clear", "before completing"]
        has_gate_language = any(indicator in phase4_section.lower() for indicator in queue_gate_indicators)

        assert has_gate_language, \
            "Phase 4 must include gate language requiring empty queue before completion"

    @pytest.mark.asyncio
    async def test_agent_protocol_includes_when_to_check_messages_guidance(
        self, orchestration_service, mock_db_manager, mock_agent_job
    ):
        """Protocol should have clear guidance on WHEN to check messages in each phase.

        This ensures agents understand the complete message checking pattern across
        all phases of execution.
        """
        db_manager, session = mock_db_manager
        job = mock_agent_job

        # Mock database query
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=job)
        session.execute = AsyncMock(return_value=result)

        with patch("httpx.AsyncClient") as MockHttpxClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            MockHttpxClient.return_value = mock_client

            response = await orchestration_service.get_agent_mission(
                agent_job_id=job.job_id,
                tenant_key="tenant-test"
            )

        protocol = response.get("full_protocol", "")

        # BEHAVIOR: Protocol should have guidance section about when to check messages
        guidance_indicators = [
            "when to check",
            "message checking",
            "check messages in each phase",
            "across phases"
        ]

        has_guidance = any(indicator in protocol.lower() for indicator in guidance_indicators)

        assert has_guidance, \
            "Protocol must include clear guidance on WHEN to check messages across phases"

        # BEHAVIOR: Should reference all phases in message handling context
        # Not just Phase 1 startup check - should cover ongoing checking pattern
        phases_mentioned = sum([
            "phase 1" in protocol.lower() and "message" in protocol.lower(),
            "phase 2" in protocol.lower() and "message" in protocol.lower(),
            "phase 3" in protocol.lower() and "message" in protocol.lower(),
            "phase 4" in protocol.lower() and "message" in protocol.lower()
        ])

        assert phases_mentioned >= 3, \
            "Message handling guidance should reference at least 3 phases (startup, execution, completion)"
