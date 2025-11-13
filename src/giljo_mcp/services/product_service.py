"""
ProductService - Dedicated service for product domain logic

Handover 0127b: Extract product operations from direct database access
to follow established service layer pattern.

Responsibilities:
- CRUD operations for products
- Product lifecycle management (activate, deactivate, archive, restore)
- Product metrics and statistics
- Vision document management
- Cascade impact analysis

Design Principles:
- Single Responsibility: Only product domain logic
- Dependency Injection: Accepts DatabaseManager and tenant_key
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product, Project, Task, VisionDocument


logger = logging.getLogger(__name__)


class ProductService:
    """
    Service for managing product lifecycle and operations.

    This service handles all product-related operations including:
    - Creating, reading, updating, deleting products
    - Product activation/deactivation (single active product per tenant)
    - Product metrics and statistics
    - Vision document management
    - Cascade impact analysis for deletions

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_key: str):
        """
        Initialize ProductService with database and tenant isolation.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        project_path: Optional[str] = None,
        config_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new product.

        Args:
            name: Product name (required)
            description: Product description
            project_path: File system path to product folder
            config_data: Rich configuration data (architecture, tech_stack, etc.)

        Returns:
            Dict with success status and product details or error

        Example:
            >>> result = await service.create_product(
            ...     name="MyApp",
            ...     description="Mobile application",
            ...     project_path="/projects/myapp"
            ... )
            >>> print(result["product_id"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Check for duplicate name (excluding soft-deleted)
                stmt = select(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.name == name,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    return {
                        "success": False,
                        "error": f"Product '{name}' already exists"
                    }

                # Create product
                product = Product(
                    id=str(uuid4()),
                    tenant_key=self.tenant_key,
                    name=name,
                    description=description,
                    project_path=project_path,
                    config_data=config_data or {},
                    is_active=False,  # Products start inactive
                    created_at=datetime.now(timezone.utc),
                )

                session.add(product)
                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Created product {product.id} for tenant {self.tenant_key}")

                return {
                    "success": True,
                    "product_id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "is_active": product.is_active,
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                }

        except Exception as e:
            self._logger.exception(f"Failed to create product: {e}")
            return {"success": False, "error": str(e)}

    async def get_product(
        self,
        product_id: str,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Get a specific product by ID with optional metrics.

        Args:
            product_id: Product UUID
            include_metrics: Include project/task counts (default: True)

        Returns:
            Dict with success status and product details or error

        Example:
            >>> result = await service.get_product("abc-123")
            >>> if result["success"]:
            ...     print(result["product"]["name"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Eagerly load vision_documents to prevent lazy-loading issues
                stmt = select(Product).options(
                    selectinload(Product.vision_documents)
                ).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                product_data = {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "vision_path": product.primary_vision_path,  # Using new VisionDocument relationship
                    "project_path": product.project_path,
                    "is_active": product.is_active,
                    "config_data": product.config_data,
                    "has_config_data": bool(product.config_data),
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                }

                if include_metrics:
                    metrics = await self._get_product_metrics(session, product_id)
                    product_data.update(metrics)

                return {
                    "success": True,
                    "product": product_data
                }

        except Exception as e:
            self._logger.exception(f"Failed to get product: {e}")
            return {"success": False, "error": str(e)}

    async def list_products(
        self,
        include_inactive: bool = False,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        List all products for tenant with optional filtering.

        Args:
            include_inactive: Include inactive products (default: False)
            include_metrics: Include project/task counts (default: True)

        Returns:
            Dict with success status and list of products or error

        Example:
            >>> result = await service.list_products()
            >>> for product in result["products"]:
            ...     print(product["name"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                conditions = [
                    Product.tenant_key == self.tenant_key,
                    Product.deleted_at.is_(None)
                ]

                if not include_inactive:
                    conditions.append(Product.is_active == True)

                # Eagerly load vision_documents to avoid lazy loading in property access
                # Sort: active products first, then by creation date (newest first)
                stmt = (
                    select(Product)
                    .where(and_(*conditions))
                    .options(selectinload(Product.vision_documents))
                    .order_by(Product.is_active.desc(), Product.created_at.desc())
                )
                result = await session.execute(stmt)
                products = result.scalars().all()

                product_list = []
                for product in products:
                    product_data = {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "vision_path": product.primary_vision_path,  # Using new VisionDocument relationship
                        "project_path": product.project_path,
                        "is_active": product.is_active,
                        "config_data": product.config_data,
                        "has_config_data": bool(product.config_data),
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    }

                    if include_metrics:
                        metrics = await self._get_product_metrics(session, product.id)
                        product_data.update(metrics)

                    product_list.append(product_data)

                self._logger.debug(f"Found {len(product_list)} products for tenant {self.tenant_key}")

                return {
                    "success": True,
                    "products": product_list
                }

        except Exception as e:
            self._logger.exception(f"Failed to list products: {e}")
            return {"success": False, "error": str(e)}

    async def update_product(
        self,
        product_id: str,
        **updates
    ) -> Dict[str, Any]:
        """
        Update a product.

        Args:
            product_id: Product UUID
            **updates: Fields to update (name, description, project_path, config_data, etc.)

        Returns:
            Dict with success status and updated product or error

        Example:
            >>> result = await service.update_product(
            ...     "abc-123",
            ...     description="Updated description",
            ...     config_data={"tech_stack": {"python": "3.11"}}
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                # Apply updates
                for field, value in updates.items():
                    if hasattr(product, field):
                        setattr(product, field, value)

                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Updated product {product_id}")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to update product: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def activate_product(self, product_id: str) -> Dict[str, Any]:
        """
        Activate a product (deactivates other products for tenant).

        Only one product can be active at a time per tenant.

        Args:
            product_id: Product UUID to activate

        Returns:
            Dict with success status and activated product or error

        Example:
            >>> result = await service.activate_product("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Verify product exists
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                # Deactivate all other products for tenant
                deactivate_stmt = select(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.is_active == True,
                        Product.id != product_id
                    )
                )
                deactivate_result = await session.execute(deactivate_stmt)
                products_to_deactivate = deactivate_result.scalars().all()

                for p in products_to_deactivate:
                    p.is_active = False
                    p.updated_at = datetime.now(timezone.utc)

                # Activate target product
                product.is_active = True
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(product)

                self._logger.info(
                    f"Activated product {product_id} (deactivated {len(products_to_deactivate)} others)"
                )

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    },
                    "deactivated_count": len(products_to_deactivate)
                }

        except Exception as e:
            self._logger.exception(f"Failed to activate product: {e}")
            return {"success": False, "error": str(e)}

    async def deactivate_product(self, product_id: str) -> Dict[str, Any]:
        """
        Deactivate a product.

        Args:
            product_id: Product UUID to deactivate

        Returns:
            Dict with success status and deactivated product or error

        Example:
            >>> result = await service.deactivate_product("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                product.is_active = False
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Deactivated product {product_id}")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to deactivate product: {e}")
            return {"success": False, "error": str(e)}

    async def delete_product(self, product_id: str) -> Dict[str, Any]:
        """
        Soft delete a product.

        Args:
            product_id: Product UUID to delete

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.delete_product("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                # Soft delete
                product.deleted_at = datetime.now(timezone.utc)
                product.is_active = False  # Deactivate when deleting
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()

                self._logger.info(f"Soft deleted product {product_id}")

                return {
                    "success": True,
                    "message": "Product deleted successfully",
                    "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
                }

        except Exception as e:
            self._logger.exception(f"Failed to delete product: {e}")
            return {"success": False, "error": str(e)}

    async def restore_product(self, product_id: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted product.

        Args:
            product_id: Product UUID to restore

        Returns:
            Dict with success status and restored product or error

        Example:
            >>> result = await service.restore_product("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.isnot(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Deleted product not found"
                    }

                # Restore
                product.deleted_at = None
                product.updated_at = datetime.now(timezone.utc)
                # Note: Don't auto-activate on restore, let user explicitly activate

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Restored product {product_id}")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to restore product: {e}")
            return {"success": False, "error": str(e)}

    async def list_deleted_products(self) -> Dict[str, Any]:
        """
        List soft-deleted products with purge information.

        Returns:
            Dict with success status and list of deleted products

        Example:
            >>> result = await service.list_deleted_products()
            >>> for product in result["products"]:
            ...     print(f"{product['name']} - purge in {product['days_until_purge']} days")
        """
        try:
            PURGE_DAYS = 30  # 30-day purge policy

            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.isnot(None)
                    )
                ).order_by(Product.deleted_at.desc())

                result = await session.execute(stmt)
                deleted_products = result.scalars().all()

                product_list = []
                for product in deleted_products:
                    # Calculate purge date
                    purge_date = product.deleted_at + timedelta(days=PURGE_DAYS)
                    days_until_purge = max(0, (purge_date - datetime.now(timezone.utc)).days)

                    # Count related entities
                    project_count = await session.execute(
                        select(func.count(Project.id)).where(Project.product_id == product.id)
                    )
                    vision_count = await session.execute(
                        select(func.count(VisionDocument.id)).where(
                            VisionDocument.product_id == product.id
                        )
                    )

                    product_list.append({
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
                        "days_until_purge": days_until_purge,
                        "purge_date": purge_date.isoformat(),
                        "project_count": project_count.scalar() or 0,
                        "vision_documents_count": vision_count.scalar() or 0,
                    })

                return {
                    "success": True,
                    "products": product_list
                }

        except Exception as e:
            self._logger.exception(f"Failed to list deleted products: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Active Product Management
    # ============================================================================

    async def get_active_product(self) -> Dict[str, Any]:
        """
        Get the currently active product for the tenant.

        Returns:
            Dict with success status and active product or error

        Example:
            >>> result = await service.get_active_product()
            >>> if result["success"] and result.get("product"):
            ...     print(f"Active: {result['product']['name']}")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                stmt = select(Product).where(
                    and_(
                        Product.tenant_key == self.tenant_key,
                        Product.is_active == True,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": True,
                        "product": None,
                        "message": "No active product"
                    }

                # Get metrics for active product
                metrics = await self._get_product_metrics(session, product.id)

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "project_path": product.project_path,
                        "config_data": product.config_data,
                        "has_config_data": bool(product.config_data),
                        **metrics
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to get active product: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Metrics & Statistics
    # ============================================================================

    async def get_product_statistics(self, product_id: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a product.

        Args:
            product_id: Product UUID

        Returns:
            Dict with success status and statistics or error

        Example:
            >>> result = await service.get_product_statistics("abc-123")
            >>> print(f"Projects: {result['statistics']['total_projects']}")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Verify product exists
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                metrics = await self._get_product_metrics(session, product_id)

                return {
                    "success": True,
                    "statistics": {
                        "product_id": product_id,
                        "name": product.name,
                        "is_active": product.is_active,
                        **metrics,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to get product statistics: {e}")
            return {"success": False, "error": str(e)}

    async def get_cascade_impact(self, product_id: str) -> Dict[str, Any]:
        """
        Get cascade impact analysis for product deletion.

        Shows what entities would be affected by deleting this product.

        Args:
            product_id: Product UUID

        Returns:
            Dict with success status and impact analysis

        Example:
            >>> result = await service.get_cascade_impact("abc-123")
            >>> print(f"Will affect {result['impact']['total_projects']} projects")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Verify product exists
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": "Product not found"
                    }

                # Count related entities
                project_count = await session.execute(
                    select(func.count(Project.id)).where(
                        and_(
                            Project.product_id == product_id,
                            or_(Project.status != "deleted", Project.status.is_(None))
                        )
                    )
                )

                task_count = await session.execute(
                    select(func.count(Task.id)).where(Task.product_id == product_id)
                )

                vision_count = await session.execute(
                    select(func.count(VisionDocument.id)).where(
                        VisionDocument.product_id == product_id
                    )
                )

                return {
                    "success": True,
                    "impact": {
                        "product_id": product_id,
                        "product_name": product.name,
                        "total_projects": project_count.scalar() or 0,
                        "total_tasks": task_count.scalar() or 0,
                        "total_vision_documents": vision_count.scalar() or 0,
                        "warning": "Deleting this product will soft-delete all related entities"
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to get cascade impact: {e}")
            return {"success": False, "error": str(e)}

    async def upload_vision_document(
        self,
        product_id: str,
        content: str,
        filename: str,
        auto_chunk: bool = True,
        max_tokens: int = 25000,
    ) -> Dict[str, Any]:
        """
        Upload and optionally chunk vision document for product.
        
        Uses VisionDocumentChunker for intelligent chunking at semantic boundaries.
        Documents exceeding max_tokens are automatically split into chunks.
        
        Args:
            product_id: Product UUID
            content: Document content (text/markdown)
            filename: Document filename
            auto_chunk: Auto-chunk if content exceeds max_tokens (default: True)
            max_tokens: Max tokens per chunk (default: 25000 for 32K models)
        
        Returns:
            Dict with success status and document/chunk details
            {
                "success": bool,
                "document_id": str,
                "document_name": str,
                "chunks_created": int,
                "total_tokens": int,
                "error": str (if failed)
            }
        
        Raises:
            ValueError: If product not found or user lacks access
        
        Example:
            >>> result = await service.upload_vision_document(
            ...     product_id="abc-123",
            ...     content="# Vision\\n...",
            ...     filename="vision.md"
            ... )
            >>> print(f"Created {result['chunks_created']} chunks")
        """
        try:
            from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
            from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
            
            async with self.db_manager.get_session_async() as session:
                # Verify product exists and belongs to tenant
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                
                if not product:
                    return {
                        "success": False,
                        "error": f"Product {product_id} not found or access denied"
                    }
                
                # Create vision document via repository
                vision_repo = VisionDocumentRepository(db_manager=self.db_manager)
                
                # Calculate file size
                file_size = len(content.encode('utf-8'))
                
                # Create document (inline storage)
                doc = await vision_repo.create(
                    session=session,
                    tenant_key=self.tenant_key,
                    product_id=product_id,
                    document_name=filename,
                    content=content,
                    document_type="vision",
                    storage_type="inline",
                    file_size=file_size,
                    is_active=True,
                    display_order=0,
                )
                
                await session.commit()
                
                self._logger.info(
                    f"Created vision document {doc.id} for product {product_id}"
                )
                
                # Auto-chunk if enabled
                chunks_created = 0
                total_tokens = 0
                
                if auto_chunk:
                    chunker = VisionDocumentChunker(target_chunk_size=max_tokens)
                    
                    # Chunk the document
                    chunk_result = await chunker.chunk_vision_document(
                        session=session,
                        tenant_key=self.tenant_key,
                        vision_document_id=str(doc.id)
                    )
                    
                    await session.commit()
                    
                    if chunk_result["success"]:
                        chunks_created = chunk_result["chunks_created"]
                        total_tokens = chunk_result["total_tokens"]
                        
                        self._logger.info(
                            f"Chunked document {doc.id}: {chunks_created} chunks, "
                            f"{total_tokens} tokens"
                        )
                    else:
                        # Chunking failed but document created
                        self._logger.warning(
                            f"Document {doc.id} created but chunking failed: "
                            f"{chunk_result.get('error', 'Unknown error')}"
                        )
                
                return {
                    "success": True,
                    "document_id": str(doc.id),
                    "document_name": doc.document_name,
                    "chunks_created": chunks_created,
                    "total_tokens": total_tokens,
                }
                
        except ValueError as e:
            self._logger.error(f"Validation error uploading vision document: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            self._logger.exception(f"Failed to upload vision document: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Validation Methods
    # ============================================================================

    @staticmethod
    def validate_project_path(project_path: str) -> bool:
        """
        Validate project path for agent export functionality (Handover 0084).

        Args:
            project_path: File system path to validate

        Returns:
            True if valid, raises HTTPException if invalid

        Raises:
            HTTPException: If path is invalid, doesn't exist, isn't a directory, or isn't writable

        Example:
            >>> ProductService.validate_project_path("/path/to/project")
            True
        """
        from pathlib import Path

        from fastapi import HTTPException

        if not project_path:
            return True  # Optional field

        try:
            # Expand user home directory if present
            path = Path(project_path).expanduser()

            # Check if path exists and is a directory
            if not path.exists():
                raise HTTPException(status_code=400, detail=f"Project path does not exist: {path}")

            if not path.is_dir():
                raise HTTPException(status_code=400, detail=f"Project path is not a directory: {path}")

            # Check if path is writable (for .claude/agents creation)
            try:
                test_dir = path / ".claude_test_write"
                test_dir.mkdir(exist_ok=True)
                test_dir.rmdir()
            except (PermissionError, OSError):
                raise HTTPException(status_code=400, detail=f"Project path is not writable: {path}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid project path: {e}")

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _get_product_metrics(
        self,
        session: AsyncSession,
        product_id: str
    ) -> Dict[str, Any]:
        """
        Get metrics for a product (projects, tasks, vision documents).

        Args:
            session: Async database session
            product_id: Product UUID

        Returns:
            Dict with metric counts
        """
        # Count projects
        projects_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(
                    Project.product_id == product_id,
                    or_(Project.status != "deleted", Project.status.is_(None))
                )
            )
        )
        project_count = projects_result.scalar() or 0

        # Count unfinished projects
        unfinished_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(
                    Project.product_id == product_id,
                    Project.status.in_(["active", "inactive"])
                )
            )
        )
        unfinished_projects = unfinished_result.scalar() or 0

        # Count tasks
        tasks_result = await session.execute(
            select(func.count(Task.id)).where(Task.product_id == product_id)
        )
        task_count = tasks_result.scalar() or 0

        # Count unresolved tasks
        unresolved_result = await session.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.product_id == product_id,
                    Task.status.in_(["pending", "in_progress"])
                )
            )
        )
        unresolved_tasks = unresolved_result.scalar() or 0

        # Count vision documents
        # Note: VisionDocument doesn't support soft delete (no deleted_at field)
        vision_result = await session.execute(
            select(func.count(VisionDocument.id)).where(
                VisionDocument.product_id == product_id
            )
        )
        vision_documents_count = vision_result.scalar() or 0

        return {
            "project_count": project_count,
            "unfinished_projects": unfinished_projects,
            "task_count": task_count,
            "unresolved_tasks": unresolved_tasks,
            "vision_documents_count": vision_documents_count,
            "has_vision": vision_documents_count > 0,
        }
