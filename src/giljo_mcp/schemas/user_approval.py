# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Pydantic schemas for the user_approvals primitive (BE-5029 Phase A).

Schemas are closed (no ``extra="allow"``) -- the wire contract for approvals is
fixed and untrusted agent input must be rejected with 422 at the tool boundary
rather than reaching the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_OPTIONS = 10
MAX_OPTION_LABEL_LENGTH = 200
MAX_OPTION_ID_LENGTH = 100
MAX_REASON_LENGTH = 2000


class ApprovalOption(BaseModel):
    """A single option presented to the user for an approval decision."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=MAX_OPTION_ID_LENGTH)
    label: str = Field(..., min_length=1, max_length=MAX_OPTION_LABEL_LENGTH)


class RequestApprovalInput(BaseModel):
    """Validated input for the request_approval MCP tool.

    Closed schema. Agent input that does not match this contract must produce a
    clean 422 from Pydantic, never a 500 from a downstream DB constraint.
    """

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., min_length=1, max_length=36)
    project_id: str = Field(..., min_length=1, max_length=36)
    reason: str = Field(..., min_length=1, max_length=MAX_REASON_LENGTH)
    options: list[ApprovalOption] = Field(..., min_length=1, max_length=MAX_OPTIONS)
    context: dict[str, Any] | None = None

    @field_validator("options")
    @classmethod
    def options_have_unique_ids(cls, v: list[ApprovalOption]) -> list[ApprovalOption]:
        ids = [opt.id for opt in v]
        if len(ids) != len(set(ids)):
            raise ValueError("options must have unique ids")
        return v


class UserApprovalRead(BaseModel):
    """Read-side projection of a user_approvals row."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    tenant_key: str
    agent_execution_id: str
    job_id: str
    project_id: str
    reason: str
    options: list[dict[str, Any]]
    context: dict[str, Any] | None
    status: str
    decided_option_id: str | None
    decided_by_user_id: str | None
    requested_at: datetime
    decided_at: datetime | None


class ApprovalListResponse(BaseModel):
    """Paginated list of pending user approvals for ``GET /api/approvals``."""

    model_config = ConfigDict(extra="forbid")

    items: list[UserApprovalRead]
    count: int
    total: int
    limit: int
    offset: int
