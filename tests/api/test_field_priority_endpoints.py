"""
Integration tests for field priority configuration endpoints.

Tests cover:
- GET /api/v1/users/me/field-priority (retrieve user config or defaults)
- PUT /api/v1/users/me/field-priority (update user config)
- POST /api/v1/users/me/field-priority/reset (reset to defaults)

Test scenarios:
- Happy path (successful operations)
- Authentication enforcement
- Validation (field paths, priority values, token budget)
- Error handling (400, 401, 403)
- Multi-tenant isolation
- Config persistence
- Default fallback behavior

Handover: 0048 - Product Field Priority Configuration
"""

import pytest
from httpx import AsyncClient
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
from src.giljo_mcp.models import User


# Fixtures


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user for testing."""
    from uuid import uuid4
    unique_suffix = uuid4().hex[:8]
    user = User(
        username=f"test_user_{unique_suffix}",
        password_hash=bcrypt.hash("test_password"),
        email=f"user_{unique_suffix}@test.com",
        role="developer",
        tenant_key=f"test_tenant_{unique_suffix}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_with_custom_config(db_session: AsyncSession):
    """Create test user with custom field priority config."""
    custom_config = {
        "version": "1.0",
        "token_budget": 2000,
        "fields": {
            "tech_stack.languages": 1,
            "tech_stack.backend": 2,
            "tech_stack.database": 3,
        },
    }

    user = User(
        username="custom_user",
        password_hash=bcrypt.hash("test_password"),
        email="custom@test.com",
        role="developer",
        tenant_key="test_tenant_1",
        is_active=True,
        field_priority_config=custom_config,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def second_tenant_user(db_session: AsyncSession):
    """Create test user in different tenant."""
    user = User(
        username="tenant2_user",
        password_hash=bcrypt.hash("test_password"),
        email="tenant2@test.com",
        role="developer",
        tenant_key="test_tenant_2",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_token(api_client: AsyncClient, test_user):
    """Get JWT token for test user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "test_user", "password": "test_password"},
    )
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
async def custom_user_token(api_client: AsyncClient, test_user_with_custom_config):
    """Get JWT token for user with custom config."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "custom_user", "password": "test_password"},
    )
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
async def second_tenant_token(api_client: AsyncClient, second_tenant_user):
    """Get JWT token for second tenant user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "tenant2_user", "password": "test_password"},
    )
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


# GET Tests - Retrieve Field Priority Config


