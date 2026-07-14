# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE/SaaS] Both editions.

"""
INF-6023b regression tests (at the failing layer).

The original INF-6023 work over-engineered a live-log "fix" on a disproven
crash theory. This rolls it back and restores the simple cross-OS, --verbose
viewer plus a defensive single-instance guard. These tests pin the behaviour
that broke / changed:

startup.py
  - start_api_server opens the live viewer ONLY when verbose=True (the
    always-on regression) and ONLY in CE (SaaS/Railway never spawns a window).
  - start_api_server passes ``--port N --strict-port`` to run_api so a losing
    duplicate exits instead of roaming to 7273 and corrupting api_stdout.log.
  - _single_instance_lock is FAIL-OPEN: a lock failure never blocks boot.

api/run_api.py
  - _strict_port_available reports an active listener as unavailable (so
    --strict-port fails fast) and a free port as available.

Parallel-safe: tmp_path + monkeypatch only; no DB, no module-level state.
"""

import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# startup.py lives at the project root (not in a package). Insert the root once
# so the import works regardless of the invocation directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest  # noqa: E402

import startup  # noqa: E402


# ---------------------------------------------------------------------------
# start_api_server: viewer gating (verbose + edition) and strict-port argv
# ---------------------------------------------------------------------------


def _run_start_api_server(monkeypatch, *, giljo_mode, verbose, api_port=None):
    """Call startup.start_api_server() with every heavy side-effect neutralised.

    Returns (viewer_spy, popen_spy). giljo_mode=None means the env var is absent
    (CE default). platform is forced to "Linux" so the Windows Job Object path
    is skipped; the live viewer is patched to a spy so no window is spawned and
    only the API-server Popen remains observable.
    """
    if giljo_mode is None:
        monkeypatch.delenv("GILJO_MODE", raising=False)
    else:
        monkeypatch.setenv("GILJO_MODE", giljo_mode)

    proc = MagicMock()
    proc.pid = 99999
    viewer_spy = MagicMock()

    with (
        patch.object(startup, "_launch_log_viewer", viewer_spy),
        patch("startup.subprocess.Popen", return_value=proc) as popen_spy,
        patch("startup.os.open", return_value=5),
        patch("startup.os.close"),
        patch("startup.platform.system", return_value="Linux"),
        patch("startup.Path.exists", return_value=True),
        patch("startup.Path.mkdir"),
        patch("startup.print_success"),
        patch("startup.print_info"),
        patch("startup.print_warning"),
        patch("startup.print_error"),
    ):
        startup.start_api_server(verbose=verbose, api_port=api_port)

    return viewer_spy, popen_spy


class TestViewerGating:
    def test_no_viewer_when_not_verbose(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CE but verbose=False -> viewer must NOT open (always-on regression)."""
        viewer_spy, _ = _run_start_api_server(monkeypatch, giljo_mode=None, verbose=False)
        viewer_spy.assert_not_called()

    def test_viewer_opens_when_verbose_ce(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CE + verbose=True -> viewer opens exactly once."""
        viewer_spy, _ = _run_start_api_server(monkeypatch, giljo_mode="ce", verbose=True)
        viewer_spy.assert_called_once()

    def test_viewer_opens_when_verbose_ce_default_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GILJO_MODE unset (CE default) + verbose=True -> viewer opens."""
        viewer_spy, _ = _run_start_api_server(monkeypatch, giljo_mode=None, verbose=True)
        viewer_spy.assert_called_once()

    def test_no_viewer_in_saas_even_when_verbose(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SaaS must never spawn a console window, even with verbose=True."""
        viewer_spy, popen_spy = _run_start_api_server(monkeypatch, giljo_mode="saas", verbose=True)
        viewer_spy.assert_not_called()
        # Only the API-server Popen ran (no viewer Popen).
        assert popen_spy.call_count == 1


class TestStrictPortArgv:
    def test_strict_port_passed_when_api_port_given(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The launcher must hand run_api an explicit port + --strict-port."""
        _, popen_spy = _run_start_api_server(monkeypatch, giljo_mode="ce", verbose=False, api_port=7272)
        argv = list(popen_spy.call_args_list[0].args[0])
        assert "--strict-port" in argv
        assert "--port" in argv
        assert argv[argv.index("--port") + 1] == "7272"

    def test_no_strict_port_when_api_port_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Back-compat: no api_port -> no --strict-port (legacy run_api behaviour)."""
        _, popen_spy = _run_start_api_server(monkeypatch, giljo_mode="ce", verbose=False, api_port=None)
        argv = list(popen_spy.call_args_list[0].args[0])
        assert "--strict-port" not in argv


# ---------------------------------------------------------------------------
# _single_instance_lock: fail-open + normal acquire/release
# ---------------------------------------------------------------------------


class TestSingleInstanceLock:
    def test_lock_yields_normally(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Happy path: the lock acquires, runs the body, and releases cleanly."""
        monkeypatch.setattr(startup.Path, "cwd", classmethod(lambda cls: tmp_path))
        ran = False
        with startup._single_instance_lock(timeout=1.0):
            ran = True
        assert ran is True

    def test_lock_is_fail_open(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """If acquiring the lock raises, the body STILL runs (never blocks boot)."""
        monkeypatch.setattr(startup.Path, "cwd", classmethod(lambda cls: tmp_path))

        def _boom(*_a, **_k):
            raise OSError("simulated lock failure")

        ran = False
        with patch("startup.os.open", _boom), patch("startup.print_warning"):
            with startup._single_instance_lock(timeout=1.0):
                ran = True
        assert ran is True


# ---------------------------------------------------------------------------
# _launch_log_viewer: smoke (no raise on the host platform)
# ---------------------------------------------------------------------------


def test_launch_log_viewer_does_not_raise(tmp_path: Path) -> None:
    """The viewer is best-effort: with subprocess mocked it must never raise."""
    with (
        patch("startup.subprocess.Popen", return_value=MagicMock()),
        patch("startup.shutil.which", return_value="/usr/bin/gnome-terminal"),
        patch("startup.print_success"),
        patch("startup.print_info"),
        patch("startup.print_warning"),
    ):
        startup._launch_log_viewer(tmp_path / "api_stdout.log", "2026-06-03_10-00-00")


# ---------------------------------------------------------------------------
# run_api._strict_port_available: the port-roaming fail-fast at the API layer
# ---------------------------------------------------------------------------


class TestStrictPortAvailable:
    def test_active_listener_is_unavailable(self) -> None:
        from api.run_api import _strict_port_available

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        # Generous backlog: each connect_ex probe leaves an un-accepted
        # connection queued. A real server drains its backlog via accept(); this
        # test does not, so listen(1) would exhaust after the first probe.
        srv.listen(128)
        port = srv.getsockname()[1]
        try:
            assert _strict_port_available("127.0.0.1", port) is False
            # 0.0.0.0 must normalise to the loopback probe and still detect it.
            assert _strict_port_available("0.0.0.0", port) is False
        finally:
            srv.close()

    def test_free_port_is_available(self) -> None:
        from api.run_api import _strict_port_available

        # Reserve then release a port number so (very likely) nothing listens.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        assert _strict_port_available("127.0.0.1", port) is True
