"""
GitHub Integration Settings Endpoints - Handover 0137

Handles GitHub integration settings for products.
Settings are stored in product_memory.github field.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import GitHubSettingsRequest, GitHubSettingsResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{product_id}/github/settings", response_model=GitHubSettingsResponse)
async def update_github_settings(
    product_id: str,
    settings: GitHubSettingsRequest,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> GitHubSettingsResponse:
    """
    Update GitHub integration settings for a product.

    Settings are stored in product_memory.github field with structure:
    {
        "enabled": bool,
        "repo_url": str | None,
        "auto_commit": bool,
        "last_sync": ISO timestamp (optional)
    }

    **Validation:**
    - `repo_url` is required when `enabled=True`
    - `repo_url` must be valid GitHub URL (HTTPS or SSH format)
    - When disabled, `repo_url` is set to None

    **Args:**
    - `product_id`: Product UUID
    - `settings`: GitHub settings to update

    **Returns:**
    - Updated GitHub settings

    **Raises:**
    - 404: Product not found
    - 400: Invalid settings (e.g., missing repo_url when enabling)
    - 403: User lacks permission
    """
    logger.info(
        f"User {current_user.username} updating GitHub settings for product {product_id}: "
        f"enabled={settings.enabled}, auto_commit={settings.auto_commit}"
    )

    try:
        result = await service.update_github_settings(
            product_id=product_id,
            enabled=settings.enabled,
            repo_url=settings.repo_url,
            auto_commit=settings.auto_commit,
        )

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Build response from returned settings
        github_settings = result["settings"]
        return GitHubSettingsResponse(
            enabled=github_settings["enabled"],
            repo_url=github_settings.get("repo_url"),
            auto_commit=github_settings.get("auto_commit", False),
            last_sync=github_settings.get("last_sync"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update GitHub settings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/{product_id}/github/settings", response_model=GitHubSettingsResponse)
async def get_github_settings(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> GitHubSettingsResponse:
    """
    Get current GitHub integration settings for a product.

    **Args:**
    - `product_id`: Product UUID

    **Returns:**
    - Current GitHub settings

    **Raises:**
    - 404: Product not found
    - 403: User lacks permission
    """
    logger.info(
        f"User {current_user.username} retrieving GitHub settings for product {product_id}"
    )

    try:
        result = await service.get_product(product_id, include_metrics=False)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Extract GitHub settings from product_memory
        product_data = result["product"]
        product_memory = product_data.get("product_memory", {})
        github_settings = product_memory.get("github", {})

        # Return settings with defaults if not configured
        return GitHubSettingsResponse(
            enabled=github_settings.get("enabled", False),
            repo_url=github_settings.get("repo_url"),
            auto_commit=github_settings.get("auto_commit", False),
            last_sync=github_settings.get("last_sync"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get GitHub settings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
