# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for UserService.check_and_emit_skills_update — 30-day cadence.

HO 1028: post-login skills-version drift reminder. The reminder fires if
the user's installed bundle is older than the server's SKILLS_VERSION and
either has never been reminded or was last reminded more than 30 days ago.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.models.auth import User
from giljo_mcp.services.user_service import UserService


def _make_user_service(db_manager, tenant_key, ws_mock, session):
    return UserService(
        db_manager=db_manager,
        tenant_key=tenant_key,
        websocket_manager=ws_mock,
        session=session,
    )


@pytest.mark.asyncio
async def test_emits_when_installed_is_null_and_never_reminded(db_manager, db_session, test_tenant_key, monkeypatch):
    monkeypatch.setattr("giljo_mcp.services.user_service.UserService", UserService, raising=False)
    # Patch SKILLS_VERSION at the import location used by the service.
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version=None,
        last_update_reminder_at=None,
    )
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(user.id)

    assert payload is not None
    assert payload["installed"] is None
    assert payload["current"] == "1.1.11"
    assert ws.broadcast_to_tenant.await_count == 1
    call_kwargs = ws.broadcast_to_tenant.await_args.kwargs
    assert call_kwargs["event_type"] == "system:update_available"


@pytest.mark.asyncio
async def test_no_emit_when_versions_match(db_manager, db_session, test_tenant_key, monkeypatch):
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version="1.1.11",
        last_update_reminder_at=None,
    )
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(user.id)

    assert payload is None
    assert ws.broadcast_to_tenant.await_count == 0


@pytest.mark.asyncio
async def test_throttle_suppresses_within_30_days(db_manager, db_session, test_tenant_key, monkeypatch):
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    recent = datetime.now(timezone.utc) - timedelta(days=10)
    user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version="1.0.0",
        last_update_reminder_at=recent,
    )
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(user.id)

    assert payload is None
    assert ws.broadcast_to_tenant.await_count == 0


@pytest.mark.asyncio
async def test_emits_after_30_day_window(db_manager, db_session, test_tenant_key, monkeypatch):
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    stale = datetime.now(timezone.utc) - timedelta(days=31)
    user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version="1.0.0",
        last_update_reminder_at=stale,
    )
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(user.id)

    assert payload is not None
    assert payload["installed"] == "1.0.0"
    assert payload["current"] == "1.1.11"
    assert ws.broadcast_to_tenant.await_count == 1


@pytest.mark.asyncio
async def test_updates_last_reminder_at_after_emit(db_manager, db_session, test_tenant_key, monkeypatch):
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=True,
        last_installed_skills_version="1.0.0",
        last_update_reminder_at=None,
    )
    db_session.add(user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    await svc.check_and_emit_skills_update(user.id)

    await db_session.refresh(user)
    assert user.last_update_reminder_at is not None


@pytest.mark.asyncio
async def test_tenant_isolation(db_manager, db_session, test_tenant_key, monkeypatch):
    """A user in another tenant must not be triggered by this service instance."""
    monkeypatch.setattr(
        "giljo_mcp.tools.slash_command_templates.SKILLS_VERSION",
        "1.1.11",
    )

    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"u_{uuid4().hex[:6]}",
        email=f"u_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=other_tenant,  # different tenant
        role="developer",
        is_active=True,
        last_installed_skills_version="1.0.0",
    )
    db_session.add(other_user)
    await db_session.commit()

    ws = MagicMock()
    ws.broadcast_to_tenant = AsyncMock()

    # Service instance is bound to test_tenant_key, NOT other_tenant.
    svc = _make_user_service(db_manager, test_tenant_key, ws, db_session)
    payload = await svc.check_and_emit_skills_update(other_user.id)

    assert payload is None
    assert ws.broadcast_to_tenant.await_count == 0
