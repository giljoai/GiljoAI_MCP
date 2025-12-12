# Handover 0345e: Sumy Semantic Compression Levels

**Date:** 2025-12-12
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor + Frontend Tester
**Priority:** High
**Estimated Complexity:** 2-3 days
**Status:** Ready for Implementation

---

## Task Summary

Implement semantic compression levels for vision documents using Sumy LSA summarization. Replace arbitrary token-based truncation with meaningful compression tiers that preserve document coherence. Remove the Sumy toggle from UI (make it always available) and integrate compression levels into the Context configuration tab.

**Why it's important:** Current Light/Moderate depth options arbitrarily cut tokens mid-sentence, losing critical context. A single 25K token summary doesn't provide flexibility. Users need semantic compression that preserves meaning at multiple levels.

**Expected outcome:** Four vision depth levels (Light/Moderate/Heavy/Full) with semantic compression, Sumy integrated by default (no toggle needed), and orchestrators receive appropriately compressed vision content based on user configuration.

---

## Problem Statement

### Current Issues

1. **Arbitrary Token Truncation**
   - Light/Moderate depth options cut tokens at arbitrary boundaries
   - Loses context randomly (sentences chopped mid-word)
   - No semantic understanding of content importance

2. **Single Summary Level**
   - Handover 0345b implemented one 25K token summary
   - Doesn't provide flexibility for different use cases
   - All-or-nothing approach (full document or single summary)

3. **Unnecessary Toggle**
   - Sumy LSA is CPU-based, fast (<5 sec), and has no cost
   - No reason to make it optional
   - Toggle adds UI complexity without benefit

4. **Inconsistent with Context Philosophy**
   - Other context fields have multiple depth levels (Tech Stack, Architecture, Testing)
   - Vision documents should follow same pattern
   - Priority × Depth model should apply uniformly

### Impact

- Orchestrators receive truncated, incoherent vision content
- Users can't fine-tune context budget vs completeness trade-off
- Confusion about when/why to enable Sumy toggle

---

## Solution Overview

### Architecture

Replace toggle-based summarization with integrated compression levels:

```
┌─────────────────────────────────────────────────────────────┐
│ Vision Document Upload Pipeline                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Upload → Chunk → Store original chunks                   │
│ 2. Generate 3 summaries (Light/Moderate/Heavy) via Sumy LSA │
│ 3. Store all 3 summaries in DB (or compute on-demand)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Context Retrieval (get_orchestrator_instructions)           │
├─────────────────────────────────────────────────────────────┤
│ User selects depth → Return corresponding summary or full   │
│  - Light: 5K tokens (~250 sentences)                        │
│  - Moderate: 12.5K tokens (~625 sentences)                  │
│  - Heavy: 25K tokens (~1,250 sentences)                     │
│  - Full: All original chunks (paginated if needed)          │
└─────────────────────────────────────────────────────────────┘
```

### Compression Levels (Semantic Tiers)

| Level    | Target Tokens | Sentences | Compression | Description                  |
|----------|---------------|-----------|-------------|------------------------------|
| Light    | 5,000         | ~250      | 87%         | Key points only              |
| Moderate | 12,500        | ~625      | 69%         | Balanced overview            |
| Heavy    | 25,000        | ~1,250    | 37%         | Detailed summary             |
| Full     | All           | All       | 0%          | Complete document (original) |

**Compression Calculation**: Assuming average vision document is ~40K tokens (based on handover 0345b context).

### UI Changes

#### Remove Sumy Toggle (Integrations Tab)

**DELETE**: `frontend/src/components/settings/integrations/VisionSummarizationCard.vue`

**REPLACE WITH**: Static info card in Integrations tab:

