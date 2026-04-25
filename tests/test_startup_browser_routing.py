# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Regression tests for IMP-0011 Phase 2: mode-aware browser auto-open URL.

The launcher (startup.py) must branch the auto-open URL on `deployment_context`
(read from config.yaml) rather than always opening `/welcome` and relying on a
frontend `route_signal` bounce for demo installs.

Branch order (load-bearing):
1. deployment_context in {"demo", "saas-production"} -> /demo-landing
2. is_first_run (CE first-run)                       -> /welcome
3. otherwise                                         -> dashboard root (no path)

`saas-production` additionally triggers `suppress_browser=True` upstream, so in
that mode `open_browser` must not be called at all.

These tests pin the three-way branch by calling the pure helper
`_choose_browser_target(deployment_context, is_first_run)` which returns:
- a route string (e.g. "/demo-landing", "/welcome", or "" for dashboard root)
- `None` when browser auto-open should be suppressed entirely
"""

from __future__ import annotations

import pytest

import startup


class TestChooseBrowserTarget:
    """Pure-helper branch coverage for _choose_browser_target()."""

    def test_demo_first_run_opens_demo_landing(self) -> None:
        assert startup._choose_browser_target("demo", is_first_run=True) == "/demo-landing"

    def test_demo_not_first_run_still_opens_demo_landing(self) -> None:
        # Demo mode MUST win over the dashboard fallback; demo operators never
        # hit /welcome and never hit the dashboard root on auto-open.
        assert startup._choose_browser_target("demo", is_first_run=False) == "/demo-landing"

    def test_saas_production_returns_none_for_suppression(self) -> None:
        # Defence in depth: even though suppress_browser short-circuits upstream,
        # the helper itself must signal "do not open" for saas-production.
        assert startup._choose_browser_target("saas-production", is_first_run=True) is None
        assert startup._choose_browser_target("saas-production", is_first_run=False) is None

    def test_localhost_first_run_opens_welcome(self) -> None:
        assert startup._choose_browser_target("localhost", is_first_run=True) == "/welcome"

    def test_localhost_not_first_run_opens_dashboard_root(self) -> None:
        # Dashboard root is represented by empty path string ("" -> URL ends in :port).
        assert startup._choose_browser_target("localhost", is_first_run=False) == ""

    def test_lan_first_run_opens_welcome(self) -> None:
        # lan is a non-demo, non-saas context; it should follow the CE branch.
        assert startup._choose_browser_target("lan", is_first_run=True) == "/welcome"

    def test_lan_not_first_run_opens_dashboard_root(self) -> None:
        assert startup._choose_browser_target("lan", is_first_run=False) == ""


class TestBrowserRoutingIntegration:
    """End-to-end URL assembly via the helper, matching how main() composes URLs."""

    @pytest.mark.parametrize(
        ("deployment_context", "is_first_run", "expected_suffix"),
        [
            ("demo", True, "/demo-landing"),
            ("demo", False, "/demo-landing"),
            ("localhost", True, "/welcome"),
        ],
    )
    def test_url_suffix_matches_branch(
        self,
        deployment_context: str,
        is_first_run: bool,
        expected_suffix: str,
    ) -> None:
        http_proto = "http"
        server_host = "127.0.0.1"
        browser_port = 5173
        target_route = startup._choose_browser_target(deployment_context, is_first_run)
        assert target_route is not None
        setup_url = f"{http_proto}://{server_host}:{browser_port}{target_route}"
        assert setup_url.endswith(expected_suffix)

    def test_dashboard_url_has_no_trailing_path(self) -> None:
        http_proto = "http"
        server_host = "127.0.0.1"
        browser_port = 5173
        target_route = startup._choose_browser_target("localhost", is_first_run=False)
        assert target_route == ""
        dashboard_url = f"{http_proto}://{server_host}:{browser_port}{target_route}"
        # Must end at the port, not at any path segment.
        assert dashboard_url == f"http://127.0.0.1:{browser_port}"
        assert not dashboard_url.endswith("/welcome")
        assert not dashboard_url.endswith("/demo-landing")

    def test_saas_production_short_circuits_no_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If the helper returns None, the caller must not invoke open_browser.

        This simulates the upstream `suppress_browser` guard: in saas-production
        mode, open_browser MUST NOT be called.
        """
        calls: list[str] = []

        def fake_open_browser(url: str, delay: int = 3) -> None:
            # `delay` is part of open_browser's signature; we don't sleep in tests.
            _ = delay
            calls.append(url)

        monkeypatch.setattr(startup, "open_browser", fake_open_browser)

        target_route = startup._choose_browser_target("saas-production", is_first_run=True)
        if target_route is not None:
            startup.open_browser(f"http://127.0.0.1:5173{target_route}", delay=0)

        assert calls == [], "open_browser must not be called in saas-production mode"
