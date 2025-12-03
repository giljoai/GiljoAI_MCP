---
**Document Type:** Handover
**Handover ID:** 0500
**Title:** ProductService Enhancement - Vision Upload & Config Data
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 4 hours
**Scope:** Implement vision upload with chunking, fix config_data persistence
**Priority:** 🔴 P0 CRITICAL
**Tool:** 🖥️ CLI
**Parallel Execution:** ❌ No (Foundation for Phase 1)
**Parent Project:** Projectplan_500.md
---

# Handover 0500: ProductService Enhancement - Vision Upload & Config Data

## 🎯 Mission Statement
Implement production-grade vision document upload with intelligent chunking (<25K tokens per chunk) and fix config_data field persistence in ProductService. This is the foundation for all product-related functionality.

## 📋 Prerequisites
**Must be complete before starting:**
- Git checkout to clean working tree
- PostgreSQL running on localhost:5432
- Python virtual environment activated
- Pytest passing for existing ProductService tests

## ⚠️ Problem Statement

### Issue 1: Vision Upload Returns HTTP 501
**Evidence**: productfixes_session.md lines 267-273
- Endpoint stub created during Handover 0126 but never implemented
- Users cannot upload vision documents
- Feature critical for context prioritization and orchestration (mission condensation)

**Root Cause**: "Modularize first, implement later" approach left stub endpoint:
```python
# Current state: api/endpoints/products/vision.py (MISSING or stubbed)
@router.post("/{product_id}/vision")
async def upload_vision(product_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented")
```

### Issue 2: config_data Field Silently Lost
**Evidence**: Projectplan_500.md lines 31
- ProductCreate/ProductUpdate models missing config_data field
- Users' product configurations lost on create/update
- No validation error - data silently dropped

**Root Cause**: Pydantic models don't include config_data field:
```python
# src/giljo_mcp/models/schemas/product_schemas.py
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_path: Optional[str] = None
    # config_data: MISSING!
```

### Issue 3: Dual Vision Upload Endpoints
**Evidence**: Projectplan_500.md line 36
- 3 different vision upload implementations exist
- Inconsistent behavior across endpoints
- Need to consolidate to single authoritative implementation

## ✅ Solution Approach

### 1. Vision Upload with Intelligent Chunking
Follow established pattern from `src/giljo_mcp/mission_planner.py` (lines 150-200):
- Use `tiktoken` for accurate token counting (cl100k_base encoding)
- Chunk documents at 25,000 tokens (safe margin below 32K limit)
- Preserve document structure (split on headings/paragraphs)
- Store chunks as separate VisionDocument records with sequence numbers

### 2. Add config_data to Product Models
Update Pydantic schemas to include JSONB field:
```python
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_path: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None  # Add this

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_path: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None  # Add this
```

### 3. Consolidate Vision Upload Endpoints
Single authoritative implementation in `api/endpoints/products/vision.py`:
- POST `/api/v1/products/{product_id}/vision` - Upload vision document
- GET `/api/v1/products/{product_id}/vision` - List vision documents
- DELETE `/api/v1/products/{product_id}/vision/{doc_id}` - Delete vision document

## 📝 Implementation Tasks

### Task 1: Add config_data to Product Schemas (30 min)
**File**: `src/giljo_mcp/models/schemas/product_schemas.py`
- [ ] Add `config_data: Optional[Dict[str, Any]]` to ProductCreate
- [ ] Add `config_data: Optional[Dict[str, Any]]` to ProductUpdate
- [ ] Add `config_data: Optional[Dict[str, Any]]` to ProductResponse
- [ ] Import `Dict, Any` from typing

