"""
Test suite for UserService - TDD Handover 0322 Phase 1

This test suite covers all 16 UserService methods with comprehensive coverage:
- list_users (tenant isolation, returns list)
- get_user (user retrieval, not found handling)
- create_user (user creation, duplicate checks)
- update_user (field updates, tenant checks)
- delete_user (soft delete with is_active=False)
- change_role (role changes, admin restrictions)
- change_password (password verification, hashing)
- reset_password (password reset generates new password)
- check_username_exists (duplicate detection)
- check_email_exists (email duplicate detection)
- verify_password (bcrypt password verification)
- get_field_priority_config (config retrieval)
- update_field_priority_config (config persistence)
- reset_field_priority_config (config reset to defaults)
- get_depth_config (depth config retrieval)
- update_depth_config (depth config persistence)

Coverage Target: >80%
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt

from src.giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.user_service import UserService


# Use existing fixtures from base_fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_service(db_manager, db_session, test_tenant_key):
    """Create UserService instance for testing with shared session (Handover 0324)"""
    return UserService(
        db_manager=db_manager,
        tenant_key=test_tenant_key,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session,  # SHARED SESSION for test transaction isolation
    )


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key):
    """Create test user in database"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("TestPassword123"),
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session, test_tenant_key):
    """Create admin user in database"""
    admin = User(
        id=str(uuid4()),
        username=f"admin_{uuid4().hex[:6]}",
        email=f"admin_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("AdminPassword123"),
        full_name="Admin User",
        role="admin",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


# ============================================================================
# TEST: list_users
# ============================================================================


@pytest.mark.asyncio
async def test_list_users_returns_users_for_tenant(user_service, db_session, test_user, test_tenant_key):
    """Test that list_users returns all users in tenant"""
    users = await user_service.list_users()

    assert isinstance(users, list)
    assert len(users) >= 1  # At least test_user

    # Verify user in list
    usernames = [u["username"] for u in users]
    assert test_user.username in usernames


@pytest.mark.asyncio
async def test_list_users_tenant_isolation(user_service, db_session, test_tenant_key):
    """Test that list_users only returns users from same tenant"""
    # Create user in different tenant
    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("OtherPassword123"),
        tenant_key=other_tenant,
        role="developer",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # List users in test tenant
    users = await user_service.list_users()

    assert isinstance(users, list)
    usernames = [u["username"] for u in users]
    assert other_user.username not in usernames


@pytest.mark.asyncio
async def test_list_users_includes_inactive(user_service, db_session, test_tenant_key):
    """Test that list_users includes inactive users by default"""
    # Create inactive user
    inactive_user = User(
        id=str(uuid4()),
        username=f"inactive_{uuid4().hex[:6]}",
        email=f"inactive_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.commit()

    users = await user_service.list_users()

    assert isinstance(users, list)
    usernames = [u["username"] for u in users]
    assert inactive_user.username in usernames


# ============================================================================
# TEST: get_user
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_returns_user_by_id(user_service, test_user):
    """Test that get_user retrieves user by ID"""
    user_dict = await user_service.get_user(test_user.id)

    assert isinstance(user_dict, dict)
    assert user_dict["id"] == test_user.id
    assert user_dict["username"] == test_user.username
    assert user_dict["email"] == test_user.email
    assert "password_hash" not in user_dict  # Password excluded  # Password excluded


@pytest.mark.asyncio
async def test_get_user_not_found(user_service):
    """Test that get_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.get_user(fake_id)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_user_tenant_isolation(user_service, db_session):
    """Test that get_user respects tenant isolation"""
    # Create user in different tenant
    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        tenant_key=other_tenant,
        role="developer",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Try to retrieve user from different tenant
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.get_user(other_user.id)

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST: create_user
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success(user_service, test_tenant_key):
    """Test successful user creation"""
    username = f"newuser_{uuid4().hex[:6]}"
    email = f"new_{uuid4().hex[:6]}@example.com"

    user_dict = await user_service.create_user(
        username=username, email=email, full_name="New User", password="NewPassword123", role="developer"
    )

    assert isinstance(user_dict, dict)
    assert user_dict["username"] == username
    assert user_dict["email"] == email
    assert user_dict["role"] == "developer"
    assert user_dict["is_active"] is True
    assert user_dict["tenant_key"] == test_tenant_key


@pytest.mark.asyncio
async def test_create_user_duplicate_username(user_service, test_user):
    """Test that create_user prevents duplicate usernames"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.create_user(
            username=test_user.username,  # Duplicate
            email="different@example.com",
            password="Password123",
            role="developer",
        )

    error_msg = str(exc_info.value).lower()
    assert "already exists" in error_msg
    assert "username" in error_msg


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service, test_user):
    """Test that create_user prevents duplicate emails"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.create_user(
            username=f"newuser_{uuid4().hex[:6]}",
            email=test_user.email,  # Duplicate
            password="Password123",
            role="developer",
        )

    error_msg = str(exc_info.value).lower()
    assert "already exists" in error_msg
    assert "email" in error_msg


@pytest.mark.asyncio
async def test_create_user_default_password(user_service):
    """Test that create_user sets default password 'GiljoMCP'"""
    username = f"newuser_{uuid4().hex[:6]}"

    user_dict = await user_service.create_user(
        username=username,
        email=f"new_{uuid4().hex[:6]}@example.com",
        role="developer",
        # No password provided - should default to "GiljoMCP"
    )

    assert isinstance(user_dict, dict)
    assert user_dict["must_change_password"] is True


# ============================================================================
# TEST: update_user
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_success(user_service, test_user):
    """Test successful user update"""
    new_email = f"updated_{uuid4().hex[:6]}@example.com"

    user_dict = await user_service.update_user(user_id=test_user.id, email=new_email, full_name="Updated Name")

    assert isinstance(user_dict, dict)
    assert user_dict["email"] == new_email
    assert user_dict["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_not_found(user_service):
    """Test that update_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.update_user(user_id=fake_id, email="new@example.com")

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_user_duplicate_email(user_service, test_user, admin_user):
    """Test that update_user prevents duplicate emails"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_user(
            user_id=test_user.id,
            email=admin_user.email,  # Duplicate
        )

    assert "already exists" in str(exc_info.value).lower()


# ============================================================================
# TEST: delete_user (soft delete)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_soft_delete(user_service, test_user, db_session):
    """Test that delete_user performs soft delete (is_active=False)"""
    result = await user_service.delete_user(test_user.id)

    # Verify method completes without error (void return)
    assert result is None

    # Verify user is deactivated, not deleted
    await db_session.refresh(test_user)
    assert test_user.is_active is False


@pytest.mark.asyncio
async def test_delete_user_not_found(user_service):
    """Test that delete_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.delete_user(fake_id)

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST: change_role
# ============================================================================


