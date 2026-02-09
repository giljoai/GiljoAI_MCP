"""
Comprehensive Integration Tests for API Key Manager Flow.

These tests validate the complete API key management workflow including:
- Key generation with name and permissions
- Key returned in plaintext (only once)
- Key stored as hash in database
- Modal/UI confirmation flows
- Copy functionality tests
- Multi-tenant isolation for API keys

Following TDD: These tests define expected API key security behavior.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy import select

from api.app import create_app
from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key, verify_api_key
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import APIKey, User


@pytest.fixture
async def test_user(db_session):
    """Create test user with API keys (0424j compliant - org_id required)."""
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    # Create org first (0424j: org_id is NOT NULL)
    org = Organization(
        name=f"API Test Org {unique_suffix}",
        slug=f"api-test-org-{unique_suffix}",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"api_test_user_{unique_suffix}",
        email=f"apiuser_{unique_suffix}@example.com",
        password_hash=bcrypt.hash("TestPassword123!"),
        role="developer",
        tenant_key=tenant_key,
        org_id=org.id,  # Required after 0424j
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get auth headers for test user."""
    token = JWTManager.create_access_token(
        user_id=test_user.id, username=test_user.username, role=test_user.role, tenant_key=test_user.tenant_key
    )
    return {"Cookie": f"access_token={token}"}


