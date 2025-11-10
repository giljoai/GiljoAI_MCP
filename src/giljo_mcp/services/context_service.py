"""
ContextService - Dedicated service for context and vision document management

This service extracts all context-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- Context document indexing (placeholder/stub functionality)
- Vision document management (placeholder/stub functionality)
- Product settings retrieval
- Context discovery (deprecated - returns error messages)

Design Principles:
- Single Responsibility: Only context domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently

Note: Many methods in this service are currently stubs or deprecated.
They are kept for backward compatibility and will be removed in v3.2.0.
"""

import logging
from typing import Any, Optional

from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ContextService:
    """
    Service for managing context and vision documents.

    This service handles context-related operations. Note that many
    methods are currently stubs or deprecated as the thin client
    architecture (Handover 0088) provides context via other means.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize ContextService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Context Index (Stub)
    # ============================================================================

    async def get_context_index(
        self,
        product_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get the context index for intelligent querying.

        Note: This is currently a stub implementation returning empty data.
        Future implementation will provide actual context indexing.

        Args:
            product_id: Optional product ID to get context for

        Returns:
            Dict with success status and empty index

        Example:
            >>> result = await service.get_context_index(product_id="prod-123")
            >>> print(result["index"])
        """
        self._logger.debug(f"get_context_index called for product_id={product_id} (stub)")

        return {
            "success": True,
            "index": {
                "documents": [],
                "sections": []
            }
        }

    # ============================================================================
    # Vision Document (Stub)
    # ============================================================================

    async def get_vision(
        self,
        part: int = 1,
        max_tokens: int = 20000
    ) -> dict[str, Any]:
        """
        Get a vision document part.

        Note: This is currently a stub implementation returning placeholder data.
        Future implementation will provide actual vision document content.

        Args:
            part: Document part number (default: 1)
            max_tokens: Maximum tokens to return (default: 20000)

        Returns:
            Dict with success status and placeholder content

        Example:
            >>> result = await service.get_vision(part=1, max_tokens=10000)
            >>> print(result["content"])
        """
        self._logger.debug(f"get_vision called for part={part}, max_tokens={max_tokens} (stub)")

        return {
            "success": True,
            "part": part,
            "total_parts": 1,
            "content": "Vision document placeholder",
            "tokens": 100,
        }

    async def get_vision_index(self) -> dict[str, Any]:
        """
        Get the vision document index.

        Note: This is currently a stub implementation returning empty data.
        Future implementation will provide actual vision document indexing.

        Returns:
            Dict with success status and empty index

        Example:
            >>> result = await service.get_vision_index()
            >>> print(result["index"])
        """
        self._logger.debug("get_vision_index called (stub)")

        return {
            "success": True,
            "index": {
                "files": [],
                "chunks": []
            }
        }

    # ============================================================================
    # Product Settings (Stub)
    # ============================================================================

    async def get_product_settings(
        self,
        product_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get all product settings for analysis.

        Note: This is currently a stub implementation returning placeholder data.
        Future implementation will retrieve actual product settings from database.

        Args:
            product_id: Optional product ID

        Returns:
            Dict with success status and placeholder settings

        Example:
            >>> result = await service.get_product_settings(product_id="prod-123")
            >>> print(result["settings"])
        """
        self._logger.debug(f"get_product_settings called for product_id={product_id} (stub)")

        return {
            "success": True,
            "settings": {
                "product_id": product_id or "default",
                "config": {}
            },
        }

    # ============================================================================
    # Deprecated Methods (Return Error Messages)
    # ============================================================================

    async def discover_context(
        self,
        project_id: Optional[str] = None,
        path: Optional[str] = None,
        agent_role: str = "default",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.

        This tool was a placeholder for context discovery functionality.
        Thin client architecture (Handover 0088) eliminated the need for this tool.
        Agents access context directly via IDE tools and get_agent_mission().
        This method will be removed in v3.2.0.

        Migration:
            # OLD (obsolete stub)
            await discover_context(project_id=project_id, agent_role="implementer")

            # NEW (no replacement needed)
            # Context provided via:
            # 1. get_agent_mission() - returns mission with embedded context
            # 2. IDE tools (Read, Grep, Glob) - direct file/codebase access

        Returns:
            Dict with error status and deprecation message
        """
        self._logger.warning(
            f"discover_context called (deprecated) - "
            f"project_id={project_id}, path={path}, agent_role={agent_role}"
        )

        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Thin client architecture eliminated need for this tool.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Agents access context via get_agent_mission() and IDE tools (Read, Grep, Glob)."
        }

    async def get_file_context(self, file_path: str) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.

        This tool was a placeholder directing users to Serena MCP tools.
        Agents access files directly via IDE tools (Read, Grep).
        This method will be removed in v3.2.0.

        Migration:
            # OLD (obsolete stub)
            await get_file_context(file_path="src/main.py")

            # NEW (no replacement needed)
            # Use IDE tools directly:
            # - Read tool for file contents
            # - mcp__serena__read_file for file reading
            # - mcp__serena__get_symbols_overview for code structure

        Returns:
            Dict with error status and deprecation message
        """
        self._logger.warning(f"get_file_context called (deprecated) - file_path={file_path}")

        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Agents access files directly via IDE tools.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Use Read tool or Serena MCP (read_file, get_symbols_overview) for file access."
        }

    async def search_context(
        self,
        query: str,
        file_types: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.

        This tool was a placeholder directing users to Serena MCP grep tools.
        Agents use IDE search capabilities (Grep tool) directly.
        This method will be removed in v3.2.0.

        Migration:
            # OLD (obsolete stub)
            await search_context(query="class MyClass", file_types=["*.py"])

            # NEW (no replacement needed)
            # Use IDE tools directly:
            # - Grep tool for pattern search
            # - mcp__serena__search_for_pattern for regex search
            # - Glob tool for file name patterns

        Returns:
            Dict with error status and deprecation message
        """
        self._logger.warning(
            f"search_context called (deprecated) - query={query}, file_types={file_types}"
        )

        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Agents use IDE search capabilities (Grep tool) directly.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Use Grep tool or Serena MCP (search_for_pattern) for content search."
        }

    async def get_context_summary(
        self,
        project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.

        This tool was a placeholder for project context summaries.
        Thin client architecture (Handover 0088) provides context via get_agent_mission().
        Mission includes all necessary context for agents.
        This method will be removed in v3.2.0.

        Migration:
            # OLD (obsolete stub)
            await get_context_summary(project_id=project_id)

            # NEW (no replacement needed)
            # Context summary provided via:
            # - get_agent_mission() returns mission with embedded context
            # - Mission field includes project/product context

        Returns:
            Dict with error status and deprecation message
        """
        self._logger.warning(f"get_context_summary called (deprecated) - project_id={project_id}")

        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Mission from get_agent_mission() provides context.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Context provided via get_agent_mission() - mission field includes all necessary context."
        }
