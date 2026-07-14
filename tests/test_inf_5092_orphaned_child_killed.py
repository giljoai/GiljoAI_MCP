# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
INF-5092 regression: orphaned child processes are killed when the launcher
exits (Windows Job Object containment).

Test strategy
-------------
Windows Job Objects with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE guarantee that
all processes assigned to the job are terminated when the last handle to the
job is closed (i.e. when the holding process exits).

This test:
1. Spawns a tiny long-lived child process (``python -c "import time; time.sleep(999)"``).
2. Wraps it in a WindowsJobObject (from src/giljo_mcp/process/win_job_object.py).
3. Terminates the *launcher* side by closing the job handle (simulating parent exit).
4. Asserts the child is dead within 2 s.

Skipped on non-Windows — the Job Object mechanism is Windows-only.  On Linux
the equivalent is process groups / prctl(PR_SET_PDEATHSIG) which is handled
separately in the same module but not tested here.

No DB interaction — no TransactionalTestContext needed.
No module-level mutable state — fixture-scoped only.
"""

from __future__ import annotations

import platform
import subprocess
import sys
import time
from pathlib import Path

import pytest


_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.mark.skipif(platform.system() != "Windows", reason="Job Object is Windows-only")
def test_orphaned_child_killed_on_job_close() -> None:
    """
    A child wrapped in a WindowsJobObject must be dead within 2 s of the
    job handle being closed.
    """
    from giljo_mcp.process.win_job_object import WindowsJobObject

    # Start a long-lived child
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(999)"])

    job = WindowsJobObject()
    job.assign(child.pid)

    # Close the job handle — this is what happens when the launcher process exits
    job.close()

    # Poll for child death
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if child.poll() is not None:
            break
        time.sleep(0.05)

    exit_code = child.poll()
    assert exit_code is not None, (
        f"Child process (PID {child.pid}) still alive 2 s after job handle closed. "
        "Job Object containment is NOT working."
    )


@pytest.mark.skipif(platform.system() != "Windows", reason="Job Object is Windows-only")
def test_job_object_context_manager() -> None:
    """
    WindowsJobObject used as a context manager: child must be dead after
    the ``with`` block exits.
    """
    from giljo_mcp.process.win_job_object import WindowsJobObject

    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(999)"])

    with WindowsJobObject() as job:
        job.assign(child.pid)
    # __exit__ calls close()

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if child.poll() is not None:
            break
        time.sleep(0.05)

    assert child.poll() is not None, f"Child (PID {child.pid}) still alive after context manager exit."
