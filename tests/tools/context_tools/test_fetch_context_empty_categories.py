# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for fetch_context contract on empty / directive-handled categories.

Wave 1 IMP-0019 Item 2: when a category produces no inline data (memory_360 on
a fresh product) OR is handled via a directive (git_history), the response
previously dropped the category from `data` AND `categories_returned`. This
broke the contract
`categories_requested == categories_returned union failed_categories`
and forced callers to dig into `directive` to know what happened.

Fix: include such categories explicitly in `data` and `categories_returned`,
and surface a new `categories_empty` field listing the empty-payload ones.
"""

import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Import the function and grab the module from sys.modules — `import ... as`
# yields the function shadowed by the package's __init__ re-export.
from giljo_mcp.tools.context_tools.fetch_context import fetch_context


fetch_context_module = sys.modules["giljo_mcp.tools.context_tools.fetch_context"]


PRODUCT_ID = "11111111-1111-1111-1111-111111111111"
TENANT_KEY = "tk_test"


def _stub_results() -> dict[str, dict[str, Any]]:
    """
    Returns canned _fetch_category results for the three categories under test.

    - memory_360: empty list payload (fresh product, no closeouts)
    - git_history: directive-only (git integration disabled / no commits)
    - vision_documents: populated dict payload (regression check)
    """
    return {
        "memory_360": {
            "source": "360_memory",
            "data": [],
            "metadata": {"total_projects": 0, "returned_projects": 0},
        },
        "git_history": {
            "source": "git_history",
            "data": [],
            "directive": {
                "action": "fetch_from_local_repo",
                "command": "git log --oneline -25",
                "note": "Git history is not stored on the server. Run this command in the project directory.",
            },
            "metadata": {"git_integration_enabled": False},
        },
        "vision_documents": {
            "source": "vision_document",
            "data": {"summary": "vision summary text", "sections": ["a", "b"]},
            "metadata": {"chunking": "medium"},
        },
    }


@pytest.mark.asyncio
async def test_empty_memory_360_appears_in_returned_and_empty_lists():
    """
    Case (a): memory_360 with no closeouts must appear in `categories_returned`
    AND in `categories_empty` AND in `data` with an empty value (not silently
    dropped).
    """
    stubs = _stub_results()

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
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["memory_360", "git_history", "vision_documents"],
            db_manager=object(),  # truthy stand-in; real DB calls are patched
        )

    assert response["categories_requested"] == [
        "memory_360",
        "git_history",
        "vision_documents",
    ]
    assert "memory_360" in response["categories_returned"], (
        f"memory_360 must remain in categories_returned even with empty data, got: {response['categories_returned']}"
    )
    assert "categories_empty" in response, "response must expose categories_empty"
    assert "memory_360" in response["categories_empty"]
    assert "memory_360" in response["data"], "memory_360 must be present in data even when empty"
    assert response["data"]["memory_360"] == []


@pytest.mark.asyncio
async def test_directive_handled_git_history_still_in_returned():
    """
    Case (b): git_history surfaced via a directive must still appear in
    `categories_returned` and in `data` (with a marker), so callers see the
    same uniform contract whether the payload is inline or directive-driven.
    The `directive` block must continue to carry the action details.
    """
    stubs = _stub_results()

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
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["memory_360", "git_history", "vision_documents"],
            db_manager=object(),
        )

    # Directive still preserved on top-level response
    assert "directive" in response
    assert "git_history" in response["directive"]
    assert response["directive"]["git_history"]["action"] == "fetch_from_local_repo"

    # New contract: git_history visible in categories_returned and data
    assert "git_history" in response["categories_returned"]
    assert "git_history" in response["data"]
    git_marker = response["data"]["git_history"]
    assert isinstance(git_marker, dict)
    assert git_marker.get("directive") is True


@pytest.mark.asyncio
async def test_populated_category_unchanged_regression():
    """
    Case (c): a category with real inline data still appears in
    `categories_returned` and `data` with its full payload — empty-list
    handling must not regress the populated path.
    """
    stubs = _stub_results()

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
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["memory_360", "git_history", "vision_documents"],
            db_manager=object(),
        )

    assert "vision_documents" in response["categories_returned"]
    assert "vision_documents" not in response.get("categories_empty", [])
    assert response["data"]["vision_documents"] == {
        "summary": "vision summary text",
        "sections": ["a", "b"],
    }


@pytest.mark.asyncio
async def test_categories_returned_union_failed_equals_requested():
    """
    Strong contract assertion: the union of categories_returned and any failed
    categories (in `errors`) must equal categories_requested. Silent omission
    breaks this invariant.
    """
    stubs = _stub_results()

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
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["memory_360", "git_history", "vision_documents"],
            db_manager=object(),
        )

    requested = set(response["categories_requested"])
    returned = set(response["categories_returned"])
    failed = {e["category"] for e in response.get("errors", [])}
    assert requested == returned | failed, (
        f"Contract violation: requested={requested} != returned={returned} union failed={failed}"
    )
