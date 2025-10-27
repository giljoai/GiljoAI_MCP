# Handover 0043: Multi-Vision Document Support with Selective Re-Chunking

**Date**: 2025-10-23
**From Agent**: System Architect & Deep Researcher
**To Agent**: Full-Stack Development Team (Database Expert + TDD Implementor + Backend Integration Tester)
**Priority**: High
**Estimated Effort**: 3-4 hours (Dev mode - no migrations needed)
**Status**: Completed (Retired)
**Risk Level**: Medium (Database schema changes, orchestrator integration)

---

## Progress Updates

### 2025-10-25 — Project Retired and Archived
**Status:** Completed (Retired)
**Work Done:**
- Reviewed handover scope against current roadmap and active priorities.
- Determined this initiative is not required at this time; no code changes executed.
- Archived the handover per Handovers README and Handover Instructions (moved to completed/ with -C suffix).

**Final Notes:**
- If multi‑document vision becomes a priority later, this document remains a solid design reference (DB schema, repository layer, and integration plan are outlined).
- Orchestrator and MissionPlanner currently operate with single vision source; future activation would require MCPContextIndex linkage and repository wiring as described herein.


## Executive Summary

**Objective**: Enable products to have multiple vision documents with independent chunking, deletion, and selective re-chunking capabilities while maintaining orchestrator workflow compatibility.

**Current Problem**:
- Products can only have ONE vision document (single `vision_path` or `vision_document` field)
- Updating any vision content requires re-chunking the entire product
- No way to track which chunks came from which document
- Users cannot organize vision into separate documents (e.g., "Technical Requirements", "User Stories", "Architecture")
- Edit Product dialog doesn't show attached vision files or allow replacement

**Proposed Solution**:
- Create new `VisionDocument` table to track multiple documents per product
- Add `vision_document_id` to `MCPContextIndex` to link chunks to source documents
- Implement selective re-chunking (only re-chunk updated document, not all)
- Update orchestrator to aggregate content from multiple vision documents
- Add UI to manage multiple vision documents (upload, delete, replace)
- Maintain backward compatibility with existing single-document products

**Value Delivered**:
- Users can organize vision into logical documents
- Updating one document doesn't re-chunk others (huge performance win)
- Cascading deletes prevent orphaned chunks
- Orchestrator workflow continues working with enhanced context
- Production-ready architecture from day 1 (no technical debt)

**Why Dev Mode Makes This Simple**:
- No production users = no migration scripts needed
- Can drop/recreate tables with `install.py`
- Fresh database schema with proper relationships
- Fast iteration and testing

---

## Research Findings

### 1. Current Vision Document Architecture

**Product Model** (`src/giljo_mcp/models.py:78-83`):
```python
class Product(Base):
    vision_path = Column(String(500), nullable=True)      # File-based storage
    vision_document = Column(Text, nullable=True)         # Inline storage
    vision_type = Column(String(20), default="none")      # 'file', 'inline', 'none'
    chunked = Column(Boolean, default=False)              # Chunking status
```

**Chunking Storage** (`MCPContextIndex` table):
```python
class MCPContextIndex(Base):
    product_id = Column(String(36), nullable=False)  # Link to product
    chunk_content = Column(Text, nullable=False)
    keywords = Column(JSONB, default=list)
    chunk_order = Column(Integer, default=0)
    # MISSING: vision_document_id to track source document
```

**Current Limitations**:
- ❌ Only one vision document per product
- ❌ Chunks have no link to source document
- ❌ Updating requires full product re-chunk
- ❌ No CASCADE delete configured

### 2. Orchestrator Workflow Analysis

**Complete Flow**: Product → VisionChunks → Mission → Agents

**Key Components Using Vision Data**:

**A. ProjectOrchestrator.process_product_vision()** (`src/giljo_mcp/orchestrator.py:1043-1048`):
```python
if product.vision_type == "inline":
    vision_content = product.vision_document
elif product.vision_type == "file" and product.vision_path:
    vision_content = Path(product.vision_path).read_text(encoding="utf-8")
```
**Impact**: Must aggregate content from multiple VisionDocument records

**B. MissionPlanner.analyze_requirements()** (`src/giljo_mcp/mission_planner.py:374`):
```python
combined_text = f"{product.vision_document or ''} {project_description}"
```
**Impact**: Must fetch and combine all vision documents

**C. MissionPlanner.generate_missions()** (`src/giljo_mcp/mission_planner.py:544-548`):
```python
chunks = self.context_repo.search_chunks(
    session, product.tenant_key, product.id,
    query=" ".join(analysis.keywords[:3]),
    limit=10
)
```
**Impact**: Context repository already abstracts chunk retrieval - minimal changes needed

