"""
Comprehensive tests for TemplateCache (Handover 0041 Phase 2)

Tests cover:
- Cache hit/miss scenarios
- Cascade resolution order (product → tenant → system → None)
- Cache invalidation (all layers)
- Multi-tenant isolation
- Performance benchmarks (cache latency < 1ms)
- Redis optional (graceful degradation)
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_cache import TemplateCache


# Test fixtures


@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    db_manager = MagicMock()
    db_manager.get_session = AsyncMock()
    return db_manager


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def template_cache(mock_db_manager):
    """TemplateCache instance without Redis"""
    return TemplateCache(mock_db_manager, redis_client=None)


@pytest.fixture
def template_cache_with_redis(mock_db_manager, mock_redis):
    """TemplateCache instance with Redis"""
    return TemplateCache(mock_db_manager, redis_client=mock_redis)


@pytest.fixture
def sample_template():
    """Sample AgentTemplate object"""
    template = AgentTemplate(
        id="tmpl-001",
        tenant_key="tenant-123",
        product_id=None,
        name="Orchestrator",
        role="orchestrator",
        category="role",
        system_instructions="You are the orchestrator for {project_name}",
        is_active=True,
        is_default=False,
        version="1.0.0",
    )
    return template


# Cache key building tests


def test_build_cache_key_tenant_only(template_cache):
    """Test cache key building for tenant-only template"""
    key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    assert key == "template:tenant-123:tenant:orchestrator"


def test_build_cache_key_with_product(template_cache):
    """Test cache key building for product-specific template"""
    key = template_cache._build_cache_key("orchestrator", "tenant-123", "prod-456")
    assert key == "template:tenant-123:prod-456:orchestrator"


# Memory cache tests


@pytest.mark.asyncio
async def test_memory_cache_hit(template_cache, sample_template, mock_db_manager):
    """Test memory cache returns cached template without database query"""
    # Pre-populate memory cache
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    template_cache._memory_cache[cache_key] = sample_template

    # Request template
    result = await template_cache.get_template("orchestrator", "tenant-123", None)

    # Verify cache hit
    assert result == sample_template
    assert template_cache._cache_hits == 1
    assert template_cache._cache_misses == 0

    # Verify database was NOT called
    mock_db_manager.get_session.assert_not_called()


@pytest.mark.asyncio
async def test_memory_cache_miss_db_query(template_cache, sample_template, mock_db_manager):
    """Test memory cache miss triggers database query"""
    # Mock database session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=sample_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request template
    result = await template_cache.get_template("orchestrator", "tenant-123", None)

    # Verify cache miss and database query
    assert result == sample_template
    assert template_cache._cache_hits == 0
    assert template_cache._cache_misses == 1

    # Verify template was cached in memory
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    assert cache_key in template_cache._memory_cache
    assert template_cache._memory_cache[cache_key] == sample_template


# Cascade resolution tests


@pytest.mark.asyncio
async def test_cascade_product_specific_priority(template_cache, mock_db_manager):
    """Test cascade resolution prioritizes product-specific template"""
    # Create templates at different levels
    product_template = AgentTemplate(
        id="tmpl-product",
        tenant_key="tenant-123",
        product_id="prod-456",
        role="orchestrator",
        system_instructions="Product-specific template",
        is_active=True,
        is_default=False,
    )

    # Mock database to return product template
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=product_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request with product_id
    result = await template_cache.get_template("orchestrator", "tenant-123", "prod-456")

    # Verify product template was returned
    assert result == product_template
    assert result.system_instructions == "Product-specific template"


@pytest.mark.asyncio
async def test_cascade_tenant_fallback(template_cache, mock_db_manager):
    """Test cascade falls back to tenant template when product not found"""
    tenant_template = AgentTemplate(
        id="tmpl-tenant",
        tenant_key="tenant-123",
        product_id=None,
        role="orchestrator",
        system_instructions="Tenant-specific template",
        is_active=True,
        is_default=False,
    )

    # Mock database to return None for product, then tenant template
    mock_session = AsyncMock()
    mock_result_product = AsyncMock()
    mock_result_product.scalar_one_or_none = AsyncMock(return_value=None)
    mock_result_tenant = AsyncMock()
    mock_result_tenant.scalar_one_or_none = AsyncMock(return_value=tenant_template)

    # First call returns None (product), second returns tenant template
    mock_session.execute = AsyncMock(side_effect=[mock_result_product, mock_result_tenant])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request with product_id
    result = await template_cache.get_template("orchestrator", "tenant-123", "prod-456")

    # Verify tenant template was returned
    assert result == tenant_template
    assert result.system_instructions == "Tenant-specific template"


@pytest.mark.asyncio
async def test_cascade_system_default_fallback(template_cache, mock_db_manager):
    """Test cascade falls back to system default when tenant not found"""
    system_template = AgentTemplate(
        id="tmpl-system",
        tenant_key="system",
        product_id=None,
        role="orchestrator",
        system_instructions="System default template",
        is_active=True,
        is_default=True,
    )

    # Mock database to return None for product and tenant, then system template
    mock_session = AsyncMock()
    mock_result_none = AsyncMock()
    mock_result_none.scalar_one_or_none = AsyncMock(return_value=None)
    mock_result_system = AsyncMock()
    mock_result_system.scalar_one_or_none = AsyncMock(return_value=system_template)

    # Three calls: product (None), tenant (None), system (found)
    mock_session.execute = AsyncMock(side_effect=[mock_result_none, mock_result_none, mock_result_system])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request with product_id
    result = await template_cache.get_template("orchestrator", "tenant-123", "prod-456")

    # Verify system template was returned
    assert result == system_template
    assert result.system_instructions == "System default template"


@pytest.mark.asyncio
async def test_cascade_returns_none_when_not_found(template_cache, mock_db_manager):
    """Test cascade returns None when no templates found at any level"""
    # Mock database to return None for all queries
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request template
    result = await template_cache.get_template("orchestrator", "tenant-123", None)

    # Verify None returned
    assert result is None


# Multi-tenant isolation tests


@pytest.mark.asyncio
async def test_multi_tenant_isolation(template_cache, mock_db_manager):
    """Test templates are isolated by tenant_key"""
    tenant1_template = AgentTemplate(
        id="tmpl-tenant1",
        tenant_key="tenant-111",
        role="orchestrator",
        system_instructions="Tenant 1 template",
        is_active=True,
        is_default=False,
    )

    tenant2_template = AgentTemplate(
        id="tmpl-tenant2",
        tenant_key="tenant-222",
        role="orchestrator",
        system_instructions="Tenant 2 template",
        is_active=True,
        is_default=False,
    )

    # Mock database to return tenant-specific templates
    mock_session = AsyncMock()

    def mock_execute_side_effect(stmt):
        # Check which tenant is being queried
        # This is a simplified check - in real scenario would parse SQL
        mock_result = AsyncMock()
        # Default to tenant1 for first call, tenant2 for second
        if not hasattr(mock_execute_side_effect, "call_count"):
            mock_execute_side_effect.call_count = 0

        if mock_execute_side_effect.call_count == 0:
            mock_result.scalar_one_or_none = AsyncMock(return_value=tenant1_template)
        else:
            mock_result.scalar_one_or_none = AsyncMock(return_value=tenant2_template)

        mock_execute_side_effect.call_count += 1
        return mock_result

    mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request template for tenant 1
    result1 = await template_cache.get_template("orchestrator", "tenant-111", None)
    assert result1 == tenant1_template

    # Request template for tenant 2
    result2 = await template_cache.get_template("orchestrator", "tenant-222", None)
    assert result2 == tenant2_template

    # Verify templates are different
    assert result1.system_instructions != result2.system_instructions


# Cache invalidation tests


@pytest.mark.asyncio
async def test_invalidate_memory_cache(template_cache, sample_template):
    """Test invalidation removes template from memory cache"""
    # Populate memory cache
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    template_cache._memory_cache[cache_key] = sample_template

    # Invalidate
    await template_cache.invalidate("orchestrator", "tenant-123", None)

    # Verify removed from memory
    assert cache_key not in template_cache._memory_cache


@pytest.mark.asyncio
async def test_invalidate_redis_cache(template_cache_with_redis, sample_template, mock_redis):
    """Test invalidation removes template from Redis"""
    cache_key = template_cache_with_redis._build_cache_key("orchestrator", "tenant-123", None)

    # Invalidate
    await template_cache_with_redis.invalidate("orchestrator", "tenant-123", None)

    # Verify Redis delete was called
    mock_redis.delete.assert_called_once_with(cache_key)


@pytest.mark.asyncio
async def test_invalidate_all_tenant(template_cache, sample_template):
    """Test invalidate_all removes all templates for specific tenant"""
    # Populate cache with multiple templates
    template_cache._memory_cache["template:tenant-123:tenant:orchestrator"] = sample_template
    template_cache._memory_cache["template:tenant-123:tenant:analyzer"] = sample_template
    template_cache._memory_cache["template:tenant-456:tenant:orchestrator"] = sample_template

    # Invalidate tenant-123 only
    await template_cache.invalidate_all("tenant-123")

    # Verify only tenant-123 templates removed
    assert "template:tenant-123:tenant:orchestrator" not in template_cache._memory_cache
    assert "template:tenant-123:tenant:analyzer" not in template_cache._memory_cache
    assert "template:tenant-456:tenant:orchestrator" in template_cache._memory_cache


@pytest.mark.asyncio
async def test_invalidate_all_global(template_cache, sample_template):
    """Test invalidate_all removes all templates when tenant_key=None"""
    # Populate cache
    template_cache._memory_cache["template:tenant-123:tenant:orchestrator"] = sample_template
    template_cache._memory_cache["template:tenant-456:tenant:analyzer"] = sample_template

    # Invalidate all
    await template_cache.invalidate_all(None)

    # Verify all removed
    assert len(template_cache._memory_cache) == 0


# Redis integration tests


@pytest.mark.asyncio
async def test_redis_cache_hit(template_cache_with_redis, sample_template, mock_redis, mock_db_manager):
    """Test Redis cache hit returns template without database query"""
    import pickle

    # Mock Redis to return serialized template
    cache_key = template_cache_with_redis._build_cache_key("orchestrator", "tenant-123", None)
    mock_redis.get = AsyncMock(return_value=pickle.dumps(sample_template))

    # Request template
    result = await template_cache_with_redis.get_template("orchestrator", "tenant-123", None)

    # Verify Redis hit
    assert result == sample_template
    mock_redis.get.assert_called_once_with(cache_key)

    # Verify database NOT called
    mock_db_manager.get_session.assert_not_called()


@pytest.mark.asyncio
async def test_redis_cache_write(template_cache_with_redis, sample_template, mock_redis, mock_db_manager):
    """Test template is written to Redis after database fetch"""
    # Mock database to return template
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=sample_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Mock Redis get to return None (cache miss)
    mock_redis.get = AsyncMock(return_value=None)

    # Request template
    result = await template_cache_with_redis.get_template("orchestrator", "tenant-123", None)

    # Verify template returned
    assert result == sample_template

    # Verify Redis setex was called with TTL=3600
    cache_key = template_cache_with_redis._build_cache_key("orchestrator", "tenant-123", None)
    assert mock_redis.setex.called
    call_args = mock_redis.setex.call_args[0]
    assert call_args[0] == cache_key
    assert call_args[1] == 3600  # TTL


@pytest.mark.asyncio
async def test_redis_failure_graceful_degradation(
    template_cache_with_redis, sample_template, mock_redis, mock_db_manager
):
    """Test Redis failure gracefully falls back to database"""
    # Mock Redis to raise exception
    mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

    # Mock database to return template
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=sample_template)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request template (should not raise exception)
    result = await template_cache_with_redis.get_template("orchestrator", "tenant-123", None)

    # Verify template returned from database
    assert result == sample_template


# Performance tests


@pytest.mark.asyncio
async def test_memory_cache_performance(template_cache, sample_template):
    """Test memory cache hit latency < 1ms (p95)"""
    # Populate cache
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    template_cache._memory_cache[cache_key] = sample_template

    # Measure 100 cache hits
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        await template_cache.get_template("orchestrator", "tenant-123", None)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to milliseconds

    # Calculate p95
    latencies.sort()
    p95_latency = latencies[94]  # 95th percentile

    # Verify p95 < 1ms
    assert p95_latency < 1.0, f"P95 latency {p95_latency:.3f}ms exceeds 1ms threshold"


@pytest.mark.asyncio
async def test_lru_cache_limit_enforcement(template_cache, mock_db_manager):
    """Test LRU cache enforces 100-template limit"""
    # Mock database to return templates
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(
        return_value=AgentTemplate(
            id="test",
            tenant_key="tenant-123",
            role="test",
            system_instructions="test",
            is_active=True,
            is_default=False,
        )
    )
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Request 105 different templates
    for i in range(105):
        await template_cache.get_template(f"role-{i}", "tenant-123", None)

    # Verify cache size is 100 (LRU eviction occurred)
    assert len(template_cache._memory_cache) == 100


# Cache statistics tests


def test_cache_stats_initial(template_cache):
    """Test cache statistics are zero initially"""
    stats = template_cache.get_cache_stats()

    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total_requests"] == 0
    assert stats["hit_rate_percent"] == 0.0
    assert stats["memory_cache_size"] == 0
    assert stats["redis_enabled"] is False


@pytest.mark.asyncio
async def test_cache_stats_after_hits(template_cache, sample_template):
    """Test cache statistics track hits correctly"""
    # Populate cache
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    template_cache._memory_cache[cache_key] = sample_template

    # Generate 5 cache hits
    for _ in range(5):
        await template_cache.get_template("orchestrator", "tenant-123", None)

    # Check stats
    stats = template_cache.get_cache_stats()
    assert stats["hits"] == 5
    assert stats["misses"] == 0
    assert stats["total_requests"] == 5
    assert stats["hit_rate_percent"] == 100.0


@pytest.mark.asyncio
async def test_cache_stats_after_misses(template_cache, mock_db_manager):
    """Test cache statistics track misses correctly"""
    # Mock database to return None (no templates)
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session.return_value = mock_session

    # Generate 3 cache misses
    for _ in range(3):
        await template_cache.get_template("orchestrator", "tenant-123", None)

    # Check stats
    stats = template_cache.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 3
    assert stats["total_requests"] == 3
    assert stats["hit_rate_percent"] == 0.0


def test_reset_stats(template_cache, sample_template):
    """Test reset_stats clears counters"""
    # Generate some hits
    cache_key = template_cache._build_cache_key("orchestrator", "tenant-123", None)
    template_cache._memory_cache[cache_key] = sample_template
    template_cache._cache_hits = 10
    template_cache._cache_misses = 5

    # Reset
    template_cache.reset_stats()

    # Verify reset
    stats = template_cache.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
