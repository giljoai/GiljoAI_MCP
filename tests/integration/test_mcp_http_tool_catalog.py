"""
Integration Tests for MCP HTTP Tool Catalog Fix

Tests the complete MCP HTTP endpoint implementation to verify:
1. Tool Discovery - All 44 tools are exposed in tools/list
2. Tool Execution - Each tool category can be called successfully
3. Schema Validation - All inputSchema definitions are JSON-Schema compliant
4. Error Handling - Invalid parameters return proper error responses
5. Backward Compatibility - Existing tool calls still work
6. Performance - Tool listing has acceptable latency

Author: Backend Integration Tester Agent
Date: 2025-11-03
Related: api/endpoints/mcp_http.py (Tool catalog fix)
"""

import asyncio
import json
import time

import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import AsyncClient as HTTPXAsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Test configuration
MCP_ENDPOINT = "/mcp"
EXPECTED_TOOL_COUNT = 44  # Updated from 30 to 44 based on implementation


class TestMCPToolDiscovery:
    """Test MCP tools/list endpoint - Tool Discovery"""

    @pytest.mark.asyncio
    async def test_tools_list_returns_all_tools(self, client: AsyncClient, test_api_key: str, initialized_session: str):
        """
        Test that tools/list returns all 44 tools.

        This verifies the fix for the tool catalog mismatch where
        previously only 6 tools were advertised but 30 were callable.
        """
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-1"},
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Validate JSON-RPC 2.0 response structure
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert "result" in data
        assert "tools" in data["result"]

        tools = data["result"]["tools"]

        # CRITICAL: Verify all 44 tools are returned
        assert len(tools) == EXPECTED_TOOL_COUNT, (
            f"Expected {EXPECTED_TOOL_COUNT} tools, got {len(tools)}. Tool catalog mismatch detected!"
        )

    @pytest.mark.asyncio
    async def test_all_tool_categories_present(self, client: AsyncClient, test_api_key: str):
        """
        Verify all tool categories are present in the catalog.

        Categories:
        - Project Management (5 tools)
        - Orchestrator (1 tool)
        - Agent Management (5 tools)
        - Message Communication (4 tools)
        - Task Management (5 tools)
        - Template Management (4 tools)
        - Context Discovery (4 tools)
        - Health & Status (1 tool)
        - Agent Coordination (6 tools)
        - Orchestration (4 tools)
        - Succession (2 tools)
        - Slash Commands (4 tools)
        """
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-2"},
            headers={"X-API-Key": test_api_key},
        )

        tools = response.json()["result"]["tools"]
        tool_names = {tool["name"] for tool in tools}

        # Project Management Tools
        assert "create_project" in tool_names
        assert "list_projects" in tool_names
        assert "get_project" in tool_names
        assert "switch_project" in tool_names
        assert "close_project" in tool_names

        # Orchestrator Tools
        assert "get_orchestrator_instructions" in tool_names

        # Agent Management Tools
        assert "spawn_agent" in tool_names
        assert "list_agents" in tool_names
        assert "get_agent_status" in tool_names
        assert "update_agent" in tool_names
        assert "retire_agent" in tool_names

        # Message Communication Tools
        assert "send_message" in tool_names
        assert "receive_messages" in tool_names
        assert "list_messages" in tool_names

        # Task Management Tools
        assert "create_task" in tool_names
        assert "list_tasks" in tool_names
        assert "update_task" in tool_names
        assert "assign_task" in tool_names
        assert "complete_task" in tool_names

        # Template Management Tools
        assert "list_templates" in tool_names
        assert "get_template" in tool_names
        assert "create_template" in tool_names
        assert "update_template" in tool_names

        # Context Discovery Tools
        assert "discover_context" in tool_names
        assert "get_file_context" in tool_names
        assert "search_context" in tool_names
        assert "get_context_summary" in tool_names

        # Health Tools
        assert "health_check" in tool_names

        # Agent Coordination Tools (Handover 0045)
        assert "get_pending_jobs" in tool_names
        assert "acknowledge_job" in tool_names
        assert "report_progress" in tool_names
        assert "get_next_instruction" in tool_names
        assert "complete_job" in tool_names
        assert "report_error" in tool_names

        # Orchestration Tools (Handover 0088)
        assert "orchestrate_project" in tool_names
        assert "get_agent_mission" in tool_names
        assert "spawn_agent_job" in tool_names
        assert "get_workflow_status" in tool_names

        # Succession Tools (Handover 0080)
        assert "create_successor_orchestrator" in tool_names
        assert "check_succession_status" in tool_names

        # Slash Command Tools (Handover 0093, 0084b)
        assert "setup_slash_commands" in tool_names
        assert "gil_import_productagents" in tool_names
        assert "gil_import_personalagents" in tool_names
        assert "gil_handover" in tool_names


