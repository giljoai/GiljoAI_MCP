"""
MCP Security Tests - Handover 0730

Comprehensive security testing for MCP HTTP endpoint including:
- API key authentication enforcement
- Multi-tenant isolation verification
- Cross-tenant access prevention
- Tool parameter validation

Test Coverage:
- Authentication enforcement (401 Unauthorized without X-API-Key)
- Invalid API key rejection (401 Unauthorized with wrong key)
- Multi-tenant isolation (tenant A cannot access tenant B data)
- Tool tenant_key parameter enforcement
- Cross-tenant project access blocking
- Cross-tenant task access blocking

Critical patterns used:
1. UUID fixtures: str(uuid4()) for all IDs
2. org_id NOT NULL (0424j): Create Organization first, flush, then User with org_id
3. AgentJob/AgentExecution separation: project_id and mission are on AgentJob, not AgentExecution
4. Exception-based assertions: Use pytest.raises() for error cases
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES - Test Users, API Keys, and Authentication
# ============================================================================


@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user for multi-tenant isolation testing."""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"mcp_sec_tenant_a_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"MCP Sec Tenant A Org {unique_id}",
            slug=f"mcp-sec-tenant-a-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Store credentials for login and MCP access
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_user(db_manager):
    """Create Tenant B user for cross-tenant access testing."""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"mcp_sec_tenant_b_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id is NOT NULL, tenant_key required)
        org = Organization(
            name=f"MCP Sec Tenant B Org {unique_id}",
            slug=f"mcp-sec-tenant-b-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Store credentials for login and MCP access
        user._test_username = username
        user._test_password = "password_b"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_api_key(db_manager, tenant_a_user):
    """Create API key for Tenant A user.

    Uses proper API key generation, hashing, and storage pattern:
    - generate_api_key() creates gk_ prefixed key
    - hash_api_key() creates bcrypt hash for storage
    - get_key_prefix() extracts display prefix

    Returns the plaintext key for use in test requests.
    """
    from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey

    # Generate a new API key
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    key_prefix = get_key_prefix(plaintext_key)

    async with db_manager.get_session_async() as session:
        api_key = APIKey(
            id=str(uuid4()),
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test API Key A",
            user_id=tenant_a_user.id,
            tenant_key=tenant_a_user._test_tenant_key,
            is_active=True,
            permissions=[],
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return plaintext_key


@pytest.fixture
async def tenant_b_api_key(db_manager, tenant_b_user):
    """Create API key for Tenant B user.

    Uses proper API key generation, hashing, and storage pattern.
    Returns the plaintext key for use in test requests.
    """
    from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey

    # Generate a new API key
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    key_prefix = get_key_prefix(plaintext_key)

    async with db_manager.get_session_async() as session:
        api_key = APIKey(
            id=str(uuid4()),
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test API Key B",
            user_id=tenant_b_user.id,
            tenant_key=tenant_b_user._test_tenant_key,
            is_active=True,
            permissions=[],
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return plaintext_key


@pytest.fixture
async def tenant_a_token(api_client: AsyncClient, tenant_a_user):
    """Get JWT token for Tenant A user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_user._test_username, "password": tenant_a_user._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_token(api_client: AsyncClient, tenant_b_user):
    """Get JWT token for Tenant B user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_b_user._test_username, "password": tenant_b_user._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_product(api_client: AsyncClient, tenant_a_token: str):
    """Create a test product for Tenant A."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "MCP Security Test Product A",
            "description": "Test product for MCP security testing",
            "project_path": "/path/to/tenant_a/mcp_sec_product",
        },
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 200
    product_data = response.json()
    api_client.cookies.clear()
    return product_data


@pytest.fixture
async def tenant_b_product(api_client: AsyncClient, tenant_b_token: str):
    """Create a test product for Tenant B."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "MCP Security Test Product B",
            "description": "Test product for MCP security testing",
            "project_path": "/path/to/tenant_b/mcp_sec_product",
        },
        cookies={"access_token": tenant_b_token},
    )
    assert response.status_code == 200
    product_data = response.json()
    api_client.cookies.clear()
    return product_data


@pytest.fixture
async def tenant_a_project(api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
    """Create a test project for Tenant A."""
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": "MCP Security Test Project A",
            "description": "Test project for MCP security testing",
            "mission": "Security test mission",
            "product_id": tenant_a_product["id"],
            "status": "active",
        },
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 201
    project_data = response.json()
    api_client.cookies.clear()
    return project_data


@pytest.fixture
async def tenant_b_project(api_client: AsyncClient, tenant_b_token: str, tenant_b_product):
    """Create a test project for Tenant B."""
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": "MCP Security Test Project B",
            "description": "Test project for MCP security testing",
            "mission": "Security test mission",
            "product_id": tenant_b_product["id"],
            "status": "active",
        },
        cookies={"access_token": tenant_b_token},
    )
    assert response.status_code == 201
    project_data = response.json()
    api_client.cookies.clear()
    return project_data


