# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Service-layer tests for the BE-9012a read cursor (D6) + acted-on state (D4).

Complements the MCP-boundary test (test_be9012a_cursor_read_mcp_boundary.py) with
the two correctness details the transport tests cannot see cleanly:

- ADR-009 Teams-readiness: the cursor is per-(thread, participant); two
  participants on the SAME thread have INDEPENDENT cursors (never per-user shared
  state). One reader draining does not advance another's cursor.
- Watermark-guard: mark_read combined with a NARROWING filter (directed/action)
  or truncation must NOT advance the drain watermark — advancing it would silently
  skip unread posts the filter excluded. The junction ack still records exactly
  what was seen.

Real DB (rollback-isolated ``db_session``), no mocks. created_at is
``func.now()`` = Postgres transaction time, so posts here share a timestamp unless
stamped; we stamp distinct increasing times where the cursor advance is asserted.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models.comm import CommParticipant
from giljo_mcp.models.tasks import Message, MessageAcknowledgment
from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.taxonomy_ops import ensure_default_types_seeded
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio

_T1 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
_T2 = datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)


def _tk(suffix: str) -> str:
    return f"tk_be9012a_{suffix}"


def _service(db_manager, db_session) -> CommThreadService:
    return CommThreadService(db_manager, TenantManager(), session=db_session)


async def _seed(db_session, tenant: str) -> None:
    with tenant_session_context(db_session, tenant):
        await ensure_default_types_seeded(db_session, tenant)


async def _post(svc, tid, tenant, content, **kwargs) -> str:
    res = await svc.post_to_thread(thread_id=tid, content=content, from_agent="alpha", tenant_key=tenant, **kwargs)
    return res["message_id"]


async def _stamp(db_session, tenant, ids_ts) -> None:
    with tenant_session_context(db_session, tenant):
        for mid, ts in ids_ts:
            await db_session.execute(sa_update(Message).where(Message.id == mid).values(created_at=ts))
        await db_session.flush()


async def _cursor_row(db_session, tenant, tid, participant_id) -> CommParticipant:
    with tenant_session_context(db_session, tenant):
        res = await db_session.execute(
            select(CommParticipant).where(
                CommParticipant.tenant_key == tenant,
                CommParticipant.thread_id == tid,
                CommParticipant.participant_id == participant_id,
            )
        )
    return res.scalar_one()


async def test_cursor_is_per_participant_independent(db_manager, db_session):
    """ADR-009: beta draining its unread does NOT touch gamma's cursor. The cursor
    is per-(thread, participant), tenant-scoped — never a shared per-user watermark."""
    tenant = _tk("indep")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="t", creator_id="alpha", tenant_key=tenant)
    tid = thread["thread_id"]
    await svc.join_thread(thread_id=tid, participant_id="beta", tenant_key=tenant)
    await svc.join_thread(thread_id=tid, participant_id="gamma", tenant_key=tenant)
    m1 = await _post(svc, tid, tenant, "one")
    m2 = await _post(svc, tid, tenant, "two")
    await _stamp(db_session, tenant, [(m1, _T1), (m2, _T2)])

    # beta drains both.
    beta_first = await svc.get_thread_history(
        thread_id=tid, as_participant="beta", unread_only=True, mark_read=True, tenant_key=tenant
    )
    assert beta_first["count"] == 2
    # beta re-reads: cursor advanced -> nothing new.
    beta_second = await svc.get_thread_history(
        thread_id=tid, as_participant="beta", unread_only=True, tenant_key=tenant
    )
    assert beta_second["count"] == 0

    # gamma's cursor is untouched -> gamma still sees both as unread.
    gamma = await svc.get_thread_history(thread_id=tid, as_participant="gamma", unread_only=True, tenant_key=tenant)
    assert gamma["count"] == 2

    # And the DB proves it: beta's cursor advanced, gamma's is still NULL.
    beta_row = await _cursor_row(db_session, tenant, tid, "beta")
    gamma_row = await _cursor_row(db_session, tenant, tid, "gamma")
    assert beta_row.last_read_message_id == m2
    assert beta_row.last_read_at is not None
    assert gamma_row.last_read_message_id is None
    assert gamma_row.last_read_at is None


async def test_narrowed_mark_read_does_not_advance_watermark(db_manager, db_session):
    """The corruption guard: mark_read + action_required_only acks the action post
    but must NOT advance the drain watermark past the unread broadcast below it.
    A later unread_only read must still return BOTH posts (cursor never moved)."""
    tenant = _tk("guard")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="t", creator_id="alpha", tenant_key=tenant)
    tid = thread["thread_id"]
    await svc.join_thread(thread_id=tid, participant_id="beta", tenant_key=tenant)
    m1 = await _post(svc, tid, tenant, "broadcast", requires_action=False)  # older
    m2 = await _post(svc, tid, tenant, "please act", requires_action=True)  # newer
    await _stamp(db_session, tenant, [(m1, _T1), (m2, _T2)])

    # Narrowed mark_read: returns only the action post, acks it, but must hold the cursor.
    narrowed = await svc.get_thread_history(
        thread_id=tid,
        as_participant="beta",
        action_required_only=True,
        mark_read=True,
        tenant_key=tenant,
    )
    assert [m["content"] for m in narrowed["messages"]] == ["please act"]

    # D4 ack recorded for the action post only.
    with tenant_session_context(db_session, tenant):
        acked = (
            (
                await db_session.execute(
                    select(MessageAcknowledgment.message_id).where(
                        MessageAcknowledgment.tenant_key == tenant,
                        MessageAcknowledgment.agent_id == "beta",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert set(acked) == {m2}

    # Watermark NOT advanced: cursor row still NULL, so a plain unread read sees BOTH.
    beta_row = await _cursor_row(db_session, tenant, tid, "beta")
    assert beta_row.last_read_at is None
    unread = await svc.get_thread_history(thread_id=tid, as_participant="beta", unread_only=True, tenant_key=tenant)
    assert unread["count"] == 2  # the older broadcast was NOT silently skipped


async def test_full_drain_advances_cursor_and_re_ack_is_idempotent(db_manager, db_session):
    """A clean unread drain advances the persisted cursor exactly once and acks each
    post once; repeating the drain is a no-op (no new rows, count 0)."""
    tenant = _tk("drain")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="t", creator_id="alpha", tenant_key=tenant)
    tid = thread["thread_id"]
    await svc.join_thread(thread_id=tid, participant_id="beta", tenant_key=tenant)
    m1 = await _post(svc, tid, tenant, "one")
    m2 = await _post(svc, tid, tenant, "two")
    await _stamp(db_session, tenant, [(m1, _T1), (m2, _T2)])

    async def _ack_count() -> int:
        with tenant_session_context(db_session, tenant):
            res = await db_session.execute(
                select(func.count())
                .select_from(MessageAcknowledgment)
                .where(
                    MessageAcknowledgment.tenant_key == tenant,
                    MessageAcknowledgment.agent_id == "beta",
                )
            )
        return res.scalar_one()

    first = await svc.get_thread_history(
        thread_id=tid, as_participant="beta", unread_only=True, mark_read=True, tenant_key=tenant
    )
    assert first["count"] == 2 and first["marked_read"] == 2
    assert await _ack_count() == 2
    row = await _cursor_row(db_session, tenant, tid, "beta")
    assert row.last_read_message_id == m2

    second = await svc.get_thread_history(
        thread_id=tid, as_participant="beta", unread_only=True, mark_read=True, tenant_key=tenant
    )
    assert second["count"] == 0 and second["marked_read"] == 0
    assert await _ack_count() == 2  # idempotent — no new ack rows
