"""
Test suite for user field priorities persistence - TDD Phase 1 (RED)

This test suite verifies that field priority settings from the UI
are correctly persisted to the database with the 'priorities' key structure.

BUG CONTEXT:
- User configures field priorities in My Settings → Context → Field Priority Configuration
- Settings should be stored in User.field_priority_config JSONB column
- Structure should be: {"version": "2.0", "priorities": {...}}
- Bug: Code looks for "fields" key instead of "priorities" key

These tests will initially FAIL to confirm the bug exists.

Handover: Field Priority Bug Fix - Phase 1
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.user_service import UserService

# Use existing fixtures
from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_service(db_manager, db_session, test_tenant_key):
    """Create UserService instance for testing with shared session"""
    return UserService(
        db_manager=db_manager,
        tenant_key=test_tenant_key,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session  # SHARED SESSION for test transaction isolation
    )


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key):
    """Create test user WITHOUT field priority configuration"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        field_priority_config=None  # Start with no config
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_priorities(db_session, test_tenant_key):
    """Create test user WITH field priority configuration (correct structure)"""
    user = User(
        id=str(uuid4()),
        username=f"configuser_{uuid4().hex[:6]}",
        email=f"config_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Configured User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        field_priority_config={
            "version": "2.0",
            "priorities": {  # CORRECT KEY - should be "priorities" not "fields"
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_context": 1,
                "memory_360": 2,
                "git_history": 4
            }
        }
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# TEST 1: Field Priorities Persist with Correct Structure
# ============================================================================

@pytest.mark.asyncio
async def test_field_priorities_persist_with_priorities_key(
    user_service,
    test_user,
    db_session
):
    """
    TEST 1: Field priorities should persist to database with 'priorities' key.

    USER STORY:
    1. User opens My Settings → Context → Field Priority Configuration
    2. User configures priorities: product_core=1, vision_documents=2, etc.
    3. User clicks Save
    4. Configuration should be stored in User.field_priority_config JSONB column

    EXPECTED STRUCTURE:
    {
        "version": "2.0",
        "priorities": {
            "product_core": 1,
            "vision_documents": 2,
            ...
        }
    }

    BUG:
    This test will FAIL if the code uses "fields" key instead of "priorities" key.
    """
    # ARRANGE: Create valid field priority configuration
    new_config = {
        "version": "2.0",
        "priorities": {  # CRITICAL: Must be "priorities" not "fields"
            "product_core": 1,
            "vision_documents": 1,
            "agent_templates": 2,
            "project_context": 1,
            "memory_360": 3,
            "git_history": 4
        }
    }

    # ACT: Update user's field priority configuration
    result = await user_service.update_field_priority_config(
        user_id=test_user.id,
        config=new_config
    )

    # ASSERT: Configuration should be saved successfully
    assert result["success"] is True, "Failed to update field priority config"

    # Refresh user from database to verify persistence
    await db_session.refresh(test_user)

    # CRITICAL ASSERTION 1: Config should exist in database
    assert test_user.field_priority_config is not None, (
        "field_priority_config should not be None after update"
    )

    # CRITICAL ASSERTION 2: Config should have "priorities" key, not "fields"
    assert "priorities" in test_user.field_priority_config, (
        f"Config should have 'priorities' key. "
        f"Got keys: {test_user.field_priority_config.keys()}"
    )

    # CRITICAL ASSERTION 3: Config should NOT have "fields" key
    assert "fields" not in test_user.field_priority_config, (
        "Config should NOT have 'fields' key - should be 'priorities'"
    )

    # CRITICAL ASSERTION 4: Priorities should match saved config
    assert test_user.field_priority_config["priorities"] == new_config["priorities"], (
        f"Expected priorities {new_config['priorities']}, "
        f"got {test_user.field_priority_config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_field_priorities_retrieved_with_correct_structure(
    user_service,
    user_with_priorities,
    db_session
):
    """
    TEST 1b: Field priorities should be retrieved with 'priorities' key.

    USER STORY:
    1. User already has configured field priorities
    2. User opens My Settings → Context → Field Priority Configuration
    3. UI loads existing configuration
    4. Configuration should have 'priorities' key

    BUG:
    This test will FAIL if the code expects "fields" key when reading config.
    """
    # ACT: Retrieve user's field priority configuration
    result = await user_service.get_field_priority_config(user_with_priorities.id)

    # ASSERT: Configuration should be retrieved successfully
    assert result["success"] is True, "Failed to retrieve field priority config"

    # CRITICAL ASSERTION 1: Config should exist
    assert "config" in result, "Response should contain 'config' key"
    config = result["config"]

    # CRITICAL ASSERTION 2: Config should have "priorities" key
    assert "priorities" in config, (
        f"Config should have 'priorities' key. Got keys: {config.keys()}"
    )

    # CRITICAL ASSERTION 3: Config should NOT have "fields" key
    assert "fields" not in config, (
        "Config should NOT have 'fields' key - should be 'priorities'"
    )

    # CRITICAL ASSERTION 4: Priorities should match database
    expected_priorities = {
        "product_core": 1,
        "vision_documents": 2,
        "agent_templates": 3,
        "project_context": 1,
        "memory_360": 2,
        "git_history": 4
    }
    assert config["priorities"] == expected_priorities, (
        f"Expected priorities {expected_priorities}, got {config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_default_field_priorities_use_priorities_key(
    user_service,
    test_user
):
    """
    TEST 1c: Default field priorities should also use 'priorities' key.

    USER STORY:
    1. New user has no custom field priority configuration
    2. User opens My Settings → Context → Field Priority Configuration
    3. UI should show default configuration with 'priorities' key

    BUG:
    This test will FAIL if defaults use "fields" key instead of "priorities".
    """
    # ACT: Retrieve defaults for user without configuration
    result = await user_service.get_field_priority_config(test_user.id)

    # ASSERT: Should return default configuration
    assert result["success"] is True, "Failed to retrieve default config"
    assert "config" in result, "Response should contain default config"

    config = result["config"]

    # CRITICAL ASSERTION 1: Default config should have "priorities" key
    assert "priorities" in config, (
        f"Default config should have 'priorities' key. Got keys: {config.keys()}"
    )

    # CRITICAL ASSERTION 2: Default config should NOT have "fields" key
    assert "fields" not in config, (
        "Default config should NOT have 'fields' key - should be 'priorities'"
    )

    # CRITICAL ASSERTION 3: Default priorities should be valid
    priorities = config["priorities"]
    assert isinstance(priorities, dict), "priorities should be a dict"
    assert len(priorities) > 0, "Default priorities should not be empty"

    # Verify all priorities are valid values (1-4)
    for category, priority in priorities.items():
        assert priority in {1, 2, 3, 4}, (
            f"Invalid priority {priority} for category '{category}'"
        )


