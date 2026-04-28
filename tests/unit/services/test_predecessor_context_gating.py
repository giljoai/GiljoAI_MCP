# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
HO1023 (pre-staging chain fix) — predecessor preamble auto-detection tests.

Background
----------
HO1022 introduced server-side auto-detection of chain vs replacement preamble
from `pred_execution.result.status`, with the heuristic "if pred_execution is
None, treat as replacement (predecessor never reached complete_job)". That
heuristic was wrong for the multi_terminal staging pattern: orchestrators
pre-spawn ALL phases up front during staging, BEFORE any of them run. At
spawn time the predecessor is in `waiting` status with no completion record,
so HO1022 baked the REPLACEMENT preamble into every healthy forward chain.

HO1023 fix
----------
Auto-detect now consults `pred_job.status` FIRST (the work order's lifecycle
state), then `pred_execution.result.status`. Replacement only when there is
an EXPLICIT failure signal:

  - pred_job.status in {failed, blocked, decommissioned}    -> REPLACEMENT
  - pred_execution.result.status in {force_completed, ...}  -> REPLACEMENT
  - otherwise (healthy, running, or pre-execution)          -> CHAIN

Reactivation flows still work: orchestrator respawns after a confirmed
predecessor failure -> pred_job.status is failed/blocked -> replacement
preamble correctly renders.

Subagent execution modes still skip injection entirely regardless of role
(the orchestrator's CLI returned the predecessor result inline).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.services._predecessor_context import (
    PREDECESSOR_CHAIN_PREAMBLE,
    PREDECESSOR_REPLACEMENT_PREAMBLE,
    SUBAGENT_EXECUTION_MODES,
    _detect_replacement_semantics,
)
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService


# ---- Fixtures -------------------------------------------------------------


@pytest.fixture
def service() -> JobLifecycleService:
    """Build a JobLifecycleService with mocked dependencies (no DB / tenant manager)."""
    return JobLifecycleService(db_manager=MagicMock(), tenant_manager=MagicMock())


def _pred_job(status: str = "waiting", project_id: str = "proj-1"):
    """Build a SimpleNamespace mirroring AgentJob shape with given status."""
    return SimpleNamespace(project_id=project_id, status=status)


def _pred_execution(result_status: str | None = None, *, display_name: str = "analyzer"):
    """Build a SimpleNamespace mirroring AgentExecution shape with optional result.status."""
    result: dict = {"summary": "Analysis complete.", "commits": ["c1", "c2"]}
    if result_status is not None:
        result["status"] = result_status
    return SimpleNamespace(agent_display_name=display_name, result=result)


def _install_repo(monkeypatch, *, pred_job, pred_execution=None) -> MagicMock:
    """Patch AgentCompletionRepository at the import site to return given fakes."""
    repo_instance = MagicMock()
    repo_instance.get_predecessor_job = AsyncMock(return_value=pred_job)
    repo_instance.get_completed_execution_for_job = AsyncMock(return_value=pred_execution)
    monkeypatch.setattr(
        "giljo_mcp.services.job_lifecycle_service.AgentCompletionRepository",
        MagicMock(return_value=repo_instance),
    )
    return repo_instance


@pytest.fixture
def fake_repo_clean_completion(monkeypatch) -> MagicMock:
    """Predecessor completed cleanly (status=complete on job, no status on result)."""
    return _install_repo(
        monkeypatch,
        pred_job=_pred_job(status="complete"),
        pred_execution=_pred_execution(),
    )


@pytest.fixture
def fake_repo_pre_execution(monkeypatch) -> MagicMock:
    """Predecessor pre-staged but not yet executed (the multi_terminal default).
    pred_job.status='waiting', pred_execution=None -- this was the case HO1022
    incorrectly treated as replacement."""
    return _install_repo(
        monkeypatch,
        pred_job=_pred_job(status="waiting"),
        pred_execution=None,
    )


# ---- Module-level constants -----------------------------------------------


def test_subagent_execution_modes_set_is_exactly_the_three_clis():
    """Hard-coded membership prevents accidental drift like 'multi_terminal' creeping in."""
    assert frozenset({"claude_code_cli", "codex_cli", "gemini_cli"}) == SUBAGENT_EXECUTION_MODES


