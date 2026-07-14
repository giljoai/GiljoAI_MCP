# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6229 — chain_conductor rides the agent WebSocket event payloads.

Edition scope: CE.

Regression at the failing layer (the WS-payload boundary): the project-less
chain conductor leaked into a member project's agent table because the agent
WS event payloads omitted the flat ``chain_conductor`` flag the FE JobsTab
filter keys on (the REST serializer already set it — BE-6200 #6). These tests
assert that the conductor's WS events now carry ``chain_conductor=True`` and a
normal agent's events carry ``False``, mirroring the REST serializer's source
(``job_metadata.chain_conductor``).

Parallel-safe: no DB, no module-level mutable state — each test builds its own
service + capturing WS manager and passes lightweight stand-ins for the job /
execution rows the broadcast code reads attributes off of.
"""

from types import SimpleNamespace

import pytest

from giljo_mcp.services.progress_service import ProgressService


class _CapturingWebSocketManager:
    """Captures every broadcast_to_tenant call's (event_type, data)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def broadcast_to_tenant(self, tenant_key: str, event_type: str, data: dict) -> None:
        self.calls.append({"tenant_key": tenant_key, "event_type": event_type, "data": data})


def _make_progress_service() -> tuple[ProgressService, _CapturingWebSocketManager]:
    ws = _CapturingWebSocketManager()
    svc = ProgressService(
        db_manager=None,
        tenant_manager=None,
        websocket_manager=ws,
    )
    return svc, ws


def _make_job(*, chain_conductor: bool):
    # The broadcast code reads job.project_id + job.job_metadata only. The
    # conductor's pre-spawned impl-phase execution carries a REAL project_id,
    # so set one (the blocked->working branch str()'s it unconditionally).
    metadata = {"chain_conductor": True, "run_id": "run-1"} if chain_conductor else {}
    return SimpleNamespace(project_id="proj-member-1", job_metadata=metadata)


def _make_execution():
    return SimpleNamespace(
        agent_id="exec-1",
        agent_display_name="conductor",
        agent_name="conductor",
        progress=50,
        current_task="driving the chain",
        last_progress_at=None,
        duration_seconds=0.0,
        working_started_at=None,
    )


async def _emit_and_collect(chain_conductor: bool) -> dict[str, dict]:
    """Drive the progress broadcast (emits job:progress_update AND, on a
    blocked->working transition, agent:status_changed) and return the captured
    payloads keyed by event_type."""
    svc, ws = _make_progress_service()
    job = _make_job(chain_conductor=chain_conductor)
    execution = _make_execution()

    await svc._broadcast_progress_update(
        tenant_key="tenant-test",
        job_id="job-1",
        job=job,
        execution=execution,
        progress={"todo_items": [{"content": "step", "status": "completed"}]},
        blocked_to_working=True,
        old_resting_status="blocked",
        todo_items_payload=[{"content": "step", "status": "completed"}],
    )

    return {call["event_type"]: call["data"] for call in ws.calls}


@pytest.mark.asyncio
async def test_conductor_ws_events_carry_chain_conductor_true():
    by_type = await _emit_and_collect(chain_conductor=True)

    # Both agent-row-bearing event types fired and both carry the flag.
    assert "job:progress_update" in by_type
    assert "agent:status_changed" in by_type
    assert by_type["job:progress_update"]["chain_conductor"] is True
    assert by_type["agent:status_changed"]["chain_conductor"] is True


@pytest.mark.asyncio
async def test_normal_agent_ws_events_carry_chain_conductor_false():
    by_type = await _emit_and_collect(chain_conductor=False)

    assert by_type["job:progress_update"]["chain_conductor"] is False
    assert by_type["agent:status_changed"]["chain_conductor"] is False
