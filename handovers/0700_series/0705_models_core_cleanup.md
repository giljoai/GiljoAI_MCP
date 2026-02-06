# Handover 0705: Models Core Cleanup

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW
**Estimated Effort:** 10-15 minutes
**Date:** 2026-02-06

---

## Mission Statement

Clean up Product, Project, and User models. Remove unused imports and optionally add `__repr__` methods for debugging consistency.

---

## Research Findings

**Assessment: MINIMAL SCOPE**

The models are already well-typed:
- All methods have proper return type hints
- No TODO/FIXME comments found
- Only 2 unused imports identified
- `__repr__` type hints handled by 0704

---

## Scope Summary

| Metric | Count |
|--------|-------|
| Unused imports to remove | 2 |
| Optional `__repr__` additions | 4 |
| TODOs found | 0 |
| Type hint gaps | 0 (handled by 0704) |

---

## Tasks

### Task 1: Remove Unused Import from products.py

**File:** `src/giljo_mcp/models/products.py`

Line 17: Remove `Float` from the sqlalchemy import (not used anywhere in file)

```python
# Current (line 17):
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func

# Change to:
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
```

### Task 2: Remove Unused Import from projects.py

**File:** `src/giljo_mcp/models/projects.py`

Line 18: Remove `UniqueConstraint` from the sqlalchemy import (not used)

```python
# Current (line 18):
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

# Change to:
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
```

### Task 3: Add `__repr__` to Product class (OPTIONAL)

**File:** `src/giljo_mcp/models/products.py`

Add after the class properties (around line 120):

```python
def __repr__(self) -> str:
    return f"<Product(id={self.id}, name='{self.name}', tenant_key='{self.tenant_key}')>"
```

### Task 4: Add `__repr__` to Project class (OPTIONAL)

**File:** `src/giljo_mcp/models/projects.py`

Add after the class properties (around line 100):

```python
def __repr__(self) -> str:
    return f"<Project(id={self.id}, name='{self.name}', product_id='{self.product_id}')>"
```

### Task 5: Add `__repr__` to VisionDocument class (OPTIONAL)

**File:** `src/giljo_mcp/models/products.py`

Add after the class methods (around line 570):

```python
def __repr__(self) -> str:
    return f"<VisionDocument(id={self.id}, name='{self.name}', product_id='{self.product_id}')>"
```

### Task 6: Add `__repr__` to Vision class (OPTIONAL)

**File:** `src/giljo_mcp/models/products.py`

Add after the column definitions (around line 637):

```python
def __repr__(self) -> str:
    return f"<Vision(id={self.id}, product_id='{self.product_id}')>"
```

---

## Verification

```bash
# Lint check for unused imports
ruff check src/giljo_mcp/models/products.py src/giljo_mcp/models/projects.py

# Verify Float not imported
grep -n "Float" src/giljo_mcp/models/products.py
# Expected: 0 matches

# Verify UniqueConstraint not imported
grep -n "UniqueConstraint" src/giljo_mcp/models/projects.py
# Expected: 0 matches

# Import verification
python -c "from src.giljo_mcp.models.products import Product, VisionDocument, Vision; print('Products OK')"
python -c "from src.giljo_mcp.models.projects import Project; print('Projects OK')"
```

---

## Files NOT Modified

- `auth.py` - User `__repr__` type hint handled by 0704
- `base.py` - Handled by 0704
- `agent_identity.py` - Handled by 0704
- Other model files - No changes needed

---

## Success Criteria

- [ ] Unused `Float` import removed from products.py
- [ ] Unused `UniqueConstraint` import removed from projects.py
- [ ] (Optional) `__repr__` methods added to Product, Project, VisionDocument, Vision
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

[Optional: Added __repr__ methods to Product, Project, VisionDocument, Vision for debugging consistency]

No behavior changes.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