def test_multi_terminal_is_not_a_subagent_mode():
    """multi_terminal MUST always inject preamble — separate processes can't share Task() returns."""
    assert "multi_terminal" not in SUBAGENT_EXECUTION_MODES


def test_chain_preamble_uses_forward_handoff_language():
    text = PREDECESSOR_CHAIN_PREAMBLE
    assert "PRIOR PHASE OUTPUT" in text
    assert "continuing a workflow" in text
    # Negative assertions: would indicate the wrong-semantics regression returning.
    assert "replacing a previous agent" not in text
    assert "issues were found" not in text
    assert "REPLACEMENT" not in text


def test_replacement_preamble_uses_replacement_language():
    text = PREDECESSOR_REPLACEMENT_PREAMBLE
    assert "REPLACEMENT" in text
    assert "taking over" in text


def test_neither_preamble_leaks_tenant_key():
    """Wave 1 invariant (commit ffa779bf): tenant_key is auto-injected and must
    never appear in agent-facing prose."""
    assert "tenant_key" not in PREDECESSOR_CHAIN_PREAMBLE
    assert "tenant_key" not in PREDECESSOR_REPLACEMENT_PREAMBLE


# ---- Auto-detect helper (HO1023 — chain default at spawn time) -----------


def test_detect_returns_false_when_predecessor_is_pre_execution():
    """HO1023 regression: pre-staged predecessor (waiting, no execution yet)
    must default to CHAIN, NOT replacement. This was the production bug HO1022
    introduced for multi_terminal pre-staging."""
    assert _detect_replacement_semantics(_pred_job(status="waiting"), None) is False


def test_detect_returns_false_when_predecessor_is_running():
    """Predecessor in flight (working) is still healthy — chain stays default."""
    assert _detect_replacement_semantics(_pred_job(status="working"), None) is False


def test_detect_returns_false_for_clean_completion():
    """Completed predecessor with no failure markers on result -> chain."""
    assert _detect_replacement_semantics(_pred_job(status="complete"), _pred_execution()) is False


@pytest.mark.parametrize("job_status", ["failed", "blocked", "decommissioned"])
def test_detect_returns_true_for_failed_job_status(job_status: str):
    """Explicit failure on the work order triggers replacement semantics."""
    assert _detect_replacement_semantics(_pred_job(status=job_status), None) is True


def test_detect_returns_true_for_failed_job_status_case_insensitive():
    """Job-status checks are case-insensitive."""
    assert _detect_replacement_semantics(_pred_job(status="FAILED"), None) is True


@pytest.mark.parametrize("result_status", ["force_completed", "failed", "blocked", "error"])
def test_detect_returns_true_for_failure_result_status(result_status: str):
    """Failure marker in pred_execution.result.status triggers replacement.
    Covers the orchestrator force-completion path (status='force_completed')."""
    assert (
        _detect_replacement_semantics(_pred_job(status="complete"), _pred_execution(result_status=result_status))
        is True
    )


def test_detect_returns_true_for_failure_result_status_case_insensitive():
    """Result-status checks are case-insensitive."""
    assert (
        _detect_replacement_semantics(_pred_job(status="complete"), _pred_execution(result_status="FORCE_COMPLETED"))
        is True
    )


def test_detect_returns_false_for_unknown_result_status():
    """An unrecognized status string is not a replacement marker — chain stays safe default."""
    assert (
        _detect_replacement_semantics(
            _pred_job(status="complete"), _pred_execution(result_status="succeeded_with_warnings")
        )
        is False
    )


def test_detect_returns_false_when_both_signals_absent():
    """No pred_job AND no pred_execution -> chain (defensive default).
    In practice the caller validates pred_job exists before reaching here, but
    the helper is robust to defensive None inputs."""
    assert _detect_replacement_semantics(None, None) is False


# ---- Mode gating ----------------------------------------------------------


