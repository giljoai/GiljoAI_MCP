# Handover 0047: Vision Document Chunking Async/Sync Architecture Fix

**Date**: 2025-10-26
**From Agent**: Deep Researcher + System Architect
**To Agent**: Backend Integration Specialist + TDD Implementor
**Priority**: Critical (Phase 1 - Must Complete First)
**Estimated Effort**: 3-4 hours
**Status**: ✅ **COMPLETE - PRODUCTION-READY**
**Actual Effort**: 4 hours (as estimated)
**Risk Level**: ~~High~~ → **RESOLVED** (Core functionality now operational)
**Blocks**: ~~Handover 0042~~ → **NOW UNBLOCKED** (Product Rich Context Fields UI)

---

## 🎉 COMPLETION REPORT

**Completed**: 2025-10-26
**Status**: ✅ MERGED TO MASTER - PRODUCTION-READY
**Total Commits**: 10 (7 async fix + 3 file size bonus feature)
**Test Coverage**: 5/5 unit tests passing, 0 async warnings
**Documentation**: Complete (COMPLETION_SUMMARY.md, IMPLEMENTATION_COMPLETE.md, TESTING_GUIDE.md)

**Deliverables**:
1. ✅ Vision document chunking fully async (API → Chunker → Repositories → Database)
2. ✅ Product deletion working (CASCADE on 4 FK constraints + await db.delete())
3. ✅ Vision document file size tracking and display (bonus feature)
4. ✅ Aggregate stats in product details (Total chunks, total file sizes)
5. ✅ Cross-platform path compatibility maintained
6. ✅ Production-grade error handling

**See**: [Completion Summary](0047/COMPLETION_SUMMARY.md) | [Devlog Entry](../docs/devlog/2025-10-26_handover_0047_vision_chunking_complete.md)

---

## ✅ IMPLEMENTATION COMPLETE

**Completion Date**: 2025-10-26
**Implementation Time**: 4 hours (as estimated)
**Test Results**: 5/5 unit tests passing, 0 async warnings
**Code Quality**: Production-grade, comprehensive documentation

**Key Achievements**:
- ✅ Full async propagation (API → Chunker → Repositories → Database)
- ✅ All async methods properly awaited (zero coroutine warnings)
- ✅ Fail-fast error handling with transaction rollback
- ✅ Cross-platform path compatibility maintained
- ✅ Comprehensive test suite (5 unit tests + 4 integration tests)
- ✅ Production-ready documentation

**Implementation Details**: See `handovers/0047/IMPLEMENTATION_COMPLETE.md`

**Git Commits** (Async Fix - 7 commits):
- `fc695b7` - test: Add comprehensive tests for async vision document chunking
- `18f6af7` - feat: Convert vision document chunking to async
- `ae8a577` - feat: Update API endpoints to use async vision document chunking
- `1d67093` - docs: Add comprehensive implementation summary for Handover 0047
- `a3242bd` - test: Fix async test mocking and add comprehensive integration tests
- `c010001` - docs: Update Handover 0047 status to Complete
- `f6d0d48` - docs: Add comprehensive testing guide for Handover 0047

**Git Commits** (Product Deletion Fixes - 3 commits):
- `2146a95` - fix: Add await to db.delete() and CASCADE to mcp_context_summary
- `72b8a47` - fix: Add CASCADE to product foreign keys for proper deletion
- `a1443b3` - Fixing product delete

**Git Commits** (File Size Bonus Feature - 3 commits):
- `faaa8f9` - test: Add comprehensive tests for vision document file size tracking
- `9ccd16d` - feat: Implement vision document file size tracking and display
- `c731bef` - fix: Update file size tracking tests to use correct test fixtures

**Status**: Production-ready, Handover 0042 unblocked

---

## ⚠️ CRITICAL PATH: This Unblocks 0042

**This handover is PHASE 1 of the Product Context Management System.**

**BLOCKS HANDOVER 0042**: Product Rich Context Fields UI
- Handover 0042 adds rich metadata (tech_stack, architecture, features)
- Those fields COMPLEMENT vision document chunks
- But vision chunking is currently 100% broken
- **Must fix chunking first** → Then 0042 adds the metadata layer

