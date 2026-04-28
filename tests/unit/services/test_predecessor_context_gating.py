# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
HO1021: predecessor_job_id is now mode + role aware.

Background
----------
Pre-HO1021, _build_predecessor_context auto-prepended a single replacement-flavored
preamble ("you are replacing a previous agent... fix the issues") to ANY successor
spawned with predecessor_job_id. Two problems:

1. Wrong semantics for forward chains. A healthy analyzer -> implementer chain is
   not "issues were found, fix them" — the predecessor succeeded and the successor
   is consuming its output as designed.
2. No mode gate. In subagent execution modes (claude_code_cli / codex_cli /
   gemini_cli) the orchestrator's CLI returns the predecessor result inline via
   Task() / spawn_agent() / @-syntax, so a server-injected preamble is redundant
   (and wrong-semantics) for chain handoffs.

HO1021 fix
----------
- Add `predecessor_role` parameter ("chain" | "replacement", default "chain") to
  spawn_job and threaded down to _build_predecessor_context.
- Add `execution_mode` parameter (read from project.execution_mode at the
  spawn_job call site) so the gating decision can be made.
- Decision matrix:
    multi_terminal + chain        -> inject CHAIN preamble
    multi_terminal + replacement  -> inject REPLACEMENT preamble
    subagent_*     + chain        -> NO preamble (orchestrator splices inline)
    subagent_*     + replacement  -> inject REPLACEMENT preamble
- Preamble templates moved to module constants so they can be unit-asserted
  without DB access.
- Predecessor existence + same-project validation still runs in the skip path
  (catches typo'd predecessor_job_id even when no preamble would be injected).

Tests cover: module constants shape, all four cells of the decision matrix, role
validation, and predecessor-validation-runs-even-on-skip.
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
    VALID_PREDECESSOR_ROLES,
)
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService


# ---- Fixtures -------------------------------------------------------------


@pytest.fixture
def service() -> JobLifecycleService:
    """Build a JobLifecycleService with mocked dependencies (no DB / tenant manager)."""
    return JobLifecycleService(db_manager=MagicMock(), tenant_manager=MagicMock())


def _install_repo(monkeypatch, *, pred_job, pred_execution=None) -> MagicMock:
    """Patch AgentCompletionRepository at the import site to return given fakes.

    Returns the repo INSTANCE mock so individual tests can assert call counts if needed.
    """
    repo_instance = MagicMock()
    repo_instance.get_predecessor_job = AsyncMock(return_value=pred_job)
    repo_instance.get_completed_execution_for_job = AsyncMock(return_value=pred_execution)
    monkeypatch.setattr(
        "giljo_mcp.services.job_lifecycle_service.AgentCompletionRepository",
        MagicMock(return_value=repo_instance),
    )
    return repo_instance


@pytest.fixture
def fake_repo(monkeypatch) -> MagicMock:
    """Default: predecessor exists in the same project, with a clean completion result."""
    pred_job = SimpleNamespace(project_id="proj-1")
    pred_execution = SimpleNamespace(
        agent_display_name="analyzer",
        result={"summary": "Analysis complete.", "commits": ["c1", "c2"]},
    )
    return _install_repo(monkeypatch, pred_job=pred_job, pred_execution=pred_execution)


# ---- Module-level constants -----------------------------------------------


def test_subagent_execution_modes_set_is_exactly_the_three_clis():
    """If a new subagent CLI is added, this set must be updated explicitly.

    Hard-coding the membership in the test (rather than asserting len) prevents
    accidental drift like 'multi_terminal' creeping into the subagent set.
    """
    assert frozenset({"claude_code_cli", "codex_cli", "gemini_cli"}) == SUBAGENT_EXECUTION_MODES


def test_multi_terminal_is_not_a_subagent_mode():
    """multi_terminal MUST always inject the chain preamble — separate processes
    cannot share a Task() return value across terminals."""
    assert "multi_terminal" not in SUBAGENT_EXECUTION_MODES


def test_valid_predecessor_roles_are_chain_and_replacement():
    assert frozenset({"chain", "replacement"}) == VALID_PREDECESSOR_ROLES


