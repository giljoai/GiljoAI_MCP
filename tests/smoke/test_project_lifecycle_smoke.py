"""Smoke test: Project lifecycle (create → activate → launch → deactivate)."""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def smoke_client() -> TestClient:
    """FastAPI client for smoke tests."""
    return TestClient(app)


@pytest.fixture
def smoke_product(smoke_client: TestClient) -> dict:
    """Create product for smoke tests."""
    response = smoke_client.post(
        "/api/v1/products/",
        json={
            "name": "Smoke Product",
            "tenant_key": "smoke-tenant",
            "description": "Smoke product for lifecycle tests",
        },
    )
    assert response.status_code == 200, "Smoke product creation failed"
    return response.json()


@pytest.mark.smoke
def test_project_lifecycle_smoke(smoke_client: TestClient, smoke_product: dict) -> None:
    """Smoke: create → activate → launch → deactivate."""
    # 1. Create project
    response = smoke_client.post(
        "/api/v1/projects/",
        json={
            "name": "Smoke Project",
            "product_id": smoke_product["id"],
            "tenant_key": "smoke-tenant",
            "mission": "Smoke test mission",
        },
    )
    assert response.status_code == 200, "Project creation failed"
    project = response.json()
    project_id = project["id"]

    # 2. Activate project
    response = smoke_client.post(
        f"/api/v1/projects/{project_id}/activate",
        json={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Project activation failed"

    # 3. Launch orchestrator for project
    response = smoke_client.post(
        f"/api/v1/projects/{project_id}/launch",
        json={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Project launch failed"

    # 4. Deactivate project
    response = smoke_client.post(
        f"/api/v1/projects/{project_id}/deactivate",
        json={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Project deactivation failed"

    print("✓ Project lifecycle workflow: PASS")

