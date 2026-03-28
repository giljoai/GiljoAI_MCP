# Handover 0842g: Per-Document AI Summary Badges

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** tdd-implementor + ux-designer
**Priority:** Medium
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Standalone handover** (follow-up to 0842d deviation #2)
**Depends on:** 0842a (summaries table), 0842c (MCP write tool)

---

## Task Summary

Add per-document AI summary badges to the vision document cards in `ProductDetailsDialog.vue`, matching the wireframe (`FLow_vision_doc3.png`). Currently only Sumy summary chips are shown. After AI analysis, a second row of badges should appear: `AI summaries: ✅ 33% (4,200 tokens) · ✅ 66% (10,800)`.

---

## Why This Was Deferred

The 0842d agent noted this would require API changes to include summary source data in the vision document list response. The `VisionDocumentResponse` schema only returns Sumy columns from the `vision_documents` table — it has no knowledge of the `vision_document_summaries` table where AI summaries live.

---

## Technical Details

### Backend Changes

**1. Extend `VisionDocumentResponse` schema**

File: `api/schemas/vision_document.py`

Add optional fields:
```python
ai_summary_light_tokens: int | None = None
ai_summary_medium_tokens: int | None = None
has_ai_summaries: bool = False
```

**2. Populate from `vision_document_summaries` table**

File: `api/endpoints/vision_documents.py`

In `list_vision_documents()` and `get_vision_document()`, after fetching the document(s), query `vision_document_summaries` for matching `document_id` + `source='ai'` rows. Populate the new response fields.

Use the existing `VisionDocumentRepository.get_summaries()` method (added in 0842a) — filter for `source='ai'` in the results.

### Frontend Changes

File: `frontend/src/components/products/ProductDetailsDialog.vue`

In the vision document card section (lines ~88-141 where Sumy chips are rendered), add a conditional second row below the Sumy chips:

```html
<!-- AI summaries (if available) -->
<div v-if="doc.has_ai_summaries" class="mt-1">
  <span class="text-caption text-medium-emphasis">AI summaries:</span>
  <v-chip size="x-small" color="info" variant="tonal" class="ml-1">
    33% ({{ doc.ai_summary_light_tokens?.toLocaleString() }} tokens)
  </v-chip>
  <v-chip size="x-small" color="info" variant="tonal" class="ml-1">
    66% ({{ doc.ai_summary_medium_tokens?.toLocaleString() }} tokens)
  </v-chip>
</div>
```

Use `color="info"` to visually distinguish AI badges from Sumy badges (which use `color="success"`).

### Key Existing Code

- **VisionDocumentResponse**: `api/schemas/vision_document.py`
- **Vision doc endpoints**: `api/endpoints/vision_documents.py` — `list_vision_documents()`, `get_vision_document()`
- **Summaries repo**: `src/giljo_mcp/repositories/vision_document_repository.py` — `get_summaries(session, tenant_key, document_id)`
- **Doc card UI**: `frontend/src/components/products/ProductDetailsDialog.vue:88-141`
- **Wireframe**: `handovers/Reference_docs/FLow_vision_doc3.png`

---

## Implementation Plan

1. TDD: Write test — API returns `has_ai_summaries=True` + token counts after AI summaries are written
2. Extend schema with 3 new optional fields
3. Update endpoints to query summaries table
4. TDD: Write frontend test — AI badge row renders when `has_ai_summaries` is true
5. Add badge row to ProductDetailsDialog
6. Commit

## Success Criteria

- [ ] API returns AI summary metadata per document
- [ ] AI badge row visible on document cards after AI analysis
- [ ] Badges hidden when no AI summaries exist
- [ ] Sumy badges unchanged
- [ ] Matches wireframe layout (`FLow_vision_doc3.png`)

## MANDATORY: Pre-Work Reading

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates
2. `handovers/Reference_docs/FLow_vision_doc3.png` — the wireframe to match

**Use `tdd-implementor` for backend, `ux-designer` for frontend.**
