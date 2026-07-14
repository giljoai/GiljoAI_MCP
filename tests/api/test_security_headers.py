# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for SecurityHeadersMiddleware.

These headers are emitted on every response by api/middleware/security.py but
were previously untested. A regression (dropping X-Frame-Options, breaking the
HTTPS-only HSTS guard, or weakening the CSP framing rules) would have shipped
silently. This locks the static headers, the HSTS scheme-gating, and the core
CSP directives in at the middleware layer.

Edition Scope: CE. The middleware itself is CE; SaaS only *adds* extra CSP
sources via register_csp_sources(), which we reset here so the assertions hold
regardless of test execution order.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.middleware.security import (
    SecurityHeadersMiddleware,
    clear_registered_csp_sources_for_tests,
)


@pytest.fixture
def app():
    """Minimal FastAPI app with only SecurityHeadersMiddleware mounted.

    Isolated from the full app/DB on purpose — header behavior is middleware-only.
    """
    clear_registered_csp_sources_for_tests()
    application = FastAPI()
    application.add_middleware(SecurityHeadersMiddleware)

    @application.get("/")
    async def root():
        return {"ok": True}

    yield application
    clear_registered_csp_sources_for_tests()


def test_static_security_headers_present(app):
    """The five static OWASP headers are emitted with their exact values."""
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    permissions_policy = response.headers["Permissions-Policy"]
    assert "geolocation=()" in permissions_policy
    assert "microphone=()" in permissions_policy
    assert "camera=()" in permissions_policy
    assert "payment=()" in permissions_policy


def test_hsts_absent_on_http(app):
    """HSTS is meaningless over HTTP and must NOT be sent for http requests."""
    response = TestClient(app, base_url="http://testserver").get("/")

    assert "Strict-Transport-Security" not in response.headers


def test_hsts_present_on_https(app):
    """HSTS is sent on HTTPS requests with the hardened directive set."""
    response = TestClient(app, base_url="https://testserver").get("/")

    hsts = response.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts
    assert "preload" in hsts


def test_csp_core_directives(app):
    """Core CSP anti-XSS / anti-clickjacking directives are present."""
    response = TestClient(app).get("/")

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp
