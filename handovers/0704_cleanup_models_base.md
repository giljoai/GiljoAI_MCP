# Handover 0704: Cleanup Models Base Layer

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert / tdd-implementor
**Priority:** High
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Depends On:** 0700, 0702, 0703

---

## Task Summary

Clean up the **foundation model layer**: base classes, enums, and exceptions. These files are imported by most of the codebase, so changes require careful validation.

**Risk Level:** Medium (many dependents, but typically stable interfaces)

**Scope:** 4 files

---

## Files In Scope

| File | Est. Lines | Risk | Expected Changes |
|------|-----------|------|------------------|
| `src/giljo_mcp/models/base.py` | ~50 | Medium | Review Base class |
| `src/giljo_mcp/enums.py` | ~200 | Medium | Review unused enums |
| `src/giljo_mcp/exceptions.py` | ~150 | Medium | Review exception hierarchy |
| `src/giljo_mcp/models/__init__.py` | ~50 | Low | Verify exports |

---

## Pre-Cleanup Analysis

### Identify All Dependents

Before making changes, identify files that import these modules:

```bash
# Files importing from base.py
grep -r "from.*models.base import" src/ api/ --include="*.py"
grep -r "from.*models import Base" src/ api/ --include="*.py"

# Files importing enums
grep -r "from.*enums import" src/ api/ --include="*.py"

# Files importing exceptions
grep -r "from.*exceptions import" src/ api/ --include="*.py"
```

Document the count before cleanup.

---

## Cleanup Checklist

### base.py

| Check | Action |
|-------|--------|
| `Base` class definition | Verify uses `declarative_base()` correctly |
| Utility functions | Review `generate_uuid()`, `generate_project_alias()` |
| DEPRECATED markers | Remove deprecated code or update markers |
| Type hints | Ensure all functions have type hints |

### enums.py

| Check | Action |
|-------|--------|
| Unused enum values | Check if referenced anywhere; remove if not |
| Duplicate definitions | Consolidate similar enums |
| Documentation | Each enum should have docstring |
| DEPRECATED enums | Remove or migrate |

### exceptions.py

| Check | Action |
|-------|--------|
| Exception hierarchy | Verify inheritance makes sense |
| Unused exceptions | Remove if never raised |
| Error messages | Ensure clear, actionable messages |
| Base exception | Should inherit from appropriate base |

---

## Implementation Plan

### Phase 1: Dependency Analysis (30 min)
1. Query cleanup_index for dependent counts
2. Document which files import each module
3. Identify breaking change risks

### Phase 2: base.py Cleanup (45 min)
1. Run linting
2. Review Base class implementation
3. Check utility functions for DEPRECATED markers
4. Verify all functions have return types
5. Run model tests

### Phase 3: enums.py Cleanup (1 hr)
1. List all enum classes and values
2. For each enum value, grep for usage
3. Remove unused values (document removals)
4. Add missing docstrings
5. Run all tests to catch breakage

### Phase 4: exceptions.py Cleanup (45 min)
1. List all exception classes
2. For each exception, grep for `raise` statements
3. Remove unused exceptions
4. Verify exception messages are useful
5. Run all tests

### Phase 5: Update Index (15 min)
```sql
UPDATE cleanup_index
SET status = 'cleaned',
    last_cleaned_at = NOW()
WHERE file_path IN (
    'src/giljo_mcp/models/base.py',
    'src/giljo_mcp/enums.py',
    'src/giljo_mcp/exceptions.py',
    'src/giljo_mcp/models/__init__.py'
);
```

---

## Testing Requirements

### Critical Tests
```bash
# All model tests
pytest tests/models/ -v

# All tests (catch ripple effects)
pytest tests/ -x --tb=short
```

### Import Verification
```python
# Verify no import errors after changes
from giljo_mcp.models import Base
from giljo_mcp.enums import *
from giljo_mcp.exceptions import *
```

### Migration Safety
If any enum values are removed, ensure:
- Database values don't reference them
- API responses don't use them

---

## Success Criteria

- [ ] ruff check passes on all 4 files
- [ ] 0 DEPRECATED markers remaining
- [ ] 0 TODO markers remaining
- [ ] All unused enums documented/removed
- [ ] All unused exceptions documented/removed
- [ ] Full test suite passes
- [ ] No import errors
- [ ] cleanup_index updated

---

## Rollback Plan

```bash
git checkout HEAD~1 -- src/giljo_mcp/models/base.py src/giljo_mcp/enums.py src/giljo_mcp/exceptions.py src/giljo_mcp/models/__init__.py
```

---

## Post-Cleanup Documentation

Document removed items:

**Removed Enums:**
- `EnumName.VALUE` - Reason: never used

**Removed Exceptions:**
- `SomeException` - Reason: never raised

---

## Next Handover

**0705_cleanup_models_core.md** - Continue with core model files (products, projects).
