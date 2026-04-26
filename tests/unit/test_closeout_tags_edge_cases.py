# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
BE-5032 verification: edge-case coverage for the agent-supplied `tags` parameter
on close_project_and_update_memory.

Covers items the implementer's primary suite did not pin:

  * Every one of the 16 CONTROLLED_TAG_VOCABULARY entries is acceptable
    (proves no enum mismatch between the docs and the validator).
  * Boundary at MEMORY_TAGS_COUNT (8 accepted, 9 rejected).
  * Duplicate tags ['refactor', 'refactor'] persist verbatim (no implicit dedup;
    matches write_360_memory's strict-pass-through behaviour via the shared
    MemoryEntryWriteSchema).
  * Whitespace-padded tags ['  refactor  '] are rejected (str_strip_whitespace=False
    on the shared schema; matches write_360_memory).
  * action_required:<title> free-form prefix is accepted (preserves the deferred-
    finding workflow described in the closeout protocol prose).
  * Production call path: ToolAccessor.close_project_and_update_memory threads
    `tags` through to the underlying tool function. This is the surface used by
    project_lifecycle_service.execute_closeout(), so a regression here would
    silently drop tags for the live closeout path.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.memory_entry_write_validator import (
    CONTROLLED_TAG_VOCABULARY,
    MEMORY_TAGS_COUNT,
    MemoryEntryWriteValidationError,
)
from giljo_mcp.tools.project_closeout import close_project_and_update_memory


