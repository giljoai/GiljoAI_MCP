# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tests for the OAuth client resolver seam (API-0021c).

The resolver seam decouples OAuthService from a hardcoded single client.
CE ships with a builtin single-client resolver (identical behavior to
pre-0021c). SaaS overrides the resolver at startup to look up clients
from the ``oauth_clients`` table populated by RFC 7591 dynamic client
registration.

These are pure-Python tests (no DB) — they exercise the Callable seam
directly. The /authorize integration with the resolver is covered by
the existing oauth tests in tests/test_oauth.py which MUST stay green.
"""

from __future__ import annotations

import pytest

from giljo_mcp.services.oauth_service import (
    ALLOWED_REDIRECT_URI_PATTERNS,
    BUILTIN_CLIENT_ID,
    OAuthService,
    ResolvedClient,
    _builtin_single_client_resolver,
    get_client_resolver,
    set_client_resolver,
)


@pytest.fixture(autouse=True)
def _restore_default_resolver():
    """Restore the default resolver after each test to keep isolation."""
    original = get_client_resolver()
    yield
    set_client_resolver(original)


class TestBuiltinResolver:
    """The default builtin resolver preserves pre-API-0021c behavior."""

    def test_returns_resolved_client_for_builtin_id(self):
        resolved = _builtin_single_client_resolver(BUILTIN_CLIENT_ID, "tk_irrelevant")
        assert resolved is not None
        assert resolved.client_id == BUILTIN_CLIENT_ID
        assert resolved.client_secret_hash is None
        assert resolved.redirect_uris is None  # signals "use pattern fallback"

    def test_returns_none_for_unknown_client_id(self):
        assert _builtin_single_client_resolver("unknown-client", "tk_irrelevant") is None

    def test_builtin_is_tenant_agnostic(self):
        """The CE built-in is global — every tenant resolves the same client.

        OAuth client resolution is global by client_id in both CE and SaaS
        (clients are shared app identities — OAUTH-MT); the built-in is the
        global localhost CLI fallback and recognises the canonical client_id
        regardless of which tenant_key is supplied.
        """
        a = _builtin_single_client_resolver(BUILTIN_CLIENT_ID, "tk_A")
        b = _builtin_single_client_resolver(BUILTIN_CLIENT_ID, "tk_B")
        assert a is not None and b is not None
        assert a.client_id == b.client_id == BUILTIN_CLIENT_ID

    def test_get_client_resolver_returns_callable(self):
        resolver = get_client_resolver()
        assert callable(resolver)
        assert resolver(BUILTIN_CLIENT_ID, "tk_irrelevant").client_id == BUILTIN_CLIENT_ID


class TestSetClientResolver:
    """set_client_resolver() swaps the active resolver atomically."""

    def test_replacement_is_used_for_lookup(self):
        sentinel = ResolvedClient(
            client_id="dcr-client-xyz",
            client_name="Claude.ai",
            redirect_uris=["https://claude.ai/oauth/callback"],
            client_secret_hash="$2b$12$dummyhash",
        )

        def custom_resolver(client_id: str, tenant_key: str):
            if client_id == sentinel.client_id and tenant_key == "tk_owner":
                return sentinel
            return None

        set_client_resolver(custom_resolver)

        assert get_client_resolver()(sentinel.client_id, "tk_owner") is sentinel
        assert get_client_resolver()("anything-else", "tk_owner") is None
        # Same client_id, different tenant_key → must not resolve
        assert get_client_resolver()(sentinel.client_id, "tk_other") is None

    def test_rejects_non_callable(self):
        with pytest.raises(TypeError, match="callable"):
            set_client_resolver("not-callable")  # type: ignore[arg-type]


@pytest.mark.asyncio
class TestValidateAuthorizeWithResolver:
    """validate_authorize_request consults the active resolver, not constants."""

    def _make_pkce(self):
        import base64
        import hashlib
        import secrets

        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    async def test_builtin_client_with_localhost_uri_passes(self):
        """Default resolver must keep CE behavior identical: builtin + localhost works."""
        # Note: validate_authorize_request awaits resolver; no DB needed for builtin
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()
        await svc.validate_authorize_request(
            client_id=BUILTIN_CLIENT_ID,
            redirect_uri="http://localhost:3000/callback",
            code_challenge=challenge,
            code_challenge_method="S256",
            response_type="code",
            scope="mcp:read",
            tenant_key="tk_seam_test",
        )

    async def test_unknown_client_rejected_by_default_resolver(self):
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()
        with pytest.raises(ValueError, match="client_id"):
            await svc.validate_authorize_request(
                client_id="unregistered-client",
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp:read",
                tenant_key="tk_seam_test",
            )

    async def test_missing_tenant_key_rejected(self):
        """validate_authorize_request requires a non-empty tenant_key."""
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()
        with pytest.raises(ValueError, match="tenant_key"):
            await svc.validate_authorize_request(
                client_id=BUILTIN_CLIENT_ID,
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp:read",
                tenant_key="",
            )

    async def test_injected_resolver_returning_none_causes_validate_to_raise(self):
        """Injecting a resolver that returns None for a known ID must cause
        validate_authorize_request to raise ValueError — proves the seam is
        consulted end-to-end, not just the builtin fallback."""

        def always_none_resolver(client_id: str, tenant_key: str):
            return None

        set_client_resolver(always_none_resolver)
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()
        with pytest.raises(ValueError, match="client_id"):
            await svc.validate_authorize_request(
                client_id=BUILTIN_CLIENT_ID,  # would succeed with builtin; must fail with injected
                redirect_uri="http://localhost:3000/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp:read",
                tenant_key="tk_seam_test",
            )

    async def test_async_resolver_is_awaited(self):
        """An async resolver must be awaited by validate_authorize_request.

        Locks the contract that ``ClientResolver`` accepts both sync and
        async callables — the SaaS DB-backed resolver is async because
        it awaits ``lookup_client``.
        """
        sentinel = ResolvedClient(
            client_id="async-client",
            client_name="Async Test Client",
            redirect_uris=["https://async.example/cb"],
            client_secret_hash=None,
        )

        async def async_resolver(client_id: str, tenant_key: str):
            if client_id == sentinel.client_id and tenant_key == "tk_async":
                return sentinel
            return None

        set_client_resolver(async_resolver)
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()

        await svc.validate_authorize_request(
            client_id="async-client",
            redirect_uri="https://async.example/cb",
            code_challenge=challenge,
            code_challenge_method="S256",
            response_type="code",
            scope="mcp:read",
            tenant_key="tk_async",
        )

        with pytest.raises(ValueError, match="client_id"):
            await svc.validate_authorize_request(
                client_id="async-client",
                redirect_uri="https://async.example/cb",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp:read",
                tenant_key="tk_other_tenant",
            )

    async def test_custom_resolver_with_exact_uri_match(self):
        """Resolver returning concrete redirect_uris uses exact-match validation."""

        def resolver(client_id: str, tenant_key: str):
            if client_id == "claudeai-client" and tenant_key == "tk_owner":
                return ResolvedClient(
                    client_id="claudeai-client",
                    client_name="Claude.ai",
                    redirect_uris=["https://claude.ai/oauth/callback"],
                    client_secret_hash="$2b$12$x",
                )
            return None

        set_client_resolver(resolver)
        svc = OAuthService(db_session=None)  # type: ignore[arg-type]
        _v, challenge = self._make_pkce()

        # Exact match passes (HTTPS is fine when resolver allows it)
        await svc.validate_authorize_request(
            client_id="claudeai-client",
            redirect_uri="https://claude.ai/oauth/callback",
            code_challenge=challenge,
            code_challenge_method="S256",
            response_type="code",
            scope="mcp:read",
            tenant_key="tk_owner",
        )

        # Non-registered URI rejected for the DCR client
        with pytest.raises(ValueError, match="redirect_uri"):
            await svc.validate_authorize_request(
                client_id="claudeai-client",
                redirect_uri="https://attacker.example/callback",
                code_challenge=challenge,
                code_challenge_method="S256",
                response_type="code",
                scope="mcp:read",
                tenant_key="tk_owner",
            )

    async def test_constants_remain_exported_for_internal_use(self):
        """Module-level constants used by ``_builtin_single_client_resolver``
        and ``OAuthService.validate_redirect_uri`` are stable public symbols
        of this module — the resolver seam consumes them directly.
        """
        assert BUILTIN_CLIENT_ID == "giljo-mcp-default"
        assert isinstance(ALLOWED_REDIRECT_URI_PATTERNS, list)
        assert any("localhost" in p for p in ALLOWED_REDIRECT_URI_PATTERNS)


class TestResolvedClientDataClass:
    """ResolvedClient is the seam contract — keep it minimal and frozen."""

    def test_required_fields(self):
        rc = ResolvedClient(
            client_id="cid",
            client_name="Test",
            redirect_uris=None,
            client_secret_hash=None,
        )
        assert rc.client_id == "cid"
        assert rc.redirect_uris is None
        assert rc.client_secret_hash is None

    def test_concrete_redirect_uris(self):
        rc = ResolvedClient(
            client_id="cid",
            client_name="Test",
            redirect_uris=["https://a.example/cb", "https://b.example/cb"],
            client_secret_hash="$2b$12$h",
        )
        assert rc.redirect_uris == ["https://a.example/cb", "https://b.example/cb"]
