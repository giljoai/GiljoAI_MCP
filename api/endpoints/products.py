"""
Product management API endpoints with vision document upload support
"""

import os
import uuid
import aiofiles
import logging
from datetime import datetime, timezone, timedelta
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
    project_path: Optional[str] = Field(None, description="File system path to product folder (required for agent export)")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_path: Optional[str] = None


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

    # Handover 0084: Project path for agent export
    project_path: Optional[str] = Field(None, description="File system path to product folder (required for agent export)")


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
    # Helpful context fields used by the UI (added by refresh endpoint)
    total_products_count: Optional[int] = None
    last_refreshed_at: Optional[datetime] = None


class DeletedProductResponse(BaseModel):
    """Response model for deleted products list (Handover 0070)"""

    id: str
    name: str
    description: Optional[str]
    deleted_at: datetime
    days_until_purge: int = Field(ge=0, description="Days remaining before permanent deletion")
    purge_date: datetime = Field(description="Date when product will be permanently deleted")
    project_count: int = Field(ge=0, description="Total projects under this product")
    vision_documents_count: int = Field(ge=0, description="Total vision documents")


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


async def get_active_product_info(db, tenant_key: str) -> Optional[Dict[str, Any]]:
    """Return a compact summary of the active product for a tenant.

    Used by the refresh-active endpoint and activation responses.
    """
    from sqlalchemy import select, func

    active_result = await db.execute(
        select(Product).where(Product.tenant_key == tenant_key, Product.is_active == True)  # noqa: E712
    )
    active_product = active_result.scalar_one_or_none()
    if not active_product:
        return None

    # Optionally count active projects; default to 0 on any error
    try:
        projects_count_result = await db.execute(
            select(func.count(Project.id)).where(
                Project.product_id == active_product.id,
                Project.status == "active",
            )
        )
        active_projects_count = projects_count_result.scalar() or 0
    except Exception:
        active_projects_count = 0

    return {
        "id": str(active_product.id),
        "name": active_product.name,
        "description": active_product.description,
        "activated_at": active_product.updated_at or active_product.created_at,
        "active_projects_count": active_projects_count,
    }


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


def validate_project_path(project_path: str) -> bool:
    """
    Validate project path for agent export functionality.

    Args:
        project_path: File system path to validate

    Returns:
        True if valid, raises HTTPException if invalid
    """
    if not project_path:
        return True  # Optional field

    try:
        from pathlib import Path

        # Expand user home directory if present
        path = Path(project_path).expanduser()

        # Check if path exists and is a directory
        if not path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {path}"
            )

        if not path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Project path is not a directory: {path}"
            )

        # Check if path is writable (for .claude/agents creation)
        try:
            test_dir = path / ".claude_test_write"
            test_dir.mkdir(exist_ok=True)
            test_dir.rmdir()
        except (PermissionError, OSError):
            raise HTTPException(
                status_code=400,
                detail=f"Project path is not writable: {path}"
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project path: {e}"
        )