### Task 2: Implement Vision Chunking Utility (60 min)
**File**: `src/giljo_mcp/services/vision_chunker.py` (NEW)
- [ ] Create `VisionChunker` class
- [ ] Implement `chunk_document(content: str, max_tokens: int = 25000) -> List[str]`
- [ ] Use tiktoken cl100k_base encoding (same as GPT-4)
- [ ] Split on markdown headers (##, ###) first, then paragraphs
- [ ] Ensure chunks don't exceed max_tokens
- [ ] Add docstrings with examples

**Example Implementation**:
```python
import tiktoken
from typing import List

class VisionChunker:
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoder = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def chunk_document(self, content: str, max_tokens: int = 25000) -> List[str]:
        """Split document into chunks under max_tokens."""
        # Implementation follows mission_planner.py pattern
        pass
```

### Task 3: Update ProductService - Vision Upload (90 min)
**File**: `src/giljo_mcp/services/product_service.py`
- [ ] Add `upload_vision_document()` method (async)
- [ ] Parameters: `product_id: str, content: str, filename: str`
- [ ] Use VisionChunker to split content
- [ ] Create VisionDocument records with sequence numbers
- [ ] Handle duplicate filename constraint (append version suffix)
- [ ] Add error handling with specific exceptions
- [ ] Update eager loading to include vision_documents (already done line 172)

**Method Signature**:
```python
async def upload_vision_document(
    self,
    product_id: str,
    content: str,
    filename: str,
) -> List[VisionDocument]:
    """Upload and chunk vision document."""
    pass
```

### Task 4: Update ProductService - config_data (20 min)
**File**: `src/giljo_mcp/services/product_service.py`
- [ ] Update `create_product()` method - add config_data to SQL insert (line ~120)
- [ ] Update `update_product()` method - add config_data to SQL update (line ~145)
- [ ] Update `_to_response()` method - include config_data in response (line ~185)

### Task 5: Create Vision Upload Endpoint (45 min)
**File**: `api/endpoints/products/vision.py` (check if exists, create if not)
- [ ] Create FastAPI router
- [ ] POST endpoint: upload_vision_document
- [ ] Accept multipart/form-data (file upload)
- [ ] Validate file size (<10MB recommended)
- [ ] Validate file type (markdown, text)
- [ ] Call ProductService.upload_vision_document()
- [ ] Return VisionDocumentResponse list

### Task 6: Unit Tests (45 min)
**File**: `tests/services/test_product_service.py`
- [ ] Test config_data create - verify persisted to DB
- [ ] Test config_data update - verify updated correctly
- [ ] Test config_data in response - verify serialized correctly
- [ ] Test vision chunking - document >25K tokens split correctly
- [ ] Test vision upload - chunks stored with sequence numbers
- [ ] Test duplicate filename handling - version suffix added

## 🧪 Testing Strategy

### Unit Tests
```python
# Test config_data persistence
async def test_product_config_data_create():
    config = {"api_key": "test", "settings": {"debug": True}}
    product = await service.create_product(
        name="Test",
        config_data=config
    )
    assert product.config_data == config

# Test vision chunking
async def test_vision_document_chunking():
    large_doc = "# Header\n" + ("Word " * 10000)  # >25K tokens
    chunks = await service.upload_vision_document(
        product_id=product.id,
        content=large_doc,
        filename="vision.md"
    )
    assert len(chunks) > 1  # Should be chunked
    for chunk in chunks:
        assert count_tokens(chunk.content) <= 25000
```

### Integration Tests
- [ ] Create product with config_data via API
- [ ] Upload 50KB vision document, verify chunked
- [ ] Fetch product, verify config_data present
- [ ] Update product config_data, verify persisted

### Manual Validation
- [ ] Use Postman/curl to POST vision document
- [ ] Check database: `SELECT * FROM vision_documents WHERE product_id = 'xxx';`
- [ ] Verify chunks: `SELECT COUNT(*), SUM(LENGTH(content)) FROM vision_documents WHERE product_id = 'xxx';`

## ✅ Success Criteria
- [ ] ProductCreate/ProductUpdate include config_data field
- [ ] config_data persists to database correctly
- [ ] Vision upload endpoint returns 200 (not 501)
- [ ] Documents >25K tokens split into chunks
- [ ] Each chunk <25K tokens
- [ ] Chunks stored with sequence numbers (0, 1, 2...)
- [ ] Vision documents queryable via GET endpoint
- [ ] All unit tests pass (>80% coverage)
- [ ] No HTTP 501 errors for vision upload

## 🔄 Rollback Plan
1. Revert migrations: `git checkout HEAD~1 -- alembic/versions/`
2. Revert service changes: `git checkout HEAD~1 -- src/giljo_mcp/services/product_service.py`
3. Revert schemas: `git checkout HEAD~1 -- src/giljo_mcp/models/schemas/product_schemas.py`
4. Drop vision_chunker.py: `git rm src/giljo_mcp/services/vision_chunker.py`

## 📚 Related Handovers
**Depends on**: None (foundation handover)
**Blocks**:
- 0503 (Product Endpoints) - needs vision upload method
- 0508 (Vision Upload Error Handling) - needs base implementation

**Related**:
- Handover 0126 (Products Modularization) - created the structure
- productfixes_session.md - identified the regressions

## 🛠️ Tool Justification
**Why CLI (Local)**:
- Database schema changes required (vision_documents table already exists)
- Service layer changes need pytest with DB fixtures
- Token counting with tiktoken requires local testing
- Integration tests require live PostgreSQL connection

## 📊 Parallel Execution
**Cannot run in parallel** - This is Phase 0 foundation work. Phase 1 (Endpoints) depends on these service methods being implemented first.

---
**Status:** Ready for Execution
**Estimated Effort:** 4 hours
**Archive Location:** `handovers/completed/0500_productservice_enhancement-COMPLETE.md`