@pytest.mark.asyncio
async def test_field_priorities_version_is_2_0(
    user_service,
    test_user
):
    """
    TEST 1d: Field priority config should always have version 2.0.

    This confirms we're using the current config schema version.
    """
    # ARRANGE: Create config with version 2.0
    new_config = {
        "version": "2.0",
        "priorities": {
            "product_core": 1,
            "vision_documents": 2,
            "agent_templates": 3,
            "project_context": 1
        }
    }

    # ACT: Update config
    await user_service.update_field_priority_config(
        user_id=test_user.id,
        config=new_config
    )

    # ASSERT: Retrieved config should have version 2.0
    result = await user_service.get_field_priority_config(test_user.id)

    assert result["success"] is True
    assert result["config"]["version"] == "2.0", (
        f"Expected version 2.0, got {result['config'].get('version')}"
    )


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_field_priorities_handles_none_gracefully(
    user_service,
    test_user,
    db_session
):
    """
    TEST 1e: When user has field_priority_config=None, should return defaults.

    This ensures the system handles missing configuration gracefully.
    """
    # ARRANGE: Verify user has no config
    assert test_user.field_priority_config is None

    # ACT: Retrieve config (should return defaults)
    result = await user_service.get_field_priority_config(test_user.id)

    # ASSERT: Should return default config, not error
    assert result["success"] is True
    assert "config" in result
    assert "priorities" in result["config"]


@pytest.mark.asyncio
async def test_field_priorities_validates_structure(
    user_service,
    test_user
):
    """
    TEST 1f: Invalid config structure should be rejected.

    This ensures validation is working correctly.
    """
    # ARRANGE: Create invalid config (wrong key)
    invalid_config = {
        "version": "2.0",
        "fields": {  # WRONG KEY - should be "priorities"
            "product_core": 1
        }
    }

    # ACT: Try to update with invalid config
    result = await user_service.update_field_priority_config(
        user_id=test_user.id,
        config=invalid_config
    )

    # ASSERT: Should be rejected
    # NOTE: This might pass if validation doesn't check for correct key
    # The test documents expected behavior
    assert result["success"] is False, (
        "Config with 'fields' key should be rejected - should use 'priorities'"
    )
    assert "priorities" in result.get("error", "").lower() or "invalid" in result.get("error", "").lower()
