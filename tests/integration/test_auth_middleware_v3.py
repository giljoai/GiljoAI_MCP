"""
Integration tests for AuthMiddleware v3 (Mode-Independent Authentication)

Tests the updated AuthMiddleware that:
- ALWAYS invokes authentication (no mode checks)
- Auto-logs in localhost requests as "localhost" user
- Requires credentials for network requests
- Returns 401 for unauthenticated network requests
- Allows public endpoints without authentication

This is part of Phase 1 Step 3: Updating middleware to remove mode-based logic.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware import AuthMiddleware
from src.giljo_mcp.auth.localhost_user import ensure_localhost_user, get_localhost_user
from src.giljo_mcp.models import User


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with API key for testing"""
    from src.giljo_mcp.auth_legacy import AuthManager

    user = User(
        username="test_network_user",
        email="test@example.com",
        password_hash="$2b$12$test_hash",  # Dummy hash
        role="user",
        is_active=True,
        tenant_key="test_tenant",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Generate an API key for this user using AuthManager
    auth_manager = AuthManager(db=db_session)
    api_key = auth_manager.generate_api_key(name="test_network_user")

    # Store the API key on the user object for test access
    user.api_key = api_key

    return user


@pytest_asyncio.fixture
async def localhost_user(db_session: AsyncSession) -> User:
    """Ensure localhost user exists"""
    return await ensure_localhost_user(db_session)


@pytest_asyncio.fixture
async def app_with_auth_middleware(db_session: AsyncSession) -> FastAPI:
    """Create test app with auth middleware"""
    app = FastAPI()

    # Add auth middleware with database session
    app.add_middleware(AuthMiddleware, db=db_session)

    @app.get("/test")
    async def test_endpoint(request: Request):
        """Test endpoint that returns authentication state"""
        return {
            "authenticated": getattr(request.state, "authenticated", False),
            "user": getattr(request.state, "user_id", None),
            "is_auto_login": getattr(request.state, "is_auto_login", False),
            "tenant_key": getattr(request.state, "tenant_key", None),
        }

    @app.get("/health")
    async def health_endpoint():
        """Public health endpoint"""
        return {"status": "ok"}

    @app.get("/docs")
    async def docs_endpoint():
        """Public docs endpoint"""
        return {"docs": "openapi"}

    return app


def test_middleware_localhost_auto_login(
    app_with_auth_middleware: FastAPI,
    localhost_user: User
):
    """Test middleware auto-authenticates localhost requests (127.0.0.1)"""
    client = TestClient(app_with_auth_middleware)

    # Simulate request from localhost (IPv4)
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"] == "localhost"
    assert data["is_auto_login"] is True
    assert data["tenant_key"] == "default"


def test_middleware_localhost_ipv6_auto_login(
    app_with_auth_middleware: FastAPI,
    localhost_user: User
):
    """Test middleware auto-authenticates localhost requests (::1)"""
    client = TestClient(app_with_auth_middleware)

    # Simulate request from localhost (IPv6)
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "::1",
            "X-Real-IP": "::1"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"] == "localhost"
    assert data["is_auto_login"] is True


def test_middleware_network_requires_auth(app_with_auth_middleware: FastAPI):
    """Test middleware requires auth for network requests"""
    client = TestClient(app_with_auth_middleware)

    # Simulate request from network without credentials
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100"
        }
    )

    # Should return 401 Unauthorized
    assert response.status_code == 401
    assert "error" in response.json()
    assert "Authentication required" in response.json()["error"]


def test_middleware_network_with_api_key(
    app_with_auth_middleware: FastAPI,
    test_user: User
):
    """Test middleware accepts valid API key from network"""
    client = TestClient(app_with_auth_middleware)

    # Request from network WITH valid API key
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100",
            "X-API-Key": test_user.api_key
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"] == test_user.username
    assert data["is_auto_login"] is False
    assert data["tenant_key"] == test_user.tenant_key


