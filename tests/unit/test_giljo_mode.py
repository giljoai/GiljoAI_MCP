# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Tests for GILJO_MODE detection and env var parsing (SAAS-001).

Verifies that api/app.py correctly reads GILJO_MODE from the environment,
defaults to 'ce', and normalises case.

SaaS-specific conditional loading tests (endpoint/middleware registration)
are in tests/saas/test_giljo_mode_saas_loading.py — they reference
api.saas_endpoints and api.saas_middleware which are stripped from CE exports.
"""

from __future__ import annotations

import importlib
import sys


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
# Mode detection / parsing
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
