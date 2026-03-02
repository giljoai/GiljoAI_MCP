"""
MCP Tool: Export Agent Templates to Claude Code Format

Provides command-line interface for exporting agent templates directly
from user's terminal context, solving path resolution issues.

Handover 0084: Agent Export Copy-Command Interface
"""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from api.endpoints.claude_export import export_templates_to_claude_code
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import FileSystemError, GiljoFileNotFoundError, ResourceNotFoundError, ToolError
from src.giljo_mcp.models import Product, User


logger = logging.getLogger(__name__)


async def export_agents_command(
    db_manager: DatabaseManager,
    tenant_key: str,
    product_path: str | None = None,
    personal: bool = False,
) -> dict[str, Any]:
    """
    Export agent templates via MCP command.

    Args:
        db_manager: Database manager instance
        tenant_key: User's tenant for multi-tenant isolation
        product_path: Path to product's .claude/agents directory
        personal: Export to user's personal ~/.claude/agents

    Returns:
        Export result dictionary
    """

    try:
        if personal:
            # Export to user's personal directory
            export_path = str(Path.home() / ".claude" / "agents")
        elif product_path:
            # Export to specified product path
            export_path = str(Path(product_path))
        else:
            raise ValueError("Must specify either --product-path or --personal")

        # Ensure directory exists
        Path(export_path).mkdir(parents=True, exist_ok=True)

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            # Get user by tenant key
            user_query = select(User).where(User.tenant_key == tenant_key)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found for tenant: {tenant_key}")

            # Perform export using existing function
            result = await export_templates_to_claude_code(
                db=session,
                current_user=user,
                export_path=export_path,
            )

            return result

    except ValueError as e:
        logger.warning(f"Export validation failed: {e}")
        raise

    except Exception as e:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Export failed")
        raise ToolError(f"Export failed: {e!s}") from e


async def get_product_for_tenant(
    db_manager: DatabaseManager, tenant_key: str, product_id: str | None = None
) -> Product | None:
    """
    Get product for tenant, optionally by product ID.

    Args:
        db_manager: Database manager instance
        tenant_key: User's tenant key
        product_id: Optional specific product ID

    Returns:
        Product instance or None
    """
    try:
        async with db_manager.get_tenant_session_async(tenant_key) as session:
            if product_id:
                # Get specific product
                query = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            else:
                # Get active product for tenant
                query = select(Product).where(Product.tenant_key == tenant_key, Product.is_active).limit(1)

            result = await session.execute(query)
            return result.scalar_one_or_none()

    except SQLAlchemyError:
        logger.exception("Failed to get product")
        return None


async def validate_product_path(
    db_manager: DatabaseManager, tenant_key: str, product_id: str, project_path: str
) -> dict[str, Any]:
    """
    Validate and update product's project_path.

    Args:
        db_manager: Database manager instance
        tenant_key: User's tenant key
        product_id: Product ID to update
        project_path: File system path to validate and set

    Returns:
        Validation result dictionary
    """
    try:
        # Validate path exists and is directory
        path = Path(project_path).expanduser()
        if not path.exists():
            raise GiljoFileNotFoundError(f"Path does not exist: {path}")
        if not path.is_dir():
            raise FileSystemError(f"Path is not a directory: {path}")

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            # Get product
            query = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await session.execute(query)
            product = result.scalar_one_or_none()

            if not product:
                raise ResourceNotFoundError("Product not found")

            # Update project_path
            product.project_path = str(path)
            await session.commit()

            return {
                "product_id": product_id,
                "project_path": str(path),
                "message": "Product path updated successfully",
            }

    except Exception as e:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Failed to validate product path")
        raise FileSystemError(f"Path validation failed: {e!s}") from e
