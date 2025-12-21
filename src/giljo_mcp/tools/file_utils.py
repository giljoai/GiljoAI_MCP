"""
MCP Tool: File Existence Utility

Provides lightweight file/directory existence checking within tenant workspace.
Prevents token waste from reading entire files just to check existence.

Handover 0360 Feature 3: File Existence Utility
"""

import logging
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product


logger = logging.getLogger(__name__)


def check_file_exists(path: str, workspace_root: str) -> dict[str, Any]:
    """
    Check if a file or directory exists within the workspace sandbox.

    Args:
        path: Relative or absolute path to check
        workspace_root: Root directory for workspace sandbox

    Returns:
        Dictionary with:
            - success: bool
            - exists: bool
            - is_file: bool
            - is_dir: bool
            - path: str (normalized path)
            - error: str (if sandbox violation)
    """
    try:
        workspace = Path(workspace_root).resolve()
        target_path = Path(path)

        # Handle both absolute and relative paths
        if target_path.is_absolute():
            resolved = target_path.resolve()
        else:
            resolved = (workspace / target_path).resolve()

        # Sandbox validation - ensure path is within workspace
        try:
            # This will raise ValueError if resolved is not relative to workspace
            relative = resolved.relative_to(workspace)
        except ValueError:
            return {
                "success": False,
                "error": f"Path '{path}' is outside workspace sandbox",
                "exists": False,
                "is_file": False,
                "is_dir": False,
            }

        # Check existence and type
        exists = resolved.exists()
        is_file = resolved.is_file() if exists else False
        is_dir = resolved.is_dir() if exists else False

        return {
            "success": True,
            "path": str(relative),  # Return normalized relative path
            "exists": exists,
            "is_file": is_file,
            "is_dir": is_dir,
        }

    except Exception:
        logger.exception("Error checking file existence")
        return {
            "success": False,
            "error": "Error checking path",
            "exists": False,
            "is_file": False,
            "is_dir": False,
        }


async def file_exists(
    path: str,
    tenant_key: str,
    workspace_root: Optional[str] = None,
) -> dict[str, Any]:
    """
    MCP tool: Check whether a file or directory exists within the allowed workspace.

    Args:
        path: Path to check (relative or absolute)
        tenant_key: Tenant isolation key
        workspace_root: Optional workspace root (defaults to product workspace)

    Returns:
        Dictionary with:
            - success: bool
            - path: str (normalized path)
            - exists: bool
            - is_file: bool
            - is_dir: bool
            - error: str (if failed)

    Example response:
        {
            "success": true,
            "path": "src/app.py",
            "exists": true,
            "is_file": true,
            "is_dir": false
        }
    """
    try:
        # If workspace_root not provided, get from product configuration
        if workspace_root is None:
            db_manager = DatabaseManager()
            async with db_manager.get_tenant_session_async(tenant_key) as session:
                # Get active product for tenant
                query = select(Product).where(
                    Product.tenant_key == tenant_key,
                    Product.is_active
                ).limit(1)

                result = await session.execute(query)
                product = result.scalar_one_or_none()

                if not product or not product.project_path:
                    return {
                        "success": False,
                        "error": "No active product workspace found for tenant",
                        "exists": False,
                        "is_file": False,
                        "is_dir": False,
                    }

                workspace_root = product.project_path

        # Use service helper to check existence with sandbox validation
        return check_file_exists(path, workspace_root)

    except Exception:
        logger.exception("file_exists tool failed")
        return {
            "success": False,
            "error": "Failed to check file existence",
            "exists": False,
            "is_file": False,
            "is_dir": False,
        }
