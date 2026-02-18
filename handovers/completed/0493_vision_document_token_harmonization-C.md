# Handover 0493: Vision Document Token Harmonization

**Date:** 2026-02-15
**From Agent:** Research/audit session (Claude Code CLI)
**To Agent:** Next Session (fresh agent team)
**Priority:** High
**Estimated Complexity:** 4-8 hours
**Status:** Ready

---

## Task Summary

Harmonize the vision document pipeline so that ALL token limits, chunking, and delivery use a consistent **25K max / 24K safety buffer** standard. Fix broken light/medium summary delivery that currently bypasses chunking entirely, and auto-trigger consolidation on upload so light/medium depths always have content.

**Why it matters:** The current pipeline has 5+ different token constants (5K, 10K, 17.5K, 20K, 24K, 25K) scattered across files with two incompatible token counting methods (tiktoken vs chars/4). Agents receiving vision content can hit Claude Code's ~25K tool response limit on light/medium summaries.

---

## Context and Background

### Root Cause Analysis (Session 2026-02-15)

A full token audit across 14 files identified 27 distinct token limits in 5 categories. The vision document pipeline was traced end-to-end (ingest -> SUMI -> store -> consolidate -> fetch) and three issues were found:

1. **Light/medium summaries delivered as single blob** - no chunking, can exceed 25K
2. **Consolidation not auto-triggered on upload** - light/medium depths return "Run consolidation first" error
3. **Token counting inconsistency** - tiktoken on ingest, chars/4 on fetch, causing budget mismatches
4. **Scattered constants** - same conceptual limit expressed as 5K, 20K, 24K, 25K in different files

### The Canonical Standard (Product Owner Intent)

- **25K** = maximum document acceptance / chunk storage threshold
- **24K** = safety buffer for delivery (EnhancedChunker.MAX_TOKENS already enforces this)
- **All depths** (full, medium, light) must deliver responses <=24K tokens per call
- **SUMI** creates 33% (light) and 66% (medium) compressions per document
- **Consolidation** merges all active docs into product-level summaries for multi-doc products
- **Pagination** with `has_more`/`next_offset` for any response exceeding 24K

---

## Current State (What Exists)

### Files and Their Token Constants

| File | Constant | Current Value | Purpose |
|------|----------|---------------|---------|
| `tools/chunking.py` (EnhancedChunker) | `MAX_TOKENS` | 24000 | Hard cap on chunk size |
| `tools/chunking.py` (EnhancedChunker) | `DEFAULT_MAX_TOKENS` | 20000 | Default when no size specified |
| `tools/chunking.py` (EnhancedChunker) | `TOKEN_CHAR_RATIO` | 4 | chars/4 estimation |
| `context_management/chunker.py` (VisionDocumentChunker) | `target_chunk_size` default | 5000 | Default (overridden by callers) |
| `services/product_service.py` | `max_tokens` param default | 25000 | Upload acceptance threshold |
| `tools/context_tools/get_vision_document.py` | `get_max_tokens("full")` | 24000 | Full-depth delivery budget |
| `tools/context_tools/get_vision_document.py` | `get_max_tokens("medium")` | 17500 | Medium-depth delivery budget |
| `tools/context_tools/get_vision_document.py` | `get_max_tokens("light")` | 10000 | Light-depth delivery budget |
| `tools/context_tools/get_vision_document.py` | `estimate_tokens()` | chars/4 | Fetch-side token counting |
| `services/context_service.py` | `get_vision max_tokens` | 20000 | Legacy context service |
| `tools/context.py` | `get_vision max_tokens` | 20000 | Legacy MCP tool |
| `context_management/manager.py` | `target_chunk_size` default | 5000 | Context manager default |
| `context_management/loader.py` | `max_tokens` default | 10000 | Context loader budget |
| `services/orchestration_service.py:2503` | `target_chunk_size` | 2000 | Orchestration-specific chunking |

### Two Token Counting Methods

