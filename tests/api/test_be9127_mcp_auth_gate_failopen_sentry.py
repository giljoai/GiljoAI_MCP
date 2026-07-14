# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9127 amendment 2 — the /mcp post-auth gate fail-open must be alertable.

Reproduce-first (Museum rule): the ``mcp_post_auth_gate_failed`` WARNING in the
CE MCP auth middleware is below the default LoggingIntegration
``event_level=ERROR``, so it produces NO Sentry event on its own. The tagged
capture lives in ``_capture_mcp_post_auth_gate_failure`` — the reachable fix
layer (the gate itself only runs behind a full authenticated /mcp request, which
is out of proportion to unit-test here; the middleware boundary is covered by the
BE-6060d transport tests). RED before the helper existed (no such attribute);
GREEN after. Also pins the CE edition-safety gate and the fail-open guarantee.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("sentry_sdk")

from api.endpoints import mcp_auth_middleware as authmw  # noqa: E402


TENANT_KEY = "tk_saasTest" + "TenantKey123456789012"  # concat: public gitleaks defang (precedent PR #240)
_DUMMY_DSN = "https://examplekey@o123456.ingest.sentry.io/123456"


def _mock_scope():
    scope = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = scope
    cm.__exit__.return_value = False
    return scope, cm


def test_post_auth_gate_failure_captures_tagged_event(monkeypatch):
    """Must FAIL before the helper existed — the fail-open produces a tagged capture."""
    monkeypatch.setenv("GILJO_MODE", "saas")
    monkeypatch.setenv("SENTRY_DSN_BACKEND", _DUMMY_DSN)
    scope, cm = _mock_scope()

    with patch("sentry_sdk.new_scope", return_value=cm), patch("sentry_sdk.capture_message") as capture:
        authmw._capture_mcp_post_auth_gate_failure(TENANT_KEY)

    scope.set_tag.assert_any_call("mcp_auth.fail_open", "post_auth_gate_failed")
    scope.set_tag.assert_any_call("tenant_key", TENANT_KEY)
    context_calls = [c for c in scope.set_context.call_args_list if c.args and c.args[0] == "mcp_auth"]
    assert context_calls, "set_context must carry the mcp_auth signal"
    capture.assert_called_once()
    assert capture.call_args.kwargs.get("level") == "error"


def test_no_capture_outside_saas(monkeypatch):
    """CE edition-safety: unset GILJO_MODE → returns before importing sentry_sdk."""
    monkeypatch.delenv("GILJO_MODE", raising=False)
    monkeypatch.setenv("SENTRY_DSN_BACKEND", _DUMMY_DSN)

    with patch("sentry_sdk.new_scope") as new_scope:
        authmw._capture_mcp_post_auth_gate_failure(TENANT_KEY)

    new_scope.assert_not_called()


def test_no_capture_without_dsn(monkeypatch):
    """No DSN configured → no capture attempt (SaaS with tracking disabled)."""
    monkeypatch.setenv("GILJO_MODE", "saas")
    monkeypatch.delenv("SENTRY_DSN_BACKEND", raising=False)

    with patch("sentry_sdk.new_scope") as new_scope:
        authmw._capture_mcp_post_auth_gate_failure(TENANT_KEY)

    new_scope.assert_not_called()


def test_sentry_failure_is_swallowed(monkeypatch):
    """A Sentry failure must never propagate out of the fail-open path."""
    monkeypatch.setenv("GILJO_MODE", "saas")
    monkeypatch.setenv("SENTRY_DSN_BACKEND", _DUMMY_DSN)

    with patch("sentry_sdk.new_scope", side_effect=RuntimeError("sentry down")) as new_scope:
        authmw._capture_mcp_post_auth_gate_failure(TENANT_KEY)  # must not raise

    assert new_scope.called
