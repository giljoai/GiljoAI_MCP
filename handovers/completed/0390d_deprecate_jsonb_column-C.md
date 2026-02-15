# Handover 0390d: Deprecate JSONB Column

**Part 4 of 4** in the 360 Memory JSONB Normalization series (0390)
**Date**: 2026-01-18
**Status**: Ready for Implementation
**Complexity**: Low-Medium
**Estimated Duration**: 3-4 hours
**Branch**: `0390-360-memory-normalization`
**Prerequisite**: 0390c Complete (all writes to table)

---

## 1. EXECUTIVE SUMMARY

### Mission
Mark `Product.product_memory.sequential_history` as deprecated, clean up any remaining references, update documentation, and prepare for future column removal.

### Context
After 0390c, the normalized table is the single source of truth - no code reads or writes to `sequential_history` JSONB. This handover marks the field as deprecated and updates all documentation.

### Why This Matters
- **Clear Signal**: Future developers know not to use JSONB
- **Clean Codebase**: Remove dead code referencing JSONB
- **Documentation**: Accurate docs for production
- **v4.0 Ready**: Column can be dropped in next major version

### Success Criteria
- [ ] JSONB field marked deprecated in code comments
- [ ] No code reads sequential_history from JSONB
- [ ] No code writes sequential_history to JSONB
- [ ] All tests pass (100% green)
- [ ] CLAUDE.md updated
- [ ] Handover catalogue updated
- [ ] Branch merged to master

---

## 2. TECHNICAL CONTEXT

### What Stays in JSONB

The `Product.product_memory` JSONB column is **NOT** being dropped. Only `sequential_history` is deprecated.

**Remaining JSONB fields** (still used):
```json
{
  "git_integration": {
    "enabled": true,
    "repo_name": "...",
    "repo_owner": "...",
    "access_token": "..."
  },
  "sequential_history": []  // DEPRECATED - use product_memory_entries table
}
```

### What's Being Deprecated

The `sequential_history` array within `product_memory`. After this handover:
- Field exists but is always `[]` (empty)
- All data lives in `product_memory_entries` table
- Future v4.0 migration will remove field entirely

---

## 3. SCOPE

### In Scope

1. **Code Comments**
   - Add deprecation notice to `Product` model
   - Add comments in relevant files

2. **Remove Dead Code**
   - Any remaining JSONB access patterns
   - Old fallback logic

3. **Documentation Updates**
   - CLAUDE.md - 360 Memory Management section
   - docs/360_MEMORY_MANAGEMENT.md
   - Handover catalogue (mark 0390 complete)

4. **Final Verification**
   - Full regression test suite
   - Manual E2E testing
   - Performance comparison

5. **Git Operations**
   - Commit all changes
   - Create PR (if applicable)
   - Merge to master

### Out of Scope
- Actually dropping the JSONB column (v4.0 task)
- Modifying git_integration handling

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Add Deprecation Comments (30 minutes)

#### 4a. Product Model

**File**: `src/giljo_mcp/models/products.py`

Add comment to `product_memory` column:

```python
product_memory = Column(
    JSONB,
    nullable=True,
    comment="Product memory storage. NOTE: 'sequential_history' field is DEPRECATED "
            "as of v3.3 (Handover 0390). Use product_memory_entries table instead. "
            "Only 'git_integration' config remains in use. "
            "WILL BE MODIFIED in v4.0 to remove sequential_history."
)
```

#### 4b. ProductMemoryEntry Model

**File**: `src/giljo_mcp/models/product_memory_entry.py`

Add module docstring update:

```python
"""
ProductMemoryEntry Model (Handover 0390a)

Normalized table for 360 memory entries.

REPLACES: Product.product_memory.sequential_history JSONB array (DEPRECATED in 0390).

This table is the SINGLE SOURCE OF TRUTH for 360 memory entries as of v3.3.
"""
```

---

### Phase 2: Remove Dead Code (1 hour)

Search for and remove any remaining JSONB patterns:

```bash
# Find remaining sequential_history references
grep -rn "sequential_history" src/giljo_mcp/
grep -rn "sequential_history" api/
grep -rn "sequential_history" frontend/src/

# Find flag_modified for product_memory (should only be for git_integration)
grep -rn 'flag_modified.*product_memory' src/giljo_mcp/
```

**Expected Results**:
- Only git_integration related code should remain
- No sequential_history reads/writes
- No fallback patterns

**Clean Up**:
- Remove commented-out JSONB code
- Remove unused imports
- Remove dead test helpers

---

### Phase 3: Update Documentation (1 hour)

#### 3a. CLAUDE.md

**File**: `CLAUDE.md`

Update "360 Memory Management" section:

```markdown
## 360 Memory Management

**Architecture**: Normalized `product_memory_entries` table (v3.3+, Handover 0390)

**DEPRECATED**: `Product.product_memory.sequential_history` JSONB array is deprecated.
Do not read from or write to this field. Use the table via `ProductMemoryRepository`.

**Data Structure** (Normalized Table):
- `product_memory_entries` table with FK to products and projects
- Cascade delete when product deleted
- Soft-delete (SET NULL) when project deleted
- Proper indexes for query performance

**MCP Tools**:
- `close_project_and_update_memory()` - Creates entry in table
- `write_360_memory()` - Creates entry in table

**Git Integration**: Stored in `Product.product_memory.git_integration` (remains in JSONB).
```

