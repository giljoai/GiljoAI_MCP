# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Regression test for the structlog-style-kwargs-to-stdlib-logger bug.

Sprint 002g (commit 8d2f660b) migrated context_tools from structlog to stdlib
`logging`, but missed several call sites that still passed structlog-style
kwargs. Stdlib `Logger._log()` rejects those kwargs with TypeError, which
isn't caught by Python's logging error suppression. The first call site that
fires (get_project line 77) blew up every `fetch_context(["project"])` call
on the demo SaaS server.

This test exercises the smallest reachable path through every affected file
that fires the broken logger BEFORE any other failure mode. If the bug
regresses, these tests fail with TypeError instead of the documented
ValueError / returned-error-shape.
"""

import pytest

from giljo_mcp.tools.context_tools.get_project import get_project


@pytest.mark.asyncio
async def test_get_project_logger_does_not_typeerror() -> None:
    """get_project's entry-point logger.info must use printf-style, not structlog kwargs.

    Reaches line 77 logger.info call before the line 81 db_manager guard.
    Pre-fix: TypeError: Logger._log() got an unexpected keyword argument 'project_id'.
    Post-fix: ValueError("db_manager parameter is required").
    """
    with pytest.raises(ValueError, match="db_manager parameter is required"):
        await get_project(
            project_id="00000000-0000-0000-0000-000000000000",
            tenant_key="tk_test",
            db_manager=None,
        )