@pytest.mark.asyncio
async def test_change_role_success(user_service, test_user, db_session):
    """Test successful role change"""
    user_dict = await user_service.change_role(user_id=test_user.id, new_role="viewer")

    assert isinstance(user_dict, dict)
    assert user_dict["role"] == "viewer"

    await db_session.refresh(test_user)
    assert test_user.role == "viewer"


@pytest.mark.asyncio
async def test_change_role_invalid_role(user_service, test_user):
    """Test that change_role rejects invalid roles"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.change_role(
            user_id=test_user.id,
            new_role="superuser",  # Invalid
        )

    assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_change_role_admin_restriction(user_service, admin_user):
    """Test that last admin cannot be demoted"""
    with pytest.raises(AuthorizationError) as exc_info:
        await user_service.change_role(user_id=admin_user.id, new_role="developer")

    assert "admin" in str(exc_info.value).lower()


# ============================================================================
# TEST: change_password
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_success(user_service, test_user, db_session):
    """Test successful password change"""
    new_password = "NewPassword456"

    result = await user_service.change_password(
        user_id=test_user.id, old_password="TestPassword123", new_password=new_password
    )

    # Verify method completes without error (void return)
    assert result is None

    # Verify new password works
    await db_session.refresh(test_user)
    assert bcrypt.verify(new_password, test_user.password_hash)


@pytest.mark.asyncio
async def test_change_password_incorrect_old_password(user_service, test_user):
    """Test that change_password rejects incorrect old password"""
    with pytest.raises(AuthenticationError) as exc_info:
        await user_service.change_password(
            user_id=test_user.id, old_password="WrongPassword", new_password="NewPassword456"
        )

    assert "incorrect" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_change_password_admin_bypass(user_service, test_user, db_session):
    """Test that admin can change password without old password"""
    new_password = "AdminSetPassword789"

    result = await user_service.change_password(
        user_id=test_user.id,
        old_password=None,  # Admin bypass
        new_password=new_password,
        is_admin=True,
    )

    # Verify method completes without error (void return)
    assert result is None

    await db_session.refresh(test_user)
    assert bcrypt.verify(new_password, test_user.password_hash)


# ============================================================================
# TEST: reset_password
# ============================================================================


@pytest.mark.asyncio
async def test_reset_password_sets_default(user_service, test_user, db_session):
    """Test that reset_password sets password to 'GiljoMCP'"""
    result = await user_service.reset_password(test_user.id)

    # Verify method completes without error (void return)
    assert result is None

    await db_session.refresh(test_user)
    assert bcrypt.verify("GiljoMCP", test_user.password_hash)
    assert test_user.must_change_password is True


# ============================================================================
# TEST: check_username_exists
# ============================================================================


@pytest.mark.asyncio
async def test_check_username_exists_true(user_service, test_user):
    """Test that check_username_exists detects existing username"""
    exists = await user_service.check_username_exists(test_user.username)

    assert exists is True


@pytest.mark.asyncio
async def test_check_username_exists_false(user_service):
    """Test that check_username_exists returns false for non-existent username"""
    exists = await user_service.check_username_exists(f"nonexistent_{uuid4().hex}")

    assert exists is False


# ============================================================================
# TEST: check_email_exists
# ============================================================================


@pytest.mark.asyncio
async def test_check_email_exists_true(user_service, test_user):
    """Test that check_email_exists detects existing email"""
    exists = await user_service.check_email_exists(test_user.email)

    assert exists is True


@pytest.mark.asyncio
async def test_check_email_exists_false(user_service):
    """Test that check_email_exists returns false for non-existent email"""
    exists = await user_service.check_email_exists(f"nonexistent_{uuid4().hex}@example.com")

    assert exists is False


# ============================================================================
# TEST: verify_password
# ============================================================================


@pytest.mark.asyncio
async def test_verify_password_correct(user_service, test_user):
    """Test that verify_password returns true for correct password"""
    verified = await user_service.verify_password(user_id=test_user.id, password="TestPassword123")

    assert verified is True


@pytest.mark.asyncio
async def test_verify_password_incorrect(user_service, test_user):
    """Test that verify_password returns false for incorrect password"""
    verified = await user_service.verify_password(user_id=test_user.id, password="WrongPassword")

    assert verified is False


# ============================================================================
# TEST: get_field_priority_config
# ============================================================================


@pytest.mark.asyncio
async def test_get_field_priority_config_custom(user_service, test_user, db_session):
    """Test that get_field_priority_config returns custom config"""
    custom_config = {
        "version": "2.0",
        "priorities": {"product_core": 1, "vision_documents": 2, "agent_templates": 3, "project_description": 4},
    }
    test_user.field_priority_config = custom_config
    await db_session.commit()

    config = await user_service.get_field_priority_config(test_user.id)

    assert isinstance(config, dict)
    assert config == custom_config


@pytest.mark.asyncio
async def test_get_field_priority_config_defaults(user_service, test_user):
    """Test that get_field_priority_config returns defaults when no custom config"""
    config = await user_service.get_field_priority_config(test_user.id)

    assert isinstance(config, dict)
    assert config["version"] in ["2.0", "2.1"]  # Version may vary
    assert "priorities" in config


# ============================================================================
# TEST: update_field_priority_config
# ============================================================================


@pytest.mark.asyncio
async def test_update_field_priority_config_success(user_service, test_user, db_session):
    """Test successful field priority config update"""
    new_config = {
        "version": "2.0",
        "priorities": {"product_core": 1, "vision_documents": 1, "agent_templates": 2, "project_description": 3},
    }

    result = await user_service.update_field_priority_config(user_id=test_user.id, config=new_config)

    # Verify method completes without error (void return)
    assert result is None

    await db_session.refresh(test_user)
    assert test_user.field_priority_config == new_config


@pytest.mark.asyncio
async def test_update_field_priority_config_validation(user_service, test_user):
    """Test that update_field_priority_config validates config"""
    invalid_config = {
        "version": "2.0",
        "priorities": {
            "product_core": 5  # Invalid priority
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_field_priority_config(user_id=test_user.id, config=invalid_config)

    assert "invalid" in str(exc_info.value).lower()


# ============================================================================
# TEST: reset_field_priority_config
# ============================================================================


@pytest.mark.asyncio
async def test_reset_field_priority_config_clears_custom(user_service, test_user, db_session):
    """Test that reset_field_priority_config clears custom config"""
    # Set custom config
    test_user.field_priority_config = {"version": "2.0", "priorities": {"product_core": 1}}
    await db_session.commit()

    result = await user_service.reset_field_priority_config(test_user.id)

    # Verify method completes without error (void return)
    assert result is None

    await db_session.refresh(test_user)
    assert test_user.field_priority_config is None


# ============================================================================
# TEST: get_depth_config
# ============================================================================


@pytest.mark.asyncio
async def test_get_depth_config_custom(user_service, test_user, db_session):
    """Test that get_depth_config returns custom config"""
    custom_depth = {"vision_chunking": "full", "memory_last_n_projects": 5, "git_commits": 50}
    test_user.depth_config = custom_depth
    await db_session.commit()

    config = await user_service.get_depth_config(test_user.id)

    assert isinstance(config, dict)
    assert config == custom_depth


@pytest.mark.asyncio
async def test_get_depth_config_defaults(user_service, test_user):
    """Test that get_depth_config returns defaults when no custom config"""
    config = await user_service.get_depth_config(test_user.id)

    assert isinstance(config, dict)
    assert "vision_documents" in config


# ============================================================================
# TEST: update_depth_config
# ============================================================================


@pytest.mark.asyncio
async def test_update_depth_config_success(user_service, test_user, db_session):
    """Test successful depth config update"""
    new_depth = {"vision_documents": "full", "memory_last_n_projects": 10, "git_commits": 100}

    result = await user_service.update_depth_config(user_id=test_user.id, config=new_depth)

    # Verify method completes without error (void return)
    assert result is None

    await db_session.refresh(test_user)
    assert test_user.depth_config == new_depth


@pytest.mark.asyncio
async def test_update_depth_config_validation(user_service, test_user):
    """Test that update_depth_config validates config"""
    invalid_depth = {
        "vision_documents": "invalid_level"  # Invalid
    }

    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_depth_config(user_id=test_user.id, config=invalid_depth)

    assert "invalid" in str(exc_info.value).lower()


# ============================================================================
# TEST: execution_mode persistence
# ============================================================================


@pytest.mark.asyncio
async def test_get_execution_mode_default(user_service, test_user):
    """Execution mode defaults to claude_code when not set."""
    execution_mode = await user_service.get_execution_mode(test_user.id)

    assert execution_mode == "claude_code"


@pytest.mark.asyncio
async def test_update_execution_mode_persists(user_service, test_user, db_session):
    """Execution mode updates persist in depth_config and are retrievable."""
    result = await user_service.update_execution_mode(
        user_id=test_user.id,
        execution_mode="multi_terminal",
    )

    # Verify method completes without error (void return)
    assert result is None

    read_back = await user_service.get_execution_mode(test_user.id)
    assert read_back == "multi_terminal"


@pytest.mark.asyncio
async def test_update_execution_mode_validation(user_service, test_user):
    """Invalid execution mode is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_execution_mode(
            user_id=test_user.id,
            execution_mode="invalid-mode",
        )

    assert "invalid" in str(exc_info.value).lower()


# ============================================================================
# TEST: Exception Handling & Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_user_service_handles_database_errors(user_service, db_session):
    """Test that UserService handles database errors gracefully"""
    pytest.skip("Session close no-op with shared async session; skip graceful error check")
    # Simulate database error by closing session
    await db_session.close()

    with pytest.raises(BaseGiljoError):
        await user_service.list_users()


@pytest.mark.asyncio
async def test_user_service_logging(user_service, test_user, caplog):
    """Test that UserService logs operations"""
    import logging

    caplog.set_level(logging.INFO)

    await user_service.get_user(test_user.id)

    assert any("user" in record.message.lower() for record in caplog.records)
