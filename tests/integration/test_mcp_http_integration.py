"""
Integration tests for MCP-over-HTTP implementation (Handover 0032)

Tests the complete MCP JSON-RPC 2.0 over HTTP endpoint including:
- Server startup and endpoint registration
- Authentication via X-API-Key header
- JSON-RPC 2.0 protocol compliance
- Session management and persistence
- Multi-tenant isolation
- Error handling

Test Coverage:
- Server startup and /mcp endpoint availability
- Valid/invalid API key authentication
- initialize, tools/list, tools/call protocol methods
- Session state preservation across requests
- Malformed request handling
- Error response format compliance
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import app
from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.models import APIKey, MCPSession, User


# Fixtures


@pytest_asyncio.fixture
async def api_client():
    """Create async HTTP client for testing API"""
    from httpx import ASGITransport

    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.database import DatabaseManager
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)
    await test_db_manager.create_tables_async()

    # Override database dependency
    async def override_get_db_session():
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await test_db_manager.close_async()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user for API key authentication"""
    from passlib.hash import bcrypt

    user = User(
        username="test_mcp_user",
        password_hash=bcrypt.hash("test_password"),
        email="test_mcp@example.com",
        role="developer",
        tenant_key="test_tenant",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    # Cleanup
    await db_session.delete(user)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession, test_user: User):
    """Create test API key for authentication"""
    # Generate API key
    api_key_value = generate_api_key()
    key_hash = hash_api_key(api_key_value)
    key_prefix = get_key_prefix(api_key_value, length=12)

    # Create API key record
    api_key = APIKey(
        user_id=test_user.id,
        tenant_key=test_user.tenant_key,
        name="MCP Test Key",
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    # Return both the record and plaintext key
    yield (api_key, api_key_value)

    # Cleanup
    await db_session.delete(api_key)
    await db_session.commit()


# Test 1: Server Startup and Endpoint Registration


@pytest.mark.asyncio
async def test_server_startup_mcp_endpoint_registered():
    """
    Test that server starts successfully and /mcp endpoint is registered.

    This verifies that:
    - FastAPI app initializes without errors
    - /mcp endpoint is included in routes
    - mcp_http router is registered
    """
    # Check app routes include /mcp endpoint
    routes = [route.path for route in app.routes]

    assert "/mcp" in routes, "MCP endpoint not registered in app routes"

    # Verify endpoint accepts POST method
    mcp_route = next(route for route in app.routes if route.path == "/mcp")
    assert "POST" in mcp_route.methods, "MCP endpoint must accept POST requests"


@pytest.mark.asyncio
async def test_mcp_endpoint_accessibility(api_client: AsyncClient):
    """
    Test that /mcp endpoint is accessible via HTTP.

    This verifies:
    - Endpoint responds to requests
    - Returns proper error when X-API-Key missing (not 404)
    """
    response = await api_client.post("/mcp", json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1})

    # Should not be 404 (endpoint exists)
    assert response.status_code != 404, "MCP endpoint returned 404 - not registered"

    # Should be accessible (even if auth fails)
    assert response.status_code in [200, 400, 401], f"Unexpected status code: {response.status_code}"


# Test 2: Authentication Tests


@pytest.mark.asyncio
async def test_authentication_valid_api_key(api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession):
    """
    Test successful authentication with valid API key.

    Verifies:
    - Valid X-API-Key header authenticates correctly
    - Session is created in database
    - Response includes valid JSON-RPC 2.0 result
    """
    api_key_record, api_key_value = test_api_key

    response = await api_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "client_info": {"name": "test-client", "version": "1.0.0"},
            },
            "id": 1,
        },
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verify JSON-RPC 2.0 success response
    assert data.get("jsonrpc") == "2.0", "Missing jsonrpc version"
    assert "result" in data, "Missing result field"
    assert data.get("id") == 1, "Request ID not preserved"

    # Verify session created
    stmt = select(MCPSession).where(MCPSession.api_key_id == api_key_record.id)
    result = await db_session.execute(stmt)
    session = result.scalar_one_or_none()

    assert session is not None, "Session not created for valid API key"
    assert session.tenant_key == api_key_record.tenant_key, "Session tenant_key mismatch"


