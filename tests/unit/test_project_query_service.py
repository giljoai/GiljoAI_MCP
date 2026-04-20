# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for ProjectQueryService (Sprint 002e extraction).

These tests verify that the read-only dashboard query methods function
correctly after extraction from ProjectService.
"""

from unittest.mock import MagicMock

import pytest

from giljo_mcp.services.project_query_service import ProjectQueryService


@pytest.fixture
def query_service(db_session, test_tenant_key):
    """Create a ProjectQueryService with a test session."""
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return ProjectQueryService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest.mark.asyncio
async def test_get_active_project_returns_none_when_no_active(query_service):
    """get_active_project returns None when no project is active."""
    result = await query_service.get_active_project()
    assert result is None


@pytest.mark.asyncio
async def test_get_project_agent_summary_returns_empty_for_missing_project(query_service, test_tenant_key):
    """get_project_agent_summary returns zero counts for non-existent project."""
    result = await query_service.get_project_agent_summary("00000000-0000-0000-0000-000000000000", test_tenant_key)
    assert result == {"agent_count": 0, "job_types": []}


@pytest.mark.asyncio
async def test_get_project_agent_details_returns_empty_for_missing_project(query_service, test_tenant_key):
    """get_project_agent_details returns empty list for non-existent project."""
    result = await query_service.get_project_agent_details("00000000-0000-0000-0000-000000000000", test_tenant_key)
    assert result == []


@pytest.mark.asyncio
async def test_get_project_memory_entries_returns_empty_for_missing_project(query_service, test_tenant_key):
    """get_project_memory_entries returns empty list for non-existent project."""
    result = await query_service.get_project_memory_entries("00000000-0000-0000-0000-000000000000", test_tenant_key)
    assert result == []


@pytest.mark.asyncio
async def test_get_project_messages_returns_empty_for_missing_project(query_service, test_tenant_key):
    """get_project_messages returns empty list for non-existent project."""
    result = await query_service.get_project_messages("00000000-0000-0000-0000-000000000000", test_tenant_key)
    assert result == []