**D. Context Management System** (`src/giljo_mcp/context_management/`):
- Chunker creates chunks from vision content
- Loader retrieves chunks for agent context
- Indexer maintains searchable index

**Impact**: Must track which chunks belong to which vision document

### 3. Current Re-Chunking Workflow

**Trigger**: `/api/agent/products/{product_id}/vision` endpoint upload

**Process** (`api/endpoints/agent_management.py:91-120`):
```python
# Step 1: Delete ALL chunks for product
context_repo.delete_chunks_by_product(db, tenant_key, product_id)

# Step 2: Chunk new content
chunks = EnhancedChunker(max_tokens=20000).chunk(content)

# Step 3: Create new chunks in MCPContextIndex
for idx, chunk in enumerate(chunks):
    create_chunk_record(product_id, chunk, idx)

# Step 4: Update product flags
product.chunked = True
product.vision_type = "inline"
```

**Problem**: All-or-nothing approach - can't selectively re-chunk one document

### 4. File Storage Patterns

**Current Structure**:
```
./products/{product_id}/vision/
  └── vision_document.md  (single file)
```

**Proposed Structure**:
```
./products/{product_id}/vision/
  ├── technical_requirements.md
  ├── user_stories.md
  └── architecture_design.md
```

**Storage**: Files remain in same directory, just multiple files instead of one

---

## Implementation Plan

### Phase 1: Database Schema (1 hour)

**A. Create VisionDocument Model** (`src/giljo_mcp/models.py`):

```python
class VisionDocument(Base):
    """
    Vision Document model - supports multiple vision documents per product.

    Each product can have multiple vision documents (e.g., requirements,
    architecture, user stories) that are chunked and tracked independently.
    """

    __tablename__ = 'vision_documents'

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Multi-tenant isolation
    tenant_key = Column(String(36), nullable=False, index=True)

    # Foreign keys
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Product this vision document belongs to"
    )

    # Document identification
    document_name = Column(
        String(255),
        nullable=False,
        comment="User-friendly name (e.g., 'Technical Requirements', 'User Stories')"
    )

    document_type = Column(
        String(50),
        default='vision',
        comment="Document type: 'vision', 'requirements', 'architecture', 'technical', 'custom'"
    )

    # Document storage (hybrid approach - same as Product model)
    vision_path = Column(
        String(500),
        nullable=True,
        comment="File path to vision document (file-based workflow)"
    )

    vision_document = Column(
        Text,
        nullable=True,
        comment="Inline vision text (alternative to vision_path)"
    )

    storage_type = Column(
        String(20),
        default='inline',
        comment="Storage type: 'file', 'inline'"
    )

    # Chunking metadata
    chunked = Column(
        Boolean,
        default=False,
        comment="Has this document been chunked into mcp_context_index"
    )

    chunk_count = Column(
        Integer,
        default=0,
        comment="Number of chunks created from this document"
    )

    total_tokens = Column(
        Integer,
        default=0,
        comment="Total tokens across all chunks"
    )

    # Document metadata
    version = Column(
        String(20),
        default='1.0',
        comment="Document version for tracking changes"
    )

    content_hash = Column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of content for change detection"
    )

    # Status tracking
    is_active = Column(
        Boolean,
        default=True,
        comment="Is this document currently active"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    chunked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When document was last chunked"
    )

    # Display order
    display_order = Column(
        Integer,
        default=0,
        comment="Display order in UI (lower numbers first)"
    )

    # Additional metadata
    meta_data = Column(JSON, default=dict)

    # Relationships
    product = relationship("Product", back_populates="vision_documents")
    chunks = relationship(
        "MCPContextIndex",
        back_populates="vision_document",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Unique constraint: One document name per product
        UniqueConstraint(
            "product_id",
            "document_name",
            name="uq_vision_doc_product_name"
        ),

        # Indexes
        Index("idx_vision_doc_tenant", "tenant_key"),
        Index("idx_vision_doc_product", "product_id"),
        Index("idx_vision_doc_active", "is_active"),
        Index("idx_vision_doc_chunked", "chunked"),
        Index("idx_vision_doc_type", "document_type"),

        # Composite index for common queries
        Index(
            "idx_vision_doc_tenant_product_active",
            "tenant_key", "product_id", "is_active"
        ),

        # Constraints
        CheckConstraint(
            "storage_type IN ('file', 'inline')",
            name="ck_vision_doc_storage_type"
        ),
        CheckConstraint(
            "document_type IN ('vision', 'requirements', 'architecture', 'technical', 'custom')",
            name="ck_vision_doc_document_type"
        ),
        # Either vision_path OR vision_document must be set
        CheckConstraint(
            "(vision_path IS NOT NULL) OR (vision_document IS NOT NULL)",
            name="ck_vision_doc_has_content"
        ),
    )

    @property
    def needs_rechunking(self) -> bool:
        """Check if document needs to be re-chunked based on content hash"""
        if not self.chunked:
            return True

        # Calculate current content hash
        import hashlib
        content = self.vision_document or ""
        current_hash = hashlib.sha256(content.encode()).hexdigest()

        return current_hash != self.content_hash

    def update_content_hash(self) -> None:
        """Update content hash after chunking"""
        import hashlib
        content = self.vision_document or ""
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()
```