def _build_session_mocks(tenant_key: str):
    """Return (mock_session, mock_db_manager, project_id) plumbed for a single closeout."""
    project_id = str(uuid4())
    product_id = str(uuid4())

    mock_project = MagicMock(spec=Project)
    mock_project.id = project_id
    mock_project.tenant_key = tenant_key
    mock_project.product_id = product_id
    mock_project.created_at = datetime.now(timezone.utc)
    mock_project.completed_at = None
    mock_project.name = "BE-5032 edge-case project"

    mock_product = MagicMock(spec=Product)
    mock_product.id = product_id
    mock_product.tenant_key = tenant_key
    mock_product.product_memory = {}

    mock_session = AsyncMock()
    mock_db_manager = MagicMock()
    mock_db_manager.get_session_async.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db_manager.get_session_async.return_value.__aexit__ = AsyncMock(return_value=False)

    call_count = {"n": 0}

    async def mock_execute(*_args, **_kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.scalar_one_or_none.return_value = mock_project
        elif call_count["n"] == 2:
            result.scalar_one_or_none.return_value = mock_product
        else:
            scalars = MagicMock()
            scalars.all.return_value = []
            result.scalars.return_value = scalars
        return result

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    return mock_session, mock_db_manager, project_id


async def _run_closeout(*, project_id, db_manager, tenant_key, tags, captured):
    """Invoke the closeout and capture the persisted MemoryEntryWriteSchema."""
    mock_entry = MagicMock()
    mock_entry.id = str(uuid4())
    mock_entry.to_dict.return_value = {"id": str(mock_entry.id)}

    async def _capture_create(params, session):
        captured["params"] = params
        return mock_entry

    with patch("giljo_mcp.tools.project_closeout.ProductMemoryService") as mock_svc_cls:
        svc = mock_svc_cls.return_value
        svc.get_next_sequence = AsyncMock(return_value=1)
        svc.create_entry = AsyncMock(side_effect=_capture_create)

        with patch(
            "giljo_mcp.tools.project_closeout.emit_websocket_event",
            new_callable=AsyncMock,
        ):
            return await close_project_and_update_memory(
                project_id=project_id,
                summary="Edge-case closeout",
                key_outcomes=["outcome"],
                decisions_made=["decision"],
                tags=tags,
                tenant_key=tenant_key,
                db_manager=db_manager,
                force=False,
                git_commits=[],
            )


# ---------------------------------------------------------------------------
# 1. Every controlled-vocab tag is accepted (no doc/validator drift)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tag", sorted(CONTROLLED_TAG_VOCABULARY))
@pytest.mark.asyncio
async def test_every_controlled_vocab_tag_is_accepted(tag):
    """Each of the 16 vocab tags must round-trip through closeout without rejection."""
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    await _run_closeout(
        project_id=project_id,
        db_manager=db_manager,
        tenant_key=tenant_key,
        tags=[tag],
        captured=captured,
    )

    assert captured["params"].tags == [tag]


# ---------------------------------------------------------------------------
# 2. MEMORY_TAGS_COUNT cap boundary (8 accepted, 9 rejected)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tags_at_cap_are_accepted():
    """Exactly MEMORY_TAGS_COUNT tags (8) must pass."""
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    eight = sorted(CONTROLLED_TAG_VOCABULARY)[:MEMORY_TAGS_COUNT]
    assert len(eight) == MEMORY_TAGS_COUNT  # vocab must have at least 8 entries

    await _run_closeout(
        project_id=project_id,
        db_manager=db_manager,
        tenant_key=tenant_key,
        tags=eight,
        captured=captured,
    )

    assert captured["params"].tags == eight


@pytest.mark.asyncio
async def test_tags_over_cap_are_rejected():
    """MEMORY_TAGS_COUNT + 1 tags must raise MemoryEntryWriteValidationError."""
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    nine = sorted(CONTROLLED_TAG_VOCABULARY)[: MEMORY_TAGS_COUNT + 1]
    assert len(nine) == MEMORY_TAGS_COUNT + 1

    with pytest.raises(MemoryEntryWriteValidationError) as exc_info:
        await _run_closeout(
            project_id=project_id,
            db_manager=db_manager,
            tenant_key=tenant_key,
            tags=nine,
            captured=captured,
        )

    assert exc_info.value.field == "tags"
    assert "params" not in captured


# ---------------------------------------------------------------------------
# 3. Duplicate handling: persist verbatim (matches write_360_memory)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_tags_persist_verbatim():
    """Duplicates are NOT silently deduped; the validator passes them through unchanged.

    This pins the contract shared with write_360_memory: the closeout path does
    NOT apply clean_tags() / dedup / lowercasing. Agents are expected to supply
    a clean list. If we ever decide to dedup, both write paths must change
    together.
    """
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    await _run_closeout(
        project_id=project_id,
        db_manager=db_manager,
        tenant_key=tenant_key,
        tags=["refactor", "refactor"],
        captured=captured,
    )

    assert captured["params"].tags == ["refactor", "refactor"]


# ---------------------------------------------------------------------------
# 4. Whitespace handling: rejected (matches write_360_memory)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_whitespace_padded_tags_are_rejected():
    """'  refactor  ' is NOT in CONTROLLED_TAG_VOCABULARY -> rejected.

    The shared MemoryEntryWriteSchema sets str_strip_whitespace=False, so the
    write boundary is intentionally strict. Agents must trim before calling.
    Same behaviour as write_360_memory.
    """
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    with pytest.raises(MemoryEntryWriteValidationError) as exc_info:
        await _run_closeout(
            project_id=project_id,
            db_manager=db_manager,
            tenant_key=tenant_key,
            tags=["  refactor  "],
            captured=captured,
        )

    assert exc_info.value.field == "tags"
    assert exc_info.value.invalid_tag == "  refactor  "
    assert "params" not in captured


# ---------------------------------------------------------------------------
# 5. action_required:<title> free-form prefix is accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_required_prefix_tag_is_accepted():
    """`action_required:<title>` is the documented free-form escape hatch.

    Closeout protocol prose (agent_lifecycle.py:218-220) tells orchestrators to
    use these tags for deferred findings. The validator must accept them so the
    documented workflow does not break.
    """
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    tag = "action_required:src/foo.py -- ruff RUF100 cleanup"
    await _run_closeout(
        project_id=project_id,
        db_manager=db_manager,
        tenant_key=tenant_key,
        tags=[tag, "chore"],
        captured=captured,
    )

    assert captured["params"].tags == [tag, "chore"]


@pytest.mark.asyncio
async def test_action_required_prefix_with_empty_title_is_rejected():
    """`action_required:` with no title after the colon must fail validation."""
    tenant_key = "test-tenant"
    _, db_manager, project_id = _build_session_mocks(tenant_key)
    captured: dict = {}

    with pytest.raises(MemoryEntryWriteValidationError) as exc_info:
        await _run_closeout(
            project_id=project_id,
            db_manager=db_manager,
            tenant_key=tenant_key,
            tags=["action_required:"],
            captured=captured,
        )

    assert exc_info.value.field == "tags"
    assert "params" not in captured


# ---------------------------------------------------------------------------
# 6. Production boundary: ToolAccessor threads tags through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_accessor_threads_tags_through_to_tool_function():
    """ToolAccessor.close_project_and_update_memory must forward `tags` verbatim.

    This is the surface that project_lifecycle_service.execute_closeout() and
    the MCP SDK tool registration both reach. A regression here would silently
    drop tags for the live closeout path even though the function-level tests
    stay green.
    """
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    accessor = ToolAccessor.__new__(ToolAccessor)
    accessor.db_manager = MagicMock()

    captured_kwargs: dict = {}

    async def fake_tool_func(**kwargs):
        captured_kwargs.update(kwargs)
        return {"ok": True}

    with patch(
        "giljo_mcp.tools.project_closeout.close_project_and_update_memory",
        new=fake_tool_func,
    ):
        result = await accessor.close_project_and_update_memory(
            project_id="proj-1",
            summary="boundary test",
            key_outcomes=["a"],
            decisions_made=["b"],
            tenant_key="test-tenant",
            tags=["refactor", "backend"],
        )

    assert result == {"ok": True}
    assert captured_kwargs["tags"] == ["refactor", "backend"]
    # tenant_key is required and must reach the tool fn
    assert captured_kwargs["tenant_key"] == "test-tenant"
    # db_manager must be injected by the accessor
    assert "db_manager" in captured_kwargs


@pytest.mark.asyncio
async def test_tool_accessor_passes_none_tags_through():
    """tags=None at the accessor surface must arrive as None at the tool function."""
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    accessor = ToolAccessor.__new__(ToolAccessor)
    accessor.db_manager = MagicMock()

    captured_kwargs: dict = {}

    async def fake_tool_func(**kwargs):
        captured_kwargs.update(kwargs)
        return {"ok": True}

    with patch(
        "giljo_mcp.tools.project_closeout.close_project_and_update_memory",
        new=fake_tool_func,
    ):
        await accessor.close_project_and_update_memory(
            project_id="proj-1",
            summary="boundary test",
            key_outcomes=["a"],
            decisions_made=["b"],
            tenant_key="test-tenant",
        )

    # Default is None; must be forwarded as None (not silently coerced to [])
    assert captured_kwargs["tags"] is None
