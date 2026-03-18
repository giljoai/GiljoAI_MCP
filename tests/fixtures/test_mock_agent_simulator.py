"""
Comprehensive tests for MockAgentSimulator.

Tests cover:
- MCP HTTP communication (fetch mission, send messages, report progress, complete job)
- Agent execution simulation (work phases, timing)
- Error handling (network errors, invalid responses, missing data)
- Multi-agent communication patterns
- Cross-platform compatibility
"""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from aiohttp import ClientError


@pytest.fixture
def mock_api_key() -> str:
    """Mock API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def mock_tenant_key() -> str:
    """Mock tenant key for testing"""
    return "test-tenant-abc"


@pytest.fixture
def mock_job_id() -> str:
    """Mock job ID for testing"""
    return "job-123-test"


@pytest.fixture
def mock_mission_response() -> dict[str, Any]:
    """Mock successful mission response from MCP"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "job_id": "job-123-test",
                            "agent_name": "implementer",
                            "agent_display_name": "implementer",
                            "mission": "Create REST API endpoint for user management",
                            "project_id": "project-456",
                            "parent_job_id": "orchestrator-789",
                            "status": "waiting",
                            "thin_client": True,
                        }
                    ),
                }
            ]
        },
    }


@pytest.fixture
def mock_send_message_response() -> dict[str, Any]:
    """Mock successful send_message response"""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": True, "message_id": "msg-999"}),
                }
            ]
        },
    }


@pytest.fixture
def mock_receive_messages_response() -> dict[str, Any]:
    """Mock successful receive_messages response"""
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": True,
                            "messages": [
                                {
                                    "id": "msg-111",
                                    "from_agent": "orchestrator-789",
                                    "to_agent": "job-123-test",
                                    "content": "Please provide status update",
                                    "created_at": "2025-11-27T10:00:00Z",
                                    "status": "waiting",
                                }
                            ],
                        }
                    ),
                }
            ]
        },
    }


@pytest.fixture
def mock_report_progress_response() -> dict[str, Any]:
    """Mock successful report_progress response"""
    return {
        "jsonrpc": "2.0",
        "id": 4,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": True}),
                }
            ]
        },
    }


@pytest.fixture
def mock_complete_job_response() -> dict[str, Any]:
    """Mock successful complete_job response"""
    return {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": True, "status": "completed"}),
                }
            ]
        },
    }


