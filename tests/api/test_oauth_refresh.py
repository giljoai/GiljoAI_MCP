# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""API endpoint tests for OAuth 2.1 refresh-token grant (API-0021e Phase 2).

Failing-layer tests run through the FastAPI route — same boundary the
claude.ai connector exercises against demo. CLAUDE.md mandates a test at
the layer the bug occurred (BE-5042 lesson).

Coverage:
  - Rotation: refresh_token swap on every call; old token rejected on reuse.
  - Reuse detection: presenting a revoked token revokes the entire family;
    subsequent calls with sibling-family tokens are rejected.
  - Tenant isolation: a refresh token issued under tenant A cannot be
    redeemed against a confidential client registered under tenant B.
  - Client authentication: wrong client_secret -> 401 invalid_client.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.services.oauth_service import BUILTIN_CLIENT_ID


def _generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _err_text(body: dict) -> str:
    """Flatten an OAuth error body to one searchable string.

    BE-6040: /token and /refresh now emit the RFC 6749 §5.2 envelope
    (``{"error": ..., "error_description": ...}``); older code used
    ``{"error_code"/"message"/"detail"}``. Concatenating every known field
    keeps these substring assertions shape-agnostic.
    """
    return " ".join(str(body.get(k, "")) for k in ("error", "error_description", "detail", "message"))


async def _seed_user_and_code(
    db_manager,
    *,
    challenge: str,
    code_value: str,
    client_id: str,
    redirect_uri: str = "http://localhost:3000/callback",
    resource: str | None = None,
) -> str:
    """Seed Org + User + AuthCode for a confidential DCR client.

    Returns the tenant_key. The OAuthClient row itself is NOT persisted
    (CE test DB has no oauth_clients table — that's a SaaS-only migration);
    tests inject a stub resolver via :func:`_install_confidential_resolver`.
    """
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.oauth import OAuthAuthorizationCode
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"Refresh Test Org {uuid4().hex[:6]}",
            slug=f"refresh-org-{uuid4().hex[:8]}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            id=str(uuid4()),
            username=f"refresh_user_{uuid4().hex[:8]}",
            email=f"refresh_{uuid4().hex[:8]}@example.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,
        )
        session.add(user)
        await session.flush()

        auth_code = OAuthAuthorizationCode(
            code=code_value,
            client_id=client_id,
            user_id=user.id,
            tenant_key=tenant_key,
            redirect_uri=redirect_uri,
            code_challenge=challenge,
            code_challenge_method="S256",
            scope="mcp:read mcp:write",
            resource=resource,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            used=False,
        )
        session.add(auth_code)
        await session.commit()

    return tenant_key


def _install_confidential_resolver(
    *clients: tuple[str, str, list[str]],
):
    """Install a resolver that recognizes the given confidential clients.

    Each tuple is ``(client_id, secret_hash, redirect_uris)``. Returns a
    ``restore`` callable to revert. Mirrors the pattern in
    ``test_oauth_endpoints.py``.
    """
    from giljo_mcp.services import oauth_service as svc

    prior = svc.get_client_resolver()
    table = {cid: (h, uris) for (cid, h, uris) in clients}

    def _resolver(cid: str, tenant_key: str):
        assert tenant_key
        if cid not in table:
            return None
        secret_hash, uris = table[cid]
        return svc.ResolvedClient(
            client_id=cid,
            client_name="DCR Confidential Test Client",
            redirect_uris=uris,
            client_secret_hash=secret_hash,
        )

    svc.set_client_resolver(_resolver)

    def _restore() -> None:
        svc.set_client_resolver(prior)

    return _restore


