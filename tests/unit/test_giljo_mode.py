# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Tests for GILJO_MODE detection and conditional SaaS loading (SAAS-001).

Verifies that api/app.py correctly reads GILJO_MODE from the environment,
defaults to 'ce', and conditionally registers SaaS endpoints/middleware
only when mode is 'demo' or 'saas'.

These tests exercise the module-level GILJO_MODE constant and the
conditional import blocks in _register_routers() and _configure_middleware().
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reload_app_module(monkeypatch, mode_value: str | None = None):
    """Reload api.app with a controlled GILJO_MODE env var.

    Because GILJO_MODE is read at module level, we must reload the module
    for the env var change to take effect.  We also need to clear the
    cached module from sys.modules so importlib picks up the new value.

    Returns the freshly-loaded module object.
    """
    if mode_value is None:
        monkeypatch.delenv("GILJO_MODE", raising=False)
    else:
        monkeypatch.setenv("GILJO_MODE", mode_value)

    # Remove cached module so reload picks up the new env value
    sys.modules.pop("api.app", None)
    mod = importlib.import_module("api.app")
    return mod


# ---------------------------------------------------------------------------
# 1. Mode detection / parsing
# ---------------------------------------------------------------------------


class TestGiljoModeDetection:
    """Verify GILJO_MODE env var is correctly read and normalised."""

    def test_default_mode_is_ce(self, monkeypatch):
        """When GILJO_MODE is not set, the detected mode must be 'ce'."""
        mod = _reload_app_module(monkeypatch, mode_value=None)
        assert mod.GILJO_MODE == "ce"

    def test_demo_mode_detected(self, monkeypatch):
        """GILJO_MODE=demo is correctly parsed."""
        mod = _reload_app_module(monkeypatch, "demo")
        assert mod.GILJO_MODE == "demo"

    def test_saas_mode_detected(self, monkeypatch):
        """GILJO_MODE=saas is correctly parsed."""
        mod = _reload_app_module(monkeypatch, "saas")
        assert mod.GILJO_MODE == "saas"

    def test_case_insensitive_saas(self, monkeypatch):
        """GILJO_MODE=SAAS (uppercase) normalises to 'saas'."""
        mod = _reload_app_module(monkeypatch, "SAAS")
        assert mod.GILJO_MODE == "saas"

    def test_case_insensitive_demo(self, monkeypatch):
        """GILJO_MODE=Demo (mixed case) normalises to 'demo'."""
        mod = _reload_app_module(monkeypatch, "Demo")
        assert mod.GILJO_MODE == "demo"

    def test_ce_mode_explicit(self, monkeypatch):
        """GILJO_MODE=ce is correctly parsed when set explicitly."""
        mod = _reload_app_module(monkeypatch, "ce")
        assert mod.GILJO_MODE == "ce"


# ---------------------------------------------------------------------------
# 2. Conditional SaaS endpoint registration
# ---------------------------------------------------------------------------


class TestSaasEndpointRegistration:
    """Verify _register_routers() conditionally loads SaaS endpoints."""

    def test_ce_mode_skips_saas_endpoint_registration(self, monkeypatch):
        """In CE mode, SaaS endpoint registration must NOT be attempted."""
        monkeypatch.setenv("GILJO_MODE", "ce")
        app = MagicMock()

        with patch("api.app.GILJO_MODE", "ce"):
            from api.app import _register_routers

            with patch("api.saas_endpoints.register_saas_routes") as mock_register:
                _register_routers(app)
                mock_register.assert_not_called()

    def test_saas_mode_registers_endpoints_when_dir_exists(self, monkeypatch):
        """In saas mode with saas_endpoints dir present, registration is called."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch("api.app.Path") as mock_path_cls,
            patch("api.saas_endpoints.register_saas_routes") as mock_register,
        ):
            # Make the directory check return True
            mock_path_instance = MagicMock()
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_path_instance)
            mock_path_instance.is_dir.return_value = True

            # We need to also patch the Path usage inside _register_routers
            # The function uses Path(__file__).parent / "saas_endpoints"
            from api.app import _register_routers

            _register_routers(app)
            mock_register.assert_called_once_with(app)

    def test_demo_mode_registers_endpoints_when_dir_exists(self, monkeypatch):
        """In demo mode, SaaS endpoints should also be registered."""
        monkeypatch.setenv("GILJO_MODE", "demo")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "demo"),
            patch("api.saas_endpoints.register_saas_routes") as mock_register,
        ):
            from api.app import _register_routers

            _register_routers(app)
            # The real saas_endpoints dir exists on disk, so registration
            # should be called since we're in demo mode
            mock_register.assert_called_once_with(app)

    def test_graceful_fallback_when_saas_endpoints_import_fails(self, monkeypatch):
        """In saas mode, if the import fails, no crash occurs."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch(
                "api.saas_endpoints.register_saas_routes",
                side_effect=ImportError("no module"),
            ),
        ):
            from api.app import _register_routers

            # Must not raise -- graceful degradation
            _register_routers(app)


# ---------------------------------------------------------------------------
# 3. Conditional SaaS middleware registration
# ---------------------------------------------------------------------------


class TestSaasMiddlewareRegistration:
    """Verify _configure_middleware() conditionally loads SaaS middleware."""

    def test_ce_mode_skips_saas_middleware_registration(self, monkeypatch):
        """In CE mode, SaaS middleware registration must NOT be attempted."""
        monkeypatch.setenv("GILJO_MODE", "ce")
        app = MagicMock()

        with patch("api.app.GILJO_MODE", "ce"):
            from api.app import _configure_middleware

            with patch("api.saas_middleware.register_saas_middleware") as mock_register:
                _configure_middleware(app)
                mock_register.assert_not_called()

    def test_saas_mode_registers_middleware_when_dir_exists(self, monkeypatch):
        """In saas mode with saas_middleware dir present, registration is called."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch("api.saas_middleware.register_saas_middleware") as mock_register,
        ):
            from api.app import _configure_middleware

            _configure_middleware(app)
            mock_register.assert_called_once_with(app)

    def test_graceful_fallback_when_saas_middleware_import_fails(self, monkeypatch):
        """In saas mode, if the middleware import fails, no crash occurs."""
        monkeypatch.setenv("GILJO_MODE", "saas")
        app = MagicMock()

        with (
            patch("api.app.GILJO_MODE", "saas"),
            patch(
                "api.saas_middleware.register_saas_middleware",
                side_effect=ImportError("no module"),
            ),
        ):
            from api.app import _configure_middleware

            # Must not raise -- graceful degradation
            _configure_middleware(app)
