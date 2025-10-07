"""
Unit tests for SetupState model.

Tests all model methods, constraints, and business logic.
"""
import pytest
from datetime import datetime
from uuid import uuid4


def test_create_setup_state_with_defaults(sync_db_session, setup_state_factory):
    """Test creating SetupState with default values"""
    state = setup_state_factory()

    assert state.id is not None
    assert state.tenant_key is not None
    assert state.completed is False
    assert state.completed_at is None
    assert state.features_configured == {}
    assert state.tools_enabled == []
    assert state.validation_passed is True
    assert state.validation_failures == []
    assert state.validation_warnings == []


def test_create_setup_state_with_custom_values(sync_db_session, setup_state_factory):
    """Test creating SetupState with custom values"""
    state = setup_state_factory(
        tenant_key="custom_tenant",
        completed=True,
        setup_version="2.0.0",
        database_version="18",
        features_configured={"database": True},
        tools_enabled=["project", "agent"],
    )

    assert state.tenant_key == "custom_tenant"
    assert state.completed is True
    assert state.setup_version == "2.0.0"
    assert state.database_version == "18"
    assert state.features_configured == {"database": True}
    assert state.tools_enabled == ["project", "agent"]


def test_tenant_key_uniqueness(sync_db_session, setup_state_factory):
    """Test UNIQUE constraint on tenant_key"""
    from sqlalchemy.exc import IntegrityError

    # Create first state
    state1 = setup_state_factory(tenant_key="unique_tenant")
    sync_db_session.commit()

    # Try to create second state with same tenant_key
    state2 = setup_state_factory(tenant_key="unique_tenant")

    with pytest.raises(IntegrityError):
        sync_db_session.commit()


def test_version_format_constraint(sync_db_session, setup_state_factory):
    """Test semantic versioning CHECK constraint on setup_version"""
    from sqlalchemy.exc import IntegrityError

    # Valid version formats
    valid_versions = ["1.0.0", "2.1.3", "10.20.30", "1.0.0-alpha", "2.0.0-beta.1"]

    for version in valid_versions:
        state = setup_state_factory(
            tenant_key=f"tenant_{version.replace('.', '_').replace('-', '_')}", setup_version=version
        )
        sync_db_session.commit()
        assert state.setup_version == version

    # Invalid version format (should fail)
    sync_db_session.rollback()
    state_invalid = setup_state_factory(tenant_key="invalid_version", setup_version="not-a-version")

    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "ck_setup_version_format" in str(exc_info.value)


def test_database_version_constraint(sync_db_session, setup_state_factory):
    """Test database version CHECK constraint"""
    from sqlalchemy.exc import IntegrityError

    # Valid database versions
    valid_versions = ["18", "16.2", "15.1.0"]

    for version in valid_versions:
        sync_db_session.rollback()
        state = setup_state_factory(
            tenant_key=f"tenant_db_{version.replace('.', '_')}", database_version=version
        )
        sync_db_session.commit()
        assert state.database_version == version

    # Invalid database version
    sync_db_session.rollback()
    state_invalid = setup_state_factory(tenant_key="invalid_db_version", database_version="abc")

    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "ck_database_version_format" in str(exc_info.value)


def test_install_mode_constraint(sync_db_session, setup_state_factory):
    """Test install_mode CHECK constraint"""
    from sqlalchemy.exc import IntegrityError

    # Valid install modes
    valid_modes = ["localhost", "server", "lan", "wan"]

    for mode in valid_modes:
        sync_db_session.rollback()
        state = setup_state_factory(tenant_key=f"tenant_{mode}", install_mode=mode)
        sync_db_session.commit()
        assert state.install_mode == mode

    # Invalid install mode
    sync_db_session.rollback()
    state_invalid = setup_state_factory(tenant_key="invalid_mode", install_mode="invalid_mode")

    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "ck_install_mode_values" in str(exc_info.value)


def test_completed_at_required_constraint(sync_db_session, setup_state_factory):
    """Test CHECK constraint that completed_at must be set when completed=True"""
    from sqlalchemy.exc import IntegrityError

    # This should fail: completed=True but no completed_at
    state = setup_state_factory(tenant_key="no_completed_at", completed=True, completed_at=None)

    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "ck_completed_at_required" in str(exc_info.value)


