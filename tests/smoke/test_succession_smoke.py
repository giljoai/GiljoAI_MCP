"""Smoke test: Orchestrator succession workflow."""
from __future__ import annotations

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def succession_project(authenticated_client):
    """Create active project suitable for succession tests."""
    client, user = authenticated_client

    # Create product
    response = await client.post(
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
    response = await client.post(
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
    response = await client.post(
        f"/api/v1/projects/{project_id}/activate",
        json={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Succession project activation failed"

    return project


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_succession_smoke(authenticated_client, succession_project: dict) -> None:
    """Smoke: trigger orchestrator succession for active project."""
    client, user = authenticated_client
    project_id = succession_project["id"]

    response = await client.post(
        "/api/v1/agent-jobs/trigger-succession",
        json={"project_id": project_id, "tenant_key": "smoke-tenant"},
    )
    assert response.status_code == 200, "Succession trigger failed"

    data = response.json()
    assert data.get("success") is True

    print("✓ Orchestrator succession workflow: PASS")

