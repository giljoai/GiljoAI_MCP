# Handover: 360 Memory UI Closeout Modal Fix

**Date:** 2026-02-07
**From Agent:** Claude Sonnet 4.5 (diagnostic session)
**To Agent:** tdd-implementor + backend-integration-tester
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

The CloseoutModal component (shown when users click "Close Out Project") displays "No 360 memory entries found" even though memory entries exist in the database. The UI is trying to read from an obsolete JSONB field (`Product.product_memory.sequential_history`) that was removed in Handover 0700c. Memory entries are now stored in the normalized `product_memory_entries` table but the UI lacks an API endpoint to fetch them.

**Expected Outcome:** Users can view their project's 360 memory entries in the CloseoutModal, properly fetched from the `product_memory_entries` table.

---

## Context and Background

### Architecture (by Design)
- **360 Memory is Product-Scoped** - Memories belong to Products (not Projects)
- **Project-Linked** - Each entry has `project_id` FK for traceability
- **Tenant-Isolated** - All queries filtered by `tenant_key`
- **Normalized Storage** - Moved from JSONB arrays (Handover 0390) to `product_memory_entries` table (Handover 0700c)

### What Happened (Root Cause Analysis)
1. User's orchestrator called `close_project_and_update_memory()` MCP tool
2. Tool successfully created entry in `product_memory_entries` table:
   - Entry ID: `6b5d998d-c9d4-4624-aeb4-c6077758b9cd`
   - Product ID: `70ba64fb-7b0d-4699-82f8-77d0b9d179e8`
   - Project ID: `5d07b2eb-520c-44ee-b928-814a153e4bf8`
   - Sequence: 13
3. User opens CloseoutModal in UI → Shows "No 360 memory entries found"
4. **Bug #1 (Backend)**: `api/endpoints/products/crud.py:237` returns obsolete JSONB structure:
   ```python
   pm = {"github": {}, "sequential_history": [], "context": {}}
   ```
5. **Bug #2 (Frontend)**: `CloseoutModal.vue:298-306` reads from obsolete field:
   ```javascript
   const sequentialHistory = productMemory.sequential_history || []
   ```

### Database Verification (Confirmed Working)
```sql
-- Entry exists in normalized table
SELECT * FROM product_memory_entries
WHERE id = '6b5d998d-c9d4-4624-aeb4-c6077758b9cd';
-- Returns: sequence=13, entry_type='project_closeout', 3-paragraph summary, 10 key outcomes
```

---

## Technical Details

### Database Schema (Already Exists)
```sql
product_memory_entries:
├── id (PK)
├── tenant_key (indexed)
├── product_id (FK → products, CASCADE DELETE)
├── project_id (FK → projects, SET NULL when project deleted)
├── sequence (unique per product, auto-incrementing)
├── entry_type (e.g., "project_closeout", "session_handover")
├── source (e.g., "closeout_v1")
├── timestamp
├── project_name
├── summary (text)
├── key_outcomes (JSONB array)
├── decisions_made (JSONB array)
├── git_commits (JSONB array)
├── deliverables (JSONB array)
├── metrics (JSONB object)
├── priority (integer)
├── significance_score (double)
├── token_estimate (integer)
├── tags (JSONB array)
├── author_job_id
├── author_name
├── author_type
├── deleted_by_user (boolean)
├── user_deleted_at
├── created_at
└── updated_at
```

### Files to Modify

**1. Backend - New API Endpoint (CREATE)**
- File: `api/endpoints/products/memory.py` (NEW FILE)
- Purpose: Fetch memory entries from `product_memory_entries` table
- Endpoint: `GET /api/v1/products/{product_id}/memory-entries`
- Query params:
  - `project_id` (optional) - filter by specific project
  - `limit` (optional, default 10) - max entries to return
  - `include_deleted` (optional, default false) - show user-deleted entries

**2. Backend - Router Registration**
- File: `api/endpoints/products/__init__.py`
- Add: `from . import memory`
- Add: `router.include_router(memory.router)`

**3. Frontend - API Service**
- File: `frontend/src/services/api.js`
- Add method to `products` object:
  ```javascript
  getMemoryEntries: (productId, params) =>
    apiClient.get(`/api/v1/products/${productId}/memory-entries`, { params })
  ```

**4. Frontend - Component**
- File: `frontend/src/components/orchestration/CloseoutModal.vue`
- Replace lines 298-306 in `loadMemoryEntries()` method
- Change from reading JSONB to calling new API endpoint

### Key Code Sections

