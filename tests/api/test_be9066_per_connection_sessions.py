# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9066 — per-connection MCP session minting (one ``mcp_sessions`` row per initialize).

The bug: ``get_or_create_session`` keyed ONE row per (api_key, tenant), deleted
"duplicate" sibling rows on EVERY request, and each ``initialize`` merged its
clientInfo onto that shared row — so with N clients on one login the last
initializer's harness poisoned every other client's render (proven live:
a claude-code CLI was served the generic spawn protocol because a hosted
``openai-mcp`` client initialized more recently).

The fix (C1): mint a fresh row per ``initialize``; non-initialize requests are
authenticate-only and validate the echoed ``Mcp-Session-Id`` with principal
binding (a row minted for another key/user/tenant behaves exactly like an
unknown id); an unknown-but-well-formed id from an authenticated caller is
soft-resurrected credential-bound instead of 404'd (never-terminate posture).

Failing-layer discipline (per CLAUDE.md): every case drives real JSON-RPC
payloads through ``MCPAuthMiddleware`` — the MCP transport boundary where the
bug lived. Reuses the seed + drivers from ``tests/api/test_mcp_session.py`` and
the state-capturing inner app from ``test_be9035d_harness_capture_and_stamp``.

Harness names: ``claude-code``, ``codex-mcp-client`` and ``opencode`` are the
clientInfo names the resolver seeds concretely today (BE-9070 added codex), so
``claude-code``/``opencode`` prove the two-distinct-harnesses side; ``openai-mcp``
(a hosted surface that cannot open terminals — kept generic by design) is the
unseeded example that mirrors the exact incident shape. Edition Scope: Both.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from giljo_mcp.database import tenant_session_context
from tests.api.test_be9035d_harness_capture_and_stamp import (  # noqa: E402
    _initialize_body,
    _StateCapturingApp,
)
from tests.api.test_mcp_session import (  # noqa: E402
    _drive_middleware_with_body,
    _jsonrpc_body,
    _seed_api_key,
)


pytestmark = pytest.mark.asyncio


@pytest.fixture
def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    return "test_secret_key"


async def _initialize(raw_key: str, client_name: str) -> str:
    """Drive an initialize through the middleware; return the minted session id."""
    from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

    status, headers, _body = await _drive_middleware_with_body(
        MCPAuthMiddleware(app=_StateCapturingApp()),
        headers=[(b"x-api-key", raw_key.encode()), (b"content-type", b"application/json")],
        body=_initialize_body(client_name),
    )
    assert status == 200, f"initialize returned {status}"
    session_id = headers.get("mcp-session-id")
    assert session_id, "initialize must issue an Mcp-Session-Id"
    return session_id


async def _tools_call(raw_key: str, session_id: str) -> tuple[int, _StateCapturingApp]:
    """Drive a non-initialize request echoing ``session_id``; return (status, inner app)."""
    from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

    inner = _StateCapturingApp()
    status, _headers, _body = await _drive_middleware_with_body(
        MCPAuthMiddleware(app=inner),
        headers=[
            (b"x-api-key", raw_key.encode()),
            (b"mcp-protocol-version", b"2025-06-18"),
            (b"mcp-session-id", session_id.encode("ascii")),
            (b"content-type", b"application/json"),
        ],
        body=_jsonrpc_body("tools/list"),
    )
    return status, inner


async def _load_row(db_manager, tenant_key: str, session_id: str):
    """Read one session row (detached snapshot) in its tenant's context, or None."""
    from giljo_mcp.models import MCPSession

    async with db_manager.get_session_async() as db:
        with tenant_session_context(db, tenant_key):
            row = (await db.execute(select(MCPSession).where(MCPSession.session_id == session_id))).scalar_one_or_none()
            if row is not None:
                db.expunge(row)
            return row


