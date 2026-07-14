# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9168 — the startup lock file must be owner-only (CodeQL alert #337).

Failing layer this regression-locks: ``_single_instance_lock`` in
startup_support/services.py created ``logs/.startup.lock`` with mode 0o644
(group/other readable). The lock file carries no content today, but a
world-readable file created by a privileged launcher is the
py/overly-permissive-file pattern; creation mode is now 0o600.

The assertion is umask-robust: the security property is "no group/other
bits", not an exact mode value.

Edition Scope: CE (startup.py is the self-hosted launcher; SaaS prod never
runs it).

Parallel-safe: tmp_path-scoped cwd, no shared state, no ordering dependency.
"""

from __future__ import annotations

import platform

import pytest


@pytest.mark.skipif(platform.system() == "Windows", reason="POSIX file modes are not meaningful on Windows")
def test_startup_lock_file_has_no_group_or_other_permissions(tmp_path, monkeypatch):
    from startup_support.services import _single_instance_lock

    monkeypatch.chdir(tmp_path)

    with _single_instance_lock(timeout=0.5):
        lock_path = tmp_path / "logs" / ".startup.lock"
        assert lock_path.exists()
        mode = lock_path.stat().st_mode & 0o777
        assert mode & 0o077 == 0, f"lock file mode {oct(mode)} grants group/other access"
