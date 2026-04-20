# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for StatisticsService (BE-5022b).

Verifies that the service layer correctly wraps the statistics repositories
and enforces tenant isolation on all analytics queries.
"""

import pytest
import pytest_asyncio

from giljo_mcp.services.statistics_service import StatisticsService


@pytest_asyncio.fixture
async def stats_service(db_manager, db_session):
    """Create StatisticsService instance with test session."""
    return StatisticsService(
        db_manager=db_manager,
        test_session=db_session,
    )


@pytest.mark.asyncio
async def test_get_system_stats_returns_expected_keys(stats_service, test_tenant_key):
    """System stats should return all expected metric keys."""
    result = await stats_service.get_system_stats(test_tenant_key)
    expected_keys = {
        "total_projects",
        "active_projects",
        "completed_projects",
        "total_agents",
        "active_agents",
        "total_messages",
        "pending_messages",
        "total_tasks",
        "completed_tasks",
        "total_agents_spawned",
        "total_jobs_completed",
        "projects_staged",
        "projects_cancelled",
    }
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_get_system_stats_tenant_isolation(stats_service):
    """System stats with non-existent tenant should return zeros."""
    result = await stats_service.get_system_stats("nonexistent_tenant_key")
    assert result["total_projects"] == 0
    assert result["total_agents"] == 0
    assert result["total_messages"] == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_returns_expected_keys(stats_service, test_tenant_key):
    """Dashboard stats should return all expected top-level keys."""
    result = await stats_service.get_dashboard_stats(test_tenant_key)
    expected_keys = {
        "project_status_dist",
        "taxonomy_dist",
        "agent_role_dist",
        "recent_projects",
        "recent_memories",
        "task_status_dist",
        "execution_mode_dist",
        "products",
    }
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_get_message_stats_returns_expected_keys(stats_service, test_tenant_key):
    """Message stats should return all expected status count keys."""
    result = await stats_service.get_message_stats(test_tenant_key)
    expected_keys = {"total", "pending", "acknowledged", "completed", "failed"}
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_execute_health_check(stats_service):
    """Health check should return True when DB is connected."""
    result = await stats_service.execute_health_check()
    assert result is True