async def _exchange_code_for_token_pair(
    api_client,
    *,
    code_value: str,
    client_id: str,
    client_secret: str,
    code_verifier: str,
    redirect_uri: str = "http://localhost:3000/callback",
    resource: str | None = None,
) -> dict:
    """Drive /token end-to-end and return the response body.

    Phase 2 issues a refresh_token alongside the access_token for
    confidential clients on the initial authorization_code grant.
    """
    payload = {
        "grant_type": "authorization_code",
        "code": code_value,
        "client_id": client_id,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "client_secret": client_secret,
    }
    if resource is not None:
        payload["resource"] = resource
    response = await api_client.post("/api/oauth/token", data=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body, "Phase 2 confidential clients receive refresh_token"
    return body


def _bcrypt_hash(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


class TestRefreshTokenGrant:
    """API-0021e Phase 2: /refresh rotation + family reuse detection."""

    @pytest.mark.asyncio
    async def test_refresh_rotates_token(self, api_client, db_manager, monkeypatch):
        """Valid refresh -> new access + new refresh; old refresh rejected on second use.

        API-0021l introduced a 5s in-window idempotency hatch for /refresh.
        This test asserts the OUTSIDE-window contract still holds:
        replaying a rotated refresh_token after the window closes is the
        reuse-detection path, not the idempotency path. The idempotency
        contract itself is covered in test_oauth_endpoints.TestTokenIdempotency.
        """
        from giljo_mcp.services import oauth_refresh_service as _refresh_svc

        monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )

            r1 = initial["refresh_token"]

            response = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            r2 = body["refresh_token"]

            assert r2 != r1, "refresh_token must rotate"
            # Rotation MUST issue a new access_token in the response (not a 204
            # No Content). At second-level timestamp resolution two JWTs minted
            # with the same payload may hash-equal — we don't assert
            # !=, only that the response carried a fresh JWT shape.
            assert body["access_token"].count(".") == 2
            assert body["token_type"] == "bearer"

            # Reusing the OLD token must fail invalid_grant.
            replay = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert replay.status_code == 401, replay.text
            replay_body = replay.json()
            replay_detail = _err_text(replay_body)
            assert "invalid_grant" in replay_detail.lower(), replay_body
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_revokes_family(self, api_client, db_manager, monkeypatch):
        """Replaying a rotated refresh -> entire family revoked; r2 also rejected.

        API-0021l: collapse the idempotency window to 0 so this test
        exercises the reuse-detection path rather than the in-window
        idempotency hatch. Inside the window the replay would be
        idempotent (covered separately in TestTokenIdempotency).
        """
        from giljo_mcp.services import oauth_refresh_service as _refresh_svc

        monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            # Rotate r1 -> r2 (success).
            rotation = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert rotation.status_code == 200, rotation.text
            r2 = rotation.json()["refresh_token"]

            # Replay r1 -> 401 + family revocation.
            replay = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert replay.status_code == 401, replay.text

            # r2 must now also be rejected — family is revoked.
            sibling = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r2,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert sibling.status_code == 401, sibling.text
            sibling_body = sibling.json()
            sibling_detail = _err_text(sibling_body)
            assert "invalid_grant" in sibling_detail.lower(), sibling_body
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_refresh_cross_tenant_blocked(self, api_client, db_manager):
        """Refresh issued under tenant A cannot be redeemed against a client_id from tenant B."""
        from sqlalchemy import select as _select

        from giljo_mcp.database import tenant_isolation_bypass
        from giljo_mcp.models.oauth import OAuthRefreshToken

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id_a = str(uuid4())
        client_id_b = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        tenant_a = await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id_a,
        )

        # Resolver knows BOTH clients; resolver-level tenant scoping is what
        # enforces isolation server-side. Both share the same plaintext secret
        # so the cross-tenant rejection is provably about tenant_key, not
        # secret mismatch.
        restore = _install_confidential_resolver(
            (client_id_a, secret_hash, [redirect_uri]),
            (client_id_b, secret_hash, [redirect_uri]),
        )
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id_a,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            # Present r1 with the OTHER tenant's client_id.
            response = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id_b,
                    "client_secret": plaintext_secret,
                },
            )
            assert response.status_code == 401, response.text
            body = response.json()
            detail = _err_text(body)
            assert "invalid_grant" in detail.lower(), body

            # Direct DB inspection: this test's token row stayed bound to
            # tenant_a — no crossover row was minted under client_id_b's
            # tenant by the rejected /refresh call. Filter by the rotated
            # row's family/client to scope around test-suite leftover rows
            # (the test DB is shared across test functions).
            # Test-only cross-tenant inspection on a bare session (intentionally
            # queries across tenants to prove isolation); use the audited bypass.
            async with db_manager.get_session_async() as session:
                with tenant_isolation_bypass(
                    session,
                    reason="test: cross-tenant refresh-row inspection to prove isolation",
                    models=(OAuthRefreshToken,),
                ):
                    rows = (
                        (
                            await session.execute(
                                _select(OAuthRefreshToken).where(OAuthRefreshToken.client_id == client_id_a)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    # Ensure no row was issued under client_id_b at all.
                    b_rows = (
                        (
                            await session.execute(
                                _select(OAuthRefreshToken).where(OAuthRefreshToken.client_id == client_id_b)
                            )
                        )
                        .scalars()
                        .all()
                    )
                assert rows, "tenant A's refresh row must still exist"
                assert all(row.tenant_key == tenant_a for row in rows), [r.tenant_key for r in rows]
                assert not b_rows, "no refresh row should be issued for client_id_b"
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_refresh_with_wrong_secret(self, api_client, db_manager):
        """Wrong client_secret on /refresh -> 401 invalid_client."""
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            response = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": "totally-wrong-secret",
                },
            )
            assert response.status_code == 401, response.text
            body = response.json()
            detail = _err_text(body)
            assert "invalid_client" in detail.lower(), body
        finally:
            restore()


class TestRefreshBlocksDeactivatedUser:
    """SEC-3001a item 1 (deactivation propagation): an offboarded user must NOT
    rotate a still-live refresh token into fresh access+refresh pairs.

    Failing layer = the OAuth 2.1 refresh-token grant
    (``oauth_refresh_service._refresh_grant_after_lookup``), exercised through
    the real ``/api/oauth/refresh`` route — the same boundary the claude.ai
    connector hits (BE-5042: test at the failing transport layer). Two-sided in
    ONE test: the active user rotates successfully (happy path), then the SAME
    token/client/secret is rejected the instant the user is deactivated — so the
    only variable that flipped the verdict is ``is_active``.
    """

    @pytest.mark.asyncio
    async def test_refresh_blocks_deactivated_user(self, api_client, db_manager, monkeypatch):
        from sqlalchemy import update as _update

        from giljo_mcp.models.auth import User
        from giljo_mcp.services import oauth_refresh_service as _refresh_svc

        # Collapse the idempotency window so the second /refresh is a true new
        # grant evaluation, not an in-window replay of a cached response.
        monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        tenant_key = await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            # Happy path (active user): r1 rotates to r2.
            ok = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert ok.status_code == 200, ok.text
            r2 = ok.json()["refresh_token"]
            assert r2 != r1

            # Offboard the user (tenant-scoped write, mirrors AuthService).
            async with db_manager.get_session_async(tenant_key=tenant_key) as session:
                await session.execute(_update(User).where(User.tenant_key == tenant_key).values(is_active=False))
                await session.commit()

            # The deactivated user presenting the still-valid r2 is rejected.
            blocked = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r2,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert blocked.status_code == 401, blocked.text
            body = blocked.json()
            detail = _err_text(body)
            assert "invalid_grant" in detail.lower(), body
        finally:
            restore()


class TestRefreshAcceptsJsonAndBasicAuth:
    """API-0021e Phase 1.2: /refresh accepts JSON body and HTTP Basic Auth.

    Same parsing rules as /token. ChatGPT shape compatibility.
    """

    @pytest.mark.asyncio
    async def test_refresh_accepts_json_content_type(self, api_client, db_manager):
        """Issue refresh+access via /token, then POST /refresh with JSON -> 200.

        MUST FAIL before Phase 1.2 fix: pre-fix returns 422.
        """
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            response = await api_client.post(
                "/api/oauth/refresh",
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                    "client_secret": plaintext_secret,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert "access_token" in body
            assert "refresh_token" in body
            assert body["refresh_token"] != r1
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_refresh_accepts_basic_auth_header(self, api_client, db_manager):
        """Client credentials via HTTP Basic Auth header -> 200.

        MUST FAIL before Phase 1.2 fix: pre-fix ignores Authorization header
        and treats body as missing client_secret -> 401 invalid_client.
        """
        import base64 as _b64

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(48)
        secret_hash = _bcrypt_hash(plaintext_secret)
        redirect_uri = "http://localhost:3000/callback"

        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=client_id,
        )

        basic = _b64.b64encode(f"{client_id}:{plaintext_secret}".encode("ascii")).decode("ascii")

        restore = _install_confidential_resolver((client_id, secret_hash, [redirect_uri]))
        try:
            initial = await _exchange_code_for_token_pair(
                api_client,
                code_value=code_value,
                client_id=client_id,
                client_secret=plaintext_secret,
                code_verifier=verifier,
                redirect_uri=redirect_uri,
            )
            r1 = initial["refresh_token"]

            response = await api_client.post(
                "/api/oauth/refresh",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": r1,
                    "client_id": client_id,
                },
                headers={"Authorization": f"Basic {basic}"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert "access_token" in body
            assert body["refresh_token"] != r1
        finally:
            restore()


class TestPublicClientRefreshTokenGrant:
    """BE-6161: public PKCE clients (CLIs) get ROTATING refresh tokens.

    Failing layer = the /token + /refresh FastAPI routes for a PUBLIC client
    (the built-in PKCE-only client, no client_secret) — the exact boundary the
    Codex / Claude Code / Gemini CLIs exercise. Before BE-6161 a public client
    received NO refresh token at /token and was rejected at /refresh with
    ``invalid_client``; after BE-6161 it receives a one-time-use rotating
    refresh token, rotation invalidates the prior token, and reuse of a consumed
    token revokes the whole family (RFC 8252 / OAuth 2.1 §4.3.1).

    No resolver is installed — the process-wide default built-in resolver
    recognizes ``BUILTIN_CLIENT_ID`` as a public (no-secret) client, exactly
    as the public-client /token tests in ``test_oauth_endpoints.py`` rely on.
    """

    async def _public_token_pair(
        self,
        api_client,
        db_manager,
        *,
        redirect_uri: str = "http://localhost:3000/callback",
    ) -> dict:
        """Seed a built-in public-client auth code and exchange it at /token.

        Returns the /token response body. The public client presents only a
        PKCE ``code_verifier`` (no ``client_secret``).
        """
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            client_id=BUILTIN_CLIENT_ID,
            redirect_uri=redirect_uri,
        )
        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": redirect_uri,
                # no client_secret — public PKCE client
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    @pytest.mark.asyncio
    async def test_public_client_token_issues_refresh_token(self, api_client, db_manager):
        """/token for a public PKCE client now returns a non-empty string refresh_token (BE-6161)."""
        body = await self._public_token_pair(api_client, db_manager)
        assert "access_token" in body
        assert isinstance(body.get("refresh_token"), str) and body["refresh_token"], body
        assert isinstance(body.get("refresh_expires_in"), int) and body["refresh_expires_in"] > 0, body

    @pytest.mark.asyncio
    async def test_public_client_refresh_rotates_and_old_token_rejected(self, api_client, db_manager, monkeypatch):
        """Public-client /refresh rotates the token; replaying the consumed token -> 401 invalid_grant.

        Idempotency window collapsed to 0 so the replay exercises the
        OUTSIDE-window reuse-detection path, not the in-window idempotency hatch.
        """
        from giljo_mcp.services import oauth_refresh_service as _refresh_svc

        monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)

        initial = await self._public_token_pair(api_client, db_manager)
        r1 = initial["refresh_token"]

        # Public client refresh: NO client_secret in the body.
        rotation = await api_client.post(
            "/api/oauth/refresh",
            data={
                "grant_type": "refresh_token",
                "refresh_token": r1,
                "client_id": BUILTIN_CLIENT_ID,
            },
        )
        assert rotation.status_code == 200, rotation.text
        body = rotation.json()
        r2 = body["refresh_token"]
        assert r2 != r1, "refresh_token must rotate"
        assert body["access_token"].count(".") == 2
        assert body["token_type"] == "bearer"

        # Replaying the consumed r1 -> 401 invalid_grant.
        replay = await api_client.post(
            "/api/oauth/refresh",
            data={
                "grant_type": "refresh_token",
                "refresh_token": r1,
                "client_id": BUILTIN_CLIENT_ID,
            },
        )
        assert replay.status_code == 401, replay.text
        replay_body = replay.json()
        replay_detail = _err_text(replay_body)
        assert "invalid_grant" in replay_detail.lower(), replay_body

    @pytest.mark.asyncio
    async def test_public_client_consumed_token_reuse_revokes_family(self, api_client, db_manager, monkeypatch):
        """Reuse of a consumed public-client refresh token revokes the whole family:
        the freshly-rotated sibling token is also rejected afterwards (RFC 6749 §10.4)."""
        from giljo_mcp.services import oauth_refresh_service as _refresh_svc

        monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)

        initial = await self._public_token_pair(api_client, db_manager)
        r1 = initial["refresh_token"]

        # Rotate r1 -> r2 (success).
        rotation = await api_client.post(
            "/api/oauth/refresh",
            data={"grant_type": "refresh_token", "refresh_token": r1, "client_id": BUILTIN_CLIENT_ID},
        )
        assert rotation.status_code == 200, rotation.text
        r2 = rotation.json()["refresh_token"]

        # Reuse the consumed r1 -> 401 + family revocation.
        replay = await api_client.post(
            "/api/oauth/refresh",
            data={"grant_type": "refresh_token", "refresh_token": r1, "client_id": BUILTIN_CLIENT_ID},
        )
        assert replay.status_code == 401, replay.text

        # The rotated sibling r2 must now ALSO be rejected — family revoked.
        sibling = await api_client.post(
            "/api/oauth/refresh",
            data={"grant_type": "refresh_token", "refresh_token": r2, "client_id": BUILTIN_CLIENT_ID},
        )
        assert sibling.status_code == 401, sibling.text
        sibling_body = sibling.json()
        sibling_detail = _err_text(sibling_body)
        assert "invalid_grant" in sibling_detail.lower(), sibling_body

    @pytest.mark.asyncio
    async def test_public_client_refresh_rejects_presented_secret(self, api_client, db_manager):
        """A public client that erroneously presents a client_secret at /refresh is
        rejected as ``invalid_client`` — the public-client auth shape forbids a secret,
        so the server never silently accepts a credential it would not validate."""
        initial = await self._public_token_pair(api_client, db_manager)
        r1 = initial["refresh_token"]

        response = await api_client.post(
            "/api/oauth/refresh",
            data={
                "grant_type": "refresh_token",
                "refresh_token": r1,
                "client_id": BUILTIN_CLIENT_ID,
                "client_secret": "public-clients-must-not-send-this",
            },
        )
        assert response.status_code == 401, response.text
        body = response.json()
        detail = _err_text(body)
        assert "invalid_client" in detail.lower(), body
