"""
Unit tests for SetupStateManager.

Following TDD principles: Tests written BEFORE implementation.
Tests all aspects of hybrid file/database storage, version tracking,
state validation, and multi-tenant isolation.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4


class TestBootstrapPhase:
    """Tests for file-based storage during bootstrap phase (no database)."""

    def test_get_state_no_file_returns_default(self, tmp_path):
        """When no setup state file exists, return default NOT_STARTED state"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        # Override home directory to temp path
        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="test_tenant")
            state = manager.get_state()

            assert state is not None
            assert state.get("completed") is False
            assert state.get("tenant_key") == "test_tenant"
            assert state.get("setup_version") is None

    def test_mark_completed_creates_file(self, tmp_path):
        """When marking setup complete, file is created with correct structure"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="test_tenant")
            manager.mark_completed(setup_version="2.0.0")

            # Check file was created
            state_file = tmp_path / ".giljo-mcp" / "setup_state.json"
            assert state_file.exists()

            # Check file contents
            with open(state_file, 'r') as f:
                data = json.load(f)

            assert data["completed"] is True
            assert data["setup_version"] == "2.0.0"
            assert data["tenant_key"] == "test_tenant"
            assert "completed_at" in data

    def test_file_permissions_secure(self, tmp_path):
        """File should be created with 0600 permissions (owner read/write only)"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        import platform

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="test_tenant")
            manager.mark_completed(setup_version="2.0.0")

            state_file = tmp_path / ".giljo-mcp" / "setup_state.json"

            # Check permissions (Unix only - skip on Windows)
            if platform.system() != "Windows":
                import os
                import stat
                file_stat = os.stat(state_file)
                file_mode = stat.S_IMODE(file_stat.st_mode)
                assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    def test_directory_created_if_missing(self, tmp_path):
        """Should create ~/.giljo-mcp directory if it doesn't exist"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="test_tenant")
            manager.mark_completed()

            giljo_dir = tmp_path / ".giljo-mcp"
            assert giljo_dir.exists()
            assert giljo_dir.is_dir()

    def test_update_state_modifies_file(self, tmp_path):
        """Updating state should modify the existing file"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="test_tenant")
            manager.mark_completed(setup_version="1.0.0")

            # Update state
            manager.update_state(setup_version="2.0.0", database_version="18")

            # Verify file was updated
            state_file = tmp_path / ".giljo-mcp" / "setup_state.json"
            with open(state_file, 'r') as f:
                data = json.load(f)

            assert data["setup_version"] == "2.0.0"
            assert data["database_version"] == "18"

    def test_malformed_json_returns_default(self, tmp_path):
        """If JSON is malformed, should log error and return default state"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create malformed JSON file
            giljo_dir = tmp_path / ".giljo-mcp"
            giljo_dir.mkdir(parents=True, exist_ok=True)
            state_file = giljo_dir / "setup_state.json"
            state_file.write_text("{this is not valid json}")

            manager = SetupStateManager(tenant_key="test_tenant")
            state = manager.get_state()

            # Should return default state
            assert state.get("completed") is False


class TestDatabasePhase:
    """Tests for database-based storage after migration."""

    def test_get_state_from_database(self, sync_db_session, setup_state_factory):
        """When database available, read state from setup_state table"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"db_tenant_{uuid4().hex[:8]}"

        # Create database state
        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="2.0.0"
        )
        sync_db_session.commit()

        # Manager should read from database
        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )
        state = manager.get_state()

        assert state["completed"] is True
        assert state["setup_version"] == "2.0.0"
        assert state["tenant_key"] == tenant_key

    def test_mark_completed_updates_database(self, sync_db_session, setup_state_factory):
        """When marking complete with database, update database row"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from uuid import uuid4

        tenant_key = f"db_tenant_mark_{uuid4().hex[:8]}"

        # Create incomplete state
        db_state = setup_state_factory(tenant_key=tenant_key, completed=False)
        sync_db_session.commit()

        # Mark as completed
        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )
        manager.mark_completed(setup_version="2.0.0")

        # Refresh and verify
        sync_db_session.refresh(db_state)
        assert db_state.completed is True
        assert db_state.setup_version == "2.0.0"
        assert db_state.completed_at is not None

    def test_database_creates_row_if_missing(self, sync_db_session):
        """If no database row exists, create one when marking completed"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from src.giljo_mcp.models import SetupState
        from uuid import uuid4

        tenant_key = f"new_tenant_{uuid4().hex[:8]}"

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )
        manager.mark_completed(setup_version="2.0.0")

        # Verify row was created
        state = SetupState.get_by_tenant(sync_db_session, tenant_key)
        assert state is not None
        assert state.completed is True
        assert state.setup_version == "2.0.0"


