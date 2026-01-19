# Handover 0423: Session and TemplateAugmentation Dead Code Cleanup

**Date**: 2026-01-19
**Priority**: MEDIUM
**Status**: NOT STARTED
**Estimated Effort**: 2-4 hours
**Related**: Handover 0371 (Dead Code Cleanup Project), Handover 0422 (Dead Token Budget Cleanup)

---

## Executive Summary

Investigation revealed two database tables that exist in schema but are never populated with data:

1. **Session table** (`sessions`) - Designed but never implemented. Model exists, table exists, but NO code creates session records. The table is effectively a phantom - ready to receive data but never called upon.

2. **TemplateAugmentation table** (`template_augmentations`) - Table is dead, but the CONCEPT of augmentations is alive. The MCP tool `create_template_augmentation` was deleted (marked "Not in vision"). Current code uses in-memory augmentation dicts (e.g., `_create_serena_augmentation()` returns dict, not DB record) which are passed to template rendering.

**Impact**: Zero user data at risk. These tables are unpopulated structural artifacts from incomplete implementations.

**Key Finding**: The Session table has cascade delete relationships but serves no functional purpose. TemplateAugmentation's database persistence was abandoned in favor of runtime-only augmentation objects.

---

## Part A: Dead Code Removal (IMPLEMENT FIRST)

### Phase A.1: Remove Session Table and Model

**Location**: `src/giljo_mcp/models/projects.py:152`

**Action Plan**:
1. Delete `Session` model class from `models/projects.py`
2. Remove any foreign key relationships pointing to `sessions` table
3. Remove cascade delete relationships (`cascade="all, delete-orphan"`)
4. Update `models/__init__.py` to remove Session export (if present)
5. Update baseline migration (`migrations/baseline_schema.py`) to remove table creation

**Files to Modify**:
```
src/giljo_mcp/models/projects.py          # Delete Session model
src/giljo_mcp/models/__init__.py          # Remove Session export
migrations/baseline_schema.py             # Remove sessions table
```

**Verification**:
- Search codebase for `from.*Session` imports (exclude AsyncSession, MCPSession)
- Verify no API endpoints reference Session
- Verify no service methods create Session objects
- Confirm table removal in migration

**Risk**: NONE - No code creates Session records, no user data exists

---

### Phase A.2: Remove TemplateAugmentation Table and Model

**Location**: `src/giljo_mcp/models/templates.py:199`

**Action Plan**:
1. Delete `TemplateAugmentation` model class from `models/templates.py`
2. Remove from `models/__init__.py` exports
3. Update baseline migration to remove `template_augmentations` table
4. Verify in-memory augmentation system remains intact (dict-based, not DB-backed)

**Files to Modify**:
```
src/giljo_mcp/models/templates.py         # Delete TemplateAugmentation model
src/giljo_mcp/models/__init__.py          # Remove export
migrations/baseline_schema.py             # Remove table
```

**CRITICAL - DO NOT REMOVE**:
- In-memory augmentation logic (dict creation and passing)
- `_create_serena_augmentation()` and similar functions
- Template rendering code that accepts augmentation dicts

**Frontend Note**:
- `TemplateManager.vue` has "Add runtime augmentations" label
- This refers to in-memory augmentations (feature works, UI may need label update)
- Frontend does NOT interact with TemplateAugmentation table

**Verification**:
- Search for `TemplateAugmentation` class references
- Verify no API endpoints query or create TemplateAugmentation
- Confirm in-memory augmentation system still works
- Check template rendering accepts dict augmentations

**Risk**: LOW - Table is unpopulated, in-memory system is separate

---

### Phase A.3: Migration and Verification

**Migration Steps**:
1. Backup database before migration:
   ```bash
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres -d giljo_mcp > backups/pre_0423_backup.sql
   ```

2. Update baseline migration (`migrations/baseline_schema.py`):
   - Remove `sessions` table creation
   - Remove `template_augmentations` table creation
   - Remove any foreign key constraints referencing these tables

3. Run fresh migration test:
   ```bash
   # Drop and recreate test database
   python install.py
   ```

**Verification Checklist**:
- [ ] `python -m pytest tests/ -x` passes
- [ ] `python -c "from src.giljo_mcp.models import *"` succeeds (no import errors)
- [ ] Server starts without errors: `python startup.py --dev`
- [ ] Database schema shows tables removed:
  ```bash
  PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt" | grep -E "(sessions|template_augmentations)"
  # Should return NO RESULTS
  ```
