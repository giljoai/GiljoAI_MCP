"""
Tests for Mission Regeneration Endpoint

Tests the /api/orchestration/regenerate-mission endpoint that allows users
to regenerate missions with different field priority overrides without
persisting changes to their saved settings.

Handover 0086B Phase 5.1: Backend Integration Testing (Task 3.3)
Created: 2025-11-02
Coverage Target: 95%+
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from api.dependencies.websocket import WebSocketDependency


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def authenticated_client_with_user(api_client, db_session):
    """
    Create API client with authenticated user and settings.

    Provides a complete test user with field_priority_config for testing
    mission regeneration with overrides.
    """
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user
    from src.giljo_mcp.models import User

    test_user = User(
        id=str(uuid4()),
        username="test_user",
        email="test@example.com",
        tenant_key="tenant_abc",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        hashed_password="hashed",
        field_priority_config={
            "product_vision": 10,
            "project_description": 8,
            "codebase_summary": 6,
            "architecture": 4,
            "serena_enabled": False,
            "token_budget": 2000
        }
    )

    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    async def mock_get_current_user():
        return test_user

    # Override authentication
    app.dependency_overrides[get_current_active_user] = mock_get_current_user

    yield api_client, test_user

    # Cleanup
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_product(db_session):
    """Create test product with vision document."""
    from src.giljo_mcp.models import Product

    product = Product(
        id=str(uuid4()),
        name="Test Product",
        tenant_key="tenant_abc",
        vision_document="# Product Vision\nBuild an enterprise application with advanced features.",
        config_data={
            "tech_stack": {
                "languages": ["Python", "JavaScript"],
                "backend": ["FastAPI"],
                "frontend": ["Vue.js"],
                "database": ["PostgreSQL"]
            },
            "features": ["Authentication", "User Management", "Analytics"],
            "architecture": {
                "pattern": "Microservices",
                "api_style": "REST",
                "notes": "Event-driven architecture with message queues"
            }
        },
        status="active"
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def test_project(db_session, test_product):
    """Create test project linked to product."""
    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key="tenant_abc",
        product_id=test_product.id,
        description="Implement authentication and user management system",
        codebase_summary="## Backend\n- FastAPI application\n- PostgreSQL database\n- JWT authentication",
        status="active"
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.fixture
def mock_websocket_dependency():
    """Create mock WebSocketDependency for broadcast verification."""
    ws_dep = MagicMock(spec=WebSocketDependency)
    ws_dep.broadcast_to_tenant = AsyncMock(return_value=3)  # 3 clients
    ws_dep.is_available = MagicMock(return_value=True)

    return ws_dep


# ============================================================================
# Test: Regenerate with Field Priority Overrides
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_mission_with_field_priority_overrides(
    authenticated_client_with_user, test_project, mock_websocket_dependency
):
    """
    Test regenerate_mission endpoint respects field priority overrides.

    Validates that users can temporarily override their saved field priorities
    to experiment with different configurations without persisting changes.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator to avoid full mission generation
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Generated mission with overrides",
            "token_estimate": 1500,
            "user_config_applied": True,
            "serena_enabled": False
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id,
            "override_field_priorities": {
                "codebase_summary": 10,  # Override from 6 to 10
                "architecture": 2  # Override from 4 to 2
            }
        }

        # Act
        response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200

        result = response.json()
        assert result["mission"] == "Generated mission with overrides"
        assert result["token_estimate"] == 1500
        assert result["user_config_applied"] is True

        # Verify field_priorities_used includes overrides
        assert result["field_priorities_used"]["codebase_summary"] == 10
        assert result["field_priorities_used"]["architecture"] == 2

    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_regenerate_mission_overrides_dont_persist(
    authenticated_client_with_user, test_project, db_session, mock_websocket_dependency
):
    """
    Test regenerate_mission overrides DO NOT persist to user settings.

    CRITICAL: Validates that override_field_priorities are temporary
    and do not modify the user's saved field_priority_config.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Save original field_priority_config
    original_config = user.field_priority_config.copy()

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Temporary overrides",
            "token_estimate": 1200,
            "user_config_applied": True,
            "serena_enabled": False
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id,
            "override_field_priorities": {
                "product_vision": 5  # Temporary override from 10 to 5
            }
        }

        # Act
        response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200

        # Refresh user from database
        await db_session.refresh(user)

        # CRITICAL: Verify field_priority_config unchanged
        assert user.field_priority_config["product_vision"] == 10  # Still 10, not 5
        assert user.field_priority_config == original_config

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Serena Toggle Override
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_mission_with_serena_toggle_override(
    authenticated_client_with_user, test_project, mock_websocket_dependency
):
    """
    Test regenerate_mission respects serena_enabled override.

    Validates that users can temporarily enable/disable Serena integration
    without changing their saved settings.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # User has serena_enabled=False by default
    assert user.field_priority_config["serena_enabled"] is False

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Mission with Serena context",
            "token_estimate": 2500,
            "user_config_applied": True,
            "serena_enabled": True  # Enabled via override
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id,
            "override_serena_enabled": True  # Temporary enable
        }

        # Act
        response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200

        result = response.json()
        assert result["serena_enabled"] is True  # Override applied

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: WebSocket Broadcasting
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_mission_broadcasts_update(
    authenticated_client_with_user, test_project, mock_websocket_dependency
):
    """
    Test regenerate_mission broadcasts project:mission_updated event.

    Validates that WebSocket event is sent to all tenant clients after
    successful mission regeneration.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Regenerated mission",
            "token_estimate": 1800,
            "user_config_applied": True,
            "serena_enabled": False
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id
        }

        # Act
        response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200

        # Verify broadcast was called
        mock_websocket_dependency.broadcast_to_tenant.assert_called_once()

        # Verify broadcast parameters
        call_args = mock_websocket_dependency.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == "tenant_abc"
        assert call_args.kwargs["event_type"] == "project:mission_updated"

        # Verify event data
        data = call_args.kwargs["data"]
        assert data["project_id"] == test_project.id
        assert data["mission"] == "Regenerated mission"
        assert data["token_estimate"] == 1800
        assert data["generated_by"] == "user"  # User-initiated regeneration
        assert data["user_config_applied"] is True

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Authorization and Multi-Tenant Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_mission_unauthorized_access_denied(
    authenticated_client_with_user, db_session
):
    """
    Test regenerate_mission rejects unauthorized access to other tenants' projects.

    CRITICAL SECURITY TEST: Validates multi-tenant isolation at API level.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Create project for different tenant
    from src.giljo_mcp.models import Project

    other_tenant_project = Project(
        id=str(uuid4()),
        name="Other Tenant Project",
        tenant_key="tenant_xyz",  # DIFFERENT tenant
        description="Should not be accessible",
        status="active"
    )

    db_session.add(other_tenant_project)
    await db_session.commit()

    request_data = {
        "project_id": other_tenant_project.id
    }

    # Act
    response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

    # Assert
    assert response.status_code == 404  # Not found (tenant filtering)