**B. Update MCPContextIndex Model**:

```python
class MCPContextIndex(Base):
    # ... existing fields ...

    # NEW FIELD: Link chunks to specific vision documents
    vision_document_id = Column(
        String(36),
        ForeignKey("vision_documents.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for backward compatibility
        comment="Vision document this chunk belongs to (NULL for legacy chunks)"
    )

    # Relationships
    product = relationship("Product", back_populates="context_chunks")
    vision_document = relationship("VisionDocument", back_populates="chunks")  # NEW

    __table_args__ = (
        # ... existing indexes ...

        # NEW INDEXES
        Index("idx_mcp_context_vision_doc", "vision_document_id"),
        Index("idx_mcp_context_product_vision_doc", "product_id", "vision_document_id"),
    )
```

**C. Update Product Model**:

```python
class Product(Base):
    # ... existing fields remain ...

    # DEPRECATED FIELDS (kept for backward compatibility during dev)
    vision_path = Column(
        String(500),
        nullable=True,
        comment="DEPRECATED: Use vision_documents relationship instead"
    )
    vision_document = Column(
        Text,
        nullable=True,
        comment="DEPRECATED: Use vision_documents relationship instead"
    )
    vision_type = Column(
        String(20),
        default="none",
        comment="DEPRECATED: Use vision_documents relationship instead"
    )
    chunked = Column(
        Boolean,
        default=False,
        comment="DEPRECATED: Use vision_documents relationship instead"
    )

    # NEW RELATIONSHIP
    vision_documents = relationship(
        "VisionDocument",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="VisionDocument.display_order"
    )

    # ... rest of existing code ...

    @property
    def has_vision_documents(self) -> bool:
        """Check if product has any vision documents"""
        return bool(self.vision_documents and len(self.vision_documents) > 0)

    @property
    def all_documents_chunked(self) -> bool:
        """Check if all active vision documents are chunked"""
        if not self.vision_documents:
            return False
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        return all(doc.chunked for doc in active_docs) if active_docs else False
```

**D. Drop and Recreate Schema** (Dev mode only):

```bash
# Since we're in dev mode with no users:
python install.py  # This will recreate all tables with new schema
```

### Phase 2: Repository Layer (45 minutes)

**A. Create VisionDocumentRepository** (`src/giljo_mcp/repositories/vision_document_repository.py`):

