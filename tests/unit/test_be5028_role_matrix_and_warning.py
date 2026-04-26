# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""BE-5028 verification: orchestrator/worker authorization matrix + warning suppression.

Phase 1 commit `8b81cdb4` introduced:
- Fix A: removed the over-eager "360 memory has not been written" warning from
  ``JobCompletionService.complete_job``.
- Fix B: per-entry-type authorization gate in ``write_360_memory``.
- Fix C: protocol prose updates.

Phase 2 commit `54242353` extended the entry_type vocabulary so the gate is
fully exercised:
- Fix D: ``valid_entry_types`` admits 7 matrix values + ``handover_closeout``.
- Fix E/F/G: doc-string and prose sync.

These tests are TDD verification of the live behavior of those fixes. They are
designed to FAIL on a hypothetical revert (load-bearing, not tautological):

* Matrix tests assert the EXACT structured rejection dict -- if the gate is
  removed, the tests fail because no rejection is returned.
* Warning-suppression test asserts the absence of the legacy substrings -- if
  Fix A is reverted, those substrings reappear and the test fails.
* valid_entry_types tests assert frozenset MEMBERSHIP -- if Fix D is reverted,
  the new entry_types raise ValidationError and the tests fail.
* Tenant-isolation test creates an orchestrator job under tenant A, then calls
  write_360_memory under tenant B with the same author_job_id; the gate must
  reject because the cross-tenant lookup returns None -> caller_role="unknown".

Coverage map (mission section -> test):
  1. Matrix unit coverage (14 cases):  TestAuthorizationMatrix
  2. Structured rejection shape:       test_rejection_shape_*
  3. Caller-role resolution path:      test_caller_role_unknown_*,
                                       test_caller_role_lookup_uses_tenant_key
  4. Tenant isolation:                 test_cross_tenant_orchestrator_*
  5. Fix A regression:                 TestCompleteJobWarningSuppression
  6. valid_entry_types extension:      TestValidEntryTypeFrozenset
  7. Existing test compatibility:      run pytest -k selector (in CI), not in-file
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.job_completion_service import JobCompletionService
from giljo_mcp.tools.write_360_memory import (
    ORCHESTRATOR_ONLY_ENTRY_TYPES,
    WORKER_ALLOWED_ENTRY_TYPES,
    write_360_memory,
)


# ---- Fixtures --------------------------------------------------------------