def test_chain_preamble_uses_forward_handoff_language():
    """Chain preamble must NOT use replacement / failure language."""
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
    never appear in agent-facing prose. Pre-HO1021 the legacy preamble had a
    `tenant_key="{tenant_key}"` arg in its example get_agent_result call."""
    assert "tenant_key" not in PREDECESSOR_CHAIN_PREAMBLE
    assert "tenant_key" not in PREDECESSOR_REPLACEMENT_PREAMBLE


# ---- Decision matrix: subagent + chain = SKIP -----------------------------


@pytest.mark.parametrize("subagent_mode", sorted(SUBAGENT_EXECUTION_MODES))
@pytest.mark.asyncio
async def test_subagent_chain_returns_mission_unchanged(
    service: JobLifecycleService, fake_repo: MagicMock, subagent_mode: str
) -> None:
    """In any subagent mode + chain role, the mission must come back byte-identical.

    The orchestrator's CLI already has the predecessor result in working context;
    splicing into mission text is the orchestrator's job, not the server's.
    """
    original_mission = "Implement the new feature according to spec."
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission=original_mission,
        agent_display_name="implementer",
        execution_mode=subagent_mode,
        predecessor_role="chain",
    )
    assert result == original_mission


# ---- Decision matrix: subagent + replacement = INJECT replacement ---------


@pytest.mark.parametrize("subagent_mode", sorted(SUBAGENT_EXECUTION_MODES))
@pytest.mark.asyncio
async def test_subagent_replacement_injects_replacement_preamble(
    service: JobLifecycleService, fake_repo: MagicMock, subagent_mode: str
) -> None:
    """Replacement always injects, even in subagent modes — a failed Task()
    subagent being respawned legitimately needs the replacement framing."""
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Pick up where they left off.",
        agent_display_name="implementer",
        execution_mode=subagent_mode,
        predecessor_role="replacement",
    )
    assert "REPLACEMENT" in result
    assert "taking over" in result
    assert "Pick up where they left off." in result  # original mission preserved


# ---- Decision matrix: multi_terminal + chain = INJECT chain --------------


@pytest.mark.asyncio
async def test_multi_terminal_chain_injects_chain_preamble(service: JobLifecycleService, fake_repo: MagicMock) -> None:
    """Multi-terminal chains MUST inject chain-flavored preamble (not replacement).

    Each terminal is isolated; without a server-injected preamble the successor
    has no inherent way to see the predecessor's output.
    """
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Implement.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
        predecessor_role="chain",
    )
    assert "PRIOR PHASE OUTPUT" in result
    assert "continuing a workflow" in result
    # Wrong-semantics regression guard:
    assert "REPLACEMENT" not in result
    assert "replacing a previous agent" not in result


# ---- Decision matrix: multi_terminal + replacement = INJECT replacement --


@pytest.mark.asyncio
async def test_multi_terminal_replacement_injects_replacement_preamble(
    service: JobLifecycleService, fake_repo: MagicMock
) -> None:
    result = await service._build_predecessor_context(
        session=None,
        predecessor_job_id="pred-1",
        tenant_key="tk-test",
        project_id="proj-1",
        mission="Pick up.",
        agent_display_name="implementer",
        execution_mode="multi_terminal",
        predecessor_role="replacement",
    )
    assert "REPLACEMENT" in result
    assert "PRIOR PHASE OUTPUT" not in result


# ---- Role validation ------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_predecessor_role_raises_validation_error(
    service: JobLifecycleService, fake_repo: MagicMock
) -> None:
    with pytest.raises(ValidationError, match="Invalid predecessor_role"):
        await service._build_predecessor_context(
            session=None,
            predecessor_job_id="pred-1",
            tenant_key="tk-test",
            project_id="proj-1",
            mission="x",
            agent_display_name="impl",
            execution_mode="multi_terminal",
            predecessor_role="bogus",
        )


# ---- Validation runs even on skip path (catches typo'd predecessor_job_id) -


@pytest.mark.asyncio
async def test_predecessor_validated_even_when_subagent_chain_skips(service: JobLifecycleService, monkeypatch) -> None:
    """A typo'd predecessor_job_id must raise ResourceNotFoundError even in the
    subagent+chain skip path. Otherwise bad ids would silently pass."""
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
            predecessor_role="chain",
        )


@pytest.mark.asyncio
async def test_cross_project_predecessor_rejected_even_when_subagent_chain_skips(
    service: JobLifecycleService, monkeypatch
) -> None:
    """Cross-project predecessor_job_id must raise ValidationError even in the
    subagent+chain skip path — the same-project guard is a security boundary."""
    pred_job_other_project = SimpleNamespace(project_id="proj-OTHER")
    _install_repo(monkeypatch, pred_job=pred_job_other_project)
    with pytest.raises(ValidationError, match="different project"):
        await service._build_predecessor_context(
            session=None,
            predecessor_job_id="pred-x",
            tenant_key="tk-test",
            project_id="proj-1",
            mission="x",
            agent_display_name="impl",
            execution_mode="gemini_cli",
            predecessor_role="chain",
        )