**Current Broken Code (CloseoutModal.vue:298-306)**
```javascript
const response = await api.products.get(props.productId)
const productMemory = response.data.product_memory || {}
const sequentialHistory = productMemory.sequential_history || []  // Empty!

memoryEntries.value = sequentialHistory
  .filter((entry) => entry.project_id === props.projectId)
  .sort((a, b) => (b.sequence || 0) - (a.sequence || 0))
```

**Proposed Fix (CloseoutModal.vue)**
```javascript
const response = await api.products.getMemoryEntries(
  props.productId,
  { project_id: props.projectId, limit: 10 }
)
memoryEntries.value = response.data.entries || []
```

### API Response Schema
```typescript
{
  success: boolean
  entries: Array<{
    id: string
    sequence: number
    entry_type: string
    source: string
    timestamp: string
    project_id: string | null
    project_name: string | null
    summary: string | null
    key_outcomes: string[]
    decisions_made: string[]
    git_commits: Array<{ message: string, author: string, timestamp: string }>
    deliverables: Array<any>
    metrics: object
    priority: number
    significance_score: number
    tags: string[]
    author_job_id: string | null
    author_name: string | null
    author_type: string | null
    deleted_by_user: boolean
  }>
  total_count: number
  filtered_count: number
}
```

---

## Implementation Plan

### Phase 1: Backend API Endpoint (TDD)
**Agent:** tdd-implementor
**Duration:** 2-3 hours

1. **Write Tests First** (`tests/endpoints/products/test_memory.py`)
   - Test fetching all entries for product
   - Test filtering by project_id
   - Test limit parameter
   - Test tenant isolation (no cross-tenant leakage)
   - Test deleted entries exclusion
   - Test empty results
   - Test 404 for invalid product_id

2. **Create API Endpoint** (`api/endpoints/products/memory.py`)
   - Import `ProductMemoryRepository` from `src/giljo_mcp/database/repositories/product_memory_repository.py`
   - Query `product_memory_entries` table
   - Filter by `tenant_key` (from current_user)
   - Filter by `product_id` (from path parameter)
   - Optional filter by `project_id` (query parameter)
   - Exclude `deleted_by_user = true` by default
   - Order by `sequence DESC` (newest first)
   - Apply `limit` parameter
   - Return Pydantic schema with entries array

3. **Register Router**
   - Add to `api/endpoints/products/__init__.py`
   - Test endpoint with `curl` or Postman

