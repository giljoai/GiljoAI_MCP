"""
DatabaseManager for GiljoAI MCP with SQLite/PostgreSQL support.

Provides connection pooling, tenant isolation, and seamless database switching.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine, Engine, pool, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import NullPool, QueuePool

from .models import Base


class DatabaseManager:
    """
    Manages database connections with support for both SQLite and PostgreSQL.
    
    Features:
    - Automatic database type detection
    - Connection pooling optimization per database type
    - Tenant isolation through filtered queries
    - Zero-configuration SQLite for local development
    - Production-ready PostgreSQL support
    """
    
    def __init__(self, database_url: Optional[str] = None, is_async: bool = False):
        """
        Initialize DatabaseManager.
        
        Args:
            database_url: Database connection URL. If None, uses SQLite default.
            is_async: Whether to use async engine and sessions.
        """
        self.database_url = database_url or self._get_default_database_url()
        self.is_async = is_async
        self.is_sqlite = "sqlite" in self.database_url
        self.is_postgresql = "postgresql" in self.database_url
        
        # Initialize engines and session factories
        if self.is_async:
            self.async_engine = self._create_async_engine()
            self.AsyncSessionLocal = sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        else:
            self.engine = self._create_sync_engine()
            self.SessionLocal = scoped_session(
                sessionmaker(
                    self.engine,
                    expire_on_commit=False
                )
            )
    
    def _get_default_database_url(self) -> str:
        """Get default database URL (SQLite for zero-config local dev)."""
        db_dir = Path.home() / ".giljo-mcp" / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "giljo_mcp.db"
        return f"sqlite:///{db_path}"
    
    def _create_sync_engine(self) -> Engine:
        """Create synchronous SQLAlchemy engine with optimized settings."""
        if self.is_sqlite:
            # SQLite optimizations
            engine = create_engine(
                self.database_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30
                },
                poolclass=pool.StaticPool,
                echo=False
            )
            
            # Enable foreign keys and WAL mode for SQLite
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
                
        elif self.is_postgresql:
            # PostgreSQL optimizations
            engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        else:
            # Generic database
            engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_pre_ping=True,
                echo=False
            )
        
        return engine
    
    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous SQLAlchemy engine with optimized settings."""
        # Convert URL for async drivers
        async_url = self.database_url
        if self.is_sqlite:
            async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.is_postgresql:
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
        
        if self.is_sqlite:
            # SQLite async optimizations
            engine = create_async_engine(
                async_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30
                },
                poolclass=pool.StaticPool,
                echo=False
            )
        elif self.is_postgresql:
            # PostgreSQL async optimizations
            engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        else:
            # Generic async database
            engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                pool_pre_ping=True,
                echo=False
            )
        
        return engine
    
    def create_tables(self):
        """Create all database tables (sync)."""
        if not self.is_async:
            Base.metadata.create_all(bind=self.engine)
        else:
            raise RuntimeError("Use create_tables_async() for async engine")
    
    async def create_tables_async(self):
        """Create all database tables (async)."""
        if self.is_async:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise RuntimeError("Use create_tables() for sync engine")
    
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
        Get a database session (async).
        
        Usage:
            async with db_manager.get_session_async() as session:
                # Use session
        """
        if not self.is_async:
            raise RuntimeError("Use get_session() for sync operations")
        
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
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
        password: str = ""
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
    
    @staticmethod
    def build_sqlite_url(db_path: Optional[Path] = None) -> str:
        """
        Build a SQLite connection URL.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default.
            
        Returns:
            SQLite connection URL
        """
        if db_path is None:
            db_dir = Path.home() / ".giljo-mcp" / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "giljo_mcp.db"
        
        return f"sqlite:///{db_path}"
    
    def get_tenant_filter(self, tenant_key: str) -> Dict[str, Any]:
        """
        Get filter dictionary for tenant isolation.
        
        Args:
            tenant_key: The tenant key to filter by
            
        Returns:
            Filter dictionary for SQLAlchemy queries
        """
        return {"tenant_key": tenant_key}


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