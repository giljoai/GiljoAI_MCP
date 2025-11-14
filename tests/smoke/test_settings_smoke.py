"""Smoke test: Settings persistence."""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.mark.smoke
def test_settings_persistence_smoke() -> None:
    """Smoke: save settings → retrieve → verify."""
    client = TestClient(app)

    # 1. Update general settings
    response = client.put(
        "/api/v1/settings/general",
        json={
            "tenant_key": "smoke-tenant",
            "settings_data": {
                "theme": "dark",
                "language": "es",
                "notifications": True,
            },
        },
    )
    assert response.status_code == 200, "Settings update failed"

    # 2. Retrieve settings
    response = client.get(
        "/api/v1/settings/general",
        params={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Settings retrieval failed"

    settings = response.json()
    data = settings.get("settings_data") or {}

    assert data.get("theme") == "dark"
    assert data.get("language") == "es"

    print("✓ Settings persistence: PASS")

