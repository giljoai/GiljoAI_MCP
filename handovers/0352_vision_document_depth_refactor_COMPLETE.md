# Handover 0352: Vision Document Depth Refactor - COMPLETE

**Status**: COMPLETE
**Date**: 2025-12-17
**Commits**: 12 commits (0e3d7dca and predecessors)

---

## Executive Brief (300 words)

This session addressed a critical gap in GiljoAI's context management system: vision document depth configuration was not being dynamically injected into orchestrator instructions based on user settings.

**Problem Identified**: When users configured vision document depth (Light/Medium/Full) in the UI, these settings were not reflected in `get_orchestrator_instructions()`. The system was also storing summarization results with incorrect dictionary keys (`moderate`/`heavy` instead of `light`/`medium`), causing KeyErrors during vision document uploads.

**Solution Implemented**: We completed a full refactor of the vision document depth system:

1. **Fixed Critical Bug**: Updated `product_service.py` to use correct Sumy summarizer output keys (`light`/`medium` instead of `moderate`/`heavy`).

2. **Implemented Depth-Based Source Selection**: Refactored `get_vision_document.py` to read different data sources based on depth:
   - Light: Returns `VisionDocument.summary_light` (33% Sumy-compressed)
   - Medium: Returns `VisionDocument.summary_medium` (66% Sumy-compressed)
   - Full: Returns paginated chunks from `MCPContextIndex` (≤25K tokens/call)

3. **Removed "Optional" Depth**: Eliminated the ambiguous "optional" setting. Users now choose explicitly between Light/Medium/Full, while Priority (Critical/Important/Reference/Off) determines urgency.

4. **Added Dynamic Framing**: Orchestrator instructions now show depth-specific framing (e.g., "66% summarized vision document (single response)") instead of generic text.

5. **Database Migration**: Created and executed migration to convert existing users from "optional" to "light".

**Impact**: Orchestrators now receive accurate, depth-aware instructions that reflect user preferences. The separation of Priority (when to read) and Depth (how much to read) provides clear, unambiguous guidance. Token estimates are now accurate per depth level, enabling better context budget management.

**Testing**: 15+ new tests added covering migration, depth selection, and end-to-end flow.

---

## Session Timeline

### Phase 1: Discovery & Bug Identification

**Initial Task**: Test orchestrator instructions and verify user settings are reflected.

**Findings**:
1. `memory_360` and `git_history` depth values not updating (key mismatch)
2. `vision_documents` showing `limit: "optional"` instead of `depth: "medium"`
3. Critical KeyError bug in `product_service.py`

**Root Causes**:
- Database stored `memory_last_n_projects` but code expected `memory_360`
- Database stored `git_commits` but code expected `git_history`
- Vision documents depth was being set as `limit` parameter, not `depth`
- Summarizer output keys changed in Handover 0246b but service layer not updated

### Phase 2: Key Mapping Fix

**File Modified**: `src/giljo_mcp/tools/orchestration.py`

Added key normalization in `_get_user_config()`:
```python
key_mapping = {
    "memory_last_n_projects": "memory_360",
    "git_commits": "git_history",
}
```

**Result**: User depth settings now correctly flow to orchestrator instructions.

### Phase 3: Vision Document Depth Refactor

#### Task 1: Fix ProductService Bug
**File**: `src/giljo_mcp/services/product_service.py`
**Change**: Updated `summaries["moderate"]` → `summaries["medium"]`
**Commit**: `c9592f45`

#### Task 2: Implement Depth-Based Source Selection
**File**: `src/giljo_mcp/tools/context_tools/get_vision_document.py`

**New Behavior**:
| Depth | Source | Response |
|-------|--------|----------|
| light | `VisionDocument.summary_light` | Single response, ~33% |
| medium | `VisionDocument.summary_medium` | Single response, ~66% |
| full | `MCPContextIndex` chunks | Paginated, ≤25K/call |

**Commits**: `d01092db`, `d7cddaef`

#### Task 3: Fix Mission Planner
**File**: `src/giljo_mcp/mission_planner.py`
**Change**: Vision documents now use `depth` param instead of `limit`

### Phase 4: Remove "Optional" & Simplify

**Design Decision**: Remove "optional" depth entirely. Let Priority determine importance, Depth determines amount.

