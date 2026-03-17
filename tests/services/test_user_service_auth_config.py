"""
Test suite for UserService authentication, validation, and configuration.

Split from test_user_service.py during test reorganization.
Covers: change_password, reset_password, check_username_exists, check_email_exists,
verify_password, field_priority_config, depth_config, execution_mode, edge cases.

Shared fixtures (test_tenant_key, user_service, test_user, admin_user) are
provided by tests/services/conftest.py.
"""

from uuid import uuid4

import pytest
import bcrypt

from src.giljo_mcp.exceptions import (
    AuthenticationError,
    ValidationError,
)
from src.giljo_mcp.models.auth import User


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
    assert bcrypt.checkpw(new_password.encode("utf-8"), test_user.password_hash.encode("utf-8"))


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
    assert bcrypt.checkpw(new_password.encode("utf-8"), test_user.password_hash.encode("utf-8"))


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
    assert bcrypt.checkpw("GiljoMCP".encode("utf-8"), test_user.password_hash.encode("utf-8"))
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
    assert config["version"] in ["2.0", "2.1", "3.0"]  # Version may vary
    assert "priorities" in config


# ============================================================================
# TEST: update_field_priority_config
# ============================================================================


@pytest.mark.asyncio
async def test_update_field_priority_config_success(user_service, test_user, db_session):
    """Test successful field priority config update"""
    new_config = {
        "version": "3.0",
        "priorities": {"product_core": True, "vision_documents": True, "agent_templates": False, "project_description": True},
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
    # Merge behavior: updated keys reflect new values, unmentioned keys preserved
    for key, value in new_depth.items():
        assert test_user.depth_config[key] == value
    # execution_mode must survive a depth-only update
    assert "execution_mode" in test_user.depth_config


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
async def test_user_service_logging(user_service, test_user, caplog):
    """Test that UserService logs operations"""
    import logging

    caplog.set_level(logging.INFO)

    await user_service.get_user(test_user.id)

    assert any("user" in record.message.lower() for record in caplog.records)
