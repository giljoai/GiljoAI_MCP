"""
Project Closeout MCP Tool (Handover 013B - Refactored)

Handles project completion and updates product memory with sequential history entries.

REMOVED: GitHub API integration (over-engineered)
Git integration is handled by CLI agents (Claude Code, Codex, Gemini).
This tool now only stores project history in product_memory.sequential_history.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)




def register_project_closeout_tools(
    mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager
):
    """Register project closeout tools with the MCP server"""

    @mcp.tool()
    async def close_project_and_update_memory_wrapper(
        project_id: str,
        summary: str,
        key_outcomes: List[str],
        decisions_made: List[str],
        tenant_key: str,
    ) -> Dict[str, Any]:
        """
        MCP wrapper for close_project_and_update_memory.

        Automatically injects db_manager dependency.
        """
        return await close_project_and_update_memory(
            project_id=project_id,
            summary=summary,
            key_outcomes=key_outcomes,
            decisions_made=decisions_made,
            tenant_key=tenant_key,
            db_manager=db_manager,
        )