**COMPLETE PRODUCT CONTEXT SYSTEM**:
```
Phase 1 (0047): Fix Vision Chunking ← YOU ARE HERE
  └─ Chunks work → Agents get vision content ✅

Phase 2 (0042): Add Rich Metadata Fields
  └─ Config fields work → Agents get metadata + vision ✅✅
```

---

## Executive Summary

**Objective**: Fix critical async/sync architecture mismatch preventing vision document chunking from working. Make chunking async-first with proper error handling and testing.

**Current Problem**:
- Vision documents upload successfully but **never get chunked** (0 chunks, 0 B displayed)
- `chunk_vision_document()` is **synchronous** but calls **async repository methods** without await
- Errors fail silently, no user feedback
- Cross-platform path handling broken (Windows backslashes cause escape sequence corruption)

**Root Causes Identified**:
1. **Async/Sync Mismatch**: `VisionDocumentChunker.chunk_vision_document()` is sync, but:
   - `VisionDocumentRepository.get_by_id()` is async (requires await)
   - `ContextRepository` methods may be async
   - Called from async endpoint with AsyncSession
2. **Path Storage Bug**: Windows backslashes (`\vision`) stored in DB cause Python to interpret `\v` as vertical tab (`\x0b`), corrupting file paths
3. **Silent Failures**: Errors caught but not logged properly or surfaced to user

**Proposed Solution**:
- Make `chunk_vision_document()` fully async
- Update all callers to use await
- Fix path storage to use forward slashes (OS-neutral)
- Add proper error handling and logging
- Add comprehensive tests
- Production-grade implementation

**Value Delivered**:
- ✅ Vision document chunking actually works
- ✅ Cross-platform path compatibility
- ✅ Proper error feedback to users
- ✅ Async-first architecture (scalable)
- ✅ Comprehensive test coverage
- ✅ Production-ready from day 1

---

## Research Findings

### 1. Bug Discovery Timeline

**Initial Symptom**:
```
User: "I uploaded TinyContacts vision document, shows 0 chunks, 0 B"
```

**Investigation Path**:
1. ✅ File uploaded successfully (4.8KB exists on disk)
2. ✅ Database record created (`vision_documents` table)
3. ❌ `chunked = false`, `chunk_count = 0`
4. ❌ No chunks in `mcp_context_index` table
5. ❌ `auto_chunk=true` sent by frontend, but chunking failed silently

**Root Cause 1 - Path Bug**:
```python
# Database stores (Windows):
vision_path = "products\8812f58f-b76a-439d-924b-31f5e05b8b8f\vision\TinyContactsProduct.md"

# Python interprets \v as vertical tab:
"\v" → "\x0b" (escape sequence)

# Path becomes corrupted:
"products\8812f58f-b76a-439d-924b-31f5e05b8b8fision\TinyContactsProduct.md"
#                                       ↑ "vision" became "ision"!

# File not found → Chunking fails
```

**Root Cause 2 - Async/Sync Mismatch**:
```python
# chunker.py:242-296 (SYNC function)
def chunk_vision_document(self, session, tenant_key, vision_document_id):
    vision_repo = VisionDocumentRepository()

    # ❌ BROKEN: Calling async method without await in sync function
    doc = vision_repo.get_by_id(session, tenant_key, vision_document_id)
    # Returns coroutine object, never actually executes!

# vision_document_repository.py:121 (ASYNC method)
async def get_by_id(self, session: AsyncSession, tenant_key, document_id):
    # Expects AsyncSession, uses await internally
```

**Why It Fails Silently**:
```python
# vision_documents.py:194-207
if auto_chunk:
    try:
        cms = ContextManagementSystem(vision_repo.db)
        result = cms.chunk_vision_document(db, tenant_key, doc.id)

        if not result.get("success"):
            logger.warning(f"Chunking failed: {result.get('error')}")
            # ❌ Doesn't fail the request!
    except Exception as chunk_error:
        logger.error(f"Chunking error: {chunk_error}")
        # ❌ Swallows exception, continues!
```

### 2. Current Architecture Analysis

**File**: `src/giljo_mcp/context_management/chunker.py`

