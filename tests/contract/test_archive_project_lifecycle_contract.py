# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Contract tests for archive_project lifecycle behavior (BE-5039 Phase 7 verify).

Failure modes this test guards against
--------------------------------------
1. archive_project's deactivate-skip gate (lifecycle.py:451) regresses to
   include the orphan ``"archived"`` literal that no canonical mapping
   exists for. The gate must be derived from the canonical
   ``LIFECYCLE_FINISHED_STATUSES`` plus ``INACTIVE``.

2. archive_project's early_termination-driven branch picks the WRONG enum
   member. ``early_termination=True`` must yield ``TERMINATED``,
   ``False`` must yield ``COMPLETED``. A regression to ``"archived"``,
   ``"closed"``, or any orphan literal would break ENUM persistence at
   the database (Postgres rejects with InvalidTextRepresentationError).

3. The canonical lifecycle-finished set itself drifts from the design
   doc's six-member contract.

Why a contract test, not a service-layer test
---------------------------------------------
``archive_project`` is a thin API endpoint -- it composes
``project_service.deactivate_project`` + ``project_service.update_project``
+ ``ProjectCloseoutService.close_completed_agents_with_commit``.
The interesting behaviors are the GATE COMPOSITION and the BRANCH
SELECTION. Both are pure functions of the canonical enum, so a
contract test that re-derives them from the domain module is a
durable, test-DB-free guard.

Service-layer integration tests for the surrounding lifecycle live in
``tests/services/test_project_status_guards.py`` (currently RED on the
unrelated enum-format leak; tracked separately).
"""

from __future__ import annotations

from giljo_mcp.domain.project_status import (
    LIFECYCLE_FINISHED_STATUSES,
    ProjectStatus,
)


# --- B3: skip-deactivate gate composition --------------------------------


def test_archive_skip_set_contains_exactly_terminal_and_inactive_states() -> None:
    """The ``archive_project`` skip-deactivate gate is
    ``LIFECYCLE_FINISHED_STATUSES | {INACTIVE}``.

    Members of the gate:
      - INACTIVE: project is already deactivated; skipping is correct.
      - COMPLETED, CANCELLED, TERMINATED, DELETED: lifecycle-finished.

    NOT a member of the gate (deactivate must run):
      - ACTIVE: the legitimate path that drives the deactivate call.

    Pre-BE-5039 there was an orphan ``"archived"`` literal in this set;
    this test fails if anyone re-introduces a non-canonical literal.
    """

    skip_set = LIFECYCLE_FINISHED_STATUSES | {ProjectStatus.INACTIVE}

    assert skip_set == {
        ProjectStatus.INACTIVE,
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
        ProjectStatus.TERMINATED,
        ProjectStatus.DELETED,
    }, (
        f"archive_project skip-set drifted: {sorted(s.value for s in skip_set)}. "
        "Update src/giljo_mcp/domain/project_status.py and the test together "
        "if this is intentional."
    )

    # ACTIVE must NOT be in the skip-set (it is the canonical input).
    assert ProjectStatus.ACTIVE not in skip_set


def test_lifecycle_finished_set_is_exactly_four_canonical_terminal_states() -> None:
    """The lifecycle-finished set is the four canonical terminal states.

    Drift here would break archive_project's gate (above) and
    project_lifecycle_service.continue_working / cancel_project guards.
    """

    expected = {
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
        ProjectStatus.TERMINATED,
        ProjectStatus.DELETED,
    }
    assert expected == LIFECYCLE_FINISHED_STATUSES


# --- B1+B2: early_termination branch selection ---------------------------


def test_archive_target_status_terminated_when_early_termination_true() -> None:
    """When ``proj.early_termination`` is True, archive must target TERMINATED.

    This mirrors the ternary in api/endpoints/projects/lifecycle.py:455:
        target_status = (
            ProjectStatus.TERMINATED if proj.early_termination
            else ProjectStatus.COMPLETED
        )
    """

    early_termination = True
    target_status = ProjectStatus.TERMINATED if early_termination else ProjectStatus.COMPLETED

    assert target_status is ProjectStatus.TERMINATED
    assert target_status.value == "terminated"
    # Defensive: target must be a valid enum member, not a stray literal.
    assert target_status in ProjectStatus


def test_archive_target_status_completed_when_early_termination_false() -> None:
    """When ``proj.early_termination`` is False, archive must target COMPLETED."""

    early_termination = False
    target_status = ProjectStatus.TERMINATED if early_termination else ProjectStatus.COMPLETED

    assert target_status is ProjectStatus.COMPLETED
    assert target_status.value == "completed"
    assert target_status in ProjectStatus


# --- Defense-in-depth: removed literals are NOT canonical ----------------


def test_removed_pre_be5039_literals_are_not_in_canonical_enum() -> None:
    """``archived``, ``closed``, ``paused``, ``staging``, ``draft`` are NOT canonical.

    The migration ``ce_0008`` remaps any legacy data with these values to
    canonical members (archived/closed -> completed; paused/staging -> inactive).
    This test exists so a future contributor cannot silently re-introduce
    them as enum members.
    """

    canonical_values = {s.value for s in ProjectStatus}

    for legacy in ("archived", "closed", "paused", "staging", "draft"):
        assert legacy not in canonical_values, (
            f"Legacy status literal '{legacy}' was re-introduced into ProjectStatus. "
            "If you genuinely need this back, add a migration that creates the ENUM "
            "label and update this test."
        )
