"""
Product CRUD Endpoints - Handover 0127b

Handles product CRUD operations using ProductService.

All database access now goes through ProductService following the
established service layer pattern (similar to ProjectService, TemplateService).
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from src.giljo_mcp.auth.dependencies import get_current_active_user
# Model imports: Use modular pattern (Post-0128a refactoring)
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import ProductCreate, ProductResponse, ProductUpdate, DeletedProductResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ProductResponse)
async def create_product(
    request: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Create a new product.

    Uses ProductService.create_product() for database operations.
    """
    try:
        result = await service.create_product(
            name=request.name,
            description=request.description,
            project_path=request.project_path,
            config_data=request.config_data,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        # Get full product details with metrics
        product_result = await service.get_product(
            product_id=result["product_id"],
            include_metrics=True
        )

        if not product_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve created product")

        product_data = product_result["product"]

        # Normalize empty config_data to None for API contract consistency
        config_data = product_data.get("config_data") or None
        has_config_data = bool(config_data)

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
            config_data=config_data,
            has_config_data=has_config_data,
            is_active=product_data.get("is_active", False),
            product_memory=product_data.get("product_memory"),  # Handover 0412: 360 Memory
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
    include_inactive: bool = Query(True, description="Include inactive products (default: True, always show all)"),
) -> List[ProductResponse]:
    """
    List all products for the current tenant.

    Uses ProductService.list_products() for database operations.
    """
    try:
        result = await service.list_products(
            include_inactive=include_inactive,
            include_metrics=True
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        logger.debug(f"Found {len(result['products'])} products")

        return [
            ProductResponse(
                id=p["id"],
                name=p["name"],
                description=p["description"],
                vision_path=p.get("vision_path"),
                project_path=p.get("project_path"),
                created_at=p.get("created_at"),
                updated_at=p.get("updated_at"),
                project_count=p.get("project_count", 0),
                task_count=p.get("task_count", 0),
                has_vision=p.get("has_vision", False),
                unresolved_tasks=p.get("unresolved_tasks", 0),
                unfinished_projects=p.get("unfinished_projects", 0),
                vision_documents_count=p.get("vision_documents_count", 0),
                config_data=p.get("config_data"),
                has_config_data=p.get("has_config_data", False),
                is_active=p.get("is_active", False),
                product_memory=p.get("product_memory"),  # Handover 0412: 360 Memory
            )
            for p in result["products"]
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/deleted", response_model=list[DeletedProductResponse])
async def list_deleted_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> list[DeletedProductResponse]:
    """
    List soft-deleted products (Handover 0070).

    Uses ProductService.list_deleted_products() for database operations.
    """
    try:
        result = await service.list_deleted_products()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return [
            DeletedProductResponse(
                id=p["id"],
                name=p["name"],
                description=p["description"],
                deleted_at=p["deleted_at"],
                days_until_purge=p["days_until_purge"],
                purge_date=p["purge_date"],
                project_count=p["project_count"],
                vision_documents_count=p["vision_documents_count"],
            )
            for p in result["products"]
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list deleted products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Get product by ID.

    Uses ProductService.get_product() for database operations.
    """
    try:
        result = await service.get_product(
            product_id=product_id,
            include_metrics=True
        )

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])

        product_data = result["product"]

        logger.debug(f"Retrieved product {product_id}")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Update an existing product.

    Uses ProductService.update_product() for database operations.
    """
    try:
        # Convert Pydantic model to dict, excluding unset fields
        update_data = updates.model_dump(exclude_unset=True)

        result = await service.update_product(product_id, **update_data)

        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])

        # Get full updated product with metrics
        product_result = await service.get_product(
            product_id=product_id,
            include_metrics=True
        )

        if not product_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated product")

        product_data = product_result["product"]

        logger.info(f"Updated product {product_id}")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")
