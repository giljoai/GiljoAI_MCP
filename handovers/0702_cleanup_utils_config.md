# Handover 0702: Cleanup Utils & Config

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Depends On:** 0700 (Index Creation)

---

## Task Summary

First cleanup handover targeting **low-risk leaf nodes**: utility functions and configuration files. These files have few or no dependents, making them safe starting points that build cleanup confidence.

**Scope:** 8 files (utils + config)

---

## Files In Scope

### Utils Layer

| File | Est. Lines | Expected Changes |
|------|-----------|------------------|
| `src/giljo_mcp/utils/path_resolver.py` | ~50 | Lint, review |
| `src/giljo_mcp/utils/__init__.py` | ~20 | Lint |

### Config Layer

| File | Est. Lines | Expected Changes |
|------|-----------|------------------|
| `src/giljo_mcp/config/defaults.py` | ~100 | Review defaults |
| `src/giljo_mcp/config/__init__.py` | ~30 | Lint |

### Related Tests

| File | Purpose |
|------|---------|
| `tests/utils/test_path_resolver.py` | Path resolution tests |
| `tests/config/test_defaults.py` | Config defaults tests |

---

## Cleanup Checklist (Per File)

### 1. Automated Linting
```bash
# Python linting
ruff check src/giljo_mcp/utils/ src/giljo_mcp/config/ --fix
black src/giljo_mcp/utils/ src/giljo_mcp/config/

# Verify
ruff check src/giljo_mcp/utils/ src/giljo_mcp/config/
```

### 2. Manual Review Checklist

For each file, check:

| Check | Action |
|-------|--------|
| **DEPRECATED markers** | If code is truly deprecated, REMOVE it. If still needed, update/remove marker. |
| **TODO markers** | Convert to GitHub issue OR remove if obsolete. |
| **Unused imports** | Remove (ruff should catch these). |
| **Unused functions** | Check if exported. If not used anywhere, remove. |
| **Hardcoded paths** | Replace with `Path()` patterns. |
| **Magic numbers** | Extract to named constants if unclear. |
| **Dead code** | Unreachable branches, impossible conditions - remove. |
| **Excessive comments** | Remove obvious comments, keep complex logic explanations. |

### 3. Verification Steps

After each file:
```bash
# 1. Lint passes
ruff check <file>

# 2. Related tests pass
pytest tests/utils/ tests/config/ -v

# 3. No import errors
python -c "from giljo_mcp.utils import *; from giljo_mcp.config import *"
```

---

## Expected Findings

Based on initial codebase scan:

| File | Expected Markers |
|------|-----------------|
| `path_resolver.py` | 0-1 TODO |
| `defaults.py` | Possibly outdated defaults |

---

## Implementation Plan

### Phase 1: Automated Fixes (15 min)
1. Run ruff with `--fix` on target directories
2. Run black for formatting
3. Commit automated fixes separately

### Phase 2: utils/ Manual Review (45 min)
1. Review `path_resolver.py`
   - Check for hardcoded Windows paths
   - Verify cross-platform compatibility
   - Remove any DEPRECATED code
2. Review `__init__.py`
   - Verify exports are used
3. Run tests

### Phase 3: config/ Manual Review (45 min)
1. Review `defaults.py`
   - Check if defaults are current
   - Remove any DEPRECATED values
   - Verify all defaults have corresponding usage
2. Review `__init__.py`
3. Run tests

### Phase 4: Update Index (15 min)
```sql
UPDATE cleanup_index
SET status = 'cleaned',
    last_cleaned_at = NOW(),
    deprecation_markers = 0,
    todo_markers = 0
WHERE file_path IN (
    'src/giljo_mcp/utils/path_resolver.py',
    'src/giljo_mcp/utils/__init__.py',
    'src/giljo_mcp/config/defaults.py',
    'src/giljo_mcp/config/__init__.py'
);
```

---

## Testing Requirements

### Existing Tests
- Run all tests in `tests/utils/` and `tests/config/`
- All must pass after cleanup

### Regression Check
```bash
# Full test suite to catch any ripple effects
pytest tests/ -x --ignore=tests/cleanup/
```

---

## Success Criteria

- [ ] ruff check passes with 0 warnings on target files
- [ ] black produces no changes (already formatted)
- [ ] 0 DEPRECATED markers remaining in scope
- [ ] 0 TODO markers remaining (converted to issues or removed)
- [ ] All utils tests pass
- [ ] All config tests pass
- [ ] cleanup_index updated with status='cleaned'

---

## Rollback Plan

Git reset to pre-cleanup commit:
```bash
git checkout HEAD~1 -- src/giljo_mcp/utils/ src/giljo_mcp/config/
```

---

## Post-Cleanup State

Document final marker counts:

| File | Before | After |
|------|--------|-------|
| `path_resolver.py` | X DEPRECATED, Y TODO | 0, 0 |
| `defaults.py` | X DEPRECATED, Y TODO | 0, 0 |

---

## Next Handover

**0703_cleanup_auth_logging.md** - Continue with low-risk auth and logging utilities.