class TestToolSchemaValidation:
    """Test JSON-Schema compliance for all tool inputSchema definitions"""

    @pytest.mark.asyncio
    async def test_all_tools_have_valid_schema(self, client: AsyncClient, test_api_key: str):
        """
        Validate that every tool has a valid JSON-Schema compliant inputSchema.

        JSON-Schema requirements:
        - Must have "type": "object"
        - Must have "properties" dict
        - Required fields in "required" array
        - Property types must be valid JSON-Schema types
        """
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-schema"},
            headers={"X-API-Key": test_api_key},
        )

        tools = response.json()["result"]["tools"]

        for tool in tools:
            # Every tool must have these fields
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool['name']} missing 'inputSchema'"

            schema = tool["inputSchema"]

            # Validate JSON-Schema structure
            assert schema.get("type") == "object", (
                f"Tool {tool['name']} inputSchema must be type 'object', got {schema.get('type')}"
            )

            assert "properties" in schema, f"Tool {tool['name']} inputSchema missing 'properties'"

            # Validate properties structure
            for prop_name, prop_def in schema["properties"].items():
                assert "type" in prop_def or "enum" in prop_def, (
                    f"Tool {tool['name']}, property {prop_name} missing 'type' or 'enum'"
                )

                # Validate property type is valid JSON-Schema type
                if "type" in prop_def:
                    valid_types = ["string", "integer", "number", "boolean", "array", "object", "null"]
                    assert prop_def["type"] in valid_types, (
                        f"Tool {tool['name']}, property {prop_name} has invalid type: {prop_def['type']}"
                    )

            # Validate required array (if present) references existing properties
            if "required" in schema:
                for required_field in schema["required"]:
                    assert required_field in schema["properties"], (
                        f"Tool {tool['name']} requires field '{required_field}' not in properties"
                    )

    @pytest.mark.asyncio
    async def test_enum_properties_have_valid_values(self, client: AsyncClient, test_api_key: str):
        """
        Validate that enum properties have valid enum arrays.

        Tests tools with enum constraints like:
        - send_message (priority: low/medium/high/critical)
        - create_successor_orchestrator (reason: context_limit/manual/phase_transition)
        """
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-enums"},
            headers={"X-API-Key": test_api_key},
        )

        tools = response.json()["result"]["tools"]

        # Check specific tools with known enum constraints
        tool_map = {tool["name"]: tool for tool in tools}

        # send_message: priority enum
        send_message = tool_map["send_message"]
        priority_prop = send_message["inputSchema"]["properties"]["priority"]
        assert "enum" in priority_prop
        assert set(priority_prop["enum"]) == {"low", "medium", "high", "critical"}

        # create_successor_orchestrator: reason enum
        succession_tool = tool_map["create_successor_orchestrator"]
        reason_prop = succession_tool["inputSchema"]["properties"]["reason"]
        assert "enum" in reason_prop
        assert set(reason_prop["enum"]) == {"context_limit", "manual", "phase_transition"}


