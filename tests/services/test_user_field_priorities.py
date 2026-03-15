"""
Test suite for user field toggle configuration persistence.

Verifies that field toggle settings from the UI are correctly persisted
to the database with the 'priorities' key structure (v3.0 toggle-only).

Handover 0820: Removed priority integer coupling, toggle-only v3.0.

Updated for:
- 0424j: User.org_id NOT NULL constraint
- 0730: Exception-based error handling patterns
- 0820: Toggle-only v3.0 (removed priority integers)
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.services.user_service import UserService


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
        websocket_manager=None,
        session=db_session,
    )


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key, test_organization):
    """Create test user WITHOUT field toggle configuration"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        org_id=test_organization.id,
        is_active=True,
        field_priority_config=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_with_toggles(db_session, test_tenant_key, test_organization):
    """Create test user WITH field toggle configuration (v3.0 format)"""
    user = User(
        id=str(uuid4()),
        username=f"configuser_{uuid4().hex[:6]}",
        email=f"config_{uuid4().hex[:6]}@example.com",
        password_hash="hashed_password",
        full_name="Configured User",
        role="developer",
        tenant_key=test_tenant_key,
        org_id=test_organization.id,
        is_active=True,
        field_priority_config={
            "version": "3.0",
            "priorities": {
                "product_core": {"toggle": True},
                "vision_documents": {"toggle": True},
                "agent_templates": {"toggle": True},
                "project_description": {"toggle": True},
                "memory_360": {"toggle": True},
                "git_history": {"toggle": False},
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# TEST 1: Field Toggles Persist with Correct Structure
# ============================================================================


@pytest.mark.asyncio
async def test_field_toggles_persist_with_priorities_key(user_service, test_user, db_session):
    """
    TEST 1: Field toggles should persist to database with 'priorities' key.

    USER STORY:
    1. User opens My Settings -> Context -> Field Toggle Configuration
    2. User configures toggles: product_core=on, git_history=off, etc.
    3. User clicks Save
    4. Configuration should be stored in User.field_priority_config JSONB column

    EXPECTED STRUCTURE (v3.0):
    {
        "version": "3.0",
        "priorities": {
            "product_core": {"toggle": true},
            "git_history": {"toggle": false},
            ...
        }
    }
    """
    new_config = {
        "version": "3.0",
        "priorities": {
            "product_core": {"toggle": True},
            "vision_documents": {"toggle": True},
            "agent_templates": {"toggle": True},
            "project_description": {"toggle": True},
            "memory_360": {"toggle": True},
            "git_history": {"toggle": False},
        },
    }

    await user_service.update_field_priority_config(user_id=test_user.id, config=new_config)

    await db_session.refresh(test_user)

    assert test_user.field_priority_config is not None, "field_priority_config should not be None after update"
    assert "priorities" in test_user.field_priority_config, (
        f"Config should have 'priorities' key. Got keys: {test_user.field_priority_config.keys()}"
    )
    assert "fields" not in test_user.field_priority_config, (
        "Config should NOT have 'fields' key - should be 'priorities'"
    )
    assert test_user.field_priority_config["priorities"] == new_config["priorities"], (
        f"Expected priorities {new_config['priorities']}, got {test_user.field_priority_config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_field_toggles_retrieved_with_correct_structure(user_service, user_with_toggles, db_session):
    """
    TEST 1b: Field toggles should be retrieved with 'priorities' key.

    USER STORY:
    1. User already has configured field toggles
    2. User opens My Settings -> Context -> Field Toggle Configuration
    3. UI loads existing configuration
    4. Configuration should have 'priorities' key with toggle booleans
    """
    config = await user_service.get_field_priority_config(user_with_toggles.id)

    assert isinstance(config, dict), "Config should be a dictionary"
    assert "priorities" in config, f"Config should have 'priorities' key. Got keys: {config.keys()}"
    assert "fields" not in config, "Config should NOT have 'fields' key - should be 'priorities'"

    expected_priorities = {
        "product_core": {"toggle": True},
        "vision_documents": {"toggle": True},
        "agent_templates": {"toggle": True},
        "project_description": {"toggle": True},
        "memory_360": {"toggle": True},
        "git_history": {"toggle": False},
    }
    assert config["priorities"] == expected_priorities, (
        f"Expected priorities {expected_priorities}, got {config.get('priorities')}"
    )


@pytest.mark.asyncio
async def test_default_field_toggles_use_priorities_key(user_service, test_user):
    """
    TEST 1c: Default field toggles should also use 'priorities' key.

    USER STORY:
    1. New user has no custom field toggle configuration
    2. User opens My Settings -> Context -> Field Toggle Configuration
    3. UI should show default configuration with 'priorities' key

    Default config uses v3.0 format: {"toggle": bool} per category
    """
    config = await user_service.get_field_priority_config(test_user.id)

    assert isinstance(config, dict), "Config should be a dictionary"
    assert "priorities" in config, f"Default config should have 'priorities' key. Got keys: {config.keys()}"
    assert "fields" not in config, "Default config should NOT have 'fields' key - should be 'priorities'"

    priorities = config["priorities"]
    assert isinstance(priorities, dict), "priorities should be a dict"
    assert len(priorities) > 0, "Default priorities should not be empty"

    for category, toggle_config in priorities.items():
        if isinstance(toggle_config, dict):
            assert "toggle" in toggle_config, f"Missing 'toggle' for category '{category}'"
            assert isinstance(toggle_config["toggle"], bool), (
                f"Toggle for '{category}' must be boolean, got {type(toggle_config['toggle'])}"
            )
        elif isinstance(toggle_config, bool):
            pass  # Flat bool format is acceptable
        else:
            pytest.fail(f"Invalid toggle format for '{category}': {toggle_config}")


@pytest.mark.asyncio
async def test_field_toggles_version_is_3_0(user_service, test_user):
    """
    TEST 1d: Field toggle config should use version 3.0.

    Handover 0820: Version bumped from 2.x to 3.0 (toggle-only, no priority integers).
    """
    new_config = {
        "version": "3.0",
        "priorities": {
            "product_core": {"toggle": True},
            "vision_documents": {"toggle": True},
            "agent_templates": {"toggle": False},
            "project_description": {"toggle": True},
        },
    }

    await user_service.update_field_priority_config(user_id=test_user.id, config=new_config)

    config = await user_service.get_field_priority_config(test_user.id)
    assert config["version"] == "3.0", f"Expected version 3.0, got {config.get('version')}"


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_field_toggles_handles_none_gracefully(user_service, test_user, db_session):
    """
    TEST 1e: When user has field_priority_config=None, should return defaults.
    """
    assert test_user.field_priority_config is None

    config = await user_service.get_field_priority_config(test_user.id)

    assert isinstance(config, dict), "Config should be a dictionary"
    assert "priorities" in config, "Default config should have 'priorities' key"


@pytest.mark.asyncio
async def test_field_toggles_validates_structure(user_service, test_user):
    """
    TEST 1f: Invalid config structure should be rejected.

    v3.0 validation: toggles must be boolean, not integers.
    """
    invalid_config = {
        "version": "3.0",
        "fields": {  # WRONG KEY - should be "priorities"
            "product_core": {"toggle": True}
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_field_priority_config(user_id=test_user.id, config=invalid_config)

    error_message = str(exc_info.value).lower()
    assert "priorities" in error_message or "invalid" in error_message, (
        f"Error should mention 'priorities' or 'invalid'. Got: {exc_info.value}"
    )
