# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression: the close_project_and_update_memory tool boundary must log a <500
domain rejection at INFO, not via logger.exception.

Sentry backlog triage (2026-07-07): the closeout boundary's broad
``except Exception: logger.exception(...); raise`` emitted a Sentry error event
for routine, agent-actionable domain rejections that propagate through it —
e.g. a wrong/foreign project_id (ResourceNotFoundError, 404, Sentry
GILJOAI-BACKEND-8) or the orchestrator self-decommission guard
(ProjectStateError, 409, GILJOAI-BACKEND-4). Behaviour is correct in both cases
(the caller gets a clean 4xx), so those must not surface as backend "errors".

Contract: a BaseGiljoError with default_status_code < 500 reaching the boundary
is logged at INFO and re-raised unchanged; genuine 5xx / unexpected errors still
go through logger.exception. This test pins the log level (the re-raise is
covered by the fact the caller still receives the exception).
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.tools.project_closeout import close_project_and_update_memory


closeout_module = sys.modules["giljo_mcp.tools.project_closeout"]

BOUNDARY_LOGGER = "giljo_mcp.tools.project_closeout"
PROJECT_ID = "44444444-4444-4444-4444-444444444444"
TENANT_KEY = "tk_test"


def _make_db_manager() -> Any:
    """A db_manager whose async session context manager yields a sentinel session."""

    @asynccontextmanager
    async def _session_cm():
        yield object()

    db_manager = AsyncMock()
    db_manager.get_session_async = _session_cm
    return db_manager


@pytest.mark.asyncio
async def test_domain_rejection_logged_at_info_not_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    # A 404 domain rejection raised from inside the closeout body — the exact
    # shape of a wrong/foreign project_id (Sentry GILJOAI-BACKEND-8).
    monkeypatch.setattr(
        closeout_module,
        "_fetch_project_and_product",
        AsyncMock(side_effect=ResourceNotFoundError("Project not found or unauthorized for tenant")),
    )
    caplog.set_level(logging.INFO, logger=BOUNDARY_LOGGER)

    # Behaviour preserved: the boundary still re-raises the rejection.
    with pytest.raises(ResourceNotFoundError):
        await close_project_and_update_memory(
            project_id=PROJECT_ID,
            summary="x",
            key_outcomes=["o1"],
            decisions_made=["d1"],
            tenant_key=TENANT_KEY,
            db_manager=_make_db_manager(),
            tags=["chore", "backend"],
        )

    boundary_records = [r for r in caplog.records if r.name == BOUNDARY_LOGGER]

    # The rejection was logged at INFO ...
    assert any(r.levelno == logging.INFO and "close_project rejected" in r.getMessage() for r in boundary_records), (
        "expected an INFO 'close_project rejected' record, got: "
        f"{[(r.levelname, r.getMessage()) for r in boundary_records]}"
    )
    # ... and NOT at ERROR/exception level (that is the Sentry-noise regression).
    assert not any(r.levelno >= logging.ERROR for r in boundary_records), (
        "a <500 domain rejection must not log at ERROR (Sentry noise): "
        f"{[(r.levelname, r.getMessage()) for r in boundary_records]}"
    )
