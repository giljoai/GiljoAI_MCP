# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
API endpoint tests for OAuth 2.1 Authorization Code flow with PKCE.

Tests the FastAPI endpoints that wrap the OAuthService:
- POST /api/oauth/authorize (consent processing, requires auth)
- POST /api/oauth/token (code-to-token exchange, public)
- GET /api/oauth/.well-known/oauth-authorization-server (metadata, public)

Test Strategy:
- Endpoint validation tests use the api_client fixture (httpx AsyncClient)
- Authenticated endpoints use the auth_headers fixture for JWT cookie injection
- Token endpoint tests create authorization codes via direct DB insertion
  to isolate endpoint behavior from service internals

Handover 0828 Phase 3.
"""

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from giljo_mcp.services.oauth_service import BUILTIN_CLIENT_ID


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate a valid PKCE code_verifier and code_challenge pair."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


class TestOAuthMetadataEndpoint:
    """Tests for GET /api/oauth/.well-known/oauth-authorization-server."""

    @pytest.mark.asyncio
    async def test_metadata_endpoint_returns_correct_fields(self, api_client):
        """Metadata endpoint must return all required OAuth server metadata fields.

        RFC 8414 §2: endpoint URLs MUST be absolute. Pre-API-0021c-live-fix
        these were relative paths; updated when ``registration_endpoint`` was
        added so the response is fully spec-compliant.
        """
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200

        data = response.json()
        assert "issuer" in data
        # Absolute URLs (RFC 8414 §2)
        assert data["authorization_endpoint"].endswith("/oauth/authorize")
        assert data["authorization_endpoint"].startswith(("http://", "https://"))
        assert data["token_endpoint"].endswith("/api/oauth/token")
        assert data["token_endpoint"].startswith(("http://", "https://"))
        assert data["response_types_supported"] == ["code"]
        assert data["code_challenge_methods_supported"] == ["S256"]
        # API-0021e Phase 3: refresh_token grant added.
        assert data["grant_types_supported"] == ["authorization_code", "refresh_token"]

    @pytest.mark.asyncio
    async def test_metadata_endpoint_is_public(self, api_client):
        """Metadata endpoint must be accessible without authentication."""
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metadata_omits_registration_endpoint_in_ce(self, api_client, monkeypatch):
        """REGRESSION (API-0021c live-fix): CE has no DCR endpoint
        (saas_endpoints/ is stripped on export), so the metadata response
        must NOT advertise ``registration_endpoint``. Advertising a path
        that doesn't exist would mislead clients into 404s.
        """
        monkeypatch.setenv("GILJO_MODE", "")  # CE default
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200
        data = response.json()
        # Either the field is absent (response_model_exclude_none) or explicitly null.
        assert data.get("registration_endpoint") is None
        assert "registration_endpoint" not in data or data["registration_endpoint"] is None

    @pytest.mark.asyncio
    async def test_metadata_advertises_registration_endpoint_in_saas(self, api_client, monkeypatch):
        """REGRESSION (API-0021c live-fix): in SaaS/demo mode the metadata
        response MUST advertise the absolute URL of the DCR endpoint.

        Without this, claude.ai (and other RFC 7591 clients that rely on
        spec discovery) fall back to ``<issuer>/register`` which is a 404
        on this server, causing connector setup to fail before consent.
        """
        monkeypatch.setenv("GILJO_MODE", "demo")
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200
        data = response.json()
        reg = data.get("registration_endpoint")
        assert reg is not None, "SaaS/demo mode must advertise registration_endpoint"
        assert reg.endswith("/api/saas/oauth/register")
        assert reg.startswith(("http://", "https://"))


class TestOAuthTokenEndpoint:
    """Tests for POST /api/oauth/token."""

    @pytest.mark.asyncio
    async def test_token_endpoint_rejects_invalid_grant_type(self, api_client):
        """Token endpoint must reject grant types other than authorization_code."""
        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "client_credentials",
                "code": "some-code",
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": "some-verifier",
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        assert response.status_code == 400
        assert "grant_type" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_token_endpoint_rejects_bad_pkce(self, api_client, db_manager):
        """Token endpoint must reject requests where PKCE verification fails."""
        from giljo_mcp.models.auth import User
        from giljo_mcp.models.oauth import OAuthAuthorizationCode
        from giljo_mcp.models.organizations import Organization
        from giljo_mcp.tenant import TenantManager

        _verifier, challenge = _generate_pkce_pair()
        wrong_verifier = secrets.token_urlsafe(64)
        tenant_key = TenantManager.generate_tenant_key()
        code_value = secrets.token_urlsafe(64)

        async with db_manager.get_session_async() as session:
            org = Organization(
                name="OAuth Test Org",
                slug=f"oauth-test-{uuid4().hex[:8]}",
                tenant_key=tenant_key,
                is_active=True,
            )
            session.add(org)
            await session.flush()

            user = User(
                id=str(uuid4()),
                username=f"oauth_token_test_{uuid4().hex[:8]}",
                email=f"oauth_token_{uuid4().hex[:8]}@example.com",
                role="developer",
                tenant_key=tenant_key,
                is_active=True,
                org_id=org.id,
            )
            session.add(user)
            await session.flush()

            auth_code = OAuthAuthorizationCode(
                code=code_value,
                client_id=BUILTIN_CLIENT_ID,
                user_id=user.id,
                tenant_key=tenant_key,
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                scope="mcp",
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
                used=False,
            )
            session.add(auth_code)
            await session.commit()

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": wrong_verifier,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        assert response.status_code == 400
        body = response.json()
        # Security hardening: error detail must NOT reveal PKCE specifics
        assert "detail" in body or "message" in body
        detail_text = body.get("detail", body.get("message", "")).lower()
        assert "pkce" not in detail_text, "Error should not leak PKCE details"
        assert "verifier" not in detail_text, "Error should not leak verifier details"

    @pytest.mark.asyncio
    async def test_token_endpoint_returns_jwt(self, api_client, db_manager):
        """Token endpoint must return a valid JWT on successful code exchange."""
        from giljo_mcp.models.auth import User
        from giljo_mcp.models.oauth import OAuthAuthorizationCode
        from giljo_mcp.models.organizations import Organization
        from giljo_mcp.tenant import TenantManager

        verifier, challenge = _generate_pkce_pair()
        tenant_key = TenantManager.generate_tenant_key()
        code_value = secrets.token_urlsafe(64)

        async with db_manager.get_session_async() as session:
            org = Organization(
                name="OAuth JWT Test Org",
                slug=f"oauth-jwt-{uuid4().hex[:8]}",
                tenant_key=tenant_key,
                is_active=True,
            )
            session.add(org)
            await session.flush()

            user = User(
                id=str(uuid4()),
                username=f"oauth_jwt_test_{uuid4().hex[:8]}",
                email=f"oauth_jwt_{uuid4().hex[:8]}@example.com",
                role="developer",
                tenant_key=tenant_key,
                is_active=True,
                org_id=org.id,
            )
            session.add(user)
            await session.flush()

            auth_code = OAuthAuthorizationCode(
                code=code_value,
                client_id=BUILTIN_CLIENT_ID,
                user_id=user.id,
                tenant_key=tenant_key,
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                scope="mcp",
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
                used=False,
            )
            session.add(auth_code)
            await session.commit()

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
        assert data["access_token"].count(".") == 2

    @pytest.mark.asyncio
    async def test_token_endpoint_is_public(self, api_client):
        """Token endpoint must be accessible without authentication (returns 400 for bad data, not 401)."""
        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "nonexistent",
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": "verifier",
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        assert response.status_code == 400


class TestOAuthAuthorizeEndpoint:
    """Tests for POST /api/oauth/authorize."""

    @pytest.mark.asyncio
    async def test_authorize_endpoint_validates_params(self, api_client, auth_headers):
        """Authorize endpoint must validate OAuth parameters and return redirect on success."""
        _verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "test-state-value",
                "response_type": "code",
            },
            follow_redirects=False,
        )
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            data = response.json()
            assert "redirect_uri" in data
            assert "code" in data["redirect_uri"]
            assert "test-state-value" in data["redirect_uri"]

    @pytest.mark.asyncio
    async def test_authorize_endpoint_rejects_invalid_client(self, api_client, auth_headers):
        """Authorize endpoint must reject requests with an invalid client_id."""
        _verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": "invalid-client-id",
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "test-state",
                "response_type": "code",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_authorize_endpoint_requires_auth(self, api_client):
        """Authorize POST endpoint must require authentication (no auth = 401)."""
        _verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "test-state",
                "response_type": "code",
            },
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# API-0021d Phase 2 — RFC 8707 resource indicator binding
# ---------------------------------------------------------------------------


async def _seed_user_and_code(
    db_manager,
    *,
    challenge: str,
    code_value: str,
    resource: str | None,
    redirect_uri: str = "http://localhost:3000/callback",
    client_id: str = BUILTIN_CLIENT_ID,
):
    """Insert an Organization + User + OAuthAuthorizationCode row.

    Returns the tenant_key used so callers can assert tenant isolation.
    """
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.oauth import OAuthAuthorizationCode
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"Resource Test Org {uuid4().hex[:6]}",
            slug=f"res-org-{uuid4().hex[:8]}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            id=str(uuid4()),
            username=f"res_user_{uuid4().hex[:8]}",
            email=f"res_{uuid4().hex[:8]}@example.com",
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


class TestResourceIndicatorBinding:
    """API-0021d Phase 2: RFC 8707 resource indicator must bind JWT aud.

    Failing-layer tests run through the FastAPI route — same boundary the
    claude.ai connector exercises against demo. CLAUDE.md mandates a test
    at the layer the bug occurred (BE-5042 lesson).
    """

    @pytest.mark.asyncio
    async def test_token_without_resource_when_code_bound_returns_400(self, api_client, db_manager):
        """Auth-code carries `resource`; client omits it at /token → 400 invalid_request."""
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            resource="https://demo.giljo.ai/mcp",
        )

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
                # no resource
            },
        )
        assert response.status_code == 400, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_request" in detail_text.lower()

    @pytest.mark.asyncio
    async def test_token_resource_mismatch_returns_401_invalid_grant(self, api_client, db_manager):
        """Auth-code resource ≠ client's `resource` → 401 invalid_grant (RFC 8707 §2.2)."""
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            resource="https://demo.giljo.ai/mcp",
        )

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
                "resource": "https://attacker.example/mcp",
            },
        )
        assert response.status_code == 401, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_grant" in detail_text.lower()

    @pytest.mark.asyncio
    async def test_token_resource_match_returns_jwt_with_aud_bound(self, api_client, db_manager):
        """Auth-code resource == client's `resource` → 200, JWT aud == that value."""
        import jwt as _jwt

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        bound_resource = "https://demo.giljo.ai/mcp"
        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            resource=bound_resource,
        )

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
                "resource": bound_resource,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        access_token = body["access_token"]

        # Decode unsigned to inspect aud — JWT signature already verified by service.
        decoded = _jwt.decode(access_token, options={"verify_signature": False})
        assert decoded.get("aud") == bound_resource, decoded

    @pytest.mark.asyncio
    async def test_legacy_audless_code_still_issues_token(self, api_client, db_manager):
        """REGRESSION (back-compat): pre-API-0021d codes (no resource on record)
        plus a client that doesn't send `resource` continue to issue a token
        with the canonical-MCP-URI fallback as `aud`. Locks the
        transition-window contract for one release.
        """
        import jwt as _jwt

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(
            db_manager,
            challenge=challenge,
            code_value=code_value,
            resource=None,  # pre-API-0021d in-flight code
        )

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
                # no resource — legacy client
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        access_token = body["access_token"]
        decoded = _jwt.decode(access_token, options={"verify_signature": False})
        # Falls back to canonical MCP URI passed by the route layer.
        assert "aud" in decoded, decoded
        assert decoded["aud"].endswith("/mcp"), decoded

    @pytest.mark.asyncio
    async def test_authorize_persists_resource_onto_code(self, api_client, auth_headers, db_manager):
        """POST /api/oauth/authorize with `resource` persists it onto the code row.

        Reachability test for the Phase 2 wiring: route → service →
        OAuthAuthorizationCode.resource column. Verifies the round-trip
        without coupling to the /token endpoint.
        """
        from sqlalchemy import select as _select

        from giljo_mcp.models.oauth import OAuthAuthorizationCode

        _verifier, challenge = _generate_pkce_pair()
        bound_resource = "https://demo.giljo.ai/mcp"

        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "test-state",
                "response_type": "code",
                "resource": bound_resource,
            },
            follow_redirects=False,
        )
        assert response.status_code in (200, 302), response.text
        data = response.json()
        # Extract the code from the redirect URI query
        redirect_url = data["redirect_uri"]
        assert "code=" in redirect_url
        issued_code = redirect_url.split("code=", 1)[1].split("&", 1)[0]

        # Verify the code row has the resource bound.
        async with db_manager.get_session_async() as session:
            row = (
                await session.execute(_select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == issued_code))
            ).scalar_one()
            assert row.resource == bound_resource

    @pytest.mark.asyncio
    async def test_authorize_rejects_malformed_resource(self, api_client, auth_headers):
        """A malformed `resource` (no scheme) must be rejected at /authorize as 400."""
        _verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "test",
                "response_type": "code",
                "resource": "demo.giljo.ai/mcp",  # missing scheme
            },
        )
        assert response.status_code == 400, response.text