class TestHybridFallback:
    """Tests for hybrid storage with database fallback."""

    def test_fallback_to_file_on_database_error(self, tmp_path):
        """When database unavailable, fall back to file storage"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        # Mock database session that raises error
        mock_session = Mock()
        mock_session.query.side_effect = Exception("Database connection failed")

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(
                tenant_key="test_tenant",
                db_session=mock_session
            )

            # Should still work via file
            manager.mark_completed(setup_version="2.0.0")
            state = manager.get_state()

            assert state["completed"] is True
            assert state["setup_version"] == "2.0.0"

    def test_migrate_from_file_to_database(self, tmp_path, sync_db_session):
        """When database becomes available, migrate file state to database"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            # Step 1: Create file-based state (no database)
            manager_file = SetupStateManager(tenant_key="migrate_tenant")
            manager_file.mark_completed(setup_version="1.0.0")

            # Verify file exists
            state_file = tmp_path / ".giljo-mcp" / "setup_state.json"
            assert state_file.exists()

            # Step 2: Create manager with database connection
            manager_db = SetupStateManager(
                tenant_key="migrate_tenant",
                db_session=sync_db_session
            )

            # Migrate from file to database
            manager_db.migrate_file_to_database()

            # Verify database has the state
            from src.giljo_mcp.models import SetupState
            state = SetupState.get_by_tenant(sync_db_session, "migrate_tenant")
            assert state is not None
            assert state.completed is True
            assert state.setup_version == "1.0.0"

    def test_prefer_database_over_file(self, tmp_path, sync_db_session, setup_state_factory):
        """When both exist, prefer database state over file state"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"conflict_tenant_{uuid4().hex[:8]}"

        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create file state
            manager_file = SetupStateManager(tenant_key=tenant_key)
            manager_file.mark_completed(setup_version="1.0.0")

            # Create database state (different version)
            db_state = setup_state_factory(
                tenant_key=tenant_key,
                completed=True,
                completed_at=datetime.utcnow(),
                setup_version="2.0.0"
            )
            sync_db_session.commit()

            # Manager should prefer database
            manager = SetupStateManager(
                tenant_key=tenant_key,
                db_session=sync_db_session
            )
            state = manager.get_state()

            assert state["setup_version"] == "2.0.0"  # Database version


class TestVersionTracking:
    """Tests for version tracking and validation."""

    def test_detect_version_mismatch(self, sync_db_session, setup_state_factory):
        """When setup_version differs from current, requires_migration returns True"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"version_tenant_mismatch_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="1.0.0"
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session,
            current_version="2.0.0"
        )

        assert manager.requires_migration() is True

    def test_no_migration_needed_when_versions_match(self, sync_db_session, setup_state_factory):
        """When versions match, requires_migration returns False"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"version_tenant_match_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="2.0.0"
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session,
            current_version="2.0.0"
        )

        assert manager.requires_migration() is False

    def test_validate_state_checks_versions(self, sync_db_session, setup_state_factory):
        """validate_state should check version compatibility"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"version_tenant_validate_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="1.0.0",
            database_version="17"
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session,
            current_version="2.0.0",
            required_db_version="18"
        )

        is_valid, errors = manager.validate_state()

        assert is_valid is False
        assert len(errors) > 0
        assert any("version" in error.lower() for error in errors)

    def test_migrate_state_updates_versions(self, sync_db_session, setup_state_factory):
        """When migrating state, all version fields are updated"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"migrate_version_tenant_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="1.0.0",
            database_version="17"
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session,
            current_version="2.0.0"
        )

        manager.migrate_state(
            new_setup_version="2.0.0",
            new_database_version="18"
        )

        # Refresh and verify
        sync_db_session.refresh(db_state)
        assert db_state.setup_version == "2.0.0"
        assert db_state.database_version == "18"


class TestStateMachine:
    """Tests for state machine transitions."""

    def test_transition_not_started_to_in_progress(self, sync_db_session):
        """Valid transition: NOT_STARTED → IN_PROGRESS"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager = SetupStateManager(
            tenant_key="state_tenant",
            db_session=sync_db_session
        )

        # Start setup
        manager.update_state(install_mode="localhost")
        state = manager.get_state()

        assert state["completed"] is False
        assert state["install_mode"] == "localhost"

    def test_transition_in_progress_to_completed(self, sync_db_session, setup_state_factory):
        """Valid transition: IN_PROGRESS → COMPLETED"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from uuid import uuid4

        tenant_key = f"state_tenant_transition_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=False,
            install_mode="localhost"
        )
        sync_db_session.commit()

        # Store original ID for verification
        original_id = db_state.id

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )

        # Complete setup
        manager.mark_completed(setup_version="2.0.0")

        # Refresh to get updated data
        sync_db_session.refresh(db_state)
        state = manager.get_state()
        assert state["completed"] is True
        assert db_state.completed is True

    def test_validation_state_tracking(self, sync_db_session, setup_state_factory):
        """Track validation state through setup process"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from uuid import uuid4

        tenant_key = f"validation_tenant_{uuid4().hex[:8]}"

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )

        # Add validation failures
        manager.add_validation_failure("Database connection failed")
        manager.add_validation_warning("Node.js not found")

        state = manager.get_state()
        assert state["validation_passed"] is False
        assert len(state["validation_failures"]) == 1
        assert len(state["validation_warnings"]) == 1