```python
"""Vision Document Repository - CRUD operations for vision documents"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timezone
import hashlib

from ..models import VisionDocument, Product, MCPContextIndex


class VisionDocumentRepository:
    """Repository for managing vision documents"""

    def create(
        self,
        session: Session,
        tenant_key: str,
        product_id: str,
        document_name: str,
        content: str,
        document_type: str = "vision",
        storage_type: str = "inline",
        file_path: Optional[str] = None
    ) -> VisionDocument:
        """Create a new vision document"""

        # Get current document count for display order
        existing_count = session.query(VisionDocument).filter(
            VisionDocument.product_id == product_id,
            VisionDocument.tenant_key == tenant_key
        ).count()

        # Create document
        doc = VisionDocument(
            tenant_key=tenant_key,
            product_id=product_id,
            document_name=document_name,
            vision_document=content if storage_type == "inline" else None,
            vision_path=file_path if storage_type == "file" else None,
            storage_type=storage_type,
            document_type=document_type,
            display_order=existing_count,
            is_active=True,
            chunked=False
        )

        session.add(doc)
        session.flush()

        return doc

    def get_by_id(
        self,
        session: Session,
        tenant_key: str,
        document_id: str
    ) -> Optional[VisionDocument]:
        """Get vision document by ID"""
        return session.query(VisionDocument).filter(
            VisionDocument.id == document_id,
            VisionDocument.tenant_key == tenant_key
        ).first()

    def list_by_product(
        self,
        session: Session,
        tenant_key: str,
        product_id: str,
        active_only: bool = True
    ) -> List[VisionDocument]:
        """List all vision documents for a product"""
        query = session.query(VisionDocument).filter(
            VisionDocument.product_id == product_id,
            VisionDocument.tenant_key == tenant_key
        )

        if active_only:
            query = query.filter(VisionDocument.is_active == True)

        return query.order_by(VisionDocument.display_order).all()

    def update_content(
        self,
        session: Session,
        tenant_key: str,
        document_id: str,
        new_content: str
    ) -> VisionDocument:
        """Update vision document content and mark for re-chunking"""
        doc = self.get_by_id(session, tenant_key, document_id)

        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Calculate new content hash
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        # Check if content actually changed
        if new_hash != doc.content_hash:
            doc.vision_document = new_content
            doc.updated_at = datetime.now(timezone.utc)
            doc.chunked = False  # Mark for re-chunking
            doc.chunk_count = 0
            doc.total_tokens = 0
            doc.chunked_at = None
            doc.content_hash = None

            session.flush()

        return doc

    def delete(
        self,
        session: Session,
        tenant_key: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Delete vision document and all associated chunks.

        Chunks are deleted automatically via CASCADE constraint.
        """
        doc = self.get_by_id(session, tenant_key, document_id)

        if not doc:
            return {"success": False, "message": "Document not found"}

        # Count chunks before deletion (for stats)
        chunk_count = session.query(MCPContextIndex).filter(
            MCPContextIndex.vision_document_id == document_id,
            MCPContextIndex.tenant_key == tenant_key
        ).count()

        document_name = doc.document_name

        # Delete document (chunks cascade automatically)
        session.delete(doc)
        session.flush()

        return {
            "success": True,
            "document_id": document_id,
            "document_name": document_name,
            "chunks_deleted": chunk_count
        }

    def mark_chunked(
        self,
        session: Session,
        document_id: str,
        chunk_count: int,
        total_tokens: int
    ) -> None:
        """Mark document as chunked with metadata"""
        doc = session.query(VisionDocument).filter(
            VisionDocument.id == document_id
        ).first()

        if doc:
            doc.chunked = True
            doc.chunk_count = chunk_count
            doc.total_tokens = total_tokens
            doc.chunked_at = datetime.now(timezone.utc)
            doc.update_content_hash()
            session.flush()
```

**B. Update ContextRepository** (`src/giljo_mcp/repositories/context_repository.py`):

Add method to delete chunks by vision document:

```python
def delete_chunks_by_vision_document(
    self,
    session: Session,
    tenant_key: str,
    vision_document_id: str
) -> int:
    """Delete all chunks for a specific vision document"""
    count = session.query(MCPContextIndex).filter(
        MCPContextIndex.tenant_key == tenant_key,
        MCPContextIndex.vision_document_id == vision_document_id
    ).count()

    session.query(MCPContextIndex).filter(
        MCPContextIndex.tenant_key == tenant_key,
        MCPContextIndex.vision_document_id == vision_document_id
    ).delete()

    return count
```

### Phase 3: Context Management System Updates (45 minutes)

**A. Update Chunker** (`src/giljo_mcp/context_management/chunker.py`):

Add method to chunk with vision document tracking:

```python
def chunk_vision_document(
    self,
    session: Session,
    tenant_key: str,
    vision_document_id: str
) -> Dict[str, Any]:
    """
    Chunk a specific vision document.

    Steps:
    1. Get vision document
    2. Delete existing chunks for this document
    3. Chunk content
    4. Create new chunks with vision_document_id link
    5. Update vision document metadata
    """
    from ..repositories.vision_document_repository import VisionDocumentRepository
    from ..repositories.context_repository import ContextRepository

    vision_repo = VisionDocumentRepository()
    context_repo = ContextRepository()

    # Get vision document
    doc = vision_repo.get_by_id(session, tenant_key, vision_document_id)
    if not doc:
        return {"success": False, "error": "Document not found"}

    # Get content
    content = doc.vision_document or ""
    if doc.storage_type == "file" and doc.vision_path:
        from pathlib import Path
        content = Path(doc.vision_path).read_text(encoding="utf-8")

    if not content:
        return {"success": False, "error": "Document has no content"}

    # Delete existing chunks for this document
    deleted_count = context_repo.delete_chunks_by_vision_document(
        session, tenant_key, vision_document_id
    )

    # Chunk content
    chunks = self.chunk(content)

    # Create chunk records with vision_document_id
    total_tokens = 0
    for idx, chunk_data in enumerate(chunks):
        chunk_record = MCPContextIndex(
            tenant_key=tenant_key,
            product_id=doc.product_id,
            vision_document_id=vision_document_id,  # NEW
            chunk_id=str(uuid.uuid4()),
            content=chunk_data["text"],
            keywords=chunk_data.get("keywords", []),
            token_count=chunk_data.get("token_count", 0),
            chunk_order=idx
        )
        session.add(chunk_record)
        total_tokens += chunk_data.get("token_count", 0)

    session.flush()

    # Update vision document metadata
    vision_repo.mark_chunked(
        session, vision_document_id, len(chunks), total_tokens
    )

    return {
        "success": True,
        "document_id": vision_document_id,
        "document_name": doc.document_name,
        "chunks_created": len(chunks),
        "total_tokens": total_tokens,
        "old_chunks_deleted": deleted_count
    }
```