**VisionDocumentChunker Class**:
- **Lines 42-56**: `__init__()` - Initializes EnhancedChunker
- **Lines 167-240**: `chunk_document()` - SYNC, works fine (pure chunking logic)
- **Lines 242-396**: `chunk_vision_document()` - **BROKEN** (sync calling async)

**Key Dependencies**:
```python
VisionDocumentRepository (ASYNC):
  - get_by_id() → async
  - create() → async
  - update_content() → async
  - mark_chunked() → ?

ContextRepository (MIXED):
  - delete_chunks_by_vision_document() → ?
  - create_chunk() → ?

MCPContextIndex (Model):
  - SQLAlchemy model
```

**Call Chain**:
```
User uploads file
  ↓
POST /api/vision-documents/ (ASYNC endpoint)
  ↓
vision_repo.create() (ASYNC) → Creates DB record
  ↓
auto_chunk=true → cms.chunk_vision_document() (SYNC!) ❌
  ↓
vision_repo.get_by_id() (ASYNC) → Called without await ❌
  ↓
Returns coroutine, never executes → No chunks created
  ↓
User sees: 0 chunks, 0 B
```

### 3. Path Storage Analysis

**Current Implementation** (`vision_documents.py:161`):
```python
file_path = storage_path / vision_file.filename  # WindowsPath or PosixPath
# ...
file_path=str(file_path) if file_path else None  # Converts to string

# On Windows: "products\8812...\vision\file.md" (backslashes)
# On Linux:   "products/8812.../vision/file.md" (forward slashes)
```

**Why Backslashes Break**:
```python
# String literal with backslashes
path = "products\vision\file.md"

# Python escape sequences:
# \v → vertical tab (0x0B)
# \t → tab
# \n → newline
# \r → carriage return
# etc.

# Path becomes:
"products<vertical-tab>ision\file.md"
```

**Solution - Forward Slashes**:
```python
# Forward slashes work on ALL platforms
normalized = str(file_path).replace('\\', '/')
# "products/vision/file.md"

# Path() handles forward slashes correctly everywhere:
Path("products/vision/file.md")  # Works on Windows, Linux, macOS
```

### 4. Database Schema

**vision_documents** table:
```sql
CREATE TABLE vision_documents (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) REFERENCES products(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    vision_path VARCHAR(500),          -- FILE PATHS STORED HERE
    vision_document TEXT,               -- Inline content
    storage_type VARCHAR(20) NOT NULL, -- 'file', 'inline', 'hybrid'
    chunked BOOLEAN NOT NULL DEFAULT false,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER,
    -- ... other fields
);
```

**mcp_context_index** table (chunks):
```sql
CREATE TABLE mcp_context_index (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(36) UNIQUE,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36),
    vision_document_id VARCHAR(36) REFERENCES vision_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    keywords JSONB,
    token_count INTEGER,
    chunk_order INTEGER,
    -- ... other fields
);
```

### 5. Partial Fixes Already Applied

**Fix 1 - Path Storage** (✅ COMPLETED):
```python
# File: api/endpoints/vision_documents.py:176-177
# BEFORE:
file_path=str(file_path) if file_path else None

# AFTER:
normalized_path = str(file_path).replace('\\', '/') if file_path else None
file_path=normalized_path
```

**Fix 2 - Path Reading** (✅ COMPLETED):
```python
# File: src/giljo_mcp/context_management/chunker.py:306-309
# BEFORE:
file_path = Path(doc.vision_path)

# AFTER:
normalized_path = doc.vision_path.replace('\\', '/')
file_path = Path(normalized_path)
```

**Status**: Path fixes complete, but **chunking still doesn't work** due to async/sync mismatch.

---

## Implementation Plan

### Phase 1: Make Chunker Fully Async (2 hours)

**A. Update VisionDocumentChunker.chunk_vision_document()** (`chunker.py:242-396`):

**Current Signature**:
```python
def chunk_vision_document(
    self,
    session,
    tenant_key: str,
    vision_document_id: str
) -> Dict[str, Any]:
```

**New Signature**:
```python
async def chunk_vision_document(
    self,
    session: AsyncSession,
    tenant_key: str,
    vision_document_id: str
) -> Dict[str, Any]:
```

