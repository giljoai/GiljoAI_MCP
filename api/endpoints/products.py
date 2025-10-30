"""
Product management API endpoints with vision document upload support
"""

import os
import uuid
import aiofiles
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
from src.giljo_mcp.models import Product, Project, Task, VisionDocument, MCPContextIndex, User
from src.giljo_mcp.tools.chunking import EnhancedChunker

# Handover 0046 Issue #4: Update router prefix to /v1/products for consistency
router = APIRouter(prefix="/v1/products", tags=["Products"])


# Pydantic models for request/response
class ProductCreate(BaseModel):
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
    # Handover 0046 Issue #1: Add missing product metrics
    unresolved_tasks: int = 0
    unfinished_projects: int = 0
    vision_documents_count: int = 0

    # Handover 0042: Rich context fields
    config_data: Optional[dict] = Field(None, description="Rich configuration: tech_stack, architecture, features")
    has_config_data: bool = Field(False, description="Whether product has config_data populated")

    # Handover 0049: Active product indicator
    is_active: bool = Field(False, description="Whether this product is currently active")


# Handover 0050: Enhanced response models for single active product architecture
class ActiveProductInfo(BaseModel):
    """Minimal active product info for efficient responses"""

    id: str
    name: str
    description: Optional[str]
    activated_at: datetime = Field(description="When this product was activated")
    active_projects_count: int = Field(default=0, description="Handover 0050b: Number of active projects")


class ProductActivationResponse(ProductResponse):
    """Enhanced response for product activation with context"""

    previous_active_product: Optional[ActiveProductInfo] = Field(
        None, description="Previously active product (if any) that was deactivated"
    )
    activation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="When this activation occurred"
    )


class ProductDeleteResponse(BaseModel):
    """Enhanced response for product deletion"""

    message: str
    deleted_product_id: str
    was_active: bool = Field(description="Whether the deleted product was active")
    remaining_products_count: int
    new_active_product: Optional[ActiveProductInfo] = Field(
        None, description="Auto-activated product (if deleted product was active)"
    )


class ActiveProductRefreshResponse(BaseModel):
    """Response for /refresh-active endpoint"""

    active_product: Optional[ActiveProductInfo]
    total_products_count: int
    last_refreshed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VisionChunk(BaseModel):
    chunk_number: int
    total_chunks: int
    content: str
    char_start: int
    char_end: int
    boundary_type: str
    keywords: List[str]
    headers: List[str]


class TokenEstimateResponse(BaseModel):
    """Token estimation response for active product (Handover 0049)"""

    product_id: str = Field(..., description="Active product ID")
    product_name: str = Field(..., description="Active product name")
    field_tokens: Dict[str, int] = Field(..., description="Token count per prioritized field")
    total_field_tokens: int = Field(..., description="Sum of all field tokens")
    overhead_tokens: int = Field(..., description="Fixed overhead for mission structure (500 tokens)")
    total_tokens: int = Field(..., description="Total tokens (field_tokens + overhead)")
    token_budget: int = Field(..., description="User's configured token budget")
    percentage_used: float = Field(..., description="Percentage of budget used (total/budget * 100)")


class CascadeImpact(BaseModel):
    """Cascade impact response for product deletion"""

    product_id: str
    projects_count: int = Field(..., description="Total number of projects")
    unfinished_projects: int = Field(..., description="Number of unfinished projects")
    tasks_count: int = Field(..., description="Total number of tasks")
    unresolved_tasks: int = Field(..., description="Number of unresolved tasks")
    vision_documents_count: int = Field(..., description="Number of vision documents")
    total_chunks: int = Field(..., description="Total number of context chunks")