class TestMockAgentSimulatorMethods:
    """Test individual methods of MockAgentSimulator"""

    @pytest_asyncio.fixture
    async def mock_agent_simulator(self, mock_api_key, mock_tenant_key, mock_job_id):
        """Create MockAgentSimulator instance for testing"""
        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        simulator = MockAgentSimulator(
            job_id=mock_job_id,
            tenant_key=mock_tenant_key,
            api_key=mock_api_key,
            api_url="http://localhost:7272/mcp",
            agent_display_name="implementer",
        )
        yield simulator

        # Cleanup
        if simulator._session and not simulator._session.closed:
            await simulator._session.close()

    @pytest.mark.asyncio
    async def test_fetch_mission_success(
        self, mock_agent_simulator, mock_mission_response, mock_job_id, mock_tenant_key
    ):
        """Test successful mission fetch"""
        # Mock HTTP response
        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_mission_response

            result = await mock_agent_simulator.fetch_mission(mock_job_id, mock_tenant_key)

            assert result["success"] is True
            assert result["job_id"] == mock_job_id
            assert result["agent_display_name"] == "implementer"
            assert "mission" in result
            assert result["thin_client"] is True

            # Verify MCP request format
            mock_request.assert_called_once()
            call_args = mock_request.call_args[1]
            assert call_args["method"] == "mcp__giljo-mcp__get_agent_mission"
            assert call_args["arguments"]["job_id"] == mock_job_id
            assert call_args["arguments"]["tenant_key"] == mock_tenant_key

    @pytest.mark.asyncio
    async def test_fetch_mission_not_found(self, mock_agent_simulator, mock_job_id, mock_tenant_key):
        """Test mission fetch with job not found"""
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": "NOT_FOUND", "message": f"Agent job {mock_job_id} not found"}),
                    }
                ]
            },
        }

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = error_response

            result = await mock_agent_simulator.fetch_mission(mock_job_id, mock_tenant_key)

            assert "error" in result
            assert result["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_agent_simulator, mock_send_message_response):
        """Test successful message sending"""
        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_send_message_response

            result = await mock_agent_simulator.send_message_to_agent("tester-job-456", "Implementation complete")

            assert result["success"] is True
            assert "message_id" in result

            # Verify MCP request format
            mock_request.assert_called_once()
            call_args = mock_request.call_args[1]
            assert call_args["method"] == "mcp__giljo-mcp__send_message"
            assert call_args["arguments"]["to_agent"] == "tester-job-456"
            assert call_args["arguments"]["message"] == "Implementation complete"

    @pytest.mark.asyncio
    async def test_check_messages_success(self, mock_agent_simulator, mock_receive_messages_response):
        """Test successful message checking"""
        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_receive_messages_response

            result = await mock_agent_simulator.check_messages()

            assert result["success"] is True
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0]["from_agent"] == "orchestrator-789"

    @pytest.mark.asyncio
    async def test_report_progress_success(self, mock_agent_simulator, mock_report_progress_response):
        """Test successful progress reporting"""
        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_report_progress_response

            progress_data = {"phase": "implementation", "completion": 50, "details": "Created 3 endpoints"}

            result = await mock_agent_simulator.report_progress(progress_data)

            assert result["success"] is True

            # Verify MCP request format
            mock_request.assert_called_once()
            call_args = mock_request.call_args[1]
            assert call_args["method"] == "mcp__giljo-mcp__report_progress"
            assert call_args["arguments"]["progress"] == progress_data

    @pytest.mark.asyncio
    async def test_complete_job_success(self, mock_agent_simulator, mock_complete_job_response):
        """Test successful job completion"""
        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_complete_job_response

            completion_data = {"status": "success", "summary": "All endpoints created", "files_changed": 5}

            result = await mock_agent_simulator.complete_job(completion_data)

            assert result["success"] is True

            # Verify MCP request format
            mock_request.assert_called_once()
            call_args = mock_request.call_args[1]
            assert call_args["method"] == "mcp__giljo-mcp__complete_job"
            assert call_args["arguments"]["result"] == completion_data

    @pytest.mark.asyncio
    async def test_execute_work_timing(self, mock_agent_simulator):
        """Test that execute_work completes within expected timeframe"""
        import time

        mission_data = {"mission": "Test mission for timing validation"}

        start_time = time.time()
        await mock_agent_simulator.execute_work(mission_data)
        elapsed_time = time.time() - start_time

        # Should complete in 5-10 seconds
        assert 4 <= elapsed_time <= 12, f"Work execution took {elapsed_time:.2f}s, expected 5-10s"

    @pytest.mark.asyncio
    async def test_execute_work_logs_actions(self, mock_agent_simulator, caplog):
        """Test that execute_work logs its actions"""
        mission_data = {"mission": "Test mission with logging"}

        with caplog.at_level("INFO"):
            await mock_agent_simulator.execute_work(mission_data)

        # Verify logging occurred
        assert any("Starting work execution" in record.message for record in caplog.records)
        assert any("Work phase" in record.message for record in caplog.records)
        assert any("Work execution completed" in record.message for record in caplog.records)


