# Kickoff Prompt: 0728 Remove Deprecated Vision Model

**Agent Role:** orchestrator-coordinator
**Estimated Time:** 30-60 minutes (across 6 phases)
**Prerequisites:** Read this entire prompt, then execute phases sequentially

---

## Your Mission

You are an **orchestrator-coordinator** agent executing **Handover 0728: Remove Deprecated Vision Model**.

Your goal is to coordinate specialized subagents through a 6-phase cleanup workflow to remove the deprecated Vision model (project-centric vision architecture) that was replaced by VisionDocument but never removed.

**This is 0700-level cleanup** - removing dead code that should have been deleted during the original deprecation work.

---

## Critical Context

**Read the full handover specification:**
`F:\GiljoAI_MCP\handovers\0728_REMOVE_DEPRECATED_VISION_MODEL.md`

**Project:** GiljoAI MCP v1.0 - Multi-tenant agent orchestration server
**Branch:** master (0700 cleanup series just merged)
**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL

**Background:**
- OLD: `Vision` model (project-centric, table: `visions`)
- NEW: `VisionDocument` model (product-centric, table: `vision_documents`)
- Migration completed in Handover 0043, but Vision model never removed
- Code analysis proves Vision is 100% dead code (see handover spec)

---

## 6-Phase Workflow

You will coordinate subagents through these phases:

```
Phase 1: Research & Validation (deep-researcher)
    ↓
Phase 2: Implementation (tdd-implementor)
    ↓
Phase 3: Database Migration (database-expert)
    ↓
Phase 4: Validation & Testing (backend-integration-tester)
    ↓
Phase 5: Fix & Iteration (tdd-implementor, if needed)
    ↓
Phase 6: Commit (YOU handle this, don't spawn subagent)
```

---

## Phase 1: Research & Validation (15 minutes)

### Launch deep-researcher agent

**Agent Task:**
```
Research and validate that the Vision model can be safely removed.

Code Analysis Required:
1. Find ALL imports of Vision (grep "from.*Vision")
2. Find ALL Vision() instantiations (production vs tests)
3. Find ALL .visions relationship accesses
4. Verify VisionDocument is the active replacement

Database Analysis:
1. Check if visions table exists in schema
2. Document table structure
3. Check for foreign key constraints

Test Analysis:
1. Identify tests using Vision model
2. Classify: safe to delete vs needs update

Expected Findings (from handover spec):
- Vision imported in 2 places ONLY (project_service.py, test file)
- ZERO production code creates Vision objects
- Vision ONLY used in deletion cleanup code
- All vision features use VisionDocument

Deliverable: Validation report confirming Vision is 100% dead code
```

**What You Do:**
1. Launch deep-researcher with above prompt
2. Wait for completion
3. Review validation report
4. Confirm findings match handover spec expectations
5. If confirmed safe → Proceed to Phase 2
6. If concerns found → Investigate before proceeding

---

## Phase 2: Implementation (15-20 minutes)

### Launch tdd-implementor agent

**Agent Task:**
```
Remove the deprecated Vision model using TDD approach.

CRITICAL: Follow TDD - update tests FIRST, then code.

Step 1: Update Tests FIRST (10 minutes)
File: tests/integration/test_project_deletion_cascade.py
- Remove Vision import
- Remove vision fixtures
- Remove vision test methods
- Update comprehensive test to not check Vision
- OR mark tests as skipped with pytest.mark.skip

Check: tests/utils/tools_helpers.py (might create Vision)

Step 2: Remove Production Code (10 minutes)

File 1: src/giljo_mcp/models/products.py
- Delete lines 584-622 (entire Vision class)

File 2: src/giljo_mcp/models/__init__.py
- Remove Vision from import statement
- Remove "Vision" from __all__ list

File 3: src/giljo_mcp/models/projects.py
- Remove: visions = relationship("Vision", ...)

File 4: src/giljo_mcp/services/project_service.py
- Line 2238: Remove Vision import
- Line 2233: Remove "visions": 0 from dict
- Lines 2305-2314: Delete Vision deletion block
- Line 2350: Remove visions from log message

Step 3: Run Tests
pytest tests/services/test_project_service.py -v
pytest tests/integration/ -v -k vision

Note failures for Phase 4 validation.

Files Modified: 4-5 files
Lines Removed: ~60 lines
```

