# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [SaaS] SaaS Edition.

"""INF-5070 Bug 1: demo/startup_demo.py fail-fast preflight for missing
SaaS/Demo Python dependencies (sentry-sdk[fastapi]).

Background: demo.giljo.ai crashed on cold restart after the 2026-05-08 Sentry
integration shipped because the demo venv had not been re-synced with
`pip install -r requirements.txt`. The deployed code imported `sentry_sdk`
and `sentry_sdk.integrations.fastapi.FastApiIntegration`, neither of which
were installed -- the process exited with ModuleNotFoundError mid-boot.

The fix lives in demo/startup_demo.py only (Demo/SaaS-only entrypoint, excluded
from CE export). CE is unaffected because CE never imports sentry_sdk.

These tests load the preflight helper without invoking the whole module
boot path -- the module's top-level imports require a working project layout,
so we use importlib.util.spec_from_file_location to load it in isolation
and stub the helpers the function calls.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.informational


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STARTUP_DEMO_PATH = _PROJECT_ROOT / "demo" / "startup_demo.py"


@pytest.fixture
def startup_demo_module():
    """Load demo/startup_demo.py with the rest of its boot side effects
    intact (it imports startup.py, which is safe in a test environment)."""
    spec = importlib.util.spec_from_file_location("startup_demo_test_load", str(_STARTUP_DEMO_PATH))
    module = importlib.util.module_from_spec(spec)
    sys.modules["startup_demo_test_load"] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop("startup_demo_test_load", None)


class TestMissingSaasDependencies:
    """The pure-function half: enumerate which packages are missing.

    These tests do not depend on the surrounding `print_error` plumbing;
    they exercise the import-check loop directly.
    """

    def test_returns_empty_when_sentry_sdk_installed(self, startup_demo_module):
        """In the local dev environment sentry-sdk is installed via
        requirements.txt, so the preflight finds nothing missing -- this is
        the green path that proves the check doesn't false-positive."""
        # Sanity: confirm sentry_sdk really is importable in this venv,
        # otherwise the test premise is broken.
        import importlib

        importlib.import_module("sentry_sdk")
        assert startup_demo_module._missing_saas_dependencies() == []

    def test_reports_sentry_sdk_when_top_level_missing(self, startup_demo_module, monkeypatch):
        """Simulate the production failure: sentry_sdk fails to import.
        Preflight must surface it under its pip name 'sentry-sdk[fastapi]'."""
        real_import = importlib.import_module

        def fake_import(name: str, *args: Any, **kwargs: Any):
            if name == "sentry_sdk" or name.startswith("sentry_sdk."):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import)
        missing = startup_demo_module._missing_saas_dependencies()
        assert "sentry-sdk[fastapi]" in missing
        # Even if both the top-level and the submodule fail, only ONE label
        # is reported (deduped) so the operator sees a clean instruction list.
        assert missing.count("sentry-sdk[fastapi]") == 1

    def test_reports_sentry_sdk_when_only_fastapi_extra_missing(self, startup_demo_module, monkeypatch):
        """A subtle production case: bare `pip install sentry-sdk` succeeded
        but `pip install sentry-sdk[fastapi]` was skipped. The top-level
        module imports, but the integration submodule does not."""
        real_import = importlib.import_module

        def fake_import(name: str, *args: Any, **kwargs: Any):
            if name == "sentry_sdk.integrations.fastapi":
                raise ImportError("No module named 'sentry_sdk.integrations.fastapi'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", fake_import)
        missing = startup_demo_module._missing_saas_dependencies()
        # The [fastapi] extra is the reason the submodule import fails, so
        # the operator instruction is still "pip install sentry-sdk[fastapi]".
        assert "sentry-sdk[fastapi]" in missing


class TestPreflightSaasDependencies:
    """The wrapper that prints + returns an exit code."""

    def test_returns_zero_on_healthy_environment(self, startup_demo_module):
        assert startup_demo_module._preflight_saas_dependencies() == 0

    def test_returns_nonzero_on_missing_dep(self, startup_demo_module, monkeypatch, capsys):
        # Force the check to report a missing dep
        monkeypatch.setattr(
            startup_demo_module,
            "_missing_saas_dependencies",
            lambda: ["sentry-sdk[fastapi]"],
        )
        rc = startup_demo_module._preflight_saas_dependencies()
        assert rc != 0, "preflight must abort startup when SaaS deps are missing"

    def test_prints_actionable_pip_command(self, startup_demo_module, monkeypatch, capsys):
        """The whole point of fail-fast is the operator sees a copy-pasteable
        fix. Regression-guard the exact pip command shape."""
        monkeypatch.setattr(
            startup_demo_module,
            "_missing_saas_dependencies",
            lambda: ["sentry-sdk[fastapi]"],
        )
        startup_demo_module._preflight_saas_dependencies()
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "pip install -r requirements.txt" in combined
        assert "sentry-sdk[fastapi]" in combined
        # The fix instructions must mention restarting the service so the
        # operator does not just install and walk away wondering why nothing
        # changed.
        assert "systemctl restart" in combined


class TestMainEntrypointHonorsPreflight:
    """Integration check: main() exits non-zero before touching migrations
    if the preflight reports missing deps. Without this, a missed sync would
    crash later in startup with an unhelpful stack trace."""

    def test_main_aborts_on_failed_preflight(self, startup_demo_module, monkeypatch):
        monkeypatch.setenv("GILJO_MODE", "demo")
        monkeypatch.setattr(
            startup_demo_module,
            "_missing_saas_dependencies",
            lambda: ["sentry-sdk[fastapi]"],
        )
        # Sentinel: if main() proceeds past preflight, this raises so the
        # test fails loudly rather than silently passing.
        monkeypatch.setattr(
            startup_demo_module,
            "run_startup",
            lambda **kw: pytest.fail("main() should have aborted before run_startup"),
        )
        # argparse will read sys.argv -- give it a clean argv to avoid
        # picking up pytest's own flags.
        with patch.object(sys, "argv", ["startup_demo.py"]):
            rc = startup_demo_module.main()
        assert rc != 0