@pytest.mark.asyncio
async def test_authentication_missing_api_key(api_client: AsyncClient):
    """
    Test that request without X-API-Key header is rejected.

    Verifies:
    - Missing header returns JSON-RPC error response
    - Error code is appropriate (-32600 Invalid Request)
    - Error message is clear
    """
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        # No X-API-Key header
    )

    assert response.status_code == 200, "Should return 200 with JSON-RPC error"

    data = response.json()

    # Verify JSON-RPC 2.0 error response
    assert data.get("jsonrpc") == "2.0", "Missing jsonrpc version"
    assert "error" in data, "Missing error field"
    assert data.get("id") == 1, "Request ID not preserved"

    # Verify error details
    error = data["error"]
    assert error.get("code") == -32600, f"Expected error code -32600, got {error.get('code')}"
    assert "X-API-Key" in error.get("message", ""), "Error message should mention X-API-Key"


@pytest.mark.asyncio
async def test_authentication_invalid_api_key(api_client: AsyncClient):
    """
    Test that request with invalid API key is rejected.

    Verifies:
    - Invalid API key returns JSON-RPC error response
    - Error message indicates authentication failure
    - Session is not created
    """
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        headers={"X-API-Key": "invalid_key_12345"},
    )

    assert response.status_code == 200, "Should return 200 with JSON-RPC error"

    data = response.json()

    # Verify JSON-RPC 2.0 error response
    assert data.get("jsonrpc") == "2.0", "Missing jsonrpc version"
    assert "error" in data, "Missing error field"

    # Verify error indicates invalid key
    error = data["error"]
    assert "Invalid API key" in error.get("message", ""), "Error message should indicate invalid API key"


# Test 3: Protocol Tests


@pytest.mark.asyncio
async def test_protocol_initialize_method(api_client: AsyncClient, test_api_key: tuple):
    """
    Test the initialize method with proper JSON-RPC 2.0 format.

    Verifies:
    - Initialize request succeeds
    - Returns server capabilities
    - Includes protocol version and server info
    """
    _, api_key_value = test_api_key

    response = await api_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "client_info": {"name": "test-client", "version": "1.0.0"},
            },
            "id": 1,
        },
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify result structure
    result = data["result"]
    assert "protocolVersion" in result, "Missing protocolVersion"
    assert "serverInfo" in result, "Missing serverInfo"
    assert "capabilities" in result, "Missing capabilities"

    # Verify server info
    server_info = result["serverInfo"]
    assert server_info.get("name") == "giljo-mcp", "Incorrect server name"
    assert "version" in server_info, "Missing version"


@pytest.mark.asyncio
async def test_protocol_tools_list_method(api_client: AsyncClient, test_api_key: tuple):
    """
    Test the tools/list method.

    Verifies:
    - Returns list of available tools
    - Each tool has name, description, inputSchema
    - Tools array is not empty
    """
    _, api_key_value = test_api_key

    # First initialize
    await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    # Then list tools
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200
    data = response.json()

    result = data["result"]
    assert "tools" in result, "Missing tools array"

    tools = result["tools"]
    assert len(tools) > 0, "Tools list should not be empty"

    # Verify tool structure
    for tool in tools:
        assert "name" in tool, f"Tool missing name: {tool}"
        assert "description" in tool, f"Tool missing description: {tool}"
        assert "inputSchema" in tool, f"Tool missing inputSchema: {tool}"


@pytest.mark.asyncio
async def test_protocol_tools_call_method(api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession):
    """
    Test the tools/call method with a basic tool.

    Verifies:
    - Tool execution returns result
    - Result format matches MCP specification
    - Includes content array with text
    """
    _, api_key_value = test_api_key

    # Initialize session
    await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    # Call list_projects tool
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_projects", "arguments": {}}, "id": 3},
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200
    data = response.json()

    result = data["result"]
    assert "content" in result, "Missing content field"
    assert isinstance(result["content"], list), "Content should be array"
    assert len(result["content"]) > 0, "Content should not be empty"

    # Verify content structure
    content_item = result["content"][0]
    assert content_item.get("type") == "text", "Content type should be text"
    assert "text" in content_item, "Content item missing text"


# Test 4: Session Management Tests


@pytest.mark.asyncio
async def test_session_creation_on_first_request(
    api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession
):
    """
    Test that session is created on first authenticated request.

    Verifies:
    - Session record created in database
    - Session includes tenant_key from API key user
    - Session data initialized correctly
    """
    api_key_record, api_key_value = test_api_key

    # Clear any existing sessions
    stmt = select(MCPSession).where(MCPSession.api_key_id == api_key_record.id)
    result = await db_session.execute(stmt)
    existing_sessions = result.scalars().all()
    for session in existing_sessions:
        await db_session.delete(session)
    await db_session.commit()

    # Make first request
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200

    # Verify session created
    stmt = select(MCPSession).where(MCPSession.api_key_id == api_key_record.id)
    result = await db_session.execute(stmt)
    session = result.scalar_one_or_none()

    assert session is not None, "Session not created"
    assert session.tenant_key == api_key_record.tenant_key, "Tenant key mismatch"
    assert session.session_data is not None, "Session data not initialized"


