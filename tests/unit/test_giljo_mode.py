# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for GILJO_MODE detection and env var parsing.

Verifies that api/app_state.py correctly reads GILJO_MODE from the environment,
defaults to 'ce', and normalises case.

SaaS-specific conditional loading tests (endpoint/middleware registration)
are in tests/saas/test_giljo_mode_saas_loading.py — they reference
api.saas_endpoints and api.saas_middleware which are stripped from CE exports.
"""

from __future__ import annotations

import importlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reload_app_state_module(monkeypatch, mode_value: str | None = None):
    """Reload api.app_state with a controlled GILJO_MODE env var.

    ``GILJO_MODE`` is read at module level, so the module must be reloaded for
    an env-var change to take effect. Use ``importlib.reload`` (NOT
    ``sys.modules.pop`` + re-import): reload re-executes the module body — which
    re-reads ``GILJO_MODE`` — in the EXISTING module ``__dict__``, so the
    ``state`` singleton is preserved (api/app_state.py reuses any instance
    already there). A pop+re-import builds a fresh ``__dict__`` and a NEW
    ``APIState``, forking it away from every module that did
    ``from api.app_state import state`` and flaking a later /health test on the
    same xdist worker (TSK-9002).

    Returns the reloaded module object.
    """
    if mode_value is None:
        monkeypatch.delenv("GILJO_MODE", raising=False)
    else:
        monkeypatch.setenv("GILJO_MODE", mode_value)

    import api.app_state as app_state_module

    importlib.reload(app_state_module)
    return app_state_module


# ---------------------------------------------------------------------------
# Mode detection / parsing
# ---------------------------------------------------------------------------


class TestGiljoModeDetection:
    """Verify GILJO_MODE env var is correctly read and normalised."""

    def test_default_mode_is_ce(self, monkeypatch):
        """When GILJO_MODE is not set, the detected mode must be 'ce'."""
        mod = _reload_app_state_module(monkeypatch, mode_value=None)
        assert mod.GILJO_MODE == "ce"

    def test_saas_mode_detected(self, monkeypatch):
        """GILJO_MODE=saas is correctly parsed."""
        mod = _reload_app_state_module(monkeypatch, "saas")
        assert mod.GILJO_MODE == "saas"

    def test_case_insensitive_saas(self, monkeypatch):
        """GILJO_MODE=SAAS (uppercase) normalises to 'saas'."""
        mod = _reload_app_state_module(monkeypatch, "SAAS")
        assert mod.GILJO_MODE == "saas"

    def test_legacy_demo_no_longer_special_cased(self, monkeypatch):
        """The legacy demo edition was fully removed (BE-6015): GILJO_MODE=demo
        is no longer coerced to 'saas'. The value is read literally like any
        other unrecognised mode (it is not 'ce' and not 'saas')."""
        mod = _reload_app_state_module(monkeypatch, "demo")
        assert mod.GILJO_MODE == "demo"
        assert mod.GILJO_MODE not in ("ce", "saas")

    def test_ce_mode_explicit(self, monkeypatch):
        """GILJO_MODE=ce is correctly parsed when set explicitly."""
        mod = _reload_app_state_module(monkeypatch, "ce")
        assert mod.GILJO_MODE == "ce"