### Phase 4: Orchestrator Integration (30 minutes)

**A. Update ProjectOrchestrator** (`src/giljo_mcp/orchestrator.py`):

Modify `process_product_vision()` to aggregate multiple documents:

```python
async def process_product_vision(
    self,
    session: Session,
    tenant_key: str,
    product_id: str
) -> Dict[str, Any]:
    """
    Process product vision documents (supports multiple documents).

    Aggregates content from all active vision documents and chunks them.
    """
    from .repositories.vision_document_repository import VisionDocumentRepository
    from .context_management.chunker import ContextManagementSystem

    vision_repo = VisionDocumentRepository()

    # Get product
    product = session.query(Product).filter(
        Product.id == product_id,
        Product.tenant_key == tenant_key
    ).first()

    if not product:
        raise ValueError(f"Product {product_id} not found")

    # Get all active vision documents
    vision_docs = vision_repo.list_by_product(
        session, tenant_key, product_id, active_only=True
    )

    if not vision_docs:
        # Fallback to legacy single vision for backward compatibility
        if product.vision_document or product.vision_path:
            return self._process_legacy_vision(session, product)
        raise ValueError(f"Product {product_id} has no vision documents")

    # Chunk each document independently
    cms = ContextManagementSystem(self.db_manager)
    results = []

    for doc in vision_docs:
        result = cms.chunk_vision_document(
            session, tenant_key, doc.id
        )
        results.append(result)

    # Return aggregated results
    total_chunks = sum(r.get("chunks_created", 0) for r in results)
    total_tokens = sum(r.get("total_tokens", 0) for r in results)

    return {
        "success": True,
        "product_id": product_id,
        "documents_processed": len(vision_docs),
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "results": results
    }
```

**B. Update MissionPlanner** (`src/giljo_mcp/mission_planner.py`):

Modify `analyze_requirements()` to fetch all vision documents:

```python
def analyze_requirements(
    self,
    session: Session,
    product: Product,
    project_description: str
) -> Dict[str, Any]:
    """Analyze requirements from multiple vision documents"""
    from .repositories.vision_document_repository import VisionDocumentRepository

    vision_repo = VisionDocumentRepository()

    # Get all active vision documents
    vision_docs = vision_repo.list_by_product(
        session, product.tenant_key, product.id, active_only=True
    )

    # Aggregate vision content
    vision_content = []
    for doc in vision_docs:
        content = doc.vision_document or ""
        vision_content.append(f"# {doc.document_name}\n\n{content}")

    combined_vision = "\n\n---\n\n".join(vision_content)

    # Combine with project description
    combined_text = f"{combined_vision}\n\n{project_description}"

    # Rest of analysis logic remains the same
    # ...
```

### Phase 5: API Endpoints (45 minutes)

**A. Create Vision Documents Endpoints** (`api/endpoints/vision_documents.py`):