async def _seed_second_key_same_user(db_manager, tenant_key: str) -> str:
    """Mint a SECOND API key for the tenant's existing user. Returns the raw key."""
    from giljo_mcp.api_key_utils import hash_api_key
    from giljo_mcp.models.auth import APIKey, User

    raw_key = f"gk_sessionTest_{uuid4().hex}"
    async with db_manager.get_session_async() as db:
        with tenant_session_context(db, tenant_key):
            user = (await db.execute(select(User).where(User.tenant_key == tenant_key))).scalars().first()
            db.add(
                APIKey(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    user_id=user.id,
                    name=f"Second Key {uuid4().hex[:8]}",
                    key_hash=hash_api_key(raw_key),
                    key_prefix=f"{raw_key[:12]}...",
                    permissions=["*"],
                    is_active=True,
                    created_at=datetime.now(UTC),
                )
            )
            await db.commit()
    return raw_key


# ---------------------------------------------------------------------------
# Per-connection minting: N clients on one login, N rows, zero contamination
# ---------------------------------------------------------------------------


async def test_two_clients_same_key_get_distinct_sessions(db_manager, jwt_env):
    """Client A (claude-code) and client B (opencode) on the SAME api key each get
    their own session row carrying their own harness — the pre-fix code returned
    one shared id for both and let B overwrite A's resolved_harness."""
    from api.app_state import state

    raw_key, tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(raw_key, "claude-code")
        sid_b = await _initialize(raw_key, "opencode")
        assert sid_a != sid_b, "each initialize must mint its OWN session (per-connection, BE-9066)"

        row_a = await _load_row(db_manager, tenant_key, sid_a)
        row_b = await _load_row(db_manager, tenant_key, sid_b)
        assert row_a is not None and row_b is not None
        assert row_a.session_data.get("resolved_harness") == "claude-code"
        assert row_b.session_data.get("resolved_harness") == "opencode"
        assert row_a.session_data.get("client_info", {}).get("name") == "claude-code", (
            "B's initialize must not overwrite A's clientInfo (last-writer-wins is the bug)"
        )
    finally:
        state.db_manager = prior_db


async def test_interleaved_tools_calls_each_render_own_harness(db_manager, jwt_env):
    """Two-sided proof: interleaved tools/calls on both ids each stamp THEIR OWN
    harness onto scope state — A never sees B's, and both keep working."""
    from api.app_state import state

    raw_key, _tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(raw_key, "claude-code")
        sid_b = await _initialize(raw_key, "opencode")

        status_a, inner_a = await _tools_call(raw_key, sid_a)
        status_b, inner_b = await _tools_call(raw_key, sid_b)
        status_a2, inner_a2 = await _tools_call(raw_key, sid_a)

        assert (status_a, status_b, status_a2) == (200, 200, 200)
        assert inner_a.resolved_harness_seen == "claude-code"
        assert inner_b.resolved_harness_seen == "opencode"
        assert inner_a2.resolved_harness_seen == "claude-code", (
            "A's render must survive B's activity (the proven live contamination)"
        )
    finally:
        state.db_manager = prior_db


async def test_incident_shape_second_client_does_not_contaminate_first(db_manager, jwt_env):
    """The exact incident: claude-code connected, then a client with an unseeded
    clientInfo name initialized on the same login. Pre-fix, claude-code's next
    call rendered generic. Now B rides its own generic row and A is untouched."""
    from api.app_state import state

    raw_key, _tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(raw_key, "claude-code")
        sid_b = await _initialize(raw_key, "openai-mcp")  # unseeded (hosted, no terminals) -> generic

        status_b, inner_b = await _tools_call(raw_key, sid_b)
        status_a, inner_a = await _tools_call(raw_key, sid_a)

        assert (status_b, status_a) == (200, 200)
        assert inner_b.resolved_harness_seen == "SENTINEL_UNSET", "generic is never stamped"
        assert inner_a.resolved_harness_seen == "claude-code", (
            "the second client's initialize must not degrade claude-code to generic"
        )
    finally:
        state.db_manager = prior_db