class TestMultiTenantIsolation:
    """Tests for multi-tenant isolation."""

    def test_different_tenants_have_separate_states(self, sync_db_session):
        """Each tenant should have its own isolated state"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        # Tenant 1
        manager1 = SetupStateManager(tenant_key="tenant1", db_session=sync_db_session)
        manager1.mark_completed(setup_version="1.0.0")

        # Tenant 2
        manager2 = SetupStateManager(tenant_key="tenant2", db_session=sync_db_session)
        manager2.mark_completed(setup_version="2.0.0")

        # Verify isolation
        state1 = manager1.get_state()
        state2 = manager2.get_state()

        assert state1["tenant_key"] == "tenant1"
        assert state2["tenant_key"] == "tenant2"
        assert state1["setup_version"] == "1.0.0"
        assert state2["setup_version"] == "2.0.0"

    def test_tenant_cannot_access_other_tenant_state(self, sync_db_session, setup_state_factory):
        """Tenant should not be able to read another tenant's state"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant1 = f"tenant1_{uuid4().hex[:8]}"
        tenant2 = f"tenant2_{uuid4().hex[:8]}"

        # Create state for tenant1
        db_state = setup_state_factory(
            tenant_key=tenant1,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="1.0.0"
        )
        sync_db_session.commit()

        # Try to access as tenant2
        manager2 = SetupStateManager(tenant_key=tenant2, db_session=sync_db_session)
        state2 = manager2.get_state()

        # Should get default state, not tenant1's state
        assert state2["tenant_key"] == tenant2
        assert state2["completed"] is False
        assert state2["setup_version"] is None


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_handle_file_permission_error(self, tmp_path):
        """Handle gracefully when file cannot be written due to permissions"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        import platform

        if platform.system() == "Windows":
            pytest.skip("Permission tests not reliable on Windows")

        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create directory with no write permissions
            giljo_dir = tmp_path / ".giljo-mcp"
            giljo_dir.mkdir(parents=True, exist_ok=True)
            import os
            os.chmod(giljo_dir, 0o444)  # Read-only

            manager = SetupStateManager(tenant_key="test_tenant")

            # Should not crash, but log error
            with pytest.raises(PermissionError):
                manager.mark_completed(setup_version="2.0.0")

            # Cleanup
            os.chmod(giljo_dir, 0o755)

    def test_handle_database_connection_failure(self, tmp_path):
        """Handle database connection failures gracefully"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        mock_session = Mock()
        mock_session.query.side_effect = Exception("Connection timeout")

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(
                tenant_key="test_tenant",
                db_session=mock_session
            )

            # Should fall back to file storage
            state = manager.get_state()
            assert state is not None

    def test_handle_missing_tenant_key(self):
        """Raise error when tenant_key is not provided"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with pytest.raises(ValueError, match="tenant_key is required"):
            SetupStateManager(tenant_key=None)

    def test_handle_invalid_version_format(self, sync_db_session):
        """Validate semantic versioning format"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager = SetupStateManager(
            tenant_key="test_tenant",
            db_session=sync_db_session
        )

        # Invalid version should raise error
        with pytest.raises(ValueError, match="Invalid version format"):
            manager.mark_completed(setup_version="not-a-version")