class TestProtectedResourceMetadataResourceIndicators:
    """API-0021d F3: RFC 9728 metadata MUST advertise resource_indicators_supported."""

    @pytest.mark.asyncio
    async def test_root_metadata_advertises_resource_indicators_supported(self, api_client):
        response = await api_client.get("/.well-known/oauth-protected-resource")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body.get("resource_indicators_supported") is True, body


# ---------------------------------------------------------------------------
# API-0021e Phase 1 — verify client_secret at /token for confidential clients
# ---------------------------------------------------------------------------


async def _seed_confidential_dcr_code(
    db_manager,
    *,
    challenge: str,
    code_value: str,
    redirect_uri: str = "http://localhost:3000/callback",
    plaintext_secret: str | None = None,
) -> tuple[str, str, str, str]:
    """Insert an Org + User + AuthCode bound to a synthetic confidential client.

    Returns ``(client_id, plaintext_secret, tenant_key, secret_hash)``. The
    OAuthClient row itself is NOT persisted (CE test DB has no oauth_clients
    table — that's a SaaS-only migration). Tests inject a stub resolver that
    returns a ``ResolvedClient`` with the bcrypt hash directly, mirroring
    what the SaaS resolver would have produced after a DCR registration.
    """
    from uuid import uuid4 as _uuid4

    import bcrypt as _bcrypt

    from giljo_mcp.models.auth import User
    from giljo_mcp.models.oauth import OAuthAuthorizationCode
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    if plaintext_secret is None:
        plaintext_secret = secrets.token_urlsafe(48)
    secret_hash = _bcrypt.hashpw(plaintext_secret.encode("utf-8"), _bcrypt.gensalt()).decode("ascii")
    tenant_key = TenantManager.generate_tenant_key()
    client_id = str(_uuid4())

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"DCR Test Org {_uuid4().hex[:6]}",
            slug=f"dcr-org-{_uuid4().hex[:8]}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            id=str(_uuid4()),
            username=f"dcr_user_{_uuid4().hex[:8]}",
            email=f"dcr_{_uuid4().hex[:8]}@example.com",
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
            resource=None,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            used=False,
        )
        session.add(auth_code)
        await session.commit()

    return client_id, plaintext_secret, tenant_key, secret_hash