```python
"""Vision Documents API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_tenant_key
from ..schemas import VisionDocumentResponse, VisionDocumentCreate, VisionDocumentUpdate
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.context_management.chunker import ContextManagementSystem

router = APIRouter(prefix="/vision-documents", tags=["Vision Documents"])

vision_repo = VisionDocumentRepository()


@router.post("/", response_model=VisionDocumentResponse)
async def create_vision_document(
    product_id: str = Form(...),
    document_name: str = Form(...),
    document_type: str = Form("vision"),
    content: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    auto_chunk: bool = Form(True),
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """Create a new vision document for a product"""

    # Validate product exists and belongs to tenant
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_key == tenant_key
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get content from file or form
    document_content = content
    storage_type = "inline"
    file_path = None

    if vision_file:
        from pathlib import Path
        import aiofiles

        # Save file
        storage_path = Path("./products") / product_id / "vision"
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / vision_file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            content_bytes = await vision_file.read()
            await f.write(content_bytes)

        document_content = content_bytes.decode('utf-8')
        storage_type = "file"

    if not document_content:
        raise HTTPException(status_code=400, detail="No content provided")

    # Create vision document
    doc = vision_repo.create(
        session=db,
        tenant_key=tenant_key,
        product_id=product_id,
        document_name=document_name,
        content=document_content,
        document_type=document_type,
        storage_type=storage_type,
        file_path=str(file_path) if file_path else None
    )

    # Optionally chunk immediately
    if auto_chunk:
        cms = ContextManagementSystem(db_manager)
        result = cms.chunk_vision_document(db, tenant_key, doc.id)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Chunking failed: {result.get('error')}")

    db.commit()

    return doc


@router.get("/product/{product_id}", response_model=List[VisionDocumentResponse])
async def list_vision_documents(
    product_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """List all vision documents for a product"""

    docs = vision_repo.list_by_product(
        session=db,
        tenant_key=tenant_key,
        product_id=product_id,
        active_only=active_only
    )

    return docs


@router.put("/{document_id}", response_model=VisionDocumentResponse)
async def update_vision_document(
    document_id: str,
    content: str = Form(...),
    auto_rechunk: bool = Form(True),
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """Update vision document content"""

    doc = vision_repo.update_content(
        session=db,
        tenant_key=tenant_key,
        document_id=document_id,
        new_content=content
    )

    # Optionally re-chunk
    if auto_rechunk:
        cms = ContextManagementSystem(db_manager)
        result = cms.chunk_vision_document(db, tenant_key, document_id)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Re-chunking failed: {result.get('error')}")

    db.commit()

    return doc


@router.delete("/{document_id}")
async def delete_vision_document(
    document_id: str,
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """Delete vision document and all associated chunks"""

    result = vision_repo.delete(
        session=db,
        tenant_key=tenant_key,
        document_id=document_id
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    db.commit()

    return result


@router.post("/{document_id}/rechunk")
async def rechunk_vision_document(
    document_id: str,
    db: Session = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    """Trigger re-chunking of a vision document"""

    cms = ContextManagementSystem(db_manager)
    result = cms.chunk_vision_document(db, tenant_key, document_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Chunking failed: {result.get('error')}")

    db.commit()

    return result
```

**B. Register Router** (`api/app.py`):

```python
from api.endpoints import vision_documents

app.include_router(vision_documents.router, prefix="/api")
```

### Phase 6: Frontend UI Updates (30 minutes)

**A. Update ProductSwitcher.vue** (Edit Product Dialog):

```vue
<!-- Add Vision Documents Section to Edit Dialog -->
<v-card-text>
  <!-- Existing fields: name, description -->

  <!-- Vision Documents Section -->
  <v-divider class="my-4"></v-divider>
  <div class="text-subtitle-1 mb-3">Vision Documents</div>

  <!-- List of existing vision documents -->
  <v-list v-if="visionDocuments.length > 0" density="compact">
    <v-list-item
      v-for="doc in visionDocuments"
      :key="doc.id"
      class="mb-2"
    >
      <template v-slot:prepend>
        <v-icon :color="doc.chunked ? 'success' : 'warning'">
          {{ doc.chunked ? 'mdi-check-circle' : 'mdi-clock-outline' }}
        </v-icon>
      </template>

      <v-list-item-title>{{ doc.document_name }}</v-list-item-title>
      <v-list-item-subtitle>
        {{ doc.chunk_count }} chunks • {{ formatDate(doc.created_at) }}
      </v-list-item-subtitle>

      <template v-slot:append>
        <v-btn
          icon
          size="small"
          variant="text"
          @click="deleteVisionDocument(doc.id)"
          color="error"
        >
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </template>
    </v-list-item>
  </v-list>

  <v-alert v-else type="info" variant="tonal" density="compact">
    No vision documents attached
  </v-alert>

  <!-- Upload new vision document -->
  <v-file-input
    v-model="newVisionFile"
    label="Upload additional vision document"
    accept=".txt,.md,.markdown"
    variant="outlined"
    density="comfortable"
    class="mt-3"
    @update:model-value="handleVisionFileUpload"
  />
</v-card-text>
```

