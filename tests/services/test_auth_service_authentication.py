# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for AuthService - Authentication, last login, and setup state.

Split from test_auth_service.py. Contains:
- TestAuthenticateUser: User authentication (login validation)
- TestUpdateLastLogin: Last login timestamp updates
- TestCheckSetupState: Setup state checking

Handover 0731c: Updated for typed service returns (AuthResult, SetupStateInfo).
"""

from datetime import UTC, datetime
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
)
from giljo_mcp.models.auth import User
from giljo_mcp.models.config import SetupState
from giljo_mcp.models.organizations import Organization
from giljo_mcp.schemas.service_responses import (
    AuthResult,
    SetupStateInfo,
)


# Fixtures local to this file


@pytest_asyncio.fixture
async def auth_inactive_org(db_session):
    """Create second test organization for inactive user (0424j)"""
    unique_id = str(uuid4())[:8]
    org = Organization(
        id=str(uuid4()),
        tenant_key=f"test_tenant_inactive_{unique_id}",
        name=f"Test Organization Inactive {unique_id}",
        slug=f"test-org-inactive-{unique_id}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def auth_inactive_user(db_session, auth_inactive_org):
    """Create inactive test user"""
    unique_id = str(uuid4())[:8]
    password = "Inactive1234!"
    user = User(
        id=str(uuid4()),
        username=f"inactiveuser_{unique_id}",
        email=f"inactive_{unique_id}@example.com",
        password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role="developer",
        tenant_key=auth_inactive_org.tenant_key,  # Use org's tenant_key
        org_id=auth_inactive_org.id,  # 0424j: User.org_id NOT NULL
        is_active=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password


@pytest_asyncio.fixture
async def auth_setup_state(db_session, auth_test_org):
    """Create setup state for first admin checking"""
    state = SetupState(
        id=str(uuid4()),
        tenant_key=auth_test_org.tenant_key,  # Use org's tenant_key
        database_initialized=True,
        database_initialized_at=datetime.now(UTC),
        first_admin_created=False,
    )
    db_session.add(state)
    await db_session.commit()
    await db_session.refresh(state)
    return state


# Test Cases


class TestAuthenticateUser:
    """Tests for authenticate_user method - returns AuthResult"""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, auth_user_with_password):
        """Test successful user authentication returns AuthResult"""
        user, password = auth_user_with_password

        result = await auth_service.authenticate_user(user.username, password)

        # Typed return: AuthResult with attribute access
        assert isinstance(result, AuthResult)
        assert result.user_id == user.id
        assert result.username == user.username
        assert result.tenant_key == user.tenant_key
        assert result.role == user.role
        assert result.email == user.email
        assert result.is_active is True
        assert result.token.startswith("eyJ")  # JWT format

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_service, auth_user_with_password):
        """Test authentication fails with invalid password"""
        user, _ = auth_user_with_password

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(user.username, "WrongPassword123!")

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent_username(self, auth_service):
        """Test authentication fails with non-existent username"""

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user("nonexistent", "Password123!")

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(self, auth_service, auth_inactive_user):
        """Test authentication fails for inactive user account"""
        user, password = auth_inactive_user

        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.authenticate_user(user.username, password)

        assert "inactive" in str(exc_info.value).lower()

    # ------------------------------------------------------------------
    # AUTH-EMAIL dual-lookup (handover af53e62b)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_authenticate_user_by_username_succeeds(self, auth_service, auth_user_with_password):
        """AUTH-EMAIL: existing username login path is preserved."""
        user, password = auth_user_with_password

        result = await auth_service.authenticate_user(user.username, password)

        assert isinstance(result, AuthResult)
        assert result.user_id == user.id
        assert result.username == user.username

    @pytest.mark.asyncio
    async def test_authenticate_user_by_email_succeeds(self, auth_service, auth_user_with_password):
        """AUTH-EMAIL: login resolves the user when the email is passed as identifier."""
        user, password = auth_user_with_password

        result = await auth_service.authenticate_user(user.email, password)

        assert isinstance(result, AuthResult)
        assert result.user_id == user.id
        assert result.email == user.email

    @pytest.mark.asyncio
    async def test_authenticate_user_by_email_is_case_insensitive(self, auth_service, auth_user_with_password):
        """AUTH-EMAIL: email match is case-insensitive (users type 'Name@x.com')."""
        user, password = auth_user_with_password

        result = await auth_service.authenticate_user(user.email.upper(), password)

        assert isinstance(result, AuthResult)
        assert result.user_id == user.id

    @pytest.mark.asyncio
    async def test_authenticate_user_unknown_identifier_raises_invalid_credentials(self, auth_service):
        """AUTH-EMAIL: unknown identifier (no username AND no email match) raises generic error."""
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user("nobody@nowhere.example", "Password123!")

        # Generic error — MUST NOT leak which lookup (username vs email) failed
        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_username_match_wins_over_email_match(
        self, auth_service, db_session, auth_test_org
    ):
        """
        AUTH-EMAIL: if the identifier happens to match User A's username AND
        User B's email, the username match wins (deterministic first-lookup order).
        """
        from datetime import datetime
        from uuid import uuid4

        import bcrypt

        from giljo_mcp.models.auth import User

        shared = f"collide_{uuid4().hex[:8]}"
        pw_username_owner = "UserWins1!"
        pw_email_owner = "EmailOwner1!"

        user_username_owner = User(
            id=str(uuid4()),
            username=shared,  # identifier matches this user's username
            email=f"{shared}_unrelated@example.com",
            password_hash=bcrypt.hashpw(pw_username_owner.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="developer",
            tenant_key=auth_test_org.tenant_key,
            org_id=auth_test_org.id,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        user_email_owner = User(
            id=str(uuid4()),
            username=f"other_{uuid4().hex[:8]}",
            email=shared,  # identifier ALSO matches this user's email
            password_hash=bcrypt.hashpw(pw_email_owner.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="developer",
            tenant_key=auth_test_org.tenant_key,
            org_id=auth_test_org.id,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add_all([user_username_owner, user_email_owner])
        await db_session.commit()

        # Password of the username-owner wins; password of the email-owner fails.
        result = await auth_service.authenticate_user(shared, pw_username_owner)
        assert result.user_id == user_username_owner.id

        with pytest.raises(AuthenticationError):
            await auth_service.authenticate_user(shared, pw_email_owner)


class TestUpdateLastLogin:
    """Tests for update_last_login method"""

    @pytest.mark.asyncio
    async def test_update_last_login_success(self, auth_service, auth_user_with_password, db_session):
        """Test updating user's last login timestamp"""
        user, _ = auth_user_with_password
        original_last_login = user.last_login
        new_timestamp = datetime.now(UTC)

        # Returns None on success (void method)
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
        """Test updating last login for non-existent user raises ResourceNotFoundError"""

        with pytest.raises(ResourceNotFoundError):
            await auth_service.update_last_login("nonexistent-user-id", datetime.now(UTC))


class TestCheckSetupState:
    """Tests for check_setup_state method - returns SetupStateInfo or None"""

    @pytest.mark.asyncio
    async def test_check_setup_state_exists(self, auth_service, auth_setup_state):
        """Test retrieving existing setup state returns SetupStateInfo"""
        result = await auth_service.check_setup_state(auth_setup_state.tenant_key)

        # Typed return: SetupStateInfo with attribute access
        assert result is not None
        assert isinstance(result, SetupStateInfo)
        assert result.first_admin_created is False
        assert result.database_initialized is True
        assert result.tenant_key == auth_setup_state.tenant_key

    @pytest.mark.asyncio
    async def test_check_setup_state_not_found(self, auth_service):
        """Test retrieving setup state when none exists returns None"""
        result = await auth_service.check_setup_state("nonexistent_tenant")

        assert result is None
