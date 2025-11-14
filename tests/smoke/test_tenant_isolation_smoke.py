"""Smoke test: Multi-tenant isolation for products/projects."""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def tenant_client() -> TestClient:
    """FastAPI client for tenant isolation tests."""
    return TestClient(app)


@pytest.mark.smoke
def test_multi_tenant_isolation_smoke(tenant_client: TestClient) -> None:
    """Smoke: ensure tenant_key scopes products and projects."""
    client = tenant_client

    # 1. Create product for tenant A
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant A Product",
            "tenant_key": "tenant-a",
            "description": "Tenant A product",
        },
    )
    assert response.status_code == 200, "Tenant A product creation failed"
    product_a_id = response.json()["id"]

    # 2. Create product for tenant B
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant B Product",
            "tenant_key": "tenant-b",
            "description": "Tenant B product",
        },
    )
    assert response.status_code == 200, "Tenant B product creation failed"
    product_b_id = response.json()["id"]

    # 3. Create project for tenant A
    response = client.post(
        "/api/v1/projects/",
        json={
            "name": "Tenant A Project",
            "product_id": product_a_id,
            "tenant_key": "tenant-a",
            "mission": "Tenant A mission",
        },
    )
    assert response.status_code == 200, "Tenant A project creation failed"
    project_a_id = response.json()["id"]

    # 4. Attempt to access tenant A project with tenant B key (should be forbidden or not found)
    response = client.get(
        f"/api/v1/projects/{project_a_id}",
        params={"tenant_key": "tenant-b"},
    )
    assert response.status_code in (403, 404), "Cross-tenant access was not blocked"

    # 5. Ensure each tenant can list their own projects
    response = client.get("/api/v1/projects/", params={"tenant_key": "tenant-a"})
    assert response.status_code == 200
    projects_a = response.json()

    response = client.get("/api/v1/projects/", params={"tenant_key": "tenant-b"})
    assert response.status_code == 200
    projects_b = response.json()

    assert all(p.get("tenant_key") == "tenant-a" for p in projects_a)
    assert all(p.get("tenant_key") == "tenant-b" for p in projects_b)

    print("✓ Multi-tenant isolation: PASS")