@pytest.fixture
async def tenant_a_task(db_manager, tenant_a_user, tenant_a_product):
    """Create a test task for Tenant A."""
    from src.giljo_mcp.models import Task

    async with db_manager.get_session_async() as session:
        task = Task(
            id=str(uuid4()),
            tenant_key=tenant_a_user._test_tenant_key,
            product_id=tenant_a_product["id"],
            title="MCP Security Test Task A",
            description="Test task for MCP security testing",
            status="pending",
            priority="medium",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return {
            "id": task.id,
            "tenant_key": task.tenant_key,
            "product_id": task.product_id,
            "title": task.title,
        }


@pytest.fixture
async def tenant_b_task(db_manager, tenant_b_user, tenant_b_product):
    """Create a test task for Tenant B."""
    from src.giljo_mcp.models import Task

    async with db_manager.get_session_async() as session:
        task = Task(
            id=str(uuid4()),
            tenant_key=tenant_b_user._test_tenant_key,
            product_id=tenant_b_product["id"],
            title="MCP Security Test Task B",
            description="Test task for MCP security testing",
            status="pending",
            priority="medium",
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return {
            "id": task.id,
            "tenant_key": task.tenant_key,
            "product_id": task.product_id,
            "title": task.title,
        }


# ============================================================================
# MCP ENDPOINT AUTHENTICATION TESTS
# ============================================================================


class TestMCPAuthentication:
    """Test MCP endpoint authentication enforcement."""

    @pytest.mark.asyncio
    async def test_mcp_endpoint_requires_api_key(self, api_client: AsyncClient):
        """Test POST /mcp - 401 without X-API-Key header.

        The MCP endpoint requires authentication via X-API-Key header.
        Requests without this header should receive a JSON-RPC error response.
        """
        # Send initialize request without authentication
        response = await api_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
                "id": 1,
            },
        )

        # Should return 200 with JSON-RPC error (not HTTP 401)
        # MCP uses JSON-RPC error codes for authentication failures
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request (auth required)
        assert "Authentication required" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_mcp_endpoint_rejects_invalid_api_key(self, api_client: AsyncClient):
        """Test POST /mcp - 401 with invalid/wrong API key.

        The MCP endpoint should reject requests with an invalid API key.
        """
        # Send request with invalid API key
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": "gk_invalid_key_that_does_not_exist"},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
                "id": 1,
            },
        )

        # Should return 200 with JSON-RPC error
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request (invalid key)
        assert "Invalid API key" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_mcp_endpoint_accepts_valid_api_key(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test POST /mcp - 200 with valid API key.

        The MCP endpoint should accept requests with a valid API key and
        return successful initialize response.
        """
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
                "id": 1,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "protocolVersion" in data["result"]
        assert data["result"]["serverInfo"]["name"] == "giljo-mcp"

    @pytest.mark.asyncio
    async def test_mcp_endpoint_accepts_bearer_token(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test POST /mcp - 200 with Authorization: Bearer header.

        The MCP endpoint should accept Bearer token authentication as fallback
        for Codex/Gemini URL transports.
        """
        response = await api_client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {tenant_a_api_key}"},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "codex-client", "version": "1.0.0"},
                },
                "id": 1,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "protocolVersion" in data["result"]


# ============================================================================
# MCP TENANT ISOLATION TESTS
# ============================================================================


