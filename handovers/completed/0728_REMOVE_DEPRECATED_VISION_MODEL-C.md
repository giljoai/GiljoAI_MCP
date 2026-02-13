# Handover 0728: Remove Deprecated Vision Model

**Series:** 0700 Code Cleanup (Missed Deprecation)
**Priority:** P3 - LOW (Technical debt cleanup)
**Estimated Effort:** 30-60 minutes
**Prerequisites:** Master branch merged (0700 cleanup complete)
**Status:** READY
**Agent Strategy:** Orchestrator with subagents for each phase

MISSION: Remove the deprecated Vision model (project-centric vision architecture) that was replaced by VisionDocument (product-centric) but never cleaned up

WHY THIS MATTERS:
- Dead code removal - Vision model is 100% orphaned
- Architectural consistency - all vision features now use VisionDocument
- Database cleanup - drop unused `visions` table
- Code clarity - remove confusing legacy model

DISCOVERY: Found during post-0700 audit of products.py (8 deprecation warnings flagged)

---

## Background: Vision → VisionDocument Migration

### OLD Architecture (DEPRECATED):
- **Model:** `Vision` (src/giljo_mcp/models/products.py lines 584-622)
- **Table:** `visions`
- **Scope:** Project-centric (vision belongs to project)
- **Relationship:** `Project.visions`

### NEW Architecture (CURRENT):
- **Model:** `VisionDocument` (src/giljo_mcp/models/products.py lines 356-582)
- **Table:** `vision_documents`
- **Scope:** Product-centric (vision belongs to product)
- **Relationship:** `Product.vision_documents`

### Migration Completed: Handover 0043 (Multi-Vision Document Support)
- VisionDocument model created
- All vision features migrated
- Vision model should have been removed but wasn't

---

## Code Analysis Results (Why It's Safe)

### Where Vision is Used (ONLY 2 Places):

**1. project_service.py - Deletion Cleanup ONLY:**
```python
# Lines 2305-2314
# This ONLY deletes legacy Vision records during project deletion
vision_stmt = select(Vision).where(Vision.project_id == project_id)
visions = (await session.execute(vision_stmt)).scalars().all()
for vision in visions:
    await session.delete(vision)
deleted_counts["visions"] = len(visions)
```

**2. test_project_deletion_cascade.py - Test Code ONLY:**
```python
# Creates Vision objects for testing deletion cascade
vision = Vision(
    project_id=project.id,
    tenant_key=cascade_test_tenant_key,
    document_name="test_vision.md",
    chunk_number=1,
    content="Test vision content",
)
```

### Where Vision is NOT Used:
- ❌ **ZERO** production code creates Vision objects
- ❌ **ZERO** code accesses `project.visions` relationship
- ❌ **ZERO** vision features use Vision model
- ❌ **ZERO** API endpoints reference Vision

**Conclusion:** Vision model is 100% DEAD CODE - safe to remove.

---

## Phase 1: Research & Validation (15 minutes)

**Agent:** deep-researcher

**Objective:** Triple-check that Vision model is truly unused and safe to remove.

**Research Tasks:**
1. **Code Search:**
   - Find all imports of Vision (should be 2: project_service.py, tests)
   - Find all Vision() instantiations (should be tests only)
   - Find all .visions relationship accesses (should be ZERO)
   - Verify VisionDocument is the active model

2. **Database Schema Check:**
   - Verify `visions` table exists in schema
   - Document table structure for migration
   - Check for any foreign key constraints

3. **Test Analysis:**
   - Identify tests that use Vision model
   - Classify as: delete-safe, needs update, or legacy cleanup test

4. **Impact Assessment:**
   - List all files that will be modified
   - Identify any risks or edge cases
   - Confirm no production features depend on Vision

**Deliverables:**
- Validation report confirming Vision is unused
- List of files to modify (expected: 5 files)
- Migration strategy for `visions` table
- Test update strategy

**Success Criteria:**
- ✅ Confirmed Vision is ONLY used in deletion code and tests
- ✅ No production features depend on Vision
- ✅ Clear removal plan documented
- ✅ Ready for Phase 2 (Implementation)

---

## Phase 2: Implementation (15-20 minutes)

**Agent:** tdd-implementor

**Objective:** Remove Vision model and update code following TDD approach.

**TDD Workflow:**

### Step 1: Update Tests FIRST (5-10 minutes)

**Update test_project_deletion_cascade.py:**
```python
# Option A: Remove Vision-related tests entirely
# - Remove Vision import
# - Remove vision fixtures
# - Remove vision test methods
# - Update comprehensive test to not check Vision

# Option B: Mark as legacy cleanup tests
# - Add pytest.mark.skip decorator
# - Add comment: "Legacy Vision model removed in 0728"
```

**Update other test files if needed:**
- Check tests/utils/tools_helpers.py (might create Vision objects)
- Search for any other test files importing Vision

### Step 2: Remove Production Code (5-10 minutes)

