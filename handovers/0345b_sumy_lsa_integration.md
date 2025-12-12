# Handover: Sumy LSA Integration for Vision Document Summarization

**Date:** 2025-12-11
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor + Backend Integration Tester
**Priority:** High
**Estimated Complexity:** 1-2 days
**Status:** Not Started

---

## Task Summary

Integrate Sumy LSA (Latent Semantic Analysis) extractive summarization into the vision document upload pipeline to compress large technical documents while preserving quality. This is an **optional** CPU-based feature that achieves 70-80% compression with <5 second processing time.

**Why it's important:** Large vision documents (100K+ tokens) currently upload as full chunks. Summarization enables 3-4x content coverage within the same token budget, improving orchestrator context without hallucination risk.

**Expected outcome:** When enabled, vision documents >30K tokens are automatically summarized using LSA extractive summarization, preserving both original and summary for auditability.

---

## Context and Background

### Related Handovers
- **0345a**: Vision Summarization Admin Settings (prerequisite - settings toggle)
- **0345c**: Vision Summarization Frontend UI (follow-up - UI indicators)
- **0338**: CPU-Based Vision Summarization (research foundation)

### Architectural Context
This builds on the vision chunking system established in Handover 0336. Current state:
- Vision documents chunked into ~25K token segments
- Full context preserved at runtime
- No summarization during upload

Post-0345b state:
- Optional summarization triggered when document >30K tokens AND admin setting enabled
- Both original and summary stored in database
- Compression metrics tracked for analytics

### User Requirements
- Zero hallucination risk (extractive only - no LLM generation)
- Fast processing (<5 seconds for 100K tokens)
- Preserves technical accuracy
- Admin can toggle on/off (default: OFF to preserve current behavior)
- Original document available for retrieval

---

## Technical Details

### Dependencies

**Add to `requirements.txt`:**
```txt
sumy>=0.11.0
nltk>=3.8
```

**Size**: ~5MB install, <100MB RAM usage
**License**: Apache 2.0 (commercial use OK)

**NLTK Data** (downloaded during `install.py`):
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

### Files to Create

#### 1. `src/giljo_mcp/services/vision_summarizer.py` (NEW)

**Class**: `VisionDocumentSummarizer`

**Core Methods**:
```python
class VisionDocumentSummarizer:
    """CPU-based extractive summarizer using LSA algorithm."""

    def __init__(self, language: str = "english"):
        """Initialize LSA summarizer with stemmer and stopwords."""
        pass

    def summarize(
        self,
        text: str,
        target_tokens: int = 25000,
        chunk_size: int = 10000
    ) -> dict:
        """
        Summarize document to target token count using map-reduce LSA.

        Returns:
            {
                "summary": str,
                "original_tokens": int,
                "summary_tokens": int,
                "compression_ratio": float,
                "processing_time_ms": int
            }
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (1 token ~ 4 chars)."""
        return len(text) // 4
```

**Algorithm**: LSA (Latent Semantic Analysis) - best for technical documents, handles synonyms and implicit topics.

**Reference Implementation**: See `handovers/0338_CPU_BASED_VISION_SUMMARIZATION.md` lines 56-148 for complete code.

### Files to Modify

#### 2. `src/giljo_mcp/services/product_service.py` (lines 1117-1239)

**Current**: `upload_vision_document()` chunks document and stores chunks directly.

**Change**: Add summarization step AFTER chunking, BEFORE storage.

**Pseudocode**:
```python
async def upload_vision_document(
    self,
    product_id: UUID,
    document_data: dict,
    tenant_key: str
) -> VisionDocument:
    # ... existing chunking logic ...

    # NEW: Check if summarization enabled AND document large enough
    settings = await self._get_settings(tenant_key)
    should_summarize = (
        settings.get("vision_summarization_enabled", False) and
        total_tokens > 30000
    )

    if should_summarize:
        summarizer = VisionDocumentSummarizer()
        result = summarizer.summarize(full_text, target_tokens=25000)

        # Store BOTH original chunks AND summary
        vision_doc.summary_text = result["summary"]
        vision_doc.is_summarized = True
        vision_doc.original_token_count = result["original_tokens"]
        vision_doc.compression_ratio = result["compression_ratio"]

    # ... existing storage logic ...
```

#### 3. `src/giljo_mcp/models/products.py`

**Add to `VisionDocument` model**:
```python
class VisionDocument(Base):
    __tablename__ = "vision_documents"

    # ... existing fields ...

    # NEW: Summarization metadata
    summary_text = Column(Text, nullable=True)
    is_summarized = Column(Boolean, default=False, nullable=False)
    original_token_count = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)
```

**Migration**: Auto-applied via `install.py` - these are nullable columns, safe for existing data.

#### 4. `requirements.txt`

**Add**:
```txt
sumy>=0.11.0
nltk>=3.8
```

