"""
Tests for AuthService - Authentication and authorization service layer.

This test suite follows TDD discipline (Red → Green → Refactor):
1. Tests written FIRST (this file)
2. All tests must FAIL initially (RED phase)
3. Implementation makes tests pass (GREEN phase)
4. Refactor for quality (REFACTOR phase)

Test Coverage:
- User authentication (login validation)
- Last login timestamp updates
- Setup state checking
- API key management (list, create, revoke)
- User registration (admin + first admin flows)
- Edge cases and error conditions
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import APIKey, User
from src.giljo_mcp.models.config import SetupState
from src.giljo_mcp.services.auth_service import AuthService


# Fixtures


@pytest_asyncio.fixture
async def auth_service(db_manager, db_session):
    """Create AuthService instance for testing with shared session (Handover 0324)"""
    return AuthService(
        db_manager=db_manager,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session,  # SHARED SESSION for test transaction isolation
    )


@pytest.fixture
async def test_user(db_session):
    """Create test user with known credentials"""
    password = "Test1234!"
    user = User(
        id="test-user-001",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash=bcrypt.hash(password),
        role="developer",
        tenant_key="test_tenant_001",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password  # Return user + plaintext password for tests


@pytest.fixture
async def test_inactive_user(db_session):
    """Create inactive test user"""
    password = "Inactive1234!"
    user = User(
        id="test-user-inactive",
        username="inactiveuser",
        email="inactive@example.com",
        password_hash=bcrypt.hash(password),
        role="developer",
        tenant_key="test_tenant_002",
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password


@pytest.fixture
async def test_api_key(db_session, test_user):
    """Create test API key"""
    user, _ = test_user
    raw_key = "gk_test_key_123456789"
    api_key = APIKey(
        id="test-api-key-001",
        tenant_key=user.tenant_key,
        user_id=user.id,
        name="Test API Key",
        key_hash=bcrypt.hash(raw_key),
        key_prefix="gk_test_key_",
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key, raw_key


@pytest.fixture
async def setup_state(db_session):
    """Create setup state for first admin checking"""
    state = SetupState(
        id="setup-state-001",
        tenant_key="test_tenant_001",
        database_initialized=True,
        database_initialized_at=datetime.now(timezone.utc),
        first_admin_created=False,
    )
    db_session.add(state)
    await db_session.commit()
    await db_session.refresh(state)
    return state


# Test Cases


class TestAuthenticateUser:
    """Tests for authenticate_user method"""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, test_user):
        """Test successful user authentication with valid credentials"""
        user, password = test_user

        result = await auth_service.authenticate_user(user.username, password)

        # New pattern: Returns dict directly with user and token
        assert "user" in result
        assert "token" in result
        assert result["user"]["id"] == user.id
        assert result["user"]["username"] == user.username
        assert result["user"]["tenant_key"] == user.tenant_key
        assert result["token"].startswith("eyJ")  # JWT format

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_service, test_user):
        """Test authentication fails with invalid password"""
        user, _ = test_user

        # New pattern: Raises AuthenticationError exception
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(user.username, "WrongPassword123!")

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent_username(self, auth_service):
        """Test authentication fails with non-existent username"""

        # New pattern: Raises AuthenticationError exception
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user("nonexistent", "Password123!")

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(self, auth_service, test_inactive_user):
        """Test authentication fails for inactive user account"""
        user, password = test_inactive_user

        # New pattern: Raises AuthorizationError exception for inactive accounts
        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.authenticate_user(user.username, password)

        assert "inactive" in str(exc_info.value).lower()


class TestUpdateLastLogin:
    """Tests for update_last_login method"""

    @pytest.mark.asyncio
    async def test_update_last_login_success(self, auth_service, test_user, db_session):
        """Test updating user's last login timestamp"""
        user, _ = test_user
        original_last_login = user.last_login
        new_timestamp = datetime.now(timezone.utc)

        # New pattern: Returns None on success (void method)
        result = await auth_service.update_last_login(user.id, new_timestamp)
        assert result is None

        # Verify in database
        stmt = select(User).where(User.id == user.id)
        result_db = await db_session.execute(stmt)
        updated_user = result_db.scalar_one()
        assert updated_user.last_login is not None
        assert updated_user.last_login != original_last_login

    @pytest.mark.asyncio
    async def test_update_last_login_nonexistent_user(self, auth_service):
        """Test updating last login for non-existent user fails gracefully"""

        # New pattern: Raises ResourceNotFoundError exception
        with pytest.raises(ResourceNotFoundError):
            await auth_service.update_last_login("nonexistent-user-id", datetime.now(timezone.utc))