class TestToolExecution:
    """Test tool execution for each category"""

    @pytest.mark.asyncio
    async def test_health_check_tool(self, client: AsyncClient, test_api_key: str):
        """Test health_check tool execution (simplest tool, no params)"""
        response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}},
                "id": "test-health",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert data["result"]["isError"] is False
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0
        assert data["result"]["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_project_management_tools(self, client: AsyncClient, test_api_key: str, tenant_key: str):
        """Test project management category: create_project, list_projects"""

        # Test create_project
        create_response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_project",
                    "arguments": {
                        "name": "MCP Test Project",
                        "mission": "Integration test for MCP HTTP tools",
                        "agents": ["implementer", "tester"],
                    },
                },
                "id": "test-create-project",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        assert create_data["result"]["isError"] is False

        # Extract project_id from response
        result_text = create_data["result"]["content"][0]["text"]
        result_json = json.loads(result_text)
        project_id = result_json.get("id") or result_json.get("project_id")

        # Test list_projects
        list_response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "list_projects", "arguments": {}},
                "id": "test-list-projects",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_template_management_tools(self, client: AsyncClient, test_api_key: str):
        """Test template management category: list_templates, get_template"""

        # Test list_templates
        list_response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "list_templates", "arguments": {}},
                "id": "test-list-templates",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["result"]["isError"] is False

        # Parse response to get first template name
        result_text = list_data["result"]["content"][0]["text"]
        result_json = json.loads(result_text)

        # If templates exist, test get_template
        if result_json and len(result_json) > 0:
            template_name = result_json[0].get("name") or result_json[0].get("template_name")

            get_response = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "get_template", "arguments": {"template_name": template_name}},
                    "id": "test-get-template",
                },
                headers={"X-API-Key": test_api_key},
            )

            assert get_response.status_code == 200
            get_data = get_response.json()
            assert get_data["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_task_management_tools(self, client: AsyncClient, test_api_key: str):
        """Test task management category: create_task, list_tasks"""

        # Test create_task
        create_response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_task",
                    "arguments": {
                        "title": "MCP Integration Test Task",
                        "description": "Verify task management tools work via MCP",
                        "priority": "medium",
                    },
                },
                "id": "test-create-task",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        assert create_data["result"]["isError"] is False

        # Test list_tasks
        list_response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "list_tasks", "arguments": {}},
                "id": "test-list-tasks",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["result"]["isError"] is False


class TestErrorHandling:
    """Test error handling for invalid parameters and edge cases"""

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, client: AsyncClient, test_api_key: str):
        """Test tool call fails gracefully when required parameter is missing"""

        # create_project requires 'name' and 'mission'
        response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_project",
                    "arguments": {
                        "name": "Test Project"
                        # Missing required 'mission' parameter
                    },
                },
                "id": "test-error-missing-param",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return error in MCP format (not HTTP error)
        assert "result" in data
        assert data["result"]["isError"] is True
        assert "content" in data["result"]
        error_text = data["result"]["content"][0]["text"]
        assert "error" in error_text.lower() or "missing" in error_text.lower()

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, client: AsyncClient, test_api_key: str):
        """Test calling non-existent tool returns 404 error"""

        response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
                "id": "test-error-invalid-tool",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return JSON-RPC error
        assert "error" in data
        assert data["error"]["code"] == -32603
        assert "not found" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_enum_value(self, client: AsyncClient, test_api_key: str):
        """Test tool call with invalid enum value fails gracefully"""

        response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "send_message",
                    "arguments": {
                        "to_agent": "test-agent-123",
                        "message": "Test message",
                        "priority": "ultra_mega_critical",  # Invalid enum value
                    },
                },
                "id": "test-error-invalid-enum",
            },
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return error (validation or execution error)
        assert data["result"]["isError"] is True

    @pytest.mark.asyncio
    async def test_missing_authentication(self, client: AsyncClient):
        """Test request without API key returns authentication error"""

        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-no-auth"},
            # No X-API-Key header
        )

        assert response.status_code == 200
        data = response.json()

        # Should return JSON-RPC authentication error
        assert "error" in data
        assert data["error"]["code"] == -32600
        assert "authentication" in data["error"]["message"].lower()


class TestBackwardCompatibility:
    """Test that existing tool calls still work after catalog expansion"""

    @pytest.mark.asyncio
    async def test_legacy_tool_calls_still_work(self, client: AsyncClient, test_api_key: str):
        """
        Verify that tools that were already exposed still work.

        Tests the original 6 tools that were advertised before the fix.
        """
        # Original tools that were exposed
        legacy_tools = [
            ("health_check", {}),
            ("list_projects", {}),
            ("list_templates", {}),
            ("list_tasks", {}),
        ]

        for tool_name, arguments in legacy_tools:
            response = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                    "id": f"test-legacy-{tool_name}",
                },
                headers={"X-API-Key": test_api_key},
            )

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            # Tool should execute (may succeed or fail, but should not crash)
            assert "content" in data["result"]

    @pytest.mark.asyncio
    async def test_tool_map_matches_advertised_tools(self, client: AsyncClient, test_api_key: str):
        """
        CRITICAL: Verify that every tool in tools/list is actually callable.

        This prevents the original bug where tools were advertised but not executable.
        """
        # Get advertised tools
        list_response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-advertised-tools"},
            headers={"X-API-Key": test_api_key},
        )

        tools = list_response.json()["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]

        # Attempt to call each tool (with empty args, may fail, but should be recognized)
        for tool_name in tool_names:
            response = await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": {}},
                    "id": f"test-callable-{tool_name}",
                },
                headers={"X-API-Key": test_api_key},
            )

            assert response.status_code == 200
            data = response.json()

            # Should NOT return "tool not found" error
            if "error" in data:
                assert "not found" not in data["error"]["message"].lower(), (
                    f"Tool {tool_name} advertised in tools/list but not found in tool_map!"
                )