**Testing Criteria:**
- All unit tests pass
- Manual curl test returns expected data
- Tenant isolation verified (cannot access other tenant's memories)

### Phase 2: Frontend Integration
**Agent:** tdd-implementor (with frontend focus)
**Duration:** 1-2 hours

1. **Update API Service** (`frontend/src/services/api.js`)
   - Add `getMemoryEntries` method to `products` object

2. **Update CloseoutModal Component** (`frontend/src/components/orchestration/CloseoutModal.vue`)
   - Replace `loadMemoryEntries()` method implementation (lines 292-318)
   - Call new API endpoint
   - Handle response mapping (API returns `entries` array)
   - Update error handling for new response format

3. **Component Testing**
   - Manual test: Open CloseoutModal for project with memory entries
   - Verify entries display correctly
   - Verify "No entries" message only shows when truly empty

**Testing Criteria:**
- Modal loads without errors
- Memory entries display correctly (summary, outcomes, decisions)
- Expansion panels work
- No console errors

### Phase 3: Integration Testing
**Agent:** backend-integration-tester
**Duration:** 1 hour

1. **End-to-End Test**
   - Create test project via API
   - Call `close_project_and_update_memory()` MCP tool
   - Fetch memory entries via new endpoint
   - Verify entry appears in UI
   - Verify filtering by project_id works

2. **Edge Cases**
   - Product with no memory entries
   - Product with 10+ memory entries (pagination)
   - Deleted memory entries (excluded by default)
   - Cross-tenant isolation test

**Testing Criteria:**
- E2E test passes
- Edge cases handled gracefully
- Performance acceptable (<500ms for 100 entries)

---

## Testing Requirements

### Unit Tests
**Location:** `tests/endpoints/products/test_memory.py`
- `test_get_memory_entries_success`
- `test_get_memory_entries_filter_by_project`
- `test_get_memory_entries_limit`
- `test_get_memory_entries_tenant_isolation`
- `test_get_memory_entries_exclude_deleted`
- `test_get_memory_entries_empty_results`
- `test_get_memory_entries_invalid_product_404`

### Integration Tests
**Location:** `tests/integration/test_360_memory_ui.py`
- `test_closeout_modal_displays_memory_entries`
- `test_memory_entry_creation_and_retrieval`
- `test_cross_project_memory_visibility`

### Manual Testing
1. Open project in UI
2. Click "Close Out Project" button
3. Verify CloseoutModal shows memory entries
4. Expand entry → verify summary, outcomes, decisions visible
5. Close modal → click again → verify data persists

**Expected Results:**
- Modal displays "X Memory Entries Found"
- Each entry shows sequence number, type, timestamp
- Expansion panels contain summary, outcomes, decisions, git commits

---

## Dependencies and Blockers

### Dependencies
- ✅ `product_memory_entries` table exists (Handover 0390a)
- ✅ `ProductMemoryRepository` exists (Handover 0390b)
- ✅ `close_project_and_update_memory()` MCP tool working (verified)

### No Blockers
All prerequisites are in place. Ready for immediate implementation.

---

## Success Criteria

**Definition of Done:**
- ✅ Backend API endpoint created and tested (7+ unit tests passing)
- ✅ Frontend API service method added
- ✅ CloseoutModal component updated and working
- ✅ Manual test confirms memory entries display correctly
- ✅ Integration tests pass
- ✅ Tenant isolation verified (no cross-tenant leakage)
- ✅ Code committed with descriptive message
- ✅ CLAUDE.md updated (if needed)
- ✅ This handover document updated with completion summary

---

## Rollback Plan

**If Things Go Wrong:**
1. **Backend Errors:**
   - Revert `api/endpoints/products/memory.py` creation
   - Remove router registration from `__init__.py`
   - Frontend will continue showing "No entries" (existing behavior)

2. **Frontend Errors:**
   - Revert `CloseoutModal.vue` changes
   - Remove `getMemoryEntries` from `api.js`
   - Modal returns to broken state (acceptable for rollback)

3. **Database Issues:**
   - No schema changes in this handover
   - Safe to rollback code without migration

**No Data Loss Risk:** This handover only adds read operations. No writes to database.

---

## Additional Resources

### Related Handovers
- **0390 Series**: 360 Memory Normalization (moved from JSONB to table)
- **0390a**: Added `product_memory_entries` table
- **0390b**: Switched reads to table via `ProductMemoryRepository`
- **0390c**: Stopped JSONB writes
- **0390d**: Deprecated JSONB column
- **0700c**: Removed `Product.product_memory.sequential_history` JSONB array

### Documentation
- [360 Memory Management](docs/features/360_MEMORY_MANAGEMENT.md)
- [Product Memory Repository](src/giljo_mcp/database/repositories/product_memory_repository.py)
- [Context Management v2.0](CLAUDE.md#context-management-v30---on-demand-fetch)

### Database Schema Reference
- Table: `product_memory_entries`
- Indexes: `idx_pme_tenant_product`, `idx_pme_sequence`, `idx_pme_project`, `idx_pme_type`
- Foreign Keys: `product_id` (CASCADE DELETE), `project_id` (SET NULL)

### GitHub Issues
- (None - this is a bug fix, not a feature request)

---

## Implementation Notes

### Why Product-Scoped (Not Project-Scoped)?
- **Projects are ephemeral** - create → work → close → archive
- **Products accumulate knowledge** - persistent across multiple projects
- **Orchestrators need history** - "What happened in the last 5 projects on this Product?"
- **Each entry remembers its project** - via `project_id` FK

### Tenant Isolation
- All queries MUST filter by `tenant_key` from `current_user`
- Product owns tenant_key (inherited from user at creation)
- Memory entries inherit tenant_key from product
- No cross-tenant leakage possible (FK constraints + query filters)

### Performance Considerations
- Table has proper indexes (`idx_pme_tenant_product`, `idx_pme_sequence`)
- Default limit of 10 entries (configurable)
- Deleted entries excluded by default (WHERE deleted_by_user = false)
- Expected query time: <50ms for 100 entries

---

## Progress Updates

### 2026-02-07 - Claude Sonnet 4.5 (Diagnostic Agent)
**Status:** Ready for Implementation
**Diagnosis Complete:**
- Root cause identified (obsolete JSONB field reads)
- Database verified (entry exists in `product_memory_entries` table)
- Architecture confirmed (product-scoped by design)
- Two bugs documented (backend endpoint + frontend component)
- Implementation plan created (3 phases, TDD approach)
- No blockers - ready for immediate implementation

**Next Steps:**
- Spawn tdd-implementor agent for Phase 1 (backend endpoint)
- Spawn backend-integration-tester agent for Phase 3 (E2E tests)
- User approval for implementation

---

**Questions for User:**
1. Should we add pagination (offset/limit) for products with 100+ memory entries?
2. Should deleted entries be accessible via `?include_deleted=true` parameter?
3. Any additional fields needed in the API response?
