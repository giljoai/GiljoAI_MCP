"""Smoke test: Orchestrator succession workflow."""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def succession_client() -> TestClient:
    """FastAPI client for succession smoke tests."""
    return TestClient(app)


@pytest.fixture
def succession_project(succession_client: TestClient) -> dict:
    """Create active project suitable for succession tests."""
    # Create product
    response = succession_client.post(
        "/api/v1/products/",
        json={
            "name": "Succession Product",
            "tenant_key": "smoke-tenant",
            "description": "Succession smoke product",
        },
    )
    assert response.status_code == 200, "Succession product creation failed"
    product_id = response.json()["id"]

    # Create project
    response = succession_client.post(
        "/api/v1/projects/",
        json={
            "name": "Succession Project",
            "product_id": product_id,
            "tenant_key": "smoke-tenant",
            "mission": "Succession smoke mission",
        },
    )
    assert response.status_code == 200, "Succession project creation failed"
    project = response.json()
    project_id = project["id"]

    # Activate project
    response = succession_client.post(
        f"/api/v1/projects/{project_id}/activate",
        json={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Succession project activation failed"

    return project


@pytest.mark.smoke
def test_succession_smoke(succession_client: TestClient, succession_project: dict) -> None:
    """Smoke: trigger orchestrator succession for active project."""
    project_id = succession_project["id"]

    response = succession_client.post(
        "/api/v1/agent-jobs/trigger-succession",
        json={"project_id": project_id, "tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Succession trigger failed"

    data = response.json()
    assert data.get("success") is True

    print("✓ Orchestrator succession workflow: PASS")