```vue
<!-- Info Card: Vision Document Summarization -->
<v-card outlined class="mb-4">
  <v-card-title class="text-subtitle-1">
    <v-icon left color="primary">mdi-file-document-outline</v-icon>
    Vision Document Summarization
  </v-card-title>
  <v-card-text>
    <v-alert type="info" variant="tonal" density="compact">
      Vision documents are automatically compressed using Sumy LSA (Latent Semantic Analysis)
      extractive summarization. Configure compression levels in
      <strong>Context → Depth Configuration → Vision Documents</strong>.
    </v-alert>
    <v-list density="compact">
      <v-list-item>
        <v-list-item-title>Compression Levels</v-list-item-title>
        <v-list-item-subtitle>
          Light (5K tokens), Moderate (12.5K), Heavy (25K), Full (all)
        </v-list-item-subtitle>
      </v-list-item>
      <v-list-item>
        <v-list-item-title>Algorithm</v-list-item-title>
        <v-list-item-subtitle>
          LSA extractive summarization (CPU-based, fast, no hallucination)
        </v-list-item-subtitle>
      </v-list-item>
      <v-list-item>
        <v-list-item-title>Processing Time</v-list-item-title>
        <v-list-item-subtitle>
          ~5 seconds for 100K token documents
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-card-text>
</v-card>
```

#### Update Context Tab (Depth Configuration)

**MODIFY**: `frontend/src/components/settings/ContextPriorityConfig.vue`

**Current** (Vision Documents):
```vue
<!-- Vision Documents: Light/Moderate/Heavy -->
<v-select
  :items="[
    { title: 'None', value: 'none' },
    { title: 'Light', value: 'light' },
    { title: 'Moderate', value: 'moderate' },
    { title: 'Heavy', value: 'heavy' }
  ]"
  v-model="depthConfig.vision_documents"
  label="Vision Documents"
/>
```

**Updated** (with token counts):
```vue
<!-- Vision Documents: Light/Moderate/Heavy/Full with Token Counts -->
<v-select
  :items="[
    { title: 'None', value: 'none', subtitle: '0 tokens' },
    { title: 'Light (5K tokens)', value: 'light', subtitle: '~250 sentences, 87% compression' },
    { title: 'Moderate (12.5K tokens)', value: 'moderate', subtitle: '~625 sentences, 69% compression' },
    { title: 'Heavy (25K tokens)', value: 'heavy', subtitle: '~1,250 sentences, 37% compression' },
    { title: 'Full (All)', value: 'full', subtitle: 'Complete document, no compression' }
  ]"
  v-model="depthConfig.vision_documents"
  label="Vision Documents"
  hint="Semantic compression using LSA extractive summarization"
  persistent-hint
/>
```

---

## Implementation Plan

### Phase 1: Backend - Multi-Level Summarization

#### Decision: Pre-compute vs On-Demand

**Option A: Pre-compute at Upload** (RECOMMENDED)
- **Pros**: Instant retrieval, predictable performance, better UX
- **Cons**: 3x storage space, longer upload time (~15 sec for 100K tokens)

**Option B: Compute On-Demand**
- **Pros**: Minimal storage, flexible targeting
- **Cons**: Slower retrieval, unpredictable latency, cache complexity

**RECOMMENDATION**: Pre-compute at upload. Storage is cheap, UX is critical.

#### Files to Modify

**1. `src/giljo_mcp/models/products.py`**

Add summary columns to `VisionDocument` model:

```python
class VisionDocument(Base):
    __tablename__ = "vision_documents"

    # ... existing fields ...

    # Existing from 0345b
    summary_text = Column(Text, nullable=True)  # DEPRECATE - was for 25K only
    is_summarized = Column(Boolean, default=False, nullable=False)
    original_token_count = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)  # DEPRECATE - per-level now

    # NEW: Multi-level summaries
    summary_light = Column(Text, nullable=True)       # 5K tokens (~250 sentences)
    summary_moderate = Column(Text, nullable=True)    # 12.5K tokens (~625 sentences)
    summary_heavy = Column(Text, nullable=True)       # 25K tokens (~1,250 sentences)
    summary_light_tokens = Column(Integer, nullable=True)
    summary_moderate_tokens = Column(Integer, nullable=True)
    summary_heavy_tokens = Column(Integer, nullable=True)
```

**Migration Strategy**: Nullable columns, safe for existing data. Run `python install.py` to apply.