@pytest.mark.asyncio
async def test_get_default_field_priority(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test GET endpoint returns default config when user has no custom config."""
    response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Assert response structure
    assert "fields" in data
    assert "token_budget" in data
    assert "version" in data

    # Assert default values match DEFAULT_FIELD_PRIORITY
    assert data["version"] == DEFAULT_FIELD_PRIORITY["version"]
    assert data["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data["fields"] == DEFAULT_FIELD_PRIORITY["fields"]


@pytest.mark.asyncio
async def test_get_custom_field_priority(
    api_client: AsyncClient,
    custom_user_token: str,
    test_user_with_custom_config: User,
    db_session: AsyncSession,
):
    """Test GET endpoint returns custom config when user has one."""
    response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": custom_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Assert custom config returned (not defaults)
    expected_config = test_user_with_custom_config.field_priority_config
    assert data["version"] == expected_config["version"]
    assert data["token_budget"] == expected_config["token_budget"]
    assert data["fields"] == expected_config["fields"]

    # Verify it's NOT the default config
    assert data["token_budget"] != DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data["fields"] != DEFAULT_FIELD_PRIORITY["fields"]


# PUT Tests - Update Field Priority Config


@pytest.mark.asyncio
async def test_update_field_priority(
    api_client: AsyncClient,
    user_token: str,
    test_user: User,
    db_session: AsyncSession,
):
    """Test PUT endpoint successfully updates field priority config."""
    custom_config = {
        "version": "1.0",
        "token_budget": 2500,
        "fields": {
            "tech_stack.languages": 1,
            "tech_stack.backend": 1,
            "tech_stack.frontend": 2,
            "tech_stack.database": 2,
            "architecture.pattern": 1,
        },
    }

    # Update config
    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=custom_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Assert response matches request
    assert data["version"] == custom_config["version"]
    assert data["token_budget"] == custom_config["token_budget"]
    assert data["fields"] == custom_config["fields"]

    # Verify persistence in database
    await db_session.refresh(test_user)
    assert test_user.field_priority_config is not None
    assert test_user.field_priority_config["token_budget"] == 2500
    assert test_user.field_priority_config["fields"] == custom_config["fields"]

    # Verify GET returns the updated config
    get_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["token_budget"] == 2500
    assert get_data["fields"] == custom_config["fields"]


@pytest.mark.asyncio
async def test_update_invalid_field(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT endpoint rejects invalid field paths."""
    invalid_config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {
            "invalid.field.path": 1,  # Invalid field
            "tech_stack.languages": 1,
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 400
    data = response.json()
    assert "invalid field" in data["detail"].lower()
    assert "invalid.field.path" in data["detail"]


@pytest.mark.asyncio
async def test_update_invalid_priority_too_low(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT endpoint rejects priority values below 1."""
    invalid_config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {
            "tech_stack.languages": 0,  # Invalid: too low
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 400
    data = response.json()
    assert "invalid priority" in data["detail"].lower()
    assert "tech_stack.languages" in data["detail"]


@pytest.mark.asyncio
async def test_update_invalid_priority_too_high(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT endpoint rejects priority values above 3."""
    invalid_config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {
            "tech_stack.backend": 4,  # Invalid: too high
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 400
    data = response.json()
    assert "invalid priority" in data["detail"].lower()
    assert "tech_stack.backend" in data["detail"]


@pytest.mark.asyncio
async def test_update_invalid_token_budget_too_low(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT endpoint rejects token budget below minimum."""
    invalid_config = {
        "version": "1.0",
        "token_budget": 50,  # Invalid: below 100
        "fields": {
            "tech_stack.languages": 1,
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 400
    data = response.json()
    assert "token budget" in data["detail"].lower()
    assert "100" in data["detail"]


@pytest.mark.asyncio
async def test_update_invalid_token_budget_negative(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT endpoint rejects negative token budget."""
    invalid_config = {
        "version": "1.0",
        "token_budget": -500,  # Invalid: negative
        "fields": {
            "tech_stack.languages": 1,
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=invalid_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 400
    data = response.json()
    assert "token budget" in data["detail"].lower()


# POST Tests - Reset Field Priority Config


@pytest.mark.asyncio
async def test_reset_field_priority(
    api_client: AsyncClient,
    custom_user_token: str,
    test_user_with_custom_config: User,
    db_session: AsyncSession,
):
    """Test POST reset endpoint clears custom config and returns defaults."""
    # Verify user has custom config
    assert test_user_with_custom_config.field_priority_config is not None

    # Reset config
    response = await api_client.post(
        "/api/v1/users/me/field-priority/reset",
        cookies={"access_token": custom_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Assert response contains default values
    assert data["version"] == DEFAULT_FIELD_PRIORITY["version"]
    assert data["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data["fields"] == DEFAULT_FIELD_PRIORITY["fields"]

    # Verify database cleared
    await db_session.refresh(test_user_with_custom_config)
    assert test_user_with_custom_config.field_priority_config is None

    # Verify GET returns defaults after reset
    get_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": custom_user_token},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]


@pytest.mark.asyncio
async def test_reset_field_priority_idempotent(
    api_client: AsyncClient,
    user_token: str,
    test_user: User,
    db_session: AsyncSession,
):
    """Test reset is idempotent - can reset even when no custom config exists."""
    # Verify user has no custom config
    assert test_user.field_priority_config is None

    # Reset config (should succeed even though nothing to reset)
    response = await api_client.post(
        "/api/v1/users/me/field-priority/reset",
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()

    # Assert response contains default values
    assert data["version"] == DEFAULT_FIELD_PRIORITY["version"]
    assert data["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data["fields"] == DEFAULT_FIELD_PRIORITY["fields"]


# Multi-Tenant Isolation Tests


@pytest.mark.asyncio
async def test_multi_tenant_isolation_get(
    api_client: AsyncClient,
    custom_user_token: str,
    second_tenant_token: str,
    test_user_with_custom_config: User,
    second_tenant_user: User,
    db_session: AsyncSession,
):
    """Test tenant isolation - users cannot see other tenants' configs."""
    # User 1 (with custom config) gets their config
    response1 = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": custom_user_token},
    )
    assert response1.status_code == 200
    data1 = response1.json()

    # User 2 (different tenant, no custom config) gets their config
    response2 = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": second_tenant_token},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # User 1 has custom config
    assert data1["token_budget"] == test_user_with_custom_config.field_priority_config["token_budget"]

    # User 2 has defaults (not User 1's config)
    assert data2["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data2["token_budget"] != data1["token_budget"]


@pytest.mark.asyncio
async def test_multi_tenant_isolation_update(
    api_client: AsyncClient,
    user_token: str,
    second_tenant_token: str,
    test_user: User,
    second_tenant_user: User,
    db_session: AsyncSession,
):
    """Test tenant isolation - updating one tenant doesn't affect another."""
    custom_config = {
        "version": "1.0",
        "token_budget": 3000,
        "fields": {
            "tech_stack.languages": 1,
            "tech_stack.backend": 1,
        },
    }

    # User 1 updates their config
    response1 = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=custom_config,
        cookies={"access_token": user_token},
    )
    assert response1.status_code == 200

    # User 2 gets their config (should still be defaults)
    response2 = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": second_tenant_token},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # User 2 still has defaults
    assert data2["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert data2["token_budget"] != 3000

    # Verify in database
    await db_session.refresh(test_user)
    await db_session.refresh(second_tenant_user)
    assert test_user.field_priority_config is not None
    assert second_tenant_user.field_priority_config is None


# Authentication Tests


@pytest.mark.asyncio
async def test_unauthorized_access_get(
    api_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test GET endpoint requires authentication."""
    response = await api_client.get("/api/v1/users/me/field-priority")

    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_unauthorized_access_put(
    api_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test PUT endpoint requires authentication."""
    config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {"tech_stack.languages": 1},
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=config,
    )

    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_unauthorized_access_reset(
    api_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test POST reset endpoint requires authentication."""
    response = await api_client.post("/api/v1/users/me/field-priority/reset")

    assert response.status_code in [401, 403]


# Persistence Tests


@pytest.mark.asyncio
async def test_field_priority_persistence(
    api_client: AsyncClient,
    user_token: str,
    test_user: User,
    db_session: AsyncSession,
):
    """Test config persists across requests and sessions."""
    custom_config = {
        "version": "1.0",
        "token_budget": 2200,
        "fields": {
            "tech_stack.languages": 1,
            "tech_stack.backend": 2,
            "tech_stack.database": 3,
            "architecture.pattern": 1,
            "features.core": 1,
        },
    }

    # Update config
    update_response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=custom_config,
        cookies={"access_token": user_token},
    )
    assert update_response.status_code == 200

    # Simulate session refresh by getting config again
    get_response1 = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get_response1.status_code == 200
    data1 = get_response1.json()
    assert data1["token_budget"] == 2200

    # Verify persistence in database directly
    await db_session.refresh(test_user)
    assert test_user.field_priority_config is not None
    assert test_user.field_priority_config["token_budget"] == 2200
    assert len(test_user.field_priority_config["fields"]) == 5

    # Get config again (simulate another session)
    get_response2 = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get_response2.status_code == 200
    data2 = get_response2.json()

    # Config should be identical
    assert data2 == data1
    assert data2["token_budget"] == 2200
    assert data2["fields"] == custom_config["fields"]


# Validation Edge Cases


@pytest.mark.asyncio
async def test_update_with_all_valid_fields(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT with all valid fields succeeds."""
    # Include all valid fields from DEFAULT_FIELD_PRIORITY
    all_fields_config = {
        "version": "1.0",
        "token_budget": 1800,
        "fields": DEFAULT_FIELD_PRIORITY["fields"].copy(),
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=all_fields_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["fields"]) == len(DEFAULT_FIELD_PRIORITY["fields"])


@pytest.mark.asyncio
async def test_update_with_empty_fields(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT with empty fields dict succeeds."""
    empty_config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {},
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=empty_config,
        cookies={"access_token": user_token},
    )

    # Should succeed - user can have minimal config
    assert response.status_code == 200
    data = response.json()
    assert data["fields"] == {}
    assert data["token_budget"] == 1500


@pytest.mark.asyncio
async def test_update_with_minimal_token_budget(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT with minimum valid token budget (100) succeeds."""
    minimal_config = {
        "version": "1.0",
        "token_budget": 100,  # Minimum valid value
        "fields": {"tech_stack.languages": 1},
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=minimal_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_budget"] == 100


@pytest.mark.asyncio
async def test_update_priority_boundary_values(
    api_client: AsyncClient,
    user_token: str,
    db_session: AsyncSession,
):
    """Test PUT with boundary priority values (1 and 3) succeeds."""
    boundary_config = {
        "version": "1.0",
        "token_budget": 1500,
        "fields": {
            "tech_stack.languages": 1,  # Min priority
            "tech_stack.backend": 3,  # Max priority
            "architecture.pattern": 2,  # Mid priority
        },
    }

    response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=boundary_config,
        cookies={"access_token": user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["fields"]["tech_stack.languages"] == 1
    assert data["fields"]["tech_stack.backend"] == 3
    assert data["fields"]["architecture.pattern"] == 2


# Integration Test - Full Workflow


@pytest.mark.asyncio
async def test_full_field_priority_workflow(
    api_client: AsyncClient,
    user_token: str,
    test_user: User,
    db_session: AsyncSession,
):
    """Test complete workflow: get defaults, update, verify, reset, verify."""
    # Step 1: Get defaults (user has no custom config)
    get1_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get1_response.status_code == 200
    defaults = get1_response.json()
    assert defaults["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]

    # Step 2: Update config
    custom_config = {
        "version": "1.0",
        "token_budget": 2500,
        "fields": {
            "tech_stack.languages": 1,
            "tech_stack.backend": 1,
            "tech_stack.database": 2,
        },
    }

    update_response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json=custom_config,
        cookies={"access_token": user_token},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["token_budget"] == 2500

    # Step 3: Verify persistence
    get2_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get2_response.status_code == 200
    verified = get2_response.json()
    assert verified["token_budget"] == 2500
    assert verified["fields"] == custom_config["fields"]

    # Step 4: Reset config
    reset_response = await api_client.post(
        "/api/v1/users/me/field-priority/reset",
        cookies={"access_token": user_token},
    )
    assert reset_response.status_code == 200
    reset_data = reset_response.json()
    assert reset_data["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]

    # Step 5: Verify reset persisted
    get3_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        cookies={"access_token": user_token},
    )
    assert get3_response.status_code == 200
    final = get3_response.json()
    assert final["token_budget"] == DEFAULT_FIELD_PRIORITY["token_budget"]
    assert final["fields"] == DEFAULT_FIELD_PRIORITY["fields"]

    # Step 6: Verify database state
    await db_session.refresh(test_user)
    assert test_user.field_priority_config is None
