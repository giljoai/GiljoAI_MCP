# Handover 0390b: Switch Reads to Table

**Part 2 of 4** in the 360 Memory JSONB Normalization series (0390)
**Date**: 2026-01-18
**Status**: Ready for Implementation
**Complexity**: High
**Estimated Duration**: 6-8 hours
**Branch**: `0390-360-memory-normalization`
**Prerequisite**: 0390a Complete (table exists with data)

---

## 1. EXECUTIVE SUMMARY

### Mission
Modify all 12 READ locations to query `product_memory_entries` table instead of `Product.product_memory.sequential_history[]` JSONB array.

### Context
After 0390a, the normalized table exists with all backfilled data. This handover switches all read operations to use the table, establishing it as the authoritative source for reads.

### Why This Matters
- **Query Performance**: Table queries with indexes vs JSONB array iteration
- **Consistent Interface**: Repository pattern for all memory access
- **Prepares for 0390c**: Once reads work, writes can be switched

### Success Criteria
- [ ] All API endpoints return data from table
- [ ] Query performance equal or better
- [ ] WebSocket events work correctly
- [ ] Frontend displays data correctly
- [ ] All existing E2E tests pass
- [ ] Zero reads from JSONB sequential_history

---

## 2. TECHNICAL CONTEXT

### Current READ Locations (12 files, 22 operations)

| File | Lines | Function | Current Pattern | New Pattern |
|------|-------|----------|-----------------|-------------|
| `tools/context_tools/get_360_memory.py` | 45-120 | `get_360_memory()` | JSONB iteration | Repository query |
| `tools/context_tools/get_git_history.py` | 30-85 | `get_git_history()` | JSONB iteration | Repository method |
| `tools/context_tools/fetch_context.py` | 180-210 | `_fetch_memory_360()` | Calls get_360_memory | Update params |
| `mission_planner.py` | 420-480 | `_get_360_memory_summary()` | JSONB iteration | Repository query |
| `thin_prompt_generator.py` | 310-360 | `_build_360_memory_section()` | JSONB iteration | Repository query |
| `services/product_service.py` | 450-520 | `get_product_memory()` | JSONB access | Repository query |
| `services/project_service.py` | 2180-2200 | `nuclear_delete_project()` | JSONB iteration | Repository method |
| `services/project_service.py` | 2260-2280 | `_purge_project_records()` | JSONB iteration | Repository method |
| `prompt_generation/memory_instructions.py` | 80-140 | `generate_context()` | JSONB access | Repository query |
| `tools/context_tools/framing_helpers.py` | 60-100 | `apply_rich_entry_framing()` | Entry formatting | Unchanged (format only) |
| `frontend/stores/products.js` | 280-320 | `handleProductMemoryUpdated()` | WebSocket payload | New payload format |
| `frontend/components/CloseoutModal.vue` | 120-180 | `loadMemoryEntries()` | API response | New response format |

---

## 3. SCOPE

### In Scope

1. **Backend Tool Updates**
   - `get_360_memory.py` - Use repository with pagination
   - `get_git_history.py` - Use repository git history method
   - `fetch_context.py` - Update dispatcher call

2. **Service Layer Updates**
   - `product_service.py` - Inject repository, query table
   - `project_service.py` - Use repository for delete marking

3. **Prompt Generation Updates**
   - `mission_planner.py` - Use repository
   - `thin_prompt_generator.py` - Use repository
   - `memory_instructions.py` - Use repository

4. **API Response Updates**
   - Ensure API responses match current format
   - Update serializers if needed

5. **Frontend Updates**
   - `products.js` - Parse new WebSocket payload
   - `CloseoutModal.vue` - Handle API response

### Out of Scope
- JSONB write operations (0390c)
- JSONB column deprecation (0390d)

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Verify 0390a Complete (15 minutes)

**Tasks**:
```bash
# Verify table exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d product_memory_entries"

# Verify data backfilled
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM product_memory_entries;"

# Run 0390a tests
pytest tests/repositories/test_product_memory_repository.py -v
```

---

### Phase 2: Update Backend Tools (2 hours)

#### 2a. get_360_memory.py

**Current** (JSONB iteration):
```python
product = await get_product(...)
memory = product.product_memory or {}
entries = memory.get("sequential_history", [])
# ... iterate and filter entries
```

**New** (Repository query):
```python
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

repo = ProductMemoryRepository()
entries = await repo.get_entries_by_product(
    session=session,
    product_id=product_id,
    tenant_key=tenant_key,
    limit=limit,
    include_deleted=False,
)
# Convert to dicts for response
return [entry.to_dict() for entry in entries]
```

#### 2b. get_git_history.py