**2. `src/giljo_mcp/services/vision_summarizer.py`**

Add multi-level summarization support:

```python
class VisionDocumentSummarizer:
    """CPU-based extractive summarizer using LSA algorithm."""

    # ... existing __init__ ...

    def summarize_multi_level(
        self,
        text: str,
        levels: dict = None
    ) -> dict:
        """
        Generate multiple summary levels in one pass.

        Args:
            text: Full document text
            levels: Target token counts per level
                    Default: {"light": 5000, "moderate": 12500, "heavy": 25000}

        Returns:
            {
                "light": {"summary": str, "tokens": int, "sentences": int},
                "moderate": {"summary": str, "tokens": int, "sentences": int},
                "heavy": {"summary": str, "tokens": int, "sentences": int},
                "original_tokens": int,
                "processing_time_ms": int
            }
        """
        if levels is None:
            levels = {
                "light": 5000,
                "moderate": 12500,
                "heavy": 25000
            }

        start_time = time.time()
        results = {}

        # Generate summaries in descending order (heavy → moderate → light)
        # Optimization: Use previous summary as input for next level
        previous_text = text
        for level in ["heavy", "moderate", "light"]:
            target_tokens = levels[level]
            result = self.summarize(previous_text, target_tokens=target_tokens)
            results[level] = {
                "summary": result["summary"],
                "tokens": result["summary_tokens"],
                "sentences": len(result["summary"].split('.'))
            }
            previous_text = result["summary"]  # Cascade for efficiency

        results["original_tokens"] = self.estimate_tokens(text)
        results["processing_time_ms"] = int((time.time() - start_time) * 1000)

        return results
```

**3. `src/giljo_mcp/services/product_service.py`**

Update `upload_vision_document()` to generate all three levels:

```python
async def upload_vision_document(
    self,
    product_id: UUID,
    document_data: dict,
    tenant_key: str
) -> VisionDocument:
    # ... existing chunking logic ...

    # NEW: Always generate multi-level summaries (no toggle check)
    if total_tokens > 5000:  # Only summarize if document is large enough
        summarizer = VisionDocumentSummarizer()
        summaries = summarizer.summarize_multi_level(full_text)

        # Store all three levels
        vision_doc.summary_light = summaries["light"]["summary"]
        vision_doc.summary_moderate = summaries["moderate"]["summary"]
        vision_doc.summary_heavy = summaries["heavy"]["summary"]
        vision_doc.summary_light_tokens = summaries["light"]["tokens"]
        vision_doc.summary_moderate_tokens = summaries["moderate"]["tokens"]
        vision_doc.summary_heavy_tokens = summaries["heavy"]["tokens"]
        vision_doc.is_summarized = True
        vision_doc.original_token_count = summaries["original_tokens"]

        logger.info(
            f"Generated multi-level summaries for vision doc {vision_doc.id}: "
            f"Light={summaries['light']['tokens']} tokens, "
            f"Moderate={summaries['moderate']['tokens']} tokens, "
            f"Heavy={summaries['heavy']['tokens']} tokens"
        )

    # ... existing storage logic ...
```

**4. `src/giljo_mcp/mission_planner.py`**

Update `_build_context_with_priorities()` to use depth configuration:

