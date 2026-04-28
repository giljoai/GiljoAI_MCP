# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
HO1022: predecessor_job_id is mode-gated; chain vs replacement is auto-detected.

Background
----------
Pre-HO1021, _build_predecessor_context auto-prepended a single replacement-
flavored preamble ("you are replacing a previous agent... fix the issues") to
ANY successor spawned with predecessor_job_id. Wrong semantics for forward
chains, redundant in subagent modes (CLI returns predecessor inline).

HO1021 added a `predecessor_role` parameter so callers could pick chain vs
replacement -- but that pushed mode-awareness onto the orchestrator and asked
it to tell the server something the server can already detect.

HO1022 (this) reverts to two-mode design:
  - subagent_*    : server NEVER injects a preamble
  - multi_terminal: server injects, auto-picks chain vs replacement from
                    predecessor's completion record (pred_execution.result.status)

Predecessor existence + same-project validation still runs in the skip path
(catches typo'd predecessor_job_id even when no preamble would be rendered).
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


def _clean_pred_execution(result_status: str | None = None):
    """Build a SimpleNamespace mirroring AgentExecution shape with optional result.status."""
    result = {"summary": "Analysis complete.", "commits": ["c1", "c2"]}
    if result_status is not None:
        result["status"] = result_status
    return SimpleNamespace(agent_display_name="analyzer", result=result)


@pytest.fixture
def fake_repo_clean(monkeypatch) -> MagicMock:
    """Default: predecessor exists in same project, completed cleanly (no result.status)."""
    return _install_repo(
        monkeypatch,
        pred_job=SimpleNamespace(project_id="proj-1"),
        pred_execution=_clean_pred_execution(),
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


# ---- Auto-detection helper ------------------------------------------------


def test_detect_replacement_returns_true_when_pred_execution_is_none():
    """Predecessor never reached complete_job → almost certainly a replacement spawn."""
    assert _detect_replacement_semantics(None) is True


def test_detect_replacement_returns_false_for_clean_completion():
    """No status field on the result dict → clean completion → chain."""
    assert _detect_replacement_semantics(_clean_pred_execution()) is False


@pytest.mark.parametrize("status", ["force_completed", "failed", "blocked", "error"])
def test_detect_replacement_returns_true_for_failure_statuses(status: str):
    """Each documented failure marker triggers replacement semantics."""
    assert _detect_replacement_semantics(_clean_pred_execution(status)) is True


def test_detect_replacement_is_case_insensitive_on_status():
    """status='FORCE_COMPLETED' matches the lowercase replacement marker set."""
    assert _detect_replacement_semantics(_clean_pred_execution("FORCE_COMPLETED")) is True


def test_detect_replacement_returns_false_for_unknown_status():
    """An unrecognized status string is not a replacement marker — chain stays safe default."""
    assert _detect_replacement_semantics(_clean_pred_execution("succeeded_with_warnings")) is False


# ---- Mode gating ----------------------------------------------------------


@pytest.mark.parametrize("subagent_mode", sorted(SUBAGENT_EXECUTION_MODES))
@pytest.mark.asyncio
async def test_subagent_mode_returns_mission_unchanged(
    service: JobLifecycleService, fake_repo_clean: MagicMock, subagent_mode: str
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
async def test_multi_terminal_clean_predecessor_injects_chain_preamble(
    service: JobLifecycleService, fake_repo_clean: MagicMock
) -> None:
    """Multi-terminal + clean predecessor (no failure status) → chain preamble."""
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


@pytest.mark.parametrize("status", ["force_completed", "failed", "blocked", "error"])
@pytest.mark.asyncio
async def test_multi_terminal_failed_predecessor_injects_replacement_preamble(
    service: JobLifecycleService, monkeypatch, status: str
) -> None:
    """Multi-terminal + predecessor with failure marker → replacement preamble."""
    _install_repo(
        monkeypatch,
        pred_job=SimpleNamespace(project_id="proj-1"),
        pred_execution=_clean_pred_execution(status),
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


@pytest.mark.asyncio
async def test_multi_terminal_missing_pred_execution_injects_replacement_preamble(
    service: JobLifecycleService, monkeypatch
) -> None:
    """Predecessor never reached complete_job → replacement (orchestrator is
    almost certainly spawning a replacement for a failed agent)."""
    _install_repo(
        monkeypatch,
        pred_job=SimpleNamespace(project_id="proj-1"),
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


# ---- Validation runs even on skip path ------------------------------------


@pytest.mark.asyncio
async def test_predecessor_validated_even_when_subagent_skips(service: JobLifecycleService, monkeypatch) -> None:
    """A typo'd predecessor_job_id must raise ResourceNotFoundError even in the
    subagent skip path. Otherwise bad ids would silently pass."""
    _install_repo(monkeypatch, pred_job=None)  # predecessor not found
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
    _install_repo(monkeypatch, pred_job=SimpleNamespace(project_id="proj-OTHER"))
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
