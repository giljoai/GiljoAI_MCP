# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for GET /api/v1/config sensitive-data masking.

Replaces the old tests/manual/test_config_endpoint_live.py, which was a
print-only script that required a live server on localhost:7272 and asserted
nothing (so it never ran under pytest). The security-relevant behavior — the
endpoint MUST mask the database password and string API keys before returning
config.yaml — had zero coverage. This locks it in with a TestClient against the
config router (no live server, no DB), monkeypatching read_config to control input.

Edition Scope: Both (configuration endpoint is core CE code, served in both editions).
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.endpoints import configuration
from giljo_mcp.auth.dependencies import get_current_active_user


@pytest.fixture
def client():
    """Minimal app mounting only the configuration router, with auth stubbed.

    The handler ignores the authenticated user, so the override just satisfies
    the dependency without needing a real JWT/cookie.
    """
    app = FastAPI()
    app.include_router(configuration.router, prefix="/api/v1/config")
    app.dependency_overrides[get_current_active_user] = object
    yield TestClient(app)
    app.dependency_overrides.clear()


def _patch_config(monkeypatch, config):
    """Force read_config() (a call-time import inside the handler) to return `config`."""
    monkeypatch.setattr("giljo_mcp._config_io.read_config", lambda: config)


def test_database_password_is_masked(client, monkeypatch):
    """A non-empty DB password must come back as '****', other fields untouched."""
    _patch_config(monkeypatch, {"database": {"host": "db.internal", "password": "supersecret"}})

    response = client.get("/api/v1/config/")

    assert response.status_code == 200
    body = response.json()
    assert body["database"]["password"] == "****"
    assert body["database"]["host"] == "db.internal"  # non-sensitive passthrough


def test_empty_database_password_becomes_empty_string(client, monkeypatch):
    """A falsy DB password is normalized to '' (never echoed)."""
    _patch_config(monkeypatch, {"database": {"password": ""}})

    response = client.get("/api/v1/config/")

    assert response.status_code == 200
    assert response.json()["database"]["password"] == ""


def test_api_keys_string_values_masked_non_strings_untouched(client, monkeypatch):
    """String API-key values are masked to '****'; non-string values pass through."""
    _patch_config(monkeypatch, {"security": {"api_keys": {"admin": "secretkey", "rotation_count": 5}}})

    response = client.get("/api/v1/config/")

    api_keys = response.json()["security"]["api_keys"]
    assert api_keys["admin"] == "****"
    assert api_keys["rotation_count"] == 5


def test_empty_config_returns_500(client, monkeypatch):
    """An empty/missing config.yaml surfaces as a 500, not an empty 200."""
    _patch_config(monkeypatch, {})

    response = client.get("/api/v1/config/")

    assert response.status_code == 500


def test_non_sensitive_sections_pass_through(client, monkeypatch):
    """Non-sensitive sections are returned verbatim."""
    _patch_config(monkeypatch, {"installation": {"mode": "localhost"}, "database": {"password": "x"}})

    body = client.get("/api/v1/config/").json()

    assert body["installation"]["mode"] == "localhost"
