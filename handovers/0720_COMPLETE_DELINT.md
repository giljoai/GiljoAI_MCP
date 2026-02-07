# Handover 0720: Complete Codebase Delinting

**Series:** 0700 Code Cleanup Series (Remediation)
**Risk Level:** MEDIUM
**Estimated Effort:** 6-8 hours (agent team)
**Date:** 2026-02-07
**Status:** READY FOR EXECUTION

---

## Background

The 0707-LINT handover was only ~15% completed before being marked done:
- T201 (print statements): ✅ Done (suppressed)
- BLE001 (blind except): 38% done (143 remain)
- ERA001, B904, F841, SIM102, RUF012: ❌ NOT STARTED

**Current State:** 1,850+ lint issues across src/ and api/

---

## Mission Statement

Achieve a **clean ruff check** on src/ and api/ directories. Fix ALL lint issues or explicitly suppress with documented rationale.

**Target:** `ruff check src/ api/` returns 0 errors

---

## Issue Breakdown by Priority

### PHASE 1: CRITICAL (Real Bugs) - ~400 issues
| Rule | Count | Description | Fix Strategy |
|------|-------|-------------|--------------|
| F821 | 13 | Undefined name | Add imports or fix typos |
| B008 | 324 | Mutable default argument | Use `None` + runtime assignment |
| F841 | 18 | Unused variable | Delete or use |
| F401 | 7 | Unused import | Delete |
| E711 | 2 | `== None` | Use `is None` |
| E712 | 43 | `== True/False` | Use truthy/falsy or `is` |

### PHASE 2: HIGH (Code Quality) - ~80 issues
| Rule | Count | Description | Fix Strategy |
|------|-------|-------------|--------------|
| ERA001 | 20 | Commented-out code | Delete (git has history) |
| RUF012 | 18 | Mutable class default | Use field() or ClassVar |
| B007 | 4 | Unused loop variable | Use `_` prefix |
| B025 | 6 | Duplicate except | Merge handlers |
| PLW0603 | 17 | Global statement | Refactor to class/param |
| A001/A002/A003 | 9 | Builtin shadowing | Rename variables |

### PHASE 3: MEDIUM (Style/Performance) - ~700 issues
| Rule | Count | Description | Fix Strategy |
|------|-------|-------------|--------------|
| TRY301 | 196 | Raise within try | Extract to function or suppress |
| TRY401 | 146 | Verbose log message | Remove exception from log call |
| TRY400 | 115 | error vs exception | Use logger.exception() |
| TRY300 | 102 | Try-consider-else | Add else clause or suppress |
| TID252 | 47 | Relative imports | Convert to absolute |
| PERF401 | 24 | Manual list comp | Use list comprehension |
| SIM102 | 18 | Collapsible if | Merge conditions |

### PHASE 4: INTENTIONAL SUPPRESSIONS - ~600 issues
| Rule | Count | Rationale |
|------|-------|-----------|
| PLC0415 | 417 | Lazy imports for performance - SUPPRESS |
| ARG001/ARG002 | 95 | API compatibility - SUPPRESS where intentional |
| SLF001 | 11 | Test access to privates - SUPPRESS in tests |
| TC001/TC002/TC003 | 18 | Type-checking imports - SUPPRESS (pedantic) |
| RUF013 | 45 | Implicit Optional - SUPPRESS (valid pattern) |

---

## Agent Team Structure

### Coordinator (You)
- Launch phase agents in sequence
- Verify each phase completion before next
- Handle merge conflicts
- Final validation

### Phase 1 Agent: Bug Fixer
**Focus:** F821, B008, F841, F401, E711, E712
**Skills:** Python debugging, import resolution
**Validation:** `ruff check src/ api/ --select F821,B008,F841,F401,E711,E712` returns 0

### Phase 2 Agent: Code Quality
**Focus:** ERA001, RUF012, B007, B025, PLW0603, A001-A003
**Skills:** Refactoring, code cleanup
**Validation:** `ruff check src/ api/ --select ERA001,RUF012,B007,B025,PLW0603,A001,A002,A003` returns 0

### Phase 3 Agent: Style Fixer
**Focus:** TRY series, TID252, PERF series, SIM series
**Skills:** Exception handling patterns, performance optimization
**Validation:** `ruff check src/ api/ --select TRY,TID252,PERF,SIM` returns 0

### Phase 4 Agent: Configuration
**Focus:** Update .ruff.toml with intentional suppressions
**Skills:** Ruff configuration, documentation
**Validation:** `ruff check src/ api/` returns 0

---

## Phase 1 Kickoff Prompt