def test_middleware_network_with_bearer_token(
    app_with_auth_middleware: FastAPI,
    test_user: User
):
    """Test middleware accepts valid Bearer token from network"""
    client = TestClient(app_with_auth_middleware)

    # Request from network WITH Bearer token (same as API key)
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100",
            "Authorization": f"Bearer {test_user.api_key}"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"] == test_user.username
    assert data["is_auto_login"] is False


def test_middleware_network_with_invalid_api_key(app_with_auth_middleware: FastAPI):
    """Test middleware rejects invalid API key"""
    client = TestClient(app_with_auth_middleware)

    # Request from network with INVALID API key
    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100",
            "X-API-Key": "invalid_key_12345"
        }
    )

    assert response.status_code == 401
    assert "error" in response.json()


def test_middleware_public_health_endpoint(app_with_auth_middleware: FastAPI):
    """Test public health endpoint accessible without auth"""
    client = TestClient(app_with_auth_middleware)

    # Request health endpoint without credentials
    response = client.get(
        "/health",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100"
        }
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_middleware_public_docs_endpoint(app_with_auth_middleware: FastAPI):
    """Test public docs endpoint accessible without auth"""
    client = TestClient(app_with_auth_middleware)

    # Request docs endpoint without credentials
    response = client.get(
        "/docs",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-Real-IP": "192.168.1.100"
        }
    )

    assert response.status_code == 200
    assert "docs" in response.json()


def test_middleware_always_invokes_auth():
    """Test middleware no longer checks is_enabled()"""
    # This test verifies implementation - ensures mode check is removed
    import inspect

    source = inspect.getsource(AuthMiddleware.dispatch)

    # Verify is_enabled() is NOT called
    assert "is_enabled" not in source, "Middleware still checks is_enabled()"
    assert "DeploymentMode" not in source, "Middleware still references DeploymentMode"

    # Verify authentication is ALWAYS invoked
    assert "authenticate_request" in source, "Middleware must call authenticate_request"


def test_middleware_no_mode_checks_in_source():
    """Verify no deployment mode checks exist in middleware source"""
    import inspect

    source = inspect.getsource(AuthMiddleware)

    # Check for mode-related imports or usage
    forbidden_patterns = [
        "DeploymentMode",
        ".mode",
        "is_enabled",
        "deployment_mode",
        "config.mode",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in source, f"Middleware contains forbidden pattern: {pattern}"


@pytest.mark.parametrize("client_ip,expected_auth", [
    ("127.0.0.1", True),     # localhost IPv4
    ("::1", True),            # localhost IPv6
    ("192.168.1.1", False),   # private network
    ("10.0.0.1", False),      # private network
    ("8.8.8.8", False),       # public internet
])
def test_middleware_ip_based_auto_login(
    app_with_auth_middleware: FastAPI,
    localhost_user: User,
    client_ip: str,
    expected_auth: bool
):
    """Test middleware auto-login based on client IP"""
    client = TestClient(app_with_auth_middleware)

    response = client.get(
        "/test",
        headers={
            "X-Forwarded-For": client_ip,
            "X-Real-IP": client_ip
        }
    )

    if expected_auth:
        # Localhost should be auto-authenticated
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["is_auto_login"] is True
    else:
        # Network clients without credentials should get 401
        assert response.status_code == 401


def test_middleware_request_state_population(
    app_with_auth_middleware: FastAPI,
    localhost_user: User
):
    """Test middleware properly populates request.state"""
    client = TestClient(app_with_auth_middleware)

    # Test localhost request
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "127.0.0.1"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all expected state fields are populated
    assert "authenticated" in data
    assert "user" in data
    assert "is_auto_login" in data
    assert "tenant_key" in data

    # Verify values are correct for localhost
    assert data["authenticated"] is True
    assert data["user"] == "localhost"
    assert data["is_auto_login"] is True
    assert data["tenant_key"] == "default"


def test_middleware_missing_forwarded_headers(app_with_auth_middleware: FastAPI):
    """Test middleware handles missing X-Forwarded-For headers"""
    client = TestClient(app_with_auth_middleware)

    # Request without X-Forwarded-For should use client.host
    # TestClient defaults to testclient as host, which is not localhost
    response = client.get("/test")

    # Should require authentication since not localhost
    assert response.status_code == 401


def test_middleware_empty_forwarded_header(app_with_auth_middleware: FastAPI):
    """Test middleware handles empty X-Forwarded-For header"""
    client = TestClient(app_with_auth_middleware)

    # Request with empty X-Forwarded-For
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": ""}
    )

    # Should require authentication
    assert response.status_code == 401


