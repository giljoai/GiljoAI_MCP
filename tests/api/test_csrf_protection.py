# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration tests for CSRF protection middleware.

Validates the double-submit cookie pattern implementation:
- State-changing methods (POST, PUT, PATCH, DELETE) require matching
  csrf_token cookie and X-CSRF-Token header
- Safe methods (GET, HEAD, OPTIONS) pass without CSRF validation
- Exempt paths/prefixes bypass CSRF entirely
- API key-authenticated requests skip CSRF
- CSRF cookie is set on first visit and is readable by JavaScript

Middleware under test: api.middleware.csrf.CSRFProtectionMiddleware
Configuration source: api.app.create_app()

Created for Handover 0765f - CSRF protection hardening.
"""

import secrets

import pytest


# ---------------------------------------------------------------------------
# Non-exempt endpoint used across tests.
# /api/v1/products/ is behind auth and CSRF, giving us a reliable target.
# ---------------------------------------------------------------------------
NON_EXEMPT_ENDPOINT = "/api/v1/products/"


# ===========================================================================
# Helpers
# ===========================================================================


def _auth_only_headers(auth_headers: dict) -> dict:
    """
    Strip CSRF artifacts from auth_headers, keeping only the access_token cookie.

    The auth_headers fixture includes both the csrf_token cookie and the
    X-CSRF-Token header.  For negative CSRF tests we need authentication
    without any CSRF material so the middleware rejects the request for
    the right reason (missing CSRF) rather than for missing auth.
    """
    cookie = auth_headers["Cookie"]
    # Keep only the access_token portion of the Cookie header
    parts = [p.strip() for p in cookie.split(";")]
    access_only = "; ".join(p for p in parts if p.startswith("access_token="))
    return {"Cookie": access_only}


# ===========================================================================
# 1-4. State-changing methods blocked without CSRF token
# ===========================================================================


class TestCSRFBlocksWithoutToken:
    """Verify that POST, PUT, PATCH, and DELETE are rejected without CSRF."""

    @pytest.mark.asyncio
    async def test_csrf_blocks_post_without_token(self, api_client, auth_headers):
        """POST to a non-exempt endpoint without CSRF token returns 403."""
        headers = _auth_only_headers(auth_headers)
        response = await api_client.post(NON_EXEMPT_ENDPOINT, headers=headers, json={})

        assert response.status_code == 403
        assert "CSRF validation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_csrf_blocks_put_without_token(self, api_client, auth_headers):
        """PUT to a non-exempt endpoint without CSRF token returns 403."""
        headers = _auth_only_headers(auth_headers)
        response = await api_client.put(f"{NON_EXEMPT_ENDPOINT}fake-id", headers=headers, json={})

        assert response.status_code == 403
        assert "CSRF validation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_csrf_blocks_delete_without_token(self, api_client, auth_headers):
        """DELETE to a non-exempt endpoint without CSRF token returns 403."""
        headers = _auth_only_headers(auth_headers)
        response = await api_client.delete(f"{NON_EXEMPT_ENDPOINT}fake-id", headers=headers)

        assert response.status_code == 403
        assert "CSRF validation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_csrf_blocks_patch_without_token(self, api_client, auth_headers):
        """PATCH to a non-exempt endpoint without CSRF token returns 403."""
        headers = _auth_only_headers(auth_headers)
        response = await api_client.patch(f"{NON_EXEMPT_ENDPOINT}fake-id", headers=headers, json={})

        assert response.status_code == 403
        assert "CSRF validation failed" in response.json()["detail"]


# ===========================================================================
# 5. Valid CSRF token allows request through
# ===========================================================================


class TestCSRFAllowsValidToken:
    """Verify that a matching cookie + header pair passes CSRF validation."""

    @pytest.mark.asyncio
    async def test_csrf_allows_post_with_valid_token(self, api_client, auth_headers):
        """POST with matching csrf_token cookie and X-CSRF-Token header is not blocked by CSRF.

        The response may be 404, 422, etc. depending on the endpoint's own
        validation -- the key assertion is that it is NOT 403 (CSRF).
        """
        response = await api_client.post(NON_EXEMPT_ENDPOINT, headers=auth_headers, json={})

        # Must not be blocked by CSRF middleware
        assert response.status_code != 403


# ===========================================================================
# 6. Mismatched token rejected
# ===========================================================================


class TestCSRFBlocksMismatchedToken:
    """Verify that a cookie/header mismatch is caught."""

    @pytest.mark.asyncio
    async def test_csrf_blocks_mismatched_token(self, api_client, auth_headers):
        """POST with different csrf_token in cookie vs header returns 403."""
        # Build headers with the original cookie but a DIFFERENT header token
        mismatched_header_token = secrets.token_urlsafe(32)
        headers = {
            "Cookie": auth_headers["Cookie"],  # contains original csrf_token cookie
            "X-CSRF-Token": mismatched_header_token,
        }
        response = await api_client.post(NON_EXEMPT_ENDPOINT, headers=headers, json={})

        assert response.status_code == 403
        assert "CSRF validation failed" in response.json()["detail"]


# ===========================================================================
# 7. Safe methods pass without CSRF
# ===========================================================================


class TestCSRFAllowsSafeMethods:
    """Verify GET, HEAD, OPTIONS are not subject to CSRF validation."""

    @pytest.mark.asyncio
    async def test_csrf_allows_get_without_token(self, api_client, auth_headers):
        """GET requests pass CSRF validation without any CSRF token.

        Uses auth-only headers (no CSRF cookie or header) to prove the
        middleware does not enforce CSRF on safe methods.
        """
        headers = _auth_only_headers(auth_headers)
        response = await api_client.get(NON_EXEMPT_ENDPOINT, headers=headers)

        # GET should never be blocked by CSRF -- any non-403 status is fine
        assert response.status_code != 403


# ===========================================================================
# 8-9. Exempt paths and prefixes
# ===========================================================================


class TestCSRFExemptPaths:
    """Verify that configured exempt paths and prefixes bypass CSRF."""

    @pytest.mark.asyncio
    async def test_csrf_exempt_login_endpoint(self, api_client):
        """POST to /api/auth/login does not require CSRF token.

        The login endpoint is under the /api/auth/ exempt prefix, so even
        without any CSRF material the response must not be 403-CSRF.
        """
        response = await api_client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "wrong"},
        )

        # Should not be a CSRF 403 -- it may be 401/422 from auth logic
        assert response.status_code != 403 or (
            response.status_code == 403 and "CSRF" not in response.json().get("detail", "")
        )

    @pytest.mark.asyncio
    async def test_csrf_exempt_setup_endpoints(self, api_client):
        """POST to /api/setup/* does not require CSRF token.

        The /api/setup/ prefix is exempt from CSRF validation because the
        setup wizard runs before authentication is configured.
        """
        response = await api_client.post(
            "/api/setup/database/test-connection",
            json={"host": "localhost", "port": 5432},
        )

        # Should not be a CSRF 403
        assert response.status_code != 403 or (
            response.status_code == 403 and "CSRF" not in response.json().get("detail", "")
        )


# ===========================================================================
# 10. API key header skips CSRF
# ===========================================================================


class TestCSRFSkipsAPIKey:
    """Verify that requests with X-API-Key header bypass CSRF."""

    @pytest.mark.asyncio
    async def test_csrf_exempt_api_key_requests(self, api_client):
        """POST with X-API-Key header skips CSRF validation entirely.

        When a request carries the X-API-Key header, the middleware assumes
        API-key-based auth (not cookie-based) and does not enforce CSRF.
        The request may fail for other reasons (invalid key, 401, etc.)
        but it must NOT fail with a CSRF 403.
        """
        headers = {"X-API-Key": "some-api-key-value"}
        response = await api_client.post(NON_EXEMPT_ENDPOINT, headers=headers, json={})

        # Must not be a CSRF rejection
        assert response.status_code != 403 or (
            response.status_code == 403 and "CSRF" not in response.json().get("detail", "")
        )


# ===========================================================================
# 11-12. Cookie behavior
# ===========================================================================


class TestCSRFCookieBehavior:
    """Verify CSRF cookie generation and attributes."""

    @pytest.mark.asyncio
    async def test_csrf_cookie_set_on_first_visit(self, api_client, auth_headers):
        """GET to a non-exempt authenticated path sets csrf_token cookie when absent.

        When the request does NOT already carry a csrf_token cookie, the
        middleware generates one and includes it in the Set-Cookie response
        header so the frontend can read it for subsequent requests.
        """
        # Use auth-only headers (no csrf_token cookie) to trigger cookie generation
        headers = _auth_only_headers(auth_headers)
        response = await api_client.get(NON_EXEMPT_ENDPOINT, headers=headers)

        # The middleware should set the csrf_token cookie
        set_cookie_headers = response.headers.get_list("set-cookie")
        csrf_cookies = [h for h in set_cookie_headers if "csrf_token=" in h]

        assert len(csrf_cookies) > 0, (
            f"Expected Set-Cookie header with csrf_token but none found. All Set-Cookie headers: {set_cookie_headers}"
        )

    @pytest.mark.asyncio
    async def test_csrf_cookie_not_httponly(self, api_client, auth_headers):
        """The csrf_token cookie must NOT be httponly so JavaScript can read it.

        The double-submit cookie pattern requires the frontend to read the
        cookie value and echo it back in the X-CSRF-Token header. If the
        cookie were httponly, JavaScript could not access it and the pattern
        would break.
        """
        headers = _auth_only_headers(auth_headers)
        response = await api_client.get(NON_EXEMPT_ENDPOINT, headers=headers)

        set_cookie_headers = response.headers.get_list("set-cookie")
        csrf_cookies = [h for h in set_cookie_headers if "csrf_token=" in h]

        assert len(csrf_cookies) > 0, "No csrf_token Set-Cookie header found"

        # The cookie must NOT contain the httponly flag
        for cookie_header in csrf_cookies:
            assert "httponly" not in cookie_header.lower(), (
                f"csrf_token cookie must NOT be httponly (JS needs to read it). Got: {cookie_header}"
            )
