# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for _build_cookie_params helper in auth endpoints.

Tests the shared cookie parameter builder that consolidates domain
validation logic previously duplicated in login, logout, and
create-first-admin endpoints.

Covers:
- IP address detection (domain omitted for origin-matching per RFC 6265)
- Domain whitelist enforcement (cookie_domain_whitelist config key)
- Unknown host fail-secure behavior (domain=None)
- Missing/empty request scenarios
- Returned dict structure and defaults
"""

from unittest.mock import MagicMock, patch

from api.endpoints.auth import _build_cookie_params


class TestBuildCookieParams:
    """Test suite for _build_cookie_params helper."""

    def _make_request(self, host_header: str = "192.0.2.10:7272") -> MagicMock:
        """Create a mock Request with the given Host header.

        Note: We do NOT use spec=Request because MagicMock(spec=Request)
        evaluates to False in boolean context, breaking the
        ``if request and request.client:`` guard in _build_cookie_params.
        """
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = host_header.split(":", maxsplit=1)[0]
        request.headers = {"host": host_header}
        # Deterministic default scheme: plain http (CE-localhost shape). Tests
        # exercising the SEC-3001a Wave 2 HTTPS->Secure upgrade set this to
        # "https" explicitly.
        request.url.scheme = "http"
        return request

    # --- Structure tests ---

    @patch("api.endpoints.auth.session.get_config")
    def test_returns_dict_with_required_keys(self, mock_config):
        """Returned dict must contain all keys needed by set_cookie."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        expected_keys = {"key", "httponly", "secure", "samesite", "path", "domain", "max_age"}
        assert set(result.keys()) == expected_keys

    @patch("api.endpoints.auth.session.get_config")
    def test_default_values(self, mock_config):
        """Verify default cookie settings."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["key"] == "access_token"
        assert result["httponly"] is True
        assert result["samesite"] == "lax"
        assert result["path"] == "/"
        assert result["max_age"] == 86400

    # --- IP address tests ---

    @patch("api.endpoints.auth.session.get_config")
    def test_ip_address_omits_cookie_domain(self, mock_config):
        """IP addresses should omit cookie domain (browser uses origin-matching).

        Per RFC 6265 Section 5.2.3, the domain attribute is designed for DNS
        names. Setting an explicit domain on an IP address is unreliable across
        browsers. Omitting it lets the browser use exact origin matching.
        """
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("192.0.2.10:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_localhost_ip_omits_cookie_domain(self, mock_config):
        """Localhost IP (127.0.0.1) should omit cookie domain (origin-matching)."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_ip_without_port_omits_cookie_domain(self, mock_config):
        """IP address without port should also omit cookie domain."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("192.0.2.100")
        # Adjust headers since no port present
        request.headers = {"host": "192.0.2.100"}

        result = _build_cookie_params(request)

        assert result["domain"] is None

    # --- Domain whitelist tests ---

    @patch("api.endpoints.auth.session.get_config")
    def test_whitelisted_domain_sets_cookie_domain(self, mock_config):
        """Domain in cookie_domain_whitelist should be used."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": True},
                "cookie_domain_whitelist": ["myapp.example.com"],
            }
        }
        request = self._make_request("myapp.example.com:7272")

        result = _build_cookie_params(request)

        assert result["domain"] == "myapp.example.com"

    @patch("api.endpoints.auth.session.get_config")
    def test_non_whitelisted_domain_returns_none(self, mock_config):
        """Domain NOT in whitelist should result in domain=None (fail secure)."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domain_whitelist": ["trusted.example.com"],
            }
        }
        request = self._make_request("evil.com:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_empty_whitelist_domain_returns_none(self, mock_config):
        """With empty whitelist, non-IP domains should get domain=None."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domain_whitelist": [],
            }
        }
        request = self._make_request("somehost.local:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_no_whitelist_key_defaults_empty(self, mock_config):
        """Missing cookie_domain_whitelist key should default to empty list."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("example.com:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    # --- Secure flag tests ---

    @patch("api.endpoints.auth.session.get_config")
    def test_secure_flag_from_config(self, mock_config):
        """Secure flag should come from security.cookies.secure config.

        INF-6236: config is the fallback only when no effective request scheme
        overrides it, so this test pins the scheme to empty to exercise the
        config-plumbing path directly (http/https override paths are covered
        separately below).
        """
        mock_config.return_value = {"security": {"cookies": {"secure": True}}}
        request = self._make_request("127.0.0.1:7272")
        request.url.scheme = ""  # no scheme override -> config drives the flag

        result = _build_cookie_params(request)

        assert result["secure"] is True

    @patch("api.endpoints.auth.session.get_config")
    def test_secure_flag_defaults_false(self, mock_config):
        """Secure flag should default to False if not configured."""
        mock_config.return_value = {}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["secure"] is False

    # --- SEC-3001a Wave 2 (item 3): HTTPS-conditional Secure flag ---

    @patch("api.endpoints.auth.session.get_config")
    def test_https_scheme_upgrades_secure(self, mock_config):
        """Over HTTPS the Secure flag is forced on even when config is False.

        SaaS prod / CE-behind-TLS see scheme=https (uvicorn resolves it from
        X-Forwarded-Proto). The keystone auth cookie must never be sent in
        cleartext there, regardless of the config default.
        """
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("app.example.com:443")
        request.url.scheme = "https"

        result = _build_cookie_params(request)

        assert result["secure"] is True

    @patch("api.endpoints.auth.session.get_config")
    def test_http_scheme_keeps_secure_false(self, mock_config):
        """Over plain http (CE-localhost) Secure stays False so login works.

        A Secure cookie is silently dropped by the browser over http, which
        would break CE-localhost login. This is the load-bearing half of the
        conditional -- it must NOT regress.
        """
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")  # helper defaults scheme=http

        result = _build_cookie_params(request)

        assert result["secure"] is False

    @patch("api.endpoints.auth.session.get_config")
    def test_http_scheme_downgrades_stale_config_secure_true(self, mock_config):
        """INF-6236: over http the scheme wins, even if config secure=True.

        This is the load-bearing footgun the fix closes: a leftover
        security.cookies.secure=True (e.g. from a prior HTTPS install) over a
        now-plain-http LAN deployment would mark the keystone access_token cookie
        Secure -> the browser silently DROPS it over http -> login breaks and the
        WebSocket handshake 1008-rejects. The effective scheme is authoritative,
        so http forces Secure=False regardless of the stale config.
        """
        mock_config.return_value = {"security": {"cookies": {"secure": True}}}
        request = self._make_request("127.0.0.1:7272")  # scheme=http

        result = _build_cookie_params(request)

        assert result["secure"] is False

    @patch("api.endpoints.auth.session.get_config")
    def test_config_secure_true_used_when_no_request_scheme(self, mock_config):
        """With no request to derive a scheme from, config secure=True applies.

        config.security.cookies.secure only takes effect as the fallback when
        there is no effective scheme (no request object).
        """
        mock_config.return_value = {"security": {"cookies": {"secure": True}}}
        request = MagicMock()
        request.client = None
        # Force the scheme guards to skip: no usable url scheme.
        request.url.scheme = ""

        result = _build_cookie_params(request)

        assert result["secure"] is True

    # --- Edge case tests ---

    @patch("api.endpoints.auth.session.get_config")
    def test_no_client_returns_domain_none(self, mock_config):
        """Request with no client attribute should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = None

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_empty_host_header_returns_domain_none(self, mock_config):
        """Empty host header should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = MagicMock()
        request.headers = {"host": ""}

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_missing_host_header_returns_domain_none(self, mock_config):
        """Missing host header should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = MagicMock()
        request.headers = {}

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.session.get_config")
    def test_host_case_insensitive(self, mock_config):
        """Host header matching should be case-insensitive."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domain_whitelist": ["myapp.example.com"],
            }
        }
        request = self._make_request("MyApp.Example.COM:7272")

        result = _build_cookie_params(request)

        assert result["domain"] == "myapp.example.com"

    # --- Config key alignment test ---

    @patch("api.endpoints.auth.session.get_config")
    def test_uses_cookie_domain_whitelist_not_cookie_domains(self, mock_config):
        """Must read security.cookie_domain_whitelist (not cookie_domains).

        This validates the config key alignment fix between auth.py
        and user_settings.py (which also uses cookie_domain_whitelist).
        """
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                # Old key (should be ignored)
                "cookie_domains": ["old-key-domain.com"],
                # New key (should be used)
                "cookie_domain_whitelist": ["correct-domain.com"],
            }
        }
        request = self._make_request("correct-domain.com:7272")

        result = _build_cookie_params(request)

        # Should match the new key, not the old one
        assert result["domain"] == "correct-domain.com"

    @patch("api.endpoints.auth.session.get_config")
    def test_old_cookie_domains_key_ignored(self, mock_config):
        """Domains only in old cookie_domains key should NOT be whitelisted."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domains": ["only-in-old-key.com"],
                # cookie_domain_whitelist not present
            }
        }
        request = self._make_request("only-in-old-key.com:7272")

        result = _build_cookie_params(request)

        # Should NOT match because cookie_domain_whitelist is empty
        assert result["domain"] is None

    # --- BE-9152: DB-store whitelist param (union with file config) ---

    @patch("api.endpoints.auth.session.get_config")
    def test_db_domain_honored_when_file_config_empty(self, mock_config):
        """A domain from the DB settings store is honored even when config.yaml is empty.

        This is the core BE-9152 fix: the admin Settings panel writes the DB store,
        and enforcement now reads it via the db_cookie_domains param.
        """
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("db-only.example.com:7272")

        result = _build_cookie_params(request, db_cookie_domains=["db-only.example.com"])

        assert result["domain"] == "db-only.example.com"

    @patch("api.endpoints.auth.session.get_config")
    def test_file_config_still_honored_when_db_empty(self, mock_config):
        """Legacy tolerance: a domain configured only in config.yaml stays honored
        when the DB store is empty (installs that never touched the panel)."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domain_whitelist": ["legacy-file.example.com"],
            }
        }
        request = self._make_request("legacy-file.example.com:7272")

        result = _build_cookie_params(request, db_cookie_domains=[])

        assert result["domain"] == "legacy-file.example.com"

    @patch("api.endpoints.auth.session.get_config")
    def test_file_and_db_domains_are_unioned(self, mock_config):
        """Both the file-config domain AND the DB-store domain are honored (union)."""
        mock_config.return_value = {
            "security": {
                "cookies": {"secure": False},
                "cookie_domain_whitelist": ["file.example.com"],
            }
        }

        file_host = self._make_request("file.example.com:7272")
        db_host = self._make_request("db.example.com:7272")

        assert _build_cookie_params(file_host, db_cookie_domains=["db.example.com"])["domain"] == "file.example.com"
        assert _build_cookie_params(db_host, db_cookie_domains=["db.example.com"])["domain"] == "db.example.com"

    @patch("api.endpoints.auth.session.get_config")
    def test_db_domain_not_matching_host_returns_none(self, mock_config):
        """A DB whitelist that does not include the request host still fails secure."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("evil.example.com:7272")

        result = _build_cookie_params(request, db_cookie_domains=["trusted.example.com"])

        assert result["domain"] is None
