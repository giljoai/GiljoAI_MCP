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

Updated for:
- 0424j: User.org_id NOT NULL constraint
- 0730: Exception-based error handling patterns

Handover: Field Priority Bug Fix - Phase 1
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.services.user_service import UserService


# Use existing fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def test_organization(db_session, test_tenant_key):
    """Create test organization for users (0424j: User.org_id NOT NULL)"""
    org = Organization(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name=f"Test Org {test_tenant_key}",
        slug=f"test-org-{test_tenant_key.replace('_', '-')}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def user_service(db_manager, db_session, test_tenant_key):
    """Create UserService instance for testing with shared session"""
    return UserService(
        db_manager=db_manager,
        tenant_key=test_tenant_key,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session,  # SHARED SESSION for test transaction isolation
    )


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key, test_organization):
    """Create test user WITHOUT field priority configuration"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        org_id=test_organization.id,  # 0424j: User.org_id NOT NULL
        is_active=True,
        field_priority_config=None,  # Start with no config
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_priorities(db_session, test_tenant_key, test_organization):
    """Create test user WITH field priority configuration (correct structure)"""
    user = User(
        id=str(uuid4()),
        username=f"configuser_{uuid4().hex[:6]}",
        email=f"config_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Configured User",
        role="developer",
        tenant_key=test_tenant_key,
        org_id=test_organization.id,  # 0424j: User.org_id NOT NULL
        is_active=True,
        field_priority_config={
            "version": "2.0",
            "priorities": {  # CORRECT KEY - should be "priorities" not "fields"
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4,
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# TEST 1: Field Priorities Persist with Correct Structure
# ============================================================================


@pytest.mark.asyncio
async def test_field_priorities_persist_with_priorities_key(user_service, test_user, db_session):
    """
    TEST 1: Field priorities should persist to database with 'priorities' key.

    USER STORY:
    1. User opens My Settings -> Context -> Field Priority Configuration
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

    NOTE: Service uses exception-based error handling (0730 refactoring).
    Success = no exception raised, returns None.
    """
    # ARRANGE: Create valid field priority configuration
    new_config = {
        "version": "2.0",
        "priorities": {  # CRITICAL: Must be "priorities" not "fields"
            "product_core": 1,
            "vision_documents": 1,
            "agent_templates": 2,
            "project_description": 1,
            "memory_360": 3,
            "git_history": 4,
        },
    }

    # ACT: Update user's field priority configuration
    # Exception-based pattern: no exception = success (void return)
    await user_service.update_field_priority_config(user_id=test_user.id, config=new_config)

    # Refresh user from database to verify persistence
    await db_session.refresh(test_user)

    # CRITICAL ASSERTION 1: Config should exist in database
    assert test_user.field_priority_config is not None, "field_priority_config should not be None after update"

    # CRITICAL ASSERTION 2: Config should have "priorities" key, not "fields"
    assert "priorities" in test_user.field_priority_config, (
        f"Config should have 'priorities' key. Got keys: {test_user.field_priority_config.keys()}"
    )

    # CRITICAL ASSERTION 3: Config should NOT have "fields" key
    assert "fields" not in test_user.field_priority_config, (
        "Config should NOT have 'fields' key - should be 'priorities'"
    )

    # CRITICAL ASSERTION 4: Priorities should match saved config
    assert test_user.field_priority_config["priorities"] == new_config["priorities"], (
        f"Expected priorities {new_config['priorities']}, got {test_user.field_priority_config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_field_priorities_retrieved_with_correct_structure(user_service, user_with_priorities, db_session):
    """
    TEST 1b: Field priorities should be retrieved with 'priorities' key.

    USER STORY:
    1. User already has configured field priorities
    2. User opens My Settings -> Context -> Field Priority Configuration
    3. UI loads existing configuration
    4. Configuration should have 'priorities' key

    NOTE: Service uses exception-based error handling (0730 refactoring).
    get_field_priority_config returns the config dict directly (not wrapped).
    """
    # ACT: Retrieve user's field priority configuration
    # Exception-based pattern: returns config dict directly
    config = await user_service.get_field_priority_config(user_with_priorities.id)

    # ASSERT: Config should be a dict with expected structure
    assert isinstance(config, dict), "Config should be a dictionary"

    # CRITICAL ASSERTION 1: Config should have "priorities" key
    assert "priorities" in config, f"Config should have 'priorities' key. Got keys: {config.keys()}"

    # CRITICAL ASSERTION 2: Config should NOT have "fields" key
    assert "fields" not in config, "Config should NOT have 'fields' key - should be 'priorities'"

    # CRITICAL ASSERTION 3: Priorities should match database
    expected_priorities = {
        "product_core": 1,
        "vision_documents": 2,
        "agent_templates": 3,
        "project_description": 1,
        "memory_360": 2,
        "git_history": 4,
    }
    assert config["priorities"] == expected_priorities, (
        f"Expected priorities {expected_priorities}, got {config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_default_field_priorities_use_priorities_key(user_service, test_user):
    """
    TEST 1c: Default field priorities should also use 'priorities' key.

    USER STORY:
    1. New user has no custom field priority configuration
    2. User opens My Settings -> Context -> Field Priority Configuration
    3. UI should show default configuration with 'priorities' key

    NOTE: Service uses exception-based error handling (0730 refactoring).
    get_field_priority_config returns the config dict directly (not wrapped).

    Default priorities use v2.1 nested format: {"toggle": True, "priority": 1}
    """
    # ACT: Retrieve defaults for user without configuration
    # Exception-based pattern: returns config dict directly
    config = await user_service.get_field_priority_config(test_user.id)

    # ASSERT: Config should be a dict with expected structure
    assert isinstance(config, dict), "Config should be a dictionary"

    # CRITICAL ASSERTION 1: Default config should have "priorities" key
    assert "priorities" in config, f"Default config should have 'priorities' key. Got keys: {config.keys()}"

    # CRITICAL ASSERTION 2: Default config should NOT have "fields" key
    assert "fields" not in config, "Default config should NOT have 'fields' key - should be 'priorities'"

    # CRITICAL ASSERTION 3: Default priorities should be valid
    priorities = config["priorities"]
    assert isinstance(priorities, dict), "priorities should be a dict"
    assert len(priorities) > 0, "Default priorities should not be empty"

    # Verify all priorities are valid
    # v2.1 format: {"toggle": bool, "priority": int} per category
    # v2.0 format: int per category (for backwards compatibility)
    for category, priority_config in priorities.items():
        if isinstance(priority_config, dict):
            # v2.1 nested format
            assert "toggle" in priority_config, f"Missing 'toggle' for category '{category}'"
            assert "priority" in priority_config, f"Missing 'priority' for category '{category}'"
            priority_value = priority_config["priority"]
            assert priority_value in {1, 2, 3, 4}, f"Invalid priority {priority_value} for category '{category}'"
        else:
            # v2.0 simple format (backwards compatibility)
            assert priority_config in {1, 2, 3, 4}, f"Invalid priority {priority_config} for category '{category}'"


@pytest.mark.asyncio
async def test_field_priorities_version_is_2_0(user_service, test_user):
    """
    TEST 1d: Field priority config should always have version 2.0.

    This confirms we're using the current config schema version.

    NOTE: Service uses exception-based error handling (0730 refactoring).
    """
    # ARRANGE: Create config with version 2.0
    new_config = {
        "version": "2.0",
        "priorities": {"product_core": 1, "vision_documents": 2, "agent_templates": 3, "project_description": 1},
    }

    # ACT: Update config (void return on success)
    await user_service.update_field_priority_config(user_id=test_user.id, config=new_config)

    # ASSERT: Retrieved config should have version 2.0
    config = await user_service.get_field_priority_config(test_user.id)

    assert config["version"] == "2.0", f"Expected version 2.0, got {config.get('version')}"


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_field_priorities_handles_none_gracefully(user_service, test_user, db_session):
    """
    TEST 1e: When user has field_priority_config=None, should return defaults.

    This ensures the system handles missing configuration gracefully.

    NOTE: Service uses exception-based error handling (0730 refactoring).
    get_field_priority_config returns the config dict directly (not wrapped).
    """
    # ARRANGE: Verify user has no config
    assert test_user.field_priority_config is None

    # ACT: Retrieve config (should return defaults)
    config = await user_service.get_field_priority_config(test_user.id)

    # ASSERT: Should return default config, not error
    assert isinstance(config, dict), "Config should be a dictionary"
    assert "priorities" in config, "Default config should have 'priorities' key"


@pytest.mark.asyncio
async def test_field_priorities_validates_structure(user_service, test_user):
    """
    TEST 1f: Invalid config structure should be rejected.

    This ensures validation is working correctly.

    NOTE: Service uses exception-based error handling (0730 refactoring).
    Invalid config raises ValidationError instead of returning error dict.
    """
    # ARRANGE: Create invalid config (wrong key)
    invalid_config = {
        "version": "2.0",
        "fields": {  # WRONG KEY - should be "priorities"
            "product_core": 1
        },
    }

    # ACT & ASSERT: Should raise ValidationError for invalid config
    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_field_priority_config(user_id=test_user.id, config=invalid_config)

    # Verify the error message mentions the issue
    error_message = str(exc_info.value).lower()
    assert "priorities" in error_message or "invalid" in error_message, (
        f"Error should mention 'priorities' or 'invalid'. Got: {exc_info.value}"
    )
