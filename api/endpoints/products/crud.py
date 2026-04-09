# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Product CRUD Endpoints - Handover 0127b

Handles product CRUD operations using ProductService.

All database access now goes through ProductService following the
established service layer pattern (similar to ProjectService, TemplateService).

Exception handling: Domain exceptions (ResourceNotFoundError, ValidationError,
AuthorizationError) propagate to the global exception handler in
api/exception_handlers.py which maps them to appropriate HTTP status codes.

Handover 0731d: Updated for typed ProductService returns (Product ORM models,
DeleteResult, ProductStatistics instead of dicts).
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.exceptions import ResourceNotFoundError

# Model imports: Use modular pattern (Post-0128a refactoring)
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services import ProductService

from .dependencies import get_product_service
from .models import DeletedProductResponse, ProductCreate, ProductResponse, ProductUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# Purge retention period for deleted products (days)
_PURGE_RETENTION_DAYS = 10


def _build_product_response(product, stats=None, override_active=None) -> ProductResponse:
    """
    Build a ProductResponse from a Product ORM model and optional ProductStatistics.

    Centralizes the ORM-to-response mapping so every endpoint uses the same logic.
    Handover 0840i: Exposes normalized fields directly (no config_data reconstruction).

    Args:
        product: Product ORM model
        stats: Optional ProductStatistics for metrics fields
        override_active: Optional bool to override product.is_active in response

    Returns:
        ProductResponse Pydantic model
    """
    from .models import ArchitectureSchema, TechStackSchema, TestConfigSchema

    ts = product.tech_stack
    tech_stack = (
        TechStackSchema(
            programming_languages=ts.programming_languages,
            frontend_frameworks=ts.frontend_frameworks,
            backend_frameworks=ts.backend_frameworks,
            databases_storage=ts.databases_storage,
            infrastructure=ts.infrastructure,
            dev_tools=ts.dev_tools,
        )
        if ts
        else None
    )

    arch = product.architecture
    architecture = (
        ArchitectureSchema(
            primary_pattern=arch.primary_pattern,
            design_patterns=arch.design_patterns,
            api_style=arch.api_style,
            architecture_notes=arch.architecture_notes,
            coding_conventions=arch.coding_conventions,
        )
        if arch
        else None
    )

    tc = product.test_config
    test_config = (
        TestConfigSchema(
            quality_standards=tc.quality_standards,
            test_strategy=tc.test_strategy,
            coverage_target=tc.coverage_target or 80,
            testing_frameworks=tc.testing_frameworks,
        )
        if tc
        else None
    )

    # Handover 0412: Ensure product_memory is never None
    pm = product.product_memory
    if pm is None:
        pm = {"github": {}, "sequential_history": [], "context": {}}

    is_active = override_active if override_active is not None else product.is_active

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        description=product.description,
        vision_path=None,
        project_path=product.project_path,
        created_at=product.created_at,
        updated_at=product.updated_at,
        project_count=stats.project_count if stats else 0,
        task_count=stats.task_count if stats else 0,
        has_vision=stats.has_vision if stats else False,
        unresolved_tasks=stats.unresolved_tasks if stats else 0,
        unfinished_projects=stats.unfinished_projects if stats else 0,
        vision_documents_count=stats.vision_documents_count if stats else 0,
        tech_stack=tech_stack,
        architecture=architecture,
        test_config=test_config,
        core_features=product.core_features,
        brand_guidelines=product.brand_guidelines,
        is_active=is_active,
        product_memory=pm,
        target_platforms=product.target_platforms or ["all"],
    )


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
    product = await service.create_product(
        name=request.name,
        description=request.description,
        project_path=request.project_path,
        tech_stack=request.tech_stack.model_dump() if request.tech_stack else None,
        architecture=request.architecture.model_dump() if request.architecture else None,
        test_config=request.test_config.model_dump() if request.test_config else None,
        core_features=request.core_features,
        brand_guidelines=request.brand_guidelines,
        target_platforms=request.target_platforms,  # Handover 0425 Phase 2
    )

    # Get statistics for the newly created product
    stats = await service.get_product_statistics(str(product.id))

    return _build_product_response(product, stats)


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
    include_inactive: bool = Query(
        default=True, description="Include inactive products (default: True, always show all)"
    ),
) -> list[ProductResponse]:
    """
    List all products for the current tenant.

    Uses ProductService.list_products() for database operations.
    """
    products = await service.list_products(include_inactive=include_inactive)

    logger.debug(f"Found {len(products)} products")

    responses = []
    for product in products:
        stats = await service.get_product_statistics(str(product.id))
        responses.append(_build_product_response(product, stats))

    return responses


@router.get("/deleted", response_model=list[DeletedProductResponse])
async def list_deleted_products(
    current_user: User = Depends(get_current_active_user),
    service: ProductService = Depends(get_product_service),
) -> list[DeletedProductResponse]:
    """
    List soft-deleted products (Handover 0070).

    Uses ProductService.list_deleted_products() for database operations.
    Handover 0731d: Purge date computation moved from service to endpoint layer.
    """
    products = await service.list_deleted_products()

    result = []
    for p in products:
        # Compute purge date: deleted_at + retention period
        purge_date = p.deleted_at + timedelta(days=_PURGE_RETENTION_DAYS)
        days_until_purge = max(0, (purge_date - datetime.now(timezone.utc)).days)

        # Get statistics for project_count and vision_documents_count
        # Note: get_product_statistics filters on deleted_at IS NULL, so
        # for deleted products we need to compute counts differently.
        # Use sensible defaults since deleted products have limited metrics.
        stats = None
        try:
            stats = await service.get_product_statistics(str(p.id))
        except (ResourceNotFoundError, ValueError, KeyError):
            # Product is deleted so get_product_statistics may raise ResourceNotFoundError
            logger.debug(f"Could not get statistics for deleted product {p.id}")

        result.append(
            DeletedProductResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                deleted_at=p.deleted_at,
                days_until_purge=days_until_purge,
                purge_date=purge_date,
                project_count=stats.project_count if stats else 0,
                vision_documents_count=stats.vision_documents_count if stats else 0,
            )
        )

    return result


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
    product = await service.get_product(product_id=product_id)
    stats = await service.get_product_statistics(str(product.id))

    # Handover 0412: Ensure product_memory is passed through correctly
    pm = product.product_memory
    if pm is None:
        logger.warning(f"Product {product_id}: product_memory is None, using default")
    logger.info(f"Product {product_id}: product_memory keys={list((pm or {}).keys())}")

    return _build_product_response(product, stats)


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
    # Convert Pydantic model to dict, excluding unset fields
    # model_dump already converts nested Pydantic models to dicts
    update_data = updates.model_dump(exclude_unset=True)

    product = await service.update_product(product_id, **update_data)

    # Get statistics for the updated product
    stats = await service.get_product_statistics(str(product.id))

    logger.info(f"Updated product {product_id}")

    return _build_product_response(product, stats)
