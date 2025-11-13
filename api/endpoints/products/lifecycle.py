"""
Product Lifecycle Endpoints - Handover 0127b

Handles product activation, deactivation, restore, and deletion operations
using ProductService.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import (
    ProductActivationResponse,
    ProductDeleteResponse,
    ProductResponse,
    CascadeImpact,
    ActiveProductRefreshResponse,
    TokenEstimateResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{product_id}/activate", response_model=ProductActivationResponse)
async def activate_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductActivationResponse:
    """
    Activate a product (deactivates other products, auto-pauses their projects).

    Uses ProductService.activate_product() for database operations.
    Handover 0503: Updated response to match frontend expectations.
    """
    logger.info(f"User {current_user.username} activating product {product_id}")

    try:
        # Get currently active product (if any) before activation
        active_result = await service.get_active_product()
        previous_active_id = None
        if active_result["success"] and active_result.get("product"):
            previous_active_id = active_result["product"]["id"]

        # Activate new product
        result = await service.activate_product(product_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Get full product details with metrics
        product_result = await service.get_product(product_id, include_metrics=True)

        if not product_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve activated product")

        product_data = product_result["product"]

        # Build ProductResponse
        product_response = ProductResponse(
            id=product_data["id"],
            name=product_data["name"],
            description=product_data["description"],
            vision_path=product_data.get("vision_path"),
            project_path=product_data.get("project_path"),
            created_at=product_data.get("created_at"),
            updated_at=product_data.get("updated_at"),
            project_count=product_data.get("project_count", 0),
            task_count=product_data.get("task_count", 0),
            has_vision=product_data.get("has_vision", False),
            unresolved_tasks=product_data.get("unresolved_tasks", 0),
            unfinished_projects=product_data.get("unfinished_projects", 0),
            vision_documents_count=product_data.get("vision_documents_count", 0),
            config_data=product_data.get("config_data"),
            has_config_data=product_data.get("has_config_data", False),
            is_active=True,
        )

        # TODO: Query for deactivated projects when ProjectService integration is complete
        # For now, return empty list as projects will be handled in future handover
        deactivated_projects = []

        return ProductActivationResponse(
            product_id=product_data["id"],
            previous_active_product_id=previous_active_id,
            product=product_response,
            message=f"Product '{product_data['name']}' activated successfully",
            deactivated_projects=deactivated_projects
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate product: {str(e)}"
        )


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Deactivate a product.

    Uses ProductService.deactivate_product() for database operations.
    """
    logger.info(f"User {current_user.username} deactivating product {product_id}")

    try:
        result = await service.deactivate_product(product_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Get full product details
        product_result = await service.get_product(product_id, include_metrics=True)

        if not product_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve product")

        product_data = product_result["product"]

        return ProductResponse(
            id=product_data["id"],
            name=product_data["name"],
            description=product_data["description"],
            vision_path=product_data.get("vision_path"),
            project_path=product_data.get("project_path"),
            created_at=product_data.get("created_at"),
            updated_at=product_data.get("updated_at"),
            project_count=product_data.get("project_count", 0),
            task_count=product_data.get("task_count", 0),
            has_vision=product_data.get("has_vision", False),
            unresolved_tasks=product_data.get("unresolved_tasks", 0),
            unfinished_projects=product_data.get("unfinished_projects", 0),
            vision_documents_count=product_data.get("vision_documents_count", 0),
            config_data=product_data.get("config_data"),
            has_config_data=product_data.get("has_config_data", False),
            is_active=product_data.get("is_active", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate product: {str(e)}"
        )


@router.delete("/{product_id}", response_model=ProductDeleteResponse)
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductDeleteResponse:
    """
    Soft delete a product.

    Uses ProductService.delete_product() for database operations.
    """
    logger.info(f"User {current_user.username} deleting product {product_id}")

    try:
        result = await service.delete_product(product_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        return ProductDeleteResponse(
            success=True,
            message=result["message"],
            deleted_at=result["deleted_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}"
        )


@router.post("/{product_id}/restore", response_model=ProductResponse)
async def restore_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Restore a soft-deleted product.

    Uses ProductService.restore_product() for database operations.
    """
    logger.info(f"User {current_user.username} restoring product {product_id}")

    try:
        result = await service.restore_product(product_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Get full product details
        product_result = await service.get_product(product_id, include_metrics=True)

        if not product_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve restored product")

        product_data = product_result["product"]

        return ProductResponse(
            id=product_data["id"],
            name=product_data["name"],
            description=product_data["description"],
            vision_path=product_data.get("vision_path"),
            project_path=product_data.get("project_path"),
            created_at=product_data.get("created_at"),
            updated_at=product_data.get("updated_at"),
            project_count=product_data.get("project_count", 0),
            task_count=product_data.get("task_count", 0),
            has_vision=product_data.get("has_vision", False),
            unresolved_tasks=product_data.get("unresolved_tasks", 0),
            unfinished_projects=product_data.get("unfinished_projects", 0),
            vision_documents_count=product_data.get("vision_documents_count", 0),
            config_data=product_data.get("config_data"),
            has_config_data=product_data.get("has_config_data", False),
            is_active=product_data.get("is_active", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore product: {str(e)}"
        )


@router.get("/{product_id}/cascade-impact", response_model=CascadeImpact)
async def get_cascade_impact(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> CascadeImpact:
    """
    Get cascade impact analysis for product deletion.

    Uses ProductService.get_cascade_impact() for database operations.
    """
    logger.debug(f"User {current_user.username} checking cascade impact for product {product_id}")

    try:
        result = await service.get_cascade_impact(product_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        impact_data = result["impact"]

        return CascadeImpact(
            product_id=impact_data["product_id"],
            product_name=impact_data["product_name"],
            total_projects=impact_data["total_projects"],
            total_tasks=impact_data["total_tasks"],
            total_vision_documents=impact_data["total_vision_documents"],
            warning=impact_data["warning"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cascade impact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cascade impact: {str(e)}"
        )


@router.get("/refresh-active", response_model=ActiveProductRefreshResponse)
async def refresh_active_product(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ActiveProductRefreshResponse:
    """
    Refresh active product information.

    Uses ProductService.get_active_product() for database operations.
    """
    logger.debug(f"User {current_user.username} refreshing active product")

    try:
        result = await service.get_active_product()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        product_data = result.get("product")

        if not product_data:
            return ActiveProductRefreshResponse(
                has_active_product=False,
                product=None
            )

        return ActiveProductRefreshResponse(
            has_active_product=True,
            product=ProductResponse(
                id=product_data["id"],
                name=product_data["name"],
                description=product_data["description"],
                vision_path=product_data.get("vision_path"),
                project_path=product_data.get("project_path"),
                created_at=product_data.get("created_at"),
                updated_at=product_data.get("updated_at"),
                project_count=product_data.get("project_count", 0),
                task_count=product_data.get("task_count", 0),
                has_vision=product_data.get("has_vision", False),
                unresolved_tasks=product_data.get("unresolved_tasks", 0),
                unfinished_projects=product_data.get("unfinished_projects", 0),
                vision_documents_count=product_data.get("vision_documents_count", 0),
                config_data=product_data.get("config_data"),
                has_config_data=product_data.get("has_config_data", False),
                is_active=True,
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh active product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh active product: {str(e)}"
        )


@router.get("/active/token-estimate", response_model=TokenEstimateResponse)
async def get_token_estimate(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> TokenEstimateResponse:
    """
    Get token estimate for active product.

    Uses ProductService.get_active_product() and calculates token estimate
    based on project statistics.
    """
    logger.debug(f"User {current_user.username} requesting token estimate for active product")

    try:
        result = await service.get_active_product()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        product_data = result.get("product")

        if not product_data:
            raise HTTPException(
                status_code=404,
                detail="No active product found"
            )

        # Calculate token estimate (simplified - can be enhanced)
        # Base tokens for product metadata
        token_estimate = 500

        # Add tokens for projects (estimate ~1000 tokens per project)
        project_count = product_data.get("project_count", 0)
        token_estimate += project_count * 1000

        # Add tokens for vision documents (estimate ~2000 tokens per doc)
        vision_count = product_data.get("vision_documents_count", 0)
        token_estimate += vision_count * 2000

        # Add tokens for config data
        if product_data.get("has_config_data"):
            token_estimate += 500

        return TokenEstimateResponse(
            product_id=product_data["id"],
            product_name=product_data["name"],
            estimated_tokens=token_estimate,
            breakdown={
                "base": 500,
                "projects": project_count * 1000,
                "vision_documents": vision_count * 2000,
                "config_data": 500 if product_data.get("has_config_data") else 0
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token estimate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token estimate: {str(e)}"
        )
