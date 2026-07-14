# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-6140 — Request Auto Check-in: interval persistence + harness-neutral inject.

Regression at the failing layer. Before FE-6140 the operator's chosen interval
died in the composer — only the ``loop_directive`` boolean reached the backend,
and even that injected only at mission-compose time (never to a LIVE agent). This
verifies the fix end-to-end at the service/storage layer:

- the interval PERSISTS on the loop_directive message (the new
  ``messages.loop_interval_minutes`` column);
- get_thread_history surfaces ``loop_directive: {active, interval_minutes}`` and
  the terminal-status gate flips ``active`` to False on resolved/closed;
- get_my_turn surfaces ``loop_directives`` for a NON-baton, NON-orchestrator
  PARTICIPANT (the design intent: every participant polling receives it, not just
  the baton holder);
- the cadence is validated at the owning service (bounds), never written raw.

Real DB (rollback-isolated db_session), parallel-safe (no module globals).
"""

from __future__ import annotations

import pytest

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.taxonomy_ops import ensure_default_types_seeded
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


def _comm(db_session) -> CommThreadService:
    return CommThreadService(db_manager=None, tenant_manager=TenantManager(), session=db_session)


async def _seed_cht(db_session, tenant_key: str) -> None:
    from giljo_mcp.database import tenant_session_context

    with tenant_session_context(db_session, tenant_key):
        await ensure_default_types_seeded(db_session, tenant_key)


async def test_interval_persists_on_loop_directive_message(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="cadence", creator_id="orchestrator", tenant_key=tenant)
    await comm.join_thread(thread_id=thread["thread_id"], participant_id="worker-1", tenant_key=tenant)

    result = await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="please check in",
        from_agent="orchestrator",
        loop_directive=True,
        loop_interval_minutes=15,
        tenant_key=tenant,
    )
    assert result["loop_directive_armed"] is True
    assert result["loop_interval_minutes"] == 15

    # Persisted: the directive message carries the interval; the history poll
    # surface reports it active with the chosen cadence.
    history = await comm.get_thread_history(thread_id=thread["thread_id"], tenant_key=tenant)
    assert history["loop_directive"] == {"active": True, "interval_minutes": 15}
    directive_msgs = [m for m in history["messages"] if m["loop_interval_minutes"] == 15]
    assert len(directive_msgs) == 1


async def test_get_my_turn_surfaces_directive_for_non_baton_participant(db_session):
    """The keystone DoD: a participant who does NOT hold the baton still receives
    the directive + interval on its get_my_turn poll (ALL participants, not just
    the baton holder / orchestrator)."""
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    # orchestrator creates (and thus holds the baton); worker-1 merely joins.
    thread = await comm.create_thread(subject="coord", creator_id="orchestrator", tenant_key=tenant)
    await comm.join_thread(thread_id=thread["thread_id"], participant_id="worker-1", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop please",
        from_agent="orchestrator",
        loop_directive=True,
        loop_interval_minutes=20,
        tenant_key=tenant,
    )

    # worker-1 is NOT the baton owner (orchestrator is) — it must still see it.
    mine = await comm.get_my_turn(agent_id="worker-1", tenant_key=tenant)
    assert thread["thread_id"] not in {t["thread_id"] for t in mine["threads"]}
    directives = mine["loop_directives"]
    assert len(directives) == 1
    assert directives[0]["thread_id"] == thread["thread_id"]
    assert directives[0]["chat_id"].startswith("CHT-")
    assert directives[0]["interval_minutes"] == 20


async def test_directive_clears_when_thread_closed(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="closeable", creator_id="orchestrator", tenant_key=tenant)
    await comm.join_thread(thread_id=thread["thread_id"], participant_id="worker-1", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop",
        from_agent="orchestrator",
        loop_directive=True,
        loop_interval_minutes=10,
        tenant_key=tenant,
    )
    assert (await comm.get_my_turn(agent_id="worker-1", tenant_key=tenant))["loop_directives"]

    # Close the thread — the directive must go silent on both poll surfaces.
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="done",
        from_agent="orchestrator",
        set_status="closed",
        tenant_key=tenant,
    )
    history = await comm.get_thread_history(thread_id=thread["thread_id"], tenant_key=tenant)
    assert history["loop_directive"] == {"active": False, "interval_minutes": None}
    assert (await comm.get_my_turn(agent_id="worker-1", tenant_key=tenant))["loop_directives"] == []


async def test_rolling_cadence_latest_interval_wins(db_session):
    from sqlalchemy import text

    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="rolling", creator_id="orchestrator", tenant_key=tenant)
    await comm.join_thread(thread_id=thread["thread_id"], participant_id="worker-1", tenant_key=tenant)

    first = await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop every 5",
        from_agent="orchestrator",
        loop_directive=True,
        loop_interval_minutes=5,
        tenant_key=tenant,
    )
    # In production each post is its own transaction with a distinct now(); inside
    # this single test transaction both share the transaction timestamp, so age the
    # first post explicitly to assert the genuine temporal "latest wins".
    await db_session.execute(
        text("UPDATE messages SET created_at = created_at - interval '1 hour' WHERE id = :mid"),
        {"mid": first["message_id"]},
    )
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop every 30",
        from_agent="orchestrator",
        loop_directive=True,
        loop_interval_minutes=30,
        tenant_key=tenant,
    )

    history = await comm.get_thread_history(thread_id=thread["thread_id"], tenant_key=tenant)
    assert history["loop_directive"]["interval_minutes"] == 30
    mine = await comm.get_my_turn(agent_id="worker-1", tenant_key=tenant)
    assert mine["loop_directives"][0]["interval_minutes"] == 30


async def test_plain_post_does_not_carry_interval(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="quiet", creator_id="orchestrator", tenant_key=tenant)
    # A non-directive post must NOT persist a cadence even if one is supplied.
    result = await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="just chatting",
        from_agent="orchestrator",
        loop_directive=False,
        loop_interval_minutes=15,
        tenant_key=tenant,
    )
    assert result["loop_interval_minutes"] is None
    history = await comm.get_thread_history(thread_id=thread["thread_id"], tenant_key=tenant)
    assert history["loop_directive"] == {"active": False, "interval_minutes": None}


@pytest.mark.parametrize("bad_interval", [0, -5, 5000])
async def test_out_of_range_interval_is_rejected(db_session, bad_interval):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="bounds", creator_id="orchestrator", tenant_key=tenant)
    with pytest.raises(ValidationError):
        await comm.post_to_thread(
            thread_id=thread["thread_id"],
            content="bad cadence",
            from_agent="orchestrator",
            loop_directive=True,
            loop_interval_minutes=bad_interval,
            tenant_key=tenant,
        )
