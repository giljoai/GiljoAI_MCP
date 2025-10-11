"""
Product management API endpoints with vision document upload support
"""

import os
import uuid
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from api.dependencies import get_tenant_key
from src.giljo_mcp.models import Product, Project, Task
from src.giljo_mcp.tools.chunking import EnhancedChunker

router = APIRouter()


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


class VisionChunk(BaseModel):
    chunk_number: int
    total_chunks: int
    content: str
    char_start: int
    char_end: int
    boundary_type: str
    keywords: List[str]
    headers: List[str]


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
    tenant_key: str = Depends(get_tenant_key),
):
    """Create a new product with optional vision document upload"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Create product in database
        product = Product(id=str(uuid.uuid4()), tenant_key=tenant_key, name=name, description=description)

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

            # Get counts
            project_count_result = await db.execute(
                select(Project).where(Project.tenant_key == tenant_key, Project.product_id == product.id)
            )
            project_count = len(project_count_result.scalars().all())

            task_count_result = await db.execute(
                select(Task).where(Task.tenant_key == tenant_key, Task.product_id == product.id)
            )
            task_count = len(task_count_result.scalars().all())

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
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    tenant_key: str = Depends(get_tenant_key),
):
    """List all products for the tenant"""
    from api.app import state

    if not state.db_manager:
        # In setup mode, return empty list instead of error
        return []

    try:
        async with state.db_manager.get_session_async() as db:
            # Query products with related counts
            stmt = (
                select(Product)
                .where(Product.tenant_key == tenant_key)
                .options(selectinload(Product.projects), selectinload(Product.tasks))
                .limit(limit)
                .offset(offset)
            )

            result = await db.execute(stmt)
            products = result.scalars().all()

            response = []
            for product in products:
                response.append(
                    ProductResponse(
                        id=product.id,
                        name=product.name,
                        description=product.description,
                        vision_path=product.vision_path,
                        created_at=product.created_at,
                        updated_at=product.updated_at,
                        project_count=len(product.projects) if product.projects else 0,
                        task_count=len(product.tasks) if product.tasks else 0,
                        has_vision=bool(product.vision_path),
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
            stmt = (
                select(Product)
                .where(Product.id == product_id, Product.tenant_key == tenant_key)
                .options(selectinload(Product.projects), selectinload(Product.tasks))
            )

            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            return ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                vision_path=product.vision_path,
                created_at=product.created_at,
                updated_at=product.updated_at,
                project_count=len(product.projects) if product.projects else 0,
                task_count=len(product.tasks) if product.tasks else 0,
                has_vision=bool(product.vision_path),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product_update: ProductUpdate, tenant_key: str = Depends(get_tenant_key)):
    """Update a product"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get existing product
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Update fields
            update_data = {}
            if product_update.name is not None:
                update_data["name"] = product_update.name
            if product_update.description is not None:
                update_data["description"] = product_update.description

            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)

                stmt = update(Product).where(Product.id == product_id).values(**update_data).returning(Product)

                result = await db.execute(stmt)
                await db.commit()
                product = result.scalar_one()

            # Get counts
            project_count_result = await db.execute(
                select(Project).where(Project.tenant_key == tenant_key, Project.product_id == product.id)
            )
            project_count = len(project_count_result.scalars().all())

            task_count_result = await db.execute(
                select(Task).where(Task.tenant_key == tenant_key, Task.product_id == product.id)
            )
            task_count = len(task_count_result.scalars().all())

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
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}")
async def delete_product(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Delete a product and all related data"""
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

            # Delete vision document files if they exist
            if product.vision_path and os.path.exists(product.vision_path):
                try:
                    os.remove(product.vision_path)
                    # Try to remove the vision directory if empty
                    vision_dir = Path(product.vision_path).parent
                    if vision_dir.exists() and not any(vision_dir.iterdir()):
                        vision_dir.rmdir()
                except Exception:
                    pass  # Don't fail deletion if file cleanup fails

            # Delete product (cascade will handle related records)
            await db.delete(product)
            await db.commit()

            return {"message": "Product deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
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