```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict,
    user_id: str,
) -> str:
    # ... existing context building ...

    # Vision Documents: Use depth configuration
    vision_depth = depth_config.get("vision_documents", "moderate")  # Default to moderate

    if vision_depth != "none" and product_has_vision:
        async with self.db_manager.get_session_async() as session:
            # Fetch appropriate summary level or full document
            if vision_depth == "full":
                # Fetch all original chunks (existing logic)
                vision_chunks = await self._get_relevant_vision_chunks(
                    session=session,
                    product=product,
                    project=project,
                    max_tokens=None,  # All chunks
                )
                vision_text = "\n\n".join([chunk.content for chunk in vision_chunks])
            else:
                # Fetch pre-computed summary
                stmt = select(VisionDocument).where(
                    VisionDocument.product_id == product.id,
                    VisionDocument.tenant_key == product.tenant_key
                )
                result = await session.execute(stmt)
                vision_doc = result.scalar_one_or_none()

                if vision_doc and vision_doc.is_summarized:
                    if vision_depth == "light":
                        vision_text = vision_doc.summary_light
                    elif vision_depth == "moderate":
                        vision_text = vision_doc.summary_moderate
                    elif vision_depth == "heavy":
                        vision_text = vision_doc.summary_heavy
                    else:
                        vision_text = vision_doc.summary_moderate  # Fallback
                else:
                    # No summaries available - fallback to chunks
                    vision_chunks = await self._get_relevant_vision_chunks(
                        session=session,
                        product=product,
                        project=project,
                        max_tokens=15000,  # Conservative fallback
                    )
                    vision_text = "\n\n".join([chunk.content for chunk in vision_chunks])

            if vision_text:
                context_parts.append(f"## Vision Documents\n\n{vision_text}")

    # ... rest of context building ...
```

### Phase 2: Frontend - Remove Toggle, Update Depth Selector

#### Files to Modify

**5. DELETE: `frontend/src/components/settings/integrations/VisionSummarizationCard.vue`**

Remove entire component (toggle no longer needed).

**6. MODIFY: `frontend/src/views/UserSettings.vue`**

Remove all references to VisionSummarizationCard:

```javascript
// DELETE these state variables (around line 336)
const visionSummarizationEnabled = ref(false)
const togglingVisionSummarization = ref(false)

// DELETE these methods (around line 477)
async function checkVisionSummarizationStatus() { ... }
async function toggleVisionSummarization(newValue) { ... }

// DELETE component import
import VisionSummarizationCard from '@/components/settings/integrations/VisionSummarizationCard.vue'
```

Add static info card in template:

```vue
<!-- In Integrations tab, after GitIntegrationCard -->
<!-- Vision Document Summarization Info -->
<v-card outlined class="mb-4">
  <v-card-title class="text-subtitle-1">
    <v-icon left color="primary">mdi-file-document-outline</v-icon>
    Vision Document Summarization
  </v-card-title>
  <v-card-text>
    <v-alert type="info" variant="tonal" density="compact">
      Vision documents are automatically compressed using Sumy LSA (Latent Semantic Analysis)
      extractive summarization. Configure compression levels in
      <strong>Context → Depth Configuration → Vision Documents</strong>.
    </v-alert>
    <v-list density="compact">
      <v-list-item>
        <v-list-item-title>Compression Levels</v-list-item-title>
        <v-list-item-subtitle>
          Light (5K tokens), Moderate (12.5K), Heavy (25K), Full (all)
        </v-list-item-subtitle>
      </v-list-item>
      <v-list-item>
        <v-list-item-title>Algorithm</v-list-item-title>
        <v-list-item-subtitle>
          LSA extractive summarization (CPU-based, fast, no hallucination)
        </v-list-item-subtitle>
      </v-list-item>
      <v-list-item>
        <v-list-item-title>Processing Time</v-list-item-title>
        <v-list-item-subtitle>
          ~5 seconds for 100K token documents
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-card-text>
</v-card>
```

**7. MODIFY: `frontend/src/components/settings/ContextPriorityConfig.vue`**

Update Vision Documents depth selector:

```vue
<!-- Vision Documents Depth Selector -->
<v-select
  :items="[
    { title: 'None', value: 'none', subtitle: '0 tokens' },
    { title: 'Light (5K tokens)', value: 'light', subtitle: '~250 sentences, 87% compression' },
    { title: 'Moderate (12.5K tokens)', value: 'moderate', subtitle: '~625 sentences, 69% compression' },
    { title: 'Heavy (25K tokens)', value: 'heavy', subtitle: '~1,250 sentences, 37% compression' },
    { title: 'Full (All)', value: 'full', subtitle: 'Complete document, no compression' }
  ]"
  v-model="depthConfig.vision_documents"
  label="Vision Documents"
  hint="Semantic compression using LSA extractive summarization"
  persistent-hint
  item-title="title"
  item-value="value"
>
  <!-- Custom item slot for subtitles -->
  <template v-slot:item="{ item, props }">
    <v-list-item v-bind="props">
      <v-list-item-title>{{ item.title }}</v-list-item-title>
      <v-list-item-subtitle>{{ item.subtitle }}</v-list-item-subtitle>
    </v-list-item>
  </template>
</v-select>
```

