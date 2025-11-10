"""
Product CRUD Endpoints - Handover 0126

Handles product CRUD operations.

NOTE: ProductService does not exist yet. This implementation uses direct
database access temporarily. Future work: Create ProductService and refactor
all endpoints to use it (similar to TemplateService pattern).
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Product, Project, Task, User, VisionDocument
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ProductCreate, ProductResponse, ProductUpdate, DeletedProductResponse


logger = logging.getLogger(__name__)
router = APIRouter()


async def _build_product_response(product: Product, db: AsyncSession) -> ProductResponse:
    """
    Build ProductResponse from Product ORM model with metrics.

    TODO: Move to ProductService as part of service layer extraction.
    """
    # Count projects
    projects_result = await db.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.product_id == product.id,
                or_(Project.status != "deleted", Project.status.is_(None))
            )
        )
    )
    project_count = projects_result.scalar() or 0

    # Count unfinished projects
    unfinished_result = await db.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.product_id == product.id,
                Project.status.in_(["active", "inactive"])
            )
        )
    )
    unfinished_projects = unfinished_result.scalar() or 0

    # Count tasks
    tasks_result = await db.execute(
        select(func.count(Task.id)).where(Task.product_id == product.id)
    )
    task_count = tasks_result.scalar() or 0

    # Count unresolved tasks
    unresolved_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(
                Task.product_id == product.id,
                Task.status.in_(["pending", "in_progress"])
            )
        )
    )
    unresolved_tasks = unresolved_result.scalar() or 0

    # Count vision documents
    vision_result = await db.execute(
        select(func.count(VisionDocument.id)).where(
            and_(
                VisionDocument.product_id == product.id,
                VisionDocument.deleted_at.is_(None)
            )
        )
    )
    vision_documents_count = vision_result.scalar() or 0

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        description=product.description,
        vision_path=product.vision_path,
        created_at=product.created_at,
        updated_at=product.updated_at,
        project_count=project_count,
        task_count=task_count,
        has_vision=vision_documents_count > 0,
        unresolved_tasks=unresolved_tasks,
        unfinished_projects=unfinished_projects,
        vision_documents_count=vision_documents_count,
        config_data=product.config_data,
        has_config_data=bool(product.config_data),
        is_active=product.is_active,
        project_path=product.project_path,
    )


@router.post("/", response_model=ProductResponse)
async def create_product(
    request: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> ProductResponse:
    """
    Create a new product.

    TODO: Refactor to use ProductService.create_product() once service exists.
    """
    try:
        # Check for duplicate name
        stmt = select(Product).where(
            and_(
                Product.tenant_key == tenant_key,
                Product.name == request.name,
                Product.deleted_at.is_(None)
            )
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Product '{request.name}' already exists")

        # Create product
        new_product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name=request.name,
            description=request.description,
            project_path=request.project_path,
            is_active=False,  # Products start inactive
            created_at=datetime.now(timezone.utc),
        )

        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)

        logger.info(f"Created product {new_product.id} for tenant {tenant_key}")

        return await _build_product_response(new_product, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
    include_inactive: bool = Query(False, description="Include inactive products"),
) -> List[ProductResponse]:
    """
    List all products for the current tenant.

    TODO: Refactor to use ProductService.list_products() once service exists.
    """
    try:
        # Build query
        conditions = [
            Product.tenant_key == tenant_key,
            Product.deleted_at.is_(None)
        ]

        if not include_inactive:
            conditions.append(Product.is_active == True)

        stmt = select(Product).where(and_(*conditions)).order_by(Product.created_at.desc())
        result = await db.execute(stmt)
        products = result.scalars().all()

        logger.debug(f"Found {len(products)} products for tenant {tenant_key}")

        return [await _build_product_response(p, db) for p in products]

    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> ProductResponse:
    """
    Get product by ID.

    TODO: Refactor to use ProductService.get_product() once service exists.
    """
    try:
        stmt = select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_key == tenant_key,
                Product.deleted_at.is_(None)
            )
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.debug(f"Retrieved product {product_id}")

        return await _build_product_response(product, db)

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
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> ProductResponse:
    """
    Update an existing product.

    TODO: Refactor to use ProductService.update_product() once service exists.
    """
    try:
        # Get existing product
        stmt = select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_key == tenant_key,
                Product.deleted_at.is_(None)
            )
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(product, field):
                setattr(product, field, value)

        product.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(product)

        logger.info(f"Updated product {product_id}")

        return await _build_product_response(product, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.get("/deleted", response_model=list[DeletedProductResponse])
async def list_deleted_products(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> list[DeletedProductResponse]:
    """
    List soft-deleted products (Handover 0070).

    TODO: Move to ProductService once created.
    """
    try:
        from datetime import timedelta

        # 30-day purge policy
        PURGE_DAYS = 30

        stmt = select(Product).where(
            and_(
                Product.tenant_key == tenant_key,
                Product.deleted_at.isnot(None)
            )
        ).order_by(Product.deleted_at.desc())

        result = await db.execute(stmt)
        deleted_products = result.scalars().all()

        responses = []
        for product in deleted_products:
            # Calculate purge date
            purge_date = product.deleted_at + timedelta(days=PURGE_DAYS)
            days_until_purge = max(0, (purge_date - datetime.now(timezone.utc)).days)

            # Count related entities
            project_count_result = await db.execute(
                select(func.count(Project.id)).where(Project.product_id == product.id)
            )
            project_count = project_count_result.scalar() or 0

            vision_count_result = await db.execute(
                select(func.count(VisionDocument.id)).where(
                    and_(
                        VisionDocument.product_id == product.id,
                        VisionDocument.deleted_at.is_(None)
                    )
                )
            )
            vision_documents_count = vision_count_result.scalar() or 0

            responses.append(DeletedProductResponse(
                id=str(product.id),
                name=product.name,
                description=product.description,
                deleted_at=product.deleted_at,
                days_until_purge=days_until_purge,
                purge_date=purge_date,
                project_count=project_count,
                vision_documents_count=vision_documents_count,
            ))

        return responses

    except Exception as e:
        logger.error(f"Failed to list deleted products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
