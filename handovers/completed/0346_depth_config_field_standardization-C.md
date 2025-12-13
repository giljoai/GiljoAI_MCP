# Handover: 0346 - Depth Config Field Standardization

**Date:** 2025-12-12
**From Agent:** Orchestrator (Claude Code)
**To Agent:** tdd-implementor
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Ready for Implementation

---

## Task Summary

Vision document depth toggle in Settings → Context has **no effect** because field names are inconsistent across layers. User selects "moderate" but Sumy summarization is **NEVER applied** - full vision doc returned instead.

**Root Cause:** Three different field names for the same concept:
- Frontend sends: `vision_document_depth`
- Backend stores: `vision_chunking`
- Consumer expects: `vision_documents`

**Solution:** Standardize on `vision_documents` (v2.0 Context Management naming convention).

---

## VERIFIED EVIDENCE (Database + MCP Tool)

### Test Case: Orchestrator 62af6b2f-404c-4332-bfbc-241d645765c1

**Database Query:**
```sql
SELECT job_metadata FROM mcp_agent_jobs WHERE job_id = '62af6b2f-404c-4332-bfbc-241d645765c1';
```

**Result:**
```json
"depth_config": {
  "vision_chunking": "moderate",  // <-- STORED AS THIS
  ...
}
```

**MissionPlanner Code (line 1377):**
```python
vision_depth = depth_config.get("vision_documents", "moderate")  // <-- EXPECTS THIS
```

**Actual Output:** Full 21,150 token TinyContacts vision document (no Sumy compression)
**Expected Output:** ~5,000 token "moderate" Sumy summary

---

## Technical Details

### Data Flow (Current - Broken)
```
UI: "heavy" → Frontend: vision_document_depth → Pydantic: vision_chunking (MISMATCH - ignored)
                                                  ↓
Database: { vision_chunking: "moderate" } → MissionPlanner: depth_config.get("vision_documents") → "moderate" (default)
                                                                                                      ↓
                                                                               BUT key doesn't exist! Falls through to FULL doc
```

### Data Flow (Fixed)
```
UI: "heavy" → Frontend: vision_documents → Pydantic: vision_documents → Database: { vision_documents: "heavy" }
                                                                              ↓
                                           MissionPlanner: depth_config.get("vision_documents") → "heavy" ✓
                                                                              ↓
                                           Sumy LSA summarization applied at "heavy" level (~12.5K tokens)
```

---

## Files to Modify

### Backend (5 files)

| File | Line(s) | Change |
|------|---------|--------|
| `api/endpoints/users.py` | 231 | `vision_chunking` → `vision_documents` |
| `src/giljo_mcp/models/auth.py` | 109 | Default dict key |
| `src/giljo_mcp/services/user_service.py` | 1114, 1170, 1277 | Defaults + validation |
| `src/giljo_mcp/services/project_service.py` | 1765 | Default dict key |
| `src/giljo_mcp/thin_prompt_generator.py` | 30, 173 | Docstring + default |

### Frontend (2 files)

| File | Line(s) | Change |
|------|---------|--------|
| `frontend/src/components/settings/ContextPriorityConfig.vue` | 424-425, 460 | `vision_document_depth` → `vision_documents` |
| `frontend/src/components/settings/ContextPriorityConfig.vision.spec.js` | 193-222 | Update assertions |

### DO NOT MODIFY
| File | Line | Reason |
|------|------|--------|
| `src/giljo_mcp/mission_planner.py` | 1377 | Already uses `vision_documents` - this is the source of truth |

---

## Implementation Plan

### Phase 1: TDD - Write Failing Tests

```python
# tests/services/test_depth_config_standardization.py
"""Handover 0346: Verify vision_documents is the canonical field name."""

import pytest
from api.endpoints.users import DepthConfig

class TestDepthConfigFieldStandardization:
    def test_pydantic_model_uses_vision_documents(self):
        config = DepthConfig()
        assert hasattr(config, 'vision_documents')
        assert not hasattr(config, 'vision_chunking')
        assert config.vision_documents == 'moderate'

    def test_depth_config_accepts_all_levels(self):
        for level in ['none', 'light', 'moderate', 'heavy']:
            config = DepthConfig(vision_documents=level)
            assert config.vision_documents == level
```

Run: `pytest tests/services/test_depth_config_standardization.py -v` → EXPECT FAILURE

### Phase 2: Backend Implementation