**Changes Required**:
1. Add `async` keyword to function definition
2. Update all repository calls to use `await`:
   ```python
   # BEFORE:
   doc = vision_repo.get_by_id(session, tenant_key, vision_document_id)

   # AFTER:
   doc = await vision_repo.get_by_id(session, tenant_key, vision_document_id)
   ```
3. Check `ContextRepository` methods - make async if needed:
   ```python
   # Check these methods:
   deleted_count = context_repo.delete_chunks_by_vision_document(...)
   context_repo.create_chunk(...)
   vision_repo.mark_chunked(...)
   ```
4. Update session operations:
   ```python
   # BEFORE:
   session.add(chunk_record)
   session.flush()

   # AFTER:
   session.add(chunk_record)
   await session.flush()
   ```

**B. Update ContextRepository** (if needed):

Check `src/giljo_mcp/repositories/context_repository.py`:
- Make `delete_chunks_by_vision_document()` async if using await internally
- Make `create_chunk()` async if needed
- Ensure all database operations use `await`

**C. Update ContextManagementSystem** (`context_management/manager.py`):

Find if `ContextManagementSystem` has a `chunk_vision_document` wrapper:
- Make it async
- Pass through to `VisionDocumentChunker.chunk_vision_document()`

### Phase 2: Update All Callers (1 hour)

**A. Update vision_documents.py Endpoint** (`api/endpoints/vision_documents.py:194-207`):

**BEFORE**:
```python
if auto_chunk:
    try:
        from src.giljo_mcp.context_management.chunker import ContextManagementSystem

        cms = ContextManagementSystem(vision_repo.db)
        result = cms.chunk_vision_document(db, tenant_key, doc.id)

        if not result.get("success"):
            logger.warning(f"Chunking failed for document {doc.id}: {result.get('error')}")
```

**AFTER**:
```python
if auto_chunk:
    try:
        from src.giljo_mcp.context_management.chunker import ContextManagementSystem

        cms = ContextManagementSystem(vision_repo.db)
        result = await cms.chunk_vision_document(db, tenant_key, doc.id)

        if not result.get("success"):
            logger.error(f"Chunking failed for document {doc.id}: {result.get('error')}")
            # Consider raising exception or returning error to user
```

**B. Find All Other Callers**:

Search codebase for calls to `chunk_vision_document()`:
```bash
grep -r "chunk_vision_document" --include="*.py" src/ api/
```

Update each caller to use `await`.

**C. Update rechunk Endpoint** (`vision_documents.py:408-425`):

Ensure rechunk endpoint also uses `await`:
```python
@router.post("/{document_id}/rechunk", response_model=RechunkResponse)
async def rechunk_vision_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo)
):
    try:
        from src.giljo_mcp.context_management.chunker import ContextManagementSystem

        cms = ContextManagementSystem(vision_repo.db)
        result = await cms.chunk_vision_document(db, tenant_key, document_id)  # ADD await

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Chunking failed: {result.get('error')}"
            )

        await db.commit()

        return RechunkResponse(**result)
```

### Phase 3: Improve Error Handling (30 minutes)

**A. Surface Errors to User**:

Instead of silent failures, return meaningful errors:

```python
# vision_documents.py create endpoint
if auto_chunk:
    try:
        cms = ContextManagementSystem(vision_repo.db)
        result = await cms.chunk_vision_document(db, tenant_key, doc.id)

        if not result.get("success"):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Chunking failed for document {doc.id}: {error_msg}")

            # OPTION 1: Fail the request
            raise HTTPException(
                status_code=500,
                detail=f"Document uploaded but chunking failed: {error_msg}"
            )

            # OPTION 2: Return warning in response
            # (Let document be created, user can retry chunking later)
    except Exception as chunk_error:
        logger.error(f"Chunking error for document {doc.id}: {chunk_error}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chunking failed: {str(chunk_error)}"
        )
```

**B. Add Detailed Logging**:

```python
# chunker.py - Add logging at key points
logger.info(f"Starting chunking for document {vision_document_id}")
logger.debug(f"Document path: {normalized_path}")
logger.debug(f"File exists: {file_path.exists()}")
logger.info(f"Created {len(chunks)} chunks, {total_tokens} tokens")
```

