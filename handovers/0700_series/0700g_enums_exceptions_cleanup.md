# Handover 0700g: Enums and Exceptions Cleanup

## Context

**Pre-release cleanup decision (2026-02-04):** Remove unused enum values and exception classes identified by the dead code audit.

**Reference:** `handovers/0700_series/dead_code_audit.md` - Manual analysis sections

## Scope

Remove unused code from:
1. `src/giljo_mcp/enums.py` - Unused enum values and entire unused enums
2. `src/giljo_mcp/exceptions.py` - Exception classes that are never raised

**Files Affected:**
- `src/giljo_mcp/enums.py`
- `src/giljo_mcp/exceptions.py`
- Any files importing removed items

## Tasks

### 1. Remove Unused Enum Values

Location: `src/giljo_mcp/enums.py`

**Verify and remove if truly unused:**

- [ ] `AgentStatus.DECOMMISSIONED` - Deprecated in 0461b, agents no longer decommissioned
  - Grep: `grep -r "DECOMMISSIONED" src/ api/ --include="*.py"`
  - If only found in enum definition, remove it

### 2. Remove Entire Unused Enums

Based on audit findings, these enums were never implemented:

- [ ] `AugmentationType` enum (~8 lines)
  - Grep: `grep -r "AugmentationType" src/ api/ --include="*.py"`
  - If only found in enum definition + imports, remove entirely

- [ ] `ArchiveType` enum (~8 lines)
  - Grep: `grep -r "ArchiveType" src/ api/ --include="*.py"`
  - If only found in enum definition + imports, remove entirely

- [ ] `InteractionType` enum (~7 lines) - Verify usage first
  - Grep: `grep -r "InteractionType" src/ api/ --include="*.py"`
  - Only remove if truly unused

### 3. Remove Unused Exception Classes

Location: `src/giljo_mcp/exceptions.py`

**Verify each is never raised, then remove:**

- [ ] `TemplateValidationError` (~5 lines)
  - Grep: `grep -r "raise TemplateValidationError" src/ api/ --include="*.py"`
  - Grep: `grep -r "except TemplateValidationError" src/ api/ --include="*.py"`

- [ ] `TemplateRenderError` (~5 lines)
  - Grep: `grep -r "raise TemplateRenderError" src/ api/ --include="*.py"`
  - Grep: `grep -r "except TemplateRenderError" src/ api/ --include="*.py"`

- [ ] `GitOperationError` (~5 lines)
  - Grep: `grep -r "raise GitOperationError" src/ api/ --include="*.py"`

- [ ] `GitAuthenticationError` (~5 lines)
  - Grep: `grep -r "raise GitAuthenticationError" src/ api/ --include="*.py"`

- [ ] `GitRepositoryError` (~5 lines)
  - Grep: `grep -r "raise GitRepositoryError" src/ api/ --include="*.py"`

### 4. Remove Unused Imports of Removed Items

After removing enums/exceptions:

- [ ] Search for imports: `grep -r "from.*enums import.*AugmentationType" src/ api/`
- [ ] Search for imports: `grep -r "from.*exceptions import.*TemplateValidationError" src/ api/`
- [ ] Remove all import statements for deleted items
- [ ] Check `__init__.py` files for re-exports

### 5. Update __all__ Exports

- [ ] Remove deleted items from `__all__` in `enums.py`
- [ ] Remove deleted items from `__all__` in `exceptions.py`

## Verification

- [ ] All tests pass: `pytest tests/`
- [ ] No import errors on startup: `python -c "from giljo_mcp import enums, exceptions"`
- [ ] Grep confirms no remaining references to removed items
- [ ] Code that DOES use remaining enums/exceptions still works

## Risk Assessment

**LOW** - Removing unused code with no callers

**Mitigation:**
- Grep verification before each removal
- If ANY usage found (beyond definition), investigate before removing
- Tests will catch any missed dependencies

## Dependencies

- **Depends on:** None
- **Blocks:** None

## Estimated Impact

- **Lines removed:** ~50-70 (enum definitions + exception classes)
- **Files modified:** 2-3 (plus import cleanup)
- **Enums removed:** 2-4
- **Exceptions removed:** 5
