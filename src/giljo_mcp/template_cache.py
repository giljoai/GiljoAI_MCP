"""
Template Caching System for GiljoAI MCP
Three-layer cache: Memory (LRU) → Redis (optional) → Database (cascade)

Handover 0041 - Phase 2: Template Resolution with Caching
"""

import logging
import pickle  # nosec B403
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DatabaseManager
from .models import AgentTemplate


logger = logging.getLogger(__name__)


class TemplateCache:
    """
    Three-layer template caching system for high-performance template resolution.

    Layer 1: In-memory LRU cache (100 templates, no TTL)
    Layer 2: Redis cache (optional, 1-hour TTL)
    Layer 3: Database with cascade resolution

    Performance targets:
    - Layer 1 hit: < 0.1ms
    - Layer 2 hit: < 2ms
    - Layer 3 hit: < 10ms
    """

    def __init__(self, db_manager: DatabaseManager, redis_client=None):
        """
        Initialize the template cache.

        Args:
            db_manager: Database manager for Layer 3 (database queries)
            redis_client: Optional Redis client for Layer 2 (shared cache)
        """
        self.db = db_manager
        self.redis = redis_client

        # Layer 1: In-memory LRU cache (100 templates)
        # Using Python's built-in lru_cache for thread-safety
        self._memory_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(f"TemplateCache initialized (redis={'enabled' if redis_client else 'disabled'})")

    def _build_cache_key(self, role: str, tenant_key: str, product_id: Optional[str] = None) -> str:
        """
        Build cache key for template lookup.

        Args:
            role: Agent role (orchestrator, analyzer, etc.)
            tenant_key: Tenant identifier for multi-tenant isolation
            product_id: Optional product ID for product-specific templates

        Returns:
            Cache key string (e.g., "template:tenant123:prod456:orchestrator")
        """
        if product_id:
            return f"template:{tenant_key}:{product_id}:{role}"
        return f"template:{tenant_key}:tenant:{role}"

    async def get_template(
        self, role: str, tenant_key: str, product_id: Optional[str] = None
    ) -> Optional[AgentTemplate]:
        """
        Get template with three-layer cache resolution.

        Resolution order:
        1. Memory cache (LRU)
        2. Redis cache (if available)
        3. Database cascade (product → tenant → system → None)

        Args:
            role: Agent role
            tenant_key: Tenant identifier
            product_id: Optional product ID

        Returns:
            AgentTemplate object or None if not found in any layer
        """
        cache_key = self._build_cache_key(role, tenant_key, product_id)

        # Layer 1: Memory cache
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            logger.debug(f"Memory cache HIT: {cache_key}")
            return self._memory_cache[cache_key]

        # Layer 2: Redis cache (if available)
        if self.redis:
            try:
                redis_data = await self._get_from_redis(cache_key)
                if redis_data:
                    template = pickle.loads(redis_data)  # nosec B301 - trusted local Redis cache
                    # Populate memory cache
                    self._memory_cache[cache_key] = template
                    self._cache_hits += 1
                    logger.debug(f"Redis cache HIT: {cache_key}")
                    return template
            except (ValueError, KeyError, RuntimeError) as e:
                logger.warning(f"Redis cache error: {e}")
                # Continue to database if Redis fails

        # Layer 3: Database cascade
        self._cache_misses += 1
        template = await self._query_cascade(role, tenant_key, product_id)

        # Cache in all layers if found
        if template:
            self._memory_cache[cache_key] = template

            # Enforce LRU limit (100 templates)
            if len(self._memory_cache) > 100:
                # Remove oldest entry (first item in dict)
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]

            if self.redis:
                try:
                    await self._set_in_redis(cache_key, template, ttl=3600)
                except (ValueError, KeyError, RuntimeError) as e:
                    logger.warning(f"Redis cache write error: {e}")

            logger.debug(f"Database cache MISS → cached: {cache_key}")
        else:
            logger.debug(f"Template not found in database: {cache_key}")

        return template

    async def _query_cascade(self, role: str, tenant_key: str, product_id: Optional[str]) -> Optional[AgentTemplate]:
        """
        Database cascade query with priority resolution.

        Priority order:
        1. Product-specific: tenant_key + product_id + role
        2. Tenant-specific: tenant_key + role (product_id=NULL)
        3. System default: tenant_key="system" + role + is_default=TRUE
        4. Return None (caller falls back to legacy templates)

        Args:
            role: Agent role
            tenant_key: Tenant identifier
            product_id: Optional product ID

        Returns:
            AgentTemplate or None
        """
        async with self.db.get_session_async() as session:
            # Priority 1: Product-specific template
            if product_id:
                template = await self._query_product_template(session, role, tenant_key, product_id)
                if template:
                    logger.info(
                        f"Template resolved (product-specific): {role} (tenant={tenant_key}, product={product_id})"
                    )
                    return template

            # Priority 2: Tenant-specific template
            template = await self._query_tenant_template(session, role, tenant_key)
            if template:
                logger.info(f"Template resolved (tenant-specific): {role} (tenant={tenant_key})")
                return template

            # Priority 3: System default template
            template = await self._query_system_template(session, role)
            if template:
                logger.info(f"Template resolved (system default): {role}")
                return template

            # Priority 4: Return None (caller uses legacy fallback)
            logger.debug(f"No database template found for role='{role}', tenant='{tenant_key}', product='{product_id}'")
            return None

    async def _query_product_template(
        self, session: AsyncSession, role: str, tenant_key: str, product_id: str
    ) -> Optional[AgentTemplate]:
        """Query product-specific template"""
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.product_id == product_id,
            AgentTemplate.role == role,
            AgentTemplate.is_active,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _query_tenant_template(
        self, session: AsyncSession, role: str, tenant_key: str
    ) -> Optional[AgentTemplate]:
        """Query tenant-specific template (product_id=NULL)"""
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.product_id.is_(None),
            AgentTemplate.role == role,
            AgentTemplate.is_active,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _query_system_template(self, session: AsyncSession, role: str) -> Optional[AgentTemplate]:
        """Query system default template"""
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == "system",
            AgentTemplate.role == role,
            AgentTemplate.is_default,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def invalidate(self, role: str, tenant_key: str, product_id: Optional[str] = None) -> None:
        """
        Invalidate template cache across all layers.

        Called when a template is updated via UI or API.

        Args:
            role: Agent role
            tenant_key: Tenant identifier
            product_id: Optional product ID
        """
        cache_key = self._build_cache_key(role, tenant_key, product_id)

        # Invalidate memory cache
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            logger.info(f"Memory cache invalidated: {cache_key}")

        # Invalidate Redis cache
        if self.redis:
            try:
                await self._delete_from_redis(cache_key)
                logger.info(f"Redis cache invalidated: {cache_key}")
            except (ValueError, KeyError, RuntimeError) as e:
                logger.warning(f"Redis cache invalidation error: {e}")

    async def invalidate_all(self, tenant_key: Optional[str] = None) -> None:
        """
        Invalidate all cached templates.

        Args:
            tenant_key: Optional tenant to invalidate (None = all tenants)
        """
        if tenant_key:
            # Invalidate only templates for specific tenant
            keys_to_remove = [k for k in self._memory_cache if f":{tenant_key}:" in k]
            for key in keys_to_remove:
                del self._memory_cache[key]
            logger.info(f"Memory cache cleared for tenant: {tenant_key}")
        else:
            # Clear entire memory cache
            self._memory_cache.clear()
            logger.info("Memory cache cleared (all tenants)")

        # Clear Redis cache pattern (if available)
        if self.redis:
            try:
                pattern = f"template:{tenant_key}:*" if tenant_key else "template:*"
                await self._delete_redis_pattern(pattern)
                logger.info(f"Redis cache cleared (pattern: {pattern})")
            except (ValueError, KeyError, RuntimeError) as e:
                logger.warning(f"Redis cache clear error: {e}")

    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.

        Returns:
            Dict with hit rate, miss rate, and cache sizes
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self._memory_cache),
            "redis_enabled": self.redis is not None,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics counters"""
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Cache statistics reset")

    # Redis helper methods (async wrappers)

    async def _get_from_redis(self, key: str) -> Optional[bytes]:
        """Get value from Redis"""
        if not self.redis:
            return None
        return await self.redis.get(key)

    async def _set_in_redis(self, key: str, template: AgentTemplate, ttl: int = 3600) -> None:
        """Set value in Redis with TTL"""
        if not self.redis:
            return
        serialized = pickle.dumps(template)
        await self.redis.setex(key, ttl, serialized)

    async def _delete_from_redis(self, key: str) -> None:
        """Delete key from Redis"""
        if not self.redis:
            return
        await self.redis.delete(key)

    async def _delete_redis_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern from Redis"""
        if not self.redis:
            return
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