@pytest_asyncio.fixture
async def linked_project(db_session, test_tenant_key, test_product):
    """Project linked to test_product (write_360_memory requires product link)."""
    project = Project(
        id=str(uuid.uuid4()),
        name="BE-5028 Verification Project",
        description="Project for matrix and warning-suppression verification",
        mission="Verify BE-5028 Phase 1 + Phase 2",
        status="active",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    return project


async def _make_agent_job(db_session, tenant_key: str, project_id: str, job_type: str) -> AgentJob:
    """Helper: create an AgentJob + AgentExecution for caller-role lookup."""
    job_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=project_id,
        mission=f"Test {job_type} mission",
        job_type=job_type,
        status="active",
        tenant_key=tenant_key,
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        id=str(uuid.uuid4()),
        job_id=job_id,
        tenant_key=tenant_key,
        agent_name=job_type,
        agent_display_name=job_type,
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.commit()
    return job


@pytest_asyncio.fixture
async def orchestrator_job(db_session, test_tenant_key, linked_project):
    return await _make_agent_job(db_session, test_tenant_key, linked_project.id, "orchestrator")


@pytest_asyncio.fixture
async def worker_job(db_session, test_tenant_key, linked_project):
    """An implementer-type job (not orchestrator) for worker-caller tests."""
    return await _make_agent_job(db_session, test_tenant_key, linked_project.id, "implementer")


def _mock_db_manager(db_session):
    """A db_manager whose ``get_session_async()`` yields the test session.

    Production code path uses ``async with db_manager.get_session_async() as s``
    when ``session=None``. Our tests pass ``session=db_session`` so the inner
    ``_provided_session`` branch is taken; db_manager only needs to exist for
    the ProductMemoryService construction.
    """
    mgr = MagicMock()
    mgr.get_session_async = MagicMock()
    mgr.get_session_async.return_value.__aenter__ = AsyncMock(return_value=db_session)
    mgr.get_session_async.return_value.__aexit__ = AsyncMock(return_value=False)
    return mgr


# ---- 1 + 2: Matrix coverage + structured rejection shape -------------------


# All 7 entry_types under matrix consideration, partitioned by allowed-role.
ALL_MATRIX_ENTRY_TYPES = sorted(WORKER_ALLOWED_ENTRY_TYPES | ORCHESTRATOR_ONLY_ENTRY_TYPES)
assert len(ALL_MATRIX_ENTRY_TYPES) == 7, "Matrix sanity: 4 worker + 3 orchestrator"


class TestAuthorizationMatrix:
    """14-case matrix: 7 entry_types x 2 caller roles (orchestrator, worker).

    Orchestrator caller: ALL seven entry_types pass the matrix gate (they may
    fail later gates -- CLOSEOUT_BLOCKED, GIT_COMMITS_REQUIRED -- but the
    matrix MUST NOT return ORCHESTRATOR_ONLY_ENTRY_TYPE).

    Worker caller: WORKER_ALLOWED pass; ORCHESTRATOR_ONLY are rejected with
    structured ORCHESTRATOR_ONLY_ENTRY_TYPE dict.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_type", ALL_MATRIX_ENTRY_TYPES)
    async def test_orchestrator_caller_passes_matrix_for_all_seven_types(
        self,
        entry_type,
        db_session,
        test_tenant_key,
        linked_project,
        orchestrator_job,
    ):
        """Orchestrator caller must NOT receive ORCHESTRATOR_ONLY_ENTRY_TYPE rejection."""
        mock_mgr = _mock_db_manager(db_session)
        # Bypass post-matrix gates so this test isolates the matrix decision.
        with (
            patch(
                "giljo_mcp.tools.write_360_memory._check_closeout_readiness",
                new=AsyncMock(return_value=(True, {})),
            ),
            patch(
                "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
                new_callable=AsyncMock,
            ),
            patch(
                "giljo_mcp.tools.write_360_memory.emit_websocket_event",
                new_callable=AsyncMock,
            ),
        ):
            result = await write_360_memory(
                project_id=str(linked_project.id),
                tenant_key=test_tenant_key,
                summary="Matrix verification headline.",
                key_outcomes=["k"],
                decisions_made=["d"],
                entry_type=entry_type,
                author_job_id=orchestrator_job.job_id,
                git_commits=[],
                tags=[],
                db_manager=mock_mgr,
                session=db_session,
            )
        # The matrix gate must NOT have rejected. result may be success or a
        # different structured failure (e.g., GIT_COMMITS_REQUIRED) but never
        # ORCHESTRATOR_ONLY_ENTRY_TYPE.
        assert isinstance(result, dict)
        assert result.get("error") != "ORCHESTRATOR_ONLY_ENTRY_TYPE", (
            f"Orchestrator should not be blocked from writing {entry_type!r}; got: {result}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_type", sorted(WORKER_ALLOWED_ENTRY_TYPES))
    async def test_worker_caller_passes_matrix_for_worker_allowed_types(
        self,
        entry_type,
        db_session,
        test_tenant_key,
        linked_project,
        worker_job,
    ):
        """Workers may write baseline/decision/architecture/discovery."""
        mock_mgr = _mock_db_manager(db_session)
        with (
            patch(
                "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
                new_callable=AsyncMock,
            ),
            patch(
                "giljo_mcp.tools.write_360_memory.emit_websocket_event",
                new_callable=AsyncMock,
            ),
        ):
            result = await write_360_memory(
                project_id=str(linked_project.id),
                tenant_key=test_tenant_key,
                summary="Worker-allowed entry headline.",
                key_outcomes=["k"],
                decisions_made=["d"],
                entry_type=entry_type,
                author_job_id=worker_job.job_id,
                git_commits=[],
                tags=[],
                db_manager=mock_mgr,
                session=db_session,
            )
        assert isinstance(result, dict)
        assert result.get("error") != "ORCHESTRATOR_ONLY_ENTRY_TYPE", (
            f"Worker must be allowed to write {entry_type!r}; got: {result}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_type", sorted(ORCHESTRATOR_ONLY_ENTRY_TYPES))
    async def test_worker_caller_rejected_for_orchestrator_only_types(
        self,
        entry_type,
        db_session,
        test_tenant_key,
        linked_project,
        worker_job,
    ):
        """Workers receive ORCHESTRATOR_ONLY_ENTRY_TYPE for closeout-shaped writes."""
        mock_mgr = _mock_db_manager(db_session)
        with patch(
            "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
            new_callable=AsyncMock,
        ):
            result = await write_360_memory(
                project_id=str(linked_project.id),
                tenant_key=test_tenant_key,
                summary="Worker attempting closeout-shaped write.",
                key_outcomes=["k"],
                decisions_made=["d"],
                entry_type=entry_type,
                author_job_id=worker_job.job_id,
                git_commits=[],
                tags=[],
                db_manager=mock_mgr,
                session=db_session,
            )
        assert result["success"] is False
        assert result["error"] == "ORCHESTRATOR_ONLY_ENTRY_TYPE"
        assert result["entry_type"] == entry_type
        assert result["calling_agent_role"] == "implementer"


# ---- Structured rejection shape (mission section 2) ------------------------


@pytest.mark.asyncio
async def test_rejection_shape_has_all_required_keys(db_session, test_tenant_key, linked_project, worker_job):
    """Structured rejection dict has the EXACT contract the orchestrator relies on."""
    mock_mgr = _mock_db_manager(db_session)
    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="shape test",
            key_outcomes=["k"],
            decisions_made=["d"],
            entry_type="project_completion",
            author_job_id=worker_job.job_id,
            git_commits=[],
            tags=[],
            db_manager=mock_mgr,
            session=db_session,
        )

    # Required keys per mission contract:
    expected_keys = {
        "success",
        "error",
        "entry_type",
        "calling_agent_role",
        "message",
        "allowed_for_workers",
    }
    assert expected_keys.issubset(result.keys()), f"Missing keys in rejection: {expected_keys - set(result.keys())}"

    assert result["success"] is False
    assert result["error"] == "ORCHESTRATOR_ONLY_ENTRY_TYPE"
    assert result["entry_type"] == "project_completion"
    assert result["calling_agent_role"] == "implementer"
    # Non-empty human-readable message
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0
    # allowed_for_workers must be a sorted list matching the constant
    assert isinstance(result["allowed_for_workers"], list)
    assert result["allowed_for_workers"] == sorted(WORKER_ALLOWED_ENTRY_TYPES)


@pytest.mark.asyncio
async def test_rejection_does_not_raise_exception(db_session, test_tenant_key, linked_project, worker_job):
    """MCP boundary contract: structured dict return, never raise."""
    mock_mgr = _mock_db_manager(db_session)
    # No pytest.raises -- the call must complete normally.
    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="no exception",
            key_outcomes=["k"],
            decisions_made=["d"],
            entry_type="session_handover",
            author_job_id=worker_job.job_id,
            git_commits=[],
            tags=[],
            db_manager=mock_mgr,
            session=db_session,
        )
    assert result["error"] == "ORCHESTRATOR_ONLY_ENTRY_TYPE"


# ---- 3: Caller-role resolution path ---------------------------------------


@pytest.mark.asyncio
async def test_caller_role_unknown_when_job_lookup_returns_none(db_session, test_tenant_key, linked_project):
    """Bogus author_job_id -> caller_role='unknown' -> rejected for orchestrator-only."""
    mock_mgr = _mock_db_manager(db_session)
    bogus_job_id = str(uuid.uuid4())  # not persisted
    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="unknown caller",
            key_outcomes=["k"],
            decisions_made=["d"],
            entry_type="action_required",
            author_job_id=bogus_job_id,
            git_commits=[],
            tags=[],
            db_manager=mock_mgr,
            session=db_session,
        )
    assert result["success"] is False
    assert result["error"] == "ORCHESTRATOR_ONLY_ENTRY_TYPE"
    assert result["calling_agent_role"] == "unknown"


@pytest.mark.asyncio
async def test_caller_role_lookup_uses_tenant_key(db_session, test_tenant_key, linked_project, orchestrator_job):
    """get_agent_job_by_job_id is called with the request's tenant_key."""
    mock_mgr = _mock_db_manager(db_session)
    with (
        patch("giljo_mcp.tools.write_360_memory.AgentCompletionRepository") as mock_repo_cls,
        patch(
            "giljo_mcp.tools.write_360_memory._check_closeout_readiness",
            new=AsyncMock(return_value=(True, {})),
        ),
        patch(
            "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
            new_callable=AsyncMock,
        ),
        patch(
            "giljo_mcp.tools.write_360_memory.emit_websocket_event",
            new_callable=AsyncMock,
        ),
    ):
        mock_repo = MagicMock()
        mock_repo.get_agent_job_by_job_id = AsyncMock(return_value=orchestrator_job)
        mock_repo_cls.return_value = mock_repo

        await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="tenant-key-lookup verification",
            key_outcomes=["k"],
            decisions_made=["d"],
            entry_type="project_completion",
            author_job_id=orchestrator_job.job_id,
            git_commits=[],
            tags=[],
            db_manager=mock_mgr,
            session=db_session,
        )

        # Lookup must be called with this request's tenant_key + author_job_id.
        mock_repo.get_agent_job_by_job_id.assert_awaited()
        # Repository signature: (session, tenant_key, author_job_id) -> AgentJob | None
        call_args = mock_repo.get_agent_job_by_job_id.await_args
        assert call_args.args[1] == test_tenant_key
        assert call_args.args[2] == orchestrator_job.job_id


