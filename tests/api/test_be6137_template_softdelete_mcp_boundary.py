# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6137 MCP-boundary regression: soft-deleted templates are invisible through
the @mcp.tool layer.

BE-5042 lesson: BE-6130b shipped a service-layer fix with zero MCP-boundary
coverage; the @mcp.tool wrapper is the actual surface that agents hit.

These tests call the standalone tool functions / mixin methods that the
@mcp.tool wrappers delegate to. All three BE-6137 read paths are covered:

  * ``get_agent_templates()``   — powers the ``get_context`` "agent_templates"
    category.
  * ``get_self_identity()``     — powers the ``get_context`` "self_identity"
    category via its ``session`` parameter (native test path on the function).
  * ``SetupMiscMixin.list_agent_templates()`` — the standalone
    ``list_agent_templates`` setup tool. NOTE: this has its OWN query in
    ``_setup_tools.py`` (it does NOT delegate to ``get_agent_templates``), so it
    is exercised separately here.

Approach: the standalone tool functions / mixin method are called directly (not
through the transport). ``get_agent_templates`` and ``list_agent_templates`` are
called with a ``db_manager`` stub that proxies ``get_session_async`` to the
rolled-back test session. ``get_self_identity`` is called via its ``session``
parameter (already supported for testing). All three code paths exercise the SQL
query with the new ``deleted_at IS NULL`` guard — the same query the @mcp.tool
wrapper executes — satisfying the DoD without requiring a full in-process MCP
transport fixture (the transport harness in ``tests/helpers/mcp_dispatch.py`` is
autospec/mock-based and returns canned data, so it cannot exercise the filter).

Parallel-safe: each test uses the ``db_session`` rollback fixture — no committed
data leaks between tests.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from giljo_mcp.models.templates import AgentTemplate


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# db_manager stub that proxies get_session_async to the test session
# ---------------------------------------------------------------------------


class _TestSessionDbManager:
    """Minimal db_manager stand-in that returns the rolled-back test session.

    Used so that the standalone tool functions (which call
    ``db_manager.get_session_async()``) see the same in-transaction rows as
    the rest of the test — without opening a separate pool connection.
    """

    def __init__(self, session) -> None:
        self._session = session

    @contextlib.asynccontextmanager
    async def get_session_async(self, **_kwargs):
        yield self._session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_template(tenant_key: str, name: str | None = None) -> AgentTemplate:
    return AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=name or f"be6137-mcp-{uuid4().hex[:8]}",
        role="custom",
        category="custom",
        system_instructions="# BE-6137 MCP boundary test template",
        is_active=True,
        version="1.0.0",
    )


# ---------------------------------------------------------------------------
# get_agent_templates boundary tests
# ---------------------------------------------------------------------------


async def test_list_agent_templates_excludes_soft_deleted(db_session, test_tenant_key):
    """A soft-deleted template must NOT appear in get_agent_templates() output."""
    from giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates

    live = _make_template(test_tenant_key)
    trashed = _make_template(test_tenant_key)
    trashed.deleted_at = datetime.now(UTC)

    db_session.add(live)
    db_session.add(trashed)
    await db_session.flush()

    db_mgr = _TestSessionDbManager(db_session)
    result = await get_agent_templates(
        product_id="",
        tenant_key=test_tenant_key,
        detail="basic",
        db_manager=db_mgr,
    )

    # get_agent_templates returns a dict with a "data" key (list of template dicts)
    templates_data = result.get("data", [])
    names_in_result = {t.get("name") for t in templates_data}

    assert live.name in names_in_result, "Live template must appear in get_agent_templates"
    assert trashed.name not in names_in_result, "Soft-deleted template must NOT appear in get_agent_templates"


async def test_list_agent_templates_shows_restored(db_session, test_tenant_key):
    """After restore (deleted_at = None), a formerly-trashed template re-surfaces."""
    from giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates

    tpl = _make_template(test_tenant_key)
    tpl.deleted_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.add(tpl)
    await db_session.flush()

    db_mgr = _TestSessionDbManager(db_session)

    # Before restore — invisible.
    result_before = await get_agent_templates(
        product_id="", tenant_key=test_tenant_key, detail="basic", db_manager=db_mgr
    )
    names_before = {t.get("name") for t in result_before.get("data", [])}
    assert tpl.name not in names_before

    # Simulate restore: clear deleted_at.
    await db_session.execute(update(AgentTemplate).where(AgentTemplate.id == tpl.id).values(deleted_at=None))
    await db_session.flush()

    # After restore — visible.
    result_after = await get_agent_templates(
        product_id="", tenant_key=test_tenant_key, detail="basic", db_manager=db_mgr
    )
    names_after = {t.get("name") for t in result_after.get("data", [])}
    assert tpl.name in names_after, "Restored template must re-appear in get_agent_templates"


