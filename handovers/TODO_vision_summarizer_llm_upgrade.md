# TODO: Vision Document Summarizer Improvements & LLM Path

**Created**: 2025-12-27
**Priority**: Medium
**Status**: Two-Phase Plan

## Phase 1: Consolidated Vision Summaries (IMMEDIATE)

**Handover**: See `0377_consolidated_vision_documents.md`

**Problem**:
- Orchestrator receives summaries from only first vision document (bug in `get_vision_document.py:112`)
- Multi-chapter products (e.g., 5 chapters) return only Chapter 1 context
- Sumy summaries underperform on multi-doc aggregates

**Architecture**:
```
VisionDocument (per-chapter) → Aggregate Full Text → Sumy → Product.consolidated_vision_light/medium
```

**Deliverables**:
- [x] Add columns to Product table: `consolidated_vision_light`, `consolidated_vision_medium`, `consolidated_vision_light_tokens`, `consolidated_vision_medium_tokens`
- [ ] Build `consolidate_vision_documents()` trigger (document change → re-summarize)
- [ ] Update `get_vision_document()` to fetch from consolidated columns
- [ ] Update mission_planner to use consolidated summaries
- [ ] Add regeneration button to Product card UI
- **Effort**: ~1 day

---

## Phase 2: LLM-Based Field Extraction (FUTURE)

**Note**: Sumy can't extract/infer structured fields. Requires LLM.

**Separate Feature**: Auto-suggest tech_stack, features, architecture from vision documents.
- Not summarization (Phase 1)
- Requires Qwen2.5-0.5B or Claude Haiku
- Stores as **suggestions** in product card, not canonical until user clicks "Apply"

**Status**: Design complete, deferred until Phase 1 complete

---

## Phase 3: LLM Summarization (LATER)

Current sumy LSA extractive summarizer underperforms:
- 2/6 documents have **identical** light/medium summaries (bug)
- Target ratios not achieved: Light should be 33%, Medium 66%
- Actual compression ranges from 43-92% (inconsistent)
- Technical documents with bullet points, code blocks, headers cause issues

### Evidence

| Document | Light % | Medium % | Status |
|----------|---------|----------|--------|
| product_proposal | 43% | 72% | OK |
| Ch7_9 | 65% | 90% | Weak |
| Ch1_4 | 92% | 92% | **IDENTICAL** |
| HWMonitor | 92% | 92% | **IDENTICAL** |

## Phase 3 Proposed Solution: Hybrid LLM Architecture

### Architecture

```
Document Upload
      │
      ▼
┌─────────────────┐
│ Is API enabled? │──Yes──► Claude Haiku (~$0.002/doc)
└────────┬────────┘
         │ No
         ▼
┌─────────────────┐
│ Queue < 3 docs? │──Yes──► Qwen2.5-0.5B local (5-10 sec)
└────────┬────────┘
         │ No (queue full)
         ▼
    Return to queue
    (process sequentially)
```

### Model Options (CPU-only, no GPU)

| Model | Size | CPU Time | Quality | Notes |
|-------|------|----------|---------|-------|
| SmolLM-360M | 360MB | 3-5 sec | Basic | Fastest |
| Qwen2.5-0.5B (GGUF) | 500MB | 5-10 sec | Good | Recommended |
| TinyLlama-1.1B | 1.1GB | 10-20 sec | Good | Backup |

### External API Option

- Claude Haiku: ~$0.002/doc, 1-2 sec, unlimited concurrency
- Configured via settings (API key optional)
- Fallback for hosted deployments without local compute

## Implementation Plan

### Phase 1: Local LLM Integration
1. Add `llama-cpp-python` dependency
2. Download Qwen2.5-0.5B-Instruct GGUF model
3. Create `LLMSummarizer` class alongside existing `VisionDocumentSummarizer`
4. Implement prompt template for 33%/66% summarization

### Phase 2: Queue & Concurrency
1. Add asyncio semaphore for CPU protection
2. Implement summarization queue
3. Sequential processing (1 doc at a time on CPU)
4. Progress feedback via WebSocket

### Phase 3: API Fallback
1. Add Haiku API integration (optional)
2. Settings UI for API key configuration
3. Auto-fallback when queue exceeds threshold

### Phase 4: Migration
1. Re-summarize existing documents with new engine
2. Add "Regenerate Summaries" button in Product Details
3. Deprecate sumy (keep as fallback for edge cases)

## Constraints

- **CPU-only**: Target machine is 5800X3D + 32GB RAM (no GPU)
- **Hosted servers**: May not have GPU, need API fallback option
- **Concurrency**: Multiple users may upload simultaneously
- **Offline support**: Local LLM must work without internet

## Success Criteria

- [ ] Light summaries consistently ~33% of original
- [ ] Medium summaries consistently ~66% of original
- [ ] No identical light/medium outputs
- [ ] Processing time <15 sec per document on 5800X3D
- [ ] Queue prevents CPU overload with concurrent uploads

## Related Files

- `src/giljo_mcp/services/vision_summarizer.py` - Current implementation
- `tests/services/test_vision_summarizer_simplified.py` - Test suite
- `api/endpoints/vision_documents.py` - Upload endpoint

## References

- Handover 0246b: Simplified summarization levels (light/medium/full)
- Handover 0374: Vision summary field migration