```
You are the Bug Fixer agent for handover 0720 - Complete Codebase Delinting.

## Your Mission
Fix all CRITICAL lint issues that represent real bugs:
- F821 (13): Undefined names - these cause RuntimeError
- B008 (324): Mutable default arguments - classic Python bug
- F841 (18): Unused variables - dead code
- F401 (7): Unused imports - dead code
- E711 (2): `== None` comparisons
- E712 (43): `== True/False` comparisons

## Approach

### Step 1: Auto-fix what's possible
```bash
ruff check src/ api/ --select F401,E711,E712 --fix
```

### Step 2: Fix F821 (undefined names) - MANUAL
For each undefined name:
1. Find the correct import
2. Add the import
3. Or fix the typo

```bash
ruff check src/ api/ --select F821 --output-format=grouped
```

### Step 3: Fix B008 (mutable defaults) - MANUAL
Pattern:
```python
# BEFORE (bug)
def func(items: list = []):
    items.append("x")  # Mutates shared default!

# AFTER (safe)
def func(items: list | None = None):
    if items is None:
        items = []
    items.append("x")
```

```bash
ruff check src/ api/ --select B008 --output-format=grouped
```

### Step 4: Fix F841 (unused variables) - MANUAL
Either:
- Delete the variable
- Use it
- Prefix with `_` if intentionally unused

```bash
ruff check src/ api/ --select F841 --output-format=grouped
```

## Validation
After ALL fixes:
```bash
ruff check src/ api/ --select F821,B008,F841,F401,E711,E712 --statistics
# Expected: 0 errors

python -c "from api.app import app; print('API OK')"
pytest tests/ -x -q --tb=short
```

## Completion
When done, report:
- Issues fixed per rule
- Any issues that couldn't be fixed (with explanation)
- Test results
```

---

## Phase 2 Kickoff Prompt

```
You are the Code Quality agent for handover 0720 - Complete Codebase Delinting.

## Your Mission
Fix code quality issues:
- ERA001 (20): Commented-out code - delete it
- RUF012 (18): Mutable class defaults
- B007 (4): Unused loop variables
- B025 (6): Duplicate exception handlers
- PLW0603 (17): Global statements
- A001/A002/A003 (9): Builtin shadowing

## Approach

### Step 1: ERA001 - Commented-out code
Delete ALL commented-out code. We have git history.
```bash
ruff check src/ api/ --select ERA001 --output-format=grouped
```

### Step 2: RUF012 - Mutable class defaults
```python
# BEFORE (bug)
class Config:
    items: list = []  # Shared across instances!

# AFTER (safe)
from dataclasses import dataclass, field

@dataclass
class Config:
    items: list = field(default_factory=list)

# OR for non-dataclass
class Config:
    items: ClassVar[list] = []  # If truly shared
    # OR
    def __init__(self):
        self.items = []
```

### Step 3: B007 - Unused loop variables
```python
# BEFORE
for i in range(10):
    do_something()

# AFTER
for _ in range(10):
    do_something()
```

### Step 4: B025 - Duplicate exception handlers
```python
# BEFORE
try:
    ...
except ValueError:
    log_error()
except TypeError:
    log_error()  # Duplicate!

# AFTER
try:
    ...
except (ValueError, TypeError):
    log_error()
```

### Step 5: PLW0603 - Global statements
Refactor to:
- Pass as parameter
- Use class attribute
- Use module-level constant (if read-only)

### Step 6: A001/A002/A003 - Builtin shadowing
Rename variables that shadow builtins:
- `id` -> `item_id`, `user_id`
- `type` -> `item_type`, `entity_type`
- `input` -> `user_input`
- `list` -> `items`, `values`

## Validation
```bash
ruff check src/ api/ --select ERA001,RUF012,B007,B025,PLW0603,A001,A002,A003 --statistics
# Expected: 0 errors
```
```

---

## Phase 3 Kickoff Prompt

```
You are the Style Fixer agent for handover 0720 - Complete Codebase Delinting.

## Your Mission
Fix style and performance issues:
- TRY301 (196): Raise within try
- TRY401 (146): Verbose log message
- TRY400 (115): error instead of exception
- TRY300 (102): Try-consider-else
- TID252 (47): Relative imports
- PERF401 (24): Manual list comprehension
- SIM102 (18): Collapsible if

## Approach

### TRY401 - Verbose log message (easiest, do first)
```python
# BEFORE
except Exception as e:
    logger.exception(f"Failed: {e}")  # e is redundant

# AFTER
except Exception:
    logger.exception("Failed")  # exception() already includes exc info
```

### TRY400 - error vs exception
```python
# BEFORE
except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)

# AFTER
except Exception:
    logger.exception("Failed")
```

### TRY301 - Raise within try
If the pattern is intentional error transformation, add noqa:
```python
try:
    result = risky_operation()
except SpecificError as e:
    raise DomainError("Context") from e  # noqa: TRY301
```

### TRY300 - Try-consider-else
Many are false positives. Add noqa if the pattern is intentional.

### TID252 - Relative imports
```python
# BEFORE
from .sibling import func
from ..parent import Class

