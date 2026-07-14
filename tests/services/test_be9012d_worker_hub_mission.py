# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9012d Phase 3.5 — worker coordination goes native-Hub.

The worker 5-phase protocol body (``worker_body.py``) now references the
project's bound Hub thread (``join_thread`` / ``get_thread_history`` /
``post_to_thread``) instead of the retired bus (``receive_messages`` /
``send_message`` / ``get_messages``). These tests cover three layers:

1. The pure render (``_build_worker_protocol_body`` / ``_generate_agent_protocol``)
   with a caller-supplied thread id — and its graceful None-degradation for a
   job with no resolved thread.
2. ``MissionService._assemble_mission_context`` — the service-layer seam that
   threads a resolved ``comm_thread_id`` into the rendered protocol (no DB,
   mirrors ``test_mission_service_serena_guidance.py``'s direct-call pattern).
3. ``MissionService._resolve_comm_thread_id`` — the NEW resolver call added to
   ``get_agent_mission``, proving it reuses the SAME session it is given (no
   cross-session read) and degrades to None on a resolution failure rather
   than breaking mission delivery (mirrors the established
   ``_resolve_chain_execution_mode`` / ``_is_chain_member`` best-effort
   pattern already in ``mission_service.py``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.protocol_sections.agent_protocol import _generate_agent_protocol
from giljo_mcp.services.protocol_sections.worker_body import _build_worker_protocol_body


_JOB = "JOB-9012D-0001"
_TENANT = "tk_be9012d_worker_mission"
_EXEC = "EXEC-9012D-0001"
_THREAD = "CHT-thread-uuid"

_BUS_CALLS = ("receive_messages(", "send_message(", "get_messages(")
_HUB_CALLS = ("get_thread_history(", "post_to_thread(", "join_thread(")


def _render(comm_thread_id: str | None) -> str:
    return _generate_agent_protocol(
        job_id=_JOB,
        tenant_key=_TENANT,
        agent_name="implementer",
        agent_id=_EXEC,
        job_type="implementer",
        comm_thread_id=comm_thread_id,
    )


class TestWorkerBodyRendersHubNotBus:
    """(a) a job WITH a resolved thread references the Hub calls + embeds the
    thread id; (b) NO bus call ever appears, with or without a resolved thread."""

    def test_with_thread_id_references_hub_calls_and_embeds_the_id(self):
        protocol = _render(_THREAD)
        for call in _HUB_CALLS:
            assert call in protocol, f"expected {call!r} in worker protocol"
        assert f'"{_THREAD}"' in protocol, "the resolved thread id must be embedded in the tool-call examples"

    def test_no_bus_calls_present_with_thread_id(self):
        protocol = _render(_THREAD)
        for call in _BUS_CALLS:
            assert call not in protocol, f"retired bus call {call!r} leaked into the worker protocol"

    def test_no_bus_calls_present_without_thread_id(self):
        """A project-less render (comm_thread_id=None) must ALSO stay bus-free —
        it degrades to the no-thread banner, never falls back to the bus."""
        protocol = _render(None)
        for call in _BUS_CALLS:
            assert call not in protocol, f"retired bus call {call!r} leaked into the degraded worker protocol"

    def test_none_degrades_gracefully_with_a_banner_not_a_crash(self):
        protocol = _render(None)
        assert "NO COORDINATION THREAD BOUND" in protocol
        assert '"<none>"' in protocol
        # Still references the Hub call NAMES (just with the placeholder id) —
        # the banner tells the agent to skip them, it does not delete the lines.
        for call in _HUB_CALLS:
            assert call in protocol

    def test_bare_tool_names_no_mcp_prefix(self):
        """F1: rendered prose uses bare tool names, never the mcp__giljo_mcp__ prefix."""
        protocol = _render(_THREAD)
        assert "mcp__giljo_mcp__" not in protocol
        assert "your MCP client may expose them under a prefix" in protocol

    def test_join_thread_happens_before_first_message_check(self):
        """Phase 1: join_thread is the FIRST comm step, ahead of the message drain."""
        protocol = _render(_THREAD)
        phase1_start = protocol.find("Phase 1: STARTUP")
        phase1_end = protocol.find("Phase 2: EXECUTION")
        phase1 = protocol[phase1_start:phase1_end]
        join_pos = phase1.find("join_thread(")
        history_pos = phase1.find("get_thread_history(")
        assert join_pos != -1 and history_pos != -1
        assert join_pos < history_pos, "join_thread must precede the first get_thread_history drain"


class TestBuildWorkerProtocolBodyDirect:
    """Pure builder-level check (no protocol-router indirection)."""

    def test_direct_call_with_comm_thread_id(self):
        body = _build_worker_protocol_body(
            job_id=_JOB,
            tenant_key=_TENANT,
            executor_id=_EXEC,
            job_type="implementer",
            phase1_step4="5. **MANDATORY: Create TodoWrite task list**",
            git_commit_block="",
            giljo_block="",
            protocol_framing="",
            comm_thread_id=_THREAD,
        )
        assert f'"{_THREAD}"' in body
        for call in _BUS_CALLS:
            assert call not in body


class TestMissionServiceThreadsCommThreadId:
    """``MissionService._assemble_mission_context`` — the service seam Part A
    wires ``comm_thread_id`` through, without touching a DB."""

    @staticmethod
    def _service() -> MissionService:
        return MissionService(db_manager=MagicMock(), tenant_manager=MagicMock())

    @staticmethod
    def _job_and_execution() -> tuple[AgentJob, AgentExecution]:
        job_id = str(uuid4())
        job = AgentJob(
            job_id=job_id,
            tenant_key=_TENANT,
            project_id=str(uuid4()),
            mission="Do the assigned work.",
            job_type="implementer",
            status="active",
        )
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_id,
            tenant_key=_TENANT,
            agent_display_name="implementer",
            agent_name="implementer-1",
            status="waiting",
        )
        return job, execution

    def test_assemble_mission_context_threads_comm_thread_id_into_full_protocol(self):
        service = self._service()
        job, execution = self._job_and_execution()

        response = service._assemble_mission_context(
            job=job,
            execution=execution,
            project=None,
            agent_identity=None,
            all_project_executions=[execution],
            mission_lookup={},
            current_team_state=None,
            tenant_key=_TENANT,
            comm_thread_id=_THREAD,
        )
        assert f'"{_THREAD}"' in (response.full_protocol or "")

    def test_assemble_mission_context_degrades_without_comm_thread_id(self):
        service = self._service()
        job, execution = self._job_and_execution()

        response = service._assemble_mission_context(
            job=job,
            execution=execution,
            project=None,
            agent_identity=None,
            all_project_executions=[execution],
            mission_lookup={},
            current_team_state=None,
            tenant_key=_TENANT,
        )
        assert "NO COORDINATION THREAD BOUND" in (response.full_protocol or "")


class TestResolveCommThreadId:
    """``MissionService._resolve_comm_thread_id`` — the NEW resolver call."""

    @pytest.mark.asyncio
    async def test_constructs_comm_thread_service_with_the_given_session(self):
        """CRITICAL contract: the SAME session as the mission render — no
        cross-session read. Also pins the exact resolver call shape."""
        db_manager = MagicMock()
        tenant_manager = MagicMock()
        service = MissionService(db_manager=db_manager, tenant_manager=tenant_manager)
        given_session = MagicMock(name="given_session")
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=_TENANT,
            project_id=str(uuid4()),
            mission="m",
            job_type="implementer",
            status="active",
        )

        with patch("giljo_mcp.services.comm_thread_service.CommThreadService") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.resolve_or_create_bound_thread = AsyncMock(return_value={"thread_id": _THREAD})

            result = await service._resolve_comm_thread_id(given_session, job, _TENANT)

        assert result == _THREAD
        mock_cls.assert_called_once_with(db_manager, tenant_manager, session=given_session)
        mock_instance.resolve_or_create_bound_thread.assert_awaited_once_with(
            project_id=str(job.project_id), tenant_key=_TENANT
        )

    @pytest.mark.asyncio
    async def test_degrades_to_none_on_resolution_failure(self):
        """A resolver failure must never break mission delivery — degrade to None."""
        service = MissionService(db_manager=MagicMock(), tenant_manager=MagicMock())
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=_TENANT,
            project_id=str(uuid4()),
            mission="m",
            job_type="implementer",
            status="active",
        )

        with patch(
            "giljo_mcp.services.comm_thread_service.CommThreadService.resolve_or_create_bound_thread",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db exploded"),
        ):
            result = await service._resolve_comm_thread_id(MagicMock(), job, _TENANT)

        assert result is None
