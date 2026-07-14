# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-3009b — per-process background-jobs gate.

Covers the worker-gate extraction that lets a single dedicated worker service own
the shared cross-tenant maintenance/reaper loops once WEB_CONCURRENCY>1:

1. ``should_run_background_jobs()`` parses ``GILJO_RUN_BACKGROUND_JOBS`` with a
   DEFAULT-ON contract (unset/empty/truthy -> on; only explicit falsey -> off),
   so CE single-process and un-split SaaS stay byte-identical.
2. ``init_background_tasks`` with the gate OFF starts ZERO maintenance/reaper
   loops, while STILL starting the per-worker telemetry flushers (api/ws metrics)
   that must run in every web worker (the audit's "justify staying per-worker"
   carve-out). With the gate ON every loop starts.

The app.py lifespan gates the trial reaper, deletion reaper, backup scheduler and
the health/silence monitors on the SAME ``should_run_background_jobs()`` helper,
so the helper contract test below is the shared guarantee for those paths too.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

from api.startup import background_tasks as bt
from api.startup import oauth_code_reaper
from api.startup.background_jobs_gate import ENV_VAR, should_run_background_jobs


# Loops that MUST run in every web worker regardless of the gate.
_TELEMETRY_LOOPS = {"sync_api_metrics_to_db", "sync_ws_metrics_to_db"}

# Maintenance/reaper/sweep loops that the gate routes to the worker service.
_GATED_LOOPS = {
    "cleanup_expired_download_tokens",
    "scan_expiring_api_keys_task",
    "purge_old_notifications_task",
    "cleanup_expired_mcp_sessions_task",
    "cleanup_expired_oauth_codes_task",
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),  # unset -> default ON
        ("", True),  # empty -> default ON
        ("   ", True),  # whitespace-only -> default ON
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("on", True),
        ("yes", True),
        ("anything-else", True),  # unknown token -> ON (fail-safe to current behaviour)
        ("0", False),
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("  off  ", False),  # surrounding whitespace tolerated
    ],
)
def test_should_run_background_jobs_parsing(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv(ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENV_VAR, value)
    assert should_run_background_jobs() is expected


def _patch_create_task(monkeypatch):
    """Capture coroutine-function names handed to asyncio.create_task.

    Closes each captured coroutine so no "coroutine was never awaited" warning is
    emitted, and returns a list that the test asserts against. Patches BOTH
    background_tasks.py and oauth_code_reaper.py (BE-8000i's reaper was
    extracted to its own module to stay under the 800-line CI guardrail, so it
    calls asyncio.create_task via its own module-level import).
    """
    created: list[str] = []

    def fake_create_task(coro, *args, **kwargs):
        created.append(coro.cr_code.co_name)
        coro.close()
        return MagicMock(name="task")

    monkeypatch.setattr(bt.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(oauth_code_reaper.asyncio, "create_task", fake_create_task)
    return created


@pytest.mark.asyncio
async def test_gate_off_starts_only_per_worker_telemetry(monkeypatch):
    """Gate OFF -> ZERO maintenance/reaper loops; only telemetry flushers run."""
    monkeypatch.setenv(ENV_VAR, "off")
    monkeypatch.setenv("GILJO_MODE", "saas")
    created = _patch_create_task(monkeypatch)

    state = types.SimpleNamespace(db_manager=None, tenant_manager=None)
    await bt.init_background_tasks(state)

    # Exactly the two per-worker telemetry flushers, nothing else.
    assert set(created) == _TELEMETRY_LOOPS
    assert not (_GATED_LOOPS & set(created))


@pytest.mark.asyncio
async def test_gate_on_starts_all_loops(monkeypatch):
    """Gate ON (default, unset) -> telemetry + every gated maintenance loop run."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    # SaaS so the CE-only update-checker / tool-rename one-shots are skipped;
    # db_manager=None so the one-time purges + banner emit short-circuit cleanly.
    monkeypatch.setenv("GILJO_MODE", "saas")
    created = _patch_create_task(monkeypatch)

    state = types.SimpleNamespace(db_manager=None, tenant_manager=None)
    await bt.init_background_tasks(state)

    started = set(created)
    assert started >= _TELEMETRY_LOOPS
    assert started >= _GATED_LOOPS


@pytest.mark.asyncio
async def test_gate_default_is_on_when_unset(monkeypatch):
    """Belt-and-suspenders: an unset env var must keep the maintenance loops on
    (the CE single-process / un-split-SaaS byte-identical guarantee)."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setenv("GILJO_MODE", "saas")
    created = _patch_create_task(monkeypatch)

    state = types.SimpleNamespace(db_manager=None, tenant_manager=None)
    await bt.init_background_tasks(state)

    assert "cleanup_expired_download_tokens" in created
