# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE+SaaS] Endpoint lives in CE; sentryDsn is non-null only in saas/demo.

"""Unit tests for the setup-status endpoint Sentry telemetry fields (INF-5063).

The frontend (commit 495433193) reads ``sentryDsn`` and ``environment`` from the
``/api/setup/status`` response in camelCase. These tests pin the response shape
so a future refactor can't silently drop or rename those keys.

Strategy: import the endpoint module, monkeypatch ``GILJO_MODE`` and the env vars,
and call the FastAPI handler with a stub async session that returns zero users.
No DB, no HTTP client.
"""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest


def _reload_with_mode(monkeypatch, mode: str):
    monkeypatch.setenv("GILJO_MODE", mode)
    import api.app_state as app_state_module

    importlib.reload(app_state_module)
    import api.endpoints.setup_security as setup_security_module

    importlib.reload(setup_security_module)
    return setup_security_module


def _stub_session(total_users: int = 0, admin_users: int = 0):
    session = MagicMock()
    results = [
        MagicMock(scalar=MagicMock(return_value=total_users)),
        MagicMock(scalar=MagicMock(return_value=admin_users)),
    ]
    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_saas_mode_exposes_sentry_dsn_and_environment(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN_FRONTEND", "https://example/0")
    module = _reload_with_mode(monkeypatch, "saas")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["sentryDsn"] == "https://example/0"
    assert response["environment"] == "saas"


@pytest.mark.asyncio
async def test_demo_mode_exposes_sentry_dsn_and_environment(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN_FRONTEND", "https://demo/1")
    module = _reload_with_mode(monkeypatch, "demo")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["sentryDsn"] == "https://demo/1"
    assert response["environment"] == "demo"


@pytest.mark.asyncio
async def test_ce_mode_returns_null_sentry_dsn(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN_FRONTEND", "https://example/0")
    module = _reload_with_mode(monkeypatch, "ce")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["sentryDsn"] is None
    assert response["environment"] == "ce"


@pytest.mark.asyncio
async def test_saas_mode_without_dsn_returns_null(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN_FRONTEND", raising=False)
    module = _reload_with_mode(monkeypatch, "saas")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["sentryDsn"] is None
    assert response["environment"] == "saas"


@pytest.mark.asyncio
async def test_unset_mode_defaults_to_ce_environment(monkeypatch):
    monkeypatch.delenv("GILJO_MODE", raising=False)
    monkeypatch.setenv("SENTRY_DSN_FRONTEND", "https://example/0")
    import api.app_state as app_state_module

    importlib.reload(app_state_module)
    import api.endpoints.setup_security as setup_security_module

    importlib.reload(setup_security_module)

    response = await setup_security_module.get_setup_security_status(db=_stub_session())

    assert response["sentryDsn"] is None
    assert response["environment"] == "ce"


# ---------------------------------------------------------------------------
# API-0016: paddle_client_token + paddle_environment exposure on /api/setup/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ce_mode_returns_null_paddle_fields(monkeypatch):
    """CE must never expose Paddle config — both fields null regardless of env."""
    monkeypatch.setenv("PADDLE_CLIENT_TOKEN", "ctok_should_not_leak")
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "production")
    module = _reload_with_mode(monkeypatch, "ce")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["paddle_client_token"] is None
    assert response["paddle_environment"] is None


@pytest.mark.asyncio
async def test_demo_mode_returns_null_paddle_fields(monkeypatch):
    """Demo mode is hosted by GiljoAI but does NOT run Paddle — fields null."""
    monkeypatch.setenv("PADDLE_CLIENT_TOKEN", "ctok_demo_leak")
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "sandbox")
    module = _reload_with_mode(monkeypatch, "demo")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["paddle_client_token"] is None
    assert response["paddle_environment"] is None


@pytest.mark.asyncio
async def test_saas_mode_exposes_paddle_fields(monkeypatch):
    """SaaS mode exposes the public client token + environment for the frontend overlay."""
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_api")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "whsec_x")
    monkeypatch.setenv("PADDLE_CLIENT_TOKEN", "ctok_saas_real")
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "production")
    module = _reload_with_mode(monkeypatch, "saas")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["paddle_client_token"] == "ctok_saas_real"
    assert response["paddle_environment"] == "production"


@pytest.mark.asyncio
async def test_saas_mode_paddle_unconfigured_returns_none_token(monkeypatch):
    """SaaS without PADDLE_CLIENT_TOKEN configured: token null, environment still echoed."""
    monkeypatch.delenv("PADDLE_API_KEY", raising=False)
    monkeypatch.delenv("PADDLE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("PADDLE_CLIENT_TOKEN", raising=False)
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "sandbox")
    module = _reload_with_mode(monkeypatch, "saas")

    response = await module.get_setup_security_status(db=_stub_session())

    assert response["paddle_client_token"] is None
    assert response["paddle_environment"] == "sandbox"