class TestCheckSetupState:
    """Tests for check_setup_state method"""

    @pytest.mark.asyncio
    async def test_check_setup_state_exists(self, auth_service, setup_state):
        """Test retrieving existing setup state"""
        result = await auth_service.check_setup_state(setup_state.tenant_key)

        # New pattern: Returns dict directly (not wrapped)
        assert result is not None
        assert result["first_admin_created"] is False
        assert result["database_initialized"] is True

    @pytest.mark.asyncio
    async def test_check_setup_state_not_found(self, auth_service):
        """Test retrieving setup state when none exists"""
        result = await auth_service.check_setup_state("nonexistent_tenant")

        # New pattern: Returns None when not found
        assert result is None


class TestListAPIKeys:
    """Tests for list_api_keys method"""

    @pytest.mark.asyncio
    async def test_list_api_keys_active_only(self, auth_service, test_user, test_api_key):
        """Test listing only active API keys"""
        user, _ = test_user

        # New pattern: Returns list directly (not wrapped)
        result = await auth_service.list_api_keys(user.id, include_revoked=False)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Test API Key"
        assert result[0]["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_api_keys_include_revoked(self, auth_service, test_user, test_api_key, db_session):
        """Test listing API keys including revoked ones"""
        user, _ = test_user
        api_key, _ = test_api_key

        # Revoke the API key
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        await db_session.commit()

        # New pattern: Returns list directly
        result = await auth_service.list_api_keys(user.id, include_revoked=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["is_active"] is False
        assert result[0]["revoked_at"] is not None

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, auth_service, test_user):
        """Test listing API keys when user has none"""
        # Create user without API keys
        from src.giljo_mcp.models.auth import User

        new_user = User(
            id="user-no-keys",
            username="nokeyuser",
            email="nokeys@example.com",
            password_hash=bcrypt.hash("Password123!"),
            role="developer",
            tenant_key="test_tenant_003",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        # Note: Would need to add to session, but for this test focusing on logic

        result = await auth_service.list_api_keys("user-no-keys", include_revoked=False)

        # New pattern: Returns empty list
        assert isinstance(result, list)
        assert len(result) == 0


class TestCreateAPIKey:
    """Tests for create_api_key method"""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, auth_service, test_user):
        """Test creating new API key"""
        user, _ = test_user

        # New pattern: Returns dict directly with API key data
        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="New Test Key", permissions=["*"]
        )

        assert result["name"] == "New Test Key"
        assert "api_key" in result  # Raw key returned once
        assert result["api_key"].startswith("gk_")
        assert "key_prefix" in result
        assert result["key_hash"] is not None  # Hashed version stored

    @pytest.mark.asyncio
    async def test_create_api_key_custom_permissions(self, auth_service, test_user):
        """Test creating API key with custom permissions"""
        user, _ = test_user

        # New pattern: Returns dict directly
        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Limited Key", permissions=["read", "write"]
        )

        assert result["permissions"] == ["read", "write"]