class TestMockAgentSimulatorExecution:
    """Test complete execution flow"""

    @pytest_asyncio.fixture
    async def mock_agent_simulator(self, mock_api_key, mock_tenant_key, mock_job_id):
        """Create MockAgentSimulator instance for execution tests"""
        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        simulator = MockAgentSimulator(
            job_id=mock_job_id,
            tenant_key=mock_tenant_key,
            api_key=mock_api_key,
            api_url="http://localhost:7272/mcp",
            agent_display_name="implementer",
        )
        yield simulator

        # Cleanup
        if simulator._session and not simulator._session.closed:
            await simulator._session.close()

    @pytest.mark.asyncio
    async def test_run_complete_flow(
        self,
        mock_agent_simulator,
        mock_mission_response,
        mock_receive_messages_response,
        mock_report_progress_response,
        mock_complete_job_response,
    ):
        """Test complete agent execution flow: fetch → work → communicate → complete"""
        call_count = {"count": 0}

        async def mock_mcp_request(*args, **kwargs):
            """Mock MCP requests with appropriate responses"""
            call_count["count"] += 1
            method = kwargs.get("method", "")

            if "get_agent_mission" in method:
                return mock_mission_response
            if "receive_messages" in method:
                # Return empty messages to avoid infinite loops
                return {
                    "jsonrpc": "2.0",
                    "id": call_count["count"],
                    "result": {"content": [{"type": "text", "text": json.dumps({"success": True, "messages": []})}]},
                }
            if "report_progress" in method:
                return mock_report_progress_response
            if "complete_job" in method:
                return mock_complete_job_response
            return {"jsonrpc": "2.0", "id": call_count["count"], "result": {"content": []}}

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_mcp_request

            # Run complete flow
            await mock_agent_simulator.run()

            # Verify all phases were called
            assert call_count["count"] >= 3, "Should have made multiple MCP requests"

    @pytest.mark.asyncio
    async def test_run_handles_fetch_error(self, mock_agent_simulator):
        """Test run handles mission fetch errors gracefully"""

        async def mock_error_request(*args, **kwargs):
            """Mock request that raises error"""
            raise ClientError("Connection failed")

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_error_request

            # Should not raise exception
            await mock_agent_simulator.run()

    @pytest.mark.asyncio
    async def test_run_completes_in_time(self, mock_agent_simulator):
        """Test that complete run finishes within 15 seconds"""
        import time

        # Mock all MCP requests to return quickly
        async def mock_quick_response(*args, **kwargs):
            method = kwargs.get("method", "")
            if "get_agent_mission" in method:
                return {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "success": True,
                                        "job_id": "job-123",
                                        "agent_display_name": "implementer",
                                        "mission": "Quick test",
                                        "thin_client": True,
                                    }
                                ),
                            }
                        ]
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": json.dumps({"success": True})}]},
            }

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_quick_response

            start_time = time.time()
            await mock_agent_simulator.run()
            elapsed_time = time.time() - start_time

            assert elapsed_time <= 15, f"Complete run took {elapsed_time:.2f}s, expected <15s"


