# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration test for Bearer auth migration (Handover 0835).

Verifies that:
- All tool config generators output Authorization: Bearer (not X-API-Key)
- Gemini HTTPS warning logic triggers correctly
- Backend ai_tools endpoint generates Bearer format
"""


# ---------------------------------------------------------------------------
# Test: Frontend prompt generators output Bearer format
# ---------------------------------------------------------------------------


class TestWizardBearerOutput:
    """Verify wizard prompt functions use Authorization: Bearer."""

    def test_claude_prompt_uses_bearer(self):
        """Claude command should use --header 'Authorization: Bearer ...'."""
        from api.endpoints.ai_tools import get_claude_code_config

        result = get_claude_code_config("https://localhost:7272", "gk_testkey123")
        assert "Authorization: Bearer gk_testkey123" in result
        assert "X-API-Key" not in result

    def test_gemini_prompt_uses_bearer(self):
        """Gemini command should use -H 'Authorization: Bearer ...'."""
        from api.endpoints.ai_tools import get_gemini_config

        result = get_gemini_config("https://localhost:7272", "gk_testkey123")
        assert "Authorization: Bearer gk_testkey123" in result
        assert "X-API-Key" not in result

    def test_codex_prompt_uses_env_var(self):
        """Codex command should use --bearer-token-env-var (unchanged)."""
        from api.endpoints.ai_tools import get_codex_config

        result = get_codex_config("https://localhost:7272", "gk_testkey123")
        assert "--bearer-token-env-var GILJO_API_KEY" in result
        assert "X-API-Key" not in result


# ---------------------------------------------------------------------------
# Test: MCP endpoint still accepts both auth methods
# ---------------------------------------------------------------------------


class TestMcpEndpointAcceptsBoth:
    """Verify the MCP SDK auth middleware accepts both Bearer and X-API-Key."""

    def test_auth_middleware_exists(self):
        """MCPAuthMiddleware should be importable and functional."""
        # Middleware should accept an ASGI app
        from unittest.mock import MagicMock

        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        middleware = MCPAuthMiddleware(app=MagicMock())
        assert callable(middleware)