# ---- 4: Tenant isolation --------------------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_orchestrator_cannot_authorize_write_in_another_tenant(
    db_session, test_tenant_key, test_product
):
    """Orchestrator job under tenant A cannot authorize a write under tenant B.

    Setup:
        tenant A: orchestrator job with job_id X.
        tenant B: project. Caller calls write_360_memory(tenant_key=B,
                  author_job_id=X) -- attempting to spoof orchestrator role.

    Expectation:
        get_agent_job_by_job_id(session, tenant_B, X) returns None because
        of the tenant_key=tenant_B filter -> caller_role='unknown' -> matrix
        rejects. No data leakage.
    """
    # Tenant A: orchestrator job.
    tenant_a = test_tenant_key
    project_a = Project(
        id=str(uuid.uuid4()),
        name="Tenant A project",
        description="x",
        mission="x",
        status="active",
        tenant_key=tenant_a,
        product_id=test_product.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project_a)
    await db_session.commit()

    orch_job_a = await _make_agent_job(db_session, tenant_a, project_a.id, "orchestrator")

    # Tenant B: separate tenant + project + product.
    from giljo_mcp.models import Product

    tenant_b = "tk_isolated_other_tenant_" + uuid.uuid4().hex[:8]
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Tenant B product",
        description="x",
        tenant_key=tenant_b,
        is_active=True,
        product_memory={},
    )
    db_session.add(product_b)
    project_b = Project(
        id=str(uuid.uuid4()),
        name="Tenant B project",
        description="x",
        mission="x",
        status="active",
        tenant_key=tenant_b,
        product_id=product_b.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project_b)
    await db_session.commit()

    mock_mgr = _mock_db_manager(db_session)
    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(project_b.id),
            tenant_key=tenant_b,  # request as tenant B
            summary="cross-tenant spoofing attempt",
            key_outcomes=["k"],
            decisions_made=["d"],
            entry_type="project_completion",
            author_job_id=orch_job_a.job_id,  # job belongs to tenant A
            git_commits=[],
            tags=[],
            db_manager=mock_mgr,
            session=db_session,
        )

    assert result["success"] is False
    assert result["error"] == "ORCHESTRATOR_ONLY_ENTRY_TYPE"
    # Critical: the cross-tenant lookup returned None, so role is 'unknown',
    # NOT 'orchestrator'. If this assertion fails, tenant isolation is broken.
    assert result["calling_agent_role"] == "unknown"