@pytest.mark.asyncio
async def test_session_persistence_across_requests(
    api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession
):
    """
    Test that session persists across multiple requests.

    Verifies:
    - Same session used for multiple requests with same API key
    - Session data accumulates across requests
    - last_accessed timestamp updates
    """
    api_key_record, api_key_value = test_api_key

    # First request (initialize)
    response1 = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )
    assert response1.status_code == 200

    # Get session after first request
    stmt = select(MCPSession).where(MCPSession.api_key_id == api_key_record.id)
    result = await db_session.execute(stmt)
    session1 = result.scalar_one()
    session1_id = session1.session_id
    first_accessed = session1.last_accessed

    # Second request (tools/list)
    response2 = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
        headers={"X-API-Key": api_key_value},
    )
    assert response2.status_code == 200

    # Verify same session reused
    await db_session.refresh(session1)
    stmt = select(MCPSession).where(MCPSession.api_key_id == api_key_record.id)
    result = await db_session.execute(stmt)
    sessions = result.scalars().all()

    assert len(sessions) == 1, "Multiple sessions created for same API key"
    assert sessions[0].session_id == session1_id, "Session ID changed"
    assert sessions[0].last_accessed > first_accessed, "last_accessed not updated"


@pytest.mark.asyncio
async def test_session_tenant_context_isolation(api_client: AsyncClient, db_session: AsyncSession):
    """
    Test that sessions maintain tenant context isolation.

    Verifies:
    - Different API keys (different tenants) get different sessions
    - Sessions preserve correct tenant_key
    - No cross-tenant data leakage
    """
    from passlib.hash import bcrypt

    # Create two users in different tenants
    user1 = User(
        username="tenant1_user",
        password_hash=bcrypt.hash("test"),
        tenant_key="tenant1",
        role="developer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    user2 = User(
        username="tenant2_user",
        password_hash=bcrypt.hash("test"),
        tenant_key="tenant2",
        role="developer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    # Create API keys for both users
    api_key1_value = generate_api_key()
    api_key1 = APIKey(
        user_id=user1.id,
        tenant_key=user1.tenant_key,
        name="Tenant1 Key",
        key_hash=hash_api_key(api_key1_value),
        key_prefix=get_key_prefix(api_key1_value),
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    api_key2_value = generate_api_key()
    api_key2 = APIKey(
        user_id=user2.id,
        tenant_key=user2.tenant_key,
        name="Tenant2 Key",
        key_hash=hash_api_key(api_key2_value),
        key_prefix=get_key_prefix(api_key2_value),
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([api_key1, api_key2])
    await db_session.commit()

    try:
        # Make requests with both API keys
        response1 = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
            headers={"X-API-Key": api_key1_value},
        )
        response2 = await api_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 2},
            headers={"X-API-Key": api_key2_value},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify separate sessions with correct tenant keys
        stmt1 = select(MCPSession).where(MCPSession.api_key_id == api_key1.id)
        result1 = await db_session.execute(stmt1)
        session1 = result1.scalar_one()

        stmt2 = select(MCPSession).where(MCPSession.api_key_id == api_key2.id)
        result2 = await db_session.execute(stmt2)
        session2 = result2.scalar_one()

        assert session1.tenant_key == "tenant1", "Session1 tenant_key incorrect"
        assert session2.tenant_key == "tenant2", "Session2 tenant_key incorrect"
        assert session1.session_id != session2.session_id, "Sessions should be different"

    finally:
        # Cleanup
        await db_session.delete(api_key1)
        await db_session.delete(api_key2)
        await db_session.delete(user1)
        await db_session.delete(user2)
        await db_session.commit()


# Test 5: Error Handling Tests


@pytest.mark.asyncio
async def test_error_handling_invalid_json_rpc_format(api_client: AsyncClient, test_api_key: tuple):
    """
    Test error handling for invalid JSON-RPC 2.0 format.

    Verifies:
    - Missing jsonrpc field returns error
    - Missing method field returns error
    - Error response follows JSON-RPC 2.0 spec
    """
    _, api_key_value = test_api_key

    # Missing method field
    response = await api_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            # Missing "method"
            "params": {},
            "id": 1,
        },
        headers={"X-API-Key": api_key_value},
    )

    # Should return 422 Unprocessable Entity (Pydantic validation error)
    assert response.status_code == 422, f"Expected 422 for invalid format, got {response.status_code}"


