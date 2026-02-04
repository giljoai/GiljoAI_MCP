# Handover 0700e: Template System Cleanup

## Context

**Pre-release cleanup decision (2026-02-04):** Remove deprecated template system components that have been superseded by the unified template manager.

**Reference:** `handovers/0700_series/dead_code_audit.md` - Strategic Direction Change section

## Scope

Remove deprecated template-related code:
1. `TemplateManager` alias (deprecated in favor of `UnifiedTemplateManager`)
2. `template_content` field (deprecated in favor of `system_instructions` + `user_instructions`)
3. Legacy template field references

**Files Affected:**
- `src/giljo_mcp/template_manager.py` - Remove alias and legacy notes
- `src/giljo_mcp/models/templates.py` - Remove deprecated field
- `src/giljo_mcp/template_seeder.py` - Remove legacy field handling

## Tasks

### 1. Remove TemplateManager Alias

Location: `src/giljo_mcp/template_manager.py:1048-1051`

```python
# DEPRECATED: Use UnifiedTemplateManager directly. This alias will be removed in v4.0.
TemplateManager = UnifiedTemplateManager  # DEPRECATED
```

- [ ] Remove the alias definition
- [ ] Remove the DEPRECATED comment
- [ ] Search for any code using `TemplateManager` and update to `UnifiedTemplateManager`
- [ ] Update imports in files that use `from template_manager import TemplateManager`

### 2. Remove template_content Deprecated Field

Location: `src/giljo_mcp/models/templates.py:76`

```python
comment="DEPRECATED (v3.1): Use system_instructions + user_instructions. Kept for backward compatibility."
```

- [ ] Remove `template_content` column from model
- [ ] Update baseline migration to exclude this column
- [ ] Search for any code reading/writing `template_content`
- [ ] Ensure all templates use `system_instructions` + `user_instructions`

### 3. Remove Legacy Field from Template Seeder

Location: `src/giljo_mcp/template_seeder.py:248`

```python
# DEPRECATED: Legacy field for backward compatibility
```

- [ ] Remove code that populates deprecated fields
- [ ] Update seed data to only use current fields
- [ ] Verify seeded templates work correctly

### 4. Remove template_content from Template Manager

Location: `src/giljo_mcp/template_manager.py:133`

```python
- template_content: DEPRECATED (v3.0 compatibility only)
```

- [ ] Remove handling of `template_content` parameter
- [ ] Update docstrings to remove deprecated field references
- [ ] Update any method signatures that accept `template_content`

### 5. Clean Up Related Code

- [ ] Search for `template_content` across entire codebase
- [ ] Remove any schema fields exposing `template_content`
- [ ] Update API responses that include `template_content`
- [ ] Update frontend if it displays/edits `template_content`

## Verification

- [ ] All tests pass: `pytest tests/`
- [ ] Template seeding works: `python install.py` seeds templates correctly
- [ ] Template CRUD operations work via API
- [ ] No references to `template_content` remain (except historical docs)
- [ ] No references to `TemplateManager` alias remain

## Risk Assessment

**LOW** - Template system has been stable since v3.1

**Mitigation:**
- `UnifiedTemplateManager` is the active implementation
- `system_instructions` + `user_instructions` is the active data model
- Seed data and tests already use new format

## Dependencies

- **Depends on:** 0700b (if template column is in baseline migration)
- **Blocks:** None

## Estimated Impact

- **Lines removed:** ~50-80 (alias, deprecated field, legacy handling)
- **Files modified:** 4-5
- **Columns removed:** 1 (template_content)
