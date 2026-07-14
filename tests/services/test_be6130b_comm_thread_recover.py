# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6130b regression: CommThread soft-delete -> recover round-trip.

CommThread already had ``deleted_at`` (ce_0057); BE-6130b added the user-facing
RECOVER half (list-deleted + restore). These tests prove, at the service layer:

* a soft-deleted thread is excluded from every normal read (list / history /
  search) and surfaces only in ``list_deleted_threads``;
* ``restore_thread`` round-trips it back (and it leaves the trash);
* tenant isolation holds on both list-deleted and restore.

Real DB (rollback-isolated ``db_session``), no mocks — parallel-safe: each test
mints its own tenant key, no module-level mutable state.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.comm import CommThread
from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.taxonomy_ops import ensure_default_types_seeded
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


def _tk(suffix: str) -> str:
    return f"tk_be6130b_cht_{suffix}"


def _service(db_manager, db_session) -> CommThreadService:
    return CommThreadService(db_manager, TenantManager(), session=db_session)


async def _seed(db_session, tenant: str) -> None:
    with tenant_session_context(db_session, tenant):
        await ensure_default_types_seeded(db_session, tenant)


async def test_delete_then_recover_round_trips(db_manager, db_session):
    tenant = _tk("roundtrip")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="recover me", creator_id="agent-a", tenant_key=tenant)
    tid = thread["thread_id"]
    chat_id = thread["chat_id"]

    # Live read sees it.
    listing = await svc.list_threads(tenant_key=tenant)
    assert tid in {t["thread_id"] for t in listing["threads"]}

    # Soft-delete (trash).
    await svc.delete_thread(thread_id=tid, tenant_key=tenant)

    # Excluded from EVERY normal read.
    listing = await svc.list_threads(tenant_key=tenant)
    assert tid not in {t["thread_id"] for t in listing["threads"]}
    found = await svc.search_threads(query="recover me", tenant_key=tenant)
    assert tid not in {t["thread_id"] for t in found["threads"]}
    with pytest.raises(ResourceNotFoundError):
        await svc.get_thread_history(thread_id=tid, tenant_key=tenant)

    # Surfaces ONLY in the trash, with a deleted_at stamp.
    trashed = await svc.list_deleted_threads(tenant_key=tenant)
    trashed_ids = {t["thread_id"] for t in trashed["threads"]}
    assert tid in trashed_ids
    assert next(t for t in trashed["threads"] if t["thread_id"] == tid)["deleted_at"] is not None

    # Restore brings it back, keeping its original CHT serial (never re-minted).
    restored = await svc.restore_thread(thread_id=tid, tenant_key=tenant)
    assert restored["chat_id"] == chat_id

    listing = await svc.list_threads(tenant_key=tenant)
    assert tid in {t["thread_id"] for t in listing["threads"]}
    history = await svc.get_thread_history(thread_id=tid, tenant_key=tenant)
    assert history["thread"]["thread_id"] == tid
    # And it is no longer in the trash.
    trashed = await svc.list_deleted_threads(tenant_key=tenant)
    assert tid not in {t["thread_id"] for t in trashed["threads"]}


async def test_restore_unknown_or_live_thread_raises(db_manager, db_session):
    tenant = _tk("notfound")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    # A live (never-deleted) thread cannot be "restored".
    thread = await svc.create_thread(subject="live", creator_id="agent-a", tenant_key=tenant)
    with pytest.raises(ResourceNotFoundError):
        await svc.restore_thread(thread_id=thread["thread_id"], tenant_key=tenant)

    # A bogus id raises too.
    with pytest.raises(ResourceNotFoundError):
        await svc.restore_thread(thread_id="does-not-exist", tenant_key=tenant)


async def test_recover_window_expired_is_rejected(db_manager, db_session):
    """BE-6130b decision A: a thread trashed more than 30 days ago can no longer
    be recovered — restore raises ValidationError and the row stays trashed."""
    tenant = _tk("expired")
    await _seed(db_session, tenant)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="old", creator_id="agent-a", tenant_key=tenant)
    tid = thread["thread_id"]
    await svc.delete_thread(thread_id=tid, tenant_key=tenant)

    # Backdate deleted_at beyond the 30-day window.
    with tenant_session_context(db_session, tenant):
        await db_session.execute(
            update(CommThread).where(CommThread.id == tid).values(deleted_at=datetime.now(UTC) - timedelta(days=31))
        )
        await db_session.flush()

    with pytest.raises(ValidationError):
        await svc.restore_thread(thread_id=tid, tenant_key=tenant)

    # Still in the trash (not resurrected).
    trashed = await svc.list_deleted_threads(tenant_key=tenant)
    assert tid in {t["thread_id"] for t in trashed["threads"]}


async def test_recover_is_tenant_isolated(db_manager, db_session):
    owner = _tk("owner")
    intruder = _tk("intruder")
    await _seed(db_session, owner)
    await _seed(db_session, intruder)
    svc = _service(db_manager, db_session)

    thread = await svc.create_thread(subject="secret", creator_id="agent-a", tenant_key=owner)
    tid = thread["thread_id"]
    await svc.delete_thread(thread_id=tid, tenant_key=owner)

    # The intruder tenant neither sees the trashed thread nor can restore it.
    intruder_trash = await svc.list_deleted_threads(tenant_key=intruder)
    assert tid not in {t["thread_id"] for t in intruder_trash["threads"]}
    with pytest.raises(ResourceNotFoundError):
        await svc.restore_thread(thread_id=tid, tenant_key=intruder)

    # The owner still can.
    owner_trash = await svc.list_deleted_threads(tenant_key=owner)
    assert tid in {t["thread_id"] for t in owner_trash["threads"]}
    await svc.restore_thread(thread_id=tid, tenant_key=owner)
