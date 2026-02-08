"""
Product Lifecycle Endpoints - Handover 0127b

Handles product activation, deactivation, restore, and deletion operations
using ProductService.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import (
    ActiveProductRefreshResponse,
    CascadeImpact,
    ProductActivationResponse,
    ProductDeleteResponse,
    ProductResponse,
    VisionDocumentStatsResponse,
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
        if active_result.get("product"):
            previous_active_id = active_result["product"]["id"]

        # Activate new product
        result = await service.activate_product(product_id)

        # Get full product details with metrics
        product_result = await service.get_product(product_id, include_metrics=True)

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
            deactivated_projects=deactivated_projects,
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error activating product: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    finally:
        # Publish WS event via EventBus (tenant-scoped)
        try:
            from api.app import state

            if getattr(state, "event_bus", None):
                await state.event_bus.publish(
                    "product:status:changed",
                    {
                        "tenant_key": current_user.tenant_key,
                        "product_id": product_id,
                        "is_active": True,
                    },
                )
        except Exception as pub_err:
            logger.warning(f"Failed to publish product activation event: {pub_err}")


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

        # Get full product details
        product_result = await service.get_product(product_id, include_metrics=True)

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
            product_memory=product_data.get("product_memory"),  # Handover 0412: 360 Memory
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deactivating product: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    finally:
        # Publish WS event via EventBus (tenant-scoped)
        try:
            from api.app import state

            if getattr(state, "event_bus", None):
                await state.event_bus.publish(
                    "product:status:changed",
                    {
                        "tenant_key": current_user.tenant_key,
                        "product_id": product_id,
                        "is_active": False,
                    },
                )
        except Exception as pub_err:
            logger.warning(f"Failed to publish product deactivation event: {pub_err}")


@router.delete("/{product_id}", response_model=ProductDeleteResponse)
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductDeleteResponse:
    """
    Soft delete a product.

    Uses ProductService.delete_product() for database operations.
    Returns enhanced response with deletion context (was_active, remaining count).
    """
    logger.info(f"User {current_user.username} deleting product {product_id}")

    try:
        # Get product state before deletion for response
        product_result = await service.get_product(product_id)
        was_active = product_result.get("product", {}).get("is_active", False)

        result = await service.delete_product(product_id)

        # Get remaining products count
        products_result = await service.list_products()
        remaining_count = len(products_result.get("products", []))

        return ProductDeleteResponse(
            message=result["message"],
            deleted_product_id=product_id,
            was_active=was_active,
            remaining_products_count=remaining_count,
            new_active_product=None,  # Could auto-activate another product if needed
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting product: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


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

        # Get full product details
        product_result = await service.get_product(product_id, include_metrics=True)

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
            product_memory=product_data.get("product_memory"),  # Handover 0412: 360 Memory
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error restoring product: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


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

        impact_data = result["impact"]

        return CascadeImpact(
            product_id=impact_data["product_id"],
            product_name=impact_data["product_name"],
            total_projects=impact_data["total_projects"],
            total_tasks=impact_data["total_tasks"],
            total_vision_documents=impact_data["total_vision_documents"],
            warning=impact_data["warning"],
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting cascade impact: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


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

        product_data = result.get("product")

        if not product_data:
            return ActiveProductRefreshResponse(has_active_product=False, product=None)

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
            ),
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error refreshing active product: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/active/vision-stats", response_model=VisionDocumentStatsResponse)
async def get_vision_document_stats(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> VisionDocumentStatsResponse:
    """
    Get vision document statistics for active product.

    Returns token counts and metadata for the active product's vision document.
    Used by frontend to dynamically display context depth options with actual token counts.

    Handover 0345: Dynamic vision document token counts for context depth configuration.
    """
    logger.debug(f"User {current_user.username} requesting vision stats for active product")

    try:
        # Get active product
        result = await service.get_active_product()

        product_data = result.get("product")

        if not product_data:
            raise HTTPException(status_code=404, detail="No active product found")

        product_id = product_data["id"]
        product_name = product_data["name"]

        # Query for active vision documents
        from sqlalchemy import and_, select

        from src.giljo_mcp.models import VisionDocument

        stmt = (
            select(VisionDocument)
            .where(
                and_(
                    VisionDocument.tenant_key == tenant_key,
                    VisionDocument.product_id == product_id,
                    VisionDocument.is_active == True,  # noqa: E712
                )
            )
            .order_by(VisionDocument.created_at.desc())
        )

        result_db = await db.execute(stmt)
        vision_doc = result_db.scalar_one_or_none()

        if not vision_doc:
            # No vision document for this product
            return VisionDocumentStatsResponse(
                product_id=product_id,
                product_name=product_name,
                has_vision_document=False,
                total_tokens=0,
                chunk_count=0,
                is_summarized=False,
                summary_tokens=0,
            )

        # Vision document exists, return its stats
        meta_data = vision_doc.meta_data or {}
        return VisionDocumentStatsResponse(
            product_id=product_id,
            product_name=product_name,
            has_vision_document=True,
            total_tokens=vision_doc.total_tokens or 0,
            chunk_count=vision_doc.chunk_count or 0,
            is_summarized=meta_data.get("is_summarized", False),
            summary_tokens=meta_data.get("summary_tokens", 0),
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting vision document stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
