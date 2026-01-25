"""
Integration tests for MCP HTTP tool catalog (`/mcp` JSON-RPC).

This suite validates that:
- tools/list advertises the same public tool surface the server can execute
- tool schemas are present and minimally JSON-Schema shaped
- a basic tools/call round-trip works (health_check)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


MCP_ENDPOINT = "/mcp"

# Source of truth: api/endpoints/mcp_http.py tool_map keys (Jan 2026)
# NOTE: gil_activate, gil_launch removed (0388) - users perform these via web UI
# NOTE: check_succession_status removed (0461a) - succession is manual-only
EXPECTED_TOOL_NAMES = {
    "acknowledge_job",
    "close_project_and_update_memory",
    "complete_job",
    "create_successor_orchestrator",
    "create_task",
    "fetch_context",
    "file_exists",
    "get_agent_mission",
    "get_orchestrator_instructions",
    "get_pending_jobs",
    "get_workflow_status",
    "gil_handover",
    "health_check",
    "list_messages",
    "orchestrate_project",
    "receive_messages",
    "report_error",
    "report_progress",
    "send_message",
    "spawn_agent_job",
    "update_agent_mission",
    "update_project_mission",
    "write_360_memory",
}


class TestMCPToolDiscovery:
    @pytest.mark.asyncio
    async def test_tools_list_returns_expected_public_tool_set(
        self,
        client: AsyncClient,
        test_api_key: str,
        initialized_session: str,
    ):
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "tools-list"},
            headers={"X-API-Key": test_api_key},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "tools-list"
        assert "result" in data and "tools" in data["result"]

        tools = data["result"]["tools"]
        names = {t["name"] for t in tools}

        assert names == EXPECTED_TOOL_NAMES

    @pytest.mark.asyncio
    async def test_tools_list_schema_shape(self, client: AsyncClient, test_api_key: str):
        response = await client.post(
            MCP_ENDPOINT,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "schema-shape"},
            headers={"X-API-Key": test_api_key},
        )
        assert response.status_code == 200
        tools = response.json()["result"]["tools"]

        for tool in tools:
            assert "name" in tool and isinstance(tool["name"], str) and tool["name"]
            assert "description" in tool and isinstance(tool["description"], str)
            assert "inputSchema" in tool and isinstance(tool["inputSchema"], dict)

            schema = tool["inputSchema"]
            # Minimal JSON schema expectations for MCP tools
            assert schema.get("type") == "object"
            assert "properties" in schema and isinstance(schema["properties"], dict)


class TestMCPToolExecution:
    @pytest.mark.asyncio
    async def test_tools_call_health_check(self, client: AsyncClient, test_api_key: str, initialized_session: str):
        response = await client.post(
            MCP_ENDPOINT,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}},
                "id": "call-health",
            },
            headers={"X-API-Key": test_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "call-health"
        assert "result" in data, data
        assert data["result"]["isError"] is False


# -------------------------
# Fixtures
# -------------------------


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession) -> str:
    """Create a valid API key + user for MCP authentication."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from src.giljo_mcp.api_key_utils import get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey, User
    from src.giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    user = User(
        id=str(uuid4()),
        username="mcp_test_user",
        email="mcp_test@example.com",
        tenant_key=tenant_key,
        password_hash="test_hash",
        is_active=True,
        role="developer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    test_key = "gk_test_mcp_http_integration_key_12345"
    key_hash = hash_api_key(test_key)

    api_key = APIKey(
        id=str(uuid4()),
        tenant_key=tenant_key,
        user_id=user.id,
        name="MCP HTTP Integration Tests",
        key_hash=key_hash,
        key_prefix=get_key_prefix(test_key, length=12).replace("...", ""),
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(api_key)
    await db_session.commit()

    return test_key


@pytest_asyncio.fixture
async def client(db_manager, db_session: AsyncSession):
    """AsyncClient for MCP HTTP endpoint integration tests."""
    from httpx import ASGITransport

    from api.app import app, state
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    async def mock_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = mock_get_db_session

    # Ensure the MCP endpoint has access to a configured ToolAccessor instance
    state.db_manager = db_manager
    app.state.db_manager = db_manager
    state.tenant_manager = state.tenant_manager or TenantManager()
    app.state.tenant_manager = state.tenant_manager
    state.tool_accessor = ToolAccessor(db_manager=db_manager, tenant_manager=state.tenant_manager)
    app.state.tool_accessor = state.tool_accessor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def initialized_session(client: AsyncClient, test_api_key: str) -> str:
    """Initialize MCP protocol session."""
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
    assert response.json()["result"]["protocolVersion"] == "2024-11-05"
    return "initialized"
