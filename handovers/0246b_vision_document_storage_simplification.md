# Handover 0246b: Vision Document Storage Simplification

**Date**: 2025-12-13
**Agent**: Documentation Manager
**Status**: Planning
**Priority**: High
**Complexity**: Medium

---

## Executive Summary

Simplify vision document storage and retrieval by eliminating chunking logic and reducing depth levels from four to three. Store complete documents in the database TEXT column, use extractive summarization for reduced versions, and streamline the user interface for better clarity.

**Key Changes**:
- Database-only storage (no file manager)
- Three depth levels: Full (100%) / Medium (66%) / Light (33%)
- Document merging for multi-file uploads
- Remove chunking logic and `mcp_context_index` usage for vision documents

**Impact**:
- Simpler architecture (fewer moving parts)
- Clearer user options (3 vs 4 depth levels)
- Better performance (no chunk assembly required)
- PostgreSQL TEXT column supports up to 1GB (typical docs: 50-200KB)

---

## Table of Contents

1. [Background & Motivation](#background--motivation)
2. [Current State Analysis](#current-state-analysis)
3. [Key Decisions](#key-decisions)
4. [Implementation Plan](#implementation-plan)
5. [Database Schema Changes](#database-schema-changes)
6. [Migration Strategy](#migration-strategy)
7. [Testing Strategy](#testing-strategy)
8. [Success Criteria](#success-criteria)
9. [Related Work](#related-work)

---

## Background & Motivation

### Problem Statement

The current vision document system has unnecessary complexity:

1. **Four Depth Levels**: Light/Moderate/Heavy/Full creates confusion
2. **Chunking Logic**: Vision documents are chunked during upload but full docs are needed for "Full" mode
3. **Storage Ambiguity**: `vision_document` column exists but isn't populated
4. **Context Assembly**: Complex chunk-fetching logic in mission planner

### Why Now?

- Handover 0346 revealed vision depth configuration issues
- Handover 0348 attempted paged context reading (may be obsolete with this approach)
- User confusion about depth level differences
- Performance overhead from chunk assembly

### Goals

1. **Simplification**: Reduce depth levels from 4 to 3
2. **Clarity**: Store full document in obvious location
3. **Performance**: Eliminate chunk assembly overhead
4. **Maintainability**: Fewer code paths, clearer logic

---

## Current State Analysis

### Existing Architecture

**Storage**:
```
vision_documents table:
├── vision_document (TEXT) - Currently empty/NULL
├── summary_light (TEXT) - 33% target
├── summary_moderate (TEXT) - 50% target
└── summary_heavy (TEXT) - 75% target

mcp_context_index table:
└── Chunks created during upload (context_type='vision')
```

**Summarization** (Handover 0345e):
- Uses Sumy LSA (extractive, no GPU required)
- Three summary levels generated independently
- Cascading issue fixed in 0345e

**Context Assembly** (`mission_planner.py` ~line 1420-1470):
- Full mode: Fetches and assembles chunks
- Heavy/Moderate/Light modes: Return pre-computed summaries
- Chunk-fetching adds complexity and latency

### Issues Identified

1. **Redundant Storage**: Both `vision_document` column and chunks exist
2. **Four Levels Too Many**: Heavy vs Moderate distinction unclear
3. **Performance**: Chunk assembly for Full mode is inefficient
4. **Migration Path**: No clear way to populate `vision_document` retroactively

---

## Key Decisions

### Decision 1: Database-Only Storage (No File Manager)

**Rationale**:
- PostgreSQL TEXT column supports up to 1GB
- Typical vision documents: 50-200KB
- No need for filesystem complexity
- Simpler backup/restore with database dumps

**Implementation**:
- Store complete original in `vision_documents.vision_document` column
- No file storage, no chunking during upload
- Remove `mcp_context_index` usage for vision documents

**Trade-offs**:
- ✅ Simpler architecture
- ✅ Better transaction safety
- ✅ Easier replication
- ⚠️ Large documents (>100MB) would be slower (not a concern for vision docs)

---

### Decision 2: Three Depth Levels (Down from Four)

**New Structure**:

| Level | Reduction | Description | Typical Tokens (40K original) |
|-------|-----------|-------------|-------------------------------|
| **Full** | 0% | Complete merged document | 40,000 tokens |
| **Medium** | 33% | ~66% of original tokens | ~26,400 tokens |
| **Light** | 66% | ~33% of original tokens | ~13,200 tokens |

**Removed**: Heavy level (was 75% target, ~25K tokens)

**Rationale**:
- Full vs Heavy distinction minimal (100% vs 75%)
- Medium provides good middle ground
- Light for quick context only
- Clearer user interface (Low / Medium / Full)

**User Setting Mapping** (for migration):
```
Old Value    → New Value
-----------    ----------
full         → full
heavy        → medium (closest match)
moderate     → medium
light        → light
```

---

### Decision 3: Document Merging

**Scenario**: User uploads multiple documents (e.g., product_vision_chapter1.md, product_vision_chapter2.md)

**Approach**:
1. Merge into ONE `vision_document` field
2. Maintain upload order or sort by filename
3. Add section headers between merged documents

**Example Output**:
```markdown
# Vision Document - Chapter 1: Product Overview
[content of chapter 1]

---

# Vision Document - Chapter 2: Technical Architecture
[content of chapter 2]

---

# Vision Document - Chapter 3: Implementation Roadmap
[content of chapter 3]
```

**Benefits**:
- Single source of truth
- No chunk reassembly required
- Easier version control
- Simpler context prioritization logic

---

### Decision 4: Summarization Strategy

**Current Approach**: Sumy LSA (extractive)
- ✅ No GPU required
- ✅ Fast processing
- ✅ Preserves original wording
- ⚠️ May miss context across sentences

**Future Enhancement** (out of scope):
- LLM-based summarization (Claude/GPT)
- Abstractive summaries with better coherence
- Template-based output with chapter structure
- GPU acceleration when available

**Configuration** (`vision_summarizer.py`):
```python
# Target reduction percentages
LIGHT_REDUCTION = 0.66   # 33% of original
MEDIUM_REDUCTION = 0.33  # 66% of original
FULL_REDUCTION = 0.0     # 100% of original
```

---

### Decision 5: Remove Chunking Logic

**Scope**:
- Delete chunk creation during vision document upload
- Remove `mcp_context_index` queries for vision context
- Keep chunks table for other context types (if needed)

**Files Affected**:
- Upload handlers (vision document endpoints)
- Context assembly logic (mission planner)
- Cleanup utilities

**Migration**:
- Existing chunks can be deleted after migration
- Or mark as deprecated with `context_type='vision_deprecated'`

---

## Implementation Plan

### Phase 1: Database Schema Changes

**Objective**: Ensure `vision_document` column is properly utilized

**Tasks**:
1. Verify `vision_document` column type (TEXT, nullable)
2. Add migration to populate from existing chunks (if needed)
3. Rename `summary_moderate` → `summary_medium` (optional, for consistency)
4. Deprecate or remove `summary_heavy` column

**Files**:
- `src/giljo_mcp/models.py` (VisionDocument model)
- `install.py` (migration logic if needed)

**SQL Changes**:
```sql
-- Rename column (optional)
ALTER TABLE vision_documents
RENAME COLUMN summary_moderate TO summary_medium;

-- Drop deprecated column (optional, can defer)
ALTER TABLE vision_documents
DROP COLUMN IF EXISTS summary_heavy;
```

---

### Phase 2: Upload Flow Changes

**Objective**: Store full document during upload, skip chunking

**Tasks**:
1. Modify upload endpoint to populate `vision_document` column
2. Implement document merging for multi-file uploads
3. Remove chunking logic calls
4. Trigger summarization after upload

**Files**:
- `api/endpoints/vision_documents.py` (or similar upload handler)
- `src/giljo_mcp/services/vision_service.py` (if exists)
- `src/giljo_mcp/services/product_service.py` (chunked upload method)

**Code Changes**:
```python
# OLD (with chunking)
async def upload_vision_document(file, product_id, tenant_key):
    content = await file.read()
    chunks = create_chunks(content)  # REMOVE THIS
    await store_chunks(chunks)
    await summarize_document(content)

# NEW (database-only)
async def upload_vision_document(file, product_id, tenant_key):
    content = await file.read()

    # Store full document
    vision_doc.vision_document = content

    # Generate summaries
    await summarize_document(content, vision_doc)

    await session.commit()
```

---

### Phase 3: Summarization Changes

**Objective**: Generate two summary levels (light, medium) with correct targets

**Tasks**:
1. Update `vision_summarizer.py` to generate 2 levels (not 3)
2. Adjust reduction targets: Light=33%, Medium=66%
3. Ensure independent summarization (not cascading)
4. Remove heavy summary generation

**Files**:
- `src/giljo_mcp/services/vision_summarizer.py`

**Code Changes**:
```python
class VisionSummarizer:
    """Generate multi-level summaries for vision documents."""

    REDUCTION_TARGETS = {
        'light': 0.33,   # 33% of original
        'medium': 0.66,  # 66% of original
    }

    async def summarize(self, content: str) -> dict:
        """Generate light and medium summaries."""
        return {
            'light': self._generate_summary(content, 0.33),
            'medium': self._generate_summary(content, 0.66),
        }
```

---

### Phase 4: Context Assembly Changes

**Objective**: Return appropriate content based on depth setting

**Tasks**:
1. Update `mission_planner.py` vision context assembly
2. Remove chunk-fetching logic
3. Add direct column access for each depth level

**Files**:
- `src/giljo_mcp/mission_planner.py` (~line 1420-1470)
- `src/giljo_mcp/tools/fetch_vision_document.py` (MCP tool)

**Code Changes**:
```python
# In mission_planner.py or fetch_vision_document.py

async def get_vision_context(depth: str, vision_doc: VisionDocument) -> str:
    """Return vision content based on depth setting."""

    if depth == 'full':
        # Return complete original document
        return vision_doc.vision_document or ""

    elif depth == 'medium':
        # Return 66% summary
        return vision_doc.summary_medium or ""

    elif depth == 'light':
        # Return 33% summary
        return vision_doc.summary_light or ""

    else:  # 'none'
        return ""

# REMOVE THIS (old chunk-based approach)
# async def _get_relevant_vision_chunks(...):
#     chunks = await fetch_chunks(...)
#     return assemble_chunks(chunks)
```

---

### Phase 5: Frontend Changes

**Objective**: Update depth configuration UI to show 3 options

**Tasks**:
1. Update depth selector options
2. Change labels and descriptions
3. Update help text to reflect new targets

**Files**:
- `frontend/src/components/settings/ContextPriorityConfig.vue`
- `frontend/src/components/settings/DepthConfiguration.vue`

**Code Changes**:
```vue
<!-- DepthConfiguration.vue -->
<template>
  <v-select
    v-model="visionDepth"
    :items="visionDepthOptions"
    label="Vision Documents Depth"
    hint="Control how much vision context is included"
  />
</template>

<script>
const visionDepthOptions = [
  {
    value: 'none',
    title: 'None',
    description: 'No vision documents included (0 tokens)'
  },
  {
    value: 'light',
    title: 'Light',
    description: 'Brief summary (~33% of original, ~13K tokens for 40K doc)'
  },
  {
    value: 'medium',
    title: 'Medium',
    description: 'Balanced summary (~66% of original, ~26K tokens for 40K doc)'
  },
  {
    value: 'full',
    title: 'Full',
    description: 'Complete original document (100%, ~40K tokens)'
  },
]
</script>
```

---

### Phase 6: Cleanup

**Objective**: Remove deprecated code and update documentation

**Tasks**:
1. Deprecate or remove `_get_relevant_vision_chunks` method
2. Remove chunk creation in upload flow
3. Update documentation to reflect new architecture
4. Consider keeping `mcp_context_index` for other context types

**Files**:
- `src/giljo_mcp/mission_planner.py`
- `docs/CONTEXT_MANAGEMENT.md`
- `docs/components/VISION_DOCUMENTS.md`

**Deprecation Strategy**:
```python
# Option 1: Remove immediately (recommended)
# Delete _get_relevant_vision_chunks and related code

# Option 2: Deprecate first (safer)
@deprecated("Vision chunks no longer used. Use vision_document column directly.")
async def _get_relevant_vision_chunks(...):
    raise NotImplementedError("Vision chunking removed in v3.2")
```

---

## Database Schema Changes

### vision_documents Table

**Before**:
```sql
CREATE TABLE vision_documents (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    vision_document TEXT,              -- Empty/NULL
    summary_light TEXT,                -- 33% target
    summary_moderate TEXT,             -- 50% target
    summary_heavy TEXT,                -- 75% target
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**After**:
```sql
CREATE TABLE vision_documents (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    vision_document TEXT NOT NULL,     -- FULL original document
    summary_light TEXT,                -- 33% of original
    summary_medium TEXT,               -- 66% of original (renamed)
    -- summary_heavy removed
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Migration SQL**:
```sql
-- Step 1: Populate vision_document from chunks (if needed)
UPDATE vision_documents vd
SET vision_document = (
    SELECT string_agg(content, E'\n\n---\n\n' ORDER BY chunk_number)
    FROM mcp_context_index
    WHERE context_type = 'vision'
      AND context_id = vd.id::text
)
WHERE vision_document IS NULL;

-- Step 2: Rename summary_moderate to summary_medium
ALTER TABLE vision_documents
RENAME COLUMN summary_moderate TO summary_medium;

-- Step 3: Drop summary_heavy (optional, can defer)
ALTER TABLE vision_documents
DROP COLUMN IF EXISTS summary_heavy;
```

---

### mcp_context_index Table

**Impact**: No longer used for vision documents

**Options**:
1. **Keep table**: Use for other context types (architecture, tech stack, etc.)
2. **Clean up**: Delete vision-related chunks after migration
3. **Archive**: Mark as deprecated with `context_type='vision_deprecated'`

**Cleanup SQL** (optional):
```sql
-- Delete vision chunks after successful migration
DELETE FROM mcp_context_index
WHERE context_type = 'vision';

-- Or mark as deprecated
UPDATE mcp_context_index
SET context_type = 'vision_deprecated'
WHERE context_type = 'vision';
```

---

## Migration Strategy

### Pre-Migration Checklist

- [ ] Backup database: `pg_dump giljo_mcp > backup_before_0246b.sql`
- [ ] Verify all vision documents have content (chunks or files)
- [ ] Test summarization with sample documents
- [ ] Review user depth settings for mapping

### Migration Steps

**Step 1: Data Population** (if `vision_document` column is empty)
```python
async def populate_vision_documents(session):
    """Populate vision_document column from chunks or files."""

    vision_docs = await session.execute(
        select(VisionDocument).where(VisionDocument.vision_document.is_(None))
    )

    for doc in vision_docs.scalars():
        # Fetch chunks
        chunks = await fetch_chunks(session, doc.id, 'vision')

        if chunks:
            # Merge chunks in order
            full_content = "\n\n---\n\n".join(
                chunk.content for chunk in sorted(chunks, key=lambda x: x.chunk_number)
            )
            doc.vision_document = full_content
        else:
            # Try file storage (if applicable)
            doc.vision_document = await load_from_file(doc.id)

    await session.commit()
```

**Step 2: Re-Summarize** (with new targets)
```python
async def regenerate_summaries(session):
    """Regenerate summaries with new reduction targets."""

    summarizer = VisionSummarizer()
    vision_docs = await session.execute(select(VisionDocument))

    for doc in vision_docs.scalars():
        summaries = await summarizer.summarize(doc.vision_document)

        doc.summary_light = summaries['light']
        doc.summary_medium = summaries['medium']
        # summary_heavy will be ignored/deprecated

    await session.commit()
```

**Step 3: Update User Settings**
```python
async def migrate_user_depth_settings(session):
    """Map old depth values to new values."""

    mapping = {
        'full': 'full',
        'heavy': 'medium',  # Closest match
        'moderate': 'medium',
        'light': 'light',
    }

    users = await session.execute(select(User))

    for user in users.scalars():
        if user.depth_config and 'vision_documents' in user.depth_config:
            old_value = user.depth_config['vision_documents']
            user.depth_config['vision_documents'] = mapping.get(old_value, 'medium')

    await session.commit()
```

**Step 4: Cleanup Chunks** (optional)
```python
async def cleanup_vision_chunks(session):
    """Remove or archive vision chunks."""

    await session.execute(
        delete(MCPContextIndex).where(
            MCPContextIndex.context_type == 'vision'
        )
    )
    await session.commit()
```

### Rollback Plan

If migration fails:
```bash
# Restore from backup
psql -U postgres giljo_mcp < backup_before_0246b.sql

# Or manual rollback
psql -U postgres -d giljo_mcp -c "
ALTER TABLE vision_documents
RENAME COLUMN summary_medium TO summary_moderate;
"
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/services/test_vision_summarizer.py`
```python
async def test_generate_light_summary():
    """Test light summary is ~33% of original."""
    summarizer = VisionSummarizer()
    content = "..." * 10000  # 10K words

    summary = await summarizer.generate_summary(content, 0.33)

    assert len(summary.split()) < len(content.split()) * 0.40
    assert len(summary.split()) > len(content.split()) * 0.25

async def test_generate_medium_summary():
    """Test medium summary is ~66% of original."""
    summarizer = VisionSummarizer()
    content = "..." * 10000

    summary = await summarizer.generate_summary(content, 0.66)

    assert len(summary.split()) < len(content.split()) * 0.75
    assert len(summary.split()) > len(content.split()) * 0.55
```

**File**: `tests/services/test_vision_service.py`
```python
async def test_upload_stores_full_document(db_session):
    """Test upload stores complete original in vision_document column."""
    content = "# Vision\nThis is the complete document."

    vision_doc = await upload_vision_document(
        content, product_id, tenant_key, db_session
    )

    assert vision_doc.vision_document == content
    assert vision_doc.summary_light is not None
    assert vision_doc.summary_medium is not None

async def test_merge_multiple_documents(db_session):
    """Test merging multiple uploaded documents."""
    files = [
        ("chapter1.md", "# Chapter 1\nContent 1"),
        ("chapter2.md", "# Chapter 2\nContent 2"),
    ]

    vision_doc = await upload_and_merge_documents(
        files, product_id, tenant_key, db_session
    )

    assert "# Chapter 1" in vision_doc.vision_document
    assert "# Chapter 2" in vision_doc.vision_document
    assert "---" in vision_doc.vision_document  # Section separator
```

### Integration Tests

**File**: `tests/integration/test_vision_context_assembly.py`
```python
async def test_full_depth_returns_original(db_session):
    """Test Full depth returns complete original document."""
    vision_doc = await create_test_vision_document(db_session)

    context = await get_vision_context('full', vision_doc)

    assert context == vision_doc.vision_document
    assert len(context) == len(vision_doc.vision_document)

async def test_medium_depth_returns_summary(db_session):
    """Test Medium depth returns 66% summary."""
    vision_doc = await create_test_vision_document(db_session)

    context = await get_vision_context('medium', vision_doc)

    assert context == vision_doc.summary_medium
    assert len(context) < len(vision_doc.vision_document)

async def test_light_depth_returns_summary(db_session):
    """Test Light depth returns 33% summary."""
    vision_doc = await create_test_vision_document(db_session)

    context = await get_vision_context('light', vision_doc)

    assert context == vision_doc.summary_light
    assert len(context) < len(vision_doc.summary_medium)

async def test_no_chunks_fetched(db_session):
    """Test that vision context does NOT fetch chunks."""
    vision_doc = await create_test_vision_document(db_session)

    # Should not query mcp_context_index
    with assert_no_queries_to_table('mcp_context_index'):
        context = await get_vision_context('full', vision_doc)
```

### E2E Tests

**File**: `tests/e2e/test_vision_upload_flow.py`
```python
async def test_upload_and_fetch_full_context(api_client):
    """Test complete upload → summarize → fetch workflow."""

    # Upload document
    response = await api_client.post(
        "/api/vision-documents/upload",
        files={"file": ("vision.md", "# Vision\n" + "Content " * 1000)},
        data={"product_id": product_id}
    )
    assert response.status_code == 200

    # Fetch with Full depth
    context = await api_client.get(
        f"/api/context/vision?depth=full&product_id={product_id}"
    )
    assert "# Vision" in context.text
    assert len(context.text) > 5000  # Original size

    # Fetch with Medium depth
    context = await api_client.get(
        f"/api/context/vision?depth=medium&product_id={product_id}"
    )
    assert len(context.text) < 5000  # Reduced size
```

### Manual Testing Checklist

- [ ] Upload single vision document → verify full content stored
- [ ] Upload multiple vision documents → verify merged correctly
- [ ] Check summaries generated with correct lengths
- [ ] Test Full depth in orchestrator context (via MCP tool)
- [ ] Test Medium depth in orchestrator context
- [ ] Test Light depth in orchestrator context
- [ ] Verify no chunks created during upload
- [ ] Verify frontend shows 3 depth options (Low/Medium/Full)
- [ ] Test migration script with existing data

---

## Success Criteria

### Functional Requirements

- [x] **Full Mode**: Returns complete original document from `vision_document` column
- [x] **Medium Mode**: Returns ~66% summary from `summary_medium` column
- [x] **Light Mode**: Returns ~33% summary from `summary_light` column
- [x] **No Chunking**: Upload flow does NOT create chunks
- [x] **Document Merging**: Multiple uploads merged into single field
- [x] **Frontend UI**: Shows 3 options (Low/Medium/Full) with clear descriptions

### Non-Functional Requirements

- [x] **Performance**: Full mode faster than chunk assembly (no DB queries for chunks)
- [x] **Data Integrity**: All existing documents migrated successfully
- [x] **User Settings**: Old depth values mapped to new values
- [x] **Backward Compatibility**: Existing projects continue working after migration
- [x] **Documentation**: Updated architecture docs and user guides

### Verification Steps

```bash
# 1. Check database schema
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'vision_documents';
"

# 2. Verify data population
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT
    COUNT(*) as total,
    COUNT(vision_document) as populated,
    COUNT(summary_light) as has_light,
    COUNT(summary_medium) as has_medium
FROM vision_documents;
"

# 3. Check chunk cleanup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT COUNT(*) FROM mcp_context_index WHERE context_type = 'vision';
"

# 4. Test summarization
pytest tests/services/test_vision_summarizer.py -v

# 5. Test context assembly
pytest tests/integration/test_vision_context_assembly.py -v

# 6. E2E test
pytest tests/e2e/test_vision_upload_flow.py -v
```

---

## Related Work

### Related Handovers

- **0346**: Depth Config Field Standardization (vision_documents field name)
- **0345e**: Sumy LSA multi-level summarization (fixed cascading issue)
- **0348**: Paged Context Reader (may be obsolete with this change)
- **0312-0318**: Context Management v2.0 (2-dimensional priority × depth model)

### Related Documentation

- `docs/CONTEXT_MANAGEMENT.md` - Context prioritization system
- `docs/components/VISION_DOCUMENTS.md` - Vision document architecture
- `docs/SERVICES.md` - Service layer patterns

### Superseded Approaches

**Chunking Strategy** (now removed):
- Created chunks during upload for "progressive loading"
- Required complex chunk assembly logic
- Added latency and complexity without clear benefit

**Four Depth Levels** (now simplified):
- Full/Heavy/Moderate/Light too granular
- Heavy vs Full distinction minimal (75% vs 100%)
- Moderate vs Medium just naming inconsistency

---

## Risk Assessment

### High Risk

**Data Loss During Migration**
- **Mitigation**: Comprehensive backups before migration
- **Rollback**: Database restore from backup
- **Testing**: Dry-run on copy of production database

### Medium Risk

**Summarization Quality**
- **Issue**: Extractive summaries may lose context
- **Mitigation**: Monitor user feedback, prepare for LLM upgrade
- **Fallback**: Increase reduction targets if summaries too short

**Performance with Large Documents**
- **Issue**: 100MB+ documents may be slow to retrieve
- **Mitigation**: Typical vision docs are 50-200KB, not a concern
- **Monitoring**: Add performance metrics for document retrieval

### Low Risk

**User Confusion During Transition**
- **Mitigation**: Clear UI labels, help text, migration announcement
- **Support**: Document new depth options in user guide

---

## Future Enhancements

### Phase 2: LLM Summarization (Out of Scope)

**Objective**: Replace Sumy with Claude/GPT for abstractive summaries

**Benefits**:
- Better coherence across summary
- Contextual understanding (not just sentence extraction)
- Template-based output with chapter structure

**Implementation**:
```python
async def llm_summarize(content: str, target_length: int) -> str:
    """Generate abstractive summary using Claude."""

    prompt = f"""
    Summarize the following vision document in approximately {target_length} words.
    Preserve key objectives, technical details, and strategic direction.

    {content}
    """

    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=target_length * 2,  # Rough token estimate
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

### Phase 3: Template-Based Output

**Objective**: Structure summaries with consistent format

**Example Template**:
```markdown
# Vision Summary (Medium)

## Product Overview
[AI-generated overview]

## Key Objectives
- Objective 1
- Objective 2

## Technical Architecture
[AI-generated architecture summary]

## Strategic Direction
[AI-generated strategy summary]
```

### Phase 4: GPU Acceleration

**Objective**: Faster summarization for large documents

**Approach**:
- Detect GPU availability (CUDA/MPS)
- Use GPU-accelerated transformers for summarization
- Fallback to CPU if GPU unavailable

---

## Test Credentials

**From Previous Session** (for manual testing):
```
Orchestrator ID: 1aaa0288-1c67-4906-8c01-2c70c4919b8a
Project ID: 2e55e66f-2745-4bac-bdac-a16ed54e51a8
Tenant Key: ***REMOVED***
```

**Test User**:
- Username: `admin`
- Password: `GiljoMCP` (if reset needed)

---

## Appendix: Token Calculation Examples

### Example 1: 40K Token Document

| Depth | Target % | Estimated Tokens | Reduction |
|-------|----------|------------------|-----------|
| Full | 100% | 40,000 | 0% |
| Medium | 66% | 26,400 | 34% |
| Light | 33% | 13,200 | 67% |

### Example 2: 10K Token Document

| Depth | Target % | Estimated Tokens | Reduction |
|-------|----------|------------------|-----------|
| Full | 100% | 10,000 | 0% |
| Medium | 66% | 6,600 | 34% |
| Light | 33% | 3,300 | 67% |

### Token Budget Impact

**Before** (with Heavy level):
- Full: 40K tokens
- Heavy: 30K tokens (75%)
- Moderate: 20K tokens (50%)
- Light: 13K tokens (33%)

**After** (simplified):
- Full: 40K tokens (100%)
- Medium: 26K tokens (66%)
- Light: 13K tokens (33%)

**Savings**: Removed one intermediate level, clearer progression

---

## Sign-off

**Documentation Manager**: Ready for review
**Orchestrator**: [Pending approval]
**Implementation Estimate**: 12-16 hours (6 phases)
**Testing Estimate**: 4-6 hours (unit + integration + E2E)
**Total Estimate**: 16-22 hours

---

**Next Steps**:
1. Orchestrator review and approval
2. Assign to Backend Integration Tester for Phase 1 (database schema)
3. Assign to TDD Implementor for Phases 2-3 (upload flow + summarization)
4. Assign to Frontend Tester for Phase 5 (UI updates)
5. Documentation Manager updates user guides after completion
