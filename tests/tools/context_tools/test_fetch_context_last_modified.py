# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""CE-0031 Task 4: fetch_context surfaces last_modified per category.

The orchestrator's get_staging_instructions response threads Modified
timestamps into the protocol's per-category framing text. Once fetch_context
runs, those dates were lost — callers had no way to detect whether a cached
fetch was stale short of re-pulling the catalog. CE-0031 Task 4 attaches a
``last_modified`` map to the response, scoped to categories that have a
server-side authoritative timestamp (product-level data + memory_360).
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from giljo_mcp.tools.context_tools.fetch_context import fetch_context


fetch_context_module = sys.modules["giljo_mcp.tools.context_tools.fetch_context"]


PRODUCT_ID = "11111111-1111-1111-1111-111111111111"
TENANT_KEY = "tk_test"


def _stub_results() -> dict[str, dict[str, Any]]:
    return {
        "tech_stack": {
            "source": "tech_stack",
            "data": {"languages": ["python"]},
            "metadata": {},
        },
        "memory_360": {
            "source": "360_memory",
            "data": [],
            "metadata": {"total_projects": 0},
        },
        "git_history": {
            "source": "git_history",
            "data": [],
            "directive": {"action": "fetch_from_local_repo"},
            "metadata": {},
        },
    }


@pytest.mark.asyncio
async def test_last_modified_returned_for_product_level_categories():
    """Product-level categories (tech_stack here) carry product.updated_at."""
    stubs = _stub_results()
    expected_map = {
        "tech_stack": "2026-05-17T10:00",
        "memory_360": "2026-05-16T08:30",
        # git_history intentionally omitted — no server-side authority.
    }

    async def fake_fetch(category: str, **_kwargs):
        return stubs[category]

    with (
        patch.object(fetch_context_module, "_fetch_category", new=AsyncMock(side_effect=fake_fetch)),
        patch.object(fetch_context_module, "_is_category_enabled", new=AsyncMock(return_value=True)),
        patch.object(
            fetch_context_module,
            "_load_user_depth_config",
            new=AsyncMock(return_value={}),
        ),
        patch.object(
            fetch_context_module,
            "_build_last_modified_map",
            new=AsyncMock(return_value=expected_map),
        ),
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["tech_stack", "memory_360", "git_history"],
            db_manager=object(),
        )

    assert "last_modified" in response, "fetch_context response must include a last_modified map per CE-0031 Task 4"
    last_modified = response["last_modified"]
    # Only categories that actually returned should appear in the map (we filter
    # the map down to categories_returned to avoid surfacing ghost entries).
    assert last_modified["tech_stack"] == "2026-05-17T10:00"
    assert last_modified["memory_360"] == "2026-05-16T08:30"
    # git_history has no server-side authority → not present in expected_map.
    assert "git_history" not in last_modified


@pytest.mark.asyncio
async def test_last_modified_filtered_to_returned_categories():
    """A timestamp for a NOT-requested category must never leak into the response."""
    stubs = _stub_results()
    # Map contains a stale category the caller didn't ask for.
    bigger_map = {
        "tech_stack": "2026-05-17T10:00",
        "architecture": "2026-05-15T09:00",  # not in categories_returned
    }

    async def fake_fetch(category: str, **_kwargs):
        return stubs[category]

    with (
        patch.object(fetch_context_module, "_fetch_category", new=AsyncMock(side_effect=fake_fetch)),
        patch.object(fetch_context_module, "_is_category_enabled", new=AsyncMock(return_value=True)),
        patch.object(
            fetch_context_module,
            "_load_user_depth_config",
            new=AsyncMock(return_value={}),
        ),
        patch.object(
            fetch_context_module,
            "_build_last_modified_map",
            new=AsyncMock(return_value=bigger_map),
        ),
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["tech_stack"],
            db_manager=object(),
        )

    assert "tech_stack" in response["last_modified"]
    assert "architecture" not in response["last_modified"], (
        "last_modified must not include categories the caller did not request — scope leak risk."
    )