@pytest.mark.parametrize("subagent_mode", sorted(SUBAGENT_EXECUTION_MODES))
@pytest.mark.asyncio
async def test_subagent_mode_returns_mission_unchanged(
    service: JobLifecycleService, fake_repo_clean_completion: MagicMock, subagent_mode: str
) -> None:
    """In any subagent mode, the mission must come back byte-identical regardless
    of predecessor's status. The orchestrator's CLI already has the predecessor
    result in working context; splicing into mission text is the orchestrator's job."""
    original_mission = "Implement the new feature according to spec."
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission=original_mission,
        agent_display_name="implementer",
        execution_mode=subagent_mode,
    )
    assert result == original_mission


@pytest.mark.asyncio
async def test_multi_terminal_pre_execution_predecessor_injects_chain_preamble(
    service: JobLifecycleService, fake_repo_pre_execution: MagicMock
) -> None:
    """HO1023 regression: multi_terminal staging pre-spawns chains before any
    phase runs. The successor's preamble MUST be the chain flavor, not the
    replacement flavor that HO1022 incorrectly produced for this case."""
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Implement.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
    )
    assert "PRIOR PHASE OUTPUT" in result
    assert "continuing a workflow" in result
    # Wrong-semantics regression guard:
    assert "REPLACEMENT" not in result
    assert "replacing a previous agent" not in result


@pytest.mark.asyncio
async def test_multi_terminal_clean_completion_injects_chain_preamble(
    service: JobLifecycleService, fake_repo_clean_completion: MagicMock
) -> None:
    """Multi-terminal + completed predecessor (no failure status) → chain preamble."""
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Implement.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
    )
    assert "PRIOR PHASE OUTPUT" in result
    assert "REPLACEMENT" not in result


@pytest.mark.parametrize("job_status", ["failed", "blocked", "decommissioned"])
@pytest.mark.asyncio
async def test_multi_terminal_failed_job_injects_replacement_preamble(
    service: JobLifecycleService, monkeypatch, job_status: str
) -> None:
    """Multi-terminal + predecessor whose work-order is in a failure state
    → replacement preamble. Covers the reactivation-after-failure flow."""
    _install_repo(
        monkeypatch,
        pred_job=_pred_job(status=job_status),
        pred_execution=None,
    )
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Pick up.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
    )
    assert "REPLACEMENT" in result
    assert "PRIOR PHASE OUTPUT" not in result


@pytest.mark.parametrize("result_status", ["force_completed", "failed", "blocked", "error"])
@pytest.mark.asyncio
async def test_multi_terminal_force_completed_predecessor_injects_replacement_preamble(
    service: JobLifecycleService, monkeypatch, result_status: str
) -> None:
    """Multi-terminal + predecessor with failure marker on result.status
    → replacement preamble. Covers orchestrator force-completion path."""
    _install_repo(
        monkeypatch,
        pred_job=_pred_job(status="complete"),
        pred_execution=_pred_execution(result_status=result_status),
    )
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Pick up.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
    )
    assert "REPLACEMENT" in result


# ---- Validation runs even on skip path ------------------------------------


@pytest.mark.asyncio
async def test_predecessor_validated_even_when_subagent_skips(service: JobLifecycleService, monkeypatch) -> None:
    """A typo'd predecessor_job_id must raise ResourceNotFoundError even in the
    subagent skip path. Otherwise bad ids would silently pass."""
    _install_repo(monkeypatch, pred_job=None)
    with pytest.raises(ResourceNotFoundError):
        await service._build_predecessor_context(
            session=None,
            predecessor_job_id="bogus-id",
            tenant_key="tk-test",
            project_id="proj-1",
            mission="x",
            agent_display_name="impl",
            execution_mode="claude_code_cli",
        )


@pytest.mark.asyncio
async def test_cross_project_predecessor_rejected_even_when_subagent_skips(
    service: JobLifecycleService, monkeypatch
) -> None:
    """Cross-project predecessor_job_id must raise ValidationError even in the
    subagent skip path -- the same-project guard is a security boundary."""
    _install_repo(monkeypatch, pred_job=_pred_job(status="waiting", project_id="proj-OTHER"))
    with pytest.raises(ValidationError, match="different project"):
        await service._build_predecessor_context(
            session=None,
            predecessor_job_id="pred-x",
            tenant_key="tk-test",
            project_id="proj-1",
            mission="x",
            agent_display_name="impl",
            execution_mode="gemini_cli",
        )