#### 5. `install.py` (NLTK data download)

**Add to installation flow** (after pip install):
```python
def download_nltk_data():
    """Download required NLTK data for summarization."""
    import nltk
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
```

Call during setup after dependencies installed.

---

## Implementation Plan

### Phase 1: TDD Test Suite (Test-Driven Development)

**Create**: `tests/services/test_vision_summarizer.py`

**Test Cases** (write FIRST, before implementation):

```python
def test_summarizer_achieves_70_percent_compression():
    """LSA should compress 100K tokens to ~25-30K (70%+ compression)."""
    summarizer = VisionDocumentSummarizer()
    large_text = generate_test_document(tokens=100000)

    result = summarizer.summarize(large_text, target_tokens=25000)

    assert result["original_tokens"] >= 95000
    assert result["summary_tokens"] <= 30000
    assert result["compression_ratio"] >= 0.70

def test_summarizer_preserves_key_sentences():
    """Extractive summarization must preserve original sentences exactly."""
    summarizer = VisionDocumentSummarizer()
    text = "Sentence A. Sentence B. Sentence C. Key: Sentence D."

    result = summarizer.summarize(text, target_tokens=100)

    # Summary should only contain sentences from original
    assert all(
        sentence in text
        for sentence in result["summary"].split('.')
        if sentence.strip()
    )

def test_summarizer_handles_empty_input():
    """Empty or very short documents should pass through unchanged."""
    summarizer = VisionDocumentSummarizer()

    result = summarizer.summarize("", target_tokens=1000)
    assert result["summary"] == ""

    result = summarizer.summarize("Short.", target_tokens=1000)
    assert result["summary"] == "Short."

def test_upload_stores_both_original_and_summary():
    """Upload should store both original chunks AND summary text."""
    # Mock settings: summarization enabled
    # Mock document: 50K tokens
    # Verify: vision_doc.summary_text populated
    # Verify: vision_doc.chunks still contains original
    pass

def test_summarization_only_when_enabled():
    """Summarization should NOT run if admin setting disabled."""
    # Mock settings: vision_summarization_enabled=False
    # Upload 100K token document
    # Verify: vision_doc.is_summarized == False
    # Verify: vision_doc.summary_text == None
    pass

def test_processing_time_under_5_seconds():
    """100K token document should summarize in <5 seconds."""
    import time
    summarizer = VisionDocumentSummarizer()
    large_text = generate_test_document(tokens=100000)

    start = time.time()
    result = summarizer.summarize(large_text)
    elapsed = time.time() - start

    assert elapsed < 5.0
```

**Run tests** (they should FAIL initially):
```bash
pytest tests/services/test_vision_summarizer.py -v
```

### Phase 2: Implementation

**Step 1: Create VisionDocumentSummarizer Service**
- Implement `src/giljo_mcp/services/vision_summarizer.py`
- Use Sumy LSA algorithm (reference: 0338 handover lines 56-148)
- Map-reduce chunking for large documents
- Token estimation and compression tracking

**Step 2: Integrate with ProductService**
- Modify `upload_vision_document()` in `product_service.py`
- Add summarization trigger logic (check settings + token threshold)
- Store both original chunks AND summary text

**Step 3: Update Database Schema**
- Add 4 new columns to `VisionDocument` model
- Run `python install.py` to apply migration

**Step 4: Add NLTK Data Download**
- Update `install.py` to download punkt and stopwords
- Make idempotent (check if already downloaded)

**Step 5: Run Tests Again**
- All tests in `test_vision_summarizer.py` should PASS
- Integration tests should verify end-to-end flow

### Phase 3: Integration Testing

**Create**: `tests/integration/test_vision_summarization_integration.py`

**Test Scenarios**:
1. Upload large document with summarization enabled → verify summary stored
2. Upload large document with summarization disabled → verify no summary
3. Upload small document (<30K tokens) → verify no summarization triggered
4. Retrieve summarized document → verify both original and summary available
5. Performance test: 100K token document processes in <5 seconds

**Run**:
```bash
pytest tests/integration/test_vision_summarization_integration.py -v
```

---

## Testing Requirements

### Unit Tests
- `test_vision_summarizer.py` - 6 test cases (see Phase 1)
- Coverage target: >90% for `vision_summarizer.py`

### Integration Tests
- `test_vision_summarization_integration.py` - 5 scenarios
- End-to-end upload → summarize → retrieve flow
- Performance validation (<5 sec for 100K tokens)

### Manual Testing
1. Enable "Vision Summarization" in Admin Settings (depends on 0345a)
2. Upload vision document >30K tokens
3. Verify summary stored in database:
   ```bash
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp \
     -c "SELECT id, is_summarized, original_token_count, compression_ratio FROM vision_documents WHERE is_summarized=true;"
   ```
