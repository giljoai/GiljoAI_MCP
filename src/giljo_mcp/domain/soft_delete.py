# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared soft-delete (trash/recover) policy — BE-6130b.

A single source of truth for the self-service recovery window so the rule does
not drift across the entities that support trash/recover (CommThread, Task,
VisionDocument, ...).

Per BE-6130b decision A: the window is enforced at the RECOVER boundary — a row
trashed more than ``RECOVER_WINDOW_DAYS`` ago is no longer recoverable. The
permanent purge of expired rows (a generalized FK-safe reaper, TSK-6132) hard-
deletes those past-window rows through each entity's owning service; the reaper
shares this module's policy so the "no longer recoverable" cutoff and the "now
eligible to purge" cutoff are the same number, by construction.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


RECOVER_WINDOW_DAYS = 30


def recover_window_expired(deleted_at: datetime | None, *, now: datetime | None = None) -> bool:
    """Return True if a soft-deleted row is past the recovery window.

    A ``None`` ``deleted_at`` (a live row) is never "expired" — callers gate the
    not-found / not-deleted case separately. Naive timestamps are treated as UTC
    so a column stored without tzinfo still compares correctly.
    """
    if deleted_at is None:
        return False
    if deleted_at.tzinfo is None:
        deleted_at = deleted_at.replace(tzinfo=UTC)
    return deleted_at < recover_window_cutoff(now=now)


def recover_window_cutoff(*, now: datetime | None = None) -> datetime:
    """Return the timestamp boundary of the recovery window.

    A soft-deleted row whose ``deleted_at`` is strictly before this cutoff is
    past the window: no longer recoverable, and eligible for the TSK-6132 reaper
    to hard-delete. Mirrors :func:`recover_window_expired` so a single
    ``RECOVER_WINDOW_DAYS`` drives both the per-row gate and the reaper's
    cross-tenant discovery query.
    """
    reference = now or datetime.now(UTC)
    return reference - timedelta(days=RECOVER_WINDOW_DAYS)