def _install_confidential_resolver(client_id: str, secret_hash: str, redirect_uri: str):
    """Install a resolver that returns a confidential ``ResolvedClient``.

    Returns a ``(prior_resolver, restore)`` pair; tests should call
    ``restore()`` in a ``finally`` to revert. Mirrors the pattern used by
    ``TestAuthorizeAcceptsClaudeComRedirectUri``.
    """
    from giljo_mcp.services import oauth_service as svc

    prior = svc.get_client_resolver()

    def _resolver(cid: str, tenant_key: str):
        assert tenant_key  # tenant filter still mandatory
        if cid != client_id:
            return None
        return svc.ResolvedClient(
            client_id=cid,
            client_name="DCR Confidential Test Client",
            redirect_uris=[redirect_uri],
            client_secret_hash=secret_hash,
        )

    svc.set_client_resolver(_resolver)

    def _restore() -> None:
        svc.set_client_resolver(prior)

    return _restore


class TestTokenClientSecretVerification:
    """API-0021e Phase 1: confidential DCR clients MUST present a valid
    client_secret at /token. Public PKCE-only clients (built-in CE) MUST
    NOT carry a client_secret. Failing-layer = the FastAPI route, same
    boundary the claude.ai connector exercises (CLAUDE.md regression-test
    rule)."""

    @pytest.mark.asyncio
    async def test_token_exchange_rejects_wrong_client_secret(self, api_client, db_manager):
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, _correct, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": "totally-wrong-secret",
                },
            )
        finally:
            restore()

        assert response.status_code == 401, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_client" in detail_text.lower(), body

    @pytest.mark.asyncio
    async def test_token_exchange_accepts_correct_client_secret(self, api_client, db_manager):
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": plaintext_secret,
                },
            )
        finally:
            restore()

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"].count(".") == 2

    @pytest.mark.asyncio
    async def test_token_exchange_rejects_confidential_client_with_no_secret(self, api_client, db_manager):
        """A confidential DCR client (client_secret_hash present) MUST NOT be
        able to exchange a code without a client_secret — that would defeat the
        Phase 1 fix entirely. The pre-API-0021e bug shipped this path as 200.
        """
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, _secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    # no client_secret
                },
            )
        finally:
            restore()

        assert response.status_code == 401, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_client" in detail_text.lower(), body

    @pytest.mark.asyncio
    async def test_token_exchange_public_pkce_client_no_secret_succeeds(self, api_client, db_manager):
        """REGRESSION: the built-in CE PKCE-only client (no client_secret_hash)
        MUST keep working without a client_secret. PKCE remains the
        proof-of-possession mechanism for public clients."""
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(db_manager, challenge=challenge, code_value=code_value, resource=None)

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "code_verifier": verifier,
                "redirect_uri": "http://localhost:3000/callback",
                # no client_secret — PKCE-only public client
            },
        )
        assert response.status_code == 200, response.text

    # API-0021e Phase 1.1: code_verifier is OPTIONAL for confidential clients
    # per RFC 6749 §6 (client_secret is the alternative authentication). The
    # original Phase 1 work shipped with code_verifier still required at the
    # FastAPI Form level, so ChatGPT (which sends client_secret_post but no
    # PKCE per RFC 6749 §4.1.3) was hitting HTTP 422 from Pydantic before any
    # handler logic ran. Live evidence on demo.giljo.ai 2026-05-10 09:28:06
    # UTC: ChatGPT POSTed /token twice with no code_verifier and got
    # {"loc":["body","code_verifier"],"msg":"Field required","type":"missing"}.

    @pytest.mark.asyncio
    async def test_token_exchange_confidential_client_no_pkce_succeeds(self, api_client, db_manager):
        """A confidential DCR client that authenticates with client_secret MUST
        be able to exchange a code WITHOUT presenting code_verifier. RFC 6749
        §6 treats client authentication and PKCE as alternative proof-of-
        possession mechanisms; OAuth 2.1 §7.4 prefers both, but the spec text
        in API-0021e called for client_secret as an "alternative to PKCE".

        The auth-code record still carries a code_challenge (set at
        /authorize), but the /token side does not require the verifier when
        the client has authenticated via secret.
        """
        verifier, challenge = _generate_pkce_pair()
        del verifier  # We deliberately do NOT send a verifier; challenge stays on the auth-code row.
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": plaintext_secret,
                    # no code_verifier — confidential client uses secret as auth
                },
            )
        finally:
            restore()

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"].count(".") == 2

    @pytest.mark.asyncio
    async def test_token_exchange_confidential_client_with_wrong_pkce_rejected(self, api_client, db_manager):
        """Defense-in-depth: if a confidential client DOES present a
        code_verifier, it MUST verify against the stored challenge. Sending
        client_secret + a wrong verifier is suspicious and rejected as
        invalid_grant. Belt-and-suspenders is fine; mismatched belt is not.
        """
        _good_verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        wrong_verifier, _wrong_challenge = _generate_pkce_pair()

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": wrong_verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": plaintext_secret,
                },
            )
        finally:
            restore()

        assert response.status_code == 400, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_request" in detail_text.lower() or "invalid_grant" in detail_text.lower(), body

    @pytest.mark.asyncio
    async def test_token_exchange_public_client_no_pkce_rejected(self, api_client, db_manager):
        """A public PKCE-only client (no client_secret_hash) MUST still
        present a code_verifier — without it, nothing authenticates the
        client. The pre-Phase-1.1 wire surfaced this as HTTP 422 from
        Pydantic; post-fix it MUST be a clean OAuth invalid_request (400).
        """
        _verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        await _seed_user_and_code(db_manager, challenge=challenge, code_value=code_value, resource=None)

        response = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code_value,
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                # no code_verifier — public client has no other auth, must fail
            },
        )
        assert response.status_code == 400, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_request" in detail_text.lower(), body


