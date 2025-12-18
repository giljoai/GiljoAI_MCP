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