#### 3b. 360_MEMORY_MANAGEMENT.md

**File**: `docs/360_MEMORY_MANAGEMENT.md`

Update to reflect normalized architecture.

#### 3c. Handover Catalogue

**File**: `handovers/handover_catalogue.md`

Add entry for 0390 series:

```markdown
### 360 Memory Normalization (0390 Series)
| ID | Title | Status |
|----|-------|--------|
| 0390 | 360 Memory Normalization Master Plan | **COMPLETE** |
| 0390a | Add Product Memory Entries Table | **COMPLETE** |
| 0390b | Switch Reads to Table | **COMPLETE** |
| 0390c | Stop JSONB Writes | **COMPLETE** |
| 0390d | Deprecate JSONB Column | **COMPLETE** |

> **Result**: product_memory_entries table is single source of truth.
> JSONB sequential_history deprecated, will be removed in v4.0.
```

---

### Phase 4: Final Verification (1 hour)

#### 4a. Full Test Suite

```bash
# Run all tests
pytest tests/ -v --tb=short

# Check coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=term

# Ensure no failures
pytest tests/ --tb=no -q | grep -E "passed|failed"
```

**Expected**: All tests pass, coverage >80%

#### 4b. Manual E2E Testing

1. **Create new project**
   - Verify project created successfully

2. **Close project with memory**
   - Verify entry appears in table
   - Verify JSONB NOT modified

3. **Write 360 memory**
   - Verify entry in table
   - Verify JSONB NOT modified

4. **View 360 memory in UI**
   - Verify entries display correctly
   - Verify git history shows (if configured)

5. **Delete project**
   - Verify entries marked as deleted (not removed)
   - Verify entries still queryable with include_deleted=true

6. **Delete product**
   - Verify entries cascade deleted

#### 4c. Performance Comparison

```bash
# Time a 360 memory query (should be equal or faster)
# Before: JSONB iteration
# After: Table query with index
```

---

### Phase 5: Git Operations (30 minutes)

#### 5a. Commit All Changes

```bash
git add .
git commit -m "feat(0390): Complete 360 Memory JSONB to Table Migration

Migrates Product.product_memory.sequential_history JSONB array to
normalized product_memory_entries table.

- 0390a: Created table, model, repository, backfill migration
- 0390b: Switched all reads to table
- 0390c: Switched all writes to table
- 0390d: Deprecated JSONB field, updated docs

BREAKING: sequential_history JSONB is deprecated.
Use ProductMemoryRepository for all 360 memory operations.

```

#### 5b. Merge to Master

```bash
git checkout master
git merge 0390-360-memory-normalization
git push origin master
```

#### 5c. Archive Handovers

```bash
# Move completed handovers to completed/
mv handovers/0390_360_memory_normalization.md handovers/completed/0390_360_memory_normalization-C.md
mv handovers/0390a_add_memory_entries_table.md handovers/completed/0390a_add_memory_entries_table-C.md
mv handovers/0390b_switch_reads_to_table.md handovers/completed/0390b_switch_reads_to_table-C.md
mv handovers/0390c_stop_jsonb_writes.md handovers/completed/0390c_stop_jsonb_writes-C.md
mv handovers/0390d_deprecate_jsonb_column.md handovers/completed/0390d_deprecate_jsonb_column-C.md

git add handovers/
git commit -m "docs: Archive completed 0390 handover series"
git push
```

---

## 5. TESTING REQUIREMENTS

### Regression Tests
- Full test suite must pass
- No new failures introduced

### Manual Tests
- Complete E2E workflow
- All CRUD operations

---

## 6. ROLLBACK PLAN

### Rollback Triggers
- Critical functionality broken
- Data loss detected

### Rollback Steps
This handover is mostly documentation - no code to roll back.
If needed, revert documentation commits.

---

## 7. FILES INDEX

### Files to MODIFY

| File | Changes |
|------|---------|
| `src/giljo_mcp/models/products.py` | Deprecation comment |
| `src/giljo_mcp/models/product_memory_entry.py` | Docstring update |
| `CLAUDE.md` | 360 Memory section |
| `docs/360_MEMORY_MANAGEMENT.md` | Architecture update |
| `handovers/handover_catalogue.md` | Add 0390 series |

### Files to CLEAN
- Remove any dead JSONB code found in Phase 2

---

## 8. SUCCESS CRITERIA

### Functional
- [ ] All tests pass (100% green)
- [ ] Manual E2E testing complete
- [ ] No JSONB reads/writes for sequential_history

### Quality
- [ ] Code properly commented
- [ ] No dead code remaining
- [ ] Linting passes

### Documentation
- [ ] CLAUDE.md updated
- [ ] 360_MEMORY_MANAGEMENT.md updated
- [ ] Handover catalogue updated
- [ ] All handovers archived

### Git
- [ ] Branch merged to master
- [ ] Handovers moved to completed/

---

## CLOSEOUT NOTES

**Status**: [NOT STARTED]

*To be filled upon completion*

---

## CHAIN COMPLETE

This is the **FINAL** handover in the 0390 series. When complete:

1. Verify all success criteria met
2. Merge to master
3. Archive all handovers
4. Update handover catalogue
5. Celebrate! The 360 Memory is now production-grade.

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