async def test_second_initialize_no_longer_deletes_first_row(db_manager, jwt_env):
    """Anti-dedup: pre-fix, B's next request DELETED A's row as a 'duplicate' and
    A's calls 404'd. Now A's row survives B's initialize + tools/call."""
    from api.app_state import state

    raw_key, tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(raw_key, "claude-code")
        sid_b = await _initialize(raw_key, "opencode")
        status_b, _ = await _tools_call(raw_key, sid_b)
        assert status_b == 200

        row_a = await _load_row(db_manager, tenant_key, sid_a)
        assert row_a is not None, "B's activity must not delete A's session row (old dedup behavior)"

        status_a, inner_a = await _tools_call(raw_key, sid_a)
        assert status_a == 200, "A's session must still be served after B's activity"
        assert inner_a.resolved_harness_seen == "claude-code"
    finally:
        state.db_manager = prior_db


# ---------------------------------------------------------------------------
# Principal binding: a caller never reaches another principal's session row
# ---------------------------------------------------------------------------


async def test_cross_key_session_id_behaves_like_unknown(db_manager, jwt_env):
    """STRICTEST binding claim: a DIFFERENT api key of the SAME user echoing A's
    session id gets 404 (keys are independently revocable credentials), and A's
    row is neither served nor hijacked by the resurrection path."""
    from api.app_state import state

    raw_key_a, tenant_key = await _seed_api_key(db_manager)
    raw_key_b = await _seed_second_key_same_user(db_manager, tenant_key)

    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(raw_key_a, "claude-code")

        status, inner = await _tools_call(raw_key_b, sid_a)
        assert status == 404, f"cross-principal session id must behave like unknown, got {status}"
        assert inner.called is False, "inner app must not run for a cross-principal session id"

        row = await _load_row(db_manager, tenant_key, sid_a)
        assert row is not None and row.session_data.get("resolved_harness") == "claude-code", (
            "the foreign echo must not mutate or replace A's row"
        )

        status_a, inner_a = await _tools_call(raw_key_a, sid_a)
        assert status_a == 200 and inner_a.resolved_harness_seen == "claude-code", (
            "the rightful owner must still be served after the foreign echo"
        )
    finally:
        state.db_manager = prior_db


async def test_cross_tenant_session_id_still_404_and_never_hijacked(db_manager, jwt_env):
    """Tenant B echoing tenant A's live id stays 404 — and the soft-resurrection
    INSERT must NOT mint a tenant-B row carrying A's session id (the unique
    constraint on session_id forces the rollback → unknown path)."""
    from api.app_state import state

    key_a, tenant_a = await _seed_api_key(db_manager)
    key_b, tenant_b = await _seed_api_key(db_manager)
    assert tenant_a != tenant_b

    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid_a = await _initialize(key_a, "claude-code")

        status, inner = await _tools_call(key_b, sid_a)
        assert status == 404, f"cross-tenant session id must 404, got {status} — tenant isolation breached"
        assert inner.called is False

        row_a = await _load_row(db_manager, tenant_a, sid_a)
        assert row_a is not None and row_a.tenant_key == tenant_a
        assert await _load_row(db_manager, tenant_b, sid_a) is None, (
            "resurrection must never mint a foreign-tenant twin of an existing session id"
        )
    finally:
        state.db_manager = prior_db


async def test_jwt_row_not_reachable_by_api_key_principal(db_manager, jwt_env):
    """Manager-level binding matrix: a JWT-minted row (api_key_id IS NULL) is owned
    by its user only — an API-key principal, or another user, reads it as unknown."""
    from api.endpoints.mcp_session import MCPSessionManager
    from giljo_mcp.models.auth import User

    _raw_key, tenant_key = await _seed_api_key(db_manager)
    async with db_manager.get_session_async() as db:
        with tenant_session_context(db, tenant_key):
            user_id = (await db.execute(select(User).where(User.tenant_key == tenant_key))).scalars().first().id

    async with db_manager.get_session_async() as db:
        mgr = MCPSessionManager(db)
        row = await mgr.create_session(tenant_key=tenant_key, user_id=user_id, auth_method="oauth_jwt")
        sid = row.session_id

        owner = await mgr.get_session(sid, tenant_key=tenant_key, caller_user_id=user_id)
        assert owner is not None, "the minting user must reach its own row"

        as_api_key = await mgr.get_session(sid, tenant_key=tenant_key, caller_api_key_id=str(uuid4()))
        assert as_api_key is None, "an API-key principal must not reach a JWT row"

        as_other_user = await mgr.get_session(sid, tenant_key=tenant_key, caller_user_id=str(uuid4()))
        assert as_other_user is None, "another user must not reach the row"


