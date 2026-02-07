"""Smoke test: Product creation + vision upload + chunking."""

from __future__ import annotations

import pytest


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_product_vision_workflow_smoke(authenticated_client) -> None:
    """Smoke: create product → upload vision → verify chunking."""
    client, user = authenticated_client

    # 1. Create product
    response = await client.post(
        "/api/v1/products/",
        json={
            "name": "Smoke Test Product",
            "tenant_key": "smoke-tenant",
            "description": "Smoke test",
        },
    )
    assert response.status_code == 200, "Product creation failed"
    product = response.json()
    product_id = product["id"]

    # 2. Upload large vision document (should chunk)
    vision_md = "# Vision\n" + ("Test content " * 10000)
    files = {"file": ("vision.md", vision_md, "text/markdown")}
    response = await client.post(
        f"/api/v1/products/{product_id}/vision",
        files=files,
        data={"tenant_key": "smoke-tenant"},
    )
    assert response.status_code in (200, 201), "Vision upload failed"
    chunks = response.json()
    assert isinstance(chunks, list), "Vision upload did not return chunk list"
    assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"

    print(f"✓ Product + Vision workflow: PASS ({len(chunks)} chunks created)")
