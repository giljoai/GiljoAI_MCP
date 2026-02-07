"""
Integration tests for Template Cache + UnifiedTemplateManager workflow
(Handover 0041 Phase 2)

Tests the full workflow:
- Template editing → Cache invalidation → Next request fetches from DB
- Multi-tenant isolation in real scenarios
- Fallback to legacy templates when database is empty
- Full end-to-end template resolution
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager


# Integration test fixtures


@pytest.fixture
def mock_db_manager():
    """Mock database manager for integration tests"""
    db_manager = MagicMock()
    db_manager.get_session = AsyncMock()
    return db_manager


@pytest.fixture
def template_manager(mock_db_manager):
    """Template manager with cache"""
    return UnifiedTemplateManager(mock_db_manager, redis_client=None)


@pytest.fixture
def orchestrator_template():
    """Sample orchestrator template"""
    return AgentTemplate(
        id="tmpl-001",
        tenant_key="tenant-123",
        product_id=None,
        name="Orchestrator",
        role="orchestrator",
        category="role",
        system_instructions="You are the orchestrator for {project_name}. Mission: {project_mission}",
        is_active=True,
        is_default=False,
        version="1.0.0",
    )


# Full workflow integration tests


@pytest.mark.asyncio
async def test_full_template_workflow_with_cache(template_manager, orchestrator_template, mock_db_manager):
    """Test full workflow: fetch → cache → retrieve from cache"""
    # Mock database session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=orchestrator_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # First request (cache miss, fetch from DB)
    result1 = await template_manager.get_template(
        role="orchestrator",
        tenant_key="tenant-123",
        variables={
            "project_name": "Test Project",
            "project_mission": "Build awesome software",
        },
    )

    # Verify template processed correctly
    assert "You are the orchestrator for Test Project" in result1
    assert "Build awesome software" in result1

    # Verify cache stats show 1 miss
    stats = template_manager.get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Second request (cache hit, no DB query)
    mock_db_manager.get_session.reset_mock()  # Reset to verify DB not called

    result2 = await template_manager.get_template(
        role="orchestrator",
        tenant_key="tenant-123",
        variables={
            "project_name": "Another Project",
            "project_mission": "Another mission",
        },
    )

    # Verify template retrieved from cache
    assert "You are the orchestrator for Another Project" in result2

    # Verify cache stats show 1 hit
    stats = template_manager.get_cache_stats()
    assert stats["hits"] == 1

    # Verify database was NOT queried (cache hit)
    mock_db_manager.get_session.assert_not_called()


@pytest.mark.asyncio
async def test_template_edit_invalidates_cache(template_manager, orchestrator_template, mock_db_manager):
    """Test editing template invalidates cache and next request fetches updated version"""
    # Mock database session for initial fetch
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=orchestrator_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Initial request (fetches and caches)
    result1 = await template_manager.get_template(
        role="orchestrator",
        tenant_key="tenant-123",
        variables={"project_name": "Test", "project_mission": "Test"},
    )
    assert "You are the orchestrator for Test" in result1

    # Verify template is cached
    cache_key = template_manager.cache._build_cache_key("orchestrator", "tenant-123", None)
    assert cache_key in template_manager.cache._memory_cache

    # Simulate template edit (invalidate cache)
    await template_manager.invalidate_cache("orchestrator", "tenant-123", None)

    # Verify cache was invalidated
    assert cache_key not in template_manager.cache._memory_cache

    # Update template content (simulate database update)
    updated_template = AgentTemplate(
        id="tmpl-001",
        tenant_key="tenant-123",
        product_id=None,
        name="Orchestrator",
        role="orchestrator",
        category="role",
        system_instructions="UPDATED: You are the NEW orchestrator for {project_name}",
        is_active=True,
        is_default=False,
        version="1.1.0",
    )

    # Mock database to return updated template
    mock_result_updated = AsyncMock()
    mock_result_updated.scalar_one_or_none = AsyncMock(return_value=updated_template)
    mock_session.execute = AsyncMock(return_value=mock_result_updated)

    # Next request should fetch updated template from database
    result2 = await template_manager.get_template(
        role="orchestrator",
        tenant_key="tenant-123",
        variables={"project_name": "Test", "project_mission": "Test"},
    )

    # Verify updated template is used
    assert "UPDATED: You are the NEW orchestrator for Test" in result2


@pytest.mark.asyncio
async def test_fallback_to_legacy_when_db_empty(template_manager, mock_db_manager):
    """Test fallback to legacy templates when database is empty"""
    # Mock database to return None (no templates in database)
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request template (should use legacy fallback)
    result = await template_manager.get_template(
        role="orchestrator",
        tenant_key="tenant-123",
        variables={"project_name": "Test Project", "project_mission": "Test"},
    )

    # Verify legacy template was used (has specific content)
    assert "PROJECT GOAL:" in result
    assert "THE 30-80-10 PRINCIPLE" in result
    assert "DISCOVERY PHASE" in result