@router.post("/", response_model=ProductResponse)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    project_path: Optional[str] = Form(None),  # Handover 0084: Project path for agent export
    vision_file: Optional[UploadFile] = File(None),
    config_data: Optional[str] = Form(None),  # Handover 0042: Rich configuration as JSON string
    tenant_key: str = Depends(get_tenant_key),
):
    """Create a new product with optional vision document upload"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Handover 0084: Validate project path if provided
        if project_path:
            validate_project_path(project_path)

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
            project_path=project_path,  # Handover 0084: Set project path for agent export
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
                # Handover 0084: Include project_path for agent export
                project_path=product.project_path,
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
                        # Handover 0084: Include project_path for agent export
                        project_path=product.project_path,
                    )
                )

            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# IMPORTANT: Specific string routes MUST come before generic /{product_id} route
# to prevent FastAPI from treating strings as UUID parameters

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
                value = _get_nested_value(product_config, field_path)
                if value is not None and value != "":
                    # Calculate tokens (character count / 4)
                    token_count = ceil(len(str(value)) / 4)
                    field_tokens[field_path] = token_count

            # Sum field tokens
            total_field_tokens = sum(field_tokens.values())

            # Add overhead
            overhead_tokens = 500
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
                # Handover 0084: Include project_path for agent export
                project_path=product.project_path,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/activate", response_model=ProductActivationResponse)
async def activate_product(
    product_id: str,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
):
    """Activate a product for the current tenant and ensure single-active invariant.

    - Deactivates any currently active product in the same tenant.
    - Activates the requested product (if not soft-deleted).
    - Returns the activated product with optional info about the previously active product.
    """
    from api.app import state
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Fetch target product and validate ownership
            result = await db.execute(
                select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            )
            product = result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            if product.deleted_at is not None:
                raise HTTPException(status_code=400, detail="Cannot activate a deleted product. Restore it first.")

            # Fetch currently active product
            current_active_info = await get_active_product_info(db, tenant_key)

            # If different product is active, deactivate it first
            if current_active_info and current_active_info["id"] != product.id:
                current_active_result = await db.execute(
                    select(Product).where(Product.id == current_active_info["id"])
                )
                current_active = current_active_result.scalar_one_or_none()
                if current_active:
                    current_active.is_active = False

                    # CASCADE: Auto-pause all active projects from the old product
                    # This maintains single source of truth when switching products
                    old_projects_stmt = select(Project).where(
                        Project.product_id == current_active.id,
                        Project.status == "active"
                    )
                    old_projects_result = await db.execute(old_projects_stmt)
                    old_active_projects = old_projects_result.scalars().all()

                    for proj in old_active_projects:
                        proj.status = "inactive"
                        logger.info(
                            f"Auto-deactivated project '{proj.name}' from product '{current_active.name}' "
                            f"(switching to product '{product.name}')"
                        )

                    # CRITICAL: Flush deactivation before activation to avoid unique constraint violation
                    # This ensures old product is fully deactivated before new product becomes active
                    await db.flush()

            # Activate requested product
            product.is_active = True
            product.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(product)

            logger.info(
                f"Product '{product.name}' activated by {current_user.username} (tenant={tenant_key})"
            )

            return ProductActivationResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=0,
                task_count=0,
                has_vision=bool(product.vision_path),
                unresolved_tasks=0,
                unfinished_projects=0,
                vision_documents_count=0,
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                is_active=product.is_active,
                previous_active_product=ActiveProductInfo(**current_active_info)
                if current_active_info and current_active_info["id"] != product.id
                else None,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: str,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
):
    """Deactivate a product for the current tenant (resulting in no active product)."""
    from api.app import state
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Fetch product and validate ownership
            result = await db.execute(
                select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            )
            product = result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Deactivate product
            product.is_active = False
            product.updated_at = datetime.now(timezone.utc)

            # CASCADE: Auto-deactivate all active projects under this product
            # This maintains single source of truth - inactive product cannot have active projects
            projects_stmt = select(Project).where(
                Project.product_id == product_id,
                Project.status == "active"
            )
            projects_result = await db.execute(projects_stmt)
            active_projects = projects_result.scalars().all()

            deactivated_project_names = []
            for proj in active_projects:
                proj.status = "inactive"
                deactivated_project_names.append(proj.name)
                logger.info(
                    f"Auto-deactivated project '{proj.name}' (parent product '{product.name}' deactivated)"
                )

            await db.commit()
            await db.refresh(product)

            logger.info(
                f"Product '{product.name}' deactivated by {current_user.username} (tenant={tenant_key})"
                + (f" - {len(deactivated_project_names)} project(s) auto-deactivated" if deactivated_project_names else "")
            )

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=0,
                task_count=0,
                has_vision=bool(product.vision_path),
                unresolved_tasks=0,
                unfinished_projects=0,
                vision_documents_count=0,
                config_data=product.config_data,
                has_config_data=product.has_config_data,
                is_active=product.is_active,
                # Handover 0084: Include project_path for agent export
                project_path=product.project_path,
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

    This allows the frontend to show a confirmation dialog with full impact details.
    """
    from api.app import state
    from sqlalchemy import func

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            product_stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            product_result = await db.execute(product_stmt)
            product = product_result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Count projects
            projects_count_stmt = select(func.count(Project.id)).where(Project.product_id == product_id)
            projects_result = await db.execute(projects_count_stmt)
            total_projects = projects_result.scalar() or 0

            # Count unfinished projects (status != 'completed')
            unfinished_projects_stmt = select(func.count(Project.id)).where(
                Project.product_id == product_id, Project.status != "completed"
            )
            unfinished_result = await db.execute(unfinished_projects_stmt)
            unfinished_projects = unfinished_result.scalar() or 0

            # Count tasks
            tasks_count_stmt = select(func.count(Task.id)).where(Task.product_id == product_id)
            tasks_result = await db.execute(tasks_count_stmt)
            total_tasks = tasks_result.scalar() or 0

            # Count unresolved tasks (status != 'completed')
            unresolved_tasks_stmt = select(func.count(Task.id)).where(
                Task.product_id == product_id, Task.status != "completed"
            )
            unresolved_result = await db.execute(unresolved_tasks_stmt)
            unresolved_tasks = unresolved_result.scalar() or 0

            # Count vision documents
            vision_docs_stmt = select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product_id)
            vision_docs_result = await db.execute(vision_docs_stmt)
            vision_documents = vision_docs_result.scalar() or 0

            return CascadeImpact(
                product_id=product_id,
                product_name=product.name,
                total_projects=total_projects,
                unfinished_projects=unfinished_projects,
                total_tasks=total_tasks,
                unresolved_tasks=unresolved_tasks,
                vision_documents=vision_documents,
                will_cascade_delete=total_projects > 0 or total_tasks > 0 or vision_documents > 0,
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
                # Handover 0084: Include project_path for agent export
                project_path=product.project_path,
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



# ============================================================================
# GENERIC ROUTES - MUST BE LAST
# ============================================================================
# FastAPI matches routes in definition order. Generic routes like
# PUT /{product_id} and GET /{product_id} must come AFTER all specific
# sub-routes like POST /{product_id}/activate to prevent route conflicts.
# ============================================================================

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    project_path: Optional[str] = Form(None),  # Handover 0084: Project path for agent export
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
            if project_path is not None:  # Handover 0084: Update project path
                validate_project_path(project_path)  # Validate before setting
                product.project_path = project_path

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
                # Handover 0084: Include project_path for agent export
                project_path=product.project_path,
            )

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
