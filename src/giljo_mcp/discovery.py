"""
Dynamic Discovery System for GiljoAI MCP
Provides priority-based context loading with role-specific filtering
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml
from sqlalchemy import select

from .context_manager import get_filtered_config, get_full_config, is_orchestrator
from .database import DatabaseManager
from .models import Configuration, Product, Project
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
    Manages dynamic context discovery with priority-based loading.
    Implements role-based filtering and token optimization.
    """

    PRIORITY_ORDER: ClassVar[list[str]] = [
        "vision",  # Priority 1: Product vision documents
        "config",  # Priority 2: Configuration (yaml + database)
        "docs",  # Priority 3: Documentation (CLAUDE.md, README)
        "memories",  # Priority 4: Session memories
        "code",  # Priority 5: Code via Serena MCP
    ]

    ROLE_PRIORITIES: ClassVar[dict[str, list[str]]] = {
        "orchestrator": ["vision", "config", "docs", "memories"],
        "analyzer": ["vision", "docs", "code"],
        "implementer": ["docs", "code", "config"],
        "tester": ["docs", "code", "memories"],
        "default": ["config", "docs"],  # Fallback for unknown roles
    }

    ROLE_TOKEN_LIMITS: ClassVar[dict[str, int]] = {
        "orchestrator": 50000,  # Needs full vision
        "analyzer": 30000,  # Focused analysis
        "implementer": 40000,  # Technical details
        "tester": 20000,  # Test specifics
        "default": 25000,  # Default limit
    }

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        path_resolver: PathResolver,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self.path_resolver = path_resolver
        self.serena_hooks = SerenaHooks(db_manager, tenant_manager)
        self._content_hashes = {}

    async def discover_context(
        self, agent_role: str, project_id: str, agent_name: Optional[str] = None, force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Main discovery method with role-based filtering.

        Args:
            agent_role: Role of the agent requesting context
            project_id: Project ID for context
            agent_name: Optional agent name for precise filtering
            force_refresh: Force fresh discovery ignoring cache

        Returns:
            Discovered context organized by priority
        """
        # Get role-specific priorities
        priorities = self.ROLE_PRIORITIES.get(agent_role, self.ROLE_PRIORITIES["default"])
        token_limit = self.ROLE_TOKEN_LIMITS.get(agent_role, self.ROLE_TOKEN_LIMITS["default"])

        # Clear cache if forced refresh
        if force_refresh:
            self.path_resolver.clear_cache()
            self._content_hashes.clear()

        # Load context by priority (pass agent_name for filtering)
        context = await self.load_by_priority(
            priorities, project_id, token_limit, agent_name=agent_name, agent_role=agent_role
        )

        # Add metadata
        context["metadata"] = {
            "agent_role": agent_role,
            "agent_name": agent_name,
            "priorities_used": priorities,
            "token_limit": token_limit,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
        }

        return context

    async def load_by_priority(
        self,
        priorities: list[str],
        project_id: str,
        token_limit: int,
        agent_name: Optional[str] = None,
        agent_role: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Load context in priority order with token limits.

        Args:
            priorities: List of context types in priority order
            project_id: Project ID
            token_limit: Maximum tokens to load
            agent_name: Optional agent name for filtering
            agent_role: Optional agent role for filtering

        Returns:
            Loaded context by type
        """
        context = {}
        tokens_used = 0

        for priority in priorities:
            if tokens_used >= token_limit:
                logger.info(f"Token limit reached at {tokens_used}/{token_limit}")
                break

            remaining_tokens = token_limit - tokens_used

            try:
                if priority == "vision":
                    result = await self._load_vision(project_id, remaining_tokens)
                elif priority == "config":
                    result = await self._load_config(project_id, remaining_tokens, agent_name, agent_role)
                elif priority == "docs":
                    result = await self._load_docs(project_id, remaining_tokens)
                elif priority == "memories":
                    result = await self._load_memories(project_id, remaining_tokens)
                elif priority == "code":
                    result = await self._load_code(project_id, remaining_tokens)
                else:
                    logger.warning(f"Unknown priority type: {priority}")
                    continue

                if result:
                    context[priority] = result["content"]
                    tokens_used += result.get("tokens", 0)

            except Exception as e:
                logger.exception("Failed to load {priority}")
                context[priority] = {"error": str(e)}

        context["tokens_used"] = tokens_used
        return context

    async def get_discovery_paths(self, project_id: Optional[str] = None) -> dict[str, Path]:
        """
        Get all configured paths dynamically.

        Args:
            project_id: Optional project ID for project-specific paths

        Returns:
            Dictionary of path keys to resolved paths
        """
        return await self.path_resolver.get_all_paths(project_id)

    async def _load_vision(self, project_id: str, max_tokens: int) -> Optional[dict]:
        """
        Legacy method - Vision model removed in Handover 0728.
        Vision functionality now handled by VisionDocument (product-centric).
        """
        return None

    async def _load_config(
        self, project_id: str, max_tokens: int, agent_name: Optional[str] = None, agent_role: Optional[str] = None
    ) -> Optional[dict]:
        """
        Load configuration from database and files.

        Args:
            project_id: Project ID
            max_tokens: Maximum tokens to load
            agent_name: Optional agent name for filtering
            agent_role: Optional agent role for filtering
        """
        try:
            config_data = {}

            # Load from database
            async with self.db_manager.get_session_async() as session:
                # Get project to find product
                project_query = select(Project).where(Project.id == project_id)
                result = await session.execute(project_query)
                project = result.scalar_one_or_none()

                if project and project.product_id:
                    # Get product config_data
                    product_query = select(Product).where(Product.id == project.product_id)
                    result = await session.execute(product_query)
                    product = result.scalar_one_or_none()

                    if product and product.config_data:
                        # Apply role-based filtering
                        if agent_name and is_orchestrator(agent_name, agent_role):
                            # Orchestrator gets FULL config
                            config_data["product_config"] = get_full_config(product)
                            logger.info("Loaded FULL product config for orchestrator")
                        elif agent_name:
                            # Worker agents get FILTERED config
                            config_data["product_config"] = get_filtered_config(agent_name, product, agent_role)
                            logger.info(f"Loaded FILTERED product config for {agent_name}")
                        else:
                            # No agent specified - return full (backward compatible)
                            config_data["product_config"] = dict(product.config_data)

                # Load standard Configuration entries
                config_query = select(Configuration).where(Configuration.project_id == project_id)
                result = await session.execute(config_query)
                configs = result.scalars().all()

                config_data["database"] = {config.key: config.value for config in configs}

            # Load from config.yaml
            config_path = await self.path_resolver.resolve_path("config", project_id)
            yaml_path = config_path / "config.yaml"
            if not yaml_path.exists():
                yaml_path = Path("config.yaml")

            if yaml_path.exists():
                with open(yaml_path, encoding="utf-8") as f:
                    config_data["yaml"] = yaml.safe_load(f)

            # Estimate tokens (rough approximation)
            content_str = json.dumps(config_data)
            estimated_tokens = len(content_str) // 4

            if estimated_tokens > max_tokens:
                # Truncate if needed
                config_data["truncated"] = True

            return {"content": config_data, "tokens": min(estimated_tokens, max_tokens)}

        except Exception:
            logger.exception("Failed to load config")

        return None

    async def _load_docs(self, project_id: str, max_tokens: int) -> Optional[dict]:
        """Load documentation files"""
        try:
            docs_path = await self.path_resolver.resolve_path("docs", project_id)
            docs_data = {}
            tokens_used = 0

            # Priority docs to load
            priority_files = ["CLAUDE.md", "README.md", "PROJECT_ORCHESTRATION_PLAN.md"]

            for filename in priority_files:
                if tokens_used >= max_tokens:
                    break

                file_path = Path(filename) if filename == "CLAUDE.md" else docs_path / filename

                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")

                    # Estimate tokens
                    file_tokens = len(content) // 4

                    if tokens_used + file_tokens <= max_tokens:
                        docs_data[filename] = content
                        tokens_used += file_tokens
                    else:
                        # Partial load
                        remaining = max_tokens - tokens_used
                        chars_to_load = remaining * 4
                        docs_data[filename] = content[:chars_to_load] + "\n... [truncated]"
                        tokens_used = max_tokens

            return {"content": docs_data, "tokens": tokens_used}

        except Exception:
            logger.exception("Failed to load docs")

        return None

    async def _load_memories(self, project_id: str, max_tokens: int) -> Optional[dict]:
        """Load session memories and project artifacts"""
        try:
            memories_data = {}
            tokens_used = 0

            # Load from sessions directory
            sessions_path = await self.path_resolver.resolve_path("sessions", project_id)

            if sessions_path.exists() and sessions_path.is_dir():
                # Get most recent session files
                session_files = sorted(
                    sessions_path.glob("*.md"),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True,
                )[:5]  # Last 5 sessions

                for file in session_files:
                    if tokens_used >= max_tokens:
                        break

                    content = file.read_text(encoding="utf-8")
                    file_tokens = len(content) // 4

                    if tokens_used + file_tokens <= max_tokens:
                        memories_data[file.name] = content
                        tokens_used += file_tokens

            # Load from Serena memories if available
            serena_path = await self.path_resolver.resolve_path("memories", project_id)
            if serena_path.exists() and serena_path.is_dir():
                memory_files = list(serena_path.glob("*.md"))[:3]  # Recent memories

                for file in memory_files:
                    if tokens_used >= max_tokens:
                        break

                    content = file.read_text(encoding="utf-8")
                    file_tokens = len(content) // 4

                    if tokens_used + file_tokens <= max_tokens:
                        memories_data[f"serena/{file.name}"] = content
                        tokens_used += file_tokens

            return {"content": memories_data, "tokens": tokens_used}

        except Exception:
            logger.exception("Failed to load memories")

        return None

    async def _load_code(self, project_id: str, max_tokens: int) -> Optional[dict]:
        """Load code context via Serena MCP hooks"""
        try:
            # This will be expanded with actual Serena MCP integration
            code_data = {
                "message": "Code discovery via Serena MCP",
                "available_tools": [
                    "find_symbol",
                    "get_symbols_overview",
                    "search_for_pattern",
                    "find_referencing_symbols",
                ],
                "recommendation": "Use Serena MCP tools for code exploration",
            }

            return {
                "content": code_data,
                "tokens": 100,  # Minimal tokens for the message
            }

        except Exception:
            logger.exception("Failed to load code context")

        return None

    def calculate_content_hash(self, content: str) -> str:
        """Calculate MD5 hash of content for change detection"""
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    async def detect_changes(self, project_id: str) -> dict[str, bool]:
        """
        Detect if any content has changed since last discovery.

        Args:
            project_id: Project ID

        Returns:
            Dictionary of content types and whether they changed
        """
        changes = {}

        try:
            paths = await self.get_discovery_paths(project_id)

            for path_key, path in paths.items():
                if path.exists():
                    if path.is_file():
                        content = path.read_text(encoding="utf-8")
                        new_hash = self.calculate_content_hash(content)
                        old_hash = self._content_hashes.get(f"{project_id}:{path_key}")
                        changes[path_key] = new_hash != old_hash
                        self._content_hashes[f"{project_id}:{path_key}"] = new_hash
                    elif path.is_dir():
                        # Check directory modification time
                        changes[path_key] = True  # Simplified - could be enhanced
        except Exception:
            logger.exception("Failed to detect changes")

        return changes


class SerenaHooks:
    """
    Integration hooks for Serena MCP server.
    Provides lazy loading and token-optimized code discovery.
    """

    def __init__(self, db_manager: "DatabaseManager", tenant_manager: "TenantManager"):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._symbol_cache = {}
        self._cache_ttl = timedelta(minutes=10)

    async def lazy_load_symbols(self, file_path: str, depth: int = 0, max_chars: int = 5000) -> dict[str, Any]:
        """
        Load symbols only when needed.

        Args:
            file_path: Path to the file
            depth: Depth of symbol tree to retrieve
            max_chars: Maximum characters to return

        Returns:
            Symbol information
        """
        # This is a placeholder for Serena MCP integration
        # In actual implementation, this would call Serena MCP tools
        return {
            "file": file_path,
            "symbols": [],
            "message": "Use mcp__serena-mcp__get_symbols_overview for actual symbols",
        }

    async def search_codebase(
        self, pattern: str, max_chars: int = 5000, paths_include: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Token-optimized code search.

        Args:
            pattern: Search pattern
            max_chars: Maximum characters in response
            paths_include: Optional glob pattern for files

        Returns:
            Search results
        """
        # Placeholder for Serena MCP integration
        return {
            "pattern": pattern,
            "results": [],
            "message": "Use mcp__serena-mcp__search_for_pattern for actual search",
        }

    async def get_file_overview(self, path: str) -> dict[str, Any]:
        """
        Get file structure without reading content.

        Args:
            path: Directory or file path

        Returns:
            File structure overview
        """
        # Placeholder for Serena MCP integration
        return {
            "path": path,
            "structure": {},
            "message": "Use mcp__serena-mcp__list_dir for actual structure",
        }

    def clear_cache(self):
        """Clear symbol cache"""
        self._symbol_cache.clear()