class TestPerformance:
    """Test performance characteristics of tool listing and execution"""

    @pytest.mark.asyncio
    async def test_tools_list_latency(self, client: AsyncClient, test_api_key: str):
        """
        Test that tools/list has acceptable latency (<500ms).

        Tool listing should be fast as MCP clients may call it frequently.
        """
        start_time = time.time()

        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-perf-list"},
            headers={"X-API-Key": test_api_key},
        )

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        assert response.status_code == 200
        assert latency_ms < 500, f"tools/list took {latency_ms:.2f}ms (expected <500ms)"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, client: AsyncClient, test_api_key: str):
        """
        Test that multiple concurrent tool calls are handled correctly.

        Verifies session isolation and concurrent request handling.
        """

        async def call_health_check(call_id: int):
            return await client.post(
                MCP_ENDPOINT,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "health_check", "arguments": {}},
                    "id": f"test-concurrent-{call_id}",
                },
                headers={"X-API-Key": test_api_key},
            )

        # Execute 10 concurrent health checks
        tasks = [call_health_check(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed"
            data = response.json()
            assert data["result"]["isError"] is False, f"Request {i} returned error"


# Pytest Fixtures


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession) -> str:
    """
    Create a test API key for authentication.

    Returns the API key string for use in X-API-Key headers.
    """
    from datetime import datetime, timezone
    from uuid import uuid4

    import bcrypt

    from src.giljo_mcp.models import APIKey, User

    # Create test user first (API keys require a user_id)
    user = User(
        id=str(uuid4()),
        username="mcp_test_user",
        email="mcp_test@example.com",
        tenant_key="test-tenant-mcp",
        password_hash="test_hash",
        is_active=True,
        role="developer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    # Create test API key with proper hashing
    test_key = "gk_test_mcp_http_integration_key_12345"
    key_hash = bcrypt.hashpw(test_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    api_key = APIKey(
        id=str(uuid4()),
        tenant_key="test-tenant-mcp",
        user_id=user.id,
        name="MCP HTTP Integration Tests",
        key_hash=key_hash,
        key_prefix=test_key[:12],  # gk_test_mcp_
        permissions=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(api_key)
    await db_session.commit()

    yield test_key

    # Cleanup (handled by transaction rollback in db_session fixture)


@pytest_asyncio.fixture
async def client(db_manager):
    """
    Create AsyncClient for MCP HTTP endpoint testing.

    Uses the api_client fixture from tests/api/conftest.py but with
    specific configuration for MCP testing.
    """
    from httpx import ASGITransport
    from httpx import AsyncClient as HTTPXAsyncClient

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    async def mock_get_db_session():
        """Provide test database session."""
        async with db_manager.get_session_async() as session:
            yield session

    # Override database session dependency
    app.dependency_overrides[get_db_session] = mock_get_db_session

    # Create async client with ASGI transport
    transport = ASGITransport(app=app)
    async with HTTPXAsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def initialized_session(client: HTTPXAsyncClient, test_api_key: str) -> str:
    """
    Initialize an MCP session for testing.

    Returns the session ID.
    """
    response = await client.post(
        MCP_ENDPOINT,
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "client_info": {"name": "mcp-test-client", "version": "1.0.0"},
                "protocolVersion": "2024-11-05",
                "capabilities": {},
            },
            "id": "init-session",
        },
        headers={"X-API-Key": test_api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"]["protocolVersion"] == "2024-11-05"

    return "initialized"


@pytest.fixture
def tenant_key() -> str:
    """Return test tenant key"""
    return "test-tenant-mcp"