### Phase 4: Testing (1 hour)

**A. Unit Tests** (`tests/unit/test_vision_chunker.py`):

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

@pytest.mark.asyncio
async def test_chunk_vision_document_success():
    """Test successful chunking of vision document"""
    chunker = VisionDocumentChunker()

    # Mock session and repositories
    mock_session = AsyncMock()
    mock_vision_repo = AsyncMock()

    # Mock vision document
    mock_doc = MagicMock()
    mock_doc.storage_type = "file"
    mock_doc.vision_path = "products/test-product/vision/test.md"
    mock_doc.product_id = "test-product-id"
    mock_doc.document_name = "Test Document"

    # Mock file exists and content
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.read_text', return_value="Test vision content"):
            result = await chunker.chunk_vision_document(
                mock_session, "test-tenant", "test-doc-id"
            )

    assert result["success"] == True
    assert result["chunks_created"] >= 1
    assert result["total_tokens"] > 0

@pytest.mark.asyncio
async def test_chunk_vision_document_file_not_found():
    """Test chunking fails gracefully when file not found"""
    chunker = VisionDocumentChunker()

    # Mock document with invalid path
    mock_doc = MagicMock()
    mock_doc.storage_type = "file"
    mock_doc.vision_path = "products/nonexistent/vision/file.md"

    with patch('pathlib.Path.exists', return_value=False):
        result = await chunker.chunk_vision_document(
            mock_session, "test-tenant", "test-doc-id"
        )

    assert result["success"] == False
    assert "not found" in result["error"].lower()

@pytest.mark.asyncio
async def test_chunk_vision_document_path_normalization():
    """Test that backslash paths are normalized to forward slashes"""
    chunker = VisionDocumentChunker()

    # Mock document with backslash path (Windows)
    mock_doc = MagicMock()
    mock_doc.storage_type = "file"
    mock_doc.vision_path = r"products\test\vision\file.md"  # Backslashes

    # Path should be normalized and file found
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.read_text', return_value="Content"):
            result = await chunker.chunk_vision_document(
                mock_session, "test-tenant", "test-doc-id"
            )

    assert result["success"] == True
```

**B. Integration Tests** (`tests/integration/test_vision_upload_chunking.py`):

```python
@pytest.mark.asyncio
async def test_vision_document_upload_and_chunk_integration(db_session, test_product):
    """Test complete upload and chunking flow"""

    # Create test file
    test_file = Path("test_vision.md")
    test_file.write_text("# Test Vision\n\nThis is a test vision document.")

    try:
        # Upload via API
        with open(test_file, 'rb') as f:
            files = {'vision_file': f}
            data = {
                'product_id': test_product.id,
                'document_name': 'Test Vision',
                'document_type': 'vision',
                'auto_chunk': 'true'
            }

            response = await client.post(
                "/api/vision-documents/",
                data=data,
                files=files,
                headers={'Authorization': f'Bearer {test_token}'}
            )

        assert response.status_code == 201
        doc_data = response.json()

        # Verify document created
        assert doc_data['document_name'] == 'Test Vision'
        assert doc_data['chunked'] == True
        assert doc_data['chunk_count'] >= 1

        # Verify chunks in database
        chunks = await db_session.execute(
            select(MCPContextIndex).where(
                MCPContextIndex.vision_document_id == doc_data['id']
            )
        )
        chunks_list = chunks.scalars().all()
        assert len(chunks_list) == doc_data['chunk_count']

    finally:
        test_file.unlink(missing_ok=True)
