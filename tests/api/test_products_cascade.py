"""
Test cascade impact endpoint for product deletion.

Tests the GET /api/products/{id}/cascade-impact endpoint that returns
counts of all data that will be cascade-deleted when a product is deleted.
"""

import pytest
from fastapi.testclient import TestClient


def test_get_cascade_impact_basic(client: TestClient, test_product, auth_headers):
    """Test basic cascade impact retrieval (Issue #4 - verify /v1/products prefix works)."""
    response = client.get(
        f"/api/v1/products/{test_product['id']}/cascade-impact",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should return all cascade counts
    assert "product_id" in data
    assert "projects_count" in data
    assert "unfinished_projects" in data
    assert "tasks_count" in data
    assert "unresolved_tasks" in data
    assert "vision_documents_count" in data
    assert "total_chunks" in data

    assert data["product_id"] == test_product["id"]


def test_get_cascade_impact_with_data(client: TestClient, test_product, test_project, test_task, auth_headers):
    """Test cascade impact with actual data."""
    response = client.get(
        f"/api/v1/products/{test_product['id']}/cascade-impact",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should count the test project and task
    assert data["projects_count"] >= 1
    assert data["tasks_count"] >= 1


def test_get_cascade_impact_not_found(client: TestClient, auth_headers):
    """Test cascade impact for non-existent product."""
    response = client.get(
        "/api/v1/products/invalid-id/cascade-impact",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_get_cascade_impact_multi_tenant_isolation(client: TestClient, test_product, auth_headers):
    """Test that cascade impact respects tenant isolation."""
    # Use different tenant key
    wrong_tenant_headers = auth_headers.copy()
    wrong_tenant_headers["X-Tenant-Key"] = "wrong_tenant_key"

    response = client.get(
        f"/api/v1/products/{test_product['id']}/cascade-impact",
        headers=wrong_tenant_headers
    )

    # Should not find product (tenant isolation)
    assert response.status_code == 404