**What You Do:**
1. Launch tdd-implementor with above prompt
2. Wait for completion
3. Review files modified
4. Confirm ~60 lines removed from expected files
5. Note any test failures (expected in TDD)
6. Proceed to Phase 3

---

## Phase 3: Database Migration (5-10 minutes)

### Launch database-expert agent

**Agent Task:**
```
Create migration to drop the visions table safely.

Step 1: Check Table Status
Run: psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM visions;"
Document: Does table exist? Any data?

Step 2: Create Migration
If using Alembic:
- Create migration file: drop_visions_table
- Use: DROP TABLE IF EXISTS visions CASCADE;
- Downgrade: Not implementing (model removed from code)

If using install.py:
- Check if table creation code exists
- Remove visions table creation

Step 3: Test Migration
Run migration
Verify: psql -U postgres -d giljo_mcp -c "\dt visions"
Expected: No relation found

Deliverable: Migration created and tested
```

**What You Do:**
1. Launch database-expert with above prompt
2. Wait for completion
3. Verify migration created
4. Confirm table drop successful (or no table existed)
5. Proceed to Phase 4

---

## Phase 4: Validation & Testing (10-15 minutes)

### Launch backend-integration-tester agent

**Agent Task:**
```
Comprehensive validation that Vision removal didn't break anything.

Test Suite Execution:
1. Unit tests: pytest tests/unit/ -v
2. Service tests: pytest tests/services/test_project_service.py -v
3. Integration tests: pytest tests/integration/ -v
4. Model tests: pytest tests/unit/test_models.py -v

Code Search Validation:
grep -r "Vision[^D]" src/ tests/ --include="*.py" | grep -v VisionDocument
Expected: ZERO matches (only VisionDocument should exist)

Import Validation:
python -c "from src.giljo_mcp.models import Vision"
Expected: ImportError

python -c "from src.giljo_mcp.models import VisionDocument; print('OK')"
Expected: OK

Project Deletion Validation:
pytest tests/integration/test_nuclear_delete_project.py -v
Expected: All passing

Success Criteria:
- All tests passing
- Zero Vision references in src/
- VisionDocument unaffected
- Import check confirms Vision gone

Deliverable: Test report with pass/fail status
```

**What You Do:**
1. Launch backend-integration-tester with above prompt
2. Wait for completion
3. Review test report
4. If all passing → Proceed to Phase 6 (Commit)
5. If failures found → Proceed to Phase 5 (Fix)

---

## Phase 5: Fix & Iteration (if needed)

**Only execute if Phase 4 found failures.**

### Resume tdd-implementor agent

**Agent Task:**
```
Fix test failures found in Phase 4 validation.

Context: Phase 4 validation found test failures.
Failures: [LIST FAILURES FROM PHASE 4]

Instructions:
1. Analyze each failure
2. Determine root cause:
   - Test needs update (expected)
   - Code bug (needs fix)
3. Apply fixes
4. Re-run failing tests
5. Repeat until all passing

Common Issues:
- Test still imports Vision → Update import
- Schema validation expects visions → Update schema
- Deletion test expects Vision cleanup → Update test

Deliverable: All tests passing
```

**What You Do:**
1. Launch tdd-implementor with above prompt + failure details
2. Wait for completion
3. Verify all tests now passing
4. If still failing → iterate (provide more context)
5. When all passing → Proceed to Phase 6

---

## Phase 6: Commit (5 minutes)

**YOU handle this phase - DO NOT spawn subagent.**

### Commit Checklist:

**1. Pre-commit validation:**
```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Ensure all changes staged
git add -A

# Verify what's being committed
git status

# Check pre-commit hooks
pre-commit run --all-files
```

