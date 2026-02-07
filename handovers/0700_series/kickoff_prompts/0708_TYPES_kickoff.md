# Kickoff: Handover 0708-TYPES - Type Hint Modernization

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW
**Estimated Effort:** 3-4 hours
**Date:** 2026-02-06

---

## Mission Statement

Modernize type annotations to PEP 585+ standards. Remove deprecated typing imports.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0708_TYPES.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
"Validate 0708-TYPES scope.

```bash
# PEP 585 violations
ruff check src/ api/ --select UP006 --statistics

# Deprecated imports
ruff check src/ api/ --select UP035 --statistics

# Optional style
ruff check src/ api/ --select UP045 --statistics

# Total type-related issues
ruff check src/ api/ --select UP --statistics
```

REPORT: Count by category, identify priority files."
```

---

## PHASE 1: EXECUTION

### Step 1: Bulk Auto-Fix (Safe)

```bash
# Fix what can be auto-fixed
ruff check src/ api/ --select UP006,UP035,UP045 --fix --unsafe-fixes
```

### Step 2: Manual Review

For remaining issues:
- Check TypeVar definitions
- Review runtime type checking
- Verify Generic class definitions

### Step 3: Return Type Annotations

Priority modules:
1. `src/giljo_mcp/services/*.py`
2. `src/giljo_mcp/tools/*.py`
3. `api/endpoints/**/*.py`

---

## PHASE 2: VERIFICATION

```bash
# Zero UP006/UP035/UP045
ruff check src/ api/ --select UP006,UP035,UP045

# Install mypy if needed
pip install mypy

# Run mypy
mypy src/giljo_mcp/ --ignore-missing-imports

# Tests pass
pytest tests/ -x -q
```

---

## Communication

```json
{
  "id": "0708-types-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0708-TYPES",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Type hint modernization complete",
  "message": "[Summary]",
  "files_affected": [],
  "action_required": false,
  "context": {
    "up006_fixed": "[X]",
    "up035_fixed": "[X]",
    "up045_fixed": "[X]",
    "return_types_added": "[X]"
  }
}
```

---

## Success Criteria

- [ ] UP006 = 0
- [ ] UP035 = 0
- [ ] UP045 = 0
- [ ] Mypy passes (ignore-missing-imports)
- [ ] Tests passing
- [ ] Committed
