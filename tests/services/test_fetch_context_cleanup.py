# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for fetch_context dead code removal (Handover 0823, Phase 4).

Verifies:
1. apply_user_config parameter is removed from fetch_context()
2. tool_accessor.py no longer falls back to categories=["all"]
3. fetch_context(categories=None) returns SINGLE_CATEGORY_REQUIRED error
"""

import inspect


class TestApplyUserConfigRemoved:
    """Verify apply_user_config dead flag is removed."""

    def test_fetch_context_signature_no_apply_user_config(self):
        """fetch_context() must NOT accept apply_user_config parameter."""
        from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

        sig = inspect.signature(fetch_context)
        params = list(sig.parameters.keys())
        assert "apply_user_config" not in params, (
            f"apply_user_config should be removed from fetch_context signature. "
            f"Current params: {params}"
        )

    def test_tool_accessor_fetch_context_no_apply_user_config(self):
        """ToolAccessor.fetch_context() must NOT accept apply_user_config parameter."""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        sig = inspect.signature(ToolAccessor.fetch_context)
        params = list(sig.parameters.keys())
        assert "apply_user_config" not in params, (
            f"apply_user_config should be removed from ToolAccessor.fetch_context. "
            f"Current params: {params}"
        )


class TestToolAccessorCategoriesDefault:
    """Verify tool_accessor.py does not inject categories=["all"]."""

    def test_tool_accessor_no_all_fallback(self):
        """ToolAccessor.fetch_context should not replace None categories with ['all']."""
        # Read the source code of ToolAccessor.fetch_context to verify
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        source = inspect.getsource(ToolAccessor.fetch_context)
        assert '["all"]' not in source, (
            "ToolAccessor.fetch_context should not fall back to ['all']. "
            "Let fetch_context handle None with its existing SINGLE_CATEGORY_REQUIRED error."
        )