**Current**:
```python
entries = memory.get("sequential_history", [])
all_commits = []
for entry in entries:
    commits = entry.get("git_commits", [])
    all_commits.extend(commits)
```

**New**:
```python
repo = ProductMemoryRepository()
commits = await repo.get_git_history(
    session=session,
    product_id=product_id,
    tenant_key=tenant_key,
    limit=limit,
)
return commits
```

#### 2c. fetch_context.py

Update the `_fetch_memory_360()` dispatcher to pass correct parameters.

---

### Phase 3: Update Services (2 hours)

#### 3a. product_service.py

**Changes**:
1. Inject `ProductMemoryRepository` instance
2. Replace `product.product_memory.get("sequential_history")` with repository calls
3. Update any methods returning memory entries

**Key Methods to Update**:
- `get_product_with_memory()`
- `get_product_details()`
- Any method returning `product_memory`

#### 3b. project_service.py

**Changes in `nuclear_delete_project()`**:

**Current** (JSONB mutation):
```python
# Mark 360 memory entries in JSONB
for entry in sequential_history:
    if entry.get("project_id") == project_id:
        entry["deleted_by_user"] = True
        entry["user_deleted_at"] = datetime.utcnow().isoformat()
```

**New** (Repository call):
```python
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

repo = ProductMemoryRepository()
count = await repo.mark_entries_deleted(
    session=session,
    project_id=project_id,
    tenant_key=tenant_key,
)
logger.info(f"Marked {count} memory entries as deleted")
```

---

### Phase 4: Update Prompt Generation (1.5 hours)

#### 4a. mission_planner.py

**File**: `src/giljo_mcp/mission_planner.py`

Find `_get_360_memory_summary()` method and update to use repository.

#### 4b. thin_prompt_generator.py

**File**: `src/giljo_mcp/thin_prompt_generator.py`

Find `_build_360_memory_section()` method and update to use repository.

#### 4c. memory_instructions.py

**File**: `src/giljo_mcp/prompt_generation/memory_instructions.py`

Update to use repository for memory access.

---

### Phase 5: Update API Responses (1 hour)

Ensure API responses maintain backward compatibility:

**Response format** (should remain unchanged):
```json
{
  "product_memory": {
    "sequential_history": [
      {
        "sequence": 1,
        "type": "project_completion",
        "project_id": "...",
        ...
      }
    ],
    "git_integration": {...}
  }
}
```

**Implementation**:
```python
# Serialize table entries to match JSONB format
entries = await repo.get_entries_by_product(...)
response = {
    "product_memory": {
        "sequential_history": [e.to_dict() for e in entries],
        "git_integration": product.product_memory.get("git_integration", {}),
    }
}
```

---

### Phase 6: Update Frontend (1 hour)

#### 6a. products.js

**File**: `frontend/src/stores/products.js`

Update WebSocket handler to parse new payload format (should be minimal if API response unchanged).

**Status**: ✅ VERIFIED - No changes needed. Store handlers gracefully accept entire product_memory objects.

#### 6b. CloseoutModal.vue

**File**: `frontend/src/components/orchestration/CloseoutModal.vue`

Verify component handles API response correctly.

**Status**: ✅ VERIFIED - No changes needed. Component uses defensive field access with v-if.

#### 6c. Verification Report

**File**: `handovers/0390b_phase6_frontend_verification_report.md`

Complete verification report showing:
- API response format is backward compatible
- WebSocket handlers work correctly
- Component display logic handles new fields
- No breaking changes introduced

**Status**: ✅ COMPLETE - Phase 6 verification finished. Ready for Phase 7.

---

### Phase 7: Integration Testing (1 hour)

**Test Scenarios**:

1. **Get 360 Memory**
   - API returns entries from table
   - Pagination works correctly
   - Filters work (include_deleted)

2. **Get Git History**
   - Returns aggregated commits
   - Sorted by date descending

3. **Project Deletion**
   - Marks entries in table (not JSONB)
   - Entries still visible with include_deleted=true

4. **Orchestrator Instructions**
   - 360 memory section populated
   - Context contains recent entries

5. **Frontend Display**
   - Closeout modal shows entries
   - Memory history displays correctly

---

## 5. TESTING REQUIREMENTS

### Unit Tests
- Repository method mocking in services
- Correct query parameters passed

### Integration Tests
- End-to-end API calls
- Database queries return expected data

### E2E Tests
- Frontend displays data correctly
- WebSocket updates work

---

## 6. ROLLBACK PLAN

### Rollback Triggers
- More than 10 tests fail
- Frontend breaks
- Data mismatch detected