class TestMockAgentSimulatorErrorHandling:
    """Test error handling and edge cases"""

    @pytest_asyncio.fixture
    async def mock_agent_simulator(self, mock_api_key, mock_tenant_key, mock_job_id):
        """Create MockAgentSimulator instance for error handling tests"""
        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        simulator = MockAgentSimulator(
            job_id=mock_job_id,
            tenant_key=mock_tenant_key,
            api_key=mock_api_key,
            api_url="http://localhost:7272/mcp",
            agent_display_name="implementer",
        )
        yield simulator

        # Cleanup
        if simulator._session and not simulator._session.closed:
            await simulator._session.close()

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_agent_simulator):
        """Test handling of network errors"""

        async def mock_network_error(*args, **kwargs):
            raise ClientError("Network unreachable")

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_network_error

            result = await mock_agent_simulator.fetch_mission("job-123", "tenant-abc")

            assert "error" in result
            assert "network" in result["message"].lower() or "connection" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_agent_simulator):
        """Test handling of request timeouts"""

        async def mock_timeout(*args, **kwargs):
            raise asyncio.TimeoutError("Request timed out")

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_timeout

            result = await mock_agent_simulator.fetch_mission("job-123", "tenant-abc")

            assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_agent_simulator):
        """Test handling of invalid JSON in response"""
        invalid_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "NOT VALID JSON {{{"}]},
        }

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = invalid_response

            result = await mock_agent_simulator.fetch_mission("job-123", "tenant-abc")

            # Should handle gracefully
            assert "error" in result or result == {}

    @pytest.mark.asyncio
    async def test_missing_content_field(self, mock_agent_simulator):
        """Test handling of missing content field in response"""
        invalid_response = {"jsonrpc": "2.0", "id": 1, "result": {}}

        with patch.object(mock_agent_simulator, "_make_mcp_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = invalid_response

            result = await mock_agent_simulator.fetch_mission("job-123", "tenant-abc")

            # Should handle gracefully
            assert "error" in result or result == {}


class TestMockAgentSimulatorCrossPlatform:
    """Test cross-platform compatibility"""

    @pytest.mark.asyncio
    async def test_path_handling_uses_pathlib(self):
        """Test that all file operations use pathlib.Path"""
        # Verify class doesn't use hardcoded paths
        import inspect

        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        source = inspect.getsource(MockAgentSimulator)

        # Should not contain hardcoded Windows paths
        assert "F:\\" not in source, "Found hardcoded Windows path"
        assert "C:\\" not in source, "Found hardcoded Windows path"

        # Should not contain hardcoded Unix paths (except in URLs)
        # Allow /mcp in URLs
        lines_without_urls = [line for line in source.split("\n") if "http" not in line.lower()]
        source_without_urls = "\n".join(lines_without_urls)

        # Check for suspicious Unix path patterns (not in comments or URLs)
        import re

        suspicious_paths = re.findall(r'[\'"](/[a-zA-Z]+/[a-zA-Z]+)', source_without_urls)
        # Filter out common URL paths
        suspicious_paths = [p for p in suspicious_paths if not any(x in p for x in ["/api/", "/mcp", "/http"])]

        assert len(suspicious_paths) == 0, f"Found potential hardcoded Unix paths: {suspicious_paths}"

    @pytest.mark.asyncio
    async def test_simulator_initialization(self, mock_api_key, mock_tenant_key, mock_job_id):
        """Test simulator can be initialized on any platform"""
        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        simulator = MockAgentSimulator(
            job_id=mock_job_id,
            tenant_key=mock_tenant_key,
            api_key=mock_api_key,
            api_url="http://localhost:7272/mcp",
            agent_display_name="implementer",
        )

        assert simulator.job_id == mock_job_id
        assert simulator.tenant_key == mock_tenant_key
        assert simulator.api_key == mock_api_key
        assert simulator.agent_display_name == "implementer"

        # Cleanup
        if simulator._session and not simulator._session.closed:
            await simulator._session.close()


class TestMockAgentSimulatorAgentTypes:
    """Test different agent type simulations"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "agent_display_name,expected_duration_min,expected_duration_max",
        [
            ("implementer", 5, 10),
            ("tester", 5, 10),
            ("reviewer", 5, 10),
            ("documenter", 5, 10),
        ],
    )
    async def test_agent_display_name_simulation(
        self,
        agent_display_name,
        expected_duration_min,
        expected_duration_max,
        mock_api_key,
        mock_tenant_key,
        mock_job_id,
    ):
        """Test simulation for different agent types"""
        from tests.fixtures.mock_agent_simulator import MockAgentSimulator

        simulator = MockAgentSimulator(
            job_id=mock_job_id,
            tenant_key=mock_tenant_key,
            api_key=mock_api_key,
            api_url="http://localhost:7272/mcp",
            agent_display_name=agent_display_name,
        )

        assert simulator.agent_display_name == agent_display_name

        # Test work execution timing
        import time

        mission_data = {"mission": f"Test {agent_display_name} work"}

        start_time = time.time()
        await simulator.execute_work(mission_data)
        elapsed_time = time.time() - start_time

        assert expected_duration_min - 1 <= elapsed_time <= expected_duration_max + 2, (
            f"{agent_display_name} work took {elapsed_time:.2f}s"
        )

        # Cleanup
        if simulator._session and not simulator._session.closed:
            await simulator._session.close()
