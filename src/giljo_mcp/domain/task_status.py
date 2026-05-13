# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Canonical ``TaskStatus`` enum + class-level metadata (FE-5041 Phase 1).

Single Source of Truth for task status across the backend (replacing the
free-form ``Column(String(50))`` + comment in ``models/tasks.py`` and the
``_VALID_TASK_STATUSES`` frozenset in ``services/task_service.py``) and
the frontend metadata API at ``GET /api/v1/task-statuses/``.

Mirrors the ``project_status`` SSoT (BE-5039) verbatim. Tasks do NOT have
a Postgres ENUM type backing them today -- the column remains a free-form
``VARCHAR(50)`` -- so the domain enum is the only authority. The
``.value`` strings here are the source of truth for what the DB stores.

Edition isolation
-----------------
This module is CE-foundational. SaaS does not extend it.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskStatusMeta:
    """Presentation + lifecycle metadata for a single :class:`TaskStatus` member.

    Attributes
    ----------
    label
        Human-readable badge label rendered by the frontend
        ``TaskStatusBadge.vue`` component.
    color_token
        Name of a CSS custom property declared in
        ``frontend/src/styles/main.scss`` (mirrored from the SCSS token
        in ``design-tokens.scss``). The frontend resolves it via
        ``getComputedStyle(...).getPropertyValue('--' + token)`` instead
        of embedding hex literals.
    is_lifecycle_finished
        Members of :data:`TASK_LIFECYCLE_FINISHED_STATUSES`. Tasks in
        these states have ``completed_at`` set (``completed`` /
        ``cancelled``).
    """

    label: str
    color_token: str
    is_lifecycle_finished: bool


class TaskStatus(enum.StrEnum):
    """Canonical task lifecycle status.

    Inherits from :class:`str` so ``TaskStatus.PENDING == "pending"`` is
    ``True`` -- preserves equality with the legacy free-form values
    written by ``TaskService`` and the existing rows in the ``tasks``
    table.

    Order of declaration matches the comment in ``models/tasks.py`` and
    the ``STATUS_META`` literal in ``frontend/src/components/TaskStatusBadge.vue``.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

    @property
    def meta(self) -> TaskStatusMeta:
        return TASK_STATUS_META[self]

    @property
    def label(self) -> str:
        return self.meta.label

    @property
    def color_token(self) -> str:
        return self.meta.color_token

    @property
    def is_lifecycle_finished(self) -> bool:
        return self.meta.is_lifecycle_finished


# Class-level metadata. The dict is the single registration site.
#
# Color-token choices (Luminous Pastels palette, all WCAG AA on `#12202e`,
# matching the hex literals previously embedded in TaskStatusBadge.vue):
#   pending     -> color-text-muted        (#9e9e9e, neutral 4.98:1)
#   in_progress -> color-agent-implementer (#6db3e4, sky 6.64:1)
#   completed   -> color-agent-researcher  (#5ec48e, mint 7.03:1)
#   blocked     -> color-agent-analyzer    (#e07872, coral 5.11:1)
#   cancelled   -> color-text-muted        (intentional same as pending --
#                  terminal/inert state, mirrors badge component note)
TASK_STATUS_META: dict[TaskStatus, TaskStatusMeta] = {
    TaskStatus.PENDING: TaskStatusMeta(
        label="Pending",
        color_token="color-text-muted",
        is_lifecycle_finished=False,
    ),
    TaskStatus.IN_PROGRESS: TaskStatusMeta(
        label="In Progress",
        color_token="color-agent-implementer",
        is_lifecycle_finished=False,
    ),
    TaskStatus.COMPLETED: TaskStatusMeta(
        label="Completed",
        color_token="color-agent-researcher",
        is_lifecycle_finished=True,
    ),
    TaskStatus.BLOCKED: TaskStatusMeta(
        label="Blocked",
        color_token="color-agent-analyzer",
        is_lifecycle_finished=False,
    ),
    TaskStatus.CANCELLED: TaskStatusMeta(
        label="Cancelled",
        color_token="color-text-muted",
        is_lifecycle_finished=True,
    ),
}


# Drift sanity check: every enum member must carry metadata. Catches
# rename/reorder drift at import time rather than at first .meta lookup.
if set(TASK_STATUS_META.keys()) != set(TaskStatus):
    missing = set(TaskStatus) - set(TASK_STATUS_META.keys())
    extra = set(TASK_STATUS_META.keys()) - set(TaskStatus)
    raise RuntimeError(
        f"TASK_STATUS_META drift detected. Missing metadata: {missing}. "
        f"Extra metadata: {extra}. Update giljo_mcp.domain.task_status."
    )


# Derived sets. Frozensets of TaskStatus members; equality with raw strings
# still works because the enum inherits from str.
TASK_LIFECYCLE_FINISHED_STATUSES: frozenset[TaskStatus] = frozenset(
    s for s, m in TASK_STATUS_META.items() if m.is_lifecycle_finished
)
VALID_TASK_STATUSES: frozenset[TaskStatus] = frozenset(TaskStatus)
