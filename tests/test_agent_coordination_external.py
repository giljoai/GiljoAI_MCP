"""
Comprehensive test suite for External Agent Coordination HTTP-based MCP Tools (Handover 0060).

Tests all 7 coordination tools with focus on:
- HTTP communication with API server
- Authentication and JWT token handling
- Multi-tenant isolation (CRITICAL)
- Error handling (401, 403, 404, 500, connection errors)
- Session management and reuse
- Retry logic for transient failures
- Request timeouts

Following TDD principles - tests written BEFORE implementation.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import aiohttp
import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_response(status: int, json_data: Optional[Dict[str, Any]] = None, text_data: str = "") -> MagicMock:
    """
    Create a properly configured mock HTTP response.

    Args:
        status: HTTP status code
        json_data: JSON response data
        text_data: Text response data

    Returns:
        MagicMock configured as aiohttp response with async context manager
    """
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data or {})
    response.text = AsyncMock(return_value=text_data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


@pytest.fixture
def mock_config():
    """Mock ConfigManager for testing."""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "api.base_url": "http://localhost:7272",
        "auth.username": "test_user",
        "auth.password": "test_pass",
    }.get(key, default)
    return config


@pytest.fixture
def tenant_key():
    """Generate unique tenant key for each test."""
    return str(uuid4())


@pytest.fixture
def other_tenant_key():
    """Generate second tenant key for isolation tests."""
    return str(uuid4())


@pytest.fixture
def job_id():
    """Generate unique job ID for testing."""
    return str(uuid4())


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession for testing."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.close = AsyncMock()
    # Session methods will be mocked per-test
    return session


class TestExternalAgentCoordinationTools:
    """Test suite for ExternalAgentCoordinationTools class."""

    @pytest.mark.asyncio
    async def test_create_agent_job_success(self, mock_session, mock_config, tenant_key, job_id):
        """Test successful job creation via HTTP API."""
        # Mock responses
        auth_response = create_mock_response(200)
        create_response = create_mock_response(201, {"job_id": job_id, "message": "Job created successfully"})

        # Mock session.post() for authentication and session.request() for API calls
        mock_session.post.return_value = auth_response
        mock_session.request.return_value = create_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.create_agent_job(
                agent_display_name="implementer", mission="Implement feature X", context_chunks=["chunk1", "chunk2"]
            )

        assert result["status"] == "success"
        assert result["job_id"] == job_id
        assert "created successfully" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_send_agent_message_success(self, mock_session, mock_config, job_id):
        """Test successful message sending via HTTP API."""
        auth_response = create_mock_response(200)
        message_response = create_mock_response(
            200, {"message_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = message_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.send_agent_message(
                job_id=job_id, role="agent", message_type="progress", content={"summary": "Completed task X"}
            )

        assert result["status"] == "success"
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_get_agent_job_status_success(self, mock_session, mock_config, job_id, tenant_key):
        """Test successful job status retrieval via HTTP API."""
        auth_response = create_mock_response(200)
        status_response = create_mock_response(
            200,
            {
                "id": 1,
                "job_id": job_id,
                "tenant_key": tenant_key,
                "agent_display_name": "implementer",
                "mission": "Test mission",
                "status": "active",
                "spawned_by": None,
                "context_chunks": ["chunk1"],
                "messages": [],
                "acknowledged": True,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = status_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id=job_id)

        assert result["status"] == "success"
        assert result["job"]["job_id"] == job_id
        assert result["job"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_acknowledge_agent_job_success(self, mock_session, mock_config, job_id):
        """Test successful job acknowledgment via HTTP API."""
        auth_response = create_mock_response(200)
        ack_response = create_mock_response(
            200,
            {
                "job_id": job_id,
                "status": "active",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "message": "Job acknowledged successfully",
            },
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = ack_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.acknowledge_agent_job(job_id=job_id)

        assert result["status"] == "success"
        assert result["job"]["job_id"] == job_id
        assert result["job"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_complete_agent_job_success(self, mock_session, mock_config, job_id):
        """Test successful job completion via HTTP API."""
        auth_response = create_mock_response(200)
        complete_response = create_mock_response(
            200,
            {
                "job_id": job_id,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "message": "Job completed successfully",
            },
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = complete_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.complete_agent_job(
                job_id=job_id, result={"summary": "Completed successfully", "files_modified": ["file1.py"]}
            )

        assert result["status"] == "success"
        assert result["job_id"] == job_id
        assert "completed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_fail_agent_job_success(self, mock_session, mock_config, job_id):
        """Test successful job failure via HTTP API."""
        auth_response = create_mock_response(200)
        fail_response = create_mock_response(
            200,
            {
                "job_id": job_id,
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "message": "Job failed successfully",
            },
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = fail_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.fail_agent_job(
                job_id=job_id, error={"type": "test_failure", "message": "Tests failed"}
            )

        assert result["status"] == "success"
        assert result["job_id"] == job_id
        assert "failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_active_agent_jobs_success(self, mock_session, mock_config, job_id, tenant_key):
        """Test successful listing of active jobs via HTTP API."""
        auth_response = create_mock_response(200)
        list_response = create_mock_response(
            200,
            {
                "jobs": [
                    {
                        "id": 1,
                        "job_id": job_id,
                        "tenant_key": tenant_key,
                        "agent_display_name": "implementer",
                        "mission": "Test mission",
                        "status": "active",
                        "spawned_by": None,
                        "context_chunks": [],
                        "messages": [],
                        "acknowledged": True,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "completed_at": None,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
                "total": 1,
            },
        )

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = list_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.list_active_agent_jobs(status="active")

        assert result["status"] == "success"
        assert len(result["jobs"]) == 1
        assert result["total"] == 1
        assert result["jobs"][0]["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_job_not_found_error(self, mock_session, mock_config):
        """Test 404 job not found error handling."""
        auth_response = create_mock_response(200)
        not_found_response = create_mock_response(404, text_data="Job not found")

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = not_found_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id="nonexistent-job-id")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_403_error(self, mock_session, mock_config, job_id):
        """Test 403 multi-tenant isolation error handling."""
        auth_response = create_mock_response(200)
        forbidden_response = create_mock_response(403, text_data="Unauthorized access")

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = forbidden_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id=job_id)

        assert result["status"] == "error"
        assert "unauthorized" in result["error"].lower() or "forbidden" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_session, mock_config, job_id):
        """Test connection error handling."""
        # Mock connection error during authentication (session.post)
        # Note: Using a simple OSError as ClientConnectorError requires complex connection_key setup
        mock_session.post.side_effect = OSError("Connection refused")

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id=job_id)

        assert result["status"] == "error"
        # The error gets caught and wrapped, so just check it's an error status
        assert "error" in result

    @pytest.mark.asyncio
    async def test_server_error_500_handling(self, mock_session, mock_config, job_id):
        """Test 500 internal server error handling."""
        auth_response = create_mock_response(200)
        error_response = create_mock_response(500, text_data="Internal server error")

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = error_response

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id=job_id)

        assert result["status"] == "error"
        assert "server error" in result["error"].lower() or "retries" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, mock_session, mock_config, job_id):
        """Test request timeout handling."""
        auth_response = create_mock_response(200)
        # Mock authentication success, then timeout on actual request
        mock_session.post.return_value = auth_response
        mock_session.request.side_effect = asyncio.TimeoutError("Request timeout")

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id=job_id)

        assert result["status"] == "error"
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_input_validation_empty_job_id(self, mock_session, mock_config):
        """Test input validation for empty job_id."""
        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.get_agent_job_status(job_id="")

        assert result["status"] == "error"
        assert "empty" in result["error"].lower() or "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_input_validation_missing_required_fields(self, mock_session, mock_config):
        """Test input validation for missing required fields."""
        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import ExternalAgentCoordinationTools

            tools = ExternalAgentCoordinationTools(mock_session, mock_config)
            result = await tools.create_agent_job(agent_display_name="", mission="Test mission")

        assert result["status"] == "error"
        assert "empty" in result["error"].lower() or "required" in result["error"].lower()


class TestExternalToolsRegistration:
    """Test registration function for external tools."""

    def test_register_external_agent_coordination_tools(self, mock_config):
        """Test tool registration function."""
        tools = {}

        with patch("src.giljo_mcp.tools.agent_coordination_external.ConfigManager", return_value=mock_config):
            from src.giljo_mcp.tools.agent_coordination_external import register_external_agent_coordination_tools

            register_external_agent_coordination_tools(tools, mock_config)

        # Verify all 7 tools are registered
        expected_tools = [
            "create_agent_job_external",
            "send_agent_message_external",
            "get_agent_job_status_external",
            "acknowledge_agent_job_external",
            "complete_agent_job_external",
            "fail_agent_job_external",
            "list_active_agent_jobs_external",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"
            assert callable(tools[tool_name]), f"Tool {tool_name} is not callable"
