# Kickoff: Handover 0705 - Models Core Cleanup

**Series:** 0700 Code Cleanup Series
**Handover:** 0705
**Risk Level:** LOW
**Estimated Effort:** 10-15 minutes
**Date:** 2026-02-06
**Depends On:** 0704 (must complete first)

---

## Mission Statement

Remove unused imports from Product and Project models. Optionally add `__repr__` methods for debugging consistency.

**NOTE:** This is a minimal handover - research found models are already well-typed with no TODOs.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0705_models_core_cleanup.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## Tasks

### Task 1: Remove Unused Import - products.py (REQUIRED)

**File:** `src/giljo_mcp/models/products.py`

Line 17: Remove `Float` from import:

```python
# Find this line:
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func

# Change to:
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
```

### Task 2: Remove Unused Import - projects.py (REQUIRED)

**File:** `src/giljo_mcp/models/projects.py`

Line 18: Remove `UniqueConstraint` from import:

```python
# Find this line:
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

# Change to:
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
```

### Task 3-6: Add `__repr__` Methods (OPTIONAL)

If time permits, add `__repr__` methods for debugging consistency:

**Product** (products.py, after class properties ~line 120):
```python
def __repr__(self) -> str:
    return f"<Product(id={self.id}, name='{self.name}', tenant_key='{self.tenant_key}')>"
```

**Project** (projects.py, after class properties ~line 100):
```python
def __repr__(self) -> str:
    return f"<Project(id={self.id}, name='{self.name}', product_id='{self.product_id}')>"
```

**VisionDocument** (products.py, after class methods ~line 570):
```python
def __repr__(self) -> str:
    return f"<VisionDocument(id={self.id}, name='{self.name}', product_id='{self.product_id}')>"
```

**Vision** (products.py, after column definitions ~line 637):
```python
def __repr__(self) -> str:
    return f"<Vision(id={self.id}, product_id='{self.product_id}')>"
```

---

## Verification

```bash
# Lint check
ruff check src/giljo_mcp/models/products.py src/giljo_mcp/models/projects.py

# Verify unused imports removed
grep -c "Float" src/giljo_mcp/models/products.py  # Expected: 0
grep -c "UniqueConstraint" src/giljo_mcp/models/projects.py  # Expected: 0

# Import verification
python -c "from src.giljo_mcp.models.products import Product, VisionDocument, Vision; print('Products OK')"
python -c "from src.giljo_mcp.models.projects import Project; print('Projects OK')"
```

---

## Communication

Write completion entry to `handovers/0700_series/comms_log.json`:

```json
{
  "id": "0705-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0705",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Models Core Cleanup complete - unused imports removed",
  "message": "Removed 2 unused imports (Float, UniqueConstraint). [Optional: Added __repr__ to 4 classes]. Models already well-typed - no TODOs found.",
  "files_affected": [
    "src/giljo_mcp/models/products.py",
    "src/giljo_mcp/models/projects.py"
  ],
  "action_required": false,
  "context": {
    "unused_imports_removed": 2,
    "repr_methods_added": "[0 or 4]",
    "todos_found": 0,
    "type_hint_gaps": 0,
    "assessment": "minimal scope - models already clean"
  }
}
```

---

## Success Criteria

- [ ] `Float` import removed from products.py
- [ ] `UniqueConstraint` import removed from projects.py
- [ ] (Optional) `__repr__` methods added
- [ ] `ruff check` passes
- [ ] Models import OK
- [ ] comms_log.json entry written
- [ ] Changes committed

---

## Commit Message Template

```
cleanup(0705): Remove unused imports from core models

Removed unused imports:
- products.py: Float (not used)
- projects.py: UniqueConstraint (not used)

No behavior changes.

```