@pytest.mark.parametrize("public_path", [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/setup/status",
    "/api/auth/login",
])
def test_middleware_public_paths(
    app_with_auth_middleware: FastAPI,
    public_path: str
):
    """Test all public paths are accessible without auth"""
    # Add these endpoints to the test app for completeness
    app = app_with_auth_middleware

    @app.get(public_path)
    async def public_endpoint():
        return {"status": "public"}

    client = TestClient(app)

    # Request from network without credentials
    response = client.get(
        public_path,
        headers={"X-Forwarded-For": "192.168.1.100"}
    )

    # Public paths should be accessible
    assert response.status_code == 200


def test_middleware_authenticated_user_object(
    app_with_auth_middleware: FastAPI,
    test_user: User
):
    """Test middleware stores user object in request.state"""
    client = TestClient(app_with_auth_middleware)

    # Add endpoint that checks for user object
    @app_with_auth_middleware.get("/test-user-obj")
    async def test_user_obj(request: Request):
        return {
            "has_user": hasattr(request.state, "user"),
            "user_id": getattr(request.state, "user_id", None),
        }

    response = client.get(
        "/test-user-obj",
        headers={
            "X-Forwarded-For": "192.168.1.100",
            "X-API-Key": test_user.api_key
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_user"] is True
    assert data["user_id"] == test_user.username


def test_middleware_error_message_clarity(app_with_auth_middleware: FastAPI):
    """Test middleware returns clear error messages"""
    client = TestClient(app_with_auth_middleware)

    # Request from network without credentials
    response = client.get(
        "/test",
        headers={"X-Forwarded-For": "192.168.1.100"}
    )

    assert response.status_code == 401
    error_data = response.json()

    # Verify error message is clear and helpful
    assert "error" in error_data
    assert "detail" in error_data
    assert "Authentication required" in error_data["error"]
    assert len(error_data["detail"]) > 0  # Has meaningful detail


def test_middleware_concurrent_requests(
    app_with_auth_middleware: FastAPI,
    localhost_user: User,
    test_user: User
):
    """Test middleware handles concurrent requests correctly"""
    import threading

    client = TestClient(app_with_auth_middleware)
    results = []

    def make_localhost_request():
        response = client.get(
            "/test",
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        results.append(("localhost", response.status_code, response.json()))

    def make_network_request():
        response = client.get(
            "/test",
            headers={
                "X-Forwarded-For": "192.168.1.100",
                "X-API-Key": test_user.api_key
            }
        )
        results.append(("network", response.status_code, response.json()))

    # Run concurrent requests
    threads = [
        threading.Thread(target=make_localhost_request),
        threading.Thread(target=make_network_request),
        threading.Thread(target=make_localhost_request),
        threading.Thread(target=make_network_request),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all requests succeeded
    assert len(results) == 4

    localhost_results = [r for r in results if r[0] == "localhost"]
    network_results = [r for r in results if r[0] == "network"]

    # All localhost requests should succeed with auto-login
    for _, status, data in localhost_results:
        assert status == 200
        assert data["authenticated"] is True
        assert data["is_auto_login"] is True

    # All network requests with valid key should succeed
    for _, status, data in network_results:
        assert status == 200
        assert data["authenticated"] is True
        assert data["is_auto_login"] is False
