"""
TDD: Product activation/deactivation emits tenant-scoped WebSocket events

Tests that:
- Product activation publishes product:status:changed event
- Product deactivation publishes product:status:changed event
- Events include correct product_id, is_active, and tenant_key
"""

import types
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from api.app import app
from src.giljo_mcp.auth.dependencies import get_db_session, get_current_active_user
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.auth_manager import AuthManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class DummyEventBus:
    """Capture events for testing."""
    def __init__(self):
        self.events = []

    async def publish(self, event_type: str, data: dict):
        self.events.append((event_type, data))
        return 1


@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client with proper database setup and event bus capture."""
    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean test data
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE products, users RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency
    async def override_get_db_session():
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Initialize app.state with required objects
    app.state.db_manager = test_db_manager

    # Create auth manager for test
    auth_manager = AuthManager(test_db_manager)
    app.state.auth = auth_manager

    # Override auth to bypass JWT
    test_tenant = "tk_test_ws_event"

    async def override_user():
        return types.SimpleNamespace(
            id=1,
            username="tester",
            role="admin",
            tenant_key=test_tenant,
            is_active=True
        )

    app.dependency_overrides[get_current_active_user] = override_user

    # Replace event bus with dummy to capture events
    dummy_bus = DummyEventBus()
    app.state.event_bus = dummy_bus

    # Create client with testserver host
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver:8000") as client:
        yield client, dummy_bus, test_tenant

    # Cleanup
    app.dependency_overrides.clear()
    await test_db_manager.close_async()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires app lifespan initialization - needs test infrastructure update for auth middleware closure")
async def test_product_activation_emits_tenant_scoped_ws_event(test_client):
    client, dummy_bus, test_tenant = test_client

    # Create product
    resp_create = await client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product",
            "description": "WS event test",
            "project_path": None,
            "config_data": None,
        },
    )
    assert resp_create.status_code == 200, f"Failed to create product: {resp_create.text}"
    product = resp_create.json()
    product_id = product["id"]

    # Clear events from create
    dummy_bus.events.clear()

    # Activate product (should publish event)
    resp_activate = await client.post(f"/api/v1/products/{product_id}/activate")
    assert resp_activate.status_code == 200, f"Failed to activate: {resp_activate.text}"

    # Check activation event
    activation_events = [
        (et, ev) for et, ev in dummy_bus.events
        if et == "product:status:changed" and ev.get("is_active") is True
    ]
    assert len(activation_events) >= 1, f"No activation event found. Events: {dummy_bus.events}"

    _, activate_data = activation_events[0]
    assert activate_data.get("product_id") == product_id
    assert activate_data.get("tenant_key") == test_tenant

    # Clear events
    dummy_bus.events.clear()

    # Deactivate product (should publish event)
    resp_deactivate = await client.post(f"/api/v1/products/{product_id}/deactivate")
    assert resp_deactivate.status_code == 200, f"Failed to deactivate: {resp_deactivate.text}"

    # Check deactivation event
    deactivation_events = [
        (et, ev) for et, ev in dummy_bus.events
        if et == "product:status:changed" and ev.get("is_active") is False
    ]
    assert len(deactivation_events) >= 1, f"No deactivation event found. Events: {dummy_bus.events}"

    _, deactivate_data = deactivation_events[0]
    assert deactivate_data.get("product_id") == product_id
    assert deactivate_data.get("tenant_key") == test_tenant
