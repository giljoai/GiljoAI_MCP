"""
Dynamic Discovery System for GiljoAI MCP
Provides dynamic path resolution for context loading.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import ClassVar, Optional

import yaml
from sqlalchemy import select

from .database import DatabaseManager
from .models import Configuration
from .tenant import TenantManager


logger = logging.getLogger(__name__)


class PathResolver:
    """
    Resolves paths dynamically with multiple fallback options.
    Resolution order: environment variables -> database -> config.yaml -> defaults
    """

    DEFAULT_PATHS: ClassVar[dict[str, str]] = {
        "vision": "docs/vision",
        "sessions": "docs/sessions",
        "devlog": "docs/devlog",
        "memories": ".serena/memories",
        "docs": "docs",
        "config": ".giljo-mcp",
        "logs": "logs",
        "data": "data",
    }

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps = {}

    async def resolve_path(self, path_key: str, project_id: Optional[str] = None) -> Path:
        """
        Resolve a path key to an actual filesystem path.

        Args:
            path_key: Key identifying the path (e.g., 'vision', 'sessions')
            project_id: Optional project ID for project-specific paths

        Returns:
            Resolved Path object
        """
        # Check cache first
        cache_key = f"{path_key}:{project_id or 'global'}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # 1. Check environment variables (highest priority)
        env_var = f"GILJO_MCP_PATH_{path_key.upper()}"
        if env_var in os.environ:
            resolved = Path(os.environ[env_var])
            self._update_cache(cache_key, resolved)
            return resolved

        # 2. Check database configuration
        if project_id:
            db_path = await self._get_database_path(path_key, project_id)
            if db_path:
                resolved = Path(db_path)
                self._update_cache(cache_key, resolved)
                return resolved

        # 3. Check config.yaml
        config_path = await self._get_config_file_path(path_key)
        if config_path:
            resolved = Path(config_path)
            self._update_cache(cache_key, resolved)
            return resolved

        # 4. Use defaults
        default = self.DEFAULT_PATHS.get(path_key, path_key)
        resolved = Path(default)
        self._update_cache(cache_key, resolved)
        return resolved

    async def get_all_paths(self, project_id: Optional[str] = None) -> dict[str, Path]:
        """
        Get all resolved paths for the current project.

        Args:
            project_id: Optional project ID

        Returns:
            Dictionary of path keys to resolved Path objects
        """
        paths = {}
        for key in self.DEFAULT_PATHS:
            paths[key] = await self.resolve_path(key, project_id)
        return paths

    async def _get_database_path(self, path_key: str, project_id: str) -> Optional[str]:
        """Get path override from database"""
        try:
            async with self.db_manager.get_session_async() as session:
                config_query = select(Configuration).where(
                    Configuration.project_id == project_id,
                    Configuration.key == f"path.{path_key}",
                    Configuration.category == "paths",
                )
                result = await session.execute(config_query)
                config = result.scalar_one_or_none()

                if config and config.value:
                    return config.value
        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Failed to get database path for {path_key}: {e}")

        return None

    async def _get_config_file_path(self, path_key: str) -> Optional[str]:
        """Get path from config.yaml"""
        try:
            config_path = Path.home() / ".giljo-mcp" / "config.yaml"
            if not config_path.exists():
                config_path = Path("config.yaml")

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                # Look for paths section
                paths = config.get("paths", {})
                if path_key in paths:
                    return paths[path_key]
        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Failed to get config file path for {path_key}: {e}")

        return None

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached path is still valid"""
        if cache_key not in self._cache:
            return False

        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False

        return datetime.now(timezone.utc) - timestamp < self._cache_ttl

    def _update_cache(self, cache_key: str, path: Path):
        """Update path cache"""
        self._cache[cache_key] = path
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)

    def clear_cache(self):
        """Clear all cached paths"""
        self._cache.clear()
        self._cache_timestamps.clear()


class DiscoveryManager:
    """
    Manages dynamic context discovery with path resolution.
    Context loading is handled by the fetch_context MCP tool (Handover 0350a-c).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        path_resolver: PathResolver,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self.path_resolver = path_resolver

    async def get_discovery_paths(self, project_id: Optional[str] = None) -> dict[str, Path]:
        """
        Get all configured paths dynamically.

        Args:
            project_id: Optional project ID for project-specific paths

        Returns:
            Dictionary of path keys to resolved paths
        """
        return await self.path_resolver.get_all_paths(project_id)


class SerenaHooks:
    """
    Integration hooks for Serena MCP server.
    Placeholder class retained for backward compatibility.
    """

    def __init__(self, db_manager: "DatabaseManager", tenant_manager: "TenantManager"):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._symbol_cache = {}
        self._cache_ttl = timedelta(minutes=10)