**2. Create commit:**
```bash
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
Phases: Research → Implement → Migrate → Validate → Fix → Commit

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**3. Verify commit:**
```bash
git log --oneline -1
git show --stat
```

---

## Success Criteria (Overall)

You are COMPLETE when all of these are true:

**CODE:**
- ✅ Vision model removed from products.py (~39 lines)
- ✅ Vision not exported from models/__init__.py
- ✅ project.visions relationship removed
- ✅ Vision deletion code removed from project_service.py
- ✅ grep "Vision[^D]" src/ returns ZERO matches

**TESTS:**
- ✅ All tests passing (100%)
- ✅ Vision-related tests updated or removed
- ✅ Project deletion tests still pass
- ✅ pytest tests/ -v shows all green

**DATABASE:**
- ✅ visions table dropped (or migration created)
- ✅ vision_documents table unaffected

**GIT:**
- ✅ All changes committed
- ✅ Pre-commit hooks passing
- ✅ Commit message descriptive and complete

---

## Orchestration Guidelines

### Subagent Communication:

**After each phase:**
1. Review subagent deliverables
2. Validate completion criteria met
3. Update progress tracking
4. Proceed to next phase or iterate

**If a phase fails:**
1. Analyze failure reason
2. Provide additional context to subagent
3. Re-run phase or adjust approach
4. Don't proceed until phase successful

**Quality Gates:**
- Phase 1: Must confirm Vision is dead code
- Phase 2: Must modify expected files (~5 files)
- Phase 3: Must handle table drop safely
- Phase 4: Must achieve 100% tests passing
- Phase 5: Must resolve all failures (if any)
- Phase 6: Must pass pre-commit hooks

### Expected Timeline:

- Phase 1 (Research): 15 minutes
- Phase 2 (Implementation): 15-20 minutes
- Phase 3 (Migration): 5-10 minutes
- Phase 4 (Validation): 10-15 minutes
- Phase 5 (Fix): 0-10 minutes (if needed)
- Phase 6 (Commit): 5 minutes

**Total:** 30-60 minutes (as estimated)

---

## Important Notes

1. **TDD is Critical** - Tests must be updated BEFORE code in Phase 2
2. **Don't Skip Validation** - Phase 4 catches issues before commit
3. **Database Safety** - Phase 3 uses IF EXISTS (won't fail if no table)
4. **Commit Yourself** - Don't spawn subagent for Phase 6, you handle it
5. **Quality Over Speed** - Better to iterate in Phase 5 than commit broken code
6. **Pre-commit Required** - Hooks must pass before final commit

---

## Resources

**Critical Files:**
- Handover spec: `handovers/0728_REMOVE_DEPRECATED_VISION_MODEL.md`
- Vision model: `src/giljo_mcp/models/products.py` (lines 584-622)
- Project service: `src/giljo_mcp/services/project_service.py`
- Tests: `tests/integration/test_project_deletion_cascade.py`

**Documentation:**
- `docs/SERVICES.md` - Service layer patterns
- `CLAUDE.md` - Project standards and pre-commit policy

**Git Branch:**
- Current: `master`
- No new branch needed (small cleanup)

---

## Troubleshooting

**If Phase 1 finds Vision is used:**
- STOP immediately
- Re-analyze with user
- Handover spec may be wrong

**If Phase 2 can't find expected files:**
- Code may have changed since analysis
- Use grep to find current locations
- Update phase instructions

**If Phase 4 tests fail:**
- Expected for some tests (Vision removed)
- Proceed to Phase 5 to fix
- Don't panic - this is normal TDD

**If pre-commit hooks fail:**
- Review hook output
- Fix issues (usually formatting)
- Re-run hooks until passing
- NEVER use --no-verify

---

**Ready to start?**

1. Read full handover specification
2. Begin Phase 1: Launch deep-researcher
3. Follow 6-phase workflow sequentially
4. Report completion when committed

Good luck! This should be straightforward - the analysis already confirmed it's safe.
