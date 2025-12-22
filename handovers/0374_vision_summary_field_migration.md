# Handover 0374: Vision Summary Field Migration

**Date**: 2025-12-22
**Priority**: MEDIUM
**Status**: IN PROGRESS
**Estimated Effort**: 2-3 hours
**Related**: Handover 0371 (Phase 4.5), Handover 0246b (original deprecation)

---

## Executive Summary

Remove deprecated vision document summary fields (`summary_moderate`, `summary_heavy`) and consolidate to the active 3-tier system: `summary_light`, `summary_medium`, `full`.

**Background**: Handover 0246b introduced percentage-based summaries (light=33%, medium=66%) but kept old field names for backward compatibility. Since we're pre-release, we can now remove the deprecated fields entirely.

---

## Current State

### Database Model (`src/giljo_mcp/models/products.py`)

| Column | Status | Action |
|--------|--------|--------|
| `summary_light` | ACTIVE | Keep |
| `summary_medium` | ACTIVE | Keep |
| `summary_moderate` | DEPRECATED | **REMOVE** (alias for medium) |
| `summary_heavy` | DEPRECATED | **REMOVE** (feature removed) |
| `summary_light_tokens` | ACTIVE | Keep |
| `summary_medium_tokens` | ACTIVE | Keep |
| `summary_moderate_tokens` | DEPRECATED | **REMOVE** |
| `summary_heavy_tokens` | DEPRECATED | **REMOVE** |

### Endpoint (`api/endpoints/products/vision.py`)

Lines 201-206 map deprecated fields:
```python
summary_moderate=doc.summary_moderate,  # Should be removed
summary_heavy=doc.summary_heavy,        # Should be removed
summary_moderate_tokens=doc.summary_moderate_tokens,
summary_heavy_tokens=doc.summary_heavy_tokens,
```

Line 177 uses deprecated fields in `has_summaries` check.

### Schema (`api/schemas/vision_document.py`)

Lines 97-101 have deprecated fields with DEPRECATED comments.

### Context Tools (`src/giljo_mcp/tools/context_tools/get_vision_document.py`)

Uses `summary_moderate` as a valid mode option.

---

## Tasks

### Phase 1: Database Model Update

**File**: `src/giljo_mcp/models/products.py`

Remove columns from `MCPVisionDocument` class:
- `summary_moderate` (line ~388)
- `summary_heavy` (line ~391)
- `summary_moderate_tokens` (line ~401)
- `summary_heavy_tokens` (line ~404)
- `summary_text` (line ~368) - also deprecated

### Phase 2: Endpoint Update

**File**: `api/endpoints/products/vision.py`

1. Remove deprecated field mappings (lines 202-206)
2. Update `has_summaries` check (line 177) to use only `summary_light` and `summary_medium`

### Phase 3: Schema Update

**File**: `api/schemas/vision_document.py`

Remove from `VisionDocumentResponse`:
- `summary_moderate` (line 98)
- `summary_heavy` (line 99)
- `summary_moderate_tokens` (line 100)
- `summary_heavy_tokens` (line 101)

### Phase 4: Context Tools Update

**File**: `src/giljo_mcp/tools/context_tools/get_vision_document.py`

Update valid modes from `["summary_light", "summary_moderate", "full"]` to `["summary_light", "summary_medium", "full"]`.

### Phase 5: Database Migration

**File**: `migrations/versions/XXXX_remove_deprecated_vision_fields.py`

Create Alembic migration to DROP columns:
- `summary_moderate`
- `summary_heavy`
- `summary_moderate_tokens`
- `summary_heavy_tokens`
- `summary_text`

### Phase 6: Test Updates

Update any tests referencing deprecated fields.

---

## Verification

After completion:
1. `python -c "from src.giljo_mcp.models import MCPVisionDocument"` - no errors
2. `cd frontend && npm run build` - builds successfully
3. `pytest tests/services/test_vision_summarizer*.py -v` - passes
4. Server starts without errors

---

## Risk Assessment

**Risk**: LOW (pre-release, no production data)

**Rollback**: Git revert + restore migration

---

## Success Criteria

1. No references to `summary_moderate` or `summary_heavy` in codebase (except completed handovers)
2. Database schema has only `summary_light`, `summary_medium` columns
3. All tests pass
4. API returns only active fields

---

*Spawned from Handover 0371 Phase 4.5*