1. **tiktoken (cl100k_base)** - Used by `VisionDocumentChunker` during ingest. Accurate.
2. **chars/4** - Used by `EnhancedChunker` and `get_vision_document` during fetch. Approximate.

A chunk stored as 24,000 tiktoken tokens could be estimated as anywhere from 18,000-30,000 by chars/4 depending on content density. This causes the fetch-side budget to cut off unpredictably.

---

## Issues to Fix

### Issue 1: Light/Medium Summaries Not Chunked (CRITICAL)

**File:** `src/giljo_mcp/tools/context_tools/get_vision_document.py`
**Function:** `_get_summary_response()` (lines 87-167)

Currently returns the entire consolidated summary as one blob with `"pagination": None`. If a product has many vision documents and the consolidated SUMI medium (66%) exceeds 24K tokens, it exceeds the CLI tool response limit.

**Fix:** Add pagination to `_get_summary_response()`. If the summary exceeds 24K tokens, chunk it and return with the same pagination format as full-depth responses. Accept `offset` and `limit` parameters.

### Issue 2: No Auto-Consolidation on Upload (HIGH)

**File:** `src/giljo_mcp/services/product_service.py`
**Function:** `upload_vision_document()` (lines 1095-1273)

After uploading and chunking a document, the method does NOT call `consolidate_vision_documents()`. This means light/medium fetches return "No consolidated summary available" until the user manually triggers consolidation via the API.

**Fix:** After successful upload + SUMI + chunking, call `ConsolidatedVisionService.consolidate_vision_documents()` to regenerate product-level summaries. Use `force=True` since we know content changed.

### Issue 3: Token Counting Inconsistency (MEDIUM)

**Ingest** uses tiktoken, **fetch** uses chars/4. Standardize on one method.