### Rollback Steps
```bash
# Revert all modified files
git checkout HEAD~1 -- src/giljo_mcp/tools/context_tools/
git checkout HEAD~1 -- src/giljo_mcp/services/
git checkout HEAD~1 -- src/giljo_mcp/mission_planner.py
git checkout HEAD~1 -- src/giljo_mcp/thin_prompt_generator.py
# etc.
```

---

## 7. FILES INDEX

### Files to MODIFY

| File | Changes | Risk |
|------|---------|------|
| `src/giljo_mcp/tools/context_tools/get_360_memory.py` | Repository queries | MEDIUM |
| `src/giljo_mcp/tools/context_tools/get_git_history.py` | Repository queries | MEDIUM |
| `src/giljo_mcp/tools/context_tools/fetch_context.py` | Update dispatcher | LOW |
| `src/giljo_mcp/services/product_service.py` | Inject repo, query table | HIGH |
| `src/giljo_mcp/services/project_service.py` | Use repo for marking | MEDIUM |
| `src/giljo_mcp/mission_planner.py` | Repository queries | MEDIUM |
| `src/giljo_mcp/thin_prompt_generator.py` | Repository queries | MEDIUM |
| `src/giljo_mcp/prompt_generation/memory_instructions.py` | Repository queries | LOW |
| `frontend/src/stores/products.js` | WebSocket handler | LOW |
| `frontend/src/components/CloseoutModal.vue` | API response | LOW |

---

## 8. SUCCESS CRITERIA

### Functional
- [ ] All API endpoints return table data
- [ ] Query performance equal or better
- [ ] WebSocket events work
- [ ] Frontend displays correctly
- [ ] Project deletion marks table entries

### Quality
- [ ] All tests pass
- [ ] No linting errors
- [ ] Code follows patterns

### Documentation
- [ ] Closeout notes completed
- [ ] Ready for 0390c handover

---

## CLOSEOUT NOTES

**Status**: [PHASE 6 VERIFIED - READY FOR CONTINUATION]

### Phase 6 Completion Summary (Frontend Verification)

**Date**: 2026-01-18
**Agent**: Frontend Tester Agent

#### Key Findings

1. **API Response Format**: Backward compatible
   - `ProductService._build_product_memory_response()` reconstructs identical structure
   - Table entries converted to dicts via `to_dict()` method
   - Sequential history array populated from table with all required fields

2. **Frontend Store Handlers**: No changes needed
   - `handleProductMemoryUpdated()` gracefully accepts entire product_memory objects
   - `handleProductLearningAdded()` appends entries without field validation
   - WebSocket routing works correctly for all event types

3. **Frontend Components**: No changes needed
   - `CloseoutModal.vue` uses defensive field access with v-if
   - All displayed fields present in table-based entries
   - Soft-delete filtering handled server-side (entries filtered before sending)

4. **Field Compatibility**: All required fields present
   - Original JSONB fields preserved in table schema
   - New table fields (id, deleted_by_user, source, author_*, etc.) safely ignored by frontend
   - Entry display logic unchanged

5. **Accessibility & Browser Support**: Maintained
   - ARIA labels preserved
   - Keyboard navigation unchanged
   - No new version requirements
   - Responsive design logic unchanged

#### Implementation Status

| Phase | Task | Status |
|-------|------|--------|
| 1 | Verify 0390a | ✅ Prerequisite met |
| 2 | Backend tools | ⏳ Ready for implementation |
| 3 | Services layer | ⏳ Ready for implementation |
| 4 | Prompt generation | ⏳ Ready for implementation |
| 5 | API responses | ✅ Already compatible |
| 6 | Frontend updates | ✅ VERIFIED - No changes needed |
| 7 | Integration testing | ⏳ Ready for implementation |

#### Recommendations

1. **Phase 6 Complete**: Frontend verification finished. No code changes required.
2. **Phase 7 Ready**: Can proceed with integration testing
3. **All Phases Can Proceed**: No blocking issues found
4. **Documentation**: Full verification report in `0390b_phase6_frontend_verification_report.md`

#### Risk Assessment

**Overall Risk**: LOW
- API response format unchanged
- Frontend code is defensive (uses optional chaining, v-if guards)
- No breaking changes in response structure
- Additional fields don't interfere with existing logic

#### Testing Checklist for Phase 7

- [ ] Backend tools return data from table (get_360_memory, get_git_history, etc.)
- [ ] API endpoints tested with actual table data
- [ ] E2E tests pass (existing test suite)
- [ ] WebSocket events properly formatted
- [ ] Frontend displays memory correctly
- [ ] No console errors in browser
- [ ] Soft-delete entries properly filtered
- [ ] Performance metrics recorded

---

**Next Steps**: Proceed with Phase 2-5 implementation of read operations, then Phase 7 integration testing.

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