# ---- 5: Fix A regression -- complete_job warning suppression ---------------


class TestCompleteJobWarningSuppression:
    """Fix A: the legacy '360 memory has not been written' warning is gone.

    Setup: orchestrator job in a project with NO 360 memory entries.
    Call: complete_job() for that orchestrator job.
    Assert:
        - response does NOT mention '360 memory has not been written'
        - response does NOT mention 'the closeout is incomplete'
        - response DOES still include closeout_checklist
    """

    @pytest.fixture
    def completion_service(self, db_session, test_tenant_key):
        db_manager = MagicMock()
        tenant_manager = MagicMock()
        tenant_manager.get_current_tenant.return_value = test_tenant_key
        return JobCompletionService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

    @pytest.mark.asyncio
    async def test_complete_job_does_not_emit_legacy_360_memory_warning(
        self, completion_service, db_session, test_tenant_key, linked_project
    ):
        # Build orchestrator job WITHOUT any 360 memory entries on the project.
        orch = await _make_agent_job(db_session, test_tenant_key, linked_project.id, "orchestrator")

        result = await completion_service.complete_job(
            job_id=orch.job_id,
            result={"summary": "Verification of warning suppression."},
            tenant_key=test_tenant_key,
        )

        # Serialize the warnings list and the response object for substring scan.
        # Fix A removed the warning emission entirely; verify it stays gone.
        flat_warnings = " ".join(getattr(result, "warnings", []) or [])
        assert "360 memory has not been written" not in flat_warnings, (
            "Fix A regression: legacy 360 memory warning has reappeared."
        )
        assert "the closeout is incomplete" not in flat_warnings, (
            "Fix A regression: 'closeout is incomplete' wording has reappeared."
        )

        # Existing behavior preserved: closeout_checklist is still attached for
        # orchestrator jobs.
        assert getattr(result, "closeout_checklist", None) is not None