def get_vision_storage_path(tenant_key: str, product_id: str) -> Path:
    """Get the vision document storage path based on deployment mode"""
    from api.app import state

    # Check deployment mode from config
    config = state.config if hasattr(state, "config") else {}
    mode = config.get("installation", {}).get("mode", "localhost")

    if mode == "localhost":
        # Local storage in products folder
        base_path = Path("./products") / product_id / "vision"
    else:
        # Server mode: uploaded files storage
        base_path = Path("./uploads/vision_documents") / tenant_key / product_id

    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    config_data: Optional[str] = Form(None),  # Handover 0042: Rich configuration as JSON string
    tenant_key: str = Depends(get_tenant_key),
):
    """Create a new product with optional vision document upload"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Handover 0042: Parse and validate config_data JSON
        config_dict: Dict[str, Any] = {}
        if config_data:
            try:
                config_dict = json.loads(config_data)
                if not isinstance(config_dict, dict):
                    raise HTTPException(status_code=400, detail="config_data must be a JSON object")
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

        # Create product in database
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name=name,
            description=description,
            config_data=config_dict if config_dict else None,
        )

        # Handle vision document upload if provided
        if vision_file:
            # Validate file type
            allowed_extensions = {".txt", ".md", ".markdown"}
            file_extension = Path(vision_file.filename).suffix.lower()
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
                )

            # Save vision document
            storage_path = get_vision_storage_path(tenant_key, product.id)
            file_path = storage_path / vision_file.filename

            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                content = await vision_file.read()
                await f.write(content)

            product.vision_path = str(file_path)

            # Process with EnhancedChunker
            try:
                chunker = EnhancedChunker()
                chunks = chunker.chunk_content(content.decode("utf-8"), document_name=vision_file.filename)

                # Store chunk metadata in product meta_data
                product.meta_data = {
                    "vision_chunks": len(chunks),
                    "vision_filename": vision_file.filename,
                    "vision_size": len(content),
                    "chunks_metadata": [
                        {
                            "chunk_number": chunk["chunk_number"],
                            "char_start": chunk["char_start"],
                            "char_end": chunk["char_end"],
                            "boundary_type": chunk["boundary_type"],
                            "keywords": chunk["keywords"][:5],  # Store top 5 keywords
                            "headers": chunk["headers"],
                        }
                        for chunk in chunks
                    ],
                }
            except Exception as e:
                # Log chunking error but don't fail product creation
                product.meta_data = {
                    "vision_error": f"Failed to chunk document: {str(e)}",
                    "vision_filename": vision_file.filename,
                }

        # Save to database using async session
        async with state.db_manager.get_session_async() as db:
            db.add(product)
            await db.commit()
            await db.refresh(product)

            # Get counts (Handover 0046: Include new metrics for create endpoint)
            project_count_result = await db.execute(
                select(Project).where(Project.tenant_key == tenant_key, Project.product_id == product.id)
            )
            projects = project_count_result.scalars().all()

            task_count_result = await db.execute(
                select(Task).where(Task.tenant_key == tenant_key, Task.product_id == product.id)
            )
            tasks = task_count_result.scalars().all()

            vision_docs_result = await db.execute(
                select(VisionDocument).where(
                    VisionDocument.tenant_key == tenant_key, VisionDocument.product_id == product.id
                )
            )
            vision_docs = vision_docs_result.scalars().all()

            # Calculate metrics (should all be 0 for new product)
            unfinished_projects = sum(1 for p in projects if p.status != "completed")
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(projects),
                task_count=len(tasks),
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=len(vision_docs),
                # Handover 0042: Include config_data in response
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                # Handover 0049: Include is_active status
                is_active=product.is_active,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    config_data: Optional[str] = Form(None),  # Handover 0042: Rich configuration as JSON string
    tenant_key: str = Depends(get_tenant_key),
):
    """Update an existing product (Handover 0042)"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Fetch existing product
            result = await db.execute(
                select(Product)
                .where(Product.id == product_id, Product.tenant_key == tenant_key)
                .options(selectinload(Product.projects), selectinload(Product.tasks))
            )
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Update fields if provided
            if name is not None:
                product.name = name
            if description is not None:
                product.description = description

            # Handover 0042: Parse and update config_data
            if config_data is not None:
                try:
                    config_dict = json.loads(config_data)
                    if not isinstance(config_dict, dict):
                        raise HTTPException(status_code=400, detail="config_data must be a JSON object")
                    product.config_data = config_dict
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid config_data JSON: {str(e)}")

            await db.commit()
            await db.refresh(product)

            # Get counts for response
            project_count_result = await db.execute(
                select(Project).where(Project.tenant_key == tenant_key, Project.product_id == product.id)
            )
            projects = project_count_result.scalars().all()

            task_count_result = await db.execute(
                select(Task).where(Task.tenant_key == tenant_key, Task.product_id == product.id)
            )
            tasks = task_count_result.scalars().all()

            vision_docs_result = await db.execute(
                select(VisionDocument).where(
                    VisionDocument.tenant_key == tenant_key, VisionDocument.product_id == product.id
                )
            )
            vision_docs = vision_docs_result.scalars().all()

            unfinished_projects = sum(1 for p in projects if p.status != "completed")
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(projects),
                task_count=len(tasks),
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=len(vision_docs),
                config_data=product.config_data,
                has_config_data=product.has_config_data,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    is_active: bool | None = Query(None, description="Filter by activation status"),
    tenant_key: str = Depends(get_tenant_key),
):
    """List all non-deleted products for the tenant (soft delete support)"""
    from api.app import state

    if not state.db_manager:
        # In setup mode, return empty list instead of error
        return []

    try:
        async with state.db_manager.get_session_async() as db:
            # Handover 0046 Issue #2: Query products with related counts including vision_documents
            # Apply optional is_active filter + EXCLUDE deleted products
            where_clauses = [
                Product.tenant_key == tenant_key,
                Product.deleted_at.is_(None)  # Exclude soft-deleted products
            ]
            if is_active is not None:
                where_clauses.append(Product.is_active == is_active)

            stmt = (
                select(Product)
                .where(*where_clauses)
                .options(
                    selectinload(Product.projects),
                    selectinload(Product.tasks),
                    selectinload(Product.vision_documents),  # NEW: Eager load vision documents
                )
                .limit(limit)
                .offset(offset)
            )

            result = await db.execute(stmt)
            products = result.scalars().all()

            response = []
            for product in products:
                # Handover 0046 Issue #2: Calculate unfinished/unresolved counts
                # Filter out deleted projects when counting
                projects = [p for p in (product.projects or []) if p.deleted_at is None]
                tasks = product.tasks or []

                # Count completed projects (excluding deleted)
                completed_projects = sum(1 for p in projects if p.status == "completed")

                # Count tasks (all states)
                total_tasks = len(tasks)

                # Count vision documents
                vision_doc_count = len(product.vision_documents) if product.vision_documents else 0

                response.append(
                    ProductResponse(
                        id=product.id,
                        name=product.name,
                        description=product.description,
                        vision_path=product.vision_path,
                        created_at=product.created_at,
                        updated_at=product.updated_at,
                        project_count=len(projects),  # Total projects (excluding deleted)
                        task_count=total_tasks,  # All tasks (any state)
                        has_vision=bool(product.vision_path),
                        # Updated metrics for new UI
                        unfinished_projects=len(projects) - completed_projects,  # For backwards compatibility
                        unresolved_tasks=sum(1 for t in tasks if t.status != "completed"),  # For backwards compatibility
                        vision_documents_count=vision_doc_count,
                        # Handover 0042: Include config_data in response
                        config_data=product.config_data,
                        has_config_data=product.has_config_data,
                        # Handover 0049: Include is_active status (BUG FIX)
                        is_active=product.is_active,
                    )
                )

            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Get a specific product by ID"""
    from api.app import state

    if not state.db_manager:
        # In setup mode, return 404 since we can't look up the product
        raise HTTPException(status_code=404, detail="Product not found (setup mode)")

    try:
        async with state.db_manager.get_session_async() as db:
            # Handover 0046 Issue #3: Query product with related data including vision_documents
            stmt = (
                select(Product)
                .where(Product.id == product_id, Product.tenant_key == tenant_key)
                .options(
                    selectinload(Product.projects),
                    selectinload(Product.tasks),
                    selectinload(Product.vision_documents),  # NEW: Eager load vision documents
                )
            )

            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Handover 0046 Issue #3: Calculate unfinished/unresolved counts
            projects = product.projects or []
            tasks = product.tasks or []

            # Count projects where status != 'completed'
            unfinished_projects = sum(1 for p in projects if p.status != "completed")

            # Count tasks where status != 'completed'
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")

            # Count vision documents
            vision_doc_count = len(product.vision_documents) if product.vision_documents else 0

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(projects),
                task_count=len(tasks),
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=vision_doc_count,
                # Handover 0042: Include config_data in response
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                # Handover 0049: Include is_active status
                is_active=product.is_active,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/cascade-impact", response_model=CascadeImpact)
async def get_cascade_impact(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Get cascade impact for deleting a product

    Returns counts of all data that will be cascade-deleted if this product is deleted:
    - Projects (total and unfinished)
    - Tasks (total and unresolved)
    - Vision documents
    - Context chunks
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Count projects
            projects_stmt = select(Project).where(Project.product_id == product_id, Project.tenant_key == tenant_key)
            projects_result = await db.execute(projects_stmt)
            projects = projects_result.scalars().all()
            projects_count = len(projects)

            # Count unfinished projects (status != 'completed')
            unfinished_projects = sum(1 for p in projects if p.status != "completed")

            # Count tasks
            tasks_stmt = select(Task).where(Task.product_id == product_id, Task.tenant_key == tenant_key)
            tasks_result = await db.execute(tasks_stmt)
            tasks = tasks_result.scalars().all()
            tasks_count = len(tasks)

            # Count unresolved tasks (status != 'completed')
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")

            # Count vision documents
            vision_docs_stmt = select(VisionDocument).where(
                VisionDocument.product_id == product_id, VisionDocument.tenant_key == tenant_key
            )
            vision_docs_result = await db.execute(vision_docs_stmt)
            vision_documents_count = len(vision_docs_result.scalars().all())

            # Count total chunks
            chunks_stmt = select(MCPContextIndex).where(
                MCPContextIndex.product_id == product_id, MCPContextIndex.tenant_key == tenant_key
            )
            chunks_result = await db.execute(chunks_stmt)
            total_chunks = len(chunks_result.scalars().all())

            return CascadeImpact(
                product_id=product_id,
                projects_count=projects_count,
                unfinished_projects=unfinished_projects,
                tasks_count=tasks_count,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=vision_documents_count,
                total_chunks=total_chunks,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Handover 0050: Helper function for active product info
async def get_active_product_info(db, tenant_key: str) -> Optional[Dict[str, Any]]:
    """
    Get active product summary info for tenant.

    Returns minimal product info for API responses and frontend state sync.
    Used by activation/deletion endpoints to provide context.

    Args:
        db: AsyncSession
        tenant_key: Tenant identifier

    Returns:
        {id, name, description, activated_at, active_projects_count} or None if no active product

    Performance: <10ms (database query)
    Note: Future enhancement - add Redis caching for <1ms response
    """
    from sqlalchemy import func
    from src.giljo_mcp.models import Project  # Handover 0050b

    # Find currently active product for tenant
    result = await db.execute(select(Product).where(Product.tenant_key == tenant_key, Product.is_active == True))
    active_product = result.scalar_one_or_none()

    if not active_product:
        return None

    # Handover 0050b: Count active projects (status='active' not is_active field)
    count_result = await db.execute(
        select(func.count(Project.id)).where(
            Project.product_id == active_product.id, Project.status == "active"  # Status field, not is_active
        )
    )
    active_projects_count = count_result.scalar() or 0

    return {
        "id": str(active_product.id),
        "name": active_product.name,
        "description": active_product.description,
        "activated_at": active_product.updated_at or active_product.created_at,
        "active_projects_count": active_projects_count,  # Handover 0050b
    }


@router.post("/{product_id}/activate", response_model=ProductActivationResponse)
async def activate_product(
    product_id: str, tenant_key: str = Depends(get_tenant_key), current_user: User = Depends(get_current_active_user)
):
    """
    Activate a product (Handover 0050)

    Sets this product as the active product for the tenant. Only one product
    can be active per tenant - activating this product will deactivate all others.

    Returns enhanced response with previous active product info for frontend
    warning dialog context.
    """
    from api.app import state

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # PHASE 1: Get current active product (for response context)
            previous_active = await get_active_product_info(db, tenant_key)

            # PHASE 2: Verify product exists and belongs to tenant
            result = await db.execute(
                select(Product)
                .where(Product.id == product_id, Product.tenant_key == tenant_key)
                .options(
                    selectinload(Product.projects), selectinload(Product.tasks), selectinload(Product.vision_documents)
                )
            )
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # PHASE 3: Atomic activation (deactivate others + activate this)
            await db.execute(
                update(Product)
                .where(Product.tenant_key == tenant_key, Product.id != product_id)
                .values(is_active=False)
            )

            # Handover 0050b: Deactivate all projects under previous active product(s)
            if previous_active:
                from src.giljo_mcp.models import Project

                # Get all active projects under previous product
                prev_projects_query = select(Project).where(
                    Project.product_id == previous_active["id"], Project.status == "active"
                )
                prev_projects_result = await db.execute(prev_projects_query)
                prev_active_projects = prev_projects_result.scalars().all()

                # Deactivate them (set to inactive - Handover 0071)
                for proj in prev_active_projects:
                    proj.status = "inactive"
                    logger.info(f"[Handover 0071] Deactivating project '{proj.name}' (parent product deactivated)")

            # Activate this product
            product.is_active = True
            await db.commit()
            await db.refresh(product)

            # PHASE 4: Calculate metrics for response
            projects = product.projects or []
            tasks = product.tasks or []
            unfinished_projects = sum(1 for p in projects if p.status != "completed")
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")
            vision_doc_count = len(product.vision_documents) if product.vision_documents else 0

            # PHASE 5: Build enhanced response with previous active product context
            return ProductActivationResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(projects),
                task_count=len(tasks),
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=vision_doc_count,
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                is_active=product.is_active,
                # Handover 0050: Enhanced fields
                previous_active_product=ActiveProductInfo(**previous_active) if previous_active else None,
                activation_timestamp=datetime.now(timezone.utc),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: str, tenant_key: str = Depends(get_tenant_key), current_user: User = Depends(get_current_active_user)
):
    """
    Deactivate a product (Handover 0049)

    Removes the active status from this product.
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            result = await db.execute(
                select(Product)
                .where(Product.id == product_id, Product.tenant_key == tenant_key)
                .options(
                    selectinload(Product.projects), selectinload(Product.tasks), selectinload(Product.vision_documents)
                )
            )
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Deactivate this product
            product.is_active = False
            await db.commit()
            await db.refresh(product)

            # Calculate metrics for response
            projects = product.projects or []
            tasks = product.tasks or []
            unfinished_projects = sum(1 for p in projects if p.status != "completed")
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")
            vision_doc_count = len(product.vision_documents) if product.vision_documents else 0

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(projects),
                task_count=len(tasks),
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=vision_doc_count,
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                is_active=product.is_active,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refresh-active", response_model=ActiveProductRefreshResponse)
async def refresh_active_product(
    tenant_key: str = Depends(get_tenant_key), current_user: User = Depends(get_current_active_user)
):
    """
    Get current active product state (Handover 0050)

    Returns the currently active product for the tenant, or None if no active product.
    Used for frontend state synchronization, especially after product deletions or
    when recovering from stale state.

    Use Cases:
    - Frontend initialization/boot-up
    - After deleting active product
    - Manual refresh after detecting stale state
    - Cross-browser-tab synchronization

    Performance: <10ms (database query)
    """
    from api.app import state
    from sqlalchemy import func

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get active product info
            active_info = await get_active_product_info(db, tenant_key)

            # Get total product count for UI state
            total_count_result = await db.execute(
                select(func.count(Product.id)).where(Product.tenant_key == tenant_key)
            )
            total_count = total_count_result.scalar() or 0

            return ActiveProductRefreshResponse(
                active_product=ActiveProductInfo(**active_info) if active_info else None,
                total_products_count=total_count,
                last_refreshed_at=datetime.now(timezone.utc),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}", response_model=ProductDeleteResponse)
