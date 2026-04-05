"""
DatabaseManager for GiljoAI MCP with PostgreSQL support.

Provides connection pooling, tenant isolation, and production-ready database management.
"""

from contextlib import asynccontextmanager, contextmanager, suppress
from typing import Any, Optional
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from .logging import ErrorCode, get_logger
from .models import Base
from .tenant import TenantManager


logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections.

    Features:
    - PostgreSQL connection pooling
    - Multi-tenant isolation through filtered queries
    - High-performance async support
    - Production-ready configuration
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        is_async: bool = False,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
    ):
        """
        Initialize DatabaseManager.

        Args:
            database_url: PostgreSQL connection URL. Required.
            is_async: Whether to use async engine and sessions.
            pool_size: Connection pool size. Auto-scaled from system RAM if not set.
            max_overflow: Max overflow connections. Defaults to 2x pool_size.
        """
        if not database_url:
            raise ValueError("Database URL is required")

        self.database_url = database_url
        self.is_async = is_async

        # Auto-scale pool from system RAM if not explicitly set
        if pool_size is None:
            pool_size = self._auto_pool_size()
        if max_overflow is None:
            max_overflow = pool_size * 2

        self.pool_size = pool_size
        self.max_overflow = max_overflow

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

    @staticmethod
    def _auto_pool_size() -> int:
        """Scale connection pool based on available system RAM.

        Returns a pool_size appropriate for the host machine:
            <=4 GB  ->  10
            <=8 GB  ->  20
            <=16 GB ->  30
            <=32 GB ->  40
            >32 GB  ->  50
        """
        try:
            import psutil

            ram_gb = psutil.virtual_memory().total / (1024**3)
        except Exception:  # noqa: BLE001 - Broad catch: psutil may be unavailable or raise any OS-level error
            return 20  # safe default when psutil unavailable

        if ram_gb <= 4:
            return 10
        if ram_gb <= 8:
            return 20
        if ram_gb <= 16:
            return 30
        if ram_gb <= 32:
            return 40
        return 50

    def _create_sync_engine(self) -> Engine:
        """Create synchronous PostgreSQL engine with optimized settings."""
        engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        return engine

    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous PostgreSQL engine with optimized settings."""
        async_url = self.database_url

        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(
            async_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
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
        except (RuntimeError, OSError):
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
            Handles GeneratorExit (BaseException) from FastAPI HTTPException.
            Ensures rollback before close when session is active to prevent
            IllegalStateChangeError.
        """
        if not self.is_async:
            raise RuntimeError("Use get_session() for sync operations")

        session = self.AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except GeneratorExit:
            # GeneratorExit is BaseException (not Exception) - raised by FastAPI
            # when HTTPException occurs or client disconnects
            if hasattr(session, "is_active") and session.is_active:
                with suppress(RuntimeError, OSError):
                    await session.rollback()
            raise
        except Exception:  # Broad catch: session cleanup resilience
            # Regular exceptions - rollback and re-raise
            try:
                await session.rollback()
            except (SQLAlchemyError, RuntimeError) as rollback_error:
                logger.error(
                    "session_rollback_failed",
                    error_code=ErrorCode.DB_TRANSACTION_ROLLBACK.value,
                    error_message=str(rollback_error),
                    exc_info=True,
                )
            raise
        finally:
            # Always close session - but check state first to prevent IllegalStateChangeError
            if hasattr(session, "is_active") and session.is_active:
                with suppress(RuntimeError, OSError):
                    await session.rollback()
            try:
                await session.close()
            except (RuntimeError, OSError, SQLAlchemyError) as close_error:
                logger.debug(f"Session close during cleanup: {close_error}")

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
    def build_postgresql_url(  # nosec B107
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


# Module-level database manager holder
class _DatabaseManagerHolder:
    """Lazy singleton holder to avoid global statement."""

    _instance: Optional[DatabaseManager] = None

    @classmethod
    def get_instance(cls, database_url: Optional[str] = None, is_async: bool = False) -> DatabaseManager:
        if cls._instance is None or (database_url and cls._instance.database_url != database_url):
            cls._instance = DatabaseManager(database_url, is_async)
        return cls._instance

    @classmethod
    def set_instance(cls, manager: DatabaseManager):
        cls._instance = manager


def get_db_manager(database_url: Optional[str] = None, is_async: bool = False) -> DatabaseManager:
    """
    Get or create the global DatabaseManager instance.

    Args:
        database_url: Database connection URL
        is_async: Whether to use async operations

    Returns:
        DatabaseManager instance
    """
    return _DatabaseManagerHolder.get_instance(database_url, is_async)


def set_db_manager(manager: DatabaseManager):
    """Set the global DatabaseManager instance."""
    _DatabaseManagerHolder.set_instance(manager)


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