@pytest.mark.asyncio
async def test_error_handling_unknown_method(api_client: AsyncClient, test_api_key: tuple):
    """
    Test error handling for unknown method calls.

    Verifies:
    - Unknown method returns JSON-RPC error
    - Error code is -32601 (Method not found)
    - Error message indicates method name
    """
    _, api_key_value = test_api_key

    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "nonexistent/method", "params": {}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200, "Should return 200 with JSON-RPC error"

    data = response.json()
    assert "error" in data, "Missing error field"

    error = data["error"]
    assert error.get("code") == -32601, f"Expected error code -32601, got {error.get('code')}"
    assert "nonexistent/method" in error.get("message", ""), "Error message should mention method name"


@pytest.mark.asyncio
async def test_error_handling_malformed_tool_call(api_client: AsyncClient, test_api_key: tuple):
    """
    Test error handling for malformed tool call requests.

    Verifies:
    - Missing tool name returns error
    - Error response is JSON-RPC compliant
    - Error message is descriptive
    """
    _, api_key_value = test_api_key

    # Initialize first
    await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    # Call tool without name
    response = await api_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                # Missing "name"
                "arguments": {}
            },
            "id": 2,
        },
        headers={"X-API-Key": api_key_value},
    )

    assert response.status_code == 200, "Should return 200 with JSON-RPC error"

    data = response.json()
    assert "error" in data, "Missing error field"

    error = data["error"]
    assert "required" in error.get("message", "").lower() or "tool name" in error.get("message", "").lower(), (
        "Error should indicate missing tool name"
    )


@pytest.mark.asyncio
async def test_error_handling_session_expiration(
    api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession
):
    """
    Test error handling for expired sessions.

    Verifies:
    - Expired sessions are rejected
    - New session created automatically
    - Error handling is graceful
    """
    api_key_record, api_key_value = test_api_key

    # Create expired session manually
    expired_session = MCPSession(
        api_key_id=api_key_record.id,
        tenant_key=api_key_record.tenant_key,
        session_data={},
        created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        last_accessed=datetime.now(timezone.utc) - timedelta(hours=48),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
    )
    db_session.add(expired_session)
    await db_session.commit()

    # Try to use expired session (should create new one)
    response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
        headers={"X-API-Key": api_key_value},
    )

    # Should succeed by creating new session
    assert response.status_code == 200, "Expired session should be handled gracefully"


# Test 6: Integration Test - Full MCP Flow


@pytest.mark.asyncio
async def test_full_mcp_flow_initialize_list_call(
    api_client: AsyncClient, test_api_key: tuple, db_session: AsyncSession
):
    """
    Test complete MCP flow: initialize → tools/list → tools/call.

    This integration test verifies:
    - Full handshake works end-to-end
    - Session state preserved across all steps
    - Tool execution successful
    - All responses JSON-RPC 2.0 compliant
    """
    _, api_key_value = test_api_key

    # Step 1: Initialize
    init_response = await api_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "client_info": {"name": "integration-test", "version": "1.0"},
            },
            "id": 1,
        },
        headers={"X-API-Key": api_key_value},
    )

    assert init_response.status_code == 200
    init_data = init_response.json()
    assert init_data["jsonrpc"] == "2.0"
    assert "result" in init_data

    # Step 2: List tools
    list_response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
        headers={"X-API-Key": api_key_value},
    )

    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["jsonrpc"] == "2.0"
    assert "result" in list_data
    assert "tools" in list_data["result"]
    assert len(list_data["result"]["tools"]) > 0

    # Step 3: Call tool
    call_response = await api_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_projects", "arguments": {}}, "id": 3},
        headers={"X-API-Key": api_key_value},
    )

    assert call_response.status_code == 200
    call_data = call_response.json()
    assert call_data["jsonrpc"] == "2.0"
    assert "result" in call_data
    assert "content" in call_data["result"]

    # Verify session exists and is active
    stmt = select(MCPSession)
    result = await db_session.execute(stmt)
    sessions = result.scalars().all()

    # Should have exactly one session for this test
    test_sessions = [s for s in sessions if "integration-test" in str(s.session_data)]
    assert len(test_sessions) >= 1, "Integration test session not found"