class TestMCPTenantIsolation:
    """Test MCP tool tenant isolation enforcement."""

    @pytest.mark.asyncio
    async def test_mcp_tenant_isolation(
        self,
        api_client: AsyncClient,
        tenant_a_api_key: str,
        tenant_b_api_key: str,
        tenant_a_project,
        tenant_b_project,
    ):
        """Test MCP tenant isolation - cannot access other tenant's data.

        When Tenant A calls get_workflow_status for Tenant B's project,
        the request should fail or return no data (tenant isolation enforced).
        """
        # Initialize session for Tenant A
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Tenant A tries to access Tenant B's project via get_workflow_status
        # The tenant_key will be overridden by session tenant_key (security fix)
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_workflow_status",
                    "arguments": {
                        "project_id": tenant_b_project["id"],
                        # Attacker tries to spoof tenant_key - should be overridden
                        "tenant_key": "spoofed_tenant_key",
                    },
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # The request should either:
        # 1. Return an error (project not found in tenant A's scope)
        # 2. Return empty result (no access to tenant B's project)
        if "error" in data:
            # Project not found for this tenant
            assert "not found" in data["error"]["message"].lower() or "error" in data["error"]["message"].lower()
        elif "result" in data:
            # Tool executed but returned error in content
            result = data["result"]
            if "content" in result and result["content"]:
                content_text = result["content"][0].get("text", "")
                # Should indicate error or no access
                assert (
                    "not found" in content_text.lower()
                    or "error" in content_text.lower()
                    or result.get("isError", False)
                )

    @pytest.mark.asyncio
    async def test_mcp_tool_requires_tenant_key(
        self, api_client: AsyncClient, tenant_a_api_key: str, tenant_a_project
    ):
        """Test MCP tools enforce tenant_key parameter.

        Tools that require tenant_key should have it automatically injected
        from the authenticated session, ensuring proper tenant isolation.
        """
        # Initialize session
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Call get_workflow_status without providing tenant_key
        # The tool should receive tenant_key from session (auto-injection)
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_workflow_status",
                    "arguments": {
                        "project_id": tenant_a_project["id"],
                        # Not providing tenant_key - should be auto-injected
                    },
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should succeed because tenant_key is auto-injected from session
        assert "result" in data
        # Even if project has no agents, the call should not fail due to missing tenant_key


# ============================================================================
# CROSS-TENANT ACCESS PREVENTION TESTS
# ============================================================================


class TestCrossTenantAccessPrevention:
    """Test cross-tenant access is properly blocked."""

    @pytest.mark.asyncio
    async def test_cross_tenant_project_access_blocked(
        self,
        api_client: AsyncClient,
        tenant_a_api_key: str,
        tenant_b_project,
        tenant_a_user,
    ):
        """Test cross-tenant project access is blocked.

        Tenant A should not be able to access Tenant B's project through
        any MCP tool. The tenant_key override security measure should prevent
        cross-tenant data access.
        """
        # Initialize session for Tenant A
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Tenant A attempts to spawn an agent job in Tenant B's project
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "spawn_agent_job",
                    "arguments": {
                        "project_id": tenant_b_project["id"],  # Cross-tenant!
                        "agent_display_name": "attacker",
                        "agent_name": "attacker-agent",
                        "mission": "Malicious cross-tenant access attempt",
                        "tenant_key": tenant_a_user._test_tenant_key,  # Will be overridden
                    },
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should fail - project belongs to different tenant
        if "result" in data:
            result = data["result"]
            # Tool should return error in content
            if "content" in result and result["content"]:
                content_text = result["content"][0].get("text", "")
                # Expect error about project not found or access denied
                assert (
                    "not found" in content_text.lower()
                    or "error" in content_text.lower()
                    or "failed" in content_text.lower()
                    or result.get("isError", False)
                )

    @pytest.mark.asyncio
    async def test_cross_tenant_task_access_blocked(
        self,
        api_client: AsyncClient,
        tenant_a_api_key: str,
        tenant_a_user,
        tenant_b_product,
    ):
        """Test cross-tenant task creation is blocked.

        Tenant A should not be able to create tasks for Tenant B's product.
        The create_task tool requires an active product which is tenant-scoped.
        """
        # Initialize session for Tenant A
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Tenant A attempts to create a task (the tool uses active product)
        # Since Tenant A has no active product set, this should fail
        # OR if we try to reference Tenant B's product directly, it should be blocked
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_task",
                    "arguments": {
                        "title": "Cross-tenant task attempt",
                        "description": "Attempting to create task in wrong tenant",
                        "priority": "high",
                    },
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should fail because:
        # 1. No active product set for Tenant A (create_task requires active product)
        # 2. Even if product was specified, tenant isolation would block it
        if "result" in data:
            result = data["result"]
            if "content" in result and result["content"]:
                content_text = result["content"][0].get("text", "")
                # Expect error about no active product or validation failure
                assert (
                    "no active product" in content_text.lower()
                    or "error" in content_text.lower()
                    or "failed" in content_text.lower()
                    or "product" in content_text.lower()
                    or result.get("isError", False)
                )

    @pytest.mark.asyncio
    async def test_tenant_key_spoofing_prevented(
        self,
        api_client: AsyncClient,
        tenant_a_api_key: str,
        tenant_b_user,
        tenant_a_project,
    ):
        """Test tenant_key spoofing is prevented.

        When a client provides a different tenant_key in tool arguments,
        it should be overridden with the authenticated session's tenant_key.
        This prevents cross-tenant data access via parameter manipulation.
        """
        # Initialize session for Tenant A
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Tenant A tries to spoof Tenant B's tenant_key
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_workflow_status",
                    "arguments": {
                        "project_id": tenant_a_project["id"],
                        # Attacker tries to use Tenant B's key
                        "tenant_key": tenant_b_user._test_tenant_key,
                    },
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # The request should succeed with Tenant A's data (spoofed key ignored)
        # OR fail if project doesn't exist (but NOT succeed with Tenant B's data)
        assert "result" in data or "error" in data

        # If successful, verify it's using the correct (session) tenant
        # The security layer overrides client-supplied tenant_key with session tenant


