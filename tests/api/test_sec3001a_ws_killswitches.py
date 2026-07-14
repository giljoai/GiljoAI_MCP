# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-3001a items 4 + 5 — WebSocket auth kill-switches.

Failing layer = the WS auth functions in ``api/auth_utils.py`` (the exact code
the ``/ws/{client_id}`` handshake runs):

  - item 4: ``validate_api_key`` excluded ``expires_at`` from its key lookup, so
    an expired-but-still-active API key authenticated a WS connection. The fix
    mirrors the REST/MCP predicate (``expires_at > now OR expires_at IS NULL``).
  - item 5: ``get_setup_state`` returned ``database_initialized=False`` on a DB
    error, routing ``authenticate_websocket`` into the unauthenticated setup
    branch — a transient DB fault on a live install granted an unauth WS. The fix
    fails CLOSED (treat as initialized -> require credentials) while leaving the
    genuine-setup ``db is None`` branch untouched.

Both items are two-sided. xdist-safe: unique tenant_key per test, no
module-level mutable state, ``db_session`` is transaction-rolled-back.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import pytest
from fastapi import WebSocketException
from sqlalchemy.exc import SQLAlchemyError

from api.auth_utils import authenticate_websocket, get_setup_state, validate_api_key
from giljo_mcp.api_key_utils import get_key_prefix, hash_api_key
from giljo_mcp.models.auth import APIKey, User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.tenant import TenantManager


async def _seed_api_key(db_session, *, expires_at: datetime | None) -> str:
    """Seed org+user+api_key with the given ``expires_at`` (flushed, not committed).

    Returns the raw key string. The key_prefix is computed with the SAME
    ``get_key_prefix`` ``validate_api_key`` uses, so the prefix-narrowed lookup
    resolves exactly this row.
    """
    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    raw_key = f"gk_{uuid4().hex}{uuid4().hex}"

    org = Organization(
        name=f"SEC3001a WS Org {unique}",
        slug=f"sec3001a-ws-org-{unique}",
        tenant_key=tk,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"sec3001a_ws_user_{unique}",
        email=f"sec3001a_ws_{unique}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=tk,
        role="developer",
        org_id=org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    api_key = APIKey(
        id=str(uuid4()),
        tenant_key=tk,
        user_id=user.id,
        name=f"SEC3001a WS Key {unique}",
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    db_session.add(api_key)
    await db_session.flush()

    return raw_key


class _NoCredWebSocket:
    """Minimal WebSocket stand-in with no auth credentials (query/cookie/header)."""

    def __init__(self) -> None:
        self.query_params: dict[str, str] = {}
        self.headers: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Item 4 — API-key WS expiry
# ---------------------------------------------------------------------------


class TestApiKeyWebSocketExpiry:
    """An expired API key must NOT authenticate a WS connection; valid keys still do."""

    @pytest.mark.asyncio
    async def test_expired_key_rejected(self, db_session):
        raw_key = await _seed_api_key(db_session, expires_at=datetime.now(UTC) - timedelta(hours=1))
        result = await validate_api_key(raw_key, db_session)
        assert result is None, "an expired (past expires_at) API key must NOT authenticate a WS connection"

    @pytest.mark.asyncio
    async def test_unexpired_key_accepted(self, db_session):
        raw_key = await _seed_api_key(db_session, expires_at=datetime.now(UTC) + timedelta(hours=1))
        result = await validate_api_key(raw_key, db_session)
        assert result is not None, "a non-expired API key must still authenticate (happy path)"
        assert result.get("tenant_key"), result

    @pytest.mark.asyncio
    async def test_null_expiry_key_accepted(self, db_session):
        # A NULL expires_at means "never expires" — must keep connecting.
        raw_key = await _seed_api_key(db_session, expires_at=None)
        result = await validate_api_key(raw_key, db_session)
        assert result is not None, "a NULL-expiry API key never expires and must still authenticate"


# ---------------------------------------------------------------------------
# Item 5 — WS setup-context fail-closed on DB error
# ---------------------------------------------------------------------------


class TestWebSocketSetupFailClosed:
    """A DB error on the WS setup probe must fail CLOSED (require auth), not open."""

    @pytest.mark.asyncio
    async def test_get_setup_state_fails_closed_on_db_error(self, db_session, monkeypatch):
        async def _boom(*_a, **_k):
            raise SQLAlchemyError("simulated transient DB fault")

        monkeypatch.setattr(db_session, "execute", _boom)

        state = await get_setup_state(db_session)
        assert state["database_initialized"] is True, (
            "a DB error must be treated as initialized (fail CLOSED -> credentials required); "
            "returning False here would route authenticate_websocket into the unauth setup branch"
        )

    @pytest.mark.asyncio
    async def test_authenticate_websocket_rejects_on_db_error_without_creds(self, db_session, monkeypatch):
        async def _boom(*_a, **_k):
            raise SQLAlchemyError("simulated transient DB fault")

        monkeypatch.setattr(db_session, "execute", _boom)

        with pytest.raises(WebSocketException):
            await authenticate_websocket(_NoCredWebSocket(), db=db_session)

    @pytest.mark.asyncio
    async def test_genuine_setup_still_allowed_without_db(self):
        # Allow-good side: a genuinely-uninitialized install (db is None, the
        # db_manager-absent setup window) must STILL grant the unauth setup
        # connection — the fix only touches the DB-error path, not this branch.
        state = await get_setup_state(None)
        assert state["database_initialized"] is False

        result = await authenticate_websocket(_NoCredWebSocket(), db=None)
        assert result == {"authenticated": True, "context": "setup"}
