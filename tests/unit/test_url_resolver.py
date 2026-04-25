# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for giljo_mcp.http.url_resolver.get_public_base_url.

INF-5012 Phase 1: public-URL resolution must come from request.base_url
(honoring X-Forwarded-* via Uvicorn proxy_headers) and never from config.
One helper, no edition branches.
"""

from unittest.mock import MagicMock

from giljo_mcp.http.url_resolver import get_public_base_url


def _make_request(base_url: str) -> MagicMock:
    """Build a minimal Request double whose base_url stringifies as given."""
    request = MagicMock()
    request.base_url = MagicMock()
    request.base_url.__str__ = lambda _self: base_url
    return request


class TestGetPublicBaseUrl:
    """get_public_base_url returns request.base_url stripped of trailing slash."""

    def test_localhost_http(self):
        request = _make_request("http://localhost:7272/")
        assert get_public_base_url(request) == "http://localhost:7272"

    def test_lan_https_with_port(self):
        request = _make_request("https://192.168.1.42:7272/")
        assert get_public_base_url(request) == "https://192.168.1.42:7272"

    def test_cloudflare_tunnel_no_port(self):
        """Demo Cloudflare Tunnel: public URL has no :7272 suffix."""
        request = _make_request("https://demo.giljo.ai/")
        assert get_public_base_url(request) == "https://demo.giljo.ai"

    def test_customer_nginx_proxy(self):
        """CE customer behind nginx: honors X-Forwarded-Host / X-Forwarded-Proto."""
        request = _make_request("https://mcp.acme.corp/")
        assert get_public_base_url(request) == "https://mcp.acme.corp"

    def test_saas_production(self):
        request = _make_request("https://app.giljo.ai/")
        assert get_public_base_url(request) == "https://app.giljo.ai"

    def test_no_trailing_slash_input(self):
        """Even if FastAPI ever yields base_url without a trailing slash, result is stable."""
        request = _make_request("http://localhost:7272")
        assert get_public_base_url(request) == "http://localhost:7272"

    def test_returns_str(self):
        request = _make_request("http://localhost:7272/")
        assert isinstance(get_public_base_url(request), str)