- [ ] Frontend builds successfully: `cd frontend && npm run build`
- [ ] Template rendering with in-memory augmentations still works

**Rollback Plan**:
- Git revert commits
- Restore database from `pre_0423_backup.sql` if needed

---

## Part B: Template Augmentation Future Planning (RESEARCH ONLY)

**Current State**:
- ✅ In-memory augmentations work (dicts passed to template rendering)
- ✅ Functions like `_create_serena_augmentation()` return dicts
- ✅ Template rendering accepts augmentation dicts as parameters
- ❌ No database persistence (table exists but never used)
- ❌ No MCP tool to create augmentations (deleted as "not in vision")

**Question for Product Owner**:
> Is persistent storage of template augmentations needed for future features?

**Option A: Keep In-Memory Only (Current Working State)**
- Pros: Simple, works today, no database overhead
- Cons: Augmentations must be recreated each session
- Use Case: Runtime-only augmentations (e.g., Serena-specific instructions)

**Option B: Design Database-Backed Storage (Future Enhancement)**
- Pros: Persistent augmentations, reusable across sessions, user-customizable
- Cons: Requires schema redesign, API endpoints, service layer
- Use Case: User saves custom agent augmentations for reuse

**Recommendation**:
Unless there's a business requirement for persistent augmentations, Option A (current state) is sufficient. This handover removes the dead table structure but preserves the working in-memory system.

**No implementation in this handover** - this section is planning only.

---

## Part C: Export Tool Impact Assessment

**Session Table**:
- Export tool should NOT export sessions (table is dead, always empty)
- No changes needed to export tool (already skips empty tables)

**TemplateAugmentation Table**:
- Export tool should NOT export template_augmentations (table is dead)
- No changes needed to export tool (already skips empty tables)

**360 Memory**:
- ✅ 360 Memory uses `ProductMemoryEntry` table (normalized, Handover 0390)
- ✅ NOT connected to Session table
- ✅ No impact from Session/TemplateAugmentation removal

---

## Risk Assessment

| Component | Risk Level | Rationale |
|-----------|------------|-----------|
| Session Removal | NONE | No code creates sessions, no user data exists |
| TemplateAugmentation Removal | LOW | Table unpopulated, in-memory system unaffected |
| Migration Changes | LOW | Fresh installs only (baseline migration) |
| Database Integrity | NONE | No foreign key dependencies from active tables |
| Frontend Impact | NONE | Frontend doesn't query these tables |
| API Impact | NONE | No endpoints reference these tables |

---

## Success Criteria

1. ✅ `Session` model deleted from `models/projects.py`
2. ✅ `TemplateAugmentation` model deleted from `models/templates.py`
3. ✅ Both tables removed from baseline migration
4. ✅ No imports of deleted models remain in codebase
5. ✅ All tests pass (`pytest tests/ -x`)
6. ✅ Server starts without errors
7. ✅ Fresh database creation works (`python install.py`)
8. ✅ Frontend builds successfully
9. ✅ In-memory augmentation system still functional
10. ✅ No references to `sessions` or `template_augmentations` tables in schema

---

## Execution Notes

**Tools Required**:
- Database Expert Agent (schema changes)
- TDD Implementor (test verification)
- Documentation Manager (update architecture docs if needed)

**Estimated Timeline**:
- Phase A.1 (Session removal): 45 minutes
- Phase A.2 (TemplateAugmentation removal): 45 minutes
- Phase A.3 (Migration + verification): 90 minutes
- **Total**: 2-4 hours

**Dependencies**:
- None (isolated cleanup, no blocking handovers)

**Commit Strategy**:
1. Commit 1: Remove Session model and update migration
2. Commit 2: Remove TemplateAugmentation model and update migration
3. Commit 3: Verification (test results, schema confirmation)

---

## Related Documentation

- [Handover 0371](0371_dead_code_cleanup_project.md) - Dead Code Cleanup Project
- [Handover 0422](0422_dead_token_budget_cleanup.md) - Dead Token Budget Cleanup
- [Handover 0390](completed/0390_normalize_product_memory_table.md) - 360 Memory Normalization
- [docs/architecture/migration-strategy.md](../docs/architecture/migration-strategy.md) - Migration Strategy

---

*Document created 2026-01-19 as part of ongoing dead code cleanup initiative*