**2.1 api/endpoints/users.py (Line 231)**
```python
# BEFORE
vision_chunking: Literal["none", "light", "moderate", "heavy"] = Field(
    default="moderate", description="Vision document chunking level (affects token usage)"
)

# AFTER
vision_documents: Literal["none", "light", "moderate", "heavy"] = Field(
    default="moderate", description="Vision document depth level (affects token usage)"
)
```

**2.2 src/giljo_mcp/models/auth.py (Line 109)**
```python
# BEFORE
default={"vision_chunking": "moderate", ...}

# AFTER
default={"vision_documents": "moderate", ...}
```

**2.3 src/giljo_mcp/services/user_service.py**
```python
# Line 1114, 1277 - Default dicts
- "vision_chunking": "moderate",
+ "vision_documents": "moderate",

# Line 1170 - Validation
- if "vision_chunking" in config and config["vision_chunking"] not in valid_vision:
+ if "vision_documents" in config and config["vision_documents"] not in valid_vision:
```

**2.4 src/giljo_mcp/services/project_service.py (Line 1765)**
```python
- "vision_chunking": "moderate",
+ "vision_documents": "moderate",
```

**2.5 src/giljo_mcp/thin_prompt_generator.py**
```python
# Line 30 (docstring)
- - vision_chunking: "none" | "light" | "moderate" | "heavy"
+ - vision_documents: "none" | "light" | "moderate" | "heavy"

# Line 173 (default dict)
- "vision_chunking": "moderate",
+ "vision_documents": "moderate",
```

### Phase 3: Frontend Implementation

**3.1 ContextPriorityConfig.vue (Lines 424-425)**
```typescript
// BEFORE
if (depthData.vision_document_depth && config.value.vision_documents) {
  config.value.vision_documents.depth = depthData.vision_document_depth
}

// AFTER
if (depthData.vision_documents && config.value.vision_documents) {
  config.value.vision_documents.depth = depthData.vision_documents
}
```

**3.2 ContextPriorityConfig.vue (Line 460)**
```typescript
// BEFORE
vision_document_depth: config.value.vision_documents?.depth || 'moderate',

// AFTER
vision_documents: config.value.vision_documents?.depth || 'moderate',
```

**3.3 ContextPriorityConfig.vision.spec.js (Lines 193-204)**
```javascript
// BEFORE
expect(depthPayload.depth_config).toHaveProperty('vision_document_depth')

// AFTER
expect(depthPayload.depth_config).toHaveProperty('vision_documents')
```

### Phase 4: Verification

1. Run backend tests: `pytest tests/services/test_user_service.py tests/services/test_depth_config_standardization.py -v`
2. Run frontend tests: `cd frontend && npm test`
3. E2E manual test:
   - Go to Settings → Context
   - Change Vision Documents depth to "heavy"
   - Save
   - Launch a project with vision document
   - Verify orchestrator mission uses heavy summarization
4. Full suite: `pytest tests/ --cov=src/giljo_mcp`

---

## Testing Requirements

### Unit Tests
- [ ] `test_pydantic_model_uses_vision_documents`
- [ ] `test_depth_config_accepts_all_levels`
- [ ] `test_user_service_defaults_use_vision_documents`
- [ ] `test_depth_config_roundtrip`

### Integration Tests
- [ ] API endpoint accepts `vision_documents` field
- [ ] Value persists to database
- [ ] Value retrieved correctly on GET

### E2E Tests
- [ ] UI toggle affects mission generation

---

## Success Criteria

- [ ] All tests pass (backend and frontend)
- [ ] No references to `vision_chunking` or `vision_document_depth` remain in codebase
- [ ] `grep -r "vision_chunking" src/ api/` returns nothing
- [ ] `grep -r "vision_document_depth" frontend/src/` returns nothing
- [ ] E2E: Vision depth change in UI affects Sumy summarization level
- [ ] Coverage >80%

---

## Dependencies and Blockers

**Dependencies:** None - self-contained fix

**Blockers:** None

---

## Rollback Plan

JSONB field - no schema migration. To rollback:
1. `git revert HEAD`
2. Existing users with `vision_documents` key will continue to work
3. New users get defaults

---

## Additional Resources

- **Related Handovers:** 0314 (Depth Controls), 0345c (Vision Settings UI), 0345e (Sumy Compression)
- **v2.0 Field Naming:** See `src/giljo_mcp/config/defaults.py:84`
- **Consumer Code:** `src/giljo_mcp/mission_planner.py:1377`

---

## Recommended Sub-Agent

**tdd-implementor** - TDD approach with clean surgical renames across 7 files.