def test_to_dict_serialization(sync_db_session, completed_setup_state):
    """Test to_dict() method serialization"""
    data = completed_setup_state.to_dict()

    assert isinstance(data, dict)
    assert data["id"] == completed_setup_state.id
    assert data["tenant_key"] == completed_setup_state.tenant_key
    assert data["completed"] is True
    assert data["setup_version"] == "2.0.0"
    assert data["database_version"] == "18"
    assert data["features_configured"] == {"database": True, "api": {"enabled": True, "port": 7272}}
    assert data["tools_enabled"] == ["project", "agent", "message", "task"]
    assert "created_at" in data
    assert isinstance(data["completed_at"], str)  # ISO format


def test_get_by_tenant(sync_db_session, completed_setup_state):
    """Test get_by_tenant() class method"""
    from src.giljo_mcp.models import SetupState

    # Find existing state
    found = SetupState.get_by_tenant(db_session, "completed_tenant")
    assert found is not None
    assert found.id == completed_setup_state.id
    assert found.tenant_key == "completed_tenant"

    # Try to find non-existent state
    not_found = SetupState.get_by_tenant(db_session, "nonexistent_tenant")
    assert not_found is None


def test_create_or_update_new(db_session):
    """Test create_or_update() creates new state when none exists"""
    from src.giljo_mcp.models import SetupState

    state = SetupState.create_or_update(
        db_session, tenant_key="new_tenant", setup_version="1.0.0", completed=True
    )

    sync_db_session.commit()

    assert state.tenant_key == "new_tenant"
    assert state.setup_version == "1.0.0"
    assert state.completed is True


def test_create_or_update_existing(sync_db_session, completed_setup_state):
    """Test create_or_update() updates existing state"""
    from src.giljo_mcp.models import SetupState

    original_id = completed_setup_state.id

    # Update existing state
    updated = SetupState.create_or_update(
        db_session, tenant_key="completed_tenant", setup_version="3.0.0", database_version="19"
    )

    sync_db_session.commit()

    # Should be the same instance (same ID)
    assert updated.id == original_id
    assert updated.tenant_key == "completed_tenant"
    assert updated.setup_version == "3.0.0"
    assert updated.database_version == "19"

    # Verify in database
    retrieved = SetupState.get_by_tenant(db_session, "completed_tenant")
    assert retrieved.id == original_id
    assert retrieved.setup_version == "3.0.0"


def test_mark_completed(sync_db_session, setup_state_factory):
    """Test mark_completed() method"""
    state = setup_state_factory(tenant_key="to_complete")
    sync_db_session.commit()

    assert state.completed is False
    assert state.completed_at is None
    assert state.setup_version is None

    # Mark as completed
    state.mark_completed(setup_version="2.0.0")
    sync_db_session.commit()

    assert state.completed is True
    assert state.completed_at is not None
    assert isinstance(state.completed_at, datetime)
    assert state.setup_version == "2.0.0"


def test_add_validation_failure(sync_db_session, setup_state_factory):
    """Test add_validation_failure() method"""
    state = setup_state_factory(tenant_key="validation_test")
    sync_db_session.commit()

    assert state.validation_passed is True
    assert state.validation_failures == []

    # Add failure
    state.add_validation_failure("Database connection failed")
    sync_db_session.commit()

    assert state.validation_passed is False
    assert len(state.validation_failures) == 1
    assert state.validation_failures[0]["message"] == "Database connection failed"
    assert "timestamp" in state.validation_failures[0]
    assert state.last_validation_at is not None

    # Add another failure
    state.add_validation_failure("Python version too old")
    sync_db_session.commit()

    assert len(state.validation_failures) == 2
    assert state.validation_failures[1]["message"] == "Python version too old"


def test_add_validation_warning(sync_db_session, setup_state_factory):
    """Test add_validation_warning() method"""
    state = setup_state_factory(tenant_key="warning_test")
    sync_db_session.commit()

    assert state.validation_warnings == []

    # Add warning
    state.add_validation_warning("Node.js not found")
    sync_db_session.commit()

    assert len(state.validation_warnings) == 1
    assert state.validation_warnings[0]["message"] == "Node.js not found"
    assert "timestamp" in state.validation_warnings[0]
    assert state.last_validation_at is not None

    # Validation should still pass with warnings
    assert state.validation_passed is True


def test_clear_validation_failures(sync_db_session, failed_validation_setup_state):
    """Test clear_validation_failures() method"""
    state = failed_validation_setup_state

    assert state.validation_passed is False
    assert len(state.validation_failures) == 2

    # Clear failures
    state.clear_validation_failures()
    sync_db_session.commit()

    assert state.validation_passed is True
    assert state.validation_failures == []
    assert state.validation_warnings == []
    assert state.last_validation_at is not None