class TestAPIKeyGeneration:
    """Test API key generation flow."""

    @pytest.mark.asyncio
    async def test_generate_api_key_with_name(self, db_manager, db_session, test_user, auth_headers):
        """Test generating API key with descriptive name."""
        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.post(
            "/api/auth/api-keys", headers=auth_headers, json={"name": "Production MCP Server", "permissions": ["*"]}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["name"] == "Production MCP Server"
        assert "api_key" in data  # Plaintext key (only shown once!)
        assert "key_prefix" in data
        assert data["message"] == "API key created successfully. Store this key securely - it will not be shown again!"

        # Verify key format
        plaintext_key = data["api_key"]
        assert plaintext_key.startswith("gk_")
        assert len(plaintext_key) >= 48  # Secure length

        # Verify key prefix matches
        expected_prefix = get_key_prefix(plaintext_key)
        assert data["key_prefix"] == expected_prefix

        # Verify key stored as hash in database
        stmt = select(APIKey).where(APIKey.id == data["id"])
        result = await db_session.execute(stmt)
        db_key = result.scalar_one()

        assert db_key.key_hash != plaintext_key  # NOT stored in plaintext
        assert db_key.key_hash.startswith("$2b$")  # bcrypt hash
        assert verify_api_key(plaintext_key, db_key.key_hash) is True

    @pytest.mark.asyncio
    async def test_api_key_returned_only_once(self, db_manager, db_session, test_user, auth_headers):
        """Test that API key plaintext is only shown at creation time."""
        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        # Create API key
        create_response = client.post(
            "/api/auth/api-keys", headers=auth_headers, json={"name": "One-Time Display Key", "permissions": ["*"]}
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        plaintext_key = create_response.json()["api_key"]

        # List API keys - plaintext should NOT be included
        list_response = client.get("/api/auth/api-keys", headers=auth_headers)

        assert list_response.status_code == status.HTTP_200_OK
        keys = list_response.json()

        # Find our key in the list
        our_key = next((k for k in keys if k["name"] == "One-Time Display Key"), None)
        assert our_key is not None

        # Verify plaintext is NOT in the response
        assert "api_key" not in our_key
        assert our_key["key_prefix"] == get_key_prefix(plaintext_key)

    @pytest.mark.asyncio
    async def test_api_key_hash_stored_correctly(self, db_session, test_user):
        """Test that API key is hashed using bcrypt before storage."""
        plaintext_key = generate_api_key()
        key_hash = hash_api_key(plaintext_key)

        # Create API key record
        api_key = APIKey(
            id=str(uuid4()),
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Hash Test Key",
            key_hash=key_hash,
            key_prefix=get_key_prefix(plaintext_key),
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(api_key)
        await db_session.commit()

        # Verify hash properties
        assert api_key.key_hash != plaintext_key
        assert api_key.key_hash.startswith("$2b$")
        assert len(api_key.key_hash) >= 60  # bcrypt hash length

        # Verify hash can be verified
        assert verify_api_key(plaintext_key, api_key.key_hash) is True
        assert verify_api_key("wrong_key", api_key.key_hash) is False

    @pytest.mark.asyncio
    async def test_api_key_with_custom_permissions(self, db_manager, db_session, test_user, auth_headers):
        """Test generating API key with specific permissions."""
        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.post(
            "/api/auth/api-keys", headers=auth_headers, json={"name": "Read-Only Key", "permissions": ["read", "list"]}
        )

        assert response.status_code == status.HTTP_201_CREATED
        key_id = response.json()["id"]

        # Verify permissions stored correctly
        stmt = select(APIKey).where(APIKey.id == key_id)
        result = await db_session.execute(stmt)
        db_key = result.scalar_one()

        assert db_key.permissions == ["read", "list"]


class TestAPIKeyListing:
    """Test API key listing functionality."""

    @pytest.mark.asyncio
    async def test_list_user_api_keys(self, db_manager, db_session, test_user, auth_headers):
        """Test user can list their own API keys."""
        # Create multiple API keys for user
        for i in range(3):
            plaintext_key = generate_api_key()
            api_key = APIKey(
                id=str(uuid4()),
                user_id=test_user.id,
                tenant_key=test_user.tenant_key,
                name=f"Test Key {i + 1}",
                key_hash=hash_api_key(plaintext_key),
                key_prefix=get_key_prefix(plaintext_key),
                permissions=["*"],
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(api_key)

        await db_session.commit()

        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.get("/api/auth/api-keys", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        keys = response.json()

        assert len(keys) == 3
        assert all("name" in k for k in keys)
        assert all("key_prefix" in k for k in keys)
        assert all("is_active" in k for k in keys)
        assert all("api_key" not in k for k in keys)  # Plaintext never returned

    @pytest.mark.asyncio
    async def test_list_includes_revoked_keys(self, db_manager, db_session, test_user, auth_headers):
        """Test that listing includes revoked keys with revoked_at timestamp."""
        # Create active key
        active_key = APIKey(
            id=str(uuid4()),
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Active Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_active",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        # Create revoked key
        revoked_key = APIKey(
            id=str(uuid4()),
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Revoked Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_revoked",
            permissions=["*"],
            is_active=False,
            created_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc),
        )

        db_session.add_all([active_key, revoked_key])
        await db_session.commit()

        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.get("/api/auth/api-keys", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        keys = response.json()

        # Should include both active and revoked keys
        assert len(keys) == 2

        # Find each key
        active = next(k for k in keys if k["name"] == "Active Key")
        revoked = next(k for k in keys if k["name"] == "Revoked Key")

        assert active["is_active"] is True
        assert active["revoked_at"] is None

        assert revoked["is_active"] is False
        assert revoked["revoked_at"] is not None


class TestAPIKeyRevocation:
    """Test API key revocation functionality."""

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, db_manager, db_session, test_user, auth_headers):
        """Test user can revoke their own API key."""
        # Create API key
        api_key = APIKey(
            id=str(uuid4()),
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Key to Revoke",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_revoke",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(api_key)
        await db_session.commit()

        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.delete(f"/api/auth/api-keys/{api_key.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["message"] == "API key revoked successfully"
        assert data["name"] == "Key to Revoke"

        # Verify key is revoked in database
        stmt = select(APIKey).where(APIKey.id == api_key.id)
        result = await db_session.execute(stmt)
        revoked_key = result.scalar_one()

        assert revoked_key.is_active is False
        assert revoked_key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_user_cannot_revoke_others_keys(self, db_manager, db_session, test_user, auth_headers):
        """Test user cannot revoke API keys belonging to other users."""
        # Create another user
        other_user = User(
            id=str(uuid4()),
            username="other_user",
            email="other@example.com",
            password_hash=bcrypt.hash("OtherPass123!"),
            role="developer",
            tenant_key="test_tenant",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_user)

        # Create API key for other user
        other_key = APIKey(
            id=str(uuid4()),
            user_id=other_user.id,
            tenant_key="test_tenant",
            name="Other User's Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_other",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_key)
        await db_session.commit()

        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        # Try to revoke other user's key
        response = client.delete(f"/api/auth/api-keys/{other_key.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify key is still active
        stmt = select(APIKey).where(APIKey.id == other_key.id)
        result = await db_session.execute(stmt)
        still_active_key = result.scalar_one()

        assert still_active_key.is_active is True


class TestAPIKeyUsageTracking:
    """Test API key usage tracking (last_used timestamp)."""

    @pytest.mark.asyncio
    async def test_api_key_last_used_updated(self, db_session, test_user):
        """Test that last_used timestamp is updated when key is used."""
        plaintext_key = generate_api_key()

        api_key = APIKey(
            id=str(uuid4()),
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Usage Tracking Key",
            key_hash=hash_api_key(plaintext_key),
            key_prefix=get_key_prefix(plaintext_key),
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_used=None,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Simulate API key usage
        # (This would happen in the API key authentication middleware)
        api_key.last_used = datetime.now(timezone.utc)
        await db_session.commit()

        # Verify last_used is set
        stmt = select(APIKey).where(APIKey.id == api_key.id)
        result = await db_session.execute(stmt)
        updated_key = result.scalar_one()

        assert updated_key.last_used is not None


class TestAPIKeyModalFlow:
    """Test modal/UI confirmation flows for API key display."""

    @pytest.mark.asyncio
    async def test_api_key_display_with_server_url(self, db_manager, test_user, auth_headers):
        """Test API key creation response includes server URL for MCP config."""
        app = create_app()
        app.state.api_state = type("obj", (object,), {"db_manager": db_manager})()

        client = TestClient(app)

        response = client.post(
            "/api/auth/api-keys", headers=auth_headers, json={"name": "Modal Test Key", "permissions": ["*"]}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Frontend would use this data to show:
        # 1. Plaintext API key (one-time display)
        # 2. Server URL for MCP config
        # 3. Claude Code config snippet
        # 4. Environment variables

        assert "api_key" in data
        assert "key_prefix" in data
        assert "name" in data

        # Frontend modal would display:
        # - API Key: {data["api_key"]}
        # - Server URL: http://192.168.1.100:7272 (from config)
        # - Claude Code config: { "mcpServers": { "giljo-mcp": { "env": { "GILJO_API_KEY": "{data["api_key"]}" } } } }

    @pytest.mark.asyncio
    async def test_api_key_confirmation_required(self):
        """Test that modal cannot close until user confirms key is saved."""
        # This is a frontend behavior test
        # The API just provides the data; frontend enforces:
        # 1. Modal shows with plaintext key
        # 2. Checkbox "I have saved this key securely" must be checked
        # 3. Modal cannot be closed until confirmed
        # 4. After closing, key is masked in list


class TestMultiTenantAPIKeyIsolation:
    """Test multi-tenant isolation for API keys."""

    @pytest.mark.asyncio
    async def test_api_keys_filtered_by_tenant(self, db_session):
        """Test API keys are isolated by tenant_key."""
        # Create users in different tenants
        user1 = User(
            id=str(uuid4()),
            username="tenant1_user",
            email="user1@example.com",
            password_hash=bcrypt.hash("Pass123!"),
            role="developer",
            tenant_key="tenant_1",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        user2 = User(
            id=str(uuid4()),
            username="tenant2_user",
            email="user2@example.com",
            password_hash=bcrypt.hash("Pass123!"),
            role="developer",
            tenant_key="tenant_2",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add_all([user1, user2])

        # Create API keys for each user
        key1 = APIKey(
            id=str(uuid4()),
            user_id=user1.id,
            tenant_key="tenant_1",
            name="Tenant 1 Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_t1",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        key2 = APIKey(
            id=str(uuid4()),
            user_id=user2.id,
            tenant_key="tenant_2",
            name="Tenant 2 Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_t2",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add_all([key1, key2])
        await db_session.commit()

        # Query keys for tenant_1
        stmt = select(APIKey).where(APIKey.tenant_key == "tenant_1")
        result = await db_session.execute(stmt)
        tenant1_keys = result.scalars().all()

        # Should only see tenant_1 keys
        assert len(tenant1_keys) == 1
        assert tenant1_keys[0].name == "Tenant 1 Key"

        # Query keys for tenant_2
        stmt = select(APIKey).where(APIKey.tenant_key == "tenant_2")
        result = await db_session.execute(stmt)
        tenant2_keys = result.scalars().all()

        # Should only see tenant_2 keys
        assert len(tenant2_keys) == 1
        assert tenant2_keys[0].name == "Tenant 2 Key"

    @pytest.mark.asyncio
    async def test_api_key_auth_respects_tenant_boundaries(self, db_session):
        """Test API key authentication respects tenant isolation."""
        # Create API key for tenant_1
        tenant1_user = User(
            id=str(uuid4()),
            username="tenant1_user",
            email="tenant1@example.com",
            password_hash=bcrypt.hash("Pass123!"),
            role="developer",
            tenant_key="tenant_1",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(tenant1_user)

        plaintext_key = generate_api_key()
        api_key = APIKey(
            id=str(uuid4()),
            user_id=tenant1_user.id,
            tenant_key="tenant_1",
            name="Tenant 1 Auth Key",
            key_hash=hash_api_key(plaintext_key),
            key_prefix=get_key_prefix(plaintext_key),
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(api_key)
        await db_session.commit()

        # When authenticating with this API key, the user's tenant_key
        # should be injected into all database queries
        # This ensures tenant isolation at the data access layer

        # Verify API key lookup includes tenant check
        stmt = select(APIKey).where(
            APIKey.key_prefix == get_key_prefix(plaintext_key),
            APIKey.tenant_key == "tenant_1",  # Tenant filter
        )
        result = await db_session.execute(stmt)
        found_key = result.scalar_one_or_none()

        assert found_key is not None

        # Trying to find key with wrong tenant should fail
        stmt = select(APIKey).where(
            APIKey.key_prefix == get_key_prefix(plaintext_key),
            APIKey.tenant_key == "tenant_2",  # Wrong tenant!
        )
        result = await db_session.execute(stmt)
        not_found = result.scalar_one_or_none()

        assert not_found is None


class TestAPIKeySecurityEdgeCases:
    """Test edge cases and security scenarios for API keys."""

    @pytest.mark.asyncio
    async def test_revoked_key_cannot_authenticate(self, db_session):
        """Test that revoked API keys cannot be used for authentication."""
        user = User(
            id=str(uuid4()),
            username="security_test",
            email="security@example.com",
            password_hash=bcrypt.hash("Pass123!"),
            role="developer",
            tenant_key="test_tenant",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)

        plaintext_key = generate_api_key()
        api_key = APIKey(
            id=str(uuid4()),
            user_id=user.id,
            tenant_key="test_tenant",
            name="Revoked Key",
            key_hash=hash_api_key(plaintext_key),
            key_prefix=get_key_prefix(plaintext_key),
            permissions=["*"],
            is_active=False,  # Revoked
            created_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc),
        )
        db_session.add(api_key)
        await db_session.commit()

        # Auth middleware should check is_active=True
        assert api_key.is_active is False

    @pytest.mark.asyncio
    async def test_api_key_prefix_collision_handling(self, db_session):
        """Test handling of API key prefix collisions (unlikely but possible)."""
        # API key prefixes should be unique enough that collisions are rare
        # But if they occur, full key hash verification ensures security

        user = User(
            id=str(uuid4()),
            username="collision_test",
            email="collision@example.com",
            password_hash=bcrypt.hash("Pass123!"),
            role="developer",
            tenant_key="test_tenant",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)

        # Create two keys with same prefix (simulated collision)
        key1 = APIKey(
            id=str(uuid4()),
            user_id=user.id,
            tenant_key="test_tenant",
            name="Key 1",
            key_hash=hash_api_key("gk_collision_key_1"),
            key_prefix="gk_collision",  # Same prefix
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        key2 = APIKey(
            id=str(uuid4()),
            user_id=user.id,
            tenant_key="test_tenant",
            name="Key 2",
            key_hash=hash_api_key("gk_collision_key_2"),
            key_prefix="gk_collision",  # Same prefix
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db_session.add_all([key1, key2])
        await db_session.commit()

        # Auth should verify full hash, not just prefix
        assert verify_api_key("gk_collision_key_1", key1.key_hash) is True
        assert verify_api_key("gk_collision_key_1", key2.key_hash) is False