**File 1: src/giljo_mcp/models/products.py**
```python
# Delete lines 584-622 (entire Vision class)
# BEFORE: 623 lines
# AFTER: ~583 lines
```

**File 2: src/giljo_mcp/models/__init__.py**
```python
# Remove from imports:
from src.giljo_mcp.models.products import Product, VisionDocument  # Remove Vision

# Remove from __all__:
"Vision",  # DELETE THIS LINE
```

**File 3: src/giljo_mcp/models/projects.py**
```python
# Remove relationship:
visions = relationship("Vision", back_populates="project", cascade="all, delete-orphan")
# DELETE THIS LINE
```

**File 4: src/giljo_mcp/services/project_service.py**
```python
# Line 2238 - Remove import:
from src.giljo_mcp.models.products import Vision  # DELETE

# Lines 2233 - Remove from deleted_counts dict:
"visions": 0,  # DELETE

# Lines 2305-2314 - Remove deletion code:
# DELETE entire Vision deletion block:
# vision_stmt = select(Vision).where(...)
# visions = (await session.execute(vision_stmt)).scalars().all()
# for vision in visions:
#     await session.delete(vision)
# deleted_counts["visions"] = len(visions)

# Line 2350 - Remove from log message:
f"{deleted_counts['visions']} visions, "  # DELETE
```

**File 5: tests/integration/test_handover_0035_database_schema.py**
```python
# If this test validates schema tables, remove "visions" from expected tables list
```

### Step 3: Run Tests to Confirm Changes (5 minutes)

```bash
# Import tests (should fail if Vision still imported anywhere)
pytest tests/unit/test_models.py -v

# Project service tests (deletion code updated)
pytest tests/services/test_project_service.py -v

# Integration tests
pytest tests/integration/ -v -k vision
```

**Expected:** Some tests may fail - this is TDD RED phase. Note failures for Phase 3.

---

## Phase 3: Database Migration (5-10 minutes)

**Agent:** database-expert

**Objective:** Create migration to drop `visions` table safely.

**Migration Strategy:**

**Check if table has data:**
```sql
-- If data exists, document it (likely none or very old)
SELECT COUNT(*) FROM visions;
SELECT * FROM visions LIMIT 5;
```

**Create migration:**
```python
# alembic/versions/YYYYMMDD_drop_visions_table.py

def upgrade():
    # Check if table exists (might not in fresh installs)
    op.execute("""
        DROP TABLE IF EXISTS visions CASCADE;
    """)

def downgrade():
    # Not implementing downgrade - Vision model removed from codebase
    # If rollback needed, restore from previous migration
    pass
```

**Alternative (if not using Alembic):**
```python
# Update install.py or database initialization
# Remove visions table creation code if present
```

**Validation:**
```bash
# After migration:
psql -U postgres -d giljo_mcp -c "\dt visions"
# Expected: "Did not find any relation named 'visions'"
```

---

## Phase 4: Validation & Testing (10-15 minutes)

**Agent:** backend-integration-tester

**Objective:** Comprehensive validation that removal didn't break anything.

### Test Suite Execution:

```bash
# 1. Unit tests
pytest tests/unit/ -v

# 2. Service tests (especially project_service)
pytest tests/services/test_project_service.py -v

# 3. Integration tests
pytest tests/integration/ -v

# 4. Model tests
pytest tests/unit/test_models.py -v

# 5. Check for any remaining Vision references
grep -r "Vision[^D]" src/ tests/ --include="*.py" | grep -v VisionDocument
# Expected: Should find ZERO references to Vision (only VisionDocument)
```

### Manual Validation:

**1. Import Check:**
```python
# Verify Vision can't be imported
python -c "from src.giljo_mcp.models import Vision"
# Expected: ImportError
```

**2. VisionDocument Still Works:**
```python
# Verify VisionDocument is unaffected
python -c "from src.giljo_mcp.models import VisionDocument; print('OK')"
# Expected: OK
```

**3. Project Deletion Works:**
```bash
# Run project deletion tests
pytest tests/integration/test_nuclear_delete_project.py -v
# Expected: All passing (Vision code removed from deletion)
```

### Success Criteria:
- ✅ All tests passing
- ✅ Zero references to Vision in production code
- ✅ VisionDocument model unaffected
- ✅ Project deletion still works (without Vision cleanup)
- ✅ No import errors
- ✅ Database migration successful (if applicable)

---

## Phase 5: Fix & Iteration (if needed)

**Agent:** tdd-implementor (resume if issues found)

**If tests fail:**
1. Analyze failure root cause
2. Determine if it's expected (test needs update) or bug (code needs fix)
3. Apply fix
4. Re-run tests
5. Repeat until all passing

**Common issues:**
- Test still imports Vision → Update test
- Schema validation expects visions table → Update schema test
- Deletion test fails → Verify test doesn't expect Vision deletion

---

## Phase 6: Commit (5 minutes)