4. Verify summary text readable and coherent
5. Disable summarization, upload again → verify no summary

### Performance Benchmark
```bash
pytest tests/services/test_vision_summarizer.py::test_processing_time_under_5_seconds -v
```

**Acceptance**: Must pass consistently (100K tokens in <5 sec)

---

## Dependencies and Blockers

### Dependencies
- **Handover 0345a**: Vision Summarization Admin Settings MUST be completed first
  - Provides `vision_summarization_enabled` setting check
  - Frontend toggle in Admin Settings

### External Dependencies
- `sumy>=0.11.0` (Apache 2.0 license)
- `nltk>=3.8` (Apache 2.0 license)
- NLTK data: punkt tokenizer, stopwords corpus (~3MB download)

### Known Blockers
None (all prerequisites available)

---

## Success Criteria

### Definition of Done
- [ ] `VisionDocumentSummarizer` class implemented with LSA algorithm
- [ ] `upload_vision_document()` integrates summarization logic
- [ ] Database schema updated with 4 new columns
- [ ] NLTK data download added to `install.py`
- [ ] All 6 unit tests passing
- [ ] All 5 integration tests passing
- [ ] Performance benchmark: <5 sec for 100K tokens
- [ ] Manual testing completed (upload → verify summary)
- [ ] Code committed with descriptive message
- [ ] Original handover updated with completion summary

### Quality Gates
- Compression ratio: 70-80% achieved consistently
- Zero hallucination (extractive only - sentences from original)
- No performance regression (<5 sec for large docs)
- Backward compatible (default OFF, nullable columns)

---

## Rollback Plan

### If Things Go Wrong

**Scenario 1: Summarization produces poor results**
- Disable feature via admin setting (toggle OFF)
- Original chunks still available, no data loss
- Investigate LSA parameters (sentence count, chunk size)

**Scenario 2: Performance issues (>5 sec)**
- Disable feature via admin setting
- Review chunking strategy (reduce chunk_size)
- Consider caching NLTK resources

**Scenario 3: Database migration fails**
- Columns are nullable - safe to rollback
- Drop columns manually:
  ```sql
  ALTER TABLE vision_documents
    DROP COLUMN summary_text,
    DROP COLUMN is_summarized,
    DROP COLUMN original_token_count,
    DROP COLUMN compression_ratio;
  ```

**Revert Code**:
```bash
git revert <commit-hash>
git push
```

---

## Additional Resources

### Documentation
- **Handover 0338**: Complete LSA implementation reference (lines 56-148)
- **Handover 0336**: Vision chunking context
- **Sumy Docs**: https://github.com/miso-belica/sumy

### Code References
- `src/giljo_mcp/services/product_service.py` (lines 1117-1239) - Upload handler
- `src/giljo_mcp/models/products.py` - VisionDocument schema

### Testing Tools
- `pytest` - Unit and integration testing
- `pytest-cov` - Coverage reporting
- `psql` - Database verification

---

## Recommended Sub-Agent

**Primary**: `tdd-implementor` - Specializes in test-driven development
- Write failing tests first
- Implement minimal code to pass
- Refactor for quality

**Secondary**: `backend-integration-tester` - End-to-end validation
- Integration test scenarios
- Performance benchmarking
- Database verification

**Tertiary**: `database-expert` - Schema review (if needed)
- Verify migration idempotency
- Optimize column types
- Index recommendations

---

## Implementation Checklist

### Before Starting
- [ ] Git status checked and clean
- [ ] Handover 0345a completed (admin settings)
- [ ] Reviewed 0338 reference implementation
- [ ] TDD Implementor agent profile reviewed
- [ ] Test database backup created

### During Implementation
- [ ] NLTK dependencies added to `requirements.txt`
- [ ] `VisionDocumentSummarizer` class created
- [ ] All 6 unit tests written (and failing)
- [ ] Implementation coded to pass tests
- [ ] Database schema updated
- [ ] `install.py` updated with NLTK download
- [ ] Integration tests written and passing
- [ ] Manual testing completed

### After Completion
- [ ] All tests passing (unit + integration)
- [ ] Performance benchmark met (<5 sec)
- [ ] Code committed with message: `feat(0345b): Add Sumy LSA vision summarization`
- [ ] Completion summary added to this handover (max 1000 words)
- [ ] User notified with 400-word summary
- [ ] Handover moved to `completed/` with `-C` suffix

---

## Questions for User (Resolve Before Implementation)

1. **Storage Strategy**: Confirmed to store BOTH original chunks AND summary?
2. **UI Indicator**: Should 0345c add visual indicator showing document was summarized?
3. **Threshold**: 30K tokens trigger OK, or make configurable in settings?
4. **Analytics**: Track compression metrics in Product memory for orchestrator context?

---

**Handover Status**: Ready for implementation after 0345a completion.
