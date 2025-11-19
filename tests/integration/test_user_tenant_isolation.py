"""
TDD: Per-user tenant isolation for registered users

Behavioral tests ensure that:
- Creating first admin yields a tenant_key (existing behavior)
- Registering a new user as admin always assigns a unique tenant_key per user
- The provided tenant_key in the request is ignored (forward policy change)

We avoid testing implementation details; we assert observable API behavior.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from unittest.mock import MagicMock, AsyncMock

from api.app import app
from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.auth_manager import AuthManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client with proper database setup."""
    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean all test data before each test
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency to use test database
    async def override_get_db_session():
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Initialize app.state with required objects
    app.state.db_manager = test_db_manager

    # Create auth manager for test
    auth_manager = AuthManager(test_db_manager)
    app.state.auth = auth_manager

    # Create client with testserver host
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver:8000") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    await test_db_manager.close_async()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires app lifespan initialization - needs test infrastructure update for auth middleware closure")
async def test_register_user_assigns_unique_tenant_per_user(test_client: AsyncClient):
    # 1) Create first admin (fresh install path)
    admin_payload = {
        "username": "admin_user",
        "password": "AdminPassw0rd!#",
        "email": "admin@example.com",
        "full_name": "Admin",
        "role": "admin",
    }
    resp_admin = await test_client.post("/api/auth/create-first-admin", json=admin_payload)
    assert resp_admin.status_code in (200, 201), f"Failed to create admin: {resp_admin.text}"
    admin_data = resp_admin.json()
    assert "tenant_key" in admin_data
    admin_tenant = admin_data["tenant_key"]
    assert isinstance(admin_tenant, str) and admin_tenant.startswith("tk_")

    # Login as admin to get auth cookie for registration
    login_resp = await test_client.post(
        "/api/auth/login",
        json={"username": "admin_user", "password": "AdminPassw0rd!#"}
    )
    assert login_resp.status_code == 200

    # 2) Register user A (request tenant_key should be ignored)
    user_a_req = {
        "username": "user_a",
        "password": "UserPassw0rd!#",
        "email": "user_a@example.com",
        "full_name": "User A",
        "role": "developer",
        "tenant_key": admin_tenant,  # should be ignored under per-user tenancy policy
    }
    resp_a = await test_client.post("/api/auth/register", json=user_a_req)
    assert resp_a.status_code == 201, f"Failed to register user A: {resp_a.text}"
    user_a = resp_a.json()
    assert user_a["tenant_key"].startswith("tk_")
    assert user_a["tenant_key"] != admin_tenant

    # 3) Register user B and ensure different tenant from user A
    user_b_req = {
        "username": "user_b",
        "password": "UserPassw0rd!#",
        "email": "user_b@example.com",
        "full_name": "User B",
        "role": "developer",
        "tenant_key": admin_tenant,  # ignored
    }
    resp_b = await test_client.post("/api/auth/register", json=user_b_req)
    assert resp_b.status_code == 201, f"Failed to register user B: {resp_b.text}"
    user_b = resp_b.json()
    assert user_b["tenant_key"].startswith("tk_")
    assert user_b["tenant_key"] != user_a["tenant_key"]
