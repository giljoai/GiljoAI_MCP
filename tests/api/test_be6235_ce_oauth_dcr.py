# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6235 — CE OAuth Dynamic Client Registration, full-flow regression.

Exercises the failing layer end-to-end through the FastAPI transport: AS metadata
advertises the CE registration_endpoint -> DCR returns the built-in public client
-> /authorize + /token succeed for a localhost redirect_uri. This is the gap that
previously stopped a fresh CE from completing OAuth auto-attach (an MCP harness has
no way to adopt a server-advertised static client_id; without a registration_endpoint
its DCR fallback 404s).
"""

import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import pytest

from giljo_mcp.services.oauth_service import BUILTIN_CLIENT_ID


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class TestCeDcrEndpoint:
    """POST /api/oauth/register (CE built-in public client, persists nothing)."""

    @pytest.mark.asyncio
    async def test_register_returns_builtin_public_client(self, api_client):
        resp = await api_client.post(
            "/api/oauth/register",
            json={
                "client_name": "Claude Code",
                "redirect_uris": ["http://localhost:54545/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # CE mints no per-client id — it always returns the built-in public client.
        assert data["client_id"] == BUILTIN_CLIENT_ID
        assert data["token_endpoint_auth_method"] == "none"
        # Public PKCE client: NO secret in the response (RFC 7591 §3.2.1).
        assert "client_secret" not in data
        # Requested loopback redirect is echoed for the harness to use at /authorize.
        assert data["redirect_uris"] == ["http://localhost:54545/callback"]
        assert "authorization_code" in data["grant_types"]

    @pytest.mark.asyncio
    async def test_register_defaults_client_name_and_grants(self, api_client):
        resp = await api_client.post(
            "/api/oauth/register",
            json={"redirect_uris": ["http://127.0.0.1:8080/cb"]},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["client_id"] == BUILTIN_CLIENT_ID
        assert data["grant_types"] == ["authorization_code", "refresh_token"]
        assert data["response_types"] == ["code"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_uri",
        [
            "https://app.example.com/callback",  # original: plain external HTTPS
            "http://127.0.0.1.evil.test/cb",  # subdomain hijack of loopback IP literal
            "http://localhost.evil.test/cb",  # subdomain hijack of localhost keyword
            "http://localhost@evil.test/cb",  # userinfo trick: real host is evil.test
            "http://[::1]@evil.test/cb",  # IPv6 userinfo trick: real host is evil.test
            "https://localhost/cb",  # HTTPS not permitted for loopback (BE-6235)
            "http://evil.test/?x=http://localhost/",  # loopback buried in query string
        ],
    )
    async def test_register_rejects_non_loopback_redirect(self, api_client, bad_uri):
        """A CE server reachable over a non-loopback URL cannot OAuth (RFC 8252) —
        the DCR endpoint must reject a non-loopback redirect with 422, not bless it.

        Parametrized to cover adversarial look-alike URIs that exploit subdomain,
        userinfo (@), scheme, and query-string tricks to impersonate loopback
        addresses (BE-6235 hardening).  Uses RFC 6761 reserved .test TLD for
        adversarial domains.  If any case returns 200/201 the validator has a
        bypass — this test is the sentinel.
        """
        resp = await api_client.post(
            "/api/oauth/register",
            json={"redirect_uris": [bad_uri]},
        )
        assert resp.status_code == 422, (
            f"SECURITY: DCR accepted a non-loopback redirect_uri — validator bypass detected!\n"
            f"  URI: {bad_uri!r}\n"
            f"  Status: {resp.status_code}\n"
            f"  Body: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_register_rejects_empty_redirect_list(self, api_client):
        resp = await api_client.post(
            "/api/oauth/register",
            json={"redirect_uris": []},
        )
        assert resp.status_code == 422, resp.text


class TestCeOAuthFullFlow:
    """metadata -> DCR -> /authorize -> /token, the BE-6235 completion path."""

    @pytest.mark.asyncio
    async def test_metadata_then_dcr_then_authorize_then_token(self, api_client, auth_headers):
        from api.endpoints.oauth import register_edition_registration_endpoint

        # 0. Metadata advertises the CE registration_endpoint (set explicitly so the
        #    assertion is independent of the shared module-global's test ordering).
        register_edition_registration_endpoint("/api/oauth/register")
        meta = (await api_client.get("/api/oauth/.well-known/oauth-authorization-server")).json()
        reg = meta["registration_endpoint"]
        assert reg.endswith("/api/oauth/register")

        # 1. DCR — obtain the client_id the way an MCP harness does.
        redirect_uri = "http://localhost:7777/callback"
        dcr = await api_client.post(
            "/api/oauth/register",
            json={"client_name": "harness", "redirect_uris": [redirect_uri]},
        )
        assert dcr.status_code == 201, dcr.text
        client_id = dcr.json()["client_id"]
        assert client_id == BUILTIN_CLIENT_ID

        # 2. /authorize (authenticated consent) -> authorization code.
        verifier, challenge = _pkce_pair()
        authz = await api_client.post(
            "/api/oauth/authorize",
            headers=auth_headers,
            json={
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": "xyz",
                "response_type": "code",
            },
            follow_redirects=False,
        )
        assert authz.status_code == 200, authz.text
        target = authz.json()["redirect_uri"]
        code = parse_qs(urlparse(target).query)["code"][0]
        assert code

        # 3. /token — exchange code for an access token (public client + PKCE).
        tok = await api_client.post(
            "/api/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
            },
        )
        assert tok.status_code == 200, tok.text
        body = tok.json()
        assert body["access_token"]
        assert body["token_type"].lower() == "bearer"
