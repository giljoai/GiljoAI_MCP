"""
Git Integration Settings Endpoints - Handover 013B

Simplified git integration without GitHub API dependency.
Settings stored in product_memory.git_integration field.

This is the NEW simplified implementation (Handover 013B).
For legacy GitHub integration, see github.py.
"""

import logging

from fastapi import APIRouter, Depends

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import GitIntegrationRequest, GitIntegrationResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{product_id}/git-integration", response_model=GitIntegrationResponse)
async def update_git_integration(
    product_id: str,
    settings: GitIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> GitIntegrationResponse:
    """
    Update Git integration settings for a product.

    Settings are stored in product_memory.git_integration field:
    {
        "enabled": bool,
        "commit_limit": int,     # Max commits to show in prompts (1-100)
        "default_branch": str    # Default branch name
    }

    **No GitHub API Integration:**
    Git operations are handled by CLI agents (Claude Code, Codex, Gemini).
    No URL validation or GitHub API calls.

    **Args:**
    - `product_id`: Product UUID
    - `settings`: Git integration settings

    **Returns:**
    - Updated git integration settings

    **Raises:**
    - 404: Product not found
    - 400: Invalid settings
    - 403: User lacks permission
    """
    logger.info(
        f"User {current_user.username} updating git integration for product {product_id}: "
        f"enabled={settings.enabled}, commit_limit={settings.commit_limit}"
    )

    result = await service.update_git_integration(
        product_id=product_id,
        enabled=settings.enabled,
        commit_limit=settings.commit_limit,
        default_branch=settings.default_branch,
    )

    # Build response from returned settings
    git_settings = result["settings"]
    return GitIntegrationResponse(
        enabled=git_settings["enabled"],
        commit_limit=git_settings.get("commit_limit", 20),
        default_branch=git_settings.get("default_branch", "main"),
    )


@router.get("/{product_id}/git-integration", response_model=GitIntegrationResponse)
async def get_git_integration(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> GitIntegrationResponse:
    """
    Get current Git integration settings for a product.

    **Args:**
    - `product_id`: Product UUID

    **Returns:**
    - Current git integration settings (with defaults if not configured)

    **Raises:**
    - 404: Product not found
    - 403: User lacks permission
    """
    logger.info(f"User {current_user.username} retrieving git integration for product {product_id}")

    result = await service.get_product(product_id, include_metrics=False)

    # Extract git integration settings from product_memory
    product_data = result["product"]
    product_memory = product_data.get("product_memory", {})
    git_integration = product_memory.get("git_integration", {})

    # Return settings with defaults if not configured
    return GitIntegrationResponse(
        enabled=git_integration.get("enabled", False),
        commit_limit=git_integration.get("commit_limit", 20),
        default_branch=git_integration.get("default_branch", "main"),
    )