class TestConcurrentAccess:
    """Tests for concurrent file access."""

    def test_file_locking_prevents_concurrent_writes(self, tmp_path):
        """File locking should prevent concurrent write corruption"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        import threading
        import time

        with patch('pathlib.Path.home', return_value=tmp_path):
            results = []

            def write_state(version):
                manager = SetupStateManager(tenant_key="concurrent_tenant")
                manager.mark_completed(setup_version=version)
                results.append(version)

            # Start multiple threads writing simultaneously
            threads = [
                threading.Thread(target=write_state, args=(f"{i}.0.0",))
                for i in range(5)
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # All writes should succeed (no corruption)
            assert len(results) == 5

            # Final state should be valid (one of the versions)
            manager = SetupStateManager(tenant_key="concurrent_tenant")
            state = manager.get_state()
            assert state["completed"] is True
            assert state["setup_version"] in [f"{i}.0.0" for i in range(5)]


class TestConfigSnapshot:
    """Tests for configuration snapshot functionality."""

    def test_save_config_snapshot(self, sync_db_session):
        """Should save config.yaml snapshot when marking complete"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        config_data = {
            "installation": {"mode": "localhost"},
            "database": {"host": "localhost", "port": 5432}
        }

        manager = SetupStateManager(
            tenant_key="snapshot_tenant",
            db_session=sync_db_session
        )

        manager.mark_completed(
            setup_version="2.0.0",
            config_snapshot=config_data
        )

        state = manager.get_state()
        assert state["config_snapshot"] == config_data

    def test_rollback_to_config_snapshot(self, sync_db_session, setup_state_factory):
        """Should be able to retrieve config snapshot for rollback"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from datetime import datetime
        from uuid import uuid4

        tenant_key = f"rollback_tenant_{uuid4().hex[:8]}"
        config_data = {"installation": {"mode": "localhost"}}

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="2.0.0",
            config_snapshot=config_data
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )

        snapshot = manager.get_config_snapshot()
        assert snapshot == config_data


class TestResetState:
    """Tests for reset functionality (testing and recovery)."""

    def test_reset_state_clears_database(self, sync_db_session, setup_state_factory):
        """reset_state should clear setup state from database"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from src.giljo_mcp.models import SetupState
        from datetime import datetime

        db_state = setup_state_factory(
            tenant_key="reset_tenant",
            completed=True,
            completed_at=datetime.utcnow(),
            setup_version="2.0.0"
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key="reset_tenant",
            db_session=sync_db_session
        )

        manager.reset_state()

        # Verify state was deleted
        state = SetupState.get_by_tenant(sync_db_session, "reset_tenant")
        assert state is None

    def test_reset_state_removes_file(self, tmp_path):
        """reset_state should remove setup state file"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        with patch('pathlib.Path.home', return_value=tmp_path):
            manager = SetupStateManager(tenant_key="reset_tenant")
            manager.mark_completed(setup_version="2.0.0")

            # Verify file exists
            state_file = tmp_path / ".giljo-mcp" / "setup_state.json"
            assert state_file.exists()

            # Reset
            manager.reset_state()

            # File should be removed
            assert not state_file.exists()


class TestFeatureTracking:
    """Tests for feature and tool tracking."""

    def test_add_configured_feature(self, sync_db_session):
        """Should track configured features"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager = SetupStateManager(
            tenant_key="feature_tenant",
            db_session=sync_db_session
        )

        manager.add_configured_feature("database", {"host": "localhost"})
        manager.add_configured_feature("api", {"enabled": True, "port": 7272})

        state = manager.get_state()
        assert "database" in state["features_configured"]
        assert "api" in state["features_configured"]
        assert state["features_configured"]["api"]["port"] == 7272

    def test_add_enabled_tool(self, sync_db_session):
        """Should track enabled MCP tools"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager = SetupStateManager(
            tenant_key="tool_tenant",
            db_session=sync_db_session
        )

        manager.add_enabled_tool("project")
        manager.add_enabled_tool("agent")
        manager.add_enabled_tool("message")

        state = manager.get_state()
        assert "project" in state["tools_enabled"]
        assert "agent" in state["tools_enabled"]
        assert "message" in state["tools_enabled"]

    def test_has_feature_check(self, sync_db_session, setup_state_factory):
        """Should check if feature is configured"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager
        from uuid import uuid4

        tenant_key = f"feature_check_tenant_{uuid4().hex[:8]}"

        db_state = setup_state_factory(
            tenant_key=tenant_key,
            features_configured={"database": True, "api": {"enabled": True}}
        )
        sync_db_session.commit()

        manager = SetupStateManager(
            tenant_key=tenant_key,
            db_session=sync_db_session
        )

        assert manager.has_feature("database") is True
        assert manager.has_feature("api.enabled") is True
        assert manager.has_feature("elasticsearch") is False


class TestSingletonPattern:
    """Tests for singleton pattern implementation."""

    def test_same_tenant_returns_same_instance(self):
        """Same tenant_key should return same SetupStateManager instance"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager1 = SetupStateManager.get_instance(tenant_key="singleton_tenant")
        manager2 = SetupStateManager.get_instance(tenant_key="singleton_tenant")

        assert manager1 is manager2

    def test_different_tenants_return_different_instances(self):
        """Different tenant_keys should return different instances"""
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        manager1 = SetupStateManager.get_instance(tenant_key="tenant1")
        manager2 = SetupStateManager.get_instance(tenant_key="tenant2")

        assert manager1 is not manager2
