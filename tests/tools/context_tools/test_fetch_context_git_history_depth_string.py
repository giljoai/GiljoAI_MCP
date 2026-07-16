# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for TSK-9159: get_context/fetch_context git_history
depth-string crash.

The get_context MCP boundary advertises string depth overrides
(``depth_config={'git_history': 'summary'}`` in the tool schema), but the
git_history branch of ``_fetch_category`` parsed the depth with a bare
``int(depth)``. A string token raised
``ValueError: invalid literal for int() with base 10: 'summary'``, the
per-category catch swallowed it, and git_history was dropped from the
response into ``errors``.

Contract under test: string depth tokens must be tolerated — a named token
maps to a sensible commit count, a numeric string parses, and an
unrecognized value falls back to the default with a warning, never an error.
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


def _git_history_result() -> dict[str, Any]:
    return {
        "source": "git_history",
        "data": [{"id": "abc123", "type": "commit", "message": "a commit"}],
        "metadata": {"git_integration_enabled": True, "returned_commits": 1},
    }


async def _run_fetch(depth_value: Any) -> tuple[dict[str, Any], AsyncMock]:
    """Drive fetch_context for git_history with the given depth override."""
    git_tool = AsyncMock(return_value=_git_history_result())

    with (
        patch.dict(fetch_context_module.CATEGORY_TOOLS, {"git_history": git_tool}),
        patch.object(fetch_context_module, "_is_category_enabled", new=AsyncMock(return_value=True)),
        patch.object(fetch_context_module, "_load_user_depth_config", new=AsyncMock(return_value={})),
        patch.object(fetch_context_module, "_build_last_modified_map", new=AsyncMock(return_value={})),
    ):
        response = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=["git_history"],
            depth_config={"git_history": depth_value},
            db_manager=object(),  # truthy stand-in; real DB calls are patched
        )
    return response, git_tool


@pytest.mark.asyncio
async def test_git_history_depth_summary_token_does_not_drop_category():
    """The exact failing input from TSK-9159: {'git_history': 'summary'}."""
    response, git_tool = await _run_fetch("summary")

    failed = {e["category"] for e in response.get("errors", [])}
    assert "git_history" not in failed, (
        f"git_history must not fail on advertised string depth 'summary', errors={response.get('errors')}"
    )
    assert "git_history" in response["categories_returned"]
    assert git_tool.await_count == 1
    commits = git_tool.await_args.kwargs.get("commits")
    assert commits is None or isinstance(commits, int), (
        f"'summary' must map to an int commit count or fall back to the default, got {commits!r}"
    )


@pytest.mark.asyncio
async def test_git_history_depth_numeric_string_parses():
    """A numeric string depth ('50') must behave like the int 50."""
    response, git_tool = await _run_fetch("50")

    assert "git_history" in response["categories_returned"]
    assert response.get("errors") is None or not response["errors"]
    assert git_tool.await_args.kwargs.get("commits") == 50


@pytest.mark.asyncio
async def test_git_history_depth_unrecognized_string_falls_back_to_default():
    """An unrecognized token must fall back to the default, not error out."""
    response, git_tool = await _run_fetch("bogus-token")

    failed = {e["category"] for e in response.get("errors", [])}
    assert "git_history" not in failed
    assert "git_history" in response["categories_returned"]
    commits = git_tool.await_args.kwargs.get("commits")
    assert commits is None or isinstance(commits, int)


@pytest.mark.asyncio
async def test_git_history_depth_int_unchanged_regression():
    """The existing int depth path must keep working exactly as before."""
    response, git_tool = await _run_fetch(50)

    assert "git_history" in response["categories_returned"]
    assert git_tool.await_args.kwargs.get("commits") == 50
