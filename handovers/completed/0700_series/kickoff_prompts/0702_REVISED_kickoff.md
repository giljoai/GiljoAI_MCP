# Kickoff: Handover 0702-REVISED - Orphan Module Cleanup

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06

---

## Mission Statement

Delete orphan modules (zero dependents). Architecture analysis found **271 orphan modules**. This is Phase 1 of surgical cleanup.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0702_REVISED.md`
2. **Dependency Analysis**: `handovers/0700_series/dependency_analysis.json`
3. **Architecture Analysis**: `docs/cleanup/architecture_analysis.md`
4. **Communications**: `handovers/0700_series/comms_log.json`
5. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY - DO THIS FIRST)

### Launch Validation Subagent

```
Use deep-researcher subagent:

"Validate orphan modules for comprehensive deletion.

STEP 1: Read dependency_analysis.json
- Find all files with 0 dependents

STEP 2: For each orphan, categorize:

SAFE TO DELETE (all must be true):
- Zero imports anywhere in codebase
- Not a runnable script (no if __name__ == '__main__')
- Not dynamically loaded (check for importlib, __import__)

KEEP - SCRIPT:
- Has if __name__ == '__main__'
- Meant to be run directly

KEEP - DYNAMIC:
- Loaded via importlib or similar
- Plugin architecture

UNCERTAIN:
- Edge cases needing human decision

STEP 3: Specific checks for known orphans:
```bash
# api_helpers - verify truly empty/unused
grep -rn 'api_helpers' src/ api/ tests/ --include='*.py'

# cleanup/ - verify dev tool only
grep -rn 'from.*cleanup import\|from cleanup import' src/ api/ --include='*.py'

# path_normalizer - check if only tests use it
grep -rn 'path_normalizer\|PathNormalizer' src/ api/ --include='*.py'

# Dead tests - find tests with all skips
grep -l '@pytest.mark.skip' tests/ -r
```

STEP 4: Output structured report:
- SAFE TO DELETE: [count] files, [list paths]
- KEEP (SCRIPT): [count] files, [list with reason]
- KEEP (DYNAMIC): [count] files, [list with reason]
- UNCERTAIN: [count] files, [list for decision]"
```

### Document Validation

```
## VALIDATION COMPLETE
Total orphans: [X]
Safe to delete: [Y]
Keep (scripts): [Z]
Keep (dynamic): [W]
Uncertain: [V]

SAFE TO DELETE LIST:
[Full path list from subagent]

KEEP LIST WITH REASONS:
[Path: reason]
```

---

## PHASE 1: EXECUTION

**Only proceed after Phase 0 complete.**

### Delete in Order

1. **Delete orphan directories first** (removes multiple files)
2. **Delete individual orphan files**
3. **Delete dead test files**
4. **Clean up __init__.py exports**

### Known Targets (validate first)

```bash
# Orphan directories
rm -rf src/giljo_mcp/api_helpers/

# Dead tests
rm tests/installer/unit/test_profile.py

# Evaluate these (may keep or delete based on validation):
# - src/giljo_mcp/cleanup/ (dev tool)
# - src/giljo_mcp/utils/path_normalizer.py (test-only usage)
```

---

## PHASE 2: VERIFICATION

```bash
# No broken imports
python -c "from src.giljo_mcp import *; print('Core OK')"
python -c "from api.app import app; print('API OK')"
python -c "from src.giljo_mcp.models import *; print('Models OK')"

# Quick test
pytest tests/unit -x -q 2>/dev/null | tail -5

# Verify deletions
ls src/giljo_mcp/api_helpers/ 2>/dev/null || echo "api_helpers DELETED"
```

---

## Communication

```json
{
  "id": "0702-revised-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0702-REVISED",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Orphan cleanup complete - [X] files deleted",
  "message": "[Summary]",
  "files_affected": ["[deleted files]"],
  "action_required": false,
  "context": {
    "validation": {
      "total_orphans": 271,
      "validated_safe": "[X]",
      "deleted": "[Y]",
      "kept_with_reason": "[Z]"
    }
  }
}
```

---

## Success Criteria

- [ ] Phase 0 validation complete with documented results
- [ ] All validated orphans deleted
- [ ] Imports still work
- [ ] Tests pass
- [ ] comms_log entry written
- [ ] Committed
