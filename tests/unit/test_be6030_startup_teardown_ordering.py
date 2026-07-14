# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6030 regression: Fix B — startup teardown ordering.

Assert that ``run_startup()`` invokes ``stop_services()`` BEFORE it spawns
the server (``start_api_server``).  The single-writer guarantee requires
tearing down any stale prior server tree *before* checking port availability
and *before* launching a new process that would open logs/giljo_mcp.log.

Test strategy
-------------
We monkeypatch every expensive side-effect in ``run_startup()`` so the
function can execute past the ordering point without requiring a real
database, real PostgreSQL, real SSL certs, or real subprocesses.  A call-
order recorder is injected into both ``stop_services`` and ``start_api_server``
so we can assert their relative positions.

This test does NOT touch the database, so no TransactionalTestContext is
needed.  All state lives in local variables (call_order list); no module-
level mutable state is introduced — parallel-safe under pytest-xdist.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Add project root to path so ``startup`` is importable as a top-level module.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def test_be6030_stop_services_called_before_start_api_server(tmp_path):
    """
    BE-6030 Fix B — teardown-before-spawn ordering regression.

    ``run_startup()`` must call ``stop_services()`` before it calls
    ``start_api_server()`` (single-writer guarantee: old process tree is torn
    down before a new one can open logs/giljo_mcp.log).

    We stub out every dependency that would require real infrastructure (DB,
    SSL, npm, subprocesses) so the function can reach the ordering point in a
    unit-test context.  The stubs record the order of the two calls we care
    about; the test asserts stop_services precedes start_api_server.

    Failing layer: startup.run_startup() call ordering
    (startup.py ~line 1565 vs ~line 1669).
    """
    import startup  # top-level module, not a package

    call_order: list[str] = []

    def _record_stop_services():
        call_order.append("stop_services")
        return 0  # stop_services returns int (stopped count)

    def _record_start_api_server(verbose=False, api_port=None):
        call_order.append("start_api_server")
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        return mock_proc

    # We need to stub out everything run_startup touches BEFORE our ordering
    # point (stop_services at ~line 1565) AND everything after it (port check,
    # npm build, start_api_server at ~line 1669).  The goal is to let the
    # function reach both calls without crashing.

    patches = [
        # --- Pre-ordering stubs (Steps 1-6 of run_startup) ---
        patch.object(startup, "check_dependencies", return_value=True),
        patch.object(startup, "install_requirements", return_value=True),
        patch.object(startup, "_patch_env_from_config", return_value=None),
        patch.object(startup, "run_database_migrations", return_value=True),
        patch.object(startup, "check_database_connectivity", return_value=(True, None)),
        patch.object(startup, "seed_default_settings", return_value=None),
        patch.object(startup, "check_first_run", return_value=(False, MagicMock())),
        patch.object(startup, "get_config_ports", return_value=(8000, 5173)),
        patch.object(startup, "get_ssl_enabled", return_value=False),
        # INF-0004: the pre-boot consistency gate runs after the frontend rebuild
        # and does a real DB connection (alembic revision check). This ordering test
        # mocks every expensive side-effect; the gate is one more — stub it to
        # "healthy" so run_startup reaches start_api_server (an empty unit-test DB
        # would otherwise read as "drifted" and short-circuit before the call we assert).
        patch.object(startup, "verify_install_consistency", return_value=[]),
        # --- Ordering point ---
        patch.object(startup, "stop_services", side_effect=_record_stop_services),
        # --- Post-ordering stubs (Steps 7-8+) ---
        patch.object(startup, "is_port_available", return_value=True),
        # Neutralise the INF-6023b single-instance lock: this test asserts call
        # ordering only, not the lock itself (covered by its own tests), and the
        # real lock would touch logs/.startup.lock on disk.
        patch.object(startup, "_single_instance_lock", side_effect=lambda *a, **k: contextlib.nullcontext()),
        patch.object(startup, "start_api_server", side_effect=_record_start_api_server),
        patch.object(startup, "start_frontend_server", return_value=MagicMock()),
        patch.object(startup, "wait_for_api_ready", return_value=True),
        # Suppress subprocess.run calls (pip install -e ., etc.)
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")),
        # Suppress any sys.argv checks (dev_mode detection)
        patch.object(sys, "argv", ["startup.py"]),
        # Suppress shutil.which (npm detection) — return None so the npm
        # build block is skipped (which is fine; we only care about ordering).
        patch("shutil.which", return_value=None),
        # Suppress browser launch / health-check output
        patch.object(startup, "open_browser", return_value=None) if hasattr(startup, "open_browser") else None,
    ]

    # Filter out None patches (optional attributes that may not exist).
    active_patches = [p for p in patches if p is not None]

    for p in active_patches:
        p.start()

    try:
        # Run with no_migrations=True to skip the migration step (already
        # stubbed, but belt-and-suspenders).  no_ssl=True avoids SSL cert
        # discovery.  no_browser=True suppresses the browser launch attempt.
        startup.run_startup(
            no_migrations=True,
            no_ssl=True,
            no_browser=True,
        )
    finally:
        for p in active_patches:
            p.stop()

    # Verify both calls were recorded (the stubs were reached).
    assert "stop_services" in call_order, (
        "stop_services() was never called by run_startup(). "
        "BE-6030 Fix B requires stop_services() to be called unconditionally "
        "before starting any new server process."
    )
    assert "start_api_server" in call_order, (
        "start_api_server() was never called by run_startup() during this test. "
        "Check that the stubs allow execution to reach line ~1669."
    )

    stop_idx = call_order.index("stop_services")
    start_idx = call_order.index("start_api_server")

    assert stop_idx < start_idx, (
        f"stop_services() must be called BEFORE start_api_server() "
        f"(single-writer guarantee — BE-6030 Fix B). "
        f"Observed order: {call_order!r}. "
        f"stop_services at position {stop_idx}, start_api_server at position {start_idx}."
    )
