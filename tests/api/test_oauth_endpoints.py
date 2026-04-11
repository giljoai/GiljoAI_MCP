# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.giljo_mcp.services.oauth_service import BUILTIN_CLIENT_ID


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
        """Metadata endpoint must return all required OAuth server metadata fields."""
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200

        data = response.json()
        assert "issuer" in data
        assert data["authorization_endpoint"] == "/oauth/authorize"
        assert data["token_endpoint"] == "/api/oauth/token"
        assert data["response_types_supported"] == ["code"]
        assert data["code_challenge_methods_supported"] == ["S256"]
        assert data["grant_types_supported"] == ["authorization_code"]

    @pytest.mark.asyncio
    async def test_metadata_endpoint_is_public(self, api_client):
        """Metadata endpoint must be accessible without authentication."""
        response = await api_client.get("/api/oauth/.well-known/oauth-authorization-server")
        assert response.status_code == 200


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
        from src.giljo_mcp.models.auth import User
        from src.giljo_mcp.models.oauth import OAuthAuthorizationCode
        from src.giljo_mcp.models.organizations import Organization
        from src.giljo_mcp.tenant import TenantManager

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
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
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
        assert "pkce" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_token_endpoint_returns_jwt(self, api_client, db_manager):
        """Token endpoint must return a valid JWT on successful code exchange."""
        from src.giljo_mcp.models.auth import User
        from src.giljo_mcp.models.oauth import OAuthAuthorizationCode
        from src.giljo_mcp.models.organizations import Organization
        from src.giljo_mcp.tenant import TenantManager

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
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
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
        verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp",
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
        verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": "invalid-client-id",
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp",
                "state": "test-state",
                "response_type": "code",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_authorize_endpoint_requires_auth(self, api_client):
        """Authorize POST endpoint must require authentication (no auth = 401)."""
        verifier, challenge = _generate_pkce_pair()
        response = await api_client.post(
            "/api/oauth/authorize",
            json={
                "client_id": BUILTIN_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp",
                "state": "test-state",
                "response_type": "code",
            },
        )
        assert response.status_code in (401, 403)
