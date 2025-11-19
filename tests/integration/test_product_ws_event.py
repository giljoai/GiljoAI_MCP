import types
import pytest
from httpx import AsyncClient

from api.app import create_app
from src.giljo_mcp.auth.dependencies import get_current_active_user


class DummyEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event_type: str, data: dict):
        self.events.append((event_type, data))
        return 1


def override_user(tenant_key: str = "tk_test_per_user_tenant"):
    async def _get_current_user():
        # Minimal object with fields used by endpoints
        return types.SimpleNamespace(username="tester", role="admin", tenant_key=tenant_key)

    return _get_current_user


@pytest.mark.asyncio
async def test_product_activation_emits_tenant_scoped_ws_event():
    app = create_app()

    # Override auth dependency to bypass JWT
    app.dependency_overrides[get_current_active_user] = override_user()

    # Replace event bus with dummy to capture events
    dummy_bus = DummyEventBus()
    app.state.event_bus = dummy_bus

    async with AsyncClient(app=app, base_url="http://test") as client:
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
        assert resp_create.status_code == 200
        product = resp_create.json()
        product_id = product["id"]

        # Activate product (should publish event)
        resp_activate = await client.post(f"/api/v1/products/{product_id}/activate")
        assert resp_activate.status_code == 200

        assert any(
            et == "product:status:changed" and ev.get("product_id") == product_id and ev.get("is_active") is True
            for et, ev in dummy_bus.events
        )

        # Deactivate product (should publish event)
        resp_deactivate = await client.post(f"/api/v1/products/{product_id}/deactivate")
        assert resp_deactivate.status_code == 200

        assert any(
            et == "product:status:changed" and ev.get("product_id") == product_id and ev.get("is_active") is False
            for et, ev in dummy_bus.events
        )

