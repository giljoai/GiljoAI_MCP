# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for JobCompletionService (Sprint 002e extraction)."""

from unittest.mock import MagicMock

import pytest

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.services.job_completion_service import JobCompletionService


@pytest.fixture
def completion_service(db_session, test_tenant_key):
    """Create a JobCompletionService with a test session."""
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest.mark.asyncio
async def test_complete_job_rejects_empty_job_id(completion_service, test_tenant_key):
    """complete_job raises ValidationError for empty job_id."""
    with pytest.raises(ValidationError):
        await completion_service.complete_job("", {"summary": "test"}, test_tenant_key)


@pytest.mark.asyncio
async def test_complete_job_rejects_non_dict_result(completion_service, test_tenant_key):
    """complete_job raises ValidationError when result is not a dict."""
    with pytest.raises(ValidationError):
        await completion_service.complete_job("some-job-id", None, test_tenant_key)


@pytest.mark.asyncio
async def test_complete_job_raises_for_missing_execution(completion_service, test_tenant_key):
    """complete_job raises ResourceNotFoundError for non-existent job."""
    with pytest.raises(ResourceNotFoundError):
        await completion_service.complete_job(
            "00000000-0000-0000-0000-000000000000", {"summary": "test"}, test_tenant_key
        )