async def delete_product(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """
    Soft delete a product with 10-day recovery window (similar to Handover 0070 for projects).

    Sets deleted_at timestamp and deactivates the product.
    If the product was active and other non-deleted products exist, automatically
    activates the oldest non-deleted product (by created_at).
    
    Physical deletion occurs after 10 days via purge_expired_deleted_products().
    """
    from api.app import state
    from sqlalchemy import func
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # PHASE 1: Get product and check status
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Check if already deleted
            if product.deleted_at is not None:
                raise HTTPException(status_code=400, detail="Product is already deleted")

            was_active = product.is_active
            product_name = product.name

            # PHASE 2: Soft delete product (set deleted_at and deactivate)
            product.deleted_at = datetime.now(timezone.utc)
            product.is_active = False
            await db.commit()

            logger.info(f"Product '{product_name}' (id: {product_id}) soft deleted. Recovery available for 10 days.")

            # PHASE 3: Count remaining non-deleted products
            remaining_count_result = await db.execute(
                select(func.count(Product.id)).where(
                    Product.tenant_key == tenant_key,
                    Product.deleted_at.is_(None)
                )
            )
            remaining_count = remaining_count_result.scalar() or 0

            # PHASE 4: Auto-activate oldest product if deleted product was active
            new_active = None
            if was_active and remaining_count > 0:
                # Get oldest non-deleted product (by created_at)
                oldest_result = await db.execute(
                    select(Product).where(
                        Product.tenant_key == tenant_key,
                        Product.deleted_at.is_(None)
                    ).order_by(Product.created_at.asc()).limit(1)
                )
                oldest_product = oldest_result.scalar_one_or_none()

                if oldest_product:
                    # Activate it
                    oldest_product.is_active = True
                    await db.commit()

                    logger.info(f"Auto-activated product '{oldest_product.name}' after deleting active product")

                    # Get info for response
                    new_active = {
                        "id": str(oldest_product.id),
                        "name": oldest_product.name,
                        "description": oldest_product.description,
                        "activated_at": datetime.now(timezone.utc),
                    }

            return ProductDeleteResponse(
                message=f"Product '{product_name}' moved to trash. Recoverable for 10 days.",
                deleted_product_id=str(product_id),
                was_active=was_active,
                remaining_products_count=remaining_count,
                new_active_product=ActiveProductInfo(**new_active) if new_active else None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class DeletedProductResponse(BaseModel):
    """Response model for deleted products list"""
    id: str
    name: str
    description: Optional[str]
    deleted_at: datetime
    days_until_purge: int
    purge_date: datetime
    project_count: int = Field(description="Total projects under this product")
    vision_documents_count: int = Field(description="Total vision documents")


@router.get("/deleted", response_model=list[DeletedProductResponse])
async def list_deleted_products(
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user)
):
    """
    List deleted products with recovery window (10 days).
    
    Returns all soft-deleted products for the tenant with:
    - Days until permanent purge
    - Purge date
    - Related entity counts
    """
    from api.app import state
    from sqlalchemy import func
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Query deleted products (deleted_at IS NOT NULL)
            stmt = select(Product).where(
                Product.tenant_key == tenant_key,
                Product.deleted_at.isnot(None)
            ).order_by(Product.deleted_at.desc())

            result = await db.execute(stmt)
            deleted_products_raw = result.scalars().all()

            deleted_products = []
            now = datetime.now(timezone.utc)

            for product in deleted_products_raw:
                # Calculate days until purge (10 days from deletion)
                deleted_at_utc = (
                    product.deleted_at.replace(tzinfo=timezone.utc)
                    if product.deleted_at.tzinfo is None
                    else product.deleted_at
                )
                purge_date = deleted_at_utc + timedelta(days=10)
                days_until_purge = max(0, (purge_date - now).days)

                # Count projects
                projects_count_result = await db.execute(
                    select(func.count(Project.id)).where(Project.product_id == product.id)
                )
                project_count = projects_count_result.scalar() or 0

                # Count vision documents
                vision_docs_count_result = await db.execute(
                    select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product.id)
                )
                vision_documents_count = vision_docs_count_result.scalar() or 0

                deleted_products.append(
                    DeletedProductResponse(
                        id=product.id,
                        name=product.name,
                        description=product.description,
                        deleted_at=deleted_at_utc,
                        days_until_purge=days_until_purge,
                        purge_date=purge_date,
                        project_count=project_count,
                        vision_documents_count=vision_documents_count,
                    )
                )

            logger.info(f"Retrieved {len(deleted_products)} deleted products for tenant (user: {current_user.username})")

            return deleted_products

    except Exception as e:
        logger.error(f"Failed to list deleted products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/restore", response_model=ProductResponse)
