# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression: the process must exit cleanly — no lingering non-daemon threads
from logging setup or the config file watcher.

Root cause (2026-06-08 intermittent CI teardown hang; faulthandler-confirmed):
- ``api.run_api._configure_logging()`` created a NEW ``QueueListener`` on the
  shared module-level ``_log_queue`` on every call and re-registered ``atexit``
  each time. Repeated calls (server start + several tests call it directly)
  accumulated orphaned monitor threads on one queue; at exit the multiple
  ``stop()`` calls deadlocked — ``join()`` waited on a monitor whose sentinel
  had been consumed by a sibling → the process hung (the original 46-min hang).
- ``ConfigManager._setup_file_watcher`` started a NON-daemon watchdog
  ``Observer`` that lingered and blocked interpreter shutdown.

Failing layer: process teardown — ``api/run_api._configure_logging`` (atexit)
and ``src/giljo_mcp/config_manager.ConfigManager._setup_file_watcher``.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_repeated_configure_logging_process_exits_cleanly():
    """Repeated ``_configure_logging()`` must not deadlock the process at exit.

    Three calls reproduce the listener accumulation. Without the idempotent /
    single-atexit fix, the atexit ``stop()`` join deadlocks and this subprocess
    never exits (caught here as a hang, asserted as a failure).
    """
    code = textwrap.dedent(
        """
        import logging
        from api import run_api
        for _ in range(3):
            run_api._configure_logging(log_level=logging.INFO)
        print("CLEAN_EXIT")
        """
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,  # asserted on stdout content below, not returncode
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - regression signal
        raise AssertionError(
            "process hung at exit after repeated _configure_logging() — a "
            "lingering non-daemon thread / atexit deadlock has regressed"
        ) from exc

    assert "CLEAN_EXIT" in proc.stdout, proc.stderr
    assert proc.returncode == 0, proc.stderr


def test_config_file_watcher_observer_is_daemon(tmp_path):
    """The config hot-reload watcher must be a daemon so it never blocks exit."""
    from giljo_mcp.config_manager import ConfigManager

    cm = ConfigManager(config_path=tmp_path / "config.yaml", auto_reload=False)
    cm._setup_file_watcher()
    try:
        assert cm._observer is not None
        assert cm._observer.daemon is True
    finally:
        cm.stop_watching()