@pytest.mark.asyncio
async def test_regenerate_mission_multi_tenant_isolation_in_broadcast(
    authenticated_client_with_user, test_project, mock_websocket_dependency
):
    """
    Test regenerate_mission broadcast enforces tenant isolation.

    Validates that WebSocket broadcast uses correct tenant_key.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return mock_websocket_dependency

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Mission content",
            "token_estimate": 1000,
            "user_config_applied": True,
            "serena_enabled": False
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id
        }

        # Act
        response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200

        # CRITICAL: Verify tenant_key in broadcast
        call_args = mock_websocket_dependency.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == "tenant_abc"

        # Verify tenant_key in event data
        data = call_args.kwargs["data"]
        assert data["tenant_key"] == "tenant_abc"

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_mission_handles_missing_project(authenticated_client_with_user):
    """
    Test regenerate_mission returns 404 for non-existent project.

    Validates error handling for invalid project_id.
    """
    # Arrange
    client, user = authenticated_client_with_user

    request_data = {
        "project_id": str(uuid4())  # Non-existent project
    }

    # Act
    response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_mission_graceful_degradation_websocket_failure(
    authenticated_client_with_user, test_project, caplog
):
    """
    Test regenerate_mission succeeds even if WebSocket broadcast fails.

    Validates graceful degradation when WebSocket is unavailable.
    """
    # Arrange
    client, user = authenticated_client_with_user

    # Create WebSocket dependency that raises exception
    ws_dep_error = MagicMock(spec=WebSocketDependency)
    ws_dep_error.broadcast_to_tenant = AsyncMock(side_effect=Exception("WebSocket error"))
    ws_dep_error.is_available = MagicMock(return_value=True)

    # Override WebSocket dependency
    from api.app import app
    from api.dependencies.websocket import get_websocket_dependency

    async def mock_get_ws_dep():
        return ws_dep_error

    app.dependency_overrides[get_websocket_dependency] = mock_get_ws_dep

    # Mock orchestrator
    with patch('api.endpoints.orchestration.ProjectOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_product_vision = AsyncMock(return_value={
            "mission": "Mission despite WebSocket error",
            "token_estimate": 1000,
            "user_config_applied": True,
            "serena_enabled": False
        })
        mock_orchestrator_class.return_value = mock_orchestrator

        request_data = {
            "project_id": test_project.id
        }

        # Act
        with caplog.at_level("ERROR"):
            response = await client.post("/api/orchestration/regenerate-mission", json=request_data)

        # Assert
        assert response.status_code == 200  # Still succeeds

        # Verify error was logged
        assert "Failed to broadcast" in caplog.text or "error" in caplog.text.lower()

    # Cleanup
    app.dependency_overrides.clear()