### Phase 3: Testing

#### Unit Tests

**Create**: `tests/services/test_vision_summarizer_multi_level.py`

```python
import pytest
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

class TestMultiLevelSummarization:
    """Test suite for multi-level semantic compression."""

    def test_summarize_multi_level_returns_three_summaries(self):
        """Should generate light, moderate, and heavy summaries."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        assert "light" in result
        assert "moderate" in result
        assert "heavy" in result
        assert result["light"]["tokens"] <= 6000  # Allow 20% tolerance
        assert result["moderate"]["tokens"] <= 15000
        assert result["heavy"]["tokens"] <= 30000

    def test_light_is_subset_of_moderate_is_subset_of_heavy(self):
        """Cascading summaries should preserve hierarchy."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        # Light should be shortest, heavy should be longest
        assert result["light"]["tokens"] < result["moderate"]["tokens"]
        assert result["moderate"]["tokens"] < result["heavy"]["tokens"]

    def test_multi_level_processing_time_under_15_seconds(self):
        """Generating 3 summaries should take <15 sec for 100K tokens."""
        import time
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=100000)

        start = time.time()
        result = summarizer.summarize_multi_level(text)
        elapsed = time.time() - start

        assert elapsed < 15.0
        assert result["processing_time_ms"] < 15000

    def test_upload_stores_three_summaries(self):
        """Upload should populate all three summary columns."""
        # Mock: Upload 50K token document
        # Verify: vision_doc.summary_light populated
        # Verify: vision_doc.summary_moderate populated
        # Verify: vision_doc.summary_heavy populated
        # Verify: Token counts match targets (±20%)
        pass

    def test_orchestrator_instructions_respects_depth_config(self):
        """Should return appropriate summary based on depth setting."""
        # Mock depth_config: {"vision_documents": "light"}
        # Call get_orchestrator_instructions
        # Verify: Response contains summary_light content
        # Verify: Response does NOT contain full document
        pass

    def test_full_depth_returns_original_chunks(self):
        """'Full' depth should bypass summaries and return original."""
        # Mock depth_config: {"vision_documents": "full"}
        # Call get_orchestrator_instructions
        # Verify: Response contains original chunks (not summaries)
        pass
```

#### Integration Tests

**Create**: `tests/integration/test_vision_compression_e2e.py`

```python
import pytest
from httpx import AsyncClient

class TestVisionCompressionE2E:
    """End-to-end tests for semantic compression pipeline."""

    @pytest.mark.asyncio
    async def test_upload_vision_document_generates_all_summaries(
        self, client: AsyncClient, auth_headers, test_product
    ):
        """Upload should auto-generate 3 summary levels."""
        large_document = generate_test_document(tokens=50000)

        response = await client.post(
            f"/api/products/{test_product['id']}/vision-documents",
            json={
                "title": "Large Vision Doc",
                "content": large_document
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        vision_doc = response.json()
        assert vision_doc["is_summarized"] is True
        assert vision_doc["summary_light_tokens"] > 0
        assert vision_doc["summary_moderate_tokens"] > 0
        assert vision_doc["summary_heavy_tokens"] > 0

    @pytest.mark.asyncio
    async def test_context_depth_setting_affects_orchestrator_instructions(
        self, client: AsyncClient, auth_headers, test_project
    ):
        """Depth setting should control which summary is returned."""
        # Set depth to "light"
        await client.put(
            "/api/settings/context",
            json={"depth_config": {"vision_documents": "light"}},
            headers=auth_headers
        )

        # Get orchestrator instructions
        response = await client.get(
            f"/api/mcp/orchestrator-instructions/{test_project['id']}",
            headers=auth_headers
        )

        instructions = response.json()
        # Should contain light summary (not moderate/heavy/full)
        assert "vision" in instructions.lower()
        # Verify token count is ~5K (light level)
        estimated_tokens = len(instructions) // 4
        assert 4000 <= estimated_tokens <= 7000
```