#### Frontend Changes
**File**: `frontend/src/components/settings/ContextPriorityConfig.vue`
- Removed "Optional (Orchestrator decides)" option
- Updated labels:
  - Light (33% Summary)
  - Medium (66% Summary)
  - Full (100% Complete)

#### Backend Changes
**Files**: `orchestration.py`, `mission_planner.py`
- Default changed from "optional" to "light"
- Runtime normalization: "optional" → "light"

#### Database Migration
**File**: `migrations/0352_vision_depth_optional_to_light.sql`
```sql
UPDATE users
SET depth_config = jsonb_set(depth_config, '{vision_documents}', '"light"')
WHERE depth_config->>'vision_documents' = 'optional';
```

**Commits**: `a3f9dff2`, `ac96a3b4`

### Phase 5: Depth-Aware Framing

**File**: `src/giljo_mcp/mission_planner.py`

Added dynamic framing based on depth:
```python
vision_framing = {
    "light": "33% summarized vision document (single response).",
    "medium": "66% summarized vision document (single response).",
    "full": "Complete vision document (paginated, call until has_more=false).",
}
vision_tokens = {
    "light": 4000,
    "medium": 8000,
    "full": 25000,
}
```

**Commit**: `0e3d7dca`

---

## Architecture Flow (Final)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER SETTINGS (UI)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│   Vision Documents                                                           │
│   ┌──────────────────────┐    ┌──────────────────────┐                      │
│   │ Priority      ▼      │    │ Depth          ▼     │                      │
│   ├──────────────────────┤    ├──────────────────────┤                      │
│   │ ○ Critical (MUST)    │    │ ○ Light   (33%)      │                      │
│   │ ● Important (SHOULD) │    │ ● Medium  (66%)      │                      │
│   │ ○ Reference (MAY)    │    │ ○ Full    (100%)     │                      │
│   │ ○ Off                │    └──────────────────────┘                      │
│   └──────────────────────┘                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    get_orchestrator_instructions() RESPONSE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│   "vision_documents": {                                                      │
│       "params": { "depth": "medium" },                                       │
│       "framing": "REQUIRED: 66% summarized vision document (single response)"│
│       "estimated_tokens": 8000                                               │
│   }                                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPTH DETERMINES DATA SOURCE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│   light  → VisionDocument.summary_light  (33%, single response)              │
│   medium → VisionDocument.summary_medium (66%, single response)              │
│   full   → MCPContextIndex chunks        (100%, paginated ≤25K/call)         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/giljo_mcp/services/product_service.py` | Fix summarizer key mismatch |
| `src/giljo_mcp/tools/context_tools/get_vision_document.py` | Depth-based source selection |
| `src/giljo_mcp/tools/orchestration.py` | Key normalization, default "light" |
| `src/giljo_mcp/mission_planner.py` | Depth param fix, depth-aware framing |
| `frontend/src/components/settings/ContextPriorityConfig.vue` | Remove "optional", update labels |
| `migrations/0352_vision_depth_optional_to_light.sql` | User migration |

## Tests Added

| File | Tests |
|------|-------|
| `tests/integration/test_vision_upload_summarization_fix.py` | 4 tests |
| `tests/tools/test_get_vision_document_depth_refactor.py` | 8 tests |
| `tests/test_vision_depth_migration.py` | 7 tests |

---

## Commits (Chronological)

1. `d07e59d9` - test: Add vision upload summarization tests (TDD RED)
2. `c9592f45` - fix(0352): Update vision document summary keys
3. `d01092db` - test: Add depth-based source selection tests (TDD RED)
4. `d7cddaef` - feat: Implement depth-based source selection
5. `a3f9dff2` - test: Add vision_documents depth migration tests
6. `ac96a3b4` - feat: Migrate vision_documents depth from 'optional' to 'light'
7. `0e3d7dca` - feat(0352): Complete vision document depth refactor

---

## Verification

Tested end-to-end with user changing settings in UI:
- `memory_360.limit`: Dynamic ✅
- `git_history.limit`: Dynamic ✅
- `agent_templates.depth`: Dynamic ✅
- `vision_documents.depth`: Dynamic ✅
- Depth-aware framing: Dynamic ✅
- Token estimates: Accurate per depth ✅