class TestTokenAcceptsJsonAndBasicAuth:
    """API-0021e Phase 1.2: /token accepts JSON body and HTTP Basic Auth.

    ChatGPT connector posts ``application/json`` to /token (verified live on
    demo.giljo.ai 2026-05-10 10:06:12 EDT, Azure 172.212.159.67/.68). The
    pre-Phase-1.2 handler used FastAPI ``Form(...)`` parameters which only
    parse ``application/x-www-form-urlencoded`` -- every JSON request
    surfaced as a 422 with "Field required" on every field.

    RFC 6749 §3.2 specifies form-encoded for /token, but the major OAuth
    providers (Google, GitHub, Auth0, Okta) accept both. claude.ai still
    sends form-encoded; we must keep that path working AND start accepting
    JSON. We also accept HTTP Basic Auth for ``client_secret_basic`` clients
    per RFC 6749 §2.3.1.
    """

    @pytest.mark.asyncio
    async def test_token_exchange_accepts_json_content_type(self, api_client, db_manager):
        """POST /token with Content-Type: application/json + JSON body must succeed.

        MUST FAIL before Phase 1.2 fix: pre-fix returns 422 because Form(...)
        parameters don't parse JSON.
        """
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": plaintext_secret,
                },
            )
        finally:
            restore()

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"].count(".") == 2

    @pytest.mark.asyncio
    async def test_token_exchange_accepts_basic_auth_header(self, api_client, db_manager):
        """POST /token with Authorization: Basic <b64(client_id:client_secret)> works.

        Body carries grant_type+code+redirect_uri only; credentials live
        in the header per RFC 6749 §2.3.1 (``client_secret_basic``).

        MUST FAIL before Phase 1.2 fix: handler ignored Authorization header
        so the request looked like a confidential client missing its
        secret -> 401 invalid_client.
        """
        import base64 as _b64

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        basic = _b64.b64encode(f"{client_id}:{plaintext_secret}".encode("ascii")).decode("ascii")

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                },
                headers={"Authorization": f"Basic {basic}"},
            )
        finally:
            restore()

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_token_exchange_form_encoded_still_works(self, api_client, db_manager):
        """REGRESSION: form-encoded path must NOT regress (claude.ai compat)."""
        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": plaintext_secret,
                },
            )
        finally:
            restore()

        assert response.status_code == 200, response.text
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_token_exchange_basic_auth_header_overrides_body(self, api_client, db_manager):
        """RFC 6749 §2.3.1: Basic Auth header takes precedence over body.

        Body contains a WRONG client_secret; header has the correct one.
        Header should win -> 200.

        MUST FAIL before Phase 1.2 fix: handler reads body only, sees the
        wrong secret -> 401 invalid_client.
        """
        import base64 as _b64

        verifier, challenge = _generate_pkce_pair()
        code_value = secrets.token_urlsafe(64)
        client_id, plaintext_secret, _tenant_key, secret_hash = await _seed_confidential_dcr_code(
            db_manager, challenge=challenge, code_value=code_value
        )

        basic = _b64.b64encode(f"{client_id}:{plaintext_secret}".encode("ascii")).decode("ascii")

        restore = _install_confidential_resolver(client_id, secret_hash, "http://localhost:3000/callback")
        try:
            response = await api_client.post(
                "/api/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code_value,
                    "client_id": client_id,
                    "code_verifier": verifier,
                    "redirect_uri": "http://localhost:3000/callback",
                    "client_secret": "wrong-secret-in-body",
                },
                headers={"Authorization": f"Basic {basic}"},
            )
        finally:
            restore()

        assert response.status_code == 200, response.text

    @pytest.mark.asyncio
    async def test_token_exchange_malformed_json_body(self, api_client):
        """Content-Type: application/json + malformed JSON -> 400 invalid_request.

        Must NOT be 422 (Pydantic schema artifact) and MUST NOT be 500.
        """
        response = await api_client.post(
            "/api/oauth/token",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400, response.text
        body = response.json()
        detail_text = body.get("detail", body.get("message", ""))
        assert "invalid_request" in detail_text.lower(), body


class TestAuthorizeAcceptsClaudeComRedirectUri:
    """API-0021d Phase 3: /authorize accepts a claude.com redirect when the
    resolver knows the client. Pairs with the SaaS-side DCR test in
    tests/saas/test_oauth_dcr_endpoint.py that locks the registration path."""

    @pytest.mark.asyncio
    async def test_authorize_with_claude_com_redirect_succeeds(self, api_client, auth_headers):
        """POST /api/oauth/authorize with a claude.com redirect_uri completes
        when the resolver knows the client.

        For the built-in CE client the localhost regex matcher would reject
        claude.com — so we install a temporary resolver that returns a DCR
        client registered with both URIs, then restore on teardown.
        """
        from giljo_mcp.services import oauth_service as svc

        _verifier, challenge = _generate_pkce_pair()
        prior = svc.get_client_resolver()

        def _resolver(client_id: str, tenant_key: str):
            assert tenant_key  # tenant filter still mandatory
            return svc.ResolvedClient(
                client_id=client_id,
                client_name="Claude Connector",
                redirect_uris=[
                    "https://claude.ai/api/mcp/auth_callback",
                    "https://claude.com/api/mcp/auth_callback",
                ],
                client_secret_hash=None,
            )

        svc.set_client_resolver(_resolver)
        try:
            response = await api_client.post(
                "/api/oauth/authorize",
                headers=auth_headers,
                json={
                    "client_id": "11111111-1111-1111-1111-111111111111",
                    "redirect_uri": "https://claude.com/api/mcp/auth_callback",
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "scope": "mcp:read mcp:write",
                    "state": "test-state",
                    "response_type": "code",
                    "resource": "https://demo.giljo.ai/mcp",
                },
                follow_redirects=False,
            )
        finally:
            svc.set_client_resolver(prior)

        assert response.status_code in (200, 302), response.text
        data = response.json()
        assert data["redirect_uri"].startswith("https://claude.com/api/mcp/auth_callback")
