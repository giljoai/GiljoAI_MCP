# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9006 — deactivating a user must bite live WebSocket sessions.

Edition Scope: Both (api/websocket.py + UserService are CE-shared; deactivation
behaves identically by GILJO_MODE).

is_active was only re-checked at the WS handshake, so a deactivated account kept
a live socket reading until it naturally reconnected. Deactivation now:

  1. bumps ``token_revocation_epoch`` + revokes the user's refresh tokens (the
     SEC-9047 eviction idiom) so outstanding tokens die AND — because the epoch
     persists — a later reactivation cannot resurrect the pre-deactivation
     session; and
  2. force-closes the account's live sockets immediately, fanned across workers
     over the existing giljo_ws_events broker (no new channel; ADR-009 tenant
     scoping — tenant_key is per-user today).

Tested at the two failing layers:

  * WS layer — ``WebSocketManager.disconnect_tenant`` closes only the target
    tenant's sockets, publishes a control message cross-worker, and a peer that
    receives that control closes its own sockets without re-publishing (no loop)
    and ignores its own echo.
  * Service layer — ``UserService.update_user(is_active=False)`` and
    ``delete_user`` bump the epoch, revoke refresh tokens, and invoke the live
    socket close; reactivation does NOT bump again (no resurrection); a
    non-is_active update evicts nothing.

Parallel-safe: manager driven with lightweight fakes (no DB); service tests use a
unique tenant/user each and monkeypatch-only module patching.
"""

from __future__ import annotations

import json
from uuid import uuid4

import bcrypt
import pytest

from api.broker.base import WebSocketBrokerMessage, WebSocketEventBroker
from api.websocket import WebSocketManager


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeWS:
    """Starlette-WebSocket stand-in recording close(code, reason)."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False
        self.close_code: int | None = None
        self.close_reason: str | None = None

    async def send_text(self, data: str) -> None:
        self.sent.append(data)

    async def send_json(self, data: dict) -> None:
        self.sent.append(json.dumps(data))

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason


class _FakeBroker(WebSocketEventBroker):
    """Records publishes and exposes the subscribed handler for peer simulation."""

    def __init__(self) -> None:
        self.published: list[WebSocketBrokerMessage] = []
        self.handler = None

    def subscribe(self, handler):
        self.handler = handler

        def _unsub() -> None:
            self.handler = None

        return _unsub

    async def publish(self, message: WebSocketBrokerMessage) -> None:
        self.published.append(message)


def _wire(mgr: WebSocketManager, client_id: str, ws: _FakeWS, tenant_key: str) -> None:
    mgr.active_connections[client_id] = ws
    mgr.auth_contexts[client_id] = {"tenant_key": tenant_key}
    mgr._index_tenant_connection(client_id, tenant_key)


def _force_multiworker(monkeypatch) -> None:
    """attach_broker caches _worker_count() > 1 as the publish gate."""
    import api.startup.database as db_startup

    monkeypatch.setattr(db_startup, "_worker_count", lambda: 2)


# ---------------------------------------------------------------------------
# WS layer — disconnect_tenant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_tenant_closes_only_target_tenant_and_deregisters():
    mgr = WebSocketManager()
    a1, a2, b1 = _FakeWS(), _FakeWS(), _FakeWS()
    _wire(mgr, "a1", a1, "tenant_A")
    _wire(mgr, "a2", a2, "tenant_A")
    _wire(mgr, "b1", b1, "tenant_B")

    closed = await mgr.disconnect_tenant("tenant_A", publish_to_broker=False)

    # Both of tenant A's sockets were closed with the policy-violation code.
    assert closed == 2
    assert a1.closed and a2.closed
    assert a1.close_code == 1008
    assert a1.close_reason == "account deactivated"
    # Deregistered from every index so they can no longer receive fan-out.
    assert "a1" not in mgr.active_connections
    assert "a2" not in mgr.active_connections
    assert "tenant_A" not in mgr.tenant_connections
    # Tenant B is untouched — deactivation is scoped to the account.
    assert not b1.closed
    assert "b1" in mgr.active_connections


@pytest.mark.asyncio
async def test_disconnect_tenant_no_sockets_is_noop():
    mgr = WebSocketManager()
    closed = await mgr.disconnect_tenant("tenant_empty", publish_to_broker=False)
    assert closed == 0


@pytest.mark.asyncio
async def test_disconnect_tenant_rejects_empty_tenant_key():
    mgr = WebSocketManager()
    with pytest.raises(ValueError):
        await mgr.disconnect_tenant("", publish_to_broker=False)


@pytest.mark.asyncio
async def test_disconnect_tenant_publishes_control_when_multiworker(monkeypatch):
    _force_multiworker(monkeypatch)
    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)

    a1 = _FakeWS()
    _wire(mgr, "a1", a1, "tenant_A")

    await mgr.disconnect_tenant("tenant_A")  # publish_to_broker defaults True

    assert a1.closed
    assert len(broker.published) == 1
    msg = broker.published[0]
    assert msg.control == "disconnect_tenant"
    assert msg.tenant_key == "tenant_A"
    assert msg.origin == mgr._broker_origin  # carries origin so the echo is suppressed


@pytest.mark.asyncio
async def test_disconnect_tenant_single_worker_does_not_publish(monkeypatch):
    import api.startup.database as db_startup

    monkeypatch.setattr(db_startup, "_worker_count", lambda: 1)
    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)
    _wire(mgr, "a1", _FakeWS(), "tenant_A")

    await mgr.disconnect_tenant("tenant_A")

    # Sole worker already closed locally — no cross-worker publish overhead.
    assert broker.published == []