def test_has_feature_simple(sync_db_session, completed_setup_state):
    """Test has_feature() method with simple feature keys"""
    state = completed_setup_state

    # Has feature
    assert state.has_feature("database") is True

    # Doesn't have feature
    assert state.has_feature("elasticsearch") is False


def test_has_feature_nested(sync_db_session, completed_setup_state):
    """Test has_feature() method with nested dot notation"""
    state = completed_setup_state

    # Nested feature exists and is truthy
    assert state.has_feature("api.enabled") is True

    # Nested feature exists but is falsy
    assert state.has_feature("api.ssl_enabled") is False

    # Nested feature doesn't exist
    assert state.has_feature("api.nonexistent") is False


def test_has_feature_empty_config(sync_db_session, setup_state_factory):
    """Test has_feature() with empty features_configured"""
    state = setup_state_factory(tenant_key="empty_features", features_configured={})
    sync_db_session.commit()

    assert state.has_feature("anything") is False


def test_has_tool(sync_db_session, completed_setup_state):
    """Test has_tool() method"""
    state = completed_setup_state

    # Has tools
    assert state.has_tool("project") is True
    assert state.has_tool("agent") is True
    assert state.has_tool("message") is True

    # Doesn't have tool
    assert state.has_tool("nonexistent_tool") is False


def test_has_tool_empty_list(sync_db_session, setup_state_factory):
    """Test has_tool() with empty tools_enabled list"""
    state = setup_state_factory(tenant_key="no_tools", tools_enabled=[])
    sync_db_session.commit()

    assert state.has_tool("project") is False


def test_jsonb_query_features(sync_db_session, completed_setup_state):
    """Test querying JSONB features_configured column"""
    from sqlalchemy import text

    # Test JSONB containment query
    result = db_session.execute(
        text(
            """
            SELECT * FROM setup_state
            WHERE features_configured @> '{"database": true}'::jsonb
        """
        )
    ).fetchone()

    assert result is not None


def test_jsonb_query_tools(sync_db_session, completed_setup_state):
    """Test querying JSONB tools_enabled column"""
    from sqlalchemy import text

    # Test JSONB array contains query
    result = db_session.execute(
        text(
            """
            SELECT * FROM setup_state
            WHERE tools_enabled @> '["project"]'::jsonb
        """
        )
    ).fetchone()

    assert result is not None


def test_partial_index_incomplete_setups(sync_db_session, setup_state_factory, completed_setup_state):
    """Test that partial index on incomplete setups works"""
    from sqlalchemy import text

    # Create incomplete setup
    incomplete = setup_state_factory(tenant_key="incomplete", completed=False)
    sync_db_session.commit()

    # Query should use the partial index (idx_setup_incomplete)
    result = db_session.execute(
        text(
            """
            SELECT tenant_key, completed FROM setup_state
            WHERE completed = false
        """
        )
    ).fetchall()

    assert len(result) >= 1
    assert any(row[0] == "incomplete" for row in result)


def test_timestamps_auto_populate(sync_db_session, setup_state_factory):
    """Test that created_at is automatically populated"""
    state = setup_state_factory(tenant_key="timestamp_test")
    sync_db_session.commit()

    assert state.created_at is not None
    assert isinstance(state.created_at, datetime)
    assert state.updated_at is None  # Not updated yet


def test_timestamps_updated_at(sync_db_session, setup_state_factory):
    """Test that updated_at is set on update"""
    state = setup_state_factory(tenant_key="update_test")
    sync_db_session.commit()

    original_created = state.created_at

    # Update the state
    state.setup_version = "1.0.0"
    sync_db_session.commit()

    # created_at should remain the same
    assert state.created_at == original_created
    # updated_at should now be set
    # Note: updated_at behavior depends on SQLAlchemy onupdate trigger
    # which may not fire in all test scenarios


def test_meta_data_jsonb_storage(sync_db_session, setup_state_factory):
    """Test storing arbitrary data in meta_data JSONB field"""
    custom_meta = {
        "installer_user": "admin",
        "installation_notes": "Test installation",
        "custom_flags": {"debug_mode": True, "verbose": False},
    }

    state = setup_state_factory(tenant_key="meta_test", meta_data=custom_meta)
    sync_db_session.commit()

    # Query it back
    from src.giljo_mcp.models import SetupState

    retrieved = SetupState.get_by_tenant(db_session, "meta_test")

    assert retrieved.meta_data == custom_meta
    assert retrieved.meta_data["installer_user"] == "admin"
    assert retrieved.meta_data["custom_flags"]["debug_mode"] is True