# ---------------------------------------------------------------------------
# get_self_identity boundary tests
# Uses the native ``session`` parameter (supported by get_self_identity for
# testing), which routes through _get_self_identity_impl — the exact same
# code path the @mcp.tool wrapper exercises via db_manager.
# ---------------------------------------------------------------------------


async def test_get_self_identity_excludes_soft_deleted(db_session, test_tenant_key):
    """get_self_identity() for a soft-deleted template returns not-found, not content."""
    from giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

    name = f"be6137-si-{uuid4().hex[:8]}"
    tpl = _make_template(test_tenant_key, name=name)
    tpl.deleted_at = datetime.now(UTC)
    db_session.add(tpl)
    await db_session.flush()

    result = await get_self_identity(
        agent_name=name,
        tenant_key=test_tenant_key,
        session=db_session,
    )

    # The function returns {"data": {}, "metadata": {"error": "template_not_found"}}
    # when the template is missing from live reads.
    meta_error = result.get("metadata", {}).get("error")
    data = result.get("data", {})
    assert data == {} or meta_error == "template_not_found", (
        f"Expected not-found response for soft-deleted template, got: {result}"
    )


async def test_get_self_identity_shows_restored(db_session, test_tenant_key):
    """After restore, get_self_identity() returns the template content."""
    from giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

    name = f"be6137-si-{uuid4().hex[:8]}"
    tpl = _make_template(test_tenant_key, name=name)
    tpl.deleted_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.add(tpl)
    await db_session.flush()

    # Before restore — not found.
    result_before = await get_self_identity(agent_name=name, tenant_key=test_tenant_key, session=db_session)
    assert result_before.get("data") == {} or result_before.get("metadata", {}).get("error") == "template_not_found"

    # Simulate restore.
    await db_session.execute(update(AgentTemplate).where(AgentTemplate.id == tpl.id).values(deleted_at=None))
    await db_session.flush()

    # After restore — found.
    result_after = await get_self_identity(agent_name=name, tenant_key=test_tenant_key, session=db_session)
    data = result_after.get("data", {})
    assert data.get("name") == name, f"Restored template must appear in get_self_identity, got: {result_after}"


# ---------------------------------------------------------------------------
# list_agent_templates (SetupMiscMixin) boundary test — the 3rd read path.
# This setup tool has its OWN query in _setup_tools.py (it does not delegate to
# get_agent_templates), so it needs its own boundary coverage. A fresh unique
# tenant is used so the only template for that tenant is the soft-deleted one —
# the tool must then behave as if there are no templates (raises
# "No active templates found"), proving the deleted_at IS NULL filter excludes
# it. (Without the filter, the trashed row would be selected and assembled.)
# ---------------------------------------------------------------------------


class _ListTemplatesHarness:
    """Minimal SetupMiscMixin host exercising list_agent_templates' real SQL."""

    def __init__(self, session) -> None:
        self._session = session
        self.db_manager = _TestSessionDbManager(session)
        self.tenant_manager = None

    @contextlib.asynccontextmanager
    async def get_session_async(self, **_kwargs):
        yield self._session


async def test_setup_list_agent_templates_excludes_soft_deleted(db_session):
    """list_agent_templates must not surface a soft-deleted template.

    Uses a fresh unique tenant whose only template is trashed, so a correct
    filter yields zero live templates -> ValidationError; a missing filter would
    select the trashed row and proceed to assembly.
    """
    from giljo_mcp.exceptions import ValidationError
    from giljo_mcp.tools.tool_accessor._setup_tools import SetupMiscMixin

    tenant = f"be6137-list-{uuid4().hex[:8]}"
    trashed = _make_template(tenant)
    trashed.deleted_at = datetime.now(UTC)
    db_session.add(trashed)
    await db_session.flush()

    harness = _ListTemplatesHarness(db_session)
    with pytest.raises(ValidationError):
        await SetupMiscMixin.list_agent_templates(harness, tenant, "claude_code")