#### Manual Testing Checklist

1. **Upload Large Vision Document** (50K+ tokens)
   - Verify upload completes in <20 seconds
   - Check database for three summary columns populated:
     ```bash
     PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp \
       -c "SELECT id, is_summarized, summary_light_tokens, summary_moderate_tokens, summary_heavy_tokens FROM vision_documents WHERE is_summarized=true LIMIT 5;"
     ```

2. **Verify Integrations Tab**
   - Navigate to My Settings → Integrations
   - Confirm static info card present (no toggle)
   - Verify text explains compression levels

3. **Verify Context Tab**
   - Navigate to My Settings → Context → Depth Configuration
   - Locate Vision Documents selector
   - Confirm 5 options: None, Light (5K), Moderate (12.5K), Heavy (25K), Full
   - Select each option and save → verify no errors

4. **Test Orchestrator Context Retrieval**
   - Set depth to "Light" → stage orchestrator → verify instructions contain ~5K token vision content
   - Set depth to "Heavy" → stage orchestrator → verify instructions contain ~25K token vision content
   - Set depth to "Full" → stage orchestrator → verify instructions contain full original chunks
   - Set depth to "None" → stage orchestrator → verify no vision content

5. **Performance Benchmark**
   - Upload 100K token document
   - Measure time from upload start to completion
   - Should complete in <30 seconds (3 summaries + storage)

---

## Testing Requirements

### Unit Tests Coverage
- `VisionDocumentSummarizer.summarize_multi_level()` - 6 test cases
- `ProductService.upload_vision_document()` - 3 test cases (multi-level storage)
- `MissionPlanner._build_context_with_priorities()` - 4 test cases (depth config)

**Target**: >90% coverage for modified services

### Integration Tests
- Upload → summarize → store pipeline
- Context depth configuration → retrieval mapping
- Edge cases: Small docs (<5K tokens), empty docs, full depth mode

### Performance Tests
- 100K token document → 3 summaries in <30 seconds
- Memory usage stays under 500MB during processing
- Database queries optimized (single query per depth level)

---

## Dependencies and Blockers

### Dependencies
- **Handover 0345a** (Lean Orchestrator Instructions): Not strictly required, but recommended to complete first to reduce orchestrator context bloat
- **Handover 0345b** (Sumy LSA Integration): MUST be complete - provides `VisionDocumentSummarizer` class

### External Dependencies
- `sumy>=0.11.0` (already added in 0345b)
- `nltk>=3.8` (already added in 0345b)
- NLTK data: punkt, stopwords (already configured in 0345b)

### Known Blockers
- **Handover 0345c** conflicts: This handover supersedes parts of 0345c (Sumy toggle). Coordinate implementation order:
  - If 0345c complete: Remove VisionSummarizationCard, keep depth selector updates
  - If 0345c not started: Implement this handover first, skip 0345c toggle logic

---

## Success Criteria

### Definition of Done
- [ ] Database schema updated with 3 new summary columns + token counts
- [ ] `VisionDocumentSummarizer.summarize_multi_level()` implemented and tested
- [ ] `upload_vision_document()` generates all 3 summary levels automatically
- [ ] `_build_context_with_priorities()` uses depth config to select summary
- [ ] VisionSummarizationCard.vue deleted (or never created)
- [ ] UserSettings.vue shows static info card (no toggle)
- [ ] ContextPriorityConfig.vue updated with 5 depth options
- [ ] All 13 unit tests passing
- [ ] All 2 integration tests passing
- [ ] Manual testing checklist completed (5 scenarios)
- [ ] Performance benchmark: <30 sec for 100K tokens (3 summaries)
- [ ] Documentation updated (CLAUDE.md, docs/context-management/)

