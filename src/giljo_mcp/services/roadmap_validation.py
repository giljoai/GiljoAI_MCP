# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Roadmap input-validation boundary (extracted from RoadmapService, IMP-6044).

Pure, DB-free validation for the Roadmapping Pane write tools. These functions
run BEFORE any DB write so a malformed agent payload raises ValidationError
(→ 422) at the boundary rather than tripping a DB constraint as a 500 — the
"no unvalidated agent input → DB" discipline (mirrors jsonb_validators.py).

No session, no tenant, no I/O: every function is a deterministic transform from
raw payload to a normalized list (or raises). Kept separate from RoadmapService
so the validation contract is independently testable and the service stays
focused on DB orchestration.

Edition Scope: CE.
"""

from typing import Any

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.roadmaps import (
    MAX_BLOCKED_REASON_LEN,
    MAX_ROADMAP_SORT_ORDER,
    VALID_ROADMAP_COMPLEXITIES,
    VALID_ROADMAP_ITEM_TYPES,
    VALID_ROADMAP_RISKS,
)


def validate_items(items: Any) -> list[dict[str, Any]]:
    """Validate + normalize a list of roadmap-item payloads.

    Raises ValidationError (→ 422) on any membership / type / range failure
    so a malformed agent payload never reaches a DB constraint as a 500.
    """
    if not isinstance(items, list):
        raise ValidationError(
            message="items must be a list of roadmap-item objects",
            context={"operation": "upsert_roadmap_items"},
        )

    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValidationError(
                message=f"items[{idx}] must be an object",
                context={"operation": "upsert_roadmap_items"},
            )

        item_type = raw.get("item_type")
        if item_type not in VALID_ROADMAP_ITEM_TYPES:
            raise ValidationError(
                message=(f"items[{idx}].item_type '{item_type}' invalid. Valid: {sorted(VALID_ROADMAP_ITEM_TYPES)}"),
                context={"operation": "upsert_roadmap_items", "valid_item_types": sorted(VALID_ROADMAP_ITEM_TYPES)},
            )

        project_id = raw.get("project_id") or None
        task_id = raw.get("task_id") or None
        if item_type == "project":
            if not project_id:
                raise ValidationError(
                    message=f"items[{idx}] item_type=project requires project_id",
                    context={"operation": "upsert_roadmap_items"},
                )
            task_id = None
        else:  # task
            if not task_id:
                raise ValidationError(
                    message=f"items[{idx}] item_type=task requires task_id",
                    context={"operation": "upsert_roadmap_items"},
                )
            project_id = None

        sort_order = validate_sort_order(raw.get("sort_order", 0), idx)

        risk = raw.get("risk") or None
        if risk is not None and risk not in VALID_ROADMAP_RISKS:
            raise ValidationError(
                message=f"items[{idx}].risk '{risk}' invalid. Valid: {sorted(VALID_ROADMAP_RISKS)}",
                context={"operation": "upsert_roadmap_items", "valid_risks": sorted(VALID_ROADMAP_RISKS)},
            )

        complexity = raw.get("complexity") or None
        if complexity is not None and complexity not in VALID_ROADMAP_COMPLEXITIES:
            raise ValidationError(
                message=(
                    f"items[{idx}].complexity '{complexity}' invalid. Valid: {sorted(VALID_ROADMAP_COMPLEXITIES)}"
                ),
                context={
                    "operation": "upsert_roadmap_items",
                    "valid_complexities": sorted(VALID_ROADMAP_COMPLEXITIES),
                },
            )

        blocked, blocked_reason = validate_blocked(raw.get("blocked"), raw.get("blocked_reason"), idx)

        normalized.append(
            {
                "item_type": item_type,
                "project_id": str(project_id) if project_id else None,
                "task_id": str(task_id) if task_id else None,
                "sort_order": sort_order,
                "risk": risk,
                "complexity": complexity,
                "blocked": blocked,
                "blocked_reason": blocked_reason,
            }
        )
    return normalized


def validate_blocked(blocked: Any, blocked_reason: Any, idx: int) -> tuple[bool, str | None]:
    """Validate the agent-flagged dependency block (FE-6022d): ``blocked`` is a
    real bool (default False); ``blocked_reason`` is optional free-text capped
    at ``MAX_BLOCKED_REASON_LEN`` and dropped when not blocked (no stale notes)."""
    op = {"operation": "upsert_roadmap_items"}
    if blocked is None:
        blocked_bool = False
    elif isinstance(blocked, bool):
        blocked_bool = blocked
    else:
        raise ValidationError(message=f"items[{idx}].blocked must be a boolean", context=op)

    reason = blocked_reason if blocked_reason not in (None, "") else None
    if reason is not None and not isinstance(reason, str):
        raise ValidationError(message=f"items[{idx}].blocked_reason must be a string", context=op)
    reason = reason.strip() or None if reason is not None else None
    if reason is not None and len(reason) > MAX_BLOCKED_REASON_LEN:
        raise ValidationError(
            message=f"items[{idx}].blocked_reason exceeds {MAX_BLOCKED_REASON_LEN} characters",
            context={**op, "max_blocked_reason_len": MAX_BLOCKED_REASON_LEN},
        )
    # An unblocked item carries no reason.
    return blocked_bool, (reason if blocked_bool else None)


def validate_sort_order(value: Any, idx: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(
            message=f"items[{idx}].sort_order must be an integer",
            context={"operation": "upsert_roadmap_items"},
        )
    if value < 0 or value > MAX_ROADMAP_SORT_ORDER:
        raise ValidationError(
            message=f"items[{idx}].sort_order must be between 0 and {MAX_ROADMAP_SORT_ORDER}",
            context={"operation": "upsert_roadmap_items", "max_sort_order": MAX_ROADMAP_SORT_ORDER},
        )
    return value


def validate_reorder(updates: Any) -> list[dict[str, Any]]:
    """Validate a reorder payload: list of {id, sort_order}."""
    if not isinstance(updates, list):
        raise ValidationError(
            message="items must be a list of {id, sort_order} objects",
            context={"operation": "reorder_roadmap"},
        )
    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(updates):
        if not isinstance(raw, dict) or not raw.get("id"):
            raise ValidationError(
                message=f"items[{idx}] must be an object with a non-empty id",
                context={"operation": "reorder_roadmap"},
            )
        sort_order = validate_sort_order(raw.get("sort_order", 0), idx)
        normalized.append({"id": str(raw["id"]), "sort_order": sort_order})
    return normalized


def validate_remove(remove: Any) -> list[dict[str, Any]]:
    """Validate + normalize a list of removal references (0006).

    Each ref mirrors the upsert item contract — ``{item_type, project_id |
    task_id}`` — so the agent removes by the SAME project/task id it ranks
    by, never by an opaque roadmap_item id. No unvalidated agent input: the
    discriminator membership + the required id are checked at the boundary
    (→ 422), never a DB constraint 500. ``None`` normalizes to ``[]``.
    """
    if remove is None:
        return []
    if not isinstance(remove, list):
        raise ValidationError(
            message="remove must be a list of {item_type, project_id|task_id} objects",
            context={"operation": "remove_roadmap_items"},
        )
    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(remove):
        if not isinstance(raw, dict):
            raise ValidationError(
                message=f"remove[{idx}] must be an object",
                context={"operation": "remove_roadmap_items"},
            )
        item_type = raw.get("item_type")
        if item_type not in VALID_ROADMAP_ITEM_TYPES:
            raise ValidationError(
                message=f"remove[{idx}].item_type '{item_type}' invalid. Valid: {sorted(VALID_ROADMAP_ITEM_TYPES)}",
                context={"operation": "remove_roadmap_items", "valid_item_types": sorted(VALID_ROADMAP_ITEM_TYPES)},
            )
        project_id = raw.get("project_id") or None
        task_id = raw.get("task_id") or None
        if item_type == "project":
            if not project_id:
                raise ValidationError(
                    message=f"remove[{idx}] item_type=project requires project_id",
                    context={"operation": "remove_roadmap_items"},
                )
            task_id = None
        else:  # task
            if not task_id:
                raise ValidationError(
                    message=f"remove[{idx}] item_type=task requires task_id",
                    context={"operation": "remove_roadmap_items"},
                )
            project_id = None
        normalized.append(
            {
                "item_type": item_type,
                "project_id": str(project_id) if project_id else None,
                "task_id": str(task_id) if task_id else None,
            }
        )
    return normalized