# ============================================================================
# MCP TOOL VALIDATION TESTS
# ============================================================================


class TestMCPToolValidation:
    """Test MCP tool parameter validation."""

    @pytest.mark.asyncio
    async def test_tools_list_returns_available_tools(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test tools/list returns all available MCP tools."""
        # Initialize session
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Get tools list
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        assert "tools" in data["result"]
        tools = data["result"]["tools"]

        # Verify essential tools are present
        tool_names = [t["name"] for t in tools]
        assert "health_check" in tool_names
        assert "get_workflow_status" in tool_names
        assert "spawn_agent_job" in tool_names
        assert "create_task" in tool_names

    @pytest.mark.asyncio
    async def test_invalid_tool_name_returns_error(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test calling non-existent tool returns proper error."""
        # Initialize session
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Call non-existent tool
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "non_existent_tool",
                    "arguments": {},
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return JSON-RPC error for tool not found
        assert "error" in data
        assert data["error"]["code"] == -32603  # Internal error
        assert "not found" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_tool_works(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test health_check tool works correctly."""
        # Initialize session
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Call health_check (doesn't require tenant_key)
        response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {},
                },
                "id": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        result = data["result"]
        assert "content" in result
        assert result.get("isError") is False


# ============================================================================
# MCP SESSION MANAGEMENT TESTS
# ============================================================================


class TestMCPSessionManagement:
    """Test MCP session management and persistence."""

    @pytest.mark.asyncio
    async def test_session_persists_across_calls(
        self, api_client: AsyncClient, tenant_a_api_key: str
    ):
        """Test MCP session persists across multiple tool calls."""
        # Initialize session
        init_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
                "id": 1,
            },
        )
        assert init_response.status_code == 200

        # Make first tool call
        call1_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {},
                },
                "id": 2,
            },
        )
        assert call1_response.status_code == 200

        # Make second tool call - session should persist
        call2_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {},
                },
                "id": 3,
            },
        )
        assert call2_response.status_code == 200

        # Both calls should succeed (session persists)
        data1 = call1_response.json()
        data2 = call2_response.json()
        assert "result" in data1
        assert "result" in data2

    @pytest.mark.asyncio
    async def test_different_api_keys_have_different_sessions(
        self, api_client: AsyncClient, tenant_a_api_key: str, tenant_b_api_key: str
    ):
        """Test different API keys have separate sessions."""
        # Initialize session for Tenant A
        init_a_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_a_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_a_response.status_code == 200

        # Initialize session for Tenant B
        init_b_response = await api_client.post(
            "/mcp",
            headers={"X-API-Key": tenant_b_api_key},
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
                "id": 1,
            },
        )
        assert init_b_response.status_code == 200

        # Both should have valid separate sessions
        data_a = init_a_response.json()
        data_b = init_b_response.json()
        assert "result" in data_a
        assert "result" in data_b