### Quality Gates
- Compression ratios match targets (±10%):
  - Light: 87% ± 10% = 77-97%
  - Moderate: 69% ± 10% = 59-79%
  - Heavy: 37% ± 10% = 27-47%
- Zero hallucination (extractive only - all sentences from original)
- Summaries are coherent and semantically meaningful
- No performance regression (upload <30 sec for 100K tokens)
- Backward compatible (existing vision docs still retrievable)

---

## Rollback Plan

### If Things Go Wrong

**Scenario 1: Summaries are poor quality**
- Check compression targets (may need adjustment)
- Review LSA parameters (sentence count, chunk size)
- Fallback: Use "full" depth mode (bypasses summaries)

**Scenario 2: Upload time too long (>30 sec)**
- Profile bottleneck (summarization vs database writes)
- Consider on-demand generation instead of pre-compute
- Implement async job queue for large documents

**Scenario 3: Database migration issues**
- Columns are nullable - safe to rollback
- Drop columns manually:
  ```sql
  ALTER TABLE vision_documents
    DROP COLUMN summary_light,
    DROP COLUMN summary_moderate,
    DROP COLUMN summary_heavy,
    DROP COLUMN summary_light_tokens,
    DROP COLUMN summary_moderate_tokens,
    DROP COLUMN summary_heavy_tokens;
  ```

**Scenario 4: Context retrieval broken**
- Revert `mission_planner.py` changes
- Fallback to original chunking logic (fetch all chunks)

**Revert Code**:
```bash
git revert <commit-hash>
python install.py  # Reapply migrations if needed
git push
```

---

## Additional Resources

### Documentation
- **Handover 0345b**: Sumy LSA integration (prerequisite - provides VisionDocumentSummarizer)
- **Handover 0345a**: Lean orchestrator instructions (context for vision content optimization)
- **Handover 0338**: CPU-based summarization research (LSA algorithm reference)
- **Handover 0336**: Vision chunking architecture (original chunking system)
- **Context Management v2.0 Docs**: `docs/context-management/` (priority × depth model)

### Code References
- `src/giljo_mcp/services/vision_summarizer.py` - Summarization service
- `src/giljo_mcp/services/product_service.py` (lines 1117-1239) - Upload handler
- `src/giljo_mcp/mission_planner.py` (lines 1327-1412) - Context building
- `src/giljo_mcp/models/products.py` - VisionDocument schema
- `frontend/src/components/settings/ContextPriorityConfig.vue` - Depth selector UI

### Testing Tools
- `pytest` - Unit and integration testing
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `psql` - Database verification

---

## Recommended Agents

**Primary**: `tdd-implementor`
- Write failing tests first (test-driven development)
- Implement minimal code to pass tests
- Refactor for quality and performance
- 13 unit tests + 2 integration tests

**Secondary**: `frontend-tester`
- Remove VisionSummarizationCard component
- Update UserSettings.vue (static info card)
- Update ContextPriorityConfig.vue (5 depth options)
- Verify UI flows and visual consistency

**Tertiary**: `database-expert` (if needed)
- Review schema changes (3 new columns + token counts)
- Optimize queries for depth-based retrieval
- Verify migration idempotency
- Performance tuning for large documents

---

## Implementation Checklist

### Before Starting
- [ ] Git status clean
- [ ] Handover 0345b completed (VisionDocumentSummarizer exists)
- [ ] Reviewed 0338 LSA reference implementation
- [ ] Confirmed 0345c toggle logic NOT implemented (or ready to remove)
- [ ] Test database backup created

### Phase 1: Backend (TDD Implementor)
- [ ] Database schema updated (3 summary columns + token counts)
- [ ] `VisionDocumentSummarizer.summarize_multi_level()` implemented
- [ ] Unit tests written and passing (6 tests)
- [ ] `upload_vision_document()` updated to generate 3 summaries
- [ ] `_build_context_with_priorities()` uses depth config
- [ ] Integration tests written and passing (2 tests)

