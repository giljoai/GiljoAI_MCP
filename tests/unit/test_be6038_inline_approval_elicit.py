# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6038 (project BE-6255): inline approval-card overlay -- server-side logic.

Covers the dormant-by-default overlay on ``request_approval``: capability + flag gating,
decide-convergence through the EXISTING ``UserApprovalService.mark_decided`` (no 2nd write
path), and robust fallback to today's async ``awaiting_user`` behavior on every miss.

Parallel-safe: no DB, no module-level mutable state. The feature flag is toggled with
``monkeypatch.setenv``; all collaborators are mocked.

NO-SHIP-UNTIL-GA: end-to-end inline rendering is transport-gated (constraint C1); these
tests exercise the reusable server-side decide-convergence logic with a mocked ``ctx``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.endpoints.mcp_tools._inline_approval import maybe_elicit_approval_inline
from giljo_mcp.exceptions import ValidationError


_FLAG = "GILJO_INLINE_APPROVAL_ELICIT"
_OPTIONS = [{"id": "approve", "label": "Approve"}, {"id": "reject", "label": "Reject"}]
_PENDING = {"approval_id": "ap-1", "status": "pending"}


def _make_ctx(*, supports: bool = True, elicit_action: str = "accept", choice: str = "approve", raises=None):
    """Build a mock Context with a session capability probe + an elicit coroutine."""
    ctx = MagicMock()
    ctx.session.check_client_capability.return_value = supports
    if raises is not None:
        ctx.elicit = AsyncMock(side_effect=raises)
    else:
        data = SimpleNamespace(choice=choice) if elicit_action == "accept" else None
        ctx.elicit = AsyncMock(return_value=SimpleNamespace(action=elicit_action, data=data))
    return ctx


def _wire_accessor(monkeypatch, *, mark_decided: AsyncMock) -> AsyncMock:
    """Point the inline-decide helpers at a mocked tool accessor + tenant/user resolvers."""
    accessor = MagicMock()
    accessor._user_approval_service.mark_decided = mark_decided
    monkeypatch.setattr("api.endpoints.mcp_tools._base._get_tool_accessor", lambda: accessor)
    monkeypatch.setattr("api.endpoints.mcp_tools._base._resolve_tenant", lambda ctx: "tenant-1")
    monkeypatch.setattr("api.endpoints.mcp_tools._base._resolve_user_id", lambda ctx: "user-9")
    return mark_decided


@pytest.mark.asyncio
async def test_flag_off_returns_unchanged_and_never_elicits(monkeypatch):
    monkeypatch.delenv(_FLAG, raising=False)
    ctx = _make_ctx()
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING
    ctx.elicit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ctx_none_returns_unchanged(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    out = await maybe_elicit_approval_inline(None, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING


@pytest.mark.asyncio
async def test_flag_on_no_client_capability_falls_back(monkeypatch):
    monkeypatch.setenv(_FLAG, "true")
    ctx = _make_ctx(supports=False)
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING
    ctx.elicit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_routes_through_mark_decided(monkeypatch):
    monkeypatch.setenv(_FLAG, "on")
    mark = _wire_accessor(monkeypatch, mark_decided=AsyncMock(return_value=MagicMock()))
    ctx = _make_ctx(elicit_action="accept", choice="approve")

    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)

    assert out["status"] == "decided"
    assert out["decided_option_id"] == "approve"
    assert out["surface"] == "inline"
    assert out["approval_id"] == "ap-1"
    mark.assert_awaited_once_with(tenant_key="tenant-1", approval_id="ap-1", option_id="approve", user_id="user-9")


@pytest.mark.asyncio
async def test_decline_leaves_pending_and_does_not_decide(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    mark = _wire_accessor(monkeypatch, mark_decided=AsyncMock())
    ctx = _make_ctx(elicit_action="decline")
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING
    mark.assert_not_awaited()


@pytest.mark.asyncio
async def test_elicit_unavailable_falls_back(monkeypatch):
    # Constraint C1: transport may not carry the round-trip -> elicit raises -> async fallback.
    monkeypatch.setenv(_FLAG, "1")
    mark = _wire_accessor(monkeypatch, mark_decided=AsyncMock())
    ctx = _make_ctx(raises=RuntimeError("no stream for server-initiated request"))
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING
    mark.assert_not_awaited()


@pytest.mark.asyncio
async def test_dashboard_race_marks_decided_validationerror_falls_back(monkeypatch):
    # Concurrent dashboard decision -> mark_decided raises (not pending) -> async fallback.
    monkeypatch.setenv(_FLAG, "1")
    mark = _wire_accessor(monkeypatch, mark_decided=AsyncMock(side_effect=ValidationError("not pending")))
    ctx = _make_ctx(elicit_action="accept", choice="approve")
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING  # unchanged; gate already cleared elsewhere
    mark.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_choice_falls_back(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    mark = _wire_accessor(monkeypatch, mark_decided=AsyncMock())
    ctx = _make_ctx(elicit_action="accept", choice="not-an-option")
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=_OPTIONS)
    assert out == _PENDING
    mark.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_pending_result_unchanged(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    ctx = _make_ctx()
    already = {"approval_id": "ap-2", "status": "decided"}
    out = await maybe_elicit_approval_inline(ctx, dict(already), reason="r", options=_OPTIONS)
    assert out == already
    ctx.elicit.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_options_falls_back(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    ctx = _make_ctx()
    out = await maybe_elicit_approval_inline(ctx, dict(_PENDING), reason="r", options=[])
    assert out == _PENDING
    ctx.elicit.assert_not_awaited()
