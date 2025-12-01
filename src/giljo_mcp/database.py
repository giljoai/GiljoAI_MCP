"""
DatabaseManager for GiljoAI MCP with PostgreSQL support.

Provides connection pooling, tenant isolation, and production-ready database management.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Optional
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base
from .tenant import TenantManager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections.

    Features:
    - PostgreSQL connection pooling
    - Multi-tenant isolation through filtered queries
    - High-performance async support
    - Production-ready configuration
    """

    def __init__(self, database_url: Optional[str] = None, is_async: bool = False):
        """
        Initialize DatabaseManager.

        Args:
            database_url: PostgreSQL connection URL. Required.
            is_async: Whether to use async engine and sessions.
        """
        if not database_url:
            raise ValueError("Database URL is required")

        self.database_url = database_url
        self.is_async = is_async

        # Validate database URL - PostgreSQL only
        if "postgresql" not in self.database_url:
            raise ValueError("Only PostgreSQL databases are supported")

        # Initialize engines and session factories
        if self.is_async:
            self.async_engine = self._create_async_engine()
            self.AsyncSessionLocal = sessionmaker(self.async_engine, class_=AsyncSession, expire_on_commit=False)
        else:
            self.engine = self._create_sync_engine()
            self.SessionLocal = scoped_session(sessionmaker(self.engine, expire_on_commit=False))

    def _create_sync_engine(self) -> Engine:
        """Create synchronous PostgreSQL engine with optimized settings."""
        # PostgreSQL optimizations
        engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        return engine

    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous PostgreSQL engine with optimized settings."""
        # Convert URL for async drivers
        async_url = self.database_url

        # Only replace if not already an async dialect
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # PostgreSQL async optimizations
        # Note: AsyncEngine handles pooling internally, don't specify poolclass
        engine = create_async_engine(
            async_url,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

        return engine

    def create_tables(self):
        """Create all database tables (sync)."""
        if not self.is_async:
            Base.metadata.create_all(bind=self.engine)
        else:
            raise RuntimeError("Use create_tables_async() for async engine")

    async def create_tables_async(self):
        """
        Create all database tables (async).

        Handover 0017: pg_trgm extension is created during installation by installer/core/database.py
        with proper superuser privileges. Application does not require CREATE privilege on database.
        """
        if self.is_async:
            async with self.async_engine.begin() as conn:
                # Create all tables
                # Extensions are now created during installation phase, not at runtime
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise RuntimeError("Use create_tables() for async engine")

    def drop_tables(self):
        """Drop all database tables (sync). USE WITH CAUTION!"""
        if not self.is_async:
            Base.metadata.drop_all(bind=self.engine)
        else:
            raise RuntimeError("Use drop_tables_async() for async engine")

    async def drop_tables_async(self):
        """Drop all database tables (async). USE WITH CAUTION!"""
        if self.is_async:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        else:
            raise RuntimeError("Use drop_tables() for sync engine")

    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session (sync).

        Usage:
            with db_manager.get_session() as session:
                # Use session
        """
        if self.is_async:
            raise RuntimeError("Use get_session_async() for async operations")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_session_async(self) -> AsyncSession:
        """
        Get a database session (async) with automatic cleanup.

        Usage:
            async with db_manager.get_session_async() as session:
                # Use session

        Note:
            The async context manager handles all session cleanup automatically.
            No manual close() needed - prevents IllegalStateChangeError.
        """
        if not self.is_async:
            raise RuntimeError("Use get_session() for sync operations")

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                # Rollback on any exception
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    # Log rollback failures but don't suppress original exception
                    logger.error(f"Session rollback failed: {rollback_error}", exc_info=True)
                raise
            # No finally block needed - context manager handles cleanup

    def close(self):
        """Close database connections (sync)."""
        if not self.is_async:
            self.SessionLocal.remove()
            self.engine.dispose()
        else:
            raise RuntimeError("Use close_async() for async engine")

    async def close_async(self):
        """Close database connections (async)."""
        if self.is_async:
            await self.async_engine.dispose()
        else:
            raise RuntimeError("Use close() for sync engine")

    @staticmethod
    def build_postgresql_url(
        host: str = "localhost",
        port: int = 5432,
        database: str = "giljo_mcp",
        username: str = "postgres",
        password: str = "",
    ) -> str:
        """
        Build a PostgreSQL connection URL.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password

        Returns:
            PostgreSQL connection URL
        """
        if password:
            password = quote_plus(password)
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        return f"postgresql://{username}@{host}:{port}/{database}"

    def get_tenant_filter(self, tenant_key: str) -> dict[str, Any]:
        """
        Get filter dictionary for tenant isolation.

        Args:
            tenant_key: The tenant key to filter by

        Returns:
            Filter dictionary for SQLAlchemy queries
        """
        return {"tenant_key": tenant_key}

    def apply_tenant_filter(self, query: Any, model: Any, tenant_key: Optional[str] = None) -> Any:
        """
        Apply tenant filtering to a query using TenantManager.

        Args:
            query: SQLAlchemy query object
            model: Model class being queried
            tenant_key: Specific tenant key or None to use current context

        Returns:
            Query with tenant filter applied
        """
        return TenantManager.apply_tenant_filter(query, model, tenant_key)

    def ensure_tenant_isolation(self, entity: Any, tenant_key: Optional[str] = None) -> None:
        """
        Ensure entity belongs to the correct tenant.

        Args:
            entity: Entity to check
            tenant_key: Expected tenant key (uses current context if None)

        Raises:
            PermissionError: If entity belongs to different tenant
        """
        TenantManager.ensure_tenant_isolation(entity, tenant_key)

    def with_tenant(self, tenant_key: str):
        """
        Context manager for tenant-scoped operations.

        Usage:
            with db_manager.with_tenant("tk_abc123..."):
                # All database operations use this tenant
                session = db_manager.get_session()
        """
        return TenantManager.with_tenant(tenant_key)

    @contextmanager
    def get_tenant_session(self, tenant_key: str):
        """
        Get a session with automatic tenant filtering.

        Args:
            tenant_key: Tenant key for this session

        Yields:
            Session configured with tenant context
        """
        with TenantManager.with_tenant(tenant_key), self.get_session() as session:
            # Add tenant key to session info for reference
            session.info["tenant_key"] = tenant_key
            yield session

    @asynccontextmanager
    async def get_tenant_session_async(self, tenant_key: str):
        """
        Get an async session with automatic tenant filtering.

        Args:
            tenant_key: Tenant key for this session

        Yields:
            AsyncSession configured with tenant context
        """
        with TenantManager.with_tenant(tenant_key):
            async with self.get_session_async() as session:
                # Add tenant key to session info for reference
                session.info["tenant_key"] = tenant_key
                yield session

    def query_with_tenant(self, session: Session, model: Any, tenant_key: Optional[str] = None):
        """
        Create a select statement with automatic tenant filtering.

        DEPRECATED: Use select(model).where() directly with async sessions.
        This method is kept for backward compatibility with sync sessions.

        Args:
            session: Database session
            model: Model to query
            tenant_key: Tenant key (uses current context if None)

        Returns:
            Select statement with tenant filter pre-applied
        """
        # For SQLAlchemy 2.0 compatibility, return select statement
        stmt = select(model)
        if hasattr(model, "tenant_key"):
            if tenant_key is None:
                tenant_key = TenantManager.get_current_tenant()
            if tenant_key:
                stmt = stmt.where(model.tenant_key == tenant_key)
        return stmt

    def validate_tenant_key(self, tenant_key: Optional[str]) -> bool:
        """
        Validate a tenant key using TenantManager.

        Args:
            tenant_key: Key to validate

        Returns:
            True if valid, False otherwise
        """
        return TenantManager.validate_tenant_key(tenant_key)

    def generate_tenant_key(self, project_name: Optional[str] = None) -> str:
        """
        Generate a new tenant key for a project.

        Args:
            project_name: Optional project name for metadata

        Returns:
            New tenant key
        """
        return TenantManager.generate_tenant_key(project_name)


# Global instance for convenience (can be overridden)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None, is_async: bool = False) -> DatabaseManager:
    """
    Get or create the global DatabaseManager instance.

    Args:
        database_url: Database connection URL
        is_async: Whether to use async operations

    Returns:
        DatabaseManager instance
    """
    global _db_manager

    if _db_manager is None or (database_url and _db_manager.database_url != database_url):
        _db_manager = DatabaseManager(database_url, is_async)

    return _db_manager


def set_db_manager(manager: DatabaseManager):
    """Set the global DatabaseManager instance."""
    global _db_manager
    _db_manager = manager


async def init_db(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Initialize database with table creation.

    Convenience function for tests and quick setup.

    Args:
        database_url: PostgreSQL connection URL. Required.

    Returns:
        DatabaseManager: Configured database manager with tables created.
    """
    db_manager = DatabaseManager(database_url, is_async=True)
    await db_manager.create_tables_async()
    return db_manager