```

**C. Manual Testing Checklist**:

1. ✅ Upload small vision document (< 20K tokens)
   - Should create 1 chunk
   - UI shows "1 chunk • X KB"

2. ✅ Upload large vision document (> 20K tokens)
   - Should create multiple chunks
   - UI shows "N chunks • X KB"

3. ✅ Upload with special characters in filename
   - Should handle correctly

4. ✅ Upload then rechunk
   - Should delete old chunks, create new ones

5. ✅ Upload with auto_chunk=false
   - Should create document but not chunk
   - Manual rechunk should work

6. ✅ Cross-platform path test
   - Paths with backslashes should work
   - Paths with forward slashes should work

---

## Success Criteria

**Phase 1-2 (Async Architecture)**:
- [ ] `chunk_vision_document()` is async
- [ ] All repository calls use `await`
- [ ] All session operations use `await`
- [ ] All callers updated to `await chunk_vision_document()`
- [ ] No sync/async mismatch warnings

**Phase 3 (Error Handling)**:
- [ ] Chunking errors logged with full context
- [ ] Errors surfaced to user (not silent)
- [ ] Helpful error messages
- [ ] Stack traces captured for debugging

**Phase 4 (Testing)**:
- [ ] Unit tests pass (chunk_vision_document)
- [ ] Integration tests pass (upload → chunk flow)
- [ ] Manual testing complete
- [ ] Cross-platform testing (Windows paths)

**Production Readiness**:
- [ ] Vision documents upload and chunk successfully
- [ ] UI shows correct chunk count and file size
- [ ] No silent failures
- [ ] Works on Windows, Linux, macOS
- [ ] Performance acceptable (< 2 seconds for typical docs)

---

## Rollback Strategy

**If Issues Arise**:

1. **Async Issues**:
   - Revert chunker.py to sync version
   - Add temporary sync wrapper that runs async in event loop
   - Fix incrementally

2. **Path Issues**:
   - Database migration to fix existing backslash paths:
     ```sql
     UPDATE vision_documents
     SET vision_path = REPLACE(vision_path, '\', '/')
     WHERE vision_path LIKE '%\%';
     ```

3. **Testing Failures**:
   - Fix specific test cases
   - Don't deploy until all tests pass

---

## Dependencies and Blockers

**Prerequisites**:
- ✅ PostgreSQL running
- ✅ VisionDocument model exists
- ✅ MCPContextIndex table exists
- ✅ Path fixes already applied

**Blockers**:
- None (can proceed immediately)

---

## Risk Assessment

**Technical Risks**: MEDIUM
- Async refactoring could introduce new bugs
- Need to find all callers and update
- Session handling must be correct

**Testing Risks**: LOW
- Can test thoroughly in dev mode
- No production users affected

**Performance Risks**: LOW
- Async is faster than sync for I/O
- Path normalization is negligible overhead

---

## Files to Modify

**Core Changes**:
1. `src/giljo_mcp/context_management/chunker.py` (242-396) - Make async
2. `api/endpoints/vision_documents.py` (194-207, 408-425) - Add await
3. `src/giljo_mcp/repositories/context_repository.py` (if needed) - Make methods async

**Testing**:
4. `tests/unit/test_vision_chunker.py` (NEW) - Unit tests
5. `tests/integration/test_vision_upload_chunking.py` (NEW) - Integration tests

**Documentation**:
6. This handover document

---

## References

**Code Locations**:
- Chunker: `F:\GiljoAI_MCP\src\giljo_mcp\context_management\chunker.py`
- Vision Endpoints: `F:\GiljoAI_MCP\api\endpoints\vision_documents.py`
- Vision Repository: `F:\GiljoAI_MCP\src\giljo_mcp\repositories\vision_document_repository.py`
- Context Repository: `F:\GiljoAI_MCP\src\giljo_mcp\repositories\context_repository.py`

**Related Handovers**:
- 0043: Multi-Vision Document Support (architecture foundation)
- 0046: ProductsView Unified Management (UI integration)

**Documentation**:
- `/docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Async architecture patterns
- `/CLAUDE.md` - Development guidelines

---

## Notes

**Why This Is Critical**:
- Vision document chunking is **core functionality**
- Affects all products that use vision documents
- Currently **100% broken** (no documents chunk successfully)
- Silent failures hide the problem from users

**Why Async-First**:
- FastAPI is async by default
- PostgreSQL async driver (asyncpg) requires async
- All repository methods are async
- Better performance and scalability

**Path Fixes Already Done**:
- Forward slash storage implemented
- Defensive normalization in chunker
- Should work cross-platform now
- Just need async fix to activate chunking

---

**Last Updated**: 2025-10-26
**Next Handover**: After implementation complete