# ---- 6: valid_entry_types extension ---------------------------------------


class TestValidEntryTypeFrozenset:
    """Fix D: frozenset admits all 7 matrix values + handover_closeout (back-compat)."""

    EXPECTED_ADMITTED: ClassVar[set[str]] = {
        "project_completion",
        "handover_closeout",
        "session_handover",
        "action_required",
        "baseline",
        "decision",
        "architecture",
        "discovery",
    }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("entry_type", sorted(EXPECTED_ADMITTED))
    async def test_admits_all_eight_canonical_entry_types(
        self,
        entry_type,
        db_session,
        test_tenant_key,
        linked_project,
        orchestrator_job,
    ):
        """Each canonical entry_type passes the valid_entry_types validator.

        We use an orchestrator caller so the matrix gate also passes; if Fix D
        is reverted, write_360_memory raises ValidationError on the new types
        (decision/architecture/discovery/baseline/action_required) BEFORE
        reaching the matrix gate, and this test fails.
        """
        mock_mgr = _mock_db_manager(db_session)
        with (
            patch(
                "giljo_mcp.tools.write_360_memory._check_closeout_readiness",
                new=AsyncMock(return_value=(True, {})),
            ),
            patch(
                "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
                new_callable=AsyncMock,
            ),
            patch(
                "giljo_mcp.tools.write_360_memory.emit_websocket_event",
                new_callable=AsyncMock,
            ),
        ):
            # Must not raise ValidationError("Invalid entry_type ...").
            try:
                result = await write_360_memory(
                    project_id=str(linked_project.id),
                    tenant_key=test_tenant_key,
                    summary=f"vocab test for {entry_type}",
                    key_outcomes=["k"],
                    decisions_made=["d"],
                    entry_type=entry_type,
                    author_job_id=orchestrator_job.job_id,
                    git_commits=[],
                    tags=[],
                    db_manager=mock_mgr,
                    session=db_session,
                )
            except ValidationError as e:
                pytest.fail(f"valid_entry_types regression: {entry_type!r} raised ValidationError: {e}")
            # And the matrix gate didn't bite an orchestrator either.
            assert result.get("error") != "ORCHESTRATOR_ONLY_ENTRY_TYPE"

    @pytest.mark.asyncio
    async def test_typo_entry_type_still_raises_validation_error(
        self, db_session, test_tenant_key, linked_project, orchestrator_job
    ):
        """Frozenset is still load-bearing for typo detection (e.g., 'desicion')."""
        mock_mgr = _mock_db_manager(db_session)
        with (
            patch(
                "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
                new_callable=AsyncMock,
            ),
            pytest.raises(ValidationError) as exc_info,
        ):
            await write_360_memory(
                project_id=str(linked_project.id),
                tenant_key=test_tenant_key,
                summary="typo test",
                key_outcomes=["k"],
                decisions_made=["d"],
                entry_type="desicion",  # typo of 'decision'
                author_job_id=orchestrator_job.job_id,
                git_commits=[],
                tags=[],
                db_manager=mock_mgr,
                session=db_session,
            )
        assert "Invalid entry_type" in str(exc_info.value)
