"""
Tests for MCP endpoint tool exposure (Handover 0298).

Verifies that only canonical messaging tools are exposed via /mcp endpoint,
and legacy queue-style tools are NOT exposed.

CANONICAL MESSAGING TOOLS (should be exposed):
- send_message
- receive_messages
- acknowledge_message
- list_messages

LEGACY TOOLS (should NOT be exposed):
- send_mcp_message
- read_mcp_messages
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestMCPEndpointToolExposure:
    """Verify MCP endpoint exposes only canonical tools."""

    async def test_mcp_endpoint_requires_authentication(self, api_client: AsyncClient):
        """MCP endpoint should require X-API-Key header."""
        response = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )

        assert response.status_code == 200
        result = response.json()
        assert "error" in result
        assert "Authentication required" in result["error"]["message"]

    async def test_mcp_endpoint_lists_canonical_messaging_tools(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """MCP endpoint should list canonical messaging tools."""
        # Create API key for MCP authentication
        from src.giljo_mcp.models import APIKey
        from passlib.hash import bcrypt
        import jwt

        # Extract tenant_key and user_id from auth_headers cookie
        cookie = auth_headers["Cookie"]
        token = cookie.split("=")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        tenant_key = payload["tenant_key"]
        user_id = payload["sub"]  # JWT uses "sub" for user_id

        # Create API key in database
        test_key = "gk_test_key_12345678901234567890"
        async with api_client._transport.app.state.db_manager.get_session_async() as session:
            api_key = APIKey(
                name="Test MCP Key 1",
                tenant_key=tenant_key,
                user_id=user_id,
                key_hash=bcrypt.hash(test_key),
                key_prefix=test_key[:12],
                permissions=["mcp:read", "mcp:write"],
            )
            session.add(api_key)
            await session.commit()

        # Call MCP tools/list with API key
        response = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"X-API-Key": test_key},
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result
        assert "tools" in result["result"]

        tools = result["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        # Should have canonical messaging tools
        assert "send_message" in tool_names, "send_message should be exposed"
        assert (
            "receive_messages" in tool_names
        ), "receive_messages should be exposed"
        assert (
            "acknowledge_message" in tool_names
        ), "acknowledge_message should be exposed"
        assert "list_messages" in tool_names, "list_messages should be exposed"

    async def test_mcp_endpoint_excludes_legacy_queue_tools(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """MCP endpoint should NOT expose legacy queue tools."""
        # Create API key for MCP authentication
        from src.giljo_mcp.models import APIKey
        from passlib.hash import bcrypt
        import jwt

        # Extract tenant_key and user_id from auth_headers cookie
        cookie = auth_headers["Cookie"]
        token = cookie.split("=")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        tenant_key = payload["tenant_key"]
        user_id = payload["sub"]  # JWT uses "sub" for user_id

        # Create API key in database
        test_key = "gk_test_key_23456789012345678901"
        async with api_client._transport.app.state.db_manager.get_session_async() as session:
            api_key = APIKey(
                name="Test MCP Key 2",
                tenant_key=tenant_key,
                user_id=user_id,
                key_hash=bcrypt.hash(test_key),
                key_prefix=test_key[:12],
                permissions=["mcp:read", "mcp:write"],
            )
            session.add(api_key)
            await session.commit()

        # Call MCP tools/list
        response = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"X-API-Key": test_key},
        )

        assert response.status_code == 200
        result = response.json()
        assert "result" in result
        tools = result["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        # Should NOT have legacy tools
        assert (
            "send_mcp_message" not in tool_names
        ), "send_mcp_message should NOT be exposed (legacy tool)"
        assert (
            "read_mcp_messages" not in tool_names
        ), "read_mcp_messages should NOT be exposed (legacy tool)"

    async def test_mcp_endpoint_canonical_tool_schemas(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Verify canonical messaging tools have correct schemas."""
        # Create API key
        from src.giljo_mcp.models import APIKey
        from passlib.hash import bcrypt
        import jwt

        cookie = auth_headers["Cookie"]
        token = cookie.split("=")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        tenant_key = payload["tenant_key"]
        user_id = payload["sub"]  # JWT uses "sub" for user_id

        test_key = "gk_test_key_34567890123456789012"
        async with api_client._transport.app.state.db_manager.get_session_async() as session:
            api_key = APIKey(
                name="Test MCP Key 3",
                tenant_key=tenant_key,
                user_id=user_id,
                key_hash=bcrypt.hash(test_key),
                key_prefix=test_key[:12],
                permissions=["mcp:read", "mcp:write"],
            )
            session.add(api_key)
            await session.commit()

        # Get tool list
        response = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"X-API-Key": test_key},
        )

        assert response.status_code == 200
        result = response.json()
        tools = result["result"]["tools"]
        tools_by_name = {t["name"]: t for t in tools}

        # Verify send_message schema
        send_msg = tools_by_name.get("send_message")
        assert send_msg is not None, "send_message tool should exist"
        assert "inputSchema" in send_msg
        schema = send_msg["inputSchema"]
        assert "to_agents" in schema["properties"]
        assert "content" in schema["properties"]
        assert "project_id" in schema["properties"]
        assert schema["properties"]["to_agents"]["type"] == "array"

        # Verify receive_messages schema
        receive_msg = tools_by_name.get("receive_messages")
        assert receive_msg is not None, "receive_messages tool should exist"
        assert "inputSchema" in receive_msg
        # receive_messages accepts agent_id (not job_id)
        # This is the canonical contract, not queue-style

        # Verify acknowledge_message schema
        ack_msg = tools_by_name.get("acknowledge_message")
        assert ack_msg is not None, "acknowledge_message tool should exist"
        assert "inputSchema" in ack_msg
        assert "message_id" in ack_msg["inputSchema"]["properties"]

    async def test_mcp_tool_map_excludes_legacy_tools(self):
        """Verify tool_map in mcp_http.py does not include legacy tools."""
        # This is a code inspection test - verifies the tool_map dictionary
        # in api/endpoints/mcp_http.py handle_tools_call() function
        from api.endpoints.mcp_http import handle_tools_call
        import inspect

        # Get the source code of handle_tools_call
        source = inspect.getsource(handle_tools_call)

        # Verify tool_map does not contain legacy tools
        assert (
            '"send_mcp_message"' not in source
        ), "tool_map should not contain send_mcp_message"
        assert (
            '"read_mcp_messages"' not in source
        ), "tool_map should not contain read_mcp_messages"

        # Verify it contains canonical tools
        assert '"send_message"' in source, "tool_map should contain send_message"
        assert (
            '"receive_messages"' in source
        ), "tool_map should contain receive_messages"
        assert (
            '"acknowledge_message"' in source
        ), "tool_map should contain acknowledge_message"
        assert '"list_messages"' in source, "tool_map should contain list_messages"

    async def test_legacy_tools_not_callable_via_mcp(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Attempting to call legacy tools via MCP should fail."""
        # Create API key
        from src.giljo_mcp.models import APIKey
        from passlib.hash import bcrypt
        import jwt

        cookie = auth_headers["Cookie"]
        token = cookie.split("=")[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        tenant_key = payload["tenant_key"]
        user_id = payload["sub"]  # JWT uses "sub" for user_id

        test_key = "gk_test_key_45678901234567890123"
        async with api_client._transport.app.state.db_manager.get_session_async() as session:
            api_key = APIKey(
                name="Test MCP Key 4",
                tenant_key=tenant_key,
                user_id=user_id,
                key_hash=bcrypt.hash(test_key),
                key_prefix=test_key[:12],
                permissions=["mcp:read", "mcp:write"],
            )
            session.add(api_key)
            await session.commit()

        # Attempt to call legacy send_mcp_message tool
        response = await api_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "send_mcp_message",
                    "arguments": {
                        "job_id": "test-job-123",
                        "tenant_key": tenant_key,
                        "content": "Test message",
                        "target": "orchestrator",
                    },
                },
                "id": 2,
            },
            headers={"X-API-Key": test_key},
        )

        # Should fail - tool not found
        assert response.status_code == 200  # JSON-RPC returns 200 even for errors
        result = response.json()

        # MCP endpoint returns JSON-RPC error format when tool not found
        assert "error" in result, "Expected error response for unknown tool"
        assert "not found" in result["error"]["message"].lower()
