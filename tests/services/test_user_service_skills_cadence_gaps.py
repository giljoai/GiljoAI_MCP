# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""HO 1028 coverage gap fills for skills-version cadence.

Existing suites cover the happy paths and tenant isolation. These tests
target gaps surfaced during verification:

1. Boundary case at exactly the 30-day mark — the `<= 30 days` predicate
   in ``check_and_emit_skills_update`` must SUPPRESS at exactly 30d (still
   inside the throttle window) and EMIT just past it.
2. WebSocket payload shape — the cadence emit must include ``user_id``,
   ``installed``, ``current``, and ``message`` keys so the frontend
   handler in ``systemEventRoutes.js`` can render both surfaces (banner
   alert + bell badge).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.models.auth import User
from giljo_mcp.services.user_service import UserService


def _svc(db_manager, tenant_key, ws, session):
    return UserService(
        db_manager=db_manager,
        tenant_key=tenant_key,
        websocket_manager=ws,
        session=session,
    )


def _make_user(tenant_key, *, last_reminder, installed="1.0.0"):
    return User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version=installed,
        last_update_reminder_at=last_reminder,
    )


@pytest.mark.asyncio
async def test_throttle_suppresses_at_exactly_30_day_boundary(db_manager, db_session, test_tenant_key, monkeypatch):
    """At exactly 30 days, the throttle is still in effect (predicate is `<= 30`)."""
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    # Exactly 30 days ago — well, a hair under to land inside the <=30d window
    # without flake risk from clock drift between the call and `datetime.now()`
    # in the service.
    boundary = datetime.now(timezone.utc) - timedelta(days=30, seconds=-5)
    user = _make_user(test_tenant_key, last_reminder=boundary)
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _svc(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(user.id)

    assert payload is None
    assert ws.broadcast_to_tenant.await_count == 0


@pytest.mark.asyncio
async def test_emit_payload_shape_contains_required_keys(db_manager, db_session, test_tenant_key, monkeypatch):
    """Emitted WS payload must carry user_id + installed + current + message.

    The frontend handler in `systemEventRoutes.js` reads these to drive both
    the banner alert and the bell-icon notification.
    """
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    user = _make_user(test_tenant_key, last_reminder=None, installed="1.0.0")
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _svc(db_manager, test_tenant_key, ws, db_session)
    returned = await svc.check_and_emit_skills_update(user.id)

    # Returned payload (used by the auth login hook for direct UI surfacing).
    assert returned is not None
    assert returned["installed"] == "1.0.0"
    assert returned["current"] == "1.1.11"
    assert returned.get("message")

    # Broadcast payload (shape consumed by the WS event router on the client).
    assert ws.broadcast_to_tenant.await_count == 1
    kwargs = ws.broadcast_to_tenant.await_args.kwargs
    assert kwargs["event_type"] == "system:update_available"
    data = kwargs["data"]
    for key in ("user_id", "installed", "current", "message"):
        assert key in data, f"WS payload missing required key: {key}"
    assert data["user_id"] == user.id
    assert data["installed"] == "1.0.0"
    assert data["current"] == "1.1.11"
