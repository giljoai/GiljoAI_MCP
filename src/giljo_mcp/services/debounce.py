# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""In-process monotonic-clock debounce for MCP hot-path write reduction (BE-6070).

This lifts the throttle pattern ALREADY used in this codebase
(``ProgressService._todo_warning_timestamps`` and
``heartbeat.touch_heartbeat``'s ``DEBOUNCE_SECONDS``) into one tiny, testable
helper so the several MCP hot-path call sites share a single reset hook. It is
NOT a new architectural layer -- it is the same ``dict[key] -> last-fire``
throttle, centralized.

Why module level: the call sites (``MCPSessionManager``, the ``_call_tool``
dispatch) are constructed per request, so per-instance state would not persist
across calls -- the debounce must outlive any one request. Module-level state
does exactly that.

Why monotonic: ``time.monotonic()`` is immune to wall-clock jumps (NTP steps,
DST), so a debounce window can never be skewed by a clock change.

Why a process-local gate is sufficient: prod runs single-worker
(``WEB_CONCURRENCY`` defaults to 1), so one process sees every call and an
in-process gate is both sufficient and correct. (pytest-xdist runs separate
*processes*, so each worker has its own state -- no cross-worker bleed.)
"""

import threading
import time


# namespace -> {key -> last-fire monotonic seconds}
_LAST_FIRED: dict[str, dict[str, float]] = {}
_LOCK = threading.Lock()


def should_run(namespace: str, key: str, interval_seconds: float) -> bool:
    """Return True (and record the fire time) when ``key`` last fired more than
    ``interval_seconds`` ago within ``namespace``; otherwise return False.

    Atomic check-and-set: the FIRST call for any key always returns True (the
    first write is never debounced), and a True result records "now" so the next
    call within the window returns False.

    Args:
        namespace: A stable bucket name per call site (e.g. ``"mcp_posthooks"``).
        key: The throttle key within the bucket (job_id, api_key_id, session_id).
        interval_seconds: Minimum seconds between two True results for one key.
    """
    now = time.monotonic()
    with _LOCK:
        bucket = _LAST_FIRED.setdefault(namespace, {})
        last = bucket.get(key)
        if last is not None and (now - last) < interval_seconds:
            return False
        bucket[key] = now
        return True


def reset(namespace: str | None = None) -> None:
    """Clear debounce state. Test hook -- keeps the in-process gate from bleeding
    across tests.

    Args:
        namespace: When given, clears only that bucket; otherwise clears all.
    """
    with _LOCK:
        if namespace is None:
            _LAST_FIRED.clear()
        else:
            _LAST_FIRED.pop(namespace, None)