# ---------------------------------------------------------------------------
# Soft-resurrection (never-terminate posture)
# ---------------------------------------------------------------------------


async def test_unknown_wellformed_id_soft_resurrects_credential_bound(db_manager, jwt_env):
    """An authenticated caller echoing a never-minted canonical UUID is served
    (not 404'd) via a fresh generic-harness row bound to ITS principal."""
    from api.app_state import state
    from giljo_mcp.models.auth import APIKey

    raw_key, tenant_key = await _seed_api_key(db_manager)
    ghost_id = str(uuid4())

    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        status, inner = await _tools_call(raw_key, ghost_id)
        assert status == 200, f"soft-resurrection must serve the caller, got {status}"
        assert inner.called is True
        assert inner.resolved_harness_seen == "SENTINEL_UNSET", "a resurrected row is generic (never stamped)"

        row = await _load_row(db_manager, tenant_key, ghost_id)
        assert row is not None, "resurrection must persist a row carrying the echoed id"
        assert row.session_data.get("resolved_harness") == "generic"
        async with db_manager.get_session_async() as db:
            with tenant_session_context(db, tenant_key):
                key_row = (await db.execute(select(APIKey).where(APIKey.tenant_key == tenant_key))).scalars().first()
        assert row.api_key_id == key_row.id, "the resurrected row must be bound to the calling credential"
    finally:
        state.db_manager = prior_db


async def test_expired_unreaped_row_is_revived_in_place_with_harness(db_manager, jwt_env):
    """The 24-48h idle window: the row expired but the reaper hasn't swept it.
    Its owner's next call revives it IN PLACE — 200 and the harness identity
    survives (a plain mint-a-new-generic-row would lose it)."""
    from api.app_state import state
    from giljo_mcp.models import MCPSession

    raw_key, tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        sid = await _initialize(raw_key, "claude-code")

        async with db_manager.get_session_async() as db:
            with tenant_session_context(db, tenant_key):
                row = (await db.execute(select(MCPSession).where(MCPSession.session_id == sid))).scalar_one()
                row.expires_at = datetime.now(UTC) - timedelta(hours=1)
                await db.commit()

        status, inner = await _tools_call(raw_key, sid)
        assert status == 200, "the rightful owner of an expired-but-unreaped id must be revived, not 404'd"
        assert inner.resolved_harness_seen == "claude-code", "revive-in-place must keep the harness identity"

        row = await _load_row(db_manager, tenant_key, sid)
        assert row.expires_at > datetime.now(UTC), "the revived row must carry a fresh expiration"
    finally:
        state.db_manager = prior_db


async def test_malformed_session_id_still_404(db_manager, jwt_env):
    """Only this server's own minted shape (canonical lowercase UUID) resurrects.
    A non-minted shape — including an oversize value that would blow the
    String(36) column — 404s exactly as before."""
    from api.app_state import state

    raw_key, _tenant_key = await _seed_api_key(db_manager)
    prior_db = state.db_manager
    state.db_manager = db_manager
    try:
        for bad_id in (uuid4().hex, "deadbeef" * 8, "not-a-session-id"):
            status, inner = await _tools_call(raw_key, bad_id)
            assert status == 404, f"malformed id {bad_id!r} must 404, got {status}"
            assert inner.called is False
    finally:
        state.db_manager = prior_db