class TestRevokeAPIKey:
    """Tests for revoke_api_key method"""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, auth_service, test_user, test_api_key, db_session):
        """Test revoking an active API key"""
        user, _ = test_user
        api_key, _ = test_api_key

        # New pattern: Returns None on success
        result = await auth_service.revoke_api_key(api_key.id, user.id)
        assert result is None

        # Verify in database
        stmt = select(APIKey).where(APIKey.id == api_key.id)
        result_db = await db_session.execute(stmt)
        revoked_key = result_db.scalar_one()
        assert revoked_key.is_active is False
        assert revoked_key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, auth_service, test_user):
        """Test revoking non-existent API key"""
        user, _ = test_user

        # New pattern: Raises ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError):
            await auth_service.revoke_api_key("nonexistent-key-id", user.id)

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_user(self, auth_service, test_api_key, db_session):
        """Test revoking API key belonging to another user fails"""
        api_key, _ = test_api_key

        # New pattern: Raises ResourceNotFoundError (access denied)
        with pytest.raises(ResourceNotFoundError):
            await auth_service.revoke_api_key(api_key.id, "wrong-user-id")


class TestRegisterUser:
    """Tests for register_user method"""

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, test_user, db_session):
        """Test registering new user (admin creates user)"""
        admin_user, _ = test_user

        # New pattern: Returns dict directly with user data
        result = await auth_service.register_user(
            username="newuser",
            email="new@example.com",
            password="NewPassword123!",
            role="developer",
            requesting_admin_id=admin_user.id,
        )

        assert result["username"] == "newuser"
        assert result["email"] == "new@example.com"
        assert result["role"] == "developer"
        assert "tenant_key" in result  # Auto-generated per-user tenant

        # Verify password was hashed
        stmt = select(User).where(User.username == "newuser")
        result_db = await db_session.execute(stmt)
        new_user = result_db.scalar_one()
        assert new_user.password_hash != "NewPassword123!"
        assert bcrypt.verify("NewPassword123!", new_user.password_hash)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, auth_service, test_user):
        """Test registering user with existing username fails"""
        admin_user, _ = test_user

        # New pattern: Raises ValidationError for duplicates
        with pytest.raises(ValidationError) as exc_info:
            await auth_service.register_user(
                username=admin_user.username,  # Duplicate
                email="different@example.com",
                password="Password123!",
                role="developer",
                requesting_admin_id=admin_user.id,
            )

        assert "already exists" in str(exc_info.value).lower()


class TestCreateFirstAdmin:
    """Tests for create_first_admin method"""

    @pytest.mark.asyncio
    async def test_create_first_admin_success(self, auth_service, db_session):
        """Test creating first admin account on fresh install"""
        # Verify no users exist
        stmt = select(User)
        result = await db_session.execute(stmt)
        assert len(result.scalars().all()) == 0

        # New pattern: Returns dict directly with user data and token
        result = await auth_service.create_first_admin(
            username="admin", email="admin@example.com", password="SecureAdmin123!@#", full_name="System Administrator"
        )

        assert result["username"] == "admin"
        assert result["role"] == "admin"
        assert result["is_active"] is True
        assert "token" in result  # JWT for immediate login

        # Verify SetupState was updated
        stmt_setup = select(SetupState)
        result_setup = await db_session.execute(stmt_setup)
        setup_state = result_setup.scalar_one_or_none()
        assert setup_state is not None
        assert setup_state.first_admin_created is True

    @pytest.mark.asyncio
    async def test_create_first_admin_fails_when_users_exist(self, auth_service, test_user):
        """Test creating first admin fails when users already exist"""

        # New pattern: Raises ValidationError when admin already exists
        with pytest.raises(ValidationError) as exc_info:
            await auth_service.create_first_admin(
                username="secondadmin", email="second@example.com", password="SecureAdmin123!@#", full_name="Second Admin"
            )

        assert "already exists" in str(exc_info.value).lower() or "Administrator account already exists" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_first_admin_weak_password(self, auth_service, db_session):
        """Test creating first admin with weak password fails"""

        # New pattern: Raises ValidationError for weak passwords
        with pytest.raises(ValidationError) as exc_info:
            await auth_service.create_first_admin(
                username="admin",
                email="admin@example.com",
                password="weak",  # Too short, no complexity
                full_name="Admin",
            )

        assert "password" in str(exc_info.value).lower()
