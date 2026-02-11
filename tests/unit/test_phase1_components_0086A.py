"""
Unit Tests for Phase 1 Components (Handover 0086A)
Production-Grade Stage Project Architecture

These tests run in isolation without full application context to avoid
circular import issues. Tests individual components independently.

Test Coverage:
1. Task 1.1: Project model hybrid_property
2. Task 1.4: Event schema validation
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError


# ==============================================================================
# TASK 1.1: Project Model Hybrid Property Tests
# ==============================================================================


class TestProjectModelHybridProperty:
    """
    Validate Task 1.1: Standardize Data Model

    Success Criteria:
    - ✅ 'id' is primary field
    - ✅ 'project_id' works as backwards-compatible alias
    - ✅ Both return same value
    - ✅ Setter works correctly
    """

    def test_project_has_id_field(self):
        """Test that Project model has 'id' as primary key."""
        from src.giljo_mcp.models import Project, generate_uuid

        # Create project with explicit ID (SQLAlchemy doesn't call default until commit)
        project = Project(
            id=generate_uuid(),
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        assert hasattr(project, "id")
        assert project.id is not None

    def test_project_has_project_id_alias(self):
        """Test that Project model has 'project_id' hybrid property."""
        from src.giljo_mcp.models import Project, generate_uuid

        # Create project with explicit ID
        project = Project(
            id=generate_uuid(),
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        assert hasattr(project, "project_id")
        assert project.project_id is not None

    def test_project_id_returns_same_as_id(self):
        """Test that 'project_id' returns same value as 'id'."""
        from src.giljo_mcp.models import Project, generate_uuid

        project_uuid = generate_uuid()
        project = Project(
            id=project_uuid,
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Both should return the same value
        assert project.project_id == project.id
        assert project.project_id == project_uuid

    def test_project_id_setter_updates_id(self):
        """Test that setting 'project_id' updates 'id' field."""
        from src.giljo_mcp.models import Project, generate_uuid

        project = Project(
            id=generate_uuid(),
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Set a new ID via project_id
        new_id = str(uuid4())
        project.project_id = new_id

        # Both should reflect the new value
        assert project.id == new_id
        assert project.project_id == new_id

    def test_backwards_compatibility_in_serialization(self):
        """Test that both 'id' and 'project_id' are accessible."""
        from src.giljo_mcp.models import Project, generate_uuid

        project_uuid = generate_uuid()
        project = Project(
            id=project_uuid,
            name="Test Project",
            description="Test Description",
            tenant_key="test_tenant",
        )

        # Access both ways
        project_id_value = project.project_id
        id_value = project.id

        assert project_id_value == id_value
        assert project_id_value == project_uuid
        assert isinstance(project_id_value, str)


# ==============================================================================
# TASK 1.4: Event Schema Validation Tests
# ==============================================================================


class TestEventSchemaStandalone:
    """
    Validate Task 1.4: Event Schemas (Standalone Tests)

    Tests Pydantic models in isolation without FastAPI context.
    """

    def test_import_event_schemas(self):
        """Test that event schema module can be imported."""
        try:
            # Import using direct file loading to avoid circular imports
            import importlib.util
            import sys
            from pathlib import Path

            schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
            spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            assert hasattr(module, "EventFactory")
            assert hasattr(module, "ProjectMissionUpdatedEvent")
            assert hasattr(module, "AgentCreatedEvent")
            assert hasattr(module, "AgentStatusChangedEvent")

        except ImportError as e:
            pytest.fail(f"Failed to import event schemas: {e}")

    def test_event_factory_project_mission_updated(self):
        """Test EventFactory creates project:mission_updated event."""
        import importlib.util
        from pathlib import Path

        # Direct import
        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        project_id = str(uuid4())
        tenant_key = "test_tenant"

        event = EventFactory.project_mission_updated(
            project_id=project_id,
            tenant_key=tenant_key,
            mission="Implement feature X",
            token_estimate=5000,
            generated_by="orchestrator",
            user_config_applied=True,
            field_priorities={"security": 5, "performance": 4},
        )

        # Validate structure
        assert event["type"] == "project:mission_updated"
        assert event["schema_version"] == "1.0"
        assert event["data"]["project_id"] == project_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["mission"] == "Implement feature X"
        assert event["data"]["token_estimate"] == 5000
        assert event["data"]["generated_by"] == "orchestrator"
        assert event["data"]["user_config_applied"] is True

        # Validate timestamp
        timestamp = event["timestamp"]
        assert timestamp.endswith("Z")
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_event_factory_agent_created(self):
        """Test EventFactory creates agent:created event."""
        import importlib.util
        from pathlib import Path

        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        project_id = str(uuid4())
        tenant_key = "test_tenant"
        agent_data = {
            "id": str(uuid4()),
            "agent_display_name": "orchestrator",
            "status": "pending",
            "mission": "Test mission",
        }

        event = EventFactory.agent_created(
            project_id=project_id,
            tenant_key=tenant_key,
            agent=agent_data,
        )

        assert event["type"] == "agent:created"
        assert event["schema_version"] == "1.0"
        assert event["data"]["project_id"] == project_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["agent"]["id"] == agent_data["id"]

    def test_event_factory_agent_status_changed(self):
        """Test EventFactory creates agent:status_changed event."""
        import importlib.util
        from pathlib import Path

        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        job_id = str(uuid4())
        tenant_key = "test_tenant"

        event = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="waiting",
            new_status="active",
            agent_display_name="orchestrator",
            project_id=str(uuid4()),
        )

        assert event["type"] == "agent:status_changed"
        assert event["schema_version"] == "1.0"
        assert event["data"]["job_id"] == job_id
        assert event["data"]["tenant_key"] == tenant_key
        assert event["data"]["old_status"] == "pending"
        assert event["data"]["new_status"] == "active"

    def test_event_schema_validation_catches_invalid_status(self):
        """Test that invalid agent status is rejected by validation."""
        import importlib.util
        from pathlib import Path

        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        with pytest.raises(ValidationError, match="Invalid agent status"):
            EventFactory.agent_status_changed(
                job_id=str(uuid4()),
                tenant_key="test",
                old_status="waiting",
                new_status="invalid_status",  # Invalid
                agent_display_name="orchestrator",
            )

    def test_event_schema_validation_catches_missing_fields(self):
        """Test that missing required fields are caught."""
        import importlib.util
        from pathlib import Path

        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        invalid_agent = {
            "id": str(uuid4()),
            "agent_display_name": "orchestrator",
            # Missing "status" field
        }

        with pytest.raises(ValidationError, match="missing required fields"):
            EventFactory.agent_created(
                project_id=str(uuid4()),
                tenant_key="test",
                agent=invalid_agent,
            )

    def test_event_json_serialization(self):
        """Test that events can be JSON serialized."""
        import importlib.util
        import json
        from pathlib import Path

        schema_path = Path(__file__).parent.parent.parent / "api" / "events" / "schemas.py"
        spec = importlib.util.spec_from_file_location("event_schemas", schema_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        EventFactory = module.EventFactory

        event = EventFactory.project_mission_updated(
            project_id=str(uuid4()),
            tenant_key="test",
            mission="Test mission",
            token_estimate=1000,
        )

        # Should serialize without errors
        json_str = json.dumps(event)
        assert isinstance(json_str, str)

        # Should deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["type"] == "project:mission_updated"
        assert deserialized["data"]["mission"] == "Test mission"


# ==============================================================================
# WEBSOCKET DEPENDENCY TESTS (Mocked)
# ==============================================================================


class TestWebSocketDependencyMocked:
    """
    Test WebSocket dependency logic with mocks (no FastAPI context).
    """

    def test_websocket_dependency_instantiation(self):
        """Test WebSocketDependency can be instantiated."""
        import importlib.util
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock

        ws_path = Path(__file__).parent.parent.parent / "api" / "dependencies" / "websocket.py"

        spec = importlib.util.spec_from_file_location("ws_dep", ws_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        WebSocketDependency = module.WebSocketDependency

        # Test instantiation
        ws_dep = WebSocketDependency(manager=None)
        assert ws_dep is not None
        assert ws_dep.manager is None
        assert not ws_dep.is_available()

        # Test with mock manager
        mock_mgr_instance = MagicMock()
        ws_dep2 = WebSocketDependency(manager=mock_mgr_instance)
        assert ws_dep2.manager == mock_mgr_instance
        assert ws_dep2.is_available()


if __name__ == "__main__":
    print("=" * 80)
    print("Phase 1 Unit Tests for Handover 0086A")
    print("=" * 80)
    print()
    print("Run with: pytest tests/unit/test_phase1_components_0086A.py -v")
    print("=" * 80)