async def restore_product(
    product_id: str,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user)
):
    """
    Restore a soft-deleted product.
    
    Clears deleted_at timestamp and reactivates the product as inactive (safe default).
    User must manually activate the product after restoration.
    """
    from api.app import state
    from sqlalchemy import select, func
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Fetch product and verify tenant ownership
            stmt = select(Product).where(
                Product.id == product_id,
                Product.tenant_key == tenant_key
            )
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found or already purged")

            # Verify product is deleted
            if product.deleted_at is None:
                raise HTTPException(status_code=400, detail="Product is not deleted")

            # Restore product: Clear deleted_at, keep is_active as False (safe default)
            product.deleted_at = None
            product.is_active = False  # User must manually activate
            product.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(product)

            # Get counts for response
            project_count_result = await db.execute(
                select(func.count(Project.id)).where(Project.product_id == product.id)
            )
            project_count = project_count_result.scalar() or 0

            task_count_result = await db.execute(
                select(func.count(Task.id)).where(Task.product_id == product.id)
            )
            task_count = task_count_result.scalar() or 0

            vision_docs_result = await db.execute(
                select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product.id)
            )
            vision_documents_count = vision_docs_result.scalar() or 0

            # Calculate unfinished/unresolved counts (optional for response)
            projects_result = await db.execute(
                select(Project).where(Project.product_id == product.id)
            )
            projects = projects_result.scalars().all()
            unfinished_projects = sum(1 for p in projects if p.status != "completed")

            tasks_result = await db.execute(
                select(Task).where(Task.product_id == product.id)
            )
            tasks = tasks_result.scalars().all()
            unresolved_tasks = sum(1 for t in tasks if t.status != "completed")

            logger.info(f"Product '{product.name}' (id: {product_id}) restored by {current_user.username}")

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=project_count,
                task_count=task_count,
                has_vision=bool(product.vision_path),
                unfinished_projects=unfinished_projects,
                unresolved_tasks=unresolved_tasks,
                vision_documents_count=vision_documents_count,
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                is_active=product.is_active,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/upload-vision", response_model=dict)
async def upload_vision_document(
    product_id: str, vision_file: UploadFile = File(...), tenant_key: str = Depends(get_tenant_key)
):
    """Upload or replace vision document for a product"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get product
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Validate file type
            allowed_extensions = {".txt", ".md", ".markdown"}
            file_extension = Path(vision_file.filename).suffix.lower()
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
                )

            # Delete old vision file if exists
            if product.vision_path and os.path.exists(product.vision_path):
                os.remove(product.vision_path)

            # Save new vision document
            storage_path = get_vision_storage_path(tenant_key, product_id)
            file_path = storage_path / vision_file.filename

            async with aiofiles.open(file_path, "wb") as f:
                content = await vision_file.read()
                await f.write(content)

            # Process with EnhancedChunker
            chunker = EnhancedChunker()
            chunks = chunker.chunk_content(content.decode("utf-8"), source_name=vision_file.filename)

            # Update product
            product.vision_path = str(file_path)
            product.meta_data = {
                "vision_chunks": len(chunks),
                "vision_filename": vision_file.filename,
                "vision_size": len(content),
                "chunks_metadata": [
                    {
                        "chunk_number": chunk["chunk_number"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "boundary_type": chunk["boundary_type"],
                        "keywords": chunk["keywords"][:5],
                        "headers": chunk["headers"],
                    }
                    for chunk in chunks
                ],
            }
            product.updated_at = datetime.now(timezone.utc)

            await db.commit()

            return {
                "message": "Vision document uploaded successfully",
                "filename": vision_file.filename,
                "chunks": len(chunks),
                "size": len(content),
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/vision-chunks", response_model=List[VisionChunk])
async def get_vision_chunks(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Get processed vision document chunks for a product"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get product
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            if not product.vision_path:
                raise HTTPException(status_code=404, detail="No vision document uploaded")

            if not os.path.exists(product.vision_path):
                raise HTTPException(status_code=404, detail="Vision document file not found")

            # Read and chunk the document
            async with aiofiles.open(product.vision_path, "r", encoding="utf-8") as f:
                content = await f.read()

            chunker = EnhancedChunker()
            chunks = chunker.chunk_content(content, source_name=Path(product.vision_path).name)

            # Convert to response format
            response = []
            for chunk in chunks:
                response.append(
                    VisionChunk(
                        chunk_number=chunk["chunk_number"],
                        total_chunks=chunk["total_chunks"],
                        content=chunk["content"],
                        char_start=chunk["char_start"],
                        char_end=chunk["char_end"],
                        boundary_type=chunk["boundary_type"],
                        keywords=chunk["keywords"],
                        headers=chunk["headers"],
                    )
                )

            return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_nested_value(data: dict, path: str) -> Any:
    """
    Extract nested value from dictionary using dot notation.

    Args:
        data: Dictionary to extract from
        path: Dot-separated path (e.g., 'tech_stack.languages')

    Returns:
        Value at path, or None if not found

    Example:
        >>> config = {"tech_stack": {"languages": "Python"}}
        >>> _get_nested_value(config, "tech_stack.languages")
        'Python'
        >>> _get_nested_value(config, "tech_stack.missing")
        None
    """
    if not data:
        return None

    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None

    return value


@router.get("/active/token-estimate", response_model=TokenEstimateResponse)
async def get_active_product_token_estimate(current_user: User = Depends(get_current_active_user)):
    """
    Calculate token estimate for active product's config_data fields (Handover 0049).

    This endpoint:
    1. Fetches the active product (is_active=True) for current user's tenant
    2. Gets user's field_priority_config (or uses default from defaults.py)
    3. Extracts values from product.config_data using dot notation
    4. Calculates tokens per field using character/4 formula
    5. Adds 500 token overhead for mission structure
    6. Returns detailed breakdown with budget percentage

    Token Calculation:
        - Per field: len(field_value) / 4 (rounded up)
        - Overhead: 500 tokens (fixed)
        - Total: sum(field_tokens) + overhead

    Multi-Tenant Isolation:
        Only returns active product for current_user's tenant_key.

    Returns:
        TokenEstimateResponse with detailed token breakdown

    Raises:
        404: No active product found for user's tenant
        401: User not authenticated

    Example Response:
        {
            "product_id": "prod-123",
            "product_name": "My Product",
            "field_tokens": {
                "tech_stack.languages": 15,
                "tech_stack.backend": 12,
                ...
            },
            "total_field_tokens": 285,
            "overhead_tokens": 500,
            "total_tokens": 785,
            "token_budget": 2000,
            "percentage_used": 39.25
        }
    """
    from api.app import state
    from math import ceil

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Fetch active product for user's tenant (CRITICAL: Multi-tenant isolation)
            stmt = select(Product).where(Product.tenant_key == current_user.tenant_key, Product.is_active == True)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(
                    status_code=404, detail=f"No active product found for tenant. Please activate a product first."
                )

            # Get user's field priority config (or use default)
            field_config = current_user.field_priority_config or DEFAULT_FIELD_PRIORITY

            # Extract token budget and field priorities
            token_budget = field_config.get("token_budget", DEFAULT_FIELD_PRIORITY["token_budget"])
            field_priorities = field_config.get("fields", DEFAULT_FIELD_PRIORITY["fields"])

            # Calculate token count for each prioritized field
            field_tokens: Dict[str, int] = {}
            product_config = product.config_data or {}

            for field_path in field_priorities.keys():
                # Extract field value using dot notation
                field_value = _get_nested_value(product_config, field_path)

                if field_value is None:
                    # Field not present in config_data
                    field_tokens[field_path] = 0
                elif isinstance(field_value, str):
                    # Calculate tokens: character count / 4 (rounded up)
                    char_count = len(field_value)
                    tokens = ceil(char_count / 4.0)
                    field_tokens[field_path] = tokens
                else:
                    # Non-string value (dict, list, etc.) - convert to JSON string
                    json_str = json.dumps(field_value)
                    char_count = len(json_str)
                    tokens = ceil(char_count / 4.0)
                    field_tokens[field_path] = tokens

            # Calculate totals
            total_field_tokens = sum(field_tokens.values())
            overhead_tokens = 500  # Fixed overhead for mission structure
            total_tokens = total_field_tokens + overhead_tokens

            # Calculate percentage used
            percentage_used = round((total_tokens / token_budget) * 100, 2) if token_budget > 0 else 0.0

            return TokenEstimateResponse(
                product_id=product.id,
                product_name=product.name,
                field_tokens=field_tokens,
                total_field_tokens=total_field_tokens,
                overhead_tokens=overhead_tokens,
                total_tokens=total_tokens,
                token_budget=token_budget,
                percentage_used=percentage_used,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
