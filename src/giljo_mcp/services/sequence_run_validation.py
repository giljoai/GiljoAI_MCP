# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SequenceRun write-boundary validation helpers (extracted from the service).

Pure, membership/length validation of the enum-like and capped fields before any
DB write, raising ValidationError (-> 422) rather than letting a DB constraint
produce a 500. Extracted to keep ``sequence_run_service.py`` under the 800-line CI
guardrail (BE-6185), mirroring the ``sequence_run_serialization.py`` extraction.
Internal; the owning service is the only caller.

Edition Scope: CE.
"""

from __future__ import annotations

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.sequence_runs import (
    ACCEPTED_EXECUTION_MODES,
    MAX_SEQUENCE_PROJECTS,
    VALID_EXECUTION_MODES,
    VALID_PROJECT_STATUSES,
    VALID_REVIEW_POLICIES,
    VALID_RUN_STATUSES,
)
from giljo_mcp.schemas.jsonb_validators import (
    validate_sequence_run_project_ids,
    validate_sequence_run_project_statuses,
)


# BE-6185: hard cap on the conductor-owned chain mission text, enforced at the
# write boundary so an over-cap value raises ValidationError (-> 422) rather than
# letting the DB produce a 500.
MAX_CHAIN_MISSION_CHARS: int = 100_000


def _validate_project_statuses(project_statuses: dict[str, str]) -> None:
    for pid, ps in project_statuses.items():
        if ps not in VALID_PROJECT_STATUSES:
            raise ValidationError(
                message=f"Invalid project status {ps!r} for project {pid!r}. Valid: {sorted(VALID_PROJECT_STATUSES)}",
                context={"field": "project_statuses", "project_id": pid, "valid": sorted(VALID_PROJECT_STATUSES)},
            )


def validate_create_fields(
    *,
    project_ids: list[str],
    execution_mode: str,
    status: str,
    review_policy: str,
    project_statuses: dict[str, str],
) -> None:
    """Membership-validate all enum-like fields before touching the DB (create path)."""
    if not project_ids:
        raise ValidationError(
            message="project_ids must be a non-empty list",
            context={"field": "project_ids"},
        )
    if len(project_ids) > MAX_SEQUENCE_PROJECTS:
        raise ValidationError(
            message=f"project_ids exceeds maximum of {MAX_SEQUENCE_PROJECTS} projects (got {len(project_ids)})",
            context={"field": "project_ids", "max": MAX_SEQUENCE_PROJECTS},
        )
    if execution_mode not in ACCEPTED_EXECUTION_MODES:
        raise ValidationError(
            message=f"Invalid execution_mode {execution_mode!r}. Valid: {sorted(VALID_EXECUTION_MODES)}",
            context={"field": "execution_mode", "valid": sorted(VALID_EXECUTION_MODES)},
        )
    if status not in VALID_RUN_STATUSES:
        raise ValidationError(
            message=f"Invalid status {status!r}. Valid: {sorted(VALID_RUN_STATUSES)}",
            context={"field": "status", "valid": sorted(VALID_RUN_STATUSES)},
        )
    if review_policy not in VALID_REVIEW_POLICIES:
        raise ValidationError(
            message=f"Invalid review_policy {review_policy!r}. Valid: {sorted(VALID_REVIEW_POLICIES)}",
            context={"field": "review_policy", "valid": sorted(VALID_REVIEW_POLICIES)},
        )
    _validate_project_statuses(project_statuses)


def validate_update_fields(
    *,
    status: str | None,
    review_policy: str | None,
    current_index: int | None,
    execution_mode: str | None,
    chain_mission: str | None,
    resolved_order: list[str] | None,
    project_statuses: dict[str, str] | None,
) -> tuple[list[str] | None, dict[str, str] | None]:
    """Membership/length-validate the optional update fields (partial-update path).

    Returns the normalized ``(resolved_order, project_statuses)`` (JSONB-validated
    when provided, else passed through as None). Raises ValidationError (-> 422) on
    any invalid value.
    """
    if status is not None and status not in VALID_RUN_STATUSES:
        raise ValidationError(
            message=f"Invalid status {status!r}. Valid: {sorted(VALID_RUN_STATUSES)}",
            context={"field": "status", "valid": sorted(VALID_RUN_STATUSES)},
        )
    if review_policy is not None and review_policy not in VALID_REVIEW_POLICIES:
        raise ValidationError(
            message=f"Invalid review_policy {review_policy!r}. Valid: {sorted(VALID_REVIEW_POLICIES)}",
            context={"field": "review_policy", "valid": sorted(VALID_REVIEW_POLICIES)},
        )
    if current_index is not None and current_index < 0:
        raise ValidationError(
            message="current_index must be >= 0",
            context={"field": "current_index"},
        )
    if execution_mode is not None and execution_mode not in ACCEPTED_EXECUTION_MODES:
        raise ValidationError(
            message=f"Invalid execution_mode {execution_mode!r}. Valid: {sorted(VALID_EXECUTION_MODES)}",
            context={"field": "execution_mode", "valid": sorted(VALID_EXECUTION_MODES)},
        )
    if chain_mission is not None:
        if not isinstance(chain_mission, str):
            raise ValidationError(
                message="chain_mission must be a string",
                context={"field": "chain_mission"},
            )
        if len(chain_mission) > MAX_CHAIN_MISSION_CHARS:
            raise ValidationError(
                message=(
                    f"chain_mission exceeds maximum of {MAX_CHAIN_MISSION_CHARS} characters (got {len(chain_mission)})"
                ),
                context={"field": "chain_mission", "max": MAX_CHAIN_MISSION_CHARS},
            )
    if resolved_order is not None:
        resolved_order = validate_sequence_run_project_ids(resolved_order)
    if project_statuses is not None:
        _validate_project_statuses(project_statuses)
        project_statuses = validate_sequence_run_project_statuses(project_statuses)
    return resolved_order, project_statuses