**Recommended fix:** Keep tiktoken for accurate ingest counting (it's already there). On the fetch side in `get_vision_document.py`, the `estimate_tokens()` function should use the `token_count` value stored on `MCPContextIndex` records (which was computed by tiktoken during ingest) rather than re-estimating with chars/4.

The chunks already store `token_count` as a column. The fetch loop should use `chunk.token_count` instead of `estimate_tokens(chunk.content)`.

### Issue 4: Standardize Constants (MEDIUM)

Replace the scattered defaults with named constants from a single source:

```python
# Proposed: src/giljo_mcp/tools/chunking.py (or a new constants module)
VISION_MAX_INGEST_TOKENS = 25000    # Max accepted document size
VISION_DELIVERY_BUDGET = 24000      # Max tokens per delivery call (safety buffer)
VISION_DEFAULT_CHUNK_SIZE = 24000   # Default chunk target (= delivery budget)
TOKEN_CHAR_RATIO = 4                # Approximate chars-per-token ratio
```

Update all callers to import these instead of hardcoding.

---

## Implementation Plan

### Phase 1: Constants Standardization
1. Add named constants to `tools/chunking.py` (or create `src/giljo_mcp/constants.py`)
2. Update `VisionDocumentChunker.__init__` default from 5000 to `VISION_DELIVERY_BUDGET` (24000)
3. Update `ContextManagementSystem.__init__` default from 5000 to `VISION_DELIVERY_BUDGET`
4. Update `get_max_tokens()` in `get_vision_document.py` to use the constant for full depth
5. Update `product_service.py` upload default from 25000 to `VISION_MAX_INGEST_TOKENS`
6. Update legacy defaults in `context_service.py` and `context.py` from 20000 to `VISION_DELIVERY_BUDGET`
7. Leave `orchestration_service.py:2503` at 2000 (intentionally small for orchestration summaries)

### Phase 2: Fix Light/Medium Delivery Chunking
1. Modify `_get_summary_response()` to accept `offset` parameter
2. If summary tokens > `VISION_DELIVERY_BUDGET`, chunk the summary text and paginate
3. Use `EnhancedChunker` for consistent boundary detection
4. Return same pagination format as full-depth: `{total_chunks, offset, limit, has_more, next_offset}`
5. Update `get_vision_document()` to pass offset/limit to `_get_summary_response()`

### Phase 3: Fix Fetch-Side Token Counting
1. In `get_vision_document()` full-depth loop, use `chunk.token_count` (stored DB value from tiktoken) instead of `estimate_tokens(chunk.content)`
2. Keep `estimate_tokens()` as fallback only when `token_count` is NULL/0
3. This ensures ingest and fetch agree on token counts

### Phase 4: Auto-Consolidation on Upload
1. In `upload_vision_document()`, after successful chunk, call consolidation
2. Import and instantiate `ConsolidatedVisionService`
3. Call `consolidate_vision_documents(product_id, session, tenant_key, force=True)`
4. Wrap in try/except so consolidation failure doesn't fail the upload
5. Log success/failure

### Phase 5: Tests (TDD - write first where practical)
1. Test light summary chunking when summary > 24K tokens
2. Test medium summary chunking when summary > 24K tokens
3. Test light/medium pagination (offset, has_more)
4. Test auto-consolidation triggers after upload
5. Test fetch uses stored token_count instead of chars/4
6. Test constants are consistent across modules
7. Regression: existing full-depth pagination still works

---

## Key Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/chunking.py` | Add named constants, keep MAX_TOKENS=24000 |
| `src/giljo_mcp/context_management/chunker.py` | Update default target_chunk_size to use constant |
| `src/giljo_mcp/context_management/manager.py` | Update default target_chunk_size |
| `src/giljo_mcp/tools/context_tools/get_vision_document.py` | Fix `_get_summary_response()` chunking, fix `estimate_tokens` usage, use constants |
| `src/giljo_mcp/services/product_service.py` | Add auto-consolidation after upload, use constant |
| `src/giljo_mcp/services/context_service.py` | Update default max_tokens |
| `src/giljo_mcp/tools/context.py` | Update default max_tokens |
| `src/giljo_mcp/context_management/loader.py` | Update default max_tokens |

**Do NOT modify:**
- `services/orchestration_service.py:2503` - intentionally uses 2000 for orchestration summaries
- `services/vision_summarizer.py` - SUMI logic is correct, no token limit changes needed
- `services/consolidation_service.py` - consolidation logic is correct, just needs to be called

---

## Testing Requirements

**Unit Tests:**
- `_get_summary_response()` returns paginated response when summary > 24K
- `_get_summary_response()` returns single response when summary <= 24K (no regression)
- `get_vision_document()` full-depth uses `chunk.token_count` from DB
- Constants are importable and consistent

**Integration Tests:**
- Upload document -> auto-consolidation runs -> light/medium fetch returns content
- Upload large document (>50K) -> light summary (33%) still fits in 24K delivery
- Upload very large document (>150K) -> medium summary (66%) gets chunked for delivery
- Multi-document upload -> consolidation aggregates all docs -> light/medium returns paginated

**Regression Tests:**
- Full-depth pagination still works (offset, limit, has_more)
- Small documents (<24K) still return single-chunk responses
- SUMI summarization still produces correct compression ratios

---

## Success Criteria

1. Zero hardcoded token literals outside the constants definition
2. Light/medium depth fetches never exceed 24K tokens per response
3. Auto-consolidation ensures light/medium always have content after upload
4. Fetch-side token counting uses stored tiktoken values, not chars/4 re-estimation
5. All existing tests pass + new tests for the fixes
6. `ruff check` passes clean

---

## Rollback Plan

All changes are additive behavior fixes. If anything breaks:
1. Revert the auto-consolidation call in `upload_vision_document()` (manual consolidation still works)
2. Revert `_get_summary_response()` pagination (returns to single-blob behavior)
3. Constants are just aliases - reverting to inline numbers has zero behavior change

---

## Dependencies

- No external dependencies
- No database schema changes
- No migration needed
- No frontend changes needed (pagination format already exists, frontend handles it)