**Agent:** Current orchestrator (don't spawn subagent for commit)

**Commit Message:**
```bash
git add -A
git commit -m "refactor(0728): Remove deprecated Vision model (project-centric visions)

Vision model was replaced by VisionDocument (product-centric) in Handover 0043
but never removed. This cleanup removes the orphaned model.

Changes:
- Remove Vision model from products.py (39 lines)
- Remove Vision from models exports
- Remove project.visions relationship
- Remove Vision deletion code from project_service.py
- Update tests to not reference Vision
- Drop visions table (migration created)

Analysis confirmed:
- ZERO production code creates Vision objects
- ZERO code accesses project.visions relationship
- Vision ONLY used in deletion cleanup and tests
- 100% safe to remove

Series: 0700 Code Cleanup (missed deprecation)
Risk: VERY LOW (dead code removal)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Pre-commit validation:**
```bash
# Ensure pre-commit hooks pass
pre-commit run --all-files
```

---

## Files Modified Summary

**Modified (5 files):**
1. `src/giljo_mcp/models/products.py` - Remove Vision class (39 lines deleted)
2. `src/giljo_mcp/models/__init__.py` - Remove Vision from exports (2 lines)
3. `src/giljo_mcp/models/projects.py` - Remove visions relationship (1 line)
4. `src/giljo_mcp/services/project_service.py` - Remove deletion code (13 lines)
5. `tests/integration/test_project_deletion_cascade.py` - Update/remove Vision tests

**Created (1 file):**
6. Migration file (if using Alembic) - Drop visions table

**Total lines removed:** ~60 lines of dead code

---

## Success Criteria (Overall)

**CODE:**
- ✅ Vision model removed from products.py
- ✅ Vision not exported from models package
- ✅ project.visions relationship removed
- ✅ Vision deletion code removed from project_service.py
- ✅ Zero grep matches for "Vision[^D]" in src/ (excluding VisionDocument)

**TESTS:**
- ✅ All tests passing
- ✅ Vision-related tests updated or removed
- ✅ Project deletion tests still pass
- ✅ No import errors for Vision

**DATABASE:**
- ✅ visions table dropped (or migration created)
- ✅ VisionDocument and vision_documents table unaffected

**GIT:**
- ✅ All changes committed
- ✅ Pre-commit hooks passing
- ✅ Commit message descriptive

---

## Risks & Mitigations

**Risk 1: Database has old Vision records**
- **Likelihood:** LOW (architecture changed long ago)
- **Impact:** LOW (deletion code removed, but table drop handles it)
- **Mitigation:** Migration includes IF EXISTS, won't fail if no data

**Risk 2: Hidden Vision usage not found by grep**
- **Likelihood:** VERY LOW (research phase comprehensive)
- **Impact:** MEDIUM (would break feature)
- **Mitigation:** Comprehensive test suite catches any issues

**Risk 3: Tests break unexpectedly**
- **Likelihood:** MEDIUM (tests reference Vision)
- **Impact:** LOW (just update tests)
- **Mitigation:** TDD approach - update tests first

---

## Rollback Plan

**If issues discovered after merge:**

```bash
# Revert the commit
git revert <commit-hash>

# Or restore Vision model
git checkout HEAD~1 src/giljo_mcp/models/products.py
git checkout HEAD~1 src/giljo_mcp/services/project_service.py
# etc.
```

**Database rollback:**
```sql
-- Would need to recreate table from old migration
-- Not recommended - better to fix forward
```

---

## Definition of Done

1. ✅ Phase 1 Research complete - Vision confirmed unused
2. ✅ Phase 2 Implementation complete - Code removed
3. ✅ Phase 3 Migration complete - Table dropped
4. ✅ Phase 4 Validation complete - All tests passing
5. ✅ Phase 5 Fixes applied (if any issues found)
6. ✅ Phase 6 Committed with pre-commit hooks passing
7. ✅ Zero Vision references in production code
8. ✅ VisionDocument functionality unaffected

---

**Created:** 2026-02-07
**Status:** READY
**Priority:** P3 - LOW (cleanup, not blocking)
**Estimated Total:** 30-60 minutes with subagent coordination

---

## Notes for Orchestrator

**Subagent Coordination:**
- Phase 1: deep-researcher (validation)
- Phase 2: tdd-implementor (removal)
- Phase 3: database-expert (migration)
- Phase 4: backend-integration-tester (validation)
- Phase 5: tdd-implementor (fixes if needed)
- Phase 6: Orchestrator handles commit (don't spawn subagent)

**Communication Pattern:**
- Each phase reports completion to orchestrator
- Orchestrator reviews deliverables before proceeding
- If validation finds issues, loop back to implementation

**Quality Standards:**
- All tests must pass before commit
- Zero Vision references in production code
- VisionDocument must remain functional
- Pre-commit hooks must pass

This is straightforward cleanup - the research phase already confirmed it's safe!