**B. Add Script Methods**:

```javascript
const visionDocuments = ref([])
const newVisionFile = ref(null)

async function loadVisionDocuments(productId) {
  try {
    const response = await api.get(`/api/vision-documents/product/${productId}`)
    visionDocuments.value = response.data
  } catch (error) {
    console.error('Failed to load vision documents:', error)
  }
}

async function handleVisionFileUpload(files) {
  if (!files || files.length === 0) return

  const file = files[0]
  const formData = new FormData()
  formData.append('product_id', editProductData.value.id)
  formData.append('document_name', file.name)
  formData.append('vision_file', file)
  formData.append('auto_chunk', 'true')

  try {
    await api.post('/api/vision-documents/', formData)
    await loadVisionDocuments(editProductData.value.id)
    newVisionFile.value = null
  } catch (error) {
    console.error('Failed to upload vision document:', error)
  }
}

async function deleteVisionDocument(documentId) {
  if (!confirm('Delete this vision document and all its chunks?')) return

  try {
    await api.delete(`/api/vision-documents/${documentId}`)
    await loadVisionDocuments(editProductData.value.id)
  } catch (error) {
    console.error('Failed to delete vision document:', error)
  }
}
```

### Phase 7: Testing (30 minutes)

**A. Unit Tests** (`tests/test_vision_documents.py`):

```python
def test_create_vision_document():
    """Test creating a vision document"""
    doc = vision_repo.create(
        session=db,
        tenant_key="test-tenant",
        product_id="test-product",
        document_name="Technical Requirements",
        content="# Requirements\n\nUser auth, payment processing",
        document_type="requirements"
    )

    assert doc.id is not None
    assert doc.document_name == "Technical Requirements"
    assert doc.chunked == False


def test_selective_rechunking():
    """Test that updating one document doesn't affect others"""
    # Create two documents
    doc1 = create_vision_document("Doc 1", "Content 1")
    doc2 = create_vision_document("Doc 2", "Content 2")

    # Chunk both
    chunk_document(doc1.id)
    chunk_document(doc2.id)

    # Get chunk counts
    doc1_chunks = get_chunk_count(doc1.id)
    doc2_chunks = get_chunk_count(doc2.id)

    # Update doc1
    vision_repo.update_content(db, tenant_key, doc1.id, "New content 1")
    chunk_document(doc1.id)

    # Verify doc2 chunks unchanged
    assert get_chunk_count(doc2.id) == doc2_chunks
    assert get_chunk_count(doc1.id) != doc1_chunks


def test_cascade_delete():
    """Test that deleting document deletes chunks"""
    doc = create_vision_document("Test Doc", "Content")
    chunk_document(doc.id)

    chunk_count = get_chunk_count(doc.id)
    assert chunk_count > 0

    # Delete document
    vision_repo.delete(db, tenant_key, doc.id)

    # Verify chunks deleted
    assert get_chunk_count(doc.id) == 0
```

**B. Integration Tests** (`tests/test_orchestrator_multi_vision.py`):

```python
def test_orchestrator_with_multiple_visions():
    """Test orchestrator processes multiple vision documents"""
    # Create product with 3 vision documents
    product_id = create_test_product()
    create_vision_document(product_id, "Requirements", "...")
    create_vision_document(product_id, "Architecture", "...")
    create_vision_document(product_id, "User Stories", "...")

    # Process product vision
    result = orchestrator.process_product_vision(
        session=db,
        tenant_key=tenant_key,
        product_id=product_id
    )

    assert result["success"] == True
    assert result["documents_processed"] == 3
    assert result["total_chunks"] > 0


def test_mission_planner_aggregates_visions():
    """Test mission planner combines multiple vision documents"""
    product = get_test_product_with_visions()

    analysis = mission_planner.analyze_requirements(
        session=db,
        product=product,
        project_description="Build user dashboard"
    )

    # Verify all vision documents included in analysis
    assert "Requirements" in analysis["combined_text"]
    assert "Architecture" in analysis["combined_text"]
```

---

## Success Criteria

**Phase 1-3 (Backend)**:
- [ ] VisionDocument table created with all fields
- [ ] MCPContextIndex has vision_document_id with CASCADE
- [ ] Product model has vision_documents relationship
- [ ] VisionDocumentRepository has all CRUD methods
- [ ] ContextRepository can delete by vision_document_id
- [ ] Chunker tracks vision_document_id in chunks

**Phase 4 (Orchestrator)**:
- [ ] ProjectOrchestrator aggregates multiple vision documents
- [ ] MissionPlanner fetches all active vision documents
- [ ] Selective re-chunking works (only changed document)
- [ ] Backward compatibility maintained (legacy single vision)

