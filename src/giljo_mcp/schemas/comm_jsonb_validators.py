# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Pydantic validators for the Agent Message Hub JSONB columns (BE-6054a).

Kept in a dedicated sibling module (not jsonb_validators.py) so the comm-hub
validators live next to their feature and the core validators file stays under
the 800-line guardrail. Mirrors the jsonb_validators.py write-boundary pattern:
a Pydantic model + a ``validate_*(data) -> data`` function called where the
column is written (CommThreadRepository.create_thread).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CommThreadResolution(BaseModel):
    """Validates comm_threads.resolution JSONB (Agent Message Hub).

    The resolution payload is genuinely free-form per-thread (different threads
    resolve in different shapes), so ``extra="allow"`` is appropriate here — but
    the known fields are typed so the common shape stays consistent.
    """

    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    resolved_by: str | None = None  # agent_id | user_id
    resolved_at: str | None = None  # ISO 8601
    outcome: str | None = None


def validate_comm_thread_resolution(data: dict | None) -> dict | None:
    """Validate comm_threads.resolution dict, or None (BE-6054a)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise TypeError(f"comm_thread resolution must be a dict, got {type(data).__name__}")
    return CommThreadResolution(**data).model_dump(exclude_none=False)
