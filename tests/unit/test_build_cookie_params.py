"""
Unit tests for _build_cookie_params helper in auth endpoints.

Tests the shared cookie parameter builder that consolidates domain
validation logic previously duplicated in login, logout, and
create-first-admin endpoints.

Covers:
- IP address detection (auto-allowed, no whitelist needed)
- Domain whitelist enforcement (cookie_domain_whitelist config key)
- Unknown host fail-secure behavior (domain=None)
- Missing/empty request scenarios
- Returned dict structure and defaults
"""

from unittest.mock import MagicMock, patch

from api.endpoints.auth import _build_cookie_params


class TestBuildCookieParams:
    """Test suite for _build_cookie_params helper."""

    def _make_request(self, host_header: str = "10.1.0.164:7272") -> MagicMock:
        """Create a mock Request with the given Host header.

        Note: We do NOT use spec=Request because MagicMock(spec=Request)
        evaluates to False in boolean context, breaking the
        ``if request and request.client:`` guard in _build_cookie_params.
        """
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = host_header.split(":", maxsplit=1)[0]
        request.headers = {"host": host_header}
        return request

    # --- Structure tests ---

    @patch("api.endpoints.auth.get_config")
    def test_returns_dict_with_required_keys(self, mock_config):
        """Returned dict must contain all keys needed by set_cookie."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        expected_keys = {"key", "httponly", "secure", "samesite", "path", "domain", "max_age"}
        assert set(result.keys()) == expected_keys

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
    def test_ip_address_sets_cookie_domain(self, mock_config):
        """IP addresses should auto-set cookie domain (no whitelist needed)."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("10.1.0.164:7272")

        result = _build_cookie_params(request)

        assert result["domain"] == "10.1.0.164"

    @patch("api.endpoints.auth.get_config")
    def test_localhost_ip_sets_cookie_domain(self, mock_config):
        """Localhost IP (127.0.0.1) should set cookie domain for cross-port sharing."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["domain"] == "127.0.0.1"

    @patch("api.endpoints.auth.get_config")
    def test_ip_without_port_sets_cookie_domain(self, mock_config):
        """IP address without port should still work."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("192.168.1.100")
        # Adjust headers since no port present
        request.headers = {"host": "192.168.1.100"}

        result = _build_cookie_params(request)

        assert result["domain"] == "192.168.1.100"

    # --- Domain whitelist tests ---

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
    def test_no_whitelist_key_defaults_empty(self, mock_config):
        """Missing cookie_domain_whitelist key should default to empty list."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = self._make_request("example.com:7272")

        result = _build_cookie_params(request)

        assert result["domain"] is None

    # --- Secure flag tests ---

    @patch("api.endpoints.auth.get_config")
    def test_secure_flag_from_config(self, mock_config):
        """Secure flag should come from security.cookies.secure config."""
        mock_config.return_value = {"security": {"cookies": {"secure": True}}}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["secure"] is True

    @patch("api.endpoints.auth.get_config")
    def test_secure_flag_defaults_false(self, mock_config):
        """Secure flag should default to False if not configured."""
        mock_config.return_value = {}
        request = self._make_request("127.0.0.1:7272")

        result = _build_cookie_params(request)

        assert result["secure"] is False

    # --- Edge case tests ---

    @patch("api.endpoints.auth.get_config")
    def test_no_client_returns_domain_none(self, mock_config):
        """Request with no client attribute should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = None

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.get_config")
    def test_empty_host_header_returns_domain_none(self, mock_config):
        """Empty host header should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = MagicMock()
        request.headers = {"host": ""}

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.get_config")
    def test_missing_host_header_returns_domain_none(self, mock_config):
        """Missing host header should return domain=None."""
        mock_config.return_value = {"security": {"cookies": {"secure": False}}}
        request = MagicMock()
        request.client = MagicMock()
        request.headers = {}

        result = _build_cookie_params(request)

        assert result["domain"] is None

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
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

    @patch("api.endpoints.auth.get_config")
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