@pytest.mark.asyncio
async def test_peer_control_message_closes_local_sockets_without_republishing(monkeypatch):
    _force_multiworker(monkeypatch)
    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)
    a1 = _FakeWS()
    _wire(mgr, "a1", a1, "tenant_A")

    # A control message from a DIFFERENT worker arrives on this worker's broker.
    peer_msg = WebSocketBrokerMessage(
        tenant_key="tenant_A",
        event={},
        origin="some-other-worker-origin",
        control="disconnect_tenant",
    )
    await broker.handler(peer_msg)

    assert a1.closed
    assert "a1" not in mgr.active_connections
    # The peer close must NOT re-publish — that would loop between workers.
    assert broker.published == []


@pytest.mark.asyncio
async def test_own_echo_control_message_is_ignored(monkeypatch):
    _force_multiworker(monkeypatch)
    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)
    a1 = _FakeWS()
    _wire(mgr, "a1", a1, "tenant_A")

    # The LISTEN connection echoes this worker's own publish back to it.
    own_msg = WebSocketBrokerMessage(
        tenant_key="tenant_A",
        event={},
        origin=mgr._broker_origin,
        control="disconnect_tenant",
    )
    await broker.handler(own_msg)

    # Already closed locally at publish time — the echo must be a no-op.
    assert not a1.closed
    assert "a1" in mgr.active_connections


def test_broker_message_control_survives_serialization_roundtrip():
    """The pg_notify (de)serializer carries the control discriminator."""
    from api.broker.postgres_notify import PostgresNotifyWebSocketEventBroker as B

    msg = WebSocketBrokerMessage(tenant_key="tenant_A", event={}, origin="orig", control="disconnect_tenant")
    restored = B._deserialize(B._serialize(msg))
    assert restored.control == "disconnect_tenant"
    assert restored.tenant_key == "tenant_A"
    assert restored.origin == "orig"


# ---------------------------------------------------------------------------
# Service layer — deactivation triggers eviction + live socket close
# ---------------------------------------------------------------------------


class _RecordingWsManager:
    """Captures disconnect_tenant calls made by the service."""

    def __init__(self) -> None:
        self.disconnects: list[str] = []

    async def disconnect_tenant(self, tenant_key: str, *, reason: str = "", **_) -> int:
        self.disconnects.append(tenant_key)
        return 0


async def _seed_user(db_manager) -> tuple[str, str]:
    """Create org+user (active, epoch 0); return (user_id, tenant_key)."""
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    user_id = str(uuid4())

    async with db_manager.get_session_async(tenant_key=tk) as session:
        org = Organization(
            name=f"TSK9006 Org {unique}",
            slug=f"tsk9006-org-{unique}",
            tenant_key=tk,
            is_active=True,
        )
        session.add(org)
        await session.flush()
        session.add(
            User(
                id=user_id,
                username=f"tsk9006_user_{unique}",
                email=f"tsk9006_{unique}@example.com",
                password_hash=bcrypt.hashpw(b"Password1!", bcrypt.gensalt()).decode("utf-8"),
                tenant_key=tk,
                role="developer",
                org_id=org.id,
                is_active=True,
                token_revocation_epoch=0,
            )
        )
        await session.commit()

    return user_id, tk


async def _read_user(db_manager, *, tenant_key: str, user_id: str):
    from giljo_mcp.models.auth import User

    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        user = await session.get(User, user_id)
        return int(user.token_revocation_epoch or 0), bool(user.is_active)


@pytest.fixture
def spy_ws_manager(monkeypatch):
    """Swap a recording ws manager onto api.app_state.state (the service's source)."""
    from api import app_state

    spy = _RecordingWsManager()
    monkeypatch.setattr(app_state.state, "websocket_manager", spy, raising=False)
    return spy


def _service(db_manager, tenant_key: str):
    from giljo_mcp.services.user_service import UserService

    return UserService(db_manager=db_manager, tenant_key=tenant_key)


@pytest.mark.asyncio
async def test_update_deactivate_bumps_epoch_and_closes_sockets(db_manager, spy_ws_manager):
    user_id, tk = await _seed_user(db_manager)

    await _service(db_manager, tk).update_user(user_id, is_active=False)

    epoch, is_active = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert epoch == 1  # eviction epoch bumped exactly once
    assert is_active is False
    assert spy_ws_manager.disconnects == [tk]  # live sockets closed for the tenant


@pytest.mark.asyncio
async def test_reactivation_does_not_resurrect_or_close(db_manager, spy_ws_manager):
    user_id, tk = await _seed_user(db_manager)
    svc = _service(db_manager, tk)

    await svc.update_user(user_id, is_active=False)
    assert spy_ws_manager.disconnects == [tk]

    # Reactivate: must NOT bump the epoch again (old tokens stay dead — no
    # resurrection) and must NOT close any sockets.
    await svc.update_user(user_id, is_active=True)

    epoch, is_active = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert epoch == 1  # unchanged by reactivation
    assert is_active is True
    assert spy_ws_manager.disconnects == [tk]  # no second disconnect


@pytest.mark.asyncio
async def test_non_active_update_evicts_nothing(db_manager, spy_ws_manager):
    user_id, tk = await _seed_user(db_manager)

    await _service(db_manager, tk).update_user(user_id, first_name="Renamed")

    epoch, _ = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert epoch == 0  # a non-credential, non-deactivation update never evicts
    assert spy_ws_manager.disconnects == []


@pytest.mark.asyncio
async def test_delete_user_soft_delete_evicts_and_closes_sockets(db_manager, spy_ws_manager):
    user_id, tk = await _seed_user(db_manager)

    await _service(db_manager, tk).delete_user(user_id)

    epoch, is_active = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert epoch == 1
    assert is_active is False
    assert spy_ws_manager.disconnects == [tk]