### Phase 2: Frontend (Frontend Tester)
- [ ] VisionSummarizationCard.vue deleted (if exists)
- [ ] UserSettings.vue updated (static info card, toggle removed)
- [ ] ContextPriorityConfig.vue updated (5 depth options with subtitles)
- [ ] UI tested in browser (5 manual scenarios)
- [ ] Visual consistency verified (Vuetify design system)

### Phase 3: Validation
- [ ] All 15 tests passing (13 unit + 2 integration)
- [ ] Performance benchmark met (<30 sec for 100K tokens)
- [ ] Manual testing completed (5 scenarios)
- [ ] Database queries verified
- [ ] Documentation updated

### After Completion
- [ ] Code committed with message: `feat(0345e): Add Sumy semantic compression levels`
- [ ] Completion summary added to this handover
- [ ] User notified with summary (400-word limit)
- [ ] Handover moved to `completed/` with `-C` suffix
- [ ] HANDOVER_CATALOGUE.md updated

---

## Questions for User (Resolve Before Implementation)

1. **Storage Strategy Confirmed?**
   - Pre-compute 3 summaries at upload time (RECOMMENDED)
   - OR compute on-demand (slower retrieval, less storage)

2. **Token Targets Appropriate?**
   - Light: 5K tokens (~250 sentences)
   - Moderate: 12.5K tokens (~625 sentences)
   - Heavy: 25K tokens (~1,250 sentences)
   - Adjustments needed based on typical vision doc sizes?

3. **Default Depth Level?**
   - Currently defaults to "moderate" in mission_planner.py
   - Should this be user-configurable in settings?

4. **Deprecate Old Fields?**
   - Keep `summary_text` and `compression_ratio` from 0345b for backward compatibility?
   - OR migrate existing data to new schema and remove old columns?

5. **UI Info Card Wording?**
   - Current wording OK or needs adjustment for clarity?
   - Should we add link to documentation?

---

**Handover Status**: Ready for implementation after 0345b completion. Supersedes Sumy toggle logic from 0345c.

---

## Completion Summary

**Completed:** 2025-12-12
**Agent:** TDD Implementor + Frontend Tester (subagents)
**Commits:** 140ae9af, e84ef654, 23321f9c, 946b857e8eb1 (migration)

### What Was Built
- Multi-level semantic compression: Light (5K), Moderate (12.5K), Heavy (25K), Full
- `summarize_multi_level()` method with cascading compression
- Database columns for three summary levels
- Updated depth selector with meaningful compression options
- Removed Sumy toggle (now always available)

### Key Files Modified
- `src/giljo_mcp/services/vision_summarizer.py`
  - Added `summarize_multi_level()` method (lines 226-318)
  - Cascading compression: heavy → moderate → light
  - Returns all three summaries in one pass
- `src/giljo_mcp/models/products.py` - Added 6 columns:
  - `summary_light`, `summary_moderate`, `summary_heavy`
  - `summary_light_tokens`, `summary_moderate_tokens`, `summary_heavy_tokens`
- `src/giljo_mcp/services/product_service.py`
  - Upload now generates all 3 summary levels automatically
  - Threshold lowered from 30K to 5K tokens
- `src/giljo_mcp/mission_planner.py`
  - `_build_context_with_priorities()` now retrieves appropriate summary based on depth config
- `frontend/src/views/UserSettings.vue`
  - Removed toggle, added static info card
  - Deleted VisionSummarizationCard import
- `frontend/src/components/settings/ContextPriorityConfig.vue`
  - Updated options: None, Light (5K), Moderate (12.5K), Heavy (25K), Full

### Database Migration
- `946b857e8eb1_add_multi_level_vision_summaries.py`
- 6 nullable columns added to `vision_documents` table

### How Depth Config Works
When orchestrator fetches instructions:
- `light` → Returns `summary_light` (~5K tokens, 250 sentences)
- `moderate` → Returns `summary_moderate` (~12.5K tokens, 625 sentences)
- `heavy` → Returns `summary_heavy` (~25K tokens, 1250 sentences)
- `full` → Returns all original chunks (fetch instructions)

### Status
✅ **COMPLETE** - All tests passing, semantic compression operational