# AFTER
from src.giljo_mcp.sibling import func
from src.giljo_mcp.parent import Class
```

### PERF401 - List comprehension
```python
# BEFORE
result = []
for item in items:
    result.append(item.name)

# AFTER
result = [item.name for item in items]
```

### SIM102 - Collapsible if
```python
# BEFORE
if condition1:
    if condition2:
        do_something()

# AFTER
if condition1 and condition2:
    do_something()
```

## Validation
```bash
ruff check src/ api/ --select TRY,TID252,PERF,SIM --statistics
# Target: 0 errors (or documented suppressions)
```
```

---

## Phase 4 Kickoff Prompt

```
You are the Configuration agent for handover 0720 - Complete Codebase Delinting.

## Your Mission
Update .ruff.toml to suppress intentional patterns and achieve clean build.

## Suppressions to Add

Add to `ignore` list in .ruff.toml:

```toml
ignore = [
    # ... existing ignores ...

    # Intentional patterns
    "PLC0415",  # Import outside top-level - lazy loading pattern
    "ARG001",   # Unused function argument - API compatibility
    "ARG002",   # Unused method argument - API compatibility
    "SLF001",   # Private member access - testing needs this
    "TC001",    # Typing-only first-party import - pedantic
    "TC002",    # Typing-only third-party import - pedantic
    "TC003",    # Typing-only stdlib import - pedantic
    "RUF013",   # Implicit Optional - valid pattern
]
```

## Per-File Ignores
Add any remaining file-specific ignores with documentation.

## Final Validation
```bash
ruff check src/ api/
# Expected: All checks passed!

ruff check src/ api/ --statistics
# Expected: No output (0 issues)
```

## Documentation
Update the ignore list comments to explain each suppression.
```

---

## Success Criteria

- [ ] Phase 1 complete: F821, B008, F841, F401, E711, E712 = 0
- [ ] Phase 2 complete: ERA001, RUF012, B007, B025, PLW0603, A00x = 0
- [ ] Phase 3 complete: TRY, TID252, PERF, SIM = 0 or suppressed
- [ ] Phase 4 complete: .ruff.toml updated with documented suppressions
- [ ] Final: `ruff check src/ api/` returns 0 errors
- [ ] All tests passing
- [ ] Pre-commit hooks pass on all files

---

## Commit Strategy

One commit per phase:
1. `fix(0720): Phase 1 - Critical bug fixes (F821, B008, F841, F401, E711, E712)`
2. `fix(0720): Phase 2 - Code quality cleanup (ERA001, RUF012, B007, B025, PLW0603, A00x)`
3. `fix(0720): Phase 3 - Style and performance fixes (TRY, TID252, PERF, SIM)`
4. `chore(0720): Phase 4 - Ruff configuration with documented suppressions`

---

---

## PHASE 5: FRONTEND LINTING (Vue/JS)

### Current State
ESLint is **completely broken** in frontend:
- `eslint.config.js` has import error: `FlatCompat` not exported from `@eslint/compat`
- npm script uses deprecated CLI flags (`--ignore-path`)
- Pre-commit ESLint hook disabled ("bash not found on Windows")

### Phase 5 Kickoff Prompt

```
You are the Frontend Linter agent for handover 0720 - Complete Codebase Delinting.

## Your Mission
Fix ESLint configuration and clean up frontend lint issues.

## Step 1: Fix ESLint Configuration

The current eslint.config.js is broken. Fix the import:

```bash
cd frontend
cat eslint.config.js  # Review current config
```

Update to use correct imports from @eslint/compat and @eslint/js.

## Step 2: Fix package.json lint script

Replace deprecated flags:
```json
// BEFORE
"lint": "eslint --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix --ignore-path .gitignore"

// AFTER (ESLint 9+ flat config)
"lint": "eslint src/ --fix"
```

## Step 3: Run ESLint and fix issues

```bash
npm run lint
```

Fix all auto-fixable issues, then manually fix remaining.

## Step 4: Re-enable pre-commit hook

Update .pre-commit-config.yaml to use npx instead of bash:

```yaml
- repo: local
  hooks:
    - id: eslint
      name: ESLint
      entry: npx --prefix frontend eslint frontend/src/ --fix
      language: system
      files: \.(js|jsx|ts|tsx|vue)$
      pass_filenames: false
```

## Validation
```bash
cd frontend && npm run lint
# Expected: No errors

cd .. && pre-commit run eslint --all-files
# Expected: Passed
```
```

---

## Notes

- Each phase agent should complete fully before next phase starts
- Large files (500+ lines) must be read in chunks
- Run tests after each phase to catch regressions
- If a fix breaks tests, investigate before proceeding
- Frontend (Phase 5) can run in parallel with backend phases
