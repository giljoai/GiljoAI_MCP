# Handover 0708-TYPES: Comprehensive Type Hints

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW
**Estimated Effort:** 3-4 hours
**Date:** 2026-02-06

---

## CRITICAL: Large File Handling

**Files over 20K tokens (~500+ lines) MUST be read in batches.** Do NOT skip large files.

```python
# Read large files in chunks of 200 lines:
Read(file_path, offset=0, limit=200)    # Lines 1-200
Read(file_path, offset=200, limit=200)  # Lines 201-400
Read(file_path, offset=400, limit=200)  # Lines 401-600
# Continue until entire file is processed
```

---

## Mission Statement

Add comprehensive type hints across the codebase. Modernize annotations to PEP 585+ standards and prepare for mypy strict mode.

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
"Validate 0708-TYPES scope for type hint improvements.

CHECK 1: PEP 585 violations (List → list, Dict → dict)
```bash
ruff check src/ api/ --select UP006 --statistics
```

CHECK 2: Deprecated imports (typing.List, typing.Dict, etc.)
```bash
ruff check src/ api/ --select UP035 --statistics
```

CHECK 3: Optional annotation style
```bash
ruff check src/ api/ --select UP045 --statistics
```

CHECK 4: Current mypy status
```bash
mypy src/giljo_mcp/ --ignore-missing-imports --stats 2>&1 | tail -20
```

CHECK 5: Functions without return types
```bash
grep -rn "def .*):$" src/giljo_mcp/*.py | wc -l
grep -rn "def .*):" src/giljo_mcp/*.py | grep -v "-> " | head -20
```

REPORT: Confirm scope and identify priority modules."
```

---

## PHASE 1: EXECUTION

### Task 1: UP006 - PEP 585 Annotations (~470 instances)

**Strategy:** Modernize type annotations.

```python
# BEFORE (old style)
from typing import List, Dict, Optional, Set, Tuple

def process(items: List[str]) -> Dict[str, int]:
    pass

# AFTER (PEP 585+)
def process(items: list[str]) -> dict[str, int]:
    pass
```

**Bulk fix approach:**
```bash
# Many can be auto-fixed with ruff
ruff check src/ api/ --select UP006 --fix --unsafe-fixes
```

**Manual review needed for:**
- TypeVar bounds
- Generic class definitions
- Runtime type checking code

### Task 2: UP035 - Deprecated Imports (~122 instances)

**Strategy:** Remove unnecessary typing imports.

```python
# BEFORE
from typing import List, Dict, Optional, Union, Any

# AFTER (Python 3.10+)
from typing import Any  # Only keep what's truly needed

# Use built-in generics
list[str]  # instead of List[str]
dict[str, int]  # instead of Dict[str, int]
str | None  # instead of Optional[str]
str | int  # instead of Union[str, int]
```

### Task 3: UP045 - Optional Annotation Style (~19 instances)

**Strategy:** Use `X | None` instead of `Optional[X]`.

```python
# BEFORE
from typing import Optional
def get_user(id: str) -> Optional[User]:
    pass

# AFTER
def get_user(id: str) -> User | None:
    pass
```

### Task 4: Return Type Annotations

**Priority files** (core modules):
1. `src/giljo_mcp/services/*.py` - All service methods
2. `src/giljo_mcp/tools/*.py` - All MCP tools
3. `api/endpoints/**/*.py` - All endpoint functions

**Pattern:**
```python
# Add return types to all public functions
def get_project(self, project_id: str, tenant_key: str) -> Project | None:
    ...

async def create_job(self, data: JobCreate) -> AgentJob:
    ...
```

### Task 5: Mypy Configuration

Create/update `pyproject.toml` mypy section:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## PHASE 2: VERIFICATION

```bash
# Check remaining type issues
ruff check src/ api/ --select UP006,UP035,UP045 --statistics

# Run mypy
mypy src/giljo_mcp/ --ignore-missing-imports

# Verify no regressions
python -c "from api.app import app; print('API OK')"
pytest tests/ -x -q --tb=short
```

---

## Success Criteria

- [ ] Phase 0 validation complete
- [ ] UP006 count reduced to 0
- [ ] UP035 count reduced to 0
- [ ] UP045 count reduced to 0
- [ ] Core services have return type annotations
- [ ] Mypy passes with ignore-missing-imports
- [ ] All tests passing
- [ ] Committed

---

## Communication

```json
{
  "id": "0708-types-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0708-TYPES",
  "to_handovers": ["orchestrator", "0709-SECURITY"],
  "type": "info",
  "subject": "Type hint modernization complete",
  "message": "[Summary]",
  "files_affected": [],
  "action_required": false,
  "context": {
    "up006_before": 470,
    "up006_after": 0,
    "up035_before": 122,
    "up035_after": 0,
    "up045_before": 19,
    "up045_after": 0,
    "return_types_added": "[X]",
    "mypy_errors_remaining": "[X]"
  }
}
```

---

## Commit Message Template

```
cleanup(0708): Modernize type hints to PEP 585+

- Converted [X] List/Dict/Set annotations to built-in generics
- Removed [X] deprecated typing imports
- Converted [X] Optional[X] to X | None
- Added return types to [X] functions
- Configured mypy for type checking

Co-Authored-By: Claude <noreply@anthropic.com>
```