**Phase 5 (API)**:
- [ ] POST /vision-documents/ creates document
- [ ] GET /vision-documents/product/{id} lists documents
- [ ] PUT /vision-documents/{id} updates content
- [ ] DELETE /vision-documents/{id} deletes with chunks
- [ ] POST /vision-documents/{id}/rechunk triggers re-chunking

**Phase 6 (Frontend)**:
- [ ] Edit Product dialog shows list of vision documents
- [ ] Can upload multiple vision documents
- [ ] Can delete individual documents
- [ ] Shows chunk status per document
- [ ] File upload works correctly

**Phase 7 (Testing)**:
- [ ] Unit tests pass (CRUD, chunking, cascade)
- [ ] Integration tests pass (orchestrator, mission planner)
- [ ] Manual testing validates full workflow

---

## Rollback Strategy

**If Issues Arise**:

1. **Database Schema Issues**:
   - Drop tables: `DROP TABLE vision_documents CASCADE;`
   - Recreate from backup or rerun `install.py`
   - In dev mode, no data loss concerns

2. **Orchestrator Breaks**:
   - Revert orchestrator changes
   - Add backward compatibility checks
   - Test with legacy single vision products

3. **API Errors**:
   - Revert API endpoint changes
   - Keep database schema (no harm)
   - Fix and redeploy

---

## Dependencies and Blockers

**Prerequisites**:
- ✅ PostgreSQL installed and running
- ✅ Product model exists
- ✅ MCPContextIndex table exists
- ✅ EnhancedChunker implemented
- ✅ Dev mode (no production users)

**Blockers**:
- None (dev mode makes this straightforward)

---

## Risk Assessment

**Technical Risks**: LOW
- Dev mode = can drop/recreate freely
- Backward compatibility maintained
- CASCADE prevents orphaned data

**Integration Risks**: MEDIUM
- Orchestrator must handle aggregation correctly
- Mission planner must combine documents properly
- Testing required to validate workflow

**Performance Risks**: LOW
- More chunks = more storage (minimal)
- Selective re-chunking = performance win
- Indexed queries = fast retrieval

---

## References

**Code Locations**:
- Database Models: `F:\GiljoAI_MCP\src\giljo_mcp\models.py`
- Orchestrator: `F:\GiljoAI_MCP\src\giljo_mcp\orchestrator.py`
- Mission Planner: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`
- Context Management: `F:\GiljoAI_MCP\src\giljo_mcp\context_management\`
- Product API: `F:\GiljoAI_MCP\api\endpoints\products.py`
- Frontend: `F:\GiljoAI_MCP\frontend\src\components\ProductSwitcher.vue`

**Related Handovers**:
- 0017: Database Schema Enhancement (foundation)
- 0018: Context Management System (chunking infrastructure)
- 0020: Orchestrator Enhancement (mission generation)
- 0042: Product Rich Context Fields UI (complementary)

**Documentation**:
- `/docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Multi-tenant architecture
- `/docs/vision/AGENTIC_WORKFLOW_VISION.md` - Orchestrator workflow
- `/CLAUDE.md` - Development guidelines

---

## Notes

**Why This Is Simple in Dev Mode**:
1. No migration scripts needed
2. No backward compatibility concerns for data
3. Can drop/recreate tables freely
4. Fast iteration and testing
5. Production-ready architecture from day 1

**When Real Users Come**:
- This architecture is already production-ready
- Proper foreign keys with CASCADE
- Multi-tenant isolation enforced
- Indexed for performance
- No technical debt

**Key Design Decisions**:
- CASCADE delete prevents orphaned chunks
- Content hashing detects changes
- display_order supports UI sorting
- storage_type supports both file and inline
- is_active enables soft deletion

---

## Acceptance Criteria

**Definition of Done**:
1. All database models implemented and tables created
2. All repository methods implemented with tests
3. Orchestrator successfully processes multiple vision documents
4. API endpoints functional and tested
5. Frontend UI allows managing multiple documents
6. All tests passing (unit + integration)
7. Manual testing validates end-to-end workflow
8. Documentation updated

**Ready for Production**:
- Multi-tenant isolation verified
- CASCADE deletes working
- Performance tested with 10+ documents
- Orchestrator workflow validated
- No breaking changes to existing code

---

**Last Updated**: 2025-10-23
**Next Handover**: TBD (after implementation complete)
<!-- Archived on 2025-10-25 -->
