# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Execution-mode selection gate (NULL-state redesign).

A project's ``execution_mode`` is NULL until the user explicitly picks one in the
dashboard. NULL means "not yet selected" -- a first-class, GATED state that must
never silently coerce to ``'multi_terminal'`` (that silent default shipped the
wrong orchestration mode). The boundary entry points -- staging prompt
generation, ``spawn_job``, ``get_staging_instructions`` and
``get_job_mission`` -- call :func:`execution_mode_selected` and refuse to
proceed when it returns ``False``. Because the refusal happens at the boundary, a
NULL never reaches the protocol-render layer, whose deliberate HO1020 fail-safes
(``.get(mode, "multi_terminal")``) map an *unknown* mode to the platform-neutral
protocol and stay untouched by this redesign.

Edition Scope: CE.
"""

from __future__ import annotations

from typing import Any

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.platform_registry import VALID_EXECUTION_MODES, mode_label_list


# The user-selectable orchestration modes. A project holds exactly one of these,
# or NULL (not yet selected). Single source: ``giljo_mcp.platform_registry`` --
# re-exported here so existing importers keep resolving the name.
__all__ = [
    "EXECUTION_MODE_NOT_SELECTED_MESSAGE",
    "VALID_EXECUTION_MODES",
    "execution_mode_selected",
    "require_execution_mode",
]


# Single user-facing instruction reused across the service-layer gates so the
# dashboard guidance is identical wherever the gate fires. The mode list is built
# from the PlatformRegistry so a new/removed platform updates this message
# automatically (BE-3010a: the literal list previously omitted Antigravity).
EXECUTION_MODE_NOT_SELECTED_MESSAGE = (
    "No execution mode is selected for this project. Open the project in the "
    f"GiljoAI dashboard, pick an execution mode ({mode_label_list()}), and stage "
    "it before continuing."
)


def execution_mode_selected(project: Any) -> bool:
    """Return ``True`` when ``project`` has a non-empty execution mode chosen.

    A loaded ORM ``Project`` always has the attribute, so ``getattr`` returns the
    column value (``None`` for a NULL row). A whitespace-only value is treated as
    unset. Callers gate on this to keep a NULL out of the dispatch/render layer.

    DELIBERATELY does NOT check membership in :data:`VALID_EXECUTION_MODES`. The
    division of labor is: this gate keeps a NULL/empty (unselected) mode out of
    rendering; an *unknown but non-empty* mode is the concern of the HO1020
    render-layer fail-safes (``.get(mode, "multi_terminal")``), which map it to
    the platform-neutral protocol. Tightening this to a membership check would
    turn a legacy/unknown mode into a hard block instead of that intended
    fallback — do not add ``in VALID_EXECUTION_MODES`` here. The write boundaries
    (staging Query regex + the ProjectService PATCH guard) are what keep stored
    modes within the valid set.
    """
    mode = getattr(project, "execution_mode", None)
    return bool(mode and str(mode).strip())


def require_execution_mode(project: Any, project_id: str, tenant_key: str) -> None:
    """Raise ``ValidationError`` when ``project`` has no execution mode selected.

    The spawn-boundary gate: refusing here dominates the downstream coercion sites
    so a NULL never silently becomes ``'multi_terminal'``. ``ValidationError`` is
    in ``spawn_job``'s re-raise allowlist, so it surfaces cleanly (not as a
    DatabaseError). Normal flow sets the mode at staging, so this is a backstop
    for out-of-band / legacy rows.
    """
    if not execution_mode_selected(project):
        raise ValidationError(
            message=EXECUTION_MODE_NOT_SELECTED_MESSAGE,
            error_code="EXECUTION_MODE_NOT_SELECTED",
            context={"project_id": project_id, "tenant_key": tenant_key},
        )
